"""Support knowledge base API (plan §5.1).

Envelope: ``{success, data}``; errors are ``HTTPException`` with
``detail={success, error, code}`` and codes from ``core/errors.py``.

Contract highlights:

* operator search and the AI only see ``status='published'``;
* editing a published article keeps it published (version++), so it never
  disappears from answers while an operator fixes a typo;
* ``expected_version`` is the edit lock — stale writers get
  ``409 KB_VERSION_CONFLICT``;
* deleting a published article is refused with ``409 KB_DOC_PUBLISHED`` —
  archive it first;
* ``status='all'`` exists only on list endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.store import kb as kb_store

router = APIRouter()

_STATUS_RE = "^(draft|published|archived|all)$"
_SOURCE_RE = "^(manual|import|candidate|faq)$"
_CANDIDATE_STATUS_RE = "^(new|accepted|rejected|all)$"
_DECISION_RE = "^(accept|reject)$"


class KbDocIn(BaseModel):
    """Article payload for create/update."""

    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=200_000)
    slug: str | None = Field(None, min_length=1, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=20)
    source: str = Field("manual", pattern=_SOURCE_RE)


class KbUpdateIn(KbDocIn):
    """Update adds the optimistic-lock version."""

    expected_version: int = Field(..., ge=1)


class PublishIn(BaseModel):
    """Publish requires the version the operator last saw."""

    expected_version: int = Field(..., ge=1)


class CandidateDecisionIn(BaseModel):
    """Accept (creates a draft) or reject (status + reason) an idea."""

    decision: str = Field(..., pattern=_DECISION_RE)
    reason: str | None = Field(None, max_length=500)
    title: str | None = Field(None, max_length=200)
    body: str | None = Field(None, max_length=200_000)


def _error(status_code: int, code: E, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "error": message, "code": code.value},
    )


def _not_found(what: str) -> HTTPException:
    return _error(404, E.NOT_FOUND, f"{what} not found")


def _invalid(message: str) -> HTTPException:
    return _error(400, E.INVALID_INPUT, message)


def _version_conflict(error: kb_store.KbVersionConflict) -> HTTPException:
    return _error(
        409,
        E.KB_VERSION_CONFLICT,
        f"Article changed (current version {error.current_version}); reload and retry",
    )


def _published_conflict() -> HTTPException:
    return _error(
        409,
        E.KB_DOC_PUBLISHED,
        "Published articles cannot be deleted; archive the article first",
    )


# ── List / search (static paths before /kb/{doc_id}) ──────────────────────

@router.get("/kb")
async def list_kb_docs(
    status: str | None = Query(None, pattern=_STATUS_RE),
    q: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Admin list. Default (no status) returns published; ``all`` includes drafts."""
    try:
        data = await service.store.list_docs(
            status=status, q=q, page=page, per_page=per_page
        )
    except ValueError as e:
        raise _invalid(str(e)) from e
    return {"success": True, "data": data}


@router.get("/kb/search")
async def search_kb_docs(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=20),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Operator search over published articles (FTS + ts_rank_cd)."""
    items = await service.store.search_docs(q, limit=limit)
    return {"success": True, "data": {"items": items}}


@router.get("/kb/candidates")
async def list_kb_candidates(
    status: str | None = Query("new", pattern=_CANDIDATE_STATUS_RE),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Article ideas; ``all`` lists every status."""
    try:
        data = await service.store.list_candidates(
            status=status, page=page, per_page=per_page
        )
    except ValueError as e:
        raise _invalid(str(e)) from e
    return {"success": True, "data": data}


@router.post("/kb/candidates/{candidate_id}")
async def decide_kb_candidate(
    candidate_id: int,
    payload: CandidateDecisionIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Accept an idea (draft article + ``doc_id``) or reject it."""
    try:
        data = await service.store.decide_candidate(
            candidate_id,
            decision=payload.decision,
            reason=payload.reason,
            title=payload.title,
            body=payload.body,
            updated_by=admin.id,
        )
    except kb_store.KbNotFound as e:
        raise _not_found("Candidate") from e
    except ValueError as e:
        raise _invalid(str(e)) from e
    return {"success": True, "data": data}


# ── CRUD ─────────────────────────────────────────────────────────────────

@router.post("/kb")
async def create_kb_doc(
    payload: KbDocIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Create a draft article."""
    try:
        data = await service.store.create_doc(
            title=payload.title,
            body=payload.body,
            slug=payload.slug,
            tags=payload.tags,
            source=payload.source,
            updated_by=admin.id,
        )
    except ValueError as e:
        raise _invalid(str(e)) from e
    return {
        "success": True,
        "data": {
            "id": data["id"],
            "slug": data.get("slug"),
            "version": data.get("version", 1),
            "status": data.get("status", "draft"),
        },
    }


@router.get("/kb/{doc_id}")
async def get_kb_doc(
    doc_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    doc = await service.store.get_doc(doc_id)
    if doc is None:
        raise _not_found("Article")
    return {"success": True, "data": {"doc": doc}}


@router.put("/kb/{doc_id}")
async def update_kb_doc(
    doc_id: int,
    payload: KbUpdateIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Update in place; stale ``expected_version`` → 409."""
    try:
        data = await service.store.update_doc(
            doc_id,
            title=payload.title,
            body=payload.body,
            slug=payload.slug,
            tags=payload.tags,
            expected_version=payload.expected_version,
            updated_by=admin.id,
        )
    except kb_store.KbNotFound as e:
        raise _not_found("Article") from e
    except kb_store.KbVersionConflict as e:
        raise _version_conflict(e) from e
    except ValueError as e:
        raise _invalid(str(e)) from e
    return {"success": True, "data": data}


@router.post("/kb/{doc_id}/publish")
async def publish_kb_doc(
    doc_id: int,
    payload: PublishIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    try:
        data = await service.store.publish_doc(
            doc_id,
            expected_version=payload.expected_version,
            updated_by=admin.id,
        )
    except kb_store.KbNotFound as e:
        raise _not_found("Article") from e
    except kb_store.KbVersionConflict as e:
        raise _version_conflict(e) from e
    return {"success": True, "data": data}


@router.post("/kb/{doc_id}/archive")
async def archive_kb_doc(
    doc_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    try:
        data = await service.store.archive_doc(doc_id, updated_by=admin.id)
    except kb_store.KbNotFound as e:
        raise _not_found("Article") from e
    except kb_store.KbVersionConflict as e:
        raise _version_conflict(e) from e
    return {"success": True, "data": data}


@router.post("/kb/{doc_id}/restore")
async def restore_kb_doc(
    doc_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    try:
        data = await service.store.restore_doc(doc_id, updated_by=admin.id)
    except kb_store.KbNotFound as e:
        raise _not_found("Article") from e
    except kb_store.KbVersionConflict as e:
        raise _version_conflict(e) from e
    return {"success": True, "data": data}


@router.delete("/kb/{doc_id}")
async def delete_kb_doc(
    doc_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    try:
        await service.store.delete_doc(doc_id)
    except kb_store.KbNotFound as e:
        raise _not_found("Article") from e
    except kb_store.KbDocPublished as e:
        raise _published_conflict() from e
    return {"success": True, "data": {"deleted": True}}
