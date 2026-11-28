"""Support AI assistant — settings, pause, activity, stats and sandbox (plan §5.3).

All endpoints return {success, data}; errors use `core/errors.py` codes. The
API key is never exposed: `GET/PUT /assistant/settings` return only `has_key`
and `effective_mode`. Writes go through `core.settings_values.upsert_value`
(the shared registry write path) followed by the regular settings hot reload.
`POST /assistant/try` is a read-only sandbox: it calls the provider and the
gate but never touches the store.
"""
from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core import integrations
from web.backend.core.database import get_db
from web.backend.core.errors import E
from web.backend.core.settings_values import upsert_value
from web.backend.core.support import SupportService
from web.backend.core.support.ai.config import MODES, AiConfig
from web.backend.core.support.ai.gate import decide as gate_decide
from web.backend.core.support.ai.gate import tone_of
from web.backend.core.support.ai.links import expand_links
from web.backend.core.support.ai.outbound import check as outbound_check
from web.backend.core.support.ai.prompt import build_prompt
from web.backend.core.support.ai.provider import ProviderError
from web.backend.core.support.ai.responder import _normalize_used
from web.backend.core.support.deps import get_support_service

logger = logging.getLogger(__name__)
router = APIRouter()

_MODE_RE = "^(off|shadow|suggest|auto)$"


class SettingsIn(BaseModel):
    """Параметры, которые меняются с экрана ИИ (ключ сюда не входит)."""

    mode: str | None = Field(None, pattern=_MODE_RE)
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    require_kb: bool | None = None
    auto_per_hour: int | None = Field(None, ge=0)
    debounce_seconds: int | None = Field(None, ge=3, le=60)


class PauseIn(BaseModel):
    """Пауза на `hours` (1..744) либо до `until` (не дальше +31 дня)."""

    hours: int | None = Field(None, ge=1, le=744)
    until: datetime | None = None
    note: str | None = Field(None, max_length=500)


class TryIn(BaseModel):
    """Песочница: вопрос оператора, без записи в БД."""

    text: str = Field(..., min_length=1, max_length=2000)
    assume_auto: bool = False


def _invalid(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"success": False, "error": message, "code": E.INVALID_INPUT.value},
    )


def _config(service: SupportService) -> AiConfig:
    runtime = getattr(service, "ai", None)
    config = getattr(runtime, "config", None)
    if isinstance(config, AiConfig):
        return config
    return AiConfig.from_settings(getattr(service, "settings", None))


async def _pause(service: SupportService) -> dict[str, Any] | None:
    store = getattr(service, "store", None)
    getter = getattr(store, "get_pause", None) if store is not None else None
    if not callable(getter):
        return None
    try:
        return await getter()
    except Exception as e:  # noqa: BLE001 — статус не должен падать из-за паузы
        logger.debug("AI pause read failed: %s", type(e).__name__)
        return None


def _pause_payload(pause: Any) -> dict[str, Any] | None:
    if not pause:
        return None
    return {
        "until": pause.get("until"),
        "by": pause.get("by"),
        "note": pause.get("note"),
    }


def _settings_payload(config: AiConfig, pause: Any) -> dict[str, Any]:
    return {
        "mode": config.mode,
        "effective_mode": config.effective_mode,
        "has_key": config.has_key,
        "paused": _pause_payload(pause),
        "model": config.model,
        "fallback_model": config.fallback_model,
        "base_url": config.base_url,
        "min_confidence": config.min_confidence,
        "require_kb": config.require_kb,
        "auto_per_hour": config.auto_per_hour,
        "human_hold_minutes": config.human_hold_minutes,
        "debounce_seconds": config.debounce_seconds,
        "kb_budget_chars": config.kb_budget_chars,
        "language": config.language,
        "brand": config.brand,
        "allowed_domains": list(config.allowed_domains),
    }


def _apply_overrides(config: AiConfig, body: SettingsIn) -> AiConfig:
    """Накатить присланные поля на снапшот (для ответа PUT)."""
    updates: dict[str, Any] = {}
    if body.mode is not None:
        if body.mode not in MODES:
            raise _invalid("Недопустимый режим ИИ")
        updates["mode"] = body.mode
    if body.min_confidence is not None:
        updates["min_confidence"] = float(body.min_confidence)
    if body.require_kb is not None:
        updates["require_kb"] = bool(body.require_kb)
    if body.auto_per_hour is not None:
        updates["auto_per_hour"] = int(body.auto_per_hour)
    if body.debounce_seconds is not None:
        updates["debounce_seconds"] = int(body.debounce_seconds)
    if not updates:
        return config

    mode = updates.get("mode", config.mode)
    updates["effective_mode"] = mode if config.has_key else "off"
    return replace(config, **updates)


# ── settings ───────────────────────────────────────────────────────────────

