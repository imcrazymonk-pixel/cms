"""Storage abstraction for backup artifacts.

Every destination implements the same small contract, so the orchestrator does
not care where bytes live. Heavy drivers (boto3/asyncssh) are imported lazily:
the module must be importable in environments without them (tests, CI).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Optional, Union

BytesLike = Union[bytes, bytearray, AsyncIterator[bytes]]

DEFAULT_PATH_TEMPLATE = "{host}/{yyyy}/{mm}/{dd}/{run}/{name}"
_UNSAFE_KEY = re.compile(r"(^|/)\.\.(/|$)")


@dataclass
class StorageObject:
    key: str
    size: int = 0
    modified: Optional[datetime] = None


@dataclass
class StorageTestResult:
    ok: bool
    message: str = ""
    latency_ms: Optional[int] = None


class StorageError(RuntimeError):
    """Raised when a storage operation cannot be performed."""


class StorageConfigError(StorageError):
    """Raised when storage configuration is incomplete or invalid."""


@dataclass
class Storage:
    name: str
    config: dict[str, Any] = field(default_factory=dict)
    advanced: dict[str, Any] = field(default_factory=dict)
    secrets: dict[str, Any] = field(default_factory=dict)
    kind: str = "base"

    # ------------------------------------------------------------------ helpers

    def opt_int(self, key: str, default: int) -> int:
        try:
            value = self.advanced.get(key, default)
            return int(value)
        except (TypeError, ValueError):
            return default

    def opt_bool(self, key: str, default: bool = False) -> bool:
        value = self.advanced.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")

    def opt_str(self, key: str, default: str = "") -> str:
        value = self.advanced.get(key, default)
        return str(value) if value is not None else default

    def template(self) -> str:
        return self.opt_str("path_template", DEFAULT_PATH_TEMPLATE)

    def key_for(self, variables: dict[str, Any]) -> str:
        """Render the object key from the path template and reject traversal."""
        values = {**variables}
        now = values.get("now")
        if isinstance(now, datetime):
            values.setdefault("yyyy", f"{now.year:04d}")
            values.setdefault("mm", f"{now.month:02d}")
            values.setdefault("dd", f"{now.day:02d}")
        rendered = self.template()
        for name, value in values.items():
            rendered = rendered.replace("{" + name + "}", str(value))
        rendered = rendered.replace("//", "/").strip("/")
        if not rendered or _UNSAFE_KEY.search(rendered):
            raise StorageConfigError(f"unsafe storage key: {rendered!r}")
        return rendered

    # ----------------------------------------------------------------- contract

    async def put(self, key: str, data: BytesLike) -> None:
        raise NotImplementedError

    async def get(self, key: str) -> AsyncIterator[bytes]:
        raise NotImplementedError
        yield b""  # pragma: no cover - makes this an async generator

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def list(self, prefix: str) -> list[StorageObject]:
        raise NotImplementedError

    async def test(self) -> StorageTestResult:
        raise NotImplementedError

    async def stat(self, key: str) -> Optional[StorageObject]:
        return None


async def iter_bytes(data: BytesLike):
    """Yield bytes from either a buffer or an async byte stream."""
    if isinstance(data, (bytes, bytearray)):
        yield bytes(data)
        return
    async for chunk in data:
        if chunk:
            yield bytes(chunk)
