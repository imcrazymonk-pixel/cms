"""Raw-SQL доступ к ИИ-сuggestion'ам, паузе и черновикам оператора.

Стиль `store/*`: функции принимают `AsyncSession` и **не коммитят** — владеет
транзакцией фасад `SupportStore`. Идентификаторы SQL — контролируемые
константы, значения — только bind-параметры.

Таблица `support_ai_suggestion` расширена миграцией 006:
`final_text`, `answer_message_id`, `operator_note`, `gate_action`,
`gate_reason`, `latency_ms`, `tokens_in`, `tokens_out`, `used` (JSONB).
Пауза — JSON в `support_setting['aiPause']`, черновик оператора —
`support_operator_draft`.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.support.store.settings import get_json_setting, set_json_setting

PAUSE_KEY = "aiPause"
PAUSE_MAX_DAYS = 31
PAUSE_MAX_HOURS = PAUSE_MAX_DAYS * 24

_SUGGESTION_STATUSES = ("pending", "sent", "edited", "rejected", "superseded")
_SUGGESTION_COLUMNS = (
    "id, conversation_id, message_id, text, confidence, needs_human, reason, model, "
    "sources, status, decided_at, created_at, final_text, answer_message_id, "
    "operator_note, gate_action, gate_reason, latency_ms, tokens_in, tokens_out, used"
)
_DRAFT_COLUMNS = "actor_id, conversation_id, text, mode, quote, from_suggestion_id, updated_at"
_MAX_PAGE = 100
_MAX_ACTIVITY = 100

_UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(_UTC)


def _as_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=_UTC)
    if isinstance(value, str) and value.strip():
        text_value = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text_value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=_UTC)
    return None


def _iso(value: datetime) -> str:
    return value.astimezone(_UTC).isoformat().replace("+00:00", "Z")


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row._mapping)
    used = data.get("used")
    if isinstance(used, str):
        try:
            data["used"] = json.loads(used)
        except (TypeError, ValueError):
            data["used"] = []
    return data


def _used_json(used: Iterable[Any] | None) -> str:
    return json.dumps(list(used or []), ensure_ascii=False)


# ── suggestions ────────────────────────────────────────────────────────────

async def supersede_pending(
    db: AsyncSession,
    conversation_id: int,
    *,
    except_id: int | None = None,
) -> int:
    """Закрыть прежние `pending` диалога; `except_id` не трогать."""
    result = await db.execute(
        sql_text(
            "UPDATE support_ai_suggestion SET status = 'superseded' "
            "WHERE conversation_id = :conversation_id AND status = 'pending' "
            "AND (CAST(:except_id AS bigint) IS NULL OR id <> CAST(:except_id AS bigint))"
        ),
        {"conversation_id": conversation_id, "except_id": except_id},
    )
    return int(result.rowcount or 0)


async def create_suggestion(
    db: AsyncSession,
    *,
    conversation_id: int,
    text: str,
    message_id: int | None = None,
    confidence: float | None = None,
    needs_human: bool = False,
    reason: str | None = None,
    model: str | None = None,
    sources: str | None = None,
    status: str = "pending",
    final_text: str | None = None,
    answer_message_id: int | None = None,
    operator_note: str | None = None,
    gate_action: str | None = None,
    gate_reason: str | None = None,
    latency_ms: int | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    used: Iterable[Any] | None = None,
) -> int:
    """Вставить предложку/автоответ. Для `pending` прежний pending закрывается."""
    if status not in _SUGGESTION_STATUSES:
        raise ValueError(f"неизвестный статус предложки: {status}")
    if status == "pending":
        await supersede_pending(db, conversation_id)

    row = (
        await db.execute(
            sql_text(
                """
                INSERT INTO support_ai_suggestion (
                    conversation_id, message_id, text, confidence, needs_human, reason,
                    model, sources, status, final_text, answer_message_id, operator_note,
                    gate_action, gate_reason, latency_ms, tokens_in, tokens_out, used
                ) VALUES (
                    :conversation_id, :message_id, :text, :confidence, :needs_human, :reason,
                    :model, :sources, :status, :final_text, :answer_message_id, :operator_note,
                    :gate_action, :gate_reason, :latency_ms, :tokens_in, :tokens_out,
                    CAST(:used AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "conversation_id": conversation_id,
                "message_id": message_id,
                "text": text,
                "confidence": confidence,
                "needs_human": bool(needs_human),
                "reason": reason,
                "model": model,
                "sources": sources,
                "status": status,
                "final_text": final_text,
                "answer_message_id": answer_message_id,
                "operator_note": operator_note,
                "gate_action": gate_action,
                "gate_reason": gate_reason,
                "latency_ms": latency_ms,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "used": _used_json(used),
            },
        )
    ).fetchone()
    return int(row.id)


