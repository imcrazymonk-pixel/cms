"""Конвейер генерации ИИ-ответа (§4.1) и runtime-снимок настроек.

`AiRuntime` — общий объект на `SupportService.ai`: иммутабельный `AiConfig`,
ленивый провайдер и точки инъекции поиска по КБ/примерам. `AiResponder`
перечитывает диалог, собирает контекст, зовёт провайдера, прогоняет замки и
ворота и записывает результат в `support_ai_suggestion`.

Границы ответственности:

* никакого `bot.api` — единственный выход наружу `Outbox.send`;
* ошибки провайдера не ломают диалог: лог без ключа, запись не создаётся;
* `auto` перепроверяется непосредственно перед отправкой (ответ оператора,
  пауза, смена режима за время генерации).

Модуль не читает env/БД сам: всё состояние приходит через `service` и
инъекции, поэтому тестируется без сети и БД.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Iterable, Protocol, Sequence

from web.backend.core.support.ai.chunks import select_chunks
from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.gate import decide as gate_decide
from web.backend.core.support.ai.gate import tone_of
from web.backend.core.support.ai.links import CustomerLink, expand_links
from web.backend.core.support.ai.outbound import check as outbound_check
from web.backend.core.support.ai.prompt import build_prompt
from web.backend.core.support.ai.provider import AiCompletion, AiProvider
from web.backend.core.support.ai.scrub import scrub
from web.backend.core.support.events import EventKind

logger = logging.getLogger(__name__)

CONTEXT_MESSAGES = 20
KB_HITS_LIMIT = 8
KB_QUERY_MESSAGES = 3
EXAMPLES_LIMIT = 3
USED_CHUNK_MAX = 500
AUTO_WINDOW = timedelta(hours=1)
OUTBOUND_BLOCKED = "outbound_blocked"

_UTC = timezone.utc


class KbSearch(Protocol):
    """Поиск по базе знаний: `await kb_search(query, limit=8)` → статьи."""

    def __call__(self, query: str, *, limit: int = KB_HITS_LIMIT) -> Awaitable[Sequence[Any]]:
        ...


class ExamplesSearch(Protocol):
    """Похожие пары операторов: `await examples(query, limit=3)`."""

    def __call__(self, query: str, *, limit: int = EXAMPLES_LIMIT) -> Awaitable[Sequence[Any]]:
        ...


async def _empty_search(query: str, *, limit: int = 0) -> list[Any]:
    """Пока Б2 не готов: пустая выдача, без ошибок и I/O."""
    return []


@dataclass
class AiRuntime:
    """Живой снимок ИИ: конфиг меняется на месте при перезагрузке настроек."""

    config: AiConfig
    provider: AiProvider | None = None
    kb_search: KbSearch | None = None
    examples: ExamplesSearch | None = None
    links: tuple[CustomerLink, ...] = ()

    def __post_init__(self) -> None:
        if self.provider is None:
            # Ленивый клиент: httpx-соединение откроется только на первый запрос.
            self.provider = AiProvider()

    @classmethod
    def from_settings(
        cls,
        settings: Any,
        *,
        provider: AiProvider | None = None,
        kb_search: KbSearch | None = None,
        examples: ExamplesSearch | None = None,
        links: Iterable[CustomerLink] | None = None,
    ) -> "AiRuntime":
        return cls(
            config=AiConfig.from_settings(settings),
            provider=provider,
            kb_search=kb_search,
            examples=examples,
            links=tuple(links or ()),
        )

    def reload(self, settings: Any) -> None:
        """Подхватить новые настройки в тот же объект (hot reload без рестарта)."""
        self.config = AiConfig.from_settings(settings)
        reset = getattr(self.provider, "reset", None)
        if callable(reset):
            reset()


def _get(source: Any, name: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_utc(value: Any) -> datetime | None:
    """Привести datetime/ISO к UTC-aware; иначе None."""
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


def _now() -> datetime:
    return datetime.now(_UTC)


def _normalize_used(raw: Any, citations: Sequence[Any]) -> list[dict[str, Any]]:
    """`used[]` модели → `[{doc_id,title,chunk}]`; неизвестные номера отбрасываем."""
    if raw is None:
        return []
    items = list(raw) if isinstance(raw, (list, tuple, set)) else [raw]
    by_index = {int(_get(citation, "index", 0) or 0): citation for citation in citations}

    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, str, str]] = set()
    for item in items:
        doc_id: Any = None
        title = ""
        chunk = ""

        if isinstance(item, dict):
            doc_id = item.get("doc_id")
            title = _text(item.get("title"))
            chunk = _text(item.get("chunk") or item.get("body"))
        else:
            try:
                index = int(item)
            except (TypeError, ValueError):
                continue
            citation = by_index.get(index)
            if citation is None:
                continue
            doc_id = _get(citation, "doc_id", None)
            title = _text(_get(citation, "title", ""))
            chunk = _text(_get(citation, "body", ""))

        if not title and not doc_id:
            continue
        try:
            doc_id = int(doc_id) if doc_id is not None else None
        except (TypeError, ValueError):
            doc_id = None
        chunk = chunk[:USED_CHUNK_MAX]

        key = (doc_id, title, chunk)
        if key in seen:
            continue
        seen.add(key)
        result.append({"doc_id": doc_id, "title": title, "chunk": chunk})
    return result


class AiResponder:
    """Один проход генерации для входящего сообщения диалога."""

    def __init__(
        self,
        service: Any,
        *,
        runtime: AiRuntime | None = None,
        kb_search: KbSearch | None = None,
        examples: ExamplesSearch | None = None,
        customer_card_builder: Callable[..., Awaitable[Any]] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.service = service
        self.runtime = runtime if runtime is not None else getattr(service, "ai", None)
        self.store = getattr(service, "store", None)
        self.outbox = getattr(service, "outbox", None)
        self.event_bus = getattr(service, "event_bus", None)

        runtime_kb = getattr(self.runtime, "kb_search", None) if self.runtime else None
        runtime_examples = getattr(self.runtime, "examples", None) if self.runtime else None
        self.kb_search: KbSearch | None = kb_search if kb_search is not None else runtime_kb
        self.examples: ExamplesSearch | None = (
            examples if examples is not None else runtime_examples
        )
        if customer_card_builder is None:
            try:
                from web.backend.core.support.integrations.bedolaga_customer import (
                    build_customer_card,
                )

                customer_card_builder = build_customer_card
            except Exception as e:  # noqa: BLE001 — карточка не обязательна для ответа
                logger.debug("Customer card builder unavailable: %s", type(e).__name__)
                customer_card_builder = None
        self._card_builder = customer_card_builder
        self._clock = clock or _now

    # ── публичный вход ───────────────────────────────────────────────
    async def handle_inbound(self, conversation_id: int) -> dict[str, Any] | None:
        """Сгенерировать ответ на последнее входящее; None — генерации не было."""
        runtime = self.runtime
        config = getattr(runtime, "config", None)
        if config is None or config.effective_mode == "off":
            return None

        cid = int(conversation_id)
        conversation = await self._store_call("get_conversation", None, cid)
        if not isinstance(conversation, dict) or not conversation:
            return None

        channel = _text(conversation.get("channel"))
        if not self._has_sender(channel):
            return None

        messages = await self._store_call("list_messages", [], cid, limit=CONTEXT_MESSAGES)
        if not messages:
            return None
        latest = messages[0]
        if _text(_get(latest, "direction")).lower() != "in":
            return None

        started_at = self._clock()
        client_text = scrub(_text(_get(latest, "text")))
        query = self._kb_query(messages)

        kb_hits = await self._search(self.kb_search, query, KB_HITS_LIMIT)
        try:
            kb_chunks = select_chunks(kb_hits, query, budget=max(int(config.kb_budget_chars), 0))
        except Exception as e:  # noqa: BLE001 — без КБ ответ всё равно возможен
            logger.debug("KB chunk selection failed: %s", type(e).__name__)
            kb_chunks = []

        examples = await self._search(self.examples, query, EXAMPLES_LIMIT)
        card = await self._customer_card(conversation)

        try:
            bundle = build_prompt(
                config=config,
                kb_chunks=kb_chunks,
                examples=examples,
                messages=messages,
                customer_card=card,
                client_text=_text(_get(latest, "text")),
                links=getattr(runtime, "links", ()) or (),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("AI prompt build failed for conversation %s: %s", cid, type(e).__name__)
            return None

        provider = getattr(runtime, "provider", None)
        try:
            completion = await provider.complete_json(bundle.messages, config)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — диалог не ломается
            # Никогда не логируем ключ: только тип и безопасное сообщение.
            logger.warning(
                "AI generation failed for conversation %s: %s",
                cid,
                _safe_error(e),
            )
            return None

        return await self._finalize(
            conversation=conversation,
            latest=latest,
            client_text=client_text,
            completion=completion,
            citations=bundle.citations,
            config=config,
            started_at=started_at,
            profile_available=bool(card),
        )

    # ── пост-обработка и запись ──────────────────────────────────────
    async def _finalize(
        self,
        *,
        conversation: dict[str, Any],
        latest: Any,
        client_text: str,
        completion: AiCompletion,
        citations: Sequence[Any],
        config: AiConfig,
        started_at: datetime,
        profile_available: bool = False,
    ) -> dict[str, Any] | None:
        cid = int(conversation["id"])
        runtime = self.runtime
        draft = dict(completion.draft or {})

        raw_reply = _text(draft.get("reply"))
        links = getattr(runtime, "links", ()) or ()
        expanded = expand_links(raw_reply, links)
        reply = _text(expanded.text)
        used = _normalize_used(draft.get("used"), citations)

        draft["used"] = used
        draft["reply"] = reply

        verdict = outbound_check(reply, config.allowed_domains)
        blocked = not bool(verdict.get("ok", True))

        # Состояние диалога читаем после генерации: ответ оператора мог прийти,
        # пока модель думала, и это должно победить `auto`.
        pause = await self._store_call("get_pause", None)
        human_hold = bool(
            await self._store_call(
                "human_hold_active", False, cid, int(config.human_hold_minutes)
            )
        )
        last_human = await self._store_call("last_human_reply_at", None, cid)
        recent_auto = int(
            await self._store_call("ai_replies_since", 0, cid, self._clock() - AUTO_WINDOW) or 0
        )
        window_open = self._window_open(conversation)

        gate_result = gate_decide(
            conversation=conversation,
            client_text=client_text,
            draft=draft,
            kb_hits=len(citations),
            runtime=config,
            pause=pause,
            recent_auto_count=recent_auto,
            tone=tone_of(client_text),
            human_hold=human_hold,
            window_open=window_open,
            profile_available=profile_available,
        )

        action = str(gate_result.get("action") or "skip")
        reason = str(gate_result.get("reason") or "")
        level = str(gate_result.get("level") or "")

        if blocked:
            # Замок важнее любого «auto»; в тени остаёмся в тени, но причину фиксируем.
            if action == "auto":
                action = "suggest"
            reason = OUTBOUND_BLOCKED

        if action == "skip":
            return None

        if action == "auto" and not await self._still_auto_async(
            conversation, config, started_at
        ):
            action = "suggest"
            reason = "состояние диалога изменилось во время генерации"

        return await self._persist(
            conversation=conversation,
            latest=latest,
            completion=completion,
            reply=reply,
            used=used,
            draft=draft,
            action=action,
            reason=reason,
            level=level,
        )

    async def _persist(
        self,
        *,
        conversation: dict[str, Any],
        latest: Any,
        completion: AiCompletion,
        reply: str,
        used: list[dict[str, Any]],
        draft: dict[str, Any],
        action: str,
        reason: str,
        level: str,
    ) -> dict[str, Any] | None:
        cid = int(conversation["id"])
        message_id = _get(latest, "id", None)
        try:
            message_id = int(message_id) if message_id is not None else None
        except (TypeError, ValueError):
            message_id = None

        # Перед новой предложкой закрываем прежние pending (§2.3).
        await self._store_call("supersede_pending", 0, cid)

        payload: dict[str, Any] = {
            "conversation_id": cid,
            "text": reply,
            "message_id": message_id,
            "confidence": draft.get("confidence"),
            "needs_human": bool(draft.get("needs_human")),
            "reason": _text(draft.get("reason")) or reason,
            "model": getattr(completion, "model", None),
            "operator_note": _text(draft.get("operator_note")) or None,
            "gate_action": action,
            "gate_reason": reason,
            "latency_ms": getattr(completion, "latency_ms", None),
            "tokens_in": getattr(completion, "tokens_in", None),
            "tokens_out": getattr(completion, "tokens_out", None),
            "used": used,
        }

        if action == "auto":
            try:
                external_id = await self.outbox.send(conversation, reply)
                answer_id = await self.store.record_outbound(
                    conversation_id=cid,
                    text_value=reply,
                    author="bot",
                    external_msg_id=external_id,
                )
                suggestion_id = await self.store.create_suggestion(
                    **payload,
                    status="sent",
                    final_text=reply,
                    answer_message_id=answer_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 — автоотправка не должна терять ответ
                logger.warning(
                    "AI auto-send failed for conversation %s: %s", cid, _safe_error(e)
                )
                action = "suggest"
                payload["gate_action"] = action
                payload["gate_reason"] = "ошибка автоотправки"
                return await self._create_pending(payload)

            self._publish(cid, suggestion_id, "sent")
            return {
                "id": suggestion_id,
                "status": "sent",
                "action": action,
                "level": level,
                "answer_message_id": answer_id,
            }

        return await self._create_pending(payload)

    async def _create_pending(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        try:
            suggestion_id = await self.store.create_suggestion(**payload, status="pending")
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "AI suggestion persist failed for conversation %s: %s",
                payload.get("conversation_id"),
                _safe_error(e),
            )
            return None
        self._publish(int(payload["conversation_id"]), suggestion_id, "pending")
        return {
            "id": suggestion_id,
            "status": "pending",
            "action": payload.get("gate_action"),
            "level": None,
        }

    def _publish(self, conversation_id: int, suggestion_id: int, status: str) -> None:
        bus = self.event_bus
        if bus is None:
            return
        try:
            bus.publish(
                EventKind.AI_SUGGESTION,
                {"suggestion_id": suggestion_id, "status": status},
                conversation_id=conversation_id,
            )
        except Exception as e:  # noqa: BLE001 — событие не должно валить запись
            logger.debug("AI suggestion event failed: %s", type(e).__name__)

    # ── проверки и контекст ──────────────────────────────────────────
    def _has_sender(self, channel: str) -> bool:
        outbox = self.outbox
        if outbox is None:
            return False
        try:
            return bool(outbox.has_sender(channel))
        except Exception as e:  # noqa: BLE001
            logger.debug("Outbox sender check failed: %s", type(e).__name__)
            return False

    def _window_open(self, conversation: dict[str, Any]) -> bool:
        outbox = self.outbox
        if outbox is None:
            return False
        try:
            outbox.check_window(conversation)
            return True
        except Exception as e:  # noqa: BLE001 — закрытое окно = skip в гейте
            logger.debug("Reply window check: %s", type(e).__name__)
            return False

    async def _still_auto_async(
        self,
        conversation: dict[str, Any],
        config: AiConfig,
        started_at: datetime,
    ) -> bool:
        current = getattr(self.runtime, "config", config)
        if getattr(current, "effective_mode", "off") != "auto":
            return False
        pause = await self._store_call("get_pause", None)
        if pause:
            return False
        latest_human = await self._store_call("last_human_reply_at", None, int(conversation["id"]))
        moment = _as_utc(latest_human)
        if moment is not None and moment >= started_at:
            return False
        return True

    def _kb_query(self, messages: Sequence[Any]) -> str:
        inbound = [
            scrub(_text(_get(message, "text")))
            for message in messages
            if _text(_get(message, "direction")).lower() == "in"
        ][:KB_QUERY_MESSAGES]
        return " ".join(reversed([item for item in inbound if item]))

    async def _search(
        self,
        search: KbSearch | ExamplesSearch | None,
        query: str,
        limit: int,
    ) -> list[Any]:
        if search is None or not query:
            return []
        try:
            result = search(query, limit=limit)
            if inspect.isawaitable(result):
                result = await result
            return list(result or [])
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — поиск не обязателен для ответа
            logger.debug("AI context search failed: %s", type(e).__name__)
            return []

    async def _customer_card(self, conversation: dict[str, Any]) -> Any:
        builder = self._card_builder
        if builder is None:
            return None
        try:
            result = builder(self.service, conversation)
            if inspect.isawaitable(result):
                result = await result
            return result
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.debug("Customer card build failed: %s", type(e).__name__)
            return None

    async def _store_call(self, name: str, default: Any, *args: Any, **kwargs: Any) -> Any:
        store = self.store
        fn = getattr(store, name, None) if store is not None else None
        if fn is None:
            return default
        try:
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return default if result is None and default is not None else result
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.debug("Store call %s failed: %s", name, type(e).__name__)
            return default


def _safe_error(error: BaseException) -> str:
    """Безопасное описание ошибки: код провайдера/тип, без ключа и тела ответа."""
    code = getattr(error, "code", None)
    status = getattr(error, "status", None)
    if code:
        return f"{code}" + (f" ({status})" if status is not None else "")
    return type(error).__name__
