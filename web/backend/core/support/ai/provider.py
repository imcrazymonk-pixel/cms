"""OpenAI-совместимый клиент генерации (httpx, только по требованию).

Клиент не создаётся, пока ИИ выключен (`effective_mode='off'`) или не задан
ключ: на старте поддержки никаких соединений наружу. Первый запрос создаёт
`httpx.AsyncClient` с `trust_env=False` (никаких наследованных прокси), таймаут
берётся из снапшота настроек.

Поведение ошибок по плану §1.1:

* `429` — один повтор с задержкой из `Retry-After`;
* `5xx` / таймаут / сеть — один повтор;
* затем (если задана) — `fallback_model` с теми же правилами;
* `401/403` — провайдер помечается `dead` до перезагрузки настроек
  (`reset()`), наружу отдаётся понятная `ProviderError` без ключа.

Ответ чистится `strip_thinking` → `extract_json` → `lenient_parse`. Ключ
`api_key` никогда не пишется в лог и не попадает в текст исключений.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Awaitable, Callable, Mapping, Sequence

import httpx

from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.repair import (
    DRAFT_KEYS,
    extract_json,
    lenient_parse,
    merge_pairs,
    strip_thinking,
)

logger = logging.getLogger(__name__)

DEFAULT_CONNECT_TIMEOUT = 5.0
MAX_RETRY_AFTER = 60.0
_AUTH_STATUSES = (401, 403)


class ProviderError(RuntimeError):
    """Понятная ошибка провайдера без секретов.

    `code` — машинный код для API (`PROVIDER_ERROR`, `PROVIDER_AUTH`, …),
    `status` — HTTP-статус, если он был, `model` — модель, на которой
    произошёл сбой. Текст сообщения не содержит `api_key`.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str = "PROVIDER_ERROR",
        model: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.model = model


@dataclass(frozen=True)
class AiCompletion:
    """Разобранный ответ модели: черновик и его метрики."""

    draft: dict[str, Any]
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def as_dict(self) -> dict[str, Any]:
        return {
            "draft": self.draft,
            "model": self.model,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "latency_ms": self.latency_ms,
        }


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on", "вкл")


def _normalize_draft(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Дополнить черновик дефолтами контракта, не теряя лишние поля."""
    draft: dict[str, Any] = dict(raw)
    draft["reply"] = str(draft.get("reply") or "").strip()
    draft["operator_note"] = str(draft.get("operator_note") or "").strip()
    draft["reason"] = str(draft.get("reason") or "").strip()
    for key in ("needs_human", "no_request", "clarify"):
        draft[key] = _as_bool(draft.get(key))
    used = draft.get("used")
    if used is None:
        used = []
    elif not isinstance(used, list):
        used = [used]
    draft["used"] = used
    try:
        draft["confidence"] = float(draft.get("confidence") or 0.0)
    except (TypeError, ValueError):
        draft["confidence"] = 0.0
    # Гарантируем полный набор ключей контракта.
    for key in DRAFT_KEYS:
        draft.setdefault(key, "" if key in ("reply", "operator_note", "reason") else None)
    return draft


def _parse_draft(text: str) -> dict[str, Any] | None:
    """Строгий JSON → терпимый разбор. None, если объекта нет вовсе."""
    block = extract_json(text)
    if block is not None:
        try:
            parsed = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            return _normalize_draft(parsed)

    result = lenient_parse(strip_thinking(text))
    if result is not None and result.pairs:
        fields = merge_pairs(result.pairs).fields
        if fields:
            return _normalize_draft(fields)
    return None


def _content_of(payload: Mapping[str, Any]) -> str | None:
    """Текст ответа из OpenAI-совместимого payload."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    choice = choices[0]
    if not isinstance(choice, Mapping):
        return None

    message = choice.get("message")
    content: Any = None
    if isinstance(message, Mapping):
        content = message.get("content")
    if content is None:
        content = choice.get("text")

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, Mapping) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "".join(parts)
    return None


def _usage(payload: Mapping[str, Any]) -> tuple[int, int]:
    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        return 0, 0
    tokens_in = usage.get("prompt_tokens", usage.get("input_tokens", 0))
    tokens_out = usage.get("completion_tokens", usage.get("output_tokens", 0))
    return _as_int(tokens_in), _as_int(tokens_out)


def _retry_after_seconds(value: str | None) -> float:
    """`Retry-After` → секунды; по умолчанию 1 с, потолок 60 с."""
    if not value:
        return 1.0
    text = value.strip()
    try:
        seconds = float(text)
    except (TypeError, ValueError):
        try:
            moment = parsedate_to_datetime(text)
        except (TypeError, ValueError, OverflowError):
            return 1.0
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        seconds = (moment - datetime.now(timezone.utc)).total_seconds()
    if seconds < 0:
        return 0.0
    return min(seconds, MAX_RETRY_AFTER)


