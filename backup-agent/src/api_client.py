"""HTTP client for the CMS agent API."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)

RETRYABLE = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
    httpx.ConnectTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)
RETRY_ERRORS = RETRYABLE + (httpx.HTTPStatusError,)


class CmsUnavailable(RuntimeError):
    """CMS is unreachable; the agent must keep working from its cache."""


class ApiClient:
    def __init__(self, base_url: str, host_id: str, token: str, version: str, protocol: int = 1,
                 timeout: int = 120, upload_timeout: int = 3600):
        self.base = base_url.rstrip("/")
        self.host_id = host_id
        self.token = token
        self.version = version
        self.protocol = protocol
        self.timeout = timeout
        self.upload_timeout = upload_timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Agent-Version": self.version,
            "X-Agent-Protocol": str(self.protocol),
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
        retries: int = 3,
        timeout: Optional[int] = None,
    ) -> httpx.Response:
        url = f"{self.base}{path}"
        last_error: Optional[Exception] = None
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
                    response = await client.request(method, url, json=json_body, headers=self._headers())
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError("cms 5xx", request=response.request, response=response)
                return response
            except RETRY_ERRORS as exc:
                last_error = exc
                if attempt + 1 < retries:
                    await asyncio.sleep(min(30, 2 ** attempt))
        raise CmsUnavailable(str(last_error))

    # ------------------------------------------------------------------ protocol

    async def register(self) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/api/backup-agent/v1/register",
            json_body={
                "host_id": self.host_id,
                "token": self.token,
                "agent_version": self.version,
                "protocol_version": self.protocol,
            },
        )
        return response.json()

    async def heartbeat(self, spool_bytes: int, disk_free: Optional[int], uptime: int) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/api/backup-agent/v1/heartbeat",
            json_body={
                "agent_version": self.version,
                "spool_bytes": spool_bytes,
                "disk_free": disk_free,
                "uptime_seconds": uptime,
            },
        )
        return response.json()

    async def state(self, etag: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
        headers = self._headers()
        if etag:
            headers["If-None-Match"] = etag
        url = f"{self.base}/api/backup-agent/v1/state"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
        except RETRYABLE as exc:
            raise CmsUnavailable(str(exc))
        if response.status_code == 304:
            return None, etag
        response.raise_for_status()
        return response.json(), response.headers.get("ETag")

    async def inventory(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/api/backup-agent/v1/inventory", json_body=payload)
        return response.json()

    async def create_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/api/backup-agent/v1/runs", json_body=payload)
        return response.json()

    async def patch_run(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("PATCH", f"/api/backup-agent/v1/runs/{run_id}", json_body=payload)
        return response.json()

    async def register_artifact(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request(
            "POST", f"/api/backup-agent/v1/runs/{run_id}/artifacts", json_body=payload
        )
        return response.json()

    async def upload_file(self, upload_url: str, path: Path) -> None:
        url = upload_url if upload_url.startswith("http") else f"{self.base}{upload_url}"

        async def _stream() -> AsyncIterator[bytes]:
            with path.open("rb") as fh:
                while True:
                    chunk = await asyncio.to_thread(fh.read, 1024 * 256)
                    if not chunk:
                        break
                    yield chunk

        try:
            async with httpx.AsyncClient(timeout=self.upload_timeout) as client:
                response = await client.put(url, content=_stream(), headers=self._headers())
        except RETRYABLE as exc:
            raise CmsUnavailable(str(exc))
        response.raise_for_status()

    async def download_artifact(self, artifact_id: str, target: Path) -> None:
        url = f"{self.base}/api/backup-agent/v1/download/{artifact_id}"
        try:
            async with httpx.AsyncClient(timeout=self.upload_timeout) as client:
                async with client.stream("GET", url, headers=self._headers()) as response:
                    response.raise_for_status()
                    with target.open("wb") as fh:
                        async for chunk in response.aiter_bytes(1024 * 256):
                            fh.write(chunk)
        except RETRYABLE as exc:
            raise CmsUnavailable(str(exc))

    async def poll_commands(self, limit: int = 10) -> list[dict[str, Any]]:
        response = await self._request("GET", f"/api/backup-agent/v1/commands?limit={limit}")
        return response.json().get("data") or []

    async def finish_command(self, command_id: str, status: str = "done") -> None:
        await self._request(
            "POST",
            f"/api/backup-agent/v1/commands/{command_id}/finish",
            json_body={"status": status},
        )
