"""Debounce-воркер ИИ: одна генерация на диалог, не больше двух параллельно.

Подписывается на `EventBus(MESSAGE_CREATED)` и на каждое событие пересоздаёт
задачу диалога: новая пачка сообщений отменяет предыдущее ожидание и ждёт
`ai_debounce_seconds`. Провайдерские вызовы ограничены `asyncio.Semaphore(2)`,
чтобы всплеск входящих не превращался в 429.

Жизненный цикл: задача `run_loop()` создаётся только из
`start_support_workers`; `stop()` (и отмена `run_loop`) гасит все debounce-задачи.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from web.backend.core.support.ai.responder import AiResponder
from web.backend.core.support.events import EventKind, SupportEvent

logger = logging.getLogger(__name__)

PROVIDER_CONCURRENCY = 2
DEFAULT_DEBOUNCE_SECONDS = 8.0


class AiWorker:
    """In-process debounce + ограничение параллелизма для генераций."""

    def __init__(
        self,
        service: Any,
        *,
        responder: AiResponder | None = None,
        debounce_seconds: float | None = None,
        provider_semaphore: asyncio.Semaphore | None = None,
    ) -> None:
        self.service = service
        self.responder = responder if responder is not None else AiResponder(service)
        self._debounce_override = debounce_seconds
        self._semaphore = provider_semaphore or asyncio.Semaphore(PROVIDER_CONCURRENCY)
        self._tasks: dict[int, asyncio.Task] = {}
        self._queue: asyncio.Queue | None = None
        self._closed = False

    # ── жизненный цикл ───────────────────────────────────────────────
    async def run_loop(self) -> None:
        """Слушать шину; на отмене — погасить все ожидающие генерации."""
        queue = self.service.event_bus.subscribe(EventKind.MESSAGE_CREATED)
        self._queue = queue
        try:
            while True:
                event = await queue.get()
                self.handle_event(event)
        except asyncio.CancelledError:
            raise
        finally:
            self._closed = True
            self.service.event_bus.unsubscribe(EventKind.MESSAGE_CREATED, queue)
            self._queue = None
            await self.stop()

    async def stop(self) -> None:
        """Отменить и дождаться всех debounce-задач (идемпотентно)."""
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def drain(self) -> None:
        """Дождаться текущих задач без отмены (для тестов и аккуратной проверки)."""
        tasks = list(self._tasks.values())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def pending_count(self) -> int:
        return len(self._tasks)

    # ── планирование ─────────────────────────────────────────────────
    def handle_event(self, event: SupportEvent) -> None:
        """Событие шины → debounce-задача диалога."""
        conversation_id = event.conversation_id or (event.payload or {}).get("conversation_id")
        self.schedule(conversation_id)

    def schedule(self, conversation_id: Any) -> None:
        """Пересоздать задачу диалога: новая пачка отменяет предыдущую."""
        if self._closed:
            return
        try:
            cid = int(conversation_id)
        except (TypeError, ValueError):
            return

        previous = self._tasks.pop(cid, None)
        if previous is not None and not previous.done():
            previous.cancel()

        task = asyncio.create_task(self._run(cid), name=f"support-ai-{cid}")
        self._tasks[cid] = task
        task.add_done_callback(lambda done, cid=cid: self._forget(cid, done))

    def _forget(self, conversation_id: int, task: asyncio.Task) -> None:
        if self._tasks.get(conversation_id) is task:
            self._tasks.pop(conversation_id, None)

    async def _run(self, conversation_id: int) -> None:
        try:
            await asyncio.sleep(self._debounce_seconds())
        except asyncio.CancelledError:
            raise

        async with self._semaphore:
            try:
                await self.responder.handle_inbound(conversation_id)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 — воркер живёт дальше
                logger.warning(
                    "AI worker generation failed for conversation %s: %s",
                    conversation_id,
                    type(e).__name__,
                )

    def _debounce_seconds(self) -> float:
        if self._debounce_override is not None:
            return max(0.0, float(self._debounce_override))
        runtime = getattr(self.service, "ai", None)
        config = getattr(runtime, "config", None)
        try:
            value = float(getattr(config, "debounce_seconds", DEFAULT_DEBOUNCE_SECONDS))
        except (TypeError, ValueError):
            value = DEFAULT_DEBOUNCE_SECONDS
        return max(0.0, value)
