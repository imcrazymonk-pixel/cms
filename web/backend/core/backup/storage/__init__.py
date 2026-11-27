"""Storage factory.

``get_storage(row)`` accepts a mapping shaped like a ``backup_storages`` row:
``name``, ``kind``, ``config`` (JSON), ``advanced`` (JSON), ``secrets``
(encrypted JSON string). Secrets are decrypted here so adapters never touch
the database.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from web.backend.core.crypto import decrypt

from .base import (
    BytesLike,
    Storage,
    StorageConfigError,
    StorageError,
    StorageObject,
    StorageTestResult,
    iter_bytes,
)
from .local import LocalStorage
from .rclone import RcloneStorage
from .s3 import S3Storage
from .sftp import SftpStorage

__all__ = [
    "BytesLike",
    "Storage",
    "StorageConfigError",
    "StorageError",
    "StorageObject",
    "StorageTestResult",
    "get_storage",
    "iter_bytes",
    "SUPPORTED_KINDS",
]

SUPPORTED_KINDS = ("local", "s3", "sftp", "ssh", "webdav", "ftp", "rclone")

_CLASSES: dict[str, type[Storage]] = {
    "local": LocalStorage,
    "s3": S3Storage,
    "sftp": SftpStorage,
    "ssh": SftpStorage,  # SFTP is the transport behind an SSH destination
    "rclone": RcloneStorage,
    "webdav": RcloneStorage,  # requires a configured rclone remote
    "ftp": RcloneStorage,  # requires a configured rclone remote
}


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def decode_secrets(value: Optional[str]) -> dict[str, Any]:
    """Decrypt the storage/channel secrets blob (legacy plaintext tolerated)."""
    if not value:
        return {}
    decoded = decrypt(value)
    if not decoded:
        return {}
    return _as_dict(decoded)


def get_storage(row: Mapping[str, Any]) -> Storage:
    kind = str(row.get("kind") or "").lower()
    cls = _CLASSES.get(kind)
    if cls is None:
        raise StorageConfigError(f"unsupported storage kind: {kind!r}")

    config = _as_dict(row.get("config"))
    advanced = _as_dict(row.get("advanced"))
    secrets = decode_secrets(row.get("secrets"))

    kwargs = {
        "name": str(row.get("name") or kind),
        "config": config,
        "advanced": advanced,
        "secrets": secrets,
    }
    if kind in ("webdav", "ftp"):
        if not config.get("remote"):
            raise StorageConfigError(
                f"storage kind {kind!r} requires an rclone remote in config.remote"
            )
        kwargs["name"] = str(row.get("name") or kind)
    return cls(kind=kind, **kwargs)
