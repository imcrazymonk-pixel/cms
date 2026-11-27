"""Bedolaga tickets channel — poller + outbox sender (phase 1).

Projects the Bedolaga Bot API ticket stream into support_* tables:

  * polling of open/answered/pending statuses, 50 per page;
  * inbound dedupe — ON CONFLICT DO NOTHING under the partial unique index;
  * cold start — before baseline (`bedolaga:last_poll`) everything is imported
    as history (is_backfill=True): unread never grows, no live events;
    after baseline the freshest inbound of a first-seen ticket is live;
  * status sync open/answered/pending ↔ our statuses;
  * repair — our active tickets missing from the active poll are re-checked
    individually (a ticket can be closed on the Bedolaga side);
  * never dies: errors are logged and published as POLLER_STATUS.

The sender talks to `bedolaga_client.reply_ticket` with zero retries — the
endpoint is not idempotent, so a 5xx is NOT re-sent automatically.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Mapping

from httpx import HTTPStatusError

from web.backend.core.bedolaga_client import bedolaga_client
from web.backend.core.support.events import EventBus, EventKind

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("open", "answered", "pending")
PAGE_LIMIT = 50
PAGE_MAX = 50
STATE_LAST_POLL = "bedolaga:last_poll"

# Bedolaga status → our status (import direction)
BEDOLAGA_TO_LOCAL: dict[str, str] = {
    "open": "open",
    "answered": "pending",
    "pending": "open",  # по ТЗ: pending-тикеты попадают в активную очередь
    "closed": "resolved",
}
# Our status → Bedolaga status (operator push direction)
LOCAL_TO_BEDOLAGA: dict[str, str] = {
    "open": "open",
    "pending": "answered",
    "resolved": "closed",
    "closed": "closed",
}


def local_status_for_ticket(status: str | None) -> str | None:
    """Map a Bedolaga ticket status to our conversation status."""
    if not status:
        return None
    return BEDOLAGA_TO_LOCAL.get(str(status).strip().lower())


def bedolaga_status_for_local(status: str | None) -> str | None:
    """Map our conversation status to a Bedolaga ticket status."""
    if not status:
        return None
    return LOCAL_TO_BEDOLAGA.get(str(status).strip().lower())


def ticket_id_of(conversation: Mapping[str, Any]) -> int:
    """Ticket id from a conversation's external_id."""
    try:
        ticket_id = int(str(conversation.get("external_id") or "").strip())
    except (TypeError, ValueError):
        ticket_id = 0
    if ticket_id <= 0:
        raise ValueError("У диалога нет корректного ID тикета Bedolaga")
    return ticket_id


def parse_message_time(source: Mapping[str, Any]) -> datetime:
    """Message time: created_at/sent_at as ISO or epoch (s/ms). Fallback: now."""
    for key in ("created_at", "createdAt", "date", "timestamp", "sent_at"):
        value = source.get(key)
        if isinstance(value, (int, float)):
            ts = value / 1000.0 if value > 1e12 else value
            try:
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                continue
        if isinstance(value, str) and value.strip():
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return datetime.now(timezone.utc)


def _collection_items(body: Any) -> tuple[list[dict], int]:
    """Normalize Bedolaga list contracts: array or {items/tickets/data, total}."""
    if isinstance(body, list):
        return [b for b in body if isinstance(b, dict)], len(body)
    if isinstance(body, dict):
        for key in ("items", "tickets", "data"):
            items = body.get(key)
            if isinstance(items, list):
                clean = [i for i in items if isinstance(i, dict)]
                return clean, int(body.get("total") or len(clean))
    return [], 0


def _extract_reply_external_id(body: Any) -> str | None:
    """Message id from the /reply response (message.id or top-level id)."""
    if not isinstance(body, dict):
        return None
    message = body.get("message")
    if isinstance(message, dict) and message.get("id") is not None:
        return str(message["id"])
    if body.get("id") is not None:
        return str(body["id"])
    return None


