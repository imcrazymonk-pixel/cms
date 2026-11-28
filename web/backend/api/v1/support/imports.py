"""Knowledge-base import API (plan §7.5).

Contract (kept deliberately minimal — JSON body, no multipart):

``POST /kb/import``::

    {"kind": "text", "text": "...", "operator_names": ["..."], "dry_run": false}
    {"kind": "result_json", "payload": {...} | "<result.json as text>",
     "operator_names": [...], "dry_run": false}

``payload`` accepts either an already-parsed object or the raw file contents as
a string. Uploaded files are not required: the frontend reads the file and
sends its text, which keeps the size check and the error envelope identical for
both formats.

``GET /kb/import/{job_id}`` returns
``{id, kind, status, progress, total, result?, error?, started_at, finished_at}``.

``POST /kb/import/{job_id}/cancel`` marks an active job
``{status: 'error', error: 'cancelled'}``.

HTTP 200 is returned for a created job (202 semantics live in the body, per the
plan), 409 ``JOB_BUSY`` for a second active import, 413 ``IMPORT_TOO_LARGE``
before parsing.
"""
from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.imports import runner as import_runner
from web.backend.core.support.imports.errors import ImportParseError, ImportTooLarge
from web.backend.core.support.store import jobs as jobs_store

router = APIRouter()

_MAX_OPERATOR_NAMES = 50
_MAX_OPERATOR_NAME_LEN = 80


class ImportIn(BaseModel):
    """Import request; ``payload`` is an object or the raw ``result.json`` text."""

    kind: Literal["text", "result_json"]
    text: str | None = None
    payload: dict[str, Any] | str | None = None
    operator_names: list[str] | None = Field(default=None, max_length=_MAX_OPERATOR_NAMES)
    dry_run: bool = False


def _error(status_code: int, code: E, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "error": message, "code": code.value},
    )


def _not_found() -> HTTPException:
    return _error(404, E.NOT_FOUND, "Import job not found")


def _invalid(message: str) -> HTTPException:
    return _error(400, E.INVALID_INPUT, message)


def _clean_names(names: list[str] | None) -> list[str] | None:
    if names is None:
        return None
    cleaned: list[str] = []
    for name in names:
        value = str(name).strip()
        if not value:
            continue
        if len(value) > _MAX_OPERATOR_NAME_LEN:
            raise _invalid(f"operator name is longer than {_MAX_OPERATOR_NAME_LEN} chars")
        cleaned.append(value)
    return cleaned or None


def _job_view(job: dict[str, Any]) -> dict[str, Any]:
    result = job.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            pass
    return {
        "id": int(job["id"]),
        "kind": job.get("kind"),
        "status": job.get("status"),
        "progress": int(job.get("progress") or 0),
        "total": job.get("total"),
        "result": result,
        "error": job.get("error"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
    }


@router.post("/kb/import")
async def create_import(
    body: ImportIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Validate the input size, create a queued job and start the runner."""
    if body.kind == "text":
        if not (body.text or "").strip():
            raise _invalid("text is required for kind='text'")
    else:
        if body.payload is None:
            raise _invalid("payload is required for kind='result_json'")

    try:
        import_runner.check_size(body.kind, body.text, body.payload)
    except ImportTooLarge as exc:
        raise _error(413, E.IMPORT_TOO_LARGE, str(exc)) from exc
    except ImportParseError as exc:
        raise _invalid(str(exc)) from exc

    job_payload = {
        "kind": body.kind,
        "text": body.text if body.kind == "text" else None,
        "payload": body.payload if body.kind == "result_json" else None,
        "operator_names": _clean_names(body.operator_names),
        "dry_run": bool(body.dry_run),
    }

    try:
        job = await service.store.create_job(
            kind=import_runner.JOB_KIND,
            payload=job_payload,
            created_by=admin.id,
        )
    except jobs_store.JobBusy as exc:
        raise _error(
            409,
            E.JOB_BUSY,
            "Another import is already running; wait for it or cancel it",
        ) from exc
    except ValueError as exc:
        raise _invalid(str(exc)) from exc

    job_id = int(job["id"])
    import_runner.spawn(service, job_id)
    return {"success": True, "data": {"job_id": job_id}}


@router.get("/kb/import/{job_id}")
async def get_import_job(
    job_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Current job state; ``result`` appears once the job is ``done``."""
    job = await service.store.get_job(job_id)
    if job is None:
        raise _not_found()
    return {"success": True, "data": _job_view(job)}


@router.post("/kb/import/{job_id}/cancel")
async def cancel_import_job(
    job_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Cancel a queued/running job; finished jobs are returned unchanged."""
    job = await service.store.cancel_job(job_id)
    if job is None:
        raise _not_found()
    return {
        "success": True,
        "data": {"status": job.get("status"), "error": job.get("error")},
    }
