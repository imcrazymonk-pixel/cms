"""Background import runner (plan §7.1, §7.4, §7.5).

The endpoint only creates a ``support_job`` row and spawns a task; all parsing
happens in ``asyncio.to_thread`` and QA pairs are written in batches of 500,
so a 50 MiB ``result.json`` never blocks the event loop.

Limits (checked before parsing where possible):

* text paste — 20 MiB;
* ``result.json`` — 50 MiB;
* 200 000 messages;
* 200 article candidates per run;
* 120 s wall clock.

Result shape stored in ``support_job.result``::

    {questions, pairs_created, skipped_duplicates, candidates_created, errors[]}

``dry_run`` adds ``would_create`` / ``would_skip`` / ``would_create_candidates``
and writes nothing.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Iterable

from web.backend.core.support.imports import cluster, tg_json, tg_text
from web.backend.core.support.imports.errors import ImportParseError, ImportTooLarge

logger = logging.getLogger(__name__)

JOB_KIND = "kb_import"
BATCH_SIZE = 500
MAX_TEXT_BYTES = 20 * 1024 * 1024
MAX_JSON_BYTES = 50 * 1024 * 1024
MAX_MESSAGES = 200_000
MAX_CANDIDATES = 200
TIME_BUDGET_SECONDS = 120.0


def _payload_dict(job: dict[str, Any]) -> dict[str, Any]:
    raw = job.get("payload")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return dict(raw) if isinstance(raw, dict) else {}


def check_size(
    kind: str,
    text: str | bytes | None = None,
    payload: str | bytes | dict[str, Any] | None = None,
) -> None:
    """Validate input size before job creation (→ 413 ``IMPORT_TOO_LARGE``)."""
    if kind == "text":
        if text is None:
            raise ImportParseError("text is required for kind='text'")
        tg_text.check_text_size(text)
        if len(text.encode("utf-8") if isinstance(text, str) else text) > MAX_TEXT_BYTES:
            raise ImportTooLarge("text exceeds 20 MiB")
    elif kind == "result_json":
        if payload is None:
            raise ImportParseError("payload is required for kind='result_json'")
        tg_json.check_json_size(payload)
    else:
        raise ImportParseError(f"unknown import kind: {kind!r}")


def _parse_sync(
    kind: str,
    raw: Any,
    operator_names: Iterable[str] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Blocking parse — always called via ``asyncio.to_thread``."""
    if kind == "text":
        messages = tg_text.parse_text(raw, operator_names)
        return messages, tg_text.build_pairs(messages)
    if kind == "result_json":
        messages = tg_json.parse_json(raw, operator_names)
        return messages, tg_json.build_pairs(messages)
    raise ImportParseError(f"unknown import kind: {kind!r}")


def _empty_result() -> dict[str, Any]:
    return {
        "questions": 0,
        "pairs_created": 0,
        "skipped_duplicates": 0,
        "candidates_created": 0,
        "errors": [],
    }


def _cancelled(job: dict[str, Any] | None) -> bool:
    if job is None:
        return True
    if job.get("status") == "error" and job.get("error") == "cancelled":
        return True
    return job.get("status") not in ("queued", "running")


async def _lookup(store: Any, job_id: int) -> dict[str, Any] | None:
    getter = getattr(store, "get_job", None)
    return await getter(job_id) if callable(getter) else None


async def run_job(service: Any, job_id: int) -> dict[str, Any] | None:
    """Execute one queued import job; safe to call directly in tests."""
    store = service.store
    job = await _lookup(store, job_id)
    if job is None:
        return None

    payload = _payload_dict(job)
    kind = str(payload.get("kind") or "text")
    dry_run = bool(payload.get("dry_run"))
    operator_names = payload.get("operator_names") or None
    raw = payload.get("text") if kind == "text" else payload.get("payload")

    claimed = await store.claim_job(job_id)
    if claimed is None:
        # Another worker/process took the job first.
        return await _lookup(store, job_id)

    started = time.monotonic()
    result = _empty_result()

    try:
        check_size(kind, raw if kind == "text" else None, raw if kind == "result_json" else None)
        messages, pairs = await asyncio.to_thread(_parse_sync, kind, raw, operator_names)

        if len(messages) > MAX_MESSAGES:
            raise ImportTooLarge(f"chat contains more than {MAX_MESSAGES} messages")
        after_parse = await _lookup(store, job_id)
        if _cancelled(after_parse):
            return after_parse
        if time.monotonic() - started > TIME_BUDGET_SECONDS:
            raise TimeoutError("import exceeded 120 s during parsing")

        result["questions"] = len(pairs)
        await store.update_job(
            job_id, progress=0, total=len(pairs), result=dict(result)
        )

        if dry_run:
            candidates = cluster.build_candidates(pairs, limit=MAX_CANDIDATES)
            result.update(
                dry_run=True,
                would_create=len(pairs),
                would_skip=0,
                would_create_candidates=len(candidates),
                candidates_found=len(candidates),
            )
            await store.update_job(job_id, progress=100, total=len(pairs))
            await store.finish_job(job_id, status="done", result=result)
            return result

        processed = 0
        for offset in range(0, len(pairs), BATCH_SIZE):
            current = await _lookup(store, job_id)
            if _cancelled(current):
                # Cancel already stamped status/error.
                return current
            if time.monotonic() - started > TIME_BUDGET_SECONDS:
                raise TimeoutError("import exceeded 120 s")

            batch = pairs[offset : offset + BATCH_SIZE]
            created, duplicates = await store.add_qa_pairs_batch(
                batch, source="import"
            )
            result["pairs_created"] += int(created)
            result["skipped_duplicates"] += int(duplicates)
            processed += len(batch)
            await store.update_job(
                job_id,
                progress=processed,
                total=len(pairs),
                result=dict(result),
            )

        candidates = cluster.build_candidates(pairs, limit=MAX_CANDIDATES)
        for candidate in candidates:
            current = await _lookup(store, job_id)
            if _cancelled(current):
                return current
            await store.create_candidate(
                topic=candidate["topic"],
                question=candidate["question"],
                answer=candidate["answer"],
                source="import",
            )
            result["candidates_created"] += 1

        await store.update_job(job_id, progress=100, total=len(pairs))
        await store.finish_job(job_id, status="done", result=result)
        return result

    except ImportTooLarge as exc:
        result["errors"].append(str(exc))
        await store.finish_job(
            job_id, status="error", result=result, error=f"IMPORT_TOO_LARGE: {exc}"
        )
        return result
    except (ImportParseError, TimeoutError) as exc:
        result["errors"].append(str(exc))
        prefix = "IMPORT_PARSE_FAILED" if isinstance(exc, ImportParseError) else "IMPORT_TIMEOUT"
        await store.finish_job(job_id, status="error", result=result, error=f"{prefix}: {exc}")
        return result
    except Exception as exc:  # noqa: BLE001 — the job must end, the app must live
        logger.exception("Support import job %s failed", job_id)
        result["errors"].append(str(exc))
        await store.finish_job(job_id, status="error", result=result, error=str(exc)[:2000])
        return result


def spawn(service: Any, job_id: int) -> asyncio.Task:
    """Schedule :func:`run_job` and remember the task on the service."""
    task = asyncio.create_task(run_job(service, job_id), name=f"support-import-{job_id}")
    tasks = getattr(service, "import_tasks", None)
    if isinstance(tasks, set):
        tasks.add(task)

        def _done(finished: asyncio.Task) -> None:
            tasks.discard(finished)
            if not finished.cancelled() and finished.exception() is not None:
                logger.error("Support import task crashed: %s", finished.exception())

        task.add_done_callback(_done)
    return task
