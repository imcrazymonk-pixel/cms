"""S3-compatible storage (Beget / R2 / Selectel / MinIO / Backblaze B2)."""
from __future__ import annotations

import asyncio
import tempfile
import time
from typing import Any, AsyncIterator, Optional

from .base import BytesLike, Storage, StorageConfigError, StorageObject, StorageTestResult, iter_bytes


class S3Storage(Storage):
    kind = "s3"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint = self.config.get("endpoint") or None
        self.region = self.config.get("region") or "us-east-1"
        self.bucket = self.config.get("bucket")
        self.prefix = (self.config.get("prefix") or "").strip("/")
        self.path_style = bool(self.config.get("path_style", True))
        self.access_key = self.secrets.get("access_key") or self.config.get("access_key")
        self.secret_key = self.secrets.get("secret_key") or self.config.get("secret_key")
        if not self.bucket:
            raise StorageConfigError("s3 storage requires config.bucket")
        if not self.access_key or not self.secret_key:
            raise StorageConfigError("s3 storage requires access_key/secret_key")

    # ------------------------------------------------------------------ boto3

    def _client_sync(self):
        import boto3  # lazy: keep module importable without the driver
        from botocore.config import Config

        return boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(
                s3={"addressing_style": "path" if self.path_style else "virtual"},
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=self.opt_int("timeout_sec", 600),
                read_timeout=self.opt_int("timeout_sec", 600),
            ),
        )

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    # --------------------------------------------------------------- contract

    async def put(self, key: str, data: BytesLike) -> None:
        full_key = self._full_key(key)
        client = self._client_sync()
        if isinstance(data, (bytes, bytearray)):
            await asyncio.to_thread(client.put_object, Bucket=self.bucket, Key=full_key, Body=bytes(data))
            return

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".upload")
        try:
            with tmp:
                async for chunk in iter_bytes(data):
                    await asyncio.to_thread(tmp.write, chunk)
            await asyncio.to_thread(client.upload_file, tmp.name, self.bucket, full_key)
        finally:
            await asyncio.to_thread(lambda: _unlink(tmp.name))

    async def get(self, key: str) -> AsyncIterator[bytes]:
        client = self._client_sync()
        response = await asyncio.to_thread(client.get_object, Bucket=self.bucket, Key=self._full_key(key))
        body = response["Body"]
        try:
            while True:
                chunk = await asyncio.to_thread(body.read, 1024 * 256)
                if not chunk:
                    break
                yield chunk
        finally:
            await asyncio.to_thread(body.close)

    async def delete(self, key: str) -> None:
        client = self._client_sync()
        await asyncio.to_thread(client.delete_object, Bucket=self.bucket, Key=self._full_key(key))

    async def list(self, prefix: str) -> list[StorageObject]:
        client = self._client_sync()
        full_prefix = self._full_key(prefix) if prefix else (f"{self.prefix}/" if self.prefix else "")
        items: list[StorageObject] = []

        def _collect() -> list[StorageObject]:
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=full_prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if self.prefix and key.startswith(self.prefix + "/"):
                        key = key[len(self.prefix) + 1 :]
                    items.append(
                        StorageObject(key=key, size=int(obj.get("Size") or 0), modified=obj.get("LastModified"))
                    )
            return items

        return await asyncio.to_thread(_collect)

    async def stat(self, key: str) -> Optional[StorageObject]:
        client = self._client_sync()
        try:
            head = await asyncio.to_thread(client.head_object, Bucket=self.bucket, Key=self._full_key(key))
        except Exception:  # noqa: BLE001
            return None
        return StorageObject(key=key, size=int(head.get("ContentLength") or 0), modified=head.get("LastModified"))

    async def test(self) -> StorageTestResult:
        started = time.perf_counter()
        client = self._client_sync()
        probe = self._full_key(".hexaveil-probe")
        try:
            await asyncio.to_thread(client.put_object, Bucket=self.bucket, Key=probe, Body=b"ok")
            head = await asyncio.to_thread(client.head_object, Bucket=self.bucket, Key=probe)
            await asyncio.to_thread(client.delete_object, Bucket=self.bucket, Key=probe)
        except Exception as exc:  # noqa: BLE001
            return StorageTestResult(False, f"{type(exc).__name__}: {exc}")
        ok = int(head.get("ContentLength") or 0) == 2
        return StorageTestResult(ok, "" if ok else "probe size mismatch", int((time.perf_counter() - started) * 1000))


def _unlink(path: str) -> None:
    import os

    try:
        os.unlink(path)
    except OSError:
        pass
