"""Шаблоны ответов оператора (Этап C, C1).

Контракт: ``{success, data}``; ошибки — ``HTTPException`` с
``detail={success, error, code}`` и кодами из ``core/errors.py``.

* ``shortcut`` — ``^[a-z0-9][a-z0-9_-]{0,31}$``, уникален;
* дубль → ``409 TEMPLATE_EXISTS``;
* аудит ``template.create|template.update|template.delete`` пишет только
  ``shortcut`` (тело шаблона в журнал не попадает).
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.audit import record as record_audit
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.store import templates as templates_store

router = APIRouter()

_SHORTCUT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_RESOURCE = "support_template"


class TemplateIn(BaseModel):
    """Поля создания/обновления шаблона."""

    shortcut: str = Field(..., min_length=1, max_length=32)
    title: str = Field(..., min_length=1, max_length=120)
    body: str = Field(..., min_length=1, max_length=4000)
    category: str | None = Field(None, max_length=64)


def _error(status_code: int, code: E, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "error": message, "code": code.value},
    )


def _not_found() -> HTTPException:
    return _error(404, E.NOT_FOUND, "Template not found")


def _invalid(message: str) -> HTTPException:
    return _error(400, E.INVALID_INPUT, message)


def _conflict() -> HTTPException:
    return _error(409, E.TEMPLATE_EXISTS, "Template shortcut already exists")


def _validate_shortcut(shortcut: str) -> str:
    value = str(shortcut or "").strip()
    if not _SHORTCUT_RE.match(value):
        raise _invalid(
            "shortcut must match ^[a-z0-9][a-z0-9_-]{0,31}$"
        )
    return value


@router.get("/templates")
async def list_templates(
    q: str | None = Query(None, max_length=200),
    category: str | None = Query(None, max_length=64),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Список шаблонов с поиском по shortcut/title/body и категорией."""
    try:
        data = await service.store.list_templates(
            q=q,
            category=category,
            limit=per_page,
            offset=(page - 1) * per_page,
        )
    except ValueError as exc:
        raise _invalid(str(exc)) from exc
    return {
        "success": True,
        "data": {**data, "page": page, "per_page": per_page},
    }


@router.post("/templates")
async def create_template(
    payload: TemplateIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Создать шаблон; дубль shortcut → 409."""
    shortcut = _validate_shortcut(payload.shortcut)
    try:
        data = await service.store.create_template(
            shortcut=shortcut,
            title=payload.title,
            body=payload.body,
            category=payload.category,
            created_by=admin.id,
        )
    except templates_store.TemplateExists as exc:
        raise _conflict() from exc
    except ValueError as exc:
        raise _invalid(str(exc)) from exc

    await record_audit(
        service,
        actor_id=admin.id,
        action="template.create",
        resource=_RESOURCE,
        resource_id=str(data["id"]),
        payload={"shortcut": data.get("shortcut", shortcut)},
    )
    return {"success": True, "data": data}


@router.put("/templates/{template_id}")
async def update_template(
    template_id: int,
    payload: TemplateIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Обновить шаблон целиком; отсутствие → 404, дубль shortcut → 409."""
    shortcut = _validate_shortcut(payload.shortcut)
    try:
        data = await service.store.update_template(
            template_id,
            shortcut=shortcut,
            title=payload.title,
            body=payload.body,
            category=payload.category,
        )
    except templates_store.TemplateExists as exc:
        raise _conflict() from exc
    except ValueError as exc:
        raise _invalid(str(exc)) from exc
    if data is None:
        raise _not_found()

    await record_audit(
        service,
        actor_id=admin.id,
        action="template.update",
        resource=_RESOURCE,
        resource_id=str(template_id),
        payload={"shortcut": data.get("shortcut", shortcut)},
    )
    return {"success": True, "data": data}


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Удалить шаблон; отсутствие → 404."""
    existing = await service.store.get_template(template_id)
    if existing is None:
        raise _not_found()
    deleted = await service.store.delete_template(template_id)
    if not deleted:
        raise _not_found()

    await record_audit(
        service,
        actor_id=admin.id,
        action="template.delete",
        resource=_RESOURCE,
        resource_id=str(template_id),
        payload={"shortcut": existing.get("shortcut")},
    )
    return {"success": True, "data": {"deleted": True}}


@router.post("/templates/{template_id}/use")
async def use_template(
    template_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Отметить применение шаблона: ``uses = uses + 1``."""
    data = await service.store.bump_template_use(template_id)
    if data is None:
        raise _not_found()
    return {"success": True, "data": data}