class AiProvider:
    """Ленивый async-клиент провайдера.

    Один экземпляр живёт на `SupportService.ai`; клиент создаётся при первом
    успешном вызове и пересоздаётся, если сменились `base_url`/таймаут.
    `reset()` снимает флаг `dead` при перезагрузке настроек.
    """

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._transport = transport
        self._sleep = sleep or asyncio.sleep
        self._client: httpx.AsyncClient | None = None
        self._client_signature: tuple[str, int] | None = None
        self._dead = False

    # ── состояние ─────────────────────────────────────────────────────
    @property
    def has_client(self) -> bool:
        return self._client is not None

    @property
    def dead(self) -> bool:
        return self._dead

    def mark_dead(self) -> None:
        self._dead = True

    def reset(self) -> None:
        """Снять `dead` после перезагрузки настроек."""
        self._dead = False

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._client_signature = None

    async def _ensure_client(self, config: AiConfig) -> httpx.AsyncClient:
        signature = (config.base_url, int(config.timeout))
        if self._client is not None and self._client_signature == signature:
            return self._client
        if self._client is not None:
            await self._client.aclose()
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(float(config.timeout), connect=DEFAULT_CONNECT_TIMEOUT),
            trust_env=False,
            transport=self._transport,
        )
        self._client_signature = signature
        return self._client

    # ── публичный вызов ───────────────────────────────────────────────
    async def complete_json(
        self,
        messages: Sequence[Mapping[str, Any]],
        config: AiConfig,
    ) -> AiCompletion:
        """Запросить черновик у модели и вернуть разобранный ответ.

        При `effective_mode='off'` или пустом ключе клиент не создаётся:
        сразу `ProviderError`. После `401/403` повторные вызовы до `reset()`
        падают без сети.
        """
        if not messages:
            raise ProviderError("Не переданы сообщения для модели", code="PROVIDER_BAD_REQUEST")
        if config.effective_mode == "off" or not config.has_key:
            raise ProviderError(
                "ИИ выключен: режим off или не задан ключ провайдера",
                code="PROVIDER_DISABLED",
            )
        if self._dead:
            raise ProviderError(
                "Провайдер отключён после ошибки авторизации. Проверьте ключ и перезагрузите настройки.",
                code="PROVIDER_AUTH",
            )

        models = [config.model]
        if config.fallback_model and config.fallback_model != config.model:
            models.append(config.fallback_model)

        last_error: ProviderError | None = None
        for model in models:
            result = await self._try_model(messages, config, model)
            if isinstance(result, AiCompletion):
                return result
            last_error = result

        raise last_error or ProviderError("Провайдер не вернул ответ", code="PROVIDER_ERROR")

    # ── один провайдерский вызов с повтором ───────────────────────────
    async def _try_model(
        self,
        messages: Sequence[Mapping[str, Any]],
        config: AiConfig,
        model: str,
    ) -> AiCompletion | ProviderError:
        client = await self._ensure_client(config)
        body = {
            "model": model,
            "messages": [dict(message) for message in messages],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

        last_error: ProviderError | None = None
        for attempt in (0, 1):
            started = time.perf_counter()
            try:
                response = await client.post("/chat/completions", json=body, headers=headers)
            except httpx.TimeoutException:
                last_error = ProviderError(
                    "Провайдер не ответил за отведённое время",
                    code="PROVIDER_TIMEOUT",
                    model=model,
                )
                if attempt == 0:
                    continue
                return last_error
            except httpx.HTTPError:
                last_error = ProviderError(
                    "Сетевая ошибка при обращении к провайдеру",
                    code="PROVIDER_NETWORK",
                    model=model,
                )
                if attempt == 0:
                    continue
                return last_error

            latency_ms = int((time.perf_counter() - started) * 1000)
            status = response.status_code

            if status in _AUTH_STATUSES:
                self._dead = True
                # Никогда не включаем тело ответа/ключ в сообщение.
                raise ProviderError(
                    "Провайдер отклонил ключ доступа (401/403). Проверьте ключ и перезагрузите настройки.",
                    status=status,
                    code="PROVIDER_AUTH",
                    model=model,
                )

            if status == 429:
                if attempt == 0:
                    delay = _retry_after_seconds(response.headers.get("retry-after"))
                    await self._sleep(delay)
                    continue
                return ProviderError(
                    "Провайдер ограничил частоту запросов (429)",
                    status=status,
                    code="PROVIDER_RATE_LIMIT",
                    model=model,
                )

            if 500 <= status < 600:
                last_error = ProviderError(
                    f"Провайдер временно недоступен ({status})",
                    status=status,
                    code="PROVIDER_UNAVAILABLE",
                    model=model,
                )
                if attempt == 0:
                    continue
                return last_error

            if status >= 400:
                raise ProviderError(
                    f"Провайдер отклонил запрос ({status})",
                    status=status,
                    code="PROVIDER_REJECTED",
                    model=model,
                )

            completion = self._parse_response(response, model, latency_ms)
            if completion is None:
                last_error = ProviderError(
                    "Провайдер вернул ответ, который не удалось разобрать как JSON",
                    status=status,
                    code="PROVIDER_BAD_JSON",
                    model=model,
                )
                if attempt == 0:
                    continue
                return last_error
            return completion

        return last_error or ProviderError("Провайдер не вернул ответ", code="PROVIDER_ERROR")

    def _parse_response(
        self,
        response: httpx.Response,
        model: str,
        latency_ms: int,
    ) -> AiCompletion | None:
        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError):
            logger.debug("Provider %s returned non-JSON body", model)
            return None
        if not isinstance(payload, Mapping):
            return None

        content = _content_of(payload)
        if not content:
            return None
        draft = _parse_draft(content)
        if draft is None:
            return None

        tokens_in, tokens_out = _usage(payload)
        actual_model = payload.get("model")
        return AiCompletion(
            draft=draft,
            model=str(actual_model or model),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=max(latency_ms, 0),
        )