class BedolagaPoller:
    """Fetches Bedolaga tickets and projects them into the support store."""

    channel = "bedolaga"

    def __init__(
        self,
        *,
        store,
        event_bus: EventBus,
        client=None,
        interval: int = 60,
        enabled: bool = True,
    ):
        self.store = store
        self.event_bus = event_bus
        self.client = client if client is not None else bedolaga_client
        self.interval = max(5, int(interval))
        self.enabled = bool(enabled)
        self._running = False
        self.status: dict[str, Any] = {
            "enabled": self.enabled,
            "running": False,
            "last_poll": None,
            "last_error": None,
            "ingested": 0,
        }

    # ── Outbox sender ────────────────────────────────────────────
    async def send_text(self, conversation: Mapping[str, Any], text: str) -> str | None:
        """Send a reply. Zero retries on purpose: /tickets/{id}/reply is not idempotent."""
        ticket_id = ticket_id_of(conversation)
        # HTTPStatusError (4xx/5xx) propagates to the caller — no auto retry.
        body = await self.client.reply_ticket(ticket_id, str(text))
        return _extract_reply_external_id(body)

    # ── Poller loop ──────────────────────────────────────────────
    async def run_loop(self) -> None:
        """Background loop — launched from workers.py (auto_sync pattern)."""
        logger.info("Bedolaga poller started (interval=%ss, enabled=%s)", self.interval, self.enabled)
        await asyncio.sleep(5)  # не мешаем стартовому прогреву
        while True:
            try:
                await self.tick()
            except Exception as e:  # noqa: BLE001 — никогда не убиваем цикл
                logger.error("Bedolaga poller loop error: %s", e)
                self._report_error(e)
            await asyncio.sleep(self.interval)

    async def tick(self) -> int:
        """One polling pass; returns the number of newly imported messages."""
        if self._running:
            return 0
        self._running = True
        self.status["running"] = True
        ingested = 0
        try:
            baseline_ready = bool(await self.store.get_poll_state(STATE_LAST_POLL))
            tickets = await self._active_tickets()
            checked_ids: set[int] = set()
            for summary in tickets:
                ticket_id = 0
                try:
                    ticket_id = int(str(summary.get("id") or 0))
                except (TypeError, ValueError):
                    continue
                if ticket_id <= 0:
                    continue
                checked_ids.add(ticket_id)
                try:
                    ingested += await self._ingest_ticket(summary, force_backfill=False, baseline_ready=baseline_ready)
                except Exception as e:  # noqa: BLE001 — один тикет не валит проход
                    logger.warning("Bedolaga ticket %s: %s", ticket_id, e)
            await self._sync_missing(checked_ids)

            now_iso = datetime.now(timezone.utc).isoformat()
            await self.store.set_poll_state(STATE_LAST_POLL, now_iso)
            self.status.update({"last_poll": now_iso, "last_error": None, "ingested": ingested})
            self.event_bus.publish(
                EventKind.POLLER_STATUS,
                {"channel": self.channel, "last_poll": now_iso, "last_error": None, "ingested": ingested},
            )
        except Exception as e:  # noqa: BLE001 — проход не убивает цикл
            logger.error("Bedolaga poller pass failed: %s", e)
            self._report_error(e)
        finally:
            self._running = False
            self.status["running"] = False
        return ingested

    # ── Fetching ─────────────────────────────────────────────────
    async def _active_tickets(self) -> list[dict]:
        """All live tickets: every active status paged until exhausted."""
        seen: dict[int, dict] = {}
        for status in ACTIVE_STATUSES:
            for page in range(PAGE_MAX):
                data = await self.client.list_tickets(limit=PAGE_LIMIT, offset=page * PAGE_LIMIT, status=status)
                items, total = _collection_items(data)
                for item in items:
                    try:
                        seen[int(str(item.get("id") or 0))] = item
                    except (TypeError, ValueError):
                        continue
                if not items or page * PAGE_LIMIT + len(items) >= total:
                    break
                if page == PAGE_MAX - 1:
                    logger.warning("Bedolaga: статус %s содержит более %s тикетов — хвост не обработан", status, PAGE_MAX * PAGE_LIMIT)
        return list(seen.values())

    # ── Ingestion ────────────────────────────────────────────────
    async def _ingest_ticket(self, summary: dict, *, force_backfill: bool, baseline_ready: bool) -> int:
        ticket = summary
        if not ticket.get("messages"):
            ticket = await self.client.get_ticket(int(str(summary.get("id") or 0)))
        if not isinstance(ticket, dict):
            return 0
        ticket_id = 0
        try:
            ticket_id = int(str(summary.get("id") or 0))
        except (TypeError, ValueError):
            return 0
        external_id = str(ticket_id)
        subject = str(ticket.get("title") or f"Тикет #{ticket_id}")
        priority = ticket.get("priority")

        # Завладеваем диалогом раньше сообщений (могут быть только исходящие)
        existing = await self.store.get_conversation_by_external(external_id=external_id, channel=self.channel)
        first_seen = existing is None
        if existing is not None:
            conv_id = int(existing["id"])
        else:
            conv_id, _ = await self.store.upsert_conversation(
                channel=self.channel, external_id=external_id, subject=subject, priority=priority,
            )

        # Самое свежее входящее на холодном старте (после baseline) — live
        latest_live_id: str | None = None
        messages = [m for m in (ticket.get("messages") or []) if isinstance(m, dict)]
        if first_seen and baseline_ready and not force_backfill:
            inbound = [m for m in messages if not m.get("is_from_admin")]
            if inbound:
                latest = max(inbound, key=_message_sort_key)
                raw_id = latest.get("id")
                latest_live_id = str(raw_id) if raw_id is not None else None

        consumed = 0
        for message in messages:
            message_id = message.get("id")
            if message_id is None:
                continue
            message_id = str(message_id)
            is_admin = bool(message.get("is_from_admin"))
            backfill = force_backfill or (first_seen and (not baseline_ready or message_id != latest_live_id))
            created_at = parse_message_time(message)
            text = message.get("message_text") or ""

            if is_admin:
                if await self.store.message_exists(
                    conversation_id=conv_id, direction="out", external_msg_id=message_id
                ):
                    continue
                await self.store.record_outbound(
                    conversation_id=conv_id, text_value=str(text), author="agent",
                    external_msg_id=message_id, media_type=message.get("media_type"),
                    media_file_id=_file_id(message), created_at=created_at,
                )
                consumed += 1
                continue

            result = await self.store.record_inbound(
                channel=self.channel, external_id=external_id, text=str(text),
                external_msg_id=message_id, created_at=created_at, is_backfill=backfill,
                media_type=message.get("media_type"), media_file_id=_file_id(message),
                subject=subject, priority=priority,
            )
            if not result["message_created"]:
                continue
            consumed += 1
            if not backfill:
                self._emit_message_event(result["conversation_id"], result["message_id"], text)

        local_status = local_status_for_ticket(ticket.get("status"))
        if local_status:
            await self.store.set_status(conv_id, local_status)
        if priority:
            await self.store.set_priority(conv_id, str(priority))
        return consumed

    async def _sync_missing(self, checked_ids: set[int]) -> None:
        """Наши активные тикеты, пропавшие из живого списка, — точечная сверка.

        Так закрытый в Bedolaga тикет сразу становится resolved, а повторно
        открытый снова попадает в обычный опрос.
        """
        known = await self.store.list_active_conversations(channel=self.channel)
        for conv in known:
            try:
                ticket_id = int(str(conv.get("external_id") or "").strip())
            except (TypeError, ValueError):
                continue
            if ticket_id <= 0 or ticket_id in checked_ids:
                continue
            try:
                ticket = await self.client.get_ticket(ticket_id)
                checked_ids.add(ticket_id)
                await self._ingest_ticket(ticket, force_backfill=True, baseline_ready=True)
            except HTTPStatusError as e:
                if e.response.status_code == 404:
                    await self.store.set_status(conv["id"], "resolved")
                logger.warning("Bedolaga sync-missing ticket %s: %s", ticket_id, e)
            except Exception as e:  # noqa: BLE001
                logger.warning("Bedolaga sync-missing ticket %s: %s", ticket_id, e)

    # ── Events & errors ──────────────────────────────────────────
    def _emit_message_event(self, conversation_id: int | None, message_id: int | None, text: str) -> None:
        event = {"message_id": message_id, "direction": "in", "text": text}
        self.event_bus.publish(EventKind.MESSAGE_CREATED, event, conversation_id=conversation_id)
        self.event_bus.publish(EventKind.CONVERSATION_CHANGED, {"status": "open"}, conversation_id=conversation_id)

    def _report_error(self, error: Exception) -> None:
        message = f"{type(error).__name__}: {error}"
        self.status["last_error"] = message
        self.event_bus.publish(
            EventKind.POLLER_STATUS,
            {"channel": self.channel, "last_poll": self.status.get("last_poll"), "last_error": message, "ingested": 0},
        )


def _message_sort_key(message: dict) -> tuple[datetime, int]:
    return (parse_message_time(message), int(str(message.get("id") or 0) or 0))


def _file_id(message: dict) -> str | None:
    value = message.get("media_file_id")
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (int, float)):
        return str(value)
    return None
