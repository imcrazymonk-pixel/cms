"""SFTP storage — "another server, down to a specific folder"."""
from __future__ import annotations

import posixpath
import time
from typing import AsyncIterator, Optional

from .base import BytesLike, Storage, StorageConfigError, StorageObject, StorageTestResult, iter_bytes


class SftpStorage(Storage):
    kind = "sftp"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = self.config.get("host")
        self.port = int(self.config.get("port") or 22)
        self.user = self.config.get("user")
        self.base = (self.config.get("path") or "").rstrip("/")
        self.password = self.secrets.get("password") or None
        self.private_key = self.secrets.get("private_key") or None
        self.known_hosts = self.config.get("known_hosts") or None
        if not self.host or not self.user:
            raise StorageConfigError("sftp storage requires config.host and config.user")
        if not self.base.startswith("/"):
            raise StorageConfigError("sftp storage requires an absolute config.path")
        if not self.password and not self.private_key:
            raise StorageConfigError("sftp storage requires password or private_key")

    def _full(self, key: str) -> str:
        return posixpath.join(self.base, key.lstrip("/"))

    def _connect(self):
        import asyncssh  # lazy

        kwargs: dict = {
            "host": self.host,
            "port": self.port,
            "username": self.user,
            "known_hosts": self.known_hosts,
        }
        if self.password:
            kwargs["password"] = self.password
        if self.private_key:
            try:
                kwargs["client_keys"] = [asyncssh.import_private_key(self.private_key)]
            except Exception as exc:  # noqa: BLE001
                raise StorageConfigError(f"invalid private_key: {exc}") from exc
        return asyncssh.connect(**kwargs)

    async def put(self, key: str, data: BytesLike) -> None:
        full = self._full(key)
        async with self._connect() as conn:
            async with conn.start_sftp_client() as sftp:
                parent = posixpath.dirname(full)
                if parent:
                    await sftp.makedirs(parent, exist_ok=True)
                tmp = full + ".part"
                async with sftp.open(tmp, "wb") as fh:
                    async for chunk in iter_bytes(data):
                        await fh.write(chunk)
                await sftp.rename(tmp, full)

    async def get(self, key: str) -> AsyncIterator[bytes]:
        full = self._full(key)
        async with self._connect() as conn:
            async with conn.start_sftp_client() as sftp:
                async with sftp.open(full, "rb") as fh:
                    while True:
                        chunk = await fh.read(1024 * 256)
                        if not chunk:
                            break
                        yield chunk

    async def delete(self, key: str) -> None:
        full = self._full(key)
        async with self._connect() as conn:
            async with conn.start_sftp_client() as sftp:
                try:
                    await sftp.remove(full)
                except Exception:  # noqa: BLE001 - already gone is fine
                    pass

    async def list(self, prefix: str) -> list[StorageObject]:
        base = self._full(prefix) if prefix else self.base
        items: list[StorageObject] = []

        async with self._connect() as conn:
            async with conn.start_sftp_client() as sftp:
                await self._walk(sftp, base, items)
        return items

    async def _walk(self, sftp, directory: str, out: list[StorageObject]) -> None:
        try:
            entries = await sftp.readdir(directory)
        except Exception:  # noqa: BLE001
            return
        for entry in entries:
            name = entry.filename
            if name in (".", ".."):
                continue
            path = posixpath.join(directory, name)
            attrs = entry.attrs
            if attrs is not None and attrs.type == 2:  # directory
                await self._walk(sftp, path, out)
            elif attrs is not None and attrs.type == 1:  # regular file
                key = path[len(self.base) + 1 :] if path.startswith(self.base + "/") else path
                out.append(StorageObject(key=key, size=int(attrs.size or 0), modified=attrs.mtime))

    async def stat(self, key: str) -> Optional[StorageObject]:
        full = self._full(key)
        try:
            async with self._connect() as conn:
                async with conn.start_sftp_client() as sftp:
                    attrs = await sftp.stat(full)
        except Exception:  # noqa: BLE001
            return None
        return StorageObject(key=key, size=int(attrs.size or 0), modified=attrs.mtime)

    async def test(self) -> StorageTestResult:
        started = time.perf_counter()
        probe = self._full(".hexaveil-probe")
        try:
            async with self._connect() as conn:
                async with conn.start_sftp_client() as sftp:
                    await sftp.makedirs(self.base, exist_ok=True)
                    async with sftp.open(probe, "wb") as fh:
                        await fh.write(b"ok")
                    attrs = await sftp.stat(probe)
                    await sftp.remove(probe)
        except Exception as exc:  # noqa: BLE001
            return StorageTestResult(False, f"{type(exc).__name__}: {exc}")
        ok = int(attrs.size or 0) == 2
        return StorageTestResult(ok, "" if ok else "probe size mismatch", int((time.perf_counter() - started) * 1000))
