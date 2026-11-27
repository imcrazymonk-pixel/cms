"""Local filesystem storage (root is always a directory inside the container)."""
from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Optional

from .base import BytesLike, Storage, StorageConfigError, StorageObject, StorageTestResult, iter_bytes


class LocalStorage(Storage):
    kind = "local"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raw_root = self.config.get("path")
        if not raw_root:
            raise StorageConfigError("local storage requires config.path")
        self.root = Path(raw_root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if self.root not in target.parents and target != self.root:
            raise StorageConfigError(f"key escapes storage root: {key!r}")
        return target

    async def put(self, key: str, data: BytesLike) -> None:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".part")
        with tmp.open("wb") as fh:
            async for chunk in iter_bytes(data):
                await asyncio.to_thread(fh.write, chunk)
        await asyncio.to_thread(os.replace, tmp, target)

    async def get(self, key: str) -> AsyncIterator[bytes]:
        target = self._resolve(key)
        if not target.is_file():
            raise FileNotFoundError(key)
        with target.open("rb") as fh:
            while True:
                chunk = await asyncio.to_thread(fh.read, 1024 * 256)
                if not chunk:
                    break
                yield chunk

    async def delete(self, key: str) -> None:
        target = self._resolve(key)
        if target.is_dir():
            raise IsADirectoryError(key)
        await asyncio.to_thread(target.unlink, True)

    async def list(self, prefix: str) -> list[StorageObject]:
        base = self._resolve(prefix) if prefix else self.root
        if not base.exists():
            return []
        items: list[StorageObject] = []
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            stat = await asyncio.to_thread(path.stat)
            items.append(
                StorageObject(
                    key=str(path.relative_to(self.root)).replace(os.sep, "/"),
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                )
            )
        return items

    async def stat(self, key: str) -> Optional[StorageObject]:
        target = self._resolve(key)
        if not target.is_file():
            return None
        stat = await asyncio.to_thread(target.stat)
        return StorageObject(
            key=key,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )

    async def test(self) -> StorageTestResult:
        started = time.perf_counter()
        probe = self.root / ".hexaveil-probe"
        try:
            await asyncio.to_thread(probe.write_bytes, b"ok")
            data = await asyncio.to_thread(probe.read_bytes)
            await asyncio.to_thread(probe.unlink, True)
        except Exception as exc:  # noqa: BLE001
            return StorageTestResult(False, f"{type(exc).__name__}: {exc}")
        ok = data == b"ok"
        return StorageTestResult(ok, "" if ok else "probe mismatch", int((time.perf_counter() - started) * 1000))