@router.get("/assistant/settings")
async def get_assistant_settings(
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Текущие настройки ИИ без `api_key` (только `has_key`)."""
    config = _config(service)
    return {"success": True, "data": _settings_payload(config, await _pause(service))}


@router.put("/assistant/settings")
async def update_assistant_settings(
    body: SettingsIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
    db: AsyncSession = Depends(get_db),
):
    """Записать параметры в реестр и перезагрузить runtime без рестарта."""
    changes: list[tuple[str, str]] = []
    if body.mode is not None:
        changes.append(("support_ai_mode", body.mode))
    if body.min_confidence is not None:
        changes.append(("support_ai_min_confidence", str(float(body.min_confidence))))
    if body.require_kb is not None:
        changes.append(("support_ai_require_kb", "1" if body.require_kb else "0"))
    if body.auto_per_hour is not None:
        changes.append(("support_ai_auto_per_hour", str(int(body.auto_per_hour))))
    if body.debounce_seconds is not None:
        changes.append(("support_ai_debounce_seconds", str(int(body.debounce_seconds))))

    for key, value in changes:
        await upsert_value(db, key, value)
    if changes:
        await db.commit()

    runtime: dict[str, Any] = {}
    if changes:
        try:
            runtime = await integrations.on_settings_changed(
                request.app, db, [key for key, _ in changes],
            )
        except Exception as e:  # noqa: BLE001 — сохранение уже состоялось
            runtime = {"warnings": [f"runtime: {type(e).__name__}"]}

    config = _apply_overrides(_config(service), body)
    return {
        "success": True,
        "data": _settings_payload(config, await _pause(service)),
        "runtime": runtime,
    }


# ── pause ──────────────────────────────────────────────────────────────────

@router.post("/assistant/pause")
async def pause_assistant(
    body: PauseIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Поставить паузу (1..744 ч либо до `until`, максимум 31 день)."""
    if (body.hours is None) == (body.until is None):
        raise _invalid("Укажите ровно одно из полей: hours или until")
    try:
        pause = await service.store.set_pause(
            by=admin.username,
            hours=body.hours,
            until=body.until,
            note=body.note,
        )
    except ValueError as e:
        raise _invalid(str(e)) from None
    return {"success": True, "data": _pause_payload(pause)}


@router.delete("/assistant/pause")
async def resume_assistant(
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Снять паузу (режим ИИ при этом не меняется)."""
    await service.store.clear_pause()
    return {"success": True, "data": {"paused": False}}


# ── activity / stats ───────────────────────────────────────────────────────

@router.get("/assistant/activity")
async def assistant_activity(
    since: datetime | None = Query(None),
    before: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Лента активности ИИ (новые сверху, курсор `before`)."""
    items = await service.store.list_activity(since=since, before_id=before, limit=limit)
    return {"success": True, "data": {"items": items}}


@router.get("/assistant/stats")
async def assistant_stats(
    days: int = Query(30, ge=1, le=90),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Агрегаты по предложкам/автоответам за период."""
    data = await service.store.assistant_stats(days=days)
    return {"success": True, "data": data}


# ── sandbox ────────────────────────────────────────────────────────────────

@router.post("/assistant/try")
async def assistant_try(
    body: TryIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Прогнать вопрос через провайдера и ворота — без записи в БД."""
    config = _config(service)
    if not config.has_key:
        raise HTTPException(
            status_code=409,
            detail={
                "success": False,
                "error": "API-ключ ИИ не задан",
                "code": E.AI_KEY_MISSING.value,
            },
        )

    runtime = getattr(service, "ai", None)
    provider = getattr(runtime, "provider", None)
    if provider is None:
        raise HTTPException(
            status_code=409,
            detail={"success": False, "error": "Провайдер ИИ недоступен", "code": E.AI_DISABLED.value},
        )

    links = getattr(runtime, "links", ()) or ()
    text = body.text.strip()
    bundle = build_prompt(
        config=config,
        messages=[{"direction": "in", "text": text}],
        client_text=text,
        links=links,
    )

    try:
        completion = await provider.complete_json(bundle.messages, config)
    except ProviderError as e:
        logger.warning("AI sandbox provider error: %s", e.code)
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Ошибка провайдера ИИ", "code": E.PROVIDER_ERROR.value},
        )
    except Exception as e:  # noqa: BLE001 — песочница не должна ронять API
        logger.warning("AI sandbox failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Ошибка провайдера ИИ", "code": E.PROVIDER_ERROR.value},
        )

    draft = dict(completion.draft or {})
    raw_reply = str(draft.get("reply") or "").strip()
    expanded = expand_links(raw_reply, links)
    reply = str(expanded.text or "").strip()
    used = _normalize_used(draft.get("used"), bundle.citations)
    draft["reply"] = reply
    draft["used"] = used

    gate_config = config
    if body.assume_auto and config.has_key:
        gate_config = replace(config, mode="auto", effective_mode="auto")

    verdict = outbound_check(reply, config.allowed_domains)
    gate = gate_decide(
        conversation={"id": 0, "status": "open"},
        client_text=text,
        draft=draft,
        kb_hits=len(bundle.citations),
        runtime=gate_config,
        pause=None,
        recent_auto_count=0,
        tone=tone_of(text),
        human_hold=False,
        window_open=True,
        profile_available=False,
    )
    if not bool(verdict.get("ok", True)) and gate.get("action") == "auto":
        gate = {**gate, "action": "suggest", "reason": "outbound_blocked"}

    return {
        "success": True,
        "data": {
            "draft": {
                "reply": reply,
                "operator_note": str(draft.get("operator_note") or "").strip(),
                "used": used,
                "confidence": draft.get("confidence"),
                "clarify": bool(draft.get("clarify")),
                "needs_human": bool(draft.get("needs_human")),
            },
            "gate": gate,
        },
    }
