"""Публичная форма ИИ-предложки — единый источник истины для API.

Строка `support_ai_suggestion` хранит служебные поля (`gate_action`,
`gate_reason`, `needs_human`) и тяжёлый `chunk` внутри `used`; клиенту они не
нужны. Модуль собирает ровно контракт плана §5.2 и используется и в
`suggestions.py`, и в `conversations.py`. I/O нет: `config_for` лишь читает
готовый снимок настроек с сервиса.
"""
from __future__ import annotations

from typing import Any

from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.gate import confidence_level

# Действия гейта, при которых ответ считается прошедшим ворота.
_PASSED_ACTIONS = ("auto", "shadow", "suggest")


def config_for(service: Any) -> AiConfig:
    """Снимок настроек ИИ: runtime.config, иначе сборка из `service.settings`."""
    runtime = getattr(service, "ai", None)
    config = getattr(runtime, "config", None)
    if isinstance(config, AiConfig):
        return config
    return AiConfig.from_settings(getattr(service, "settings", None))


def used_items(raw: Any) -> list[dict[str, Any]]:
    """`used` JSONB → [{doc_id,title}] (без тяжёлого `chunk`)."""
    if not isinstance(raw, (list, tuple)):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        doc_id = item.get("doc_id")
        try:
            doc_id = int(doc_id) if doc_id is not None else None
        except (TypeError, ValueError):
            doc_id = None
        result.append({"doc_id": doc_id, "title": str(item.get("title") or "")})
    return result


def level(suggestion: dict[str, Any], config: AiConfig) -> str:
    """Уровень уверенности (`sure|check|unsure`) от порога в настройках."""
    action = str(suggestion.get("gate_action") or "")
    text = suggestion.get("final_text") or suggestion.get("text") or ""
    used = suggestion.get("used")
    try:
        score = float(suggestion.get("confidence") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    return confidence_level(
        score,
        config.min_confidence,
        bool(used),
        bool(suggestion.get("needs_human")),
        bool(str(text).strip()),
        passed=action in _PASSED_ACTIONS,
    )


def public_suggestion(suggestion: dict[str, Any], config: AiConfig) -> dict[str, Any]:
    """Публичная форма (план §5.2) — питает карточку и «Почему так?»."""
    return {
        "id": suggestion.get("id"),
        "conversation_id": suggestion.get("conversation_id"),
        "message_id": suggestion.get("message_id"),
        "text": suggestion.get("text"),
        "final_text": suggestion.get("final_text"),
        "operator_note": suggestion.get("operator_note"),
        "confidence": suggestion.get("confidence"),
        "level": level(suggestion, config),
        "used": used_items(suggestion.get("used")),
        "reason": suggestion.get("reason"),
        "gate": {
            "action": suggestion.get("gate_action"),
            "reason": suggestion.get("gate_reason"),
        },
        "model": suggestion.get("model"),
        "status": suggestion.get("status"),
        "created_at": suggestion.get("created_at"),
    }
