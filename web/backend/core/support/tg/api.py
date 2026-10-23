"""Telegram Bot API client — тонкий httpx-обёртка, без автоматических ретраев.

Методы: get_updates/send_message/send_photo/send_document/get_file/download_file.
Ошибки: TelegramAPIError (общая) и TelegramRateLimited(429, retry_after).
429 и 5xx НЕ повторяются автоматически — решение о паузе принимает поллер.
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_URL = "https://api.telegram.org"
FILE_URL = "https://api.telegram.org/file"
REQUEST_TIMEOUT = 40.0  # дольше long-poll (30с)


class TelegramAPIError(Exception):
    """Ответ Bot API с ok=false или сетевой сбой."""

    def __init__(self, description: str, *, error_code: int | None = None):
        super().__init__(description)
        self.description = description
        self.error_code = error_code


class TelegramRateLimited(TelegramAPIError):
    """HTTP 429 — выдержать паузу (retry_after, сек)."""

    def __init__(self, description: str, retry_after: int = 0, *, error_code: int | None = 429):
        super().__init__(description, error_code=error_code)
        self.retry_after = int(retry_after or 0)


class TelegramClient:
    """Безопасный к инъекциям клиент: можно передать свой httpx.AsyncClient (тесты)."""

    def __init__(
        self,
        token: str,
        *,
        api_url: str = API_URL,
        http_client: httpx.AsyncClient | None = None,
    ):
        self._token = token
        self._api_url = api_url.rstrip("/")
        self.base_url = f"{self._api_url}/bot{token}"
        self._http = http_client
        self._owned_http = http_client is None

    @property
    def token(self) -> str:
        return self._token

    async def close(self) -> None:
        if self._owned_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    # ── Bot API методы ─────────────────────────────────────────────
    async def get_updates(self, *, offset: int | None = None, timeout: int = 30, limit: int = 100) -> list[dict]:
        """Long-poll: пустой список — нормальный ответ по таймауту."""
        payload: dict[str, Any] = {"timeout": timeout, "limit": limit}
        if offset:
            payload["offset"] = offset
        result = await self._call("getUpdates", payload=payload, timeout=timeout + 8)
        return result if isinstance(result, list) else []

    async def send_message(self, chat_id: int, text: str, *, parse_mode: str | None = None) -> dict:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        result = await self._call("sendMessage", payload=payload)
        return result if isinstance(result, dict) else {}

    async def send_photo(self, chat_id: int, file_id: str, *, caption: str | None = None) -> dict:
        payload = {"chat_id": chat_id, "photo": file_id}
        if caption:
            payload["caption"] = caption
        result = await self._call("sendPhoto", payload=payload)
        return result if isinstance(result, dict) else {}

    async def send_document(self, chat_id: int, file_id: str, *, caption: str | None = None) -> dict:
        payload = {"chat_id": chat_id, "document": file_id}
        if caption:
            payload["caption"] = caption
        result = await self._call("sendDocument", payload=payload)
        return result if isinstance(result, dict) else {}

    async def get_file(self, file_id: str) -> dict:
        result = await self._call("getFile", payload={"file_id": file_id})
        return result if isinstance(result, dict) else {}

    async def send_photo_upload(
        self,
        chat_id: int,
        file_path: str,
        *,
        filename: str | None = None,
        mime_type: str | None = None,
        caption: str | None = None,
    ) -> dict:
        """Отправка ЛОКАЛЬНОГО файла как фото (multipart)."""
        return await self._upload("sendPhoto", "photo", chat_id, file_path, filename=filename, mime_type=mime_type, caption=caption)

    async def send_document_upload(
        self,
        chat_id: int,
        file_path: str,
        *,
        filename: str | None = None,
        mime_type: str | None = None,
        caption: str | None = None,
    ) -> dict:
        """Отправка ЛОКАЛЬНОГО файла как документа (multipart)."""
        return await self._upload("sendDocument", "document", chat_id, file_path, filename=filename, mime_type=mime_type, caption=caption)

    async def _upload(
        self,
        method: str,
        param: str,
        chat_id: int,
        file_path: str,
        *,
        filename: str | None = None,
        mime_type: str | None = None,
        caption: str | None = None,
    ) -> dict:
        url = f"{self.base_url}/{method}"
        data: dict[str, Any] = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption
        name = filename or file_path.split("/")[-1]
        client = self._http
        owned = client is None
        if owned:
            client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
        try:
            with open(file_path, "rb") as fh:
                files = {param: (name, fh, mime_type or "application/octet-stream")}
                response = await client.post(url, data=data, files=files, timeout=REQUEST_TIMEOUT)
        except OSError as e:
            raise TelegramAPIError(f"{method}: cannot read {file_path}: {e}") from e
        except httpx.HTTPError as e:
            raise TelegramAPIError(f"{method} http error: {e}") from e
        finally:
            if owned and client is not None:
                await client.aclose()
        result = self._raise_or_json(response, method)
        return result if isinstance(result, dict) else {}

    async def download_file(self, file_path: str) -> bytes:
        """Скачивает файл по file_path: https://api.telegram.org/file/bot<token>/<path>."""
        url = f"{FILE_URL}/bot{self._token}/{file_path.lstrip('/')}"
        client = self._http
        owned = client is None
        if owned:
            client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
        try:
            response = await client.get(url)
            if response.status_code != 200:
                raise TelegramAPIError(f"download_file HTTP {response.status_code}", error_code=response.status_code)
            return response.content
        except TelegramAPIError:
            raise
        except httpx.HTTPError as e:
            raise TelegramAPIError(f"download_file http error: {e}") from e
        finally:
            if owned and client is not None:
                await client.aclose()

    async def _call(self, method: str, payload: dict[str, Any] | None = None, timeout: float = REQUEST_TIMEOUT) -> Any:
        url = f"{self.base_url}/{method}"
        client = self._http
        owned = client is None
        if owned:
            client = httpx.AsyncClient(timeout=timeout)
        try:
            response = await client.post(url, json=payload or {}, timeout=timeout)
        except httpx.HTTPError as e:
            raise TelegramAPIError(f"{method} http error: {e}") from e
        finally:
            if owned and client is not None:
                await client.aclose()
        return self._raise_or_json(response, method)

    @staticmethod
    def _raise_or_json(response: httpx.Response, method: str = "api") -> Any:
        try:
            payload = response.json()
        except ValueError:
            raise TelegramAPIError(f"{method}: bad JSON (HTTP {response.status_code})", error_code=response.status_code)
        if not isinstance(payload, dict):
            raise TelegramAPIError(f"{method}: unexpected payload type {type(payload).__name__} (HTTP {response.status_code})")
        if payload.get("ok") is not True:
            description = str(payload.get("description") or "unknown error")
            error_code = payload.get("error_code")
            if response.status_code == 429 or error_code == 429:
                retry_after = 0
                try:
                    retry_after = int(payload.get("parameters", {}).get("retry_after") or 0)
                except (TypeError, ValueError):
                    retry_after = 0
                raise TelegramRateLimited(description, retry_after, error_code=error_code)
            raise TelegramAPIError(f"{description} (error_code={error_code})", error_code=error_code)
        return payload.get("result")
