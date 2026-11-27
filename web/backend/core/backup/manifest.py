"""Backup manifest: what exactly was captured and how to verify it.

A manifest is written last in the object prefix and is the marker of a complete
backup. It is HMAC-signed with the CMS encryption key so a tampered object in
remote storage cannot be restored silently.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from web.backend.core.crypto import _key_bytes

MANIFEST_VERSION = 1
TOOL_NAME = "hexaveil-backup"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_backup_id(now: Optional[datetime] = None) -> str:
    moment = now or _utcnow()
    return f"bkp_{moment.strftime('%Y%m%dT%H%M%SZ')}_{secrets.token_hex(4)}"


def new_consistency_group(now: Optional[datetime] = None) -> str:
    moment = now or _utcnow()
    return f"grp_{moment.strftime('%Y%m%dT%H%M%SZ')}_{secrets.token_hex(3)}"


def artifact_entry(
    *,
    artifact_type: str,
    file: str,
    size: int,
    sha256: str,
    encrypted: bool = True,
    component: Optional[str] = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "type": artifact_type,
        "file": file,
        "size": int(size),
        "sha256": sha256,
        "encrypted": bool(encrypted),
    }
    if component:
        entry["component"] = component
    return entry


def component_entry(
    *,
    recipe: str,
    recipe_version: int = 1,
    name: Optional[str] = None,
    container: Optional[str] = None,
    image: Optional[str] = None,
    image_digest: Optional[str] = None,
    app_version: Optional[str] = None,
    migrations: Optional[dict[str, Any]] = None,
    artifacts: Optional[Iterable[dict[str, Any]]] = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "recipe": recipe,
        "recipe_version": int(recipe_version),
        "artifacts": list(artifacts or []),
    }
    if name:
        entry["name"] = name
    if container:
        entry["container"] = container
    if image:
        entry["image"] = image
    if image_digest:
        entry["image_digest"] = image_digest
    if app_version:
        entry["app_version"] = app_version
    if migrations:
        entry["migrations"] = migrations
    return entry


def build_manifest(
    *,
    backup_id: str,
    host: dict[str, Any],
    components: list[dict[str, Any]],
    consistency_group: Optional[str] = None,
    integrity: Optional[dict[str, Any]] = None,
    tool_version: str = "0.1.0",
    created_at: Optional[datetime] = None,
) -> dict[str, Any]:
    moment = created_at or _utcnow()
    return {
        "manifest_version": MANIFEST_VERSION,
        "backup_id": backup_id,
        "created_at": moment.isoformat(),
        "host": host,
        "consistency_group": consistency_group,
        "components": components,
        "integrity": integrity or {},
        "tool": {"name": TOOL_NAME, "version": tool_version},
    }


def dumps(manifest: dict[str, Any]) -> str:
    """Deterministic JSON (stable signature input)."""
    return json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def loads(payload: str | bytes) -> dict[str, Any]:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    if int(data.get("manifest_version", 0)) != MANIFEST_VERSION:
        raise ValueError(f"unsupported manifest version: {data.get('manifest_version')!r}")
    if not data.get("backup_id"):
        raise ValueError("manifest has no backup_id")
    return data


def sign(payload: str) -> str:
    return hmac.new(_key_bytes(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify(payload: str, signature: str) -> bool:
    if not signature:
        return False
    return hmac.compare_digest(sign(payload), signature.strip().lower())


def total_size(manifest: dict[str, Any]) -> int:
    total = 0
    for component in manifest.get("components", []):
        for artifact in component.get("artifacts", []):
            total += int(artifact.get("size") or 0)
    return total


def find_artifact(manifest: dict[str, Any], file: str) -> Optional[dict[str, Any]]:
    for component in manifest.get("components", []):
        for artifact in component.get("artifacts", []):
            if artifact.get("file") == file:
                return artifact
    return None
