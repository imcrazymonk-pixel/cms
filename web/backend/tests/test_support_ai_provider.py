"""B1b-2a — провайдер: ленивый httpx, повторы, fallback, утечка ключа.

Сеть не используется: `httpx.MockTransport`. Проверяются §1.1 и §8 плана
`docs/plans/2026-11-28-support-stage-b.md`.
"""
from __future__ import annotations

import json

import httpx
import pytest

from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.provider import AiCompletion, AiProvider, ProviderError

SECRET = "sk-test-secret-1234567890"


async def _no_sleep(_seconds: float) -> None:
    return None


def _config(**overrides) -> AiConfig:
    values = {
        "mode": "suggest",
        "effective_mode": "suggest",
        "has_key": True,
        "api_key": SECRET,
        "base_url": "https://api.test/v1",
        "model": "primary",
        "fallback_model": "",
        "timeout": 7,
        "max_tokens": 321,
        "temperature": 0.4,
    }
    values.update(overrides)
    return AiConfig(**values)


def _response(content: str, *, status: int = 200, model: str = "served-model") -> httpx.Response:
    return httpx.Response(
        status,
        json={
            "model": model,
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        },
    )


def _provider(handler, **kwargs) -> AiProvider:
    return AiProvider(transport=httpx.MockTransport(handler), sleep=_no_sleep, **kwargs)


MESSAGES = [{"role": "user", "content": "Клиент не подключается"}]


@pytest.mark.asyncio
async def test_valid_json_and_request_shape():
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            {
                "url": str(request.url),
                "auth": request.headers.get("authorization"),
                "body": json.loads(request.content),
            }
        )
        return _response('{"reply": "Обновите подписку", "confidence": 0.93, "used": [1]}')

    provider = _provider(handler)
    assert provider.has_client is False

    completion = await provider.complete_json(MESSAGES, _config())

    assert isinstance(completion, AiCompletion)
    assert completion.draft["reply"] == "Обновите подписку"
    assert completion.draft["confidence"] == 0.93
    assert completion.draft["used"] == [1]
    assert completion.model == "served-model"
    assert (completion.tokens_in, completion.tokens_out) == (11, 7)
    assert completion.latency_ms >= 0
    assert provider.has_client is True

    assert seen[0]["url"] == "https://api.test/v1/chat/completions"
    assert seen[0]["auth"] == f"Bearer {SECRET}"
    body = seen[0]["body"]
    assert body["model"] == "primary"
    assert body["response_format"] == {"type": "json_object"}
    assert body["temperature"] == 0.4
    assert body["max_tokens"] == 321
    assert body["messages"] == MESSAGES

    await provider.aclose()


@pytest.mark.asyncio
async def test_fenced_json_is_stripped():
    def handler(_request: httpx.Request) -> httpx.Response:
        return _response('```json\n{"reply": "Готово", "confidence": 0.8}\n```')

    provider = _provider(handler)
    completion = await provider.complete_json(MESSAGES, _config())
    assert completion.draft["reply"] == "Готово"
    await provider.aclose()


@pytest.mark.asyncio
async def test_lenient_single_quotes_are_parsed():
    def handler(_request: httpx.Request) -> httpx.Response:
        return _response("{reply: 'Проверьте кабинет', confidence: 0.7}")

    provider = _provider(handler)
    completion = await provider.complete_json(MESSAGES, _config())
    assert completion.draft["reply"] == "Проверьте кабинет"
    await provider.aclose()


@pytest.mark.asyncio
async def test_429_retries_once_by_retry_after():
    calls: list[int] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return _response('{"reply": "ok", "confidence": 0.9}')

    provider = _provider(handler)
    completion = await provider.complete_json(MESSAGES, _config())
    assert completion.draft["reply"] == "ok"
    assert len(calls) == 2
    await provider.aclose()


@pytest.mark.asyncio
async def test_500_retries_then_uses_fallback_model():
    models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        models.append(body["model"])
        if body["model"] == "primary":
            return httpx.Response(500)
        return _response('{"reply": "fallback ok", "confidence": 0.88}', model="fallback")

    provider = _provider(handler)
    completion = await provider.complete_json(
        MESSAGES, _config(fallback_model="fallback")
    )

    assert completion.draft["reply"] == "fallback ok"
    assert completion.model == "fallback"
    # Две попытки primary (5xx + повтор), затем успех fallback.
    assert models == ["primary", "primary", "fallback"]
    await provider.aclose()


@pytest.mark.asyncio
async def test_timeout_retries_once():
    calls: list[int] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("timed out")
        return _response('{"reply": "после таймаута", "confidence": 0.9}')

    provider = _provider(handler)
    completion = await provider.complete_json(MESSAGES, _config())
    assert completion.draft["reply"] == "после таймаута"
    assert len(calls) == 2
    await provider.aclose()


@pytest.mark.asyncio
async def test_401_marks_provider_dead_and_hides_key(caplog):
    calls: list[int] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401, json={"error": "bad key"})

    provider = _provider(handler)
    with pytest.raises(ProviderError) as info:
        await provider.complete_json(MESSAGES, _config())

    error = info.value
    assert error.code == "PROVIDER_AUTH"
    assert error.status == 401
    assert provider.dead is True
    assert SECRET not in str(error)
    assert SECRET not in repr(error)
    assert SECRET not in caplog.text

    # До reset() повторный вызов не ходит в сеть.
    with pytest.raises(ProviderError):
        await provider.complete_json(MESSAGES, _config())
    assert len(calls) == 1

    provider.reset()
    assert provider.dead is False
    await provider.aclose()


@pytest.mark.asyncio
async def test_mode_off_does_not_create_client():
    provider = _provider(lambda _request: _response('{"reply": "x"}'))
    config = _config(mode="off", effective_mode="off")

    with pytest.raises(ProviderError) as info:
        await provider.complete_json(MESSAGES, config)

    assert info.value.code == "PROVIDER_DISABLED"
    assert provider.has_client is False


@pytest.mark.asyncio
async def test_empty_key_does_not_create_client():
    provider = _provider(lambda _request: _response('{"reply": "x"}'))
    config = _config(has_key=False, api_key="", effective_mode="off")

    with pytest.raises(ProviderError):
        await provider.complete_json(MESSAGES, config)
    assert provider.has_client is False
