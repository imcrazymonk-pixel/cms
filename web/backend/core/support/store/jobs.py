"""``support_job`` — background jobs for imports (plan §2.7, §7.5).

One active job per ``kind`` is enforced by ``uq_support_job_active``; the
application-level check raises :class:`JobBusy` (→ 409 ``JOB_BUSY``) and the
unique index catches the create race.

Follows ``store/*`` conventions: an ``AsyncSession`` in, **no commit** — the
``SupportStore`` facade owns the transaction.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

STATUSES = ("queued", "running", "done", "error")
ACTIVE_STATUSES = ("queued", "running")

_JOB_COLUMNS = (
    "id, kind, status, progress, total, payload, result, error, "
    "created_by, started_at, finished_at"
)


class JobsError(Exception):
    """Base class for job-store errors."""


class JobBusy(JobsError):
    """A queued/running job of the same ``kind`` already exists."""

    def __init__(self, kind: str):
        super().__init__(f"job of kind {kind!r} is already active")
        self.kind = kind


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row._mapping)


def _json_param(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


async def create_job(
    db: AsyncSession,
    *,
    kind: str,
    payload: dict[str, Any] | None = None,
    created_by: int | None = None,
    total: int | None = None,
) -> dict[str, Any]:
    """Insert a ``queued`` job; a second active job of the same kind → JobBusy."""
    clean_kind = str(kind or "").strip()
    if not clean_kind:
        raise ValueError("job kind is required")
    if len(clean_kind) > 64:
        raise ValueError("job kind is too long")

    existing = (
        await db.execute(
            sql_text(
                "SELECT id FROM support_job "
                "WHERE kind = :kind AND status IN ('queued', 'running') "
                "LIMIT 1"
            ),
            {"kind": clean_kind},
        )
    ).fetchone()
    if existing is not None:
        raise JobBusy(clean_kind)

    try:
        row = (
            await db.execute(
                sql_text(
                    """
                    INSERT INTO support_job (kind, status, payload, total, created_by, progress)
                    VALUES (:kind, 'queued', CAST(:payload AS jsonb), :total, :created_by, 0)
                    RETURNING
                    """
                    + _JOB_COLUMNS
                ),
                {
                    "kind": clean_kind,
                    "payload": _json_param(payload),
                    "total": int(total) if total is not None else None,
                    "created_by": int(created_by) if created_by is not None else None,
                },
            )
        ).fetchone()
    except IntegrityError as exc:
        # Lost the race against another creator: the partial unique index wins.
        raise JobBusy(clean_kind) from exc
    return _row_to_dict(row) or {}


async def get_job(db: AsyncSession, job_id: int) -> dict[str, Any] | None:
    """One job by id, or ``None``."""
    row = (
        await db.execute(
            sql_text(f"SELECT {_JOB_COLUMNS} FROM support_job WHERE id = :id"),
            {"id": int(job_id)},
        )
    ).fetchone()
    return _row_to_dict(row)


async def claim_job(db: AsyncSession, job_id: int) -> dict[str, Any] | None:
    """``queued`` → ``running`` atomically; ``None`` when already taken."""
    row = (
        await db.execute(
            sql_text(
                f"UPDATE support_job SET status = 'running', started_at = now() "
                f"WHERE id = :id AND status = 'queued' "
                f"RETURNING {_JOB_COLUMNS}"
            ),
            {"id": int(job_id)},
        )
    ).fetchone()
    return _row_to_dict(row)


async def update_job(
    db: AsyncSession,
    job_id: int,
    *,
    progress: int | None = None,
    total: int | None = None,
    result: Any = None,
    error: str | None = None,
) -> dict[str, Any] | None:
    """Update progress/total/result/error of an existing job."""
    assignments: list[str] = []
    params: dict[str, Any] = {"id": int(job_id)}
    if progress is not None:
        assignments.append("progress = :progress")
        params["progress"] = max(0, int(progress))
    if total is not None:
        assignments.append("total = :total")
        params["total"] = max(0, int(total))
    if result is not None:
        assignments.append("result = CAST(:result AS jsonb)")
        params["result"] = _json_param(result)
    if error is not None:
        assignments.append("error = :error")
        params["error"] = str(error)[:2000]
    if not assignments:
        return await get_job(db, job_id)

    row = (
        await db.execute(
            sql_text(
                f"UPDATE support_job SET {', '.join(assignments)} "
                f"WHERE id = :id RETURNING {_JOB_COLUMNS}"
            ),
            params,
        )
    ).fetchone()
    return _row_to_dict(row)


async def finish_job(
    db: AsyncSession,
    job_id: int,
    *,
    status: str = "done",
    result: Any = None,
    error: str | None = None,
) -> dict[str, Any] | None:
    """Move a job to ``done``/``error`` and stamp ``finished_at``."""
    if status not in ("done", "error"):
        raise ValueError(f"finish status must be done|error, got {status!r}")
    row = (
        await db.execute(
            sql_text(
                "UPDATE support_job SET status = :status, "
                "result = COALESCE(CAST(:result AS jsonb), result), "
                "error = :error, finished_at = now() "
                f"WHERE id = :id RETURNING {_JOB_COLUMNS}"
            ),
            {
                "id": int(job_id),
                "status": status,
                "result": _json_param(result) if result is not None else None,
                "error": (str(error)[:2000] if error is not None else None),
            },
        )
    ).fetchone()
    return _row_to_dict(row)


async def cancel_job(db: AsyncSession, job_id: int) -> dict[str, Any] | None:
    """Cancel an active job (``status='error'``, ``error='cancelled'``)."""
    row = (
        await db.execute(
            sql_text(
                "UPDATE support_job SET status = 'error', error = 'cancelled', "
                "finished_at = now() "
                "WHERE id = :id AND status IN ('queued', 'running') "
                f"RETURNING {_JOB_COLUMNS}"
            ),
            {"id": int(job_id)},
        )
    ).fetchone()
    if row is not None:
        return _row_to_dict(row)
    # Already finished or missing: report the current state unchanged.
    return await get_job(db, job_id)