async def get_suggestion(db: AsyncSession, suggestion_id: int) -> dict[str, Any] | None:
    row = (
        await db.execute(
            sql_text(f"SELECT {_SUGGESTION_COLUMNS} FROM support_ai_suggestion WHERE id = :id"),
            {"id": suggestion_id},
        )
    ).fetchone()
    return _row_to_dict(row)


async def get_pending_suggestion(
    db: AsyncSession,
    conversation_id: int,
) -> dict[str, Any] | None:
    """Текущая pending-предложка диалога (одна благодаря частичному индексу)."""
    row = (
        await db.execute(
            sql_text(
                f"SELECT {_SUGGESTION_COLUMNS} FROM support_ai_suggestion "
                "WHERE conversation_id = :conversation_id AND status = 'pending' "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"conversation_id": conversation_id},
        )
    ).fetchone()
    return _row_to_dict(row)


async def list_suggestions(
    db: AsyncSession,
    *,
    status: str | None = None,
    conversation_id: int | None = None,
    page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    """Список предложок с фильтрами и пагинацией."""
    page = max(int(page or 1), 1)
    per_page = min(max(int(per_page or 50), 1), _MAX_PAGE)

    where: list[str] = []
    params: dict[str, Any] = {}
    if status and status != "all":
        if status not in _SUGGESTION_STATUSES:
            raise ValueError(f"неизвестный статус предложки: {status}")
        where.append("status = :status")
        params["status"] = status
    if conversation_id is not None:
        where.append("conversation_id = :conversation_id")
        params["conversation_id"] = conversation_id
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""

    total_row = (
        await db.execute(
            sql_text(f"SELECT COUNT(*) AS total FROM support_ai_suggestion{where_sql}"),
            params,
        )
    ).fetchone()
    total = int(total_row.total if total_row is not None else 0)

    offset = (page - 1) * per_page
    rows = (
        await db.execute(
            sql_text(
                f"SELECT {_SUGGESTION_COLUMNS} FROM support_ai_suggestion{where_sql} "
                "ORDER BY created_at DESC, id DESC LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": per_page, "offset": offset},
        )
    ).fetchall()

    return {
        "items": [item for item in (_row_to_dict(row) for row in rows) if item is not None],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def decide_suggestion(
    db: AsyncSession,
    suggestion_id: int,
    *,
    decision: str,
    final_text: str | None = None,
    reason: str | None = None,
) -> dict[str, Any] | None:
    """Решить судьбу предложки: `send`/`edit`/`reject`.

    Отправку сообщения и `answer_message_id` выполняет вызывающий код через
    `outbox` + `mark_suggestion_sent`; здесь фиксируется решение.
    """
    if decision not in ("send", "edit", "reject"):
        raise ValueError(f"неизвестное решение: {decision}")
    status = {"send": "sent", "edit": "edited", "reject": "rejected"}[decision]

    sets = ["status = :status", "decided_at = now()"]
    params: dict[str, Any] = {"id": suggestion_id, "status": status}
    if decision in ("send", "edit") and final_text is not None:
        sets.append("final_text = :final_text")
        params["final_text"] = final_text
    if decision == "reject" and reason is not None:
        sets.append("operator_note = :operator_note")
        params["operator_note"] = reason

    row = (
        await db.execute(
            sql_text(
                f"UPDATE support_ai_suggestion SET {', '.join(sets)} "
                f"WHERE id = :id RETURNING {_SUGGESTION_COLUMNS}"
            ),
            params,
        )
    ).fetchone()
    return _row_to_dict(row)


async def mark_suggestion_sent(
    db: AsyncSession,
    suggestion_id: int,
    *,
    answer_message_id: int,
    final_text: str | None = None,
) -> bool:
    """Пометить отправленной и связать с сообщением в треде."""
    result = await db.execute(
        sql_text(
            "UPDATE support_ai_suggestion SET "
            "status = 'sent', answer_message_id = :answer_message_id, "
            "final_text = COALESCE(:final_text, final_text, text), "
            "decided_at = COALESCE(decided_at, now()) "
            "WHERE id = :id"
        ),
        {
            "id": suggestion_id,
            "answer_message_id": answer_message_id,
            "final_text": final_text,
        },
    )
    return bool(result.rowcount)


async def ai_replies_since(
    db: AsyncSession,
    conversation_id: int,
    since: datetime,
) -> int:
    """Сколько автоответов ИИ ушло в диалог с момента `since` (§2.3)."""
    row = (
        await db.execute(
            sql_text(
                "SELECT COUNT(*) AS total FROM support_ai_suggestion "
                "WHERE conversation_id = :conversation_id AND gate_action = 'auto' "
                "AND status = 'sent' AND created_at >= :since"
            ),
            {"conversation_id": conversation_id, "since": _as_utc(since) or since},
        )
    ).fetchone()
    return int(row.total if row is not None else 0)


async def last_human_reply_at(
    db: AsyncSession,
    conversation_id: int,
) -> datetime | None:
    """Последний ответ оператора (`author='agent'`), не бот и не клиент."""
    row = (
        await db.execute(
            sql_text(
                "SELECT max(created_at) AS last_at FROM support_message "
                "WHERE conversation_id = :conversation_id AND direction = 'out' "
                "AND author = 'agent'"
            ),
            {"conversation_id": conversation_id},
        )
    ).fetchone()
    return _as_utc(row.last_at) if row is not None else None


async def human_hold_active(
    db: AsyncSession,
    conversation_id: int,
    minutes: int,
    *,
    now: datetime | None = None,
) -> bool:
    """Тишина ИИ после ответа оператора (`minutes <= 0` — выключено)."""
    try:
        limit = int(minutes)
    except (TypeError, ValueError):
        limit = 0
    if limit <= 0:
        return False
    last = await last_human_reply_at(db, conversation_id)
    if last is None:
        return False
    moment = _as_utc(now) or _now()
    return (moment - last).total_seconds() < limit * 60


# ── статистика и активность ────────────────────────────────────────────────

async def assistant_stats(db: AsyncSession, *, days: int = 30) -> dict[str, Any]:
    """Агрегаты для `/assistant/stats` (§5.3) + разбивка по дням."""
    days = min(max(int(days or 30), 1), 90)
    moment = _now()
    since = moment - timedelta(days=days)

    row = (
        await db.execute(
            sql_text(
                """
                SELECT
                    COUNT(*)                                                        AS generated,
                    COUNT(*) FILTER (WHERE status = 'sent')                          AS sent,
                    COUNT(*) FILTER (WHERE status = 'edited')                        AS edited,
                    COUNT(*) FILTER (WHERE status = 'rejected')                      AS rejected,
                    COUNT(*) FILTER (WHERE status = 'superseded')                    AS superseded,
                    COUNT(*) FILTER (WHERE status = 'sent' AND gate_action = 'auto') AS auto_sent,
                    COUNT(*) FILTER (WHERE status = 'sent' AND gate_action = 'suggest') AS suggest_sent,
                    COUNT(*) FILTER (WHERE gate_action = 'shadow')                   AS shadow,
                    AVG(confidence)                                                 AS avg_confidence,
                    COALESCE(SUM(tokens_in), 0)                                     AS tokens_in,
                    COALESCE(SUM(tokens_out), 0)                                    AS tokens_out
                FROM support_ai_suggestion
                WHERE created_at >= :since
                """
            ),
            {"since": since},
        )
    ).fetchone()
    data = dict(row._mapping) if row is not None else {}

    generated = int(data.get("generated") or 0)
    sent = int(data.get("sent") or 0)
    avg_confidence = data.get("avg_confidence")
    sent_rate = (sent / generated) if generated else 0.0

    day_rows = (
        await db.execute(
            sql_text(
                """
                SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day,
                       COUNT(*)                                             AS generated,
                       COUNT(*) FILTER (WHERE status = 'sent')              AS sent
                FROM support_ai_suggestion
                WHERE created_at >= :since
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"since": since},
        )
    ).fetchall()
    by_day_map = {
        str(item.day): {
            "date": str(item.day),
            "generated": int(item.generated or 0),
            "sent": int(item.sent or 0),
        }
        for item in day_rows
    }

    by_day: list[dict[str, Any]] = []
    cursor = since.date()
    last_day = moment.date()
    while cursor <= last_day:
        key = cursor.isoformat()
        by_day.append(
            by_day_map.get(key, {"date": key, "generated": 0, "sent": 0})
        )
        cursor += timedelta(days=1)

    return {
        "generated": generated,
        "sent": sent,
        "edited": int(data.get("edited") or 0),
        "rejected": int(data.get("rejected") or 0),
        "superseded": int(data.get("superseded") or 0),
        "auto_sent": int(data.get("auto_sent") or 0),
        "suggest_sent": int(data.get("suggest_sent") or 0),
        "shadow": int(data.get("shadow") or 0),
        "sent_rate": round(float(sent_rate), 4),
        "avg_confidence": round(float(avg_confidence), 4) if avg_confidence is not None else 0.0,
        "tokens_in": int(data.get("tokens_in") or 0),
        "tokens_out": int(data.get("tokens_out") or 0),
        "by_day": by_day,
    }


async def list_activity(
    db: AsyncSession,
    *,
    since: datetime | None = None,
    before_id: int | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Лента активности ИИ (новые сверху), с курсором `before_id`."""
    limit = min(max(int(limit or 100), 1), _MAX_ACTIVITY)
    where: list[str] = []
    params: dict[str, Any] = {"limit": limit}
    if since is not None:
        where.append("created_at >= :since")
        params["since"] = _as_utc(since) or since
    if before_id is not None:
        where.append("id < :before_id")
        params["before_id"] = before_id
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""

    rows = (
        await db.execute(
            sql_text(
                "SELECT id, conversation_id, gate_action AS action, gate_reason, confidence, "
                "model, tokens_in, tokens_out, status, created_at "
                f"FROM support_ai_suggestion{where_sql} ORDER BY id DESC LIMIT :limit"
            ),
            params,
        )
    ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row._mapping)
        item["gate_action"] = item.get("action")
        items.append(item)
    return items


# ── пауза (support_setting['aiPause']) ─────────────────────────────────────

async def get_pause(db: AsyncSession, *, now: datetime | None = None) -> dict[str, Any] | None:
    """Активная пауза или None. Истёкшая пауза неактивна и не пишет в БД."""
    raw = await get_json_setting(db, PAUSE_KEY, None)
    if not isinstance(raw, Mapping):
        return None
    until = _as_utc(raw.get("until"))
    moment = _as_utc(now) or _now()
    if until is None or until <= moment:
        return None
    return {
        "until": _iso(until),
        "by": str(raw.get("by") or ""),
        "at": raw.get("at"),
        "note": str(raw.get("note") or ""),
    }


async def set_pause(
    db: AsyncSession,
    *,
    by: str,
    hours: int | float | None = None,
    until: datetime | str | None = None,
    note: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Поставить паузу на `hours` или до `until` (не дальше +31 дня)."""
    moment = _as_utc(now) or _now()

    if hours is not None:
        try:
            value = float(hours)
        except (TypeError, ValueError):
            raise ValueError("hours должен быть числом") from None
        if value <= 0 or value > PAUSE_MAX_HOURS:
            raise ValueError("пауза должна быть от 1 часа до 31 дня")
        target = moment + timedelta(hours=value)
    elif until is not None:
        target = _as_utc(until)
        if target is None:
            raise ValueError("until должен быть ISO-датой")
    else:
        raise ValueError("укажите hours или until")

    if target <= moment:
        raise ValueError("пауза должна заканчиваться в будущем")
    if target > moment + timedelta(days=PAUSE_MAX_DAYS):
        raise ValueError("пауза не может длиться дольше 31 дня")

    payload = {
        "until": _iso(target),
        "by": str(by or ""),
        "at": _iso(moment),
        "note": str(note or ""),
    }
    await set_json_setting(db, PAUSE_KEY, payload)
    return payload


async def clear_pause(db: AsyncSession) -> None:
    """Снять паузу (значение JSON null)."""
    await set_json_setting(db, PAUSE_KEY, None)


# ── черновик оператора (support_operator_draft) ───────────────────────────

async def get_operator_draft(
    db: AsyncSession,
    actor_id: int,
    conversation_id: int,
) -> dict[str, Any] | None:
    row = (
        await db.execute(
            sql_text(
                f"SELECT {_DRAFT_COLUMNS} FROM support_operator_draft "
                "WHERE actor_id = :actor_id AND conversation_id = :conversation_id"
            ),
            {"actor_id": actor_id, "conversation_id": conversation_id},
        )
    ).fetchone()
    return _row_to_dict(row)


async def put_operator_draft(
    db: AsyncSession,
    actor_id: int,
    conversation_id: int,
    *,
    text: str = "",
    mode: str = "reply",
    quote: str | None = None,
    from_suggestion_id: int | None = None,
) -> dict[str, Any]:
    """Upsert серверного черновика (переживает перезагрузку вкладки)."""
    if mode not in ("reply", "note"):
        raise ValueError(f"неизвестный режим черновика: {mode}")
    row = (
        await db.execute(
            sql_text(
                """
                INSERT INTO support_operator_draft (
                    actor_id, conversation_id, text, mode, quote, from_suggestion_id, updated_at
                ) VALUES (
                    :actor_id, :conversation_id, :text, :mode, :quote, :from_suggestion_id, now()
                )
                ON CONFLICT (actor_id, conversation_id) DO UPDATE SET
                    text = EXCLUDED.text,
                    mode = EXCLUDED.mode,
                    quote = EXCLUDED.quote,
                    from_suggestion_id = EXCLUDED.from_suggestion_id,
                    updated_at = now()
                RETURNING actor_id, conversation_id, text, mode, quote,
                          from_suggestion_id, updated_at
                """
            ),
            {
                "actor_id": actor_id,
                "conversation_id": conversation_id,
                "text": text or "",
                "mode": mode,
                "quote": quote,
                "from_suggestion_id": from_suggestion_id,
            },
        )
    ).fetchone()
    return _row_to_dict(row)


async def delete_operator_draft(
    db: AsyncSession,
    actor_id: int,
    conversation_id: int,
) -> bool:
    result = await db.execute(
        sql_text(
            "DELETE FROM support_operator_draft "
            "WHERE actor_id = :actor_id AND conversation_id = :conversation_id"
        ),
        {"actor_id": actor_id, "conversation_id": conversation_id},
    )
    return bool(result.rowcount)
