"""rclone storage — one adapter for Google Drive / Yandex Disk / Dropbox / B2..."""
from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator, Optional

from .base import BytesLike, Storage, StorageConfigError, StorageObject, StorageTestResult, iter_bytes


class RcloneStorage(Storage):
    kind = "rclone"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.remote = (self.config.get("remote") or "").rstrip(":")
        self.path = (self.config.get("path") or "").strip("/")
        self.config_file = self.config.get("config_file") or self.secrets.get("config_file")
        if not self.remote:
            raise StorageConfigError("rclone storage requires config.remote (e.g. 'gdrive')")

    # ------------------------------------------------------------------ helpers

    def _target(self, key: str = "") -> str:
        parts = [self.remote + ":"]
        if self.path:
            parts.append(self.path)
        if key:
            parts.append(key.lstrip("/"))
        return "/".join(parts)

    def _base_args(self) -> list[str]:
        args = ["rclone"]
        if self.config_file:
            args.extend(["--config", str(self.config_file)])
        transfers = self.opt_int("concurrency", 2)
        if transfers > 0:
            args.extend(["--transfers", str(transfers)])
        bwlimit = self.opt_str("bandwidth_limit", "off")
        if bwlimit and bwlimit != "off":
            args.extend(["--bwlimit", bwlimit])
        return args

    async def _run(self, args: list[str], stdin: Optional[bytes] = None) -> tuple[int, bytes, bytes]:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate(stdin)
        return proc.returncode or 0, out, err

    # --------------------------------------------------------------- contract

    async def put(self, key: str, data: BytesLike) -> None:
        target = self._target(key)
        if isinstance(data, (bytes, bytearray)):
            code, _, err = await self._run(self._base_args() + ["copyto", "-", target], bytes(data))
            if code != 0:
                raise StorageErrorRclone(err)
            return

        proc = await asyncio.create_subprocess_exec(
            *self._base_args(),
            "copyto",
            "-",
            target,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdin is not None
        try:
            async for chunk in iter_bytes(data):
                proc.stdin.write(chunk)
                await proc.stdin.drain()
            proc.stdin.close()
        except Exception:
            proc.kill()
            raise
        _, err = await proc.communicate()
        if (proc.returncode or 0) != 0:
            raise StorageErrorRclone(err)

    async def get(self, key: str) -> AsyncIterator[bytes]:
        proc = await asyncio.create_subprocess_exec(
            *self._base_args(),
            "cat",
            self._target(key),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        while True:
            chunk = await proc.stdout.read(1024 * 256)
            if not chunk:
                break
            yield chunk
        await proc.wait()

    async def delete(self, key: str) -> None:
        await self._run(self._base_args() + ["deletefile", self._target(key)])

    async def list(self, prefix: str) -> list[StorageObject]:
        args = self._base_args() + [
            "lsf",
            "-R",
            "--files-only",
            "--separator",
            ";",
            "--format",
            "p;s",
            self._target(prefix),
        ]
        code, out, err = await self._run(args)
        if code != 0:
            # A missing directory is not an error for our callers.
            if b"not found" in err.lower() or b"directory not found" in err.lower():
                return []
            raise StorageErrorRclone(err)
        items: list[StorageObject] = []
        for line in out.decode("utf-8", "replace").splitlines():
            if not line.strip():
                continue
            name, _, size = line.partition(";")
            try:
                items.append(StorageObject(key=name, size=int(size or 0)))
            except ValueError:
                items.append(StorageObject(key=name))
        return items

    async def test(self) -> StorageTestResult:
        started = time.perf_counter()
        try:
            code, _, err = await self._run(self._base_args() + ["lsd", self._target()])
            if code != 0:
                # Try to create the target path once; then re-check.
                await self._run(self._base_args() + ["mkdir", self._target()])
                code, _, err = await self._run(self._base_args() + ["lsd", self._target()])
        except FileNotFoundError:
            return StorageTestResult(False, "rclone binary is not installed")
        if code != 0:
            return StorageTestResult(False, err.decode("utf-8", "replace").strip()[:500])
        return StorageTestResult(True, "", int((time.perf_counter() - started) * 1000))


class StorageErrorRclone(RuntimeError):
    def __init__(self, stderr: bytes):
        super().__init__(stderr.decode("utf-8", "replace").strip()[:500] or "rclone failed")
