"""Backup repository — all SQL for the backup module lives here.

Routers stay thin; this layer normalizes asyncpg/SQLAlchemy return values
(UUID -> str, JSONB -> python objects) so Pydantic models get plain data.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.crypto import encrypt

JSON_FIELDS = {
    "config",
    "advanced",
    "tags",
    "steps",
    "detect_meta",
    "threshold",
    "plan",
    "manifest",
    "component_ids",
    "storage_ids",
    "channel_ids",
    "payload",
}
ARRAY_FIELDS = {"tags", "component_ids", "storage_ids", "channel_ids", "steps"}


def _default_for(key: str) -> Any:
    if key in ARRAY_FIELDS:
        return []
    if key in JSON_FIELDS:
        return {}
    return None


def normalize(row: Any) -> dict[str, Any]:
    data = dict(row)
    # Never let the encrypted SSH key leave the repository layer.
    data.pop("ssh_key_enc", None)
    for key, value in list(data.items()):
        if isinstance(value, uuid.UUID):
            data[key] = str(value)
        elif key in JSON_FIELDS:
            if value is None:
                data[key] = _default_for(key)
            elif isinstance(value, str):
                try:
                    data[key] = json.loads(value)
                except json.JSONDecodeError:
                    data[key] = _default_for(key)
    return data


async def _all(session: AsyncSession, sql: str, params: Optional[dict] = None) -> list[dict[str, Any]]:
    result = await session.execute(text(sql), params or {})
    return [normalize(row) for row in result.mappings().all()]


async def _one(session: AsyncSession, sql: str, params: Optional[dict] = None) -> Optional[dict[str, Any]]:
    result = await session.execute(text(sql), params or {})
    row = result.mappings().first()
    return normalize(row) if row else None


async def _one_raw(session: AsyncSession, sql: str, params: Optional[dict] = None) -> Optional[dict[str, Any]]:
    """Like ``_one`` but keeps secret columns (used by internal services only)."""
    result = await session.execute(text(sql), params or {})
    row = result.mappings().first()
    if not row:
        return None
    data = dict(row)
    for key, value in list(data.items()):
        if isinstance(value, uuid.UUID):
            data[key] = str(value)
    return data


async def _exec(session: AsyncSession, sql: str, params: Optional[dict] = None) -> None:
    await session.execute(text(sql), params or {})


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def _update_payload(fields: dict[str, Any], allowed: Iterable[str]) -> tuple[str, dict[str, Any]]:
    allowed_set = set(allowed)
    sets: list[str] = []
    params: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in allowed_set or value is None:
            continue
        if key in JSON_FIELDS:
            value = _json(value)
        sets.append(f"{key} = :{key}")
        params[key] = value
    return ", ".join(sets), params


# --------------------------------------------------------------------------- hosts

_HOST_SELECT = """
SELECT h.*,
       (h.ssh_key_enc IS NOT NULL AND h.ssh_key_enc <> '') AS has_ssh_key,
       a.id            AS agent_id,
       a.agent_version,
       a.desired_version,
       a.status        AS agent_status,
       a.spool_bytes,
       a.last_heartbeat,
       (SELECT count(*) FROM backup_components c WHERE c.host_id = h.id) AS components_count,
       (SELECT count(*) FROM backup_policies p WHERE p.host_id = h.id) AS policies_count,
       (SELECT max(r.finished_at) FROM backup_runs r
          WHERE r.host_id = h.id AND r.status = 'success') AS last_success_at
FROM backup_hosts h
LEFT JOIN backup_agents a ON a.host_id = h.id
"""


async def list_hosts(session: AsyncSession) -> list[dict[str, Any]]:
    return await _all(session, _HOST_SELECT + " ORDER BY h.created_at")


async def get_host(session: AsyncSession, host_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, _HOST_SELECT + " WHERE h.id = :id", {"id": host_id})


async def get_host_raw(session: AsyncSession, host_id: str) -> Optional[dict[str, Any]]:
    """Full host row including the encrypted SSH key (never returned by the API)."""
    return await _one_raw(session, "SELECT * FROM backup_hosts WHERE id = :id", {"id": host_id})


async def create_host(session: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    host = await _one(
        session,
        """
        INSERT INTO backup_hosts (name, role, address, transport, ssh_port, ssh_user, credential_ref, ssh_key_enc, tags)
        VALUES (:name, :role, :address, :transport, :ssh_port, :ssh_user, :credential_ref, :ssh_key_enc, :tags)
        RETURNING *
        """,
        {
            "name": data["name"],
            "role": data.get("role", "server"),
            "address": data["address"],
            "transport": data.get("transport", "agent"),
            "ssh_port": data.get("ssh_port", 22),
            "ssh_user": data.get("ssh_user"),
            "credential_ref": data.get("credential_ref"),
            "ssh_key_enc": data.get("ssh_key_enc"),
            "tags": _json(data.get("tags", [])),
        },
    )
    assert host is not None
    return host


async def update_host(session: AsyncSession, host_id: str, fields: dict[str, Any]) -> Optional[dict[str, Any]]:
    sets, params = _update_payload(
        fields,
        {"name", "role", "address", "transport", "ssh_port", "ssh_user", "credential_ref", "tags", "status",
         "ssh_key_enc"},
    )
    if sets:
        await _exec(session, f"UPDATE backup_hosts SET {sets} WHERE id = :id", {**params, "id": host_id})
    return await get_host(session, host_id)


async def delete_host(session: AsyncSession, host_id: str) -> None:
    await _exec(session, "DELETE FROM backup_hosts WHERE id = :id", {"id": host_id})


async def mark_host_scanned(session: AsyncSession, host_id: str, status: str = "reachable") -> None:
    await _exec(
        session,
        "UPDATE backup_hosts SET status = :status, last_scan_at = now(), last_seen_at = now() WHERE id = :id",
        {"id": host_id, "status": status},
    )


# -------------------------------------------------------------------------- agents

async def get_agent(session: AsyncSession, host_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_agents WHERE host_id = :host_id", {"host_id": host_id})


async def get_agent_by_id(session: AsyncSession, agent_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_agents WHERE id = :id", {"id": agent_id})


async def list_agent_rows(session: AsyncSession) -> list[dict[str, Any]]:
    return await _all(session, "SELECT * FROM backup_agents")


async def upsert_agent(
    session: AsyncSession,
    host_id: str,
    token: str,
    desired_version: Optional[str] = None,
) -> dict[str, Any]:
    row = await _one(
        session,
        """
        INSERT INTO backup_agents (host_id, token_enc, desired_version, status, installed_at)
        VALUES (:host_id, :token_enc, :desired_version, 'pending', now())
        ON CONFLICT (host_id) DO UPDATE
           SET token_enc = EXCLUDED.token_enc,
               desired_version = COALESCE(EXCLUDED.desired_version, backup_agents.desired_version),
               status = 'pending',
               installed_at = now()
        RETURNING *
        """,
        {"host_id": host_id, "token_enc": encrypt(token), "desired_version": desired_version},
    )
    assert row is not None
    return row


async def touch_agent(
    session: AsyncSession,
    agent_id: str,
    *,
    version: Optional[str] = None,
    spool_bytes: Optional[int] = None,
    disk_free: Optional[int] = None,
) -> None:
    await _exec(
        session,
        """
        UPDATE backup_agents
           SET status = 'online',
               last_heartbeat = now(),
               agent_version = COALESCE(:version, agent_version),
               spool_bytes = COALESCE(:spool_bytes, spool_bytes),
               disk_free = COALESCE(:disk_free, disk_free)
         WHERE id = :id
        """,
        {"id": agent_id, "version": version, "spool_bytes": spool_bytes, "disk_free": disk_free},
    )


async def set_agent_status(session: AsyncSession, agent_id: str, status: str) -> None:
    await _exec(session, "UPDATE backup_agents SET status = :status WHERE id = :id", {"id": agent_id, "status": status})


async def set_agent_desired_version(session: AsyncSession, agent_id: str, version: Optional[str]) -> None:
    await _exec(
        session,
        "UPDATE backup_agents SET desired_version = :version WHERE id = :id",
        {"id": agent_id, "version": version},
    )


# ---------------------------------------------------------------------- components

async def list_components(session: AsyncSession, host_id: Optional[str] = None) -> list[dict[str, Any]]:
    if host_id:
        return await _all(
            session, "SELECT * FROM backup_components WHERE host_id = :host_id ORDER BY name", {"host_id": host_id}
        )
    return await _all(session, "SELECT * FROM backup_components ORDER BY host_id, name")


async def upsert_component(
    session: AsyncSession,
    host_id: str,
    *,
    recipe_id: str,
    name: str,
    container_name: Optional[str] = None,
    image: Optional[str] = None,
    image_digest: Optional[str] = None,
    version: Optional[str] = None,
    confidence: str = "high",
    detect_meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    row = await _one(
        session,
        """
        INSERT INTO backup_components
            (host_id, recipe_id, name, container_name, image, image_digest, version, confidence, detect_meta)
        VALUES (:host_id, :recipe_id, :name, :container_name, :image, :image_digest, :version, :confidence, :detect_meta)
        ON CONFLICT (host_id, recipe_id, name) DO UPDATE
           SET container_name = EXCLUDED.container_name,
               image = EXCLUDED.image,
               image_digest = EXCLUDED.image_digest,
               version = EXCLUDED.version,
               confidence = EXCLUDED.confidence,
               detect_meta = EXCLUDED.detect_meta,
               updated_at = now()
        RETURNING *
        """,
        {
            "host_id": host_id,
            "recipe_id": recipe_id,
            "name": name,
            "container_name": container_name,
            "image": image,
            "image_digest": image_digest,
            "version": version,
            "confidence": confidence,
            "detect_meta": _json(detect_meta or {}),
        },
    )
    assert row is not None
    return row


async def get_component(session: AsyncSession, component_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_components WHERE id = :id", {"id": component_id})


async def update_component(session: AsyncSession, component_id: str, fields: dict[str, Any]) -> Optional[dict[str, Any]]:
    sets, params = _update_payload(fields, {"enabled", "confidence"})
    if sets:
        await _exec(session, f"UPDATE backup_components SET {sets}, updated_at = now() WHERE id = :id",
                    {**params, "id": component_id})
    return await get_component(session, component_id)


# ------------------------------------------------------------------------ storages

_STORAGE_PUBLIC = """
SELECT id, name, kind, config, advanced, enabled, is_default, quota_bytes, used_bytes,
       last_check_at, last_check_ok, created_at,
       (secrets IS NOT NULL AND secrets <> '') AS has_secret
FROM backup_storages
"""


async def list_storages(session: AsyncSession) -> list[dict[str, Any]]:
    return await _all(session, _STORAGE_PUBLIC + " ORDER BY is_default DESC, name")


async def get_storage_public(session: AsyncSession, storage_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, _STORAGE_PUBLIC + " WHERE id = :id", {"id": storage_id})


async def get_storage_raw(session: AsyncSession, storage_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_storages WHERE id = :id", {"id": storage_id})


async def list_storages_raw(session: AsyncSession, enabled_only: bool = True) -> list[dict[str, Any]]:
    where = " WHERE enabled" if enabled_only else ""
    return await _all(session, "SELECT * FROM backup_storages" + where + " ORDER BY is_default DESC, name")


async def create_storage(session: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    secret = data.pop("secret", None)
    row = await _one(
        session,
        """
        INSERT INTO backup_storages (name, kind, config, advanced, secrets, enabled, is_default, quota_bytes)
        VALUES (:name, :kind, :config, :advanced, :secrets, :enabled, :is_default, :quota_bytes)
        RETURNING id
        """,
        {
            "name": data["name"],
            "kind": data["kind"],
            "config": _json(data.get("config") or {}),
            "advanced": _json(data.get("advanced") or {}),
            "secrets": encrypt(_json(secret)) if secret else None,
            "enabled": data.get("enabled", True),
            "is_default": data.get("is_default", False),
            "quota_bytes": data.get("quota_bytes"),
        },
    )
    assert row is not None
    if data.get("is_default"):
        await _exec(session, "UPDATE backup_storages SET is_default = false WHERE id <> :id", {"id": row["id"]})
    return row


async def update_storage(session: AsyncSession, storage_id: str, fields: dict[str, Any]) -> None:
    secret = fields.pop("secret", None)
    sets, params = _update_payload(
        fields, {"name", "kind", "config", "advanced", "enabled", "is_default", "quota_bytes"}
    )
    if secret is not None:
        sets = (sets + ", " if sets else "") + "secrets = :secrets"
        params["secrets"] = encrypt(_json(secret))
    if sets:
        await _exec(session, f"UPDATE backup_storages SET {sets} WHERE id = :id", {**params, "id": storage_id})
    if fields.get("is_default") is True:
        await _exec(session, "UPDATE backup_storages SET is_default = false WHERE id <> :id", {"id": storage_id})


async def delete_storage(session: AsyncSession, storage_id: str) -> None:
    await _exec(session, "DELETE FROM backup_storages WHERE id = :id", {"id": storage_id})


async def enabled_storage_ids(session: AsyncSession) -> list[str]:
    rows = await _all(
        session,
        "SELECT id FROM backup_storages WHERE enabled ORDER BY is_default DESC, name",
    )
    return [str(row["id"]) for row in rows]


async def mark_storage_tested(session: AsyncSession, storage_id: str, ok: bool, used_bytes: Optional[int] = None) -> None:    await _exec(
        session,
        """
        UPDATE backup_storages
           SET last_check_at = now(), last_check_ok = :ok,
               used_bytes = COALESCE(:used_bytes, used_bytes)
         WHERE id = :id
        """,
        {"id": storage_id, "ok": ok, "used_bytes": used_bytes},
    )


# ------------------------------------------------------------------------ policies

async def list_policies(session: AsyncSession, host_id: Optional[str] = None) -> list[dict[str, Any]]:
    if host_id:
        return await _all(session, "SELECT * FROM backup_policies WHERE host_id = :host_id ORDER BY created_at",
                          {"host_id": host_id})
    return await _all(session, "SELECT * FROM backup_policies ORDER BY created_at")


async def get_policy(session: AsyncSession, policy_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_policies WHERE id = :id", {"id": policy_id})


async def create_policy(session: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    row = await _one(
        session,
        """
        INSERT INTO backup_policies (name, host_id, timezone, enabled, created_by)
        VALUES (:name, :host_id, :timezone, :enabled, :created_by)
        RETURNING *
        """,
        {
            "name": data["name"],
            "host_id": data["host_id"],
            "timezone": data.get("timezone", "Europe/Moscow"),
            "enabled": data.get("enabled", True),
            "created_by": data.get("created_by"),
        },
    )
    assert row is not None
    return row


async def update_policy(session: AsyncSession, policy_id: str, fields: dict[str, Any]) -> Optional[dict[str, Any]]:
    sets, params = _update_payload(fields, {"name", "timezone", "enabled"})
    if sets:
        await _exec(session, f"UPDATE backup_policies SET {sets} WHERE id = :id", {**params, "id": policy_id})
    return await get_policy(session, policy_id)


async def delete_policy(session: AsyncSession, policy_id: str) -> None:
    await _exec(session, "DELETE FROM backup_policies WHERE id = :id", {"id": policy_id})


# --------------------------------------------------------------------------- tiers

_TIER_FIELDS = {
    "name", "position", "scope", "component_ids", "schedule_kind", "cron", "interval_minutes",
    "retention_mode", "retention_copies", "retention_days", "min_copies", "storage_ids",
    "encrypt", "include_logs", "consistency", "enabled", "next_run_at",
}


async def list_tiers(session: AsyncSession, policy_id: str) -> list[dict[str, Any]]:
    return await _all(session, "SELECT * FROM backup_tiers WHERE policy_id = :policy_id ORDER BY position",
                      {"policy_id": policy_id})


async def get_tier(session: AsyncSession, tier_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_tiers WHERE id = :id", {"id": tier_id})


async def create_tier(session: AsyncSession, policy_id: str, data: dict[str, Any]) -> dict[str, Any]:
    fields = {k: data.get(k) for k in _TIER_FIELDS if k in data}
    fields["policy_id"] = policy_id
    columns = ", ".join(fields)
    values = ", ".join(f":{k}" for k in fields)
    params = {k: (_json(v) if k in JSON_FIELDS else v) for k, v in fields.items()}
    row = await _one(
        session,
        f"INSERT INTO backup_tiers ({columns}) VALUES ({values}) RETURNING *",
        params,
    )
    assert row is not None
    return row


async def update_tier(session: AsyncSession, tier_id: str, fields: dict[str, Any]) -> Optional[dict[str, Any]]:
    sets, params = _update_payload(fields, _TIER_FIELDS)
    if sets:
        await _exec(session, f"UPDATE backup_tiers SET {sets} WHERE id = :id", {**params, "id": tier_id})
    return await get_tier(session, tier_id)


async def delete_tier(session: AsyncSession, tier_id: str) -> None:
    await _exec(session, "DELETE FROM backup_tiers WHERE id = :id", {"id": tier_id})


async def due_tiers(session: AsyncSession, limit: int = 50) -> list[dict[str, Any]]:
    return await _all(
        session,
        """
        SELECT t.*, p.host_id AS policy_host_id, p.timezone, p.enabled AS policy_enabled
          FROM backup_tiers t
          JOIN backup_policies p ON p.id = t.policy_id
         WHERE t.enabled AND p.enabled
           AND (t.next_run_at IS NULL OR t.next_run_at <= now())
         ORDER BY t.next_run_at NULLS FIRST
         LIMIT :limit
        """,
        {"limit": limit},
    )


async def set_tier_next_run(session: AsyncSession, tier_id: str, next_run_at: datetime) -> None:
    await _exec(session, "UPDATE backup_tiers SET next_run_at = :next WHERE id = :id",
                {"id": tier_id, "next": next_run_at})


# ---------------------------------------------------------------------------- runs

async def create_run(
    session: AsyncSession,
    *,
    host_id: str,
    tier_id: Optional[str] = None,
    policy_id: Optional[str] = None,
    kind: str = "backup",
    trigger: str = "manual",
    artifact_scope: Optional[str] = None,
    client_run_id: Optional[str] = None,
    consistency_group: Optional[str] = None,
    agent_id: Optional[str] = None,
    steps: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    row = await _one(
        session,
        """
        INSERT INTO backup_runs
            (host_id, tier_id, policy_id, kind, "trigger", artifact_scope, client_run_id,
             consistency_group, agent_id, status, progress, steps, started_at)
        VALUES
            (:host_id, :tier_id, :policy_id, :kind, :trigger, :artifact_scope, :client_run_id,
             :consistency_group, :agent_id, 'queued', 0, :steps, now())
        RETURNING *
        """,
        {
            "host_id": host_id,
            "tier_id": tier_id,
            "policy_id": policy_id,
            "kind": kind,
            "trigger": trigger,
            "artifact_scope": artifact_scope,
            "client_run_id": client_run_id,
            "consistency_group": consistency_group,
            "agent_id": agent_id,
            "steps": _json(steps or []),
        },
    )
    assert row is not None
    return row


async def get_run(session: AsyncSession, run_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_runs WHERE id = :id", {"id": run_id})


async def get_run_by_client_id(session: AsyncSession, client_run_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_runs WHERE client_run_id = :cid", {"cid": client_run_id})


async def list_runs(
    session: AsyncSession,
    *,
    host_id: Optional[str] = None,
    status: Optional[str] = None,
    kind: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    clauses = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if host_id:
        clauses.append("host_id = :host_id")
        params["host_id"] = host_id
    if status:
        clauses.append("status = :status")
        params["status"] = status
    if kind:
        clauses.append("kind = :kind")
        params["kind"] = kind
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return await _all(
        session,
        f"SELECT * FROM backup_runs{where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset",
        params,
    )


async def update_run(session: AsyncSession, run_id: str, fields: dict[str, Any]) -> None:
    sets, params = _update_payload(
        fields,
        {"status", "progress", "steps", "error", "size_bytes", "artifact_scope", "finished_at", "started_at",
         "cancel_requested"},
    )
    if sets:
        await _exec(session, f"UPDATE backup_runs SET {sets} WHERE id = :id", {**params, "id": run_id})


async def append_run_log(session: AsyncSession, run_id: str, chunk: str, limit: int = 512_000) -> None:
    if not chunk:
        return
    await _exec(
        session,
        """
        UPDATE backup_runs
           SET log = right(COALESCE(log, '') || :chunk, :limit)
         WHERE id = :id
        """,
        {"id": run_id, "chunk": chunk, "limit": limit},
    )


async def request_cancel(session: AsyncSession, run_id: str) -> None:
    await _exec(session, "UPDATE backup_runs SET cancel_requested = true WHERE id = :id", {"id": run_id})


async def last_successful_run(session: AsyncSession, host_id: str, scope: Optional[str] = None) -> Optional[dict[str, Any]]:
    params: dict[str, Any] = {"host_id": host_id}
    scope_clause = ""
    if scope:
        scope_clause = " AND artifact_scope = :scope"
        params["scope"] = scope
    return await _one(
        session,
        f"""
        SELECT * FROM backup_runs
         WHERE host_id = :host_id AND status = 'success'{scope_clause}
         ORDER BY finished_at DESC NULLS LAST
         LIMIT 1
        """,
        params,
    )


# ------------------------------------------------------------------------ commands

async def enqueue_command(
    session: AsyncSession,
    host_id: str,
    command_type: str,
    payload: Optional[dict[str, Any]] = None,
    created_by: Optional[str] = None,
) -> dict[str, Any]:
    row = await _one(
        session,
        """
        INSERT INTO backup_commands (host_id, type, payload, created_by)
        VALUES (:host_id, :type, :payload, :created_by)
        RETURNING *
        """,
        {"host_id": host_id, "type": command_type, "payload": _json(payload or {}), "created_by": created_by},
    )
    assert row is not None
    return row


async def take_commands(session: AsyncSession, host_id: str, limit: int = 10) -> list[dict[str, Any]]:
    rows = await _all(
        session,
        """
        WITH picked AS (
            SELECT id FROM backup_commands
             WHERE host_id = :host_id AND status = 'queued' AND expires_at > now()
             ORDER BY created_at
             LIMIT :limit
             FOR UPDATE SKIP LOCKED
        )
        UPDATE backup_commands c
           SET status = 'taken'
          FROM picked
         WHERE c.id = picked.id
        RETURNING c.*
        """,
        {"host_id": host_id, "limit": limit},
    )
    return rows


async def finish_command(session: AsyncSession, command_id: str, status: str = "done") -> None:
    await _exec(session, "UPDATE backup_commands SET status = :status WHERE id = :id",
                {"id": command_id, "status": status})


async def expire_commands(session: AsyncSession) -> None:
    await _exec(session, "UPDATE backup_commands SET status = 'expired' WHERE status = 'queued' AND expires_at <= now()")


# ----------------------------------------------------------------------- artifacts

async def create_artifact(session: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    row = await _one(
        session,
        """
        INSERT INTO backup_artifacts
            (run_id, component_id, storage_id, artifact_type, object_key, size_bytes, sha256, encrypted, manifest, expires_at)
        VALUES
            (:run_id, :component_id, :storage_id, :artifact_type, :object_key, :size_bytes, :sha256, :encrypted,
             :manifest, :expires_at)
        RETURNING *
        """,
        {
            "run_id": data["run_id"],
            "component_id": data.get("component_id"),
            "storage_id": data.get("storage_id"),
            "artifact_type": data["artifact_type"],
            "object_key": data["object_key"],
            "size_bytes": data.get("size_bytes"),
            "sha256": data.get("sha256"),
            "encrypted": data.get("encrypted", True),
            "manifest": _json(data.get("manifest") or {}),
            "expires_at": data.get("expires_at"),
        },
    )
    assert row is not None
    return row


async def list_artifacts(
    session: AsyncSession,
    *,
    host_id: Optional[str] = None,
    run_id: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    clauses = []
    params: dict[str, Any] = {"limit": limit}
    if host_id:
        clauses.append("r.host_id = :host_id")
        params["host_id"] = host_id
    if run_id:
        clauses.append("a.run_id = :run_id")
        params["run_id"] = run_id
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return await _all(
        session,
        f"""
        SELECT a.*, r.host_id, r.kind AS run_kind
          FROM backup_artifacts a
          JOIN backup_runs r ON r.id = a.run_id
          {where}
         ORDER BY a.created_at DESC
         LIMIT :limit
        """,
        params,
    )


async def get_artifact(session: AsyncSession, artifact_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_artifacts WHERE id = :id", {"id": artifact_id})


async def delete_artifact(session: AsyncSession, artifact_id: str) -> None:
    await _exec(session, "DELETE FROM backup_artifacts WHERE id = :id", {"id": artifact_id})


async def expired_artifacts(session: AsyncSession, limit: int = 200) -> list[dict[str, Any]]:
    return await _all(
        session,
        "SELECT * FROM backup_artifacts WHERE expires_at IS NOT NULL AND expires_at <= now() LIMIT :limit",
        {"limit": limit},
    )


async def artifacts_for_group(session: AsyncSession, group_key: str) -> list[dict[str, Any]]:
    return await _all(
        session,
        """
        SELECT a.*, r.consistency_group, r.host_id, r.kind AS run_kind, r.finished_at
          FROM backup_artifacts a
          JOIN backup_runs r ON r.id = a.run_id
         WHERE r.consistency_group = :group_key AND r.status = 'success'
         ORDER BY a.created_at
        """,
        {"group_key": group_key},
    )


# ------------------------------------------------------------------------ restores

async def create_restore(session: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    row = await _one(
        session,
        """
        INSERT INTO backup_restores (group_key, target_host_id, target_kind, plan, plan_token, created_by)
        VALUES (:group_key, :target_host_id, :target_kind, :plan, :plan_token, :created_by)
        RETURNING *
        """,
        {
            "group_key": data.get("group_key"),
            "target_host_id": data.get("target_host_id"),
            "target_kind": data.get("target_kind", "same"),
            "plan": _json(data.get("plan") or {}),
            "plan_token": data.get("plan_token"),
            "created_by": data.get("created_by"),
        },
    )
    assert row is not None
    return row


async def get_restore(session: AsyncSession, restore_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_restores WHERE id = :id", {"id": restore_id})


async def get_restore_by_token(session: AsyncSession, plan_token: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_restores WHERE plan_token = :token", {"token": plan_token})


async def list_restores(session: AsyncSession, limit: int = 50) -> list[dict[str, Any]]:
    return await _all(session, "SELECT * FROM backup_restores ORDER BY created_at DESC LIMIT :limit", {"limit": limit})


async def update_restore(session: AsyncSession, restore_id: str, fields: dict[str, Any]) -> None:
    sets, params = _update_payload(fields, {"status", "error", "started_at", "finished_at", "pre_snapshot_run_id"})
    if sets:
        await _exec(session, f"UPDATE backup_restores SET {sets} WHERE id = :id", {**params, "id": restore_id})


# ------------------------------------------------------------------- notifications

_CHANNEL_PUBLIC = """
SELECT id, name, kind, config, enabled, last_check_at, last_check_ok, created_at,
       (secrets IS NOT NULL AND secrets <> '') AS has_secret
FROM backup_notification_channels
"""


async def list_channels(session: AsyncSession) -> list[dict[str, Any]]:
    return await _all(session, _CHANNEL_PUBLIC + " ORDER BY name")


async def get_channel_public(session: AsyncSession, channel_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, _CHANNEL_PUBLIC + " WHERE id = :id", {"id": channel_id})


async def get_channel_raw(session: AsyncSession, channel_id: str) -> Optional[dict[str, Any]]:
    return await _one(session, "SELECT * FROM backup_notification_channels WHERE id = :id", {"id": channel_id})


async def create_channel(session: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    secret = data.pop("secret", None)
    row = await _one(
        session,
        """
        INSERT INTO backup_notification_channels (name, kind, config, secrets, enabled)
        VALUES (:name, :kind, :config, :secrets, :enabled)
        RETURNING id
        """,
        {
            "name": data["name"],
            "kind": data["kind"],
            "config": _json(data.get("config") or {}),
            "secrets": encrypt(_json(secret)) if secret else None,
            "enabled": data.get("enabled", True),
        },
    )
    assert row is not None
    return row


async def update_channel(session: AsyncSession, channel_id: str, fields: dict[str, Any]) -> None:
    secret = fields.pop("secret", None)
    sets, params = _update_payload(fields, {"name", "kind", "config", "enabled"})
    if secret is not None:
        sets = (sets + ", " if sets else "") + "secrets = :secrets"
        params["secrets"] = encrypt(_json(secret))
    if sets:
        await _exec(session,
                    f"UPDATE backup_notification_channels SET {sets} WHERE id = :id",
                    {**params, "id": channel_id})


async def delete_channel(session: AsyncSession, channel_id: str) -> None:
    await _exec(session, "DELETE FROM backup_notification_channels WHERE id = :id", {"id": channel_id})


async def mark_channel_tested(session: AsyncSession, channel_id: str, ok: bool) -> None:
    await _exec(session,
                "UPDATE backup_notification_channels SET last_check_at = now(), last_check_ok = :ok WHERE id = :id",
                {"id": channel_id, "ok": ok})


async def list_rules(session: AsyncSession, event: Optional[str] = None) -> list[dict[str, Any]]:
    if event:
        return await _all(session, "SELECT * FROM backup_notification_rules WHERE event = :event ORDER BY created_at",
                          {"event": event})
    return await _all(session, "SELECT * FROM backup_notification_rules ORDER BY created_at")


async def create_rule(session: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
    row = await _one(
        session,
        """
        INSERT INTO backup_notification_rules
            (name, event, host_id, policy_id, channel_ids, threshold, quiet_hours, repeat_every_min, severity, enabled)
        VALUES
            (:name, :event, :host_id, :policy_id, :channel_ids, :threshold, :quiet_hours, :repeat_every_min,
             :severity, :enabled)
        RETURNING *
        """,
        {
            "name": data["name"],
            "event": data["event"],
            "host_id": data.get("host_id"),
            "policy_id": data.get("policy_id"),
            "channel_ids": _json(data.get("channel_ids") or []),
            "threshold": _json(data.get("threshold") or {}),
            "quiet_hours": data.get("quiet_hours"),
            "repeat_every_min": data.get("repeat_every_min"),
            "severity": data.get("severity", "warning"),
            "enabled": data.get("enabled", True),
        },
    )
    assert row is not None
    return row


async def update_rule(session: AsyncSession, rule_id: str, fields: dict[str, Any]) -> Optional[dict[str, Any]]:
    sets, params = _update_payload(
        fields,
        {"name", "event", "host_id", "policy_id", "channel_ids", "threshold", "quiet_hours",
         "repeat_every_min", "severity", "enabled"},
    )
    if sets:
        await _exec(session, f"UPDATE backup_notification_rules SET {sets} WHERE id = :id", {**params, "id": rule_id})
    return await _one(session, "SELECT * FROM backup_notification_rules WHERE id = :id", {"id": rule_id})


async def delete_rule(session: AsyncSession, rule_id: str) -> None:
    await _exec(session, "DELETE FROM backup_notification_rules WHERE id = :id", {"id": rule_id})


# ------------------------------------------------------------------------- settings

async def get_settings(session: AsyncSession) -> dict[str, Any]:
    rows = await _all(session, "SELECT setting_key, setting_value, is_secret FROM backup_settings")
    result: dict[str, Any] = {}
    for row in rows:
        value: Any = row.get("setting_value")
        try:
            value = json.loads(value) if value is not None else None
        except (TypeError, json.JSONDecodeError):
            pass
        result[row["setting_key"]] = "***" if row.get("is_secret") and value else value
    return result


async def put_settings(session: AsyncSession, values: dict[str, Any], secret_keys: set[str] | None = None) -> None:
    secret_keys = secret_keys or set()
    for key, value in values.items():
        is_secret = key in secret_keys
        raw = encrypt(_json(value)) if is_secret else _json(value)
        await _exec(
            session,
            """
            INSERT INTO backup_settings (setting_key, setting_value, is_secret)
            VALUES (:key, :value, :is_secret)
            ON CONFLICT (setting_key) DO UPDATE
               SET setting_value = EXCLUDED.setting_value,
                   is_secret = EXCLUDED.is_secret,
                   updated_at = now()
            """,
            {"key": key, "value": raw, "is_secret": is_secret},
        )


# ------------------------------------------------------------------------- overview

async def overview_counts(session: AsyncSession) -> dict[str, Any]:
    row = await _one(
        session,
        """
        SELECT
          (SELECT count(*) FROM backup_hosts) AS hosts_total,
          (SELECT count(*) FROM backup_hosts WHERE status = 'unreachable') AS hosts_unreachable,
          (SELECT count(*) FROM backup_agents WHERE status = 'online') AS agents_online,
          (SELECT count(*) FROM backup_agents WHERE status <> 'online') AS agents_offline,
          (SELECT count(*) FROM backup_storages) AS storages_total,
          (SELECT count(*) FROM backup_storages WHERE last_check_ok = false) AS storages_error,
          (SELECT count(*) FROM backup_policies) AS policies_total,
          (SELECT coalesce(sum(size_bytes), 0) FROM backup_artifacts) AS total_bytes,
          (SELECT max(finished_at) FROM backup_runs WHERE status = 'success') AS last_success_at,
          (SELECT max(finished_at) FROM backup_runs WHERE status = 'success' AND artifact_scope = 'database')
              AS last_db_backup_at,
          (SELECT max(finished_at) FROM backup_runs WHERE status = 'success' AND artifact_scope = 'full')
              AS last_full_backup_at
        """
    )
    return row or {}


async def attention_runs(session: AsyncSession, limit: int = 10) -> list[dict[str, Any]]:
    return await _all(
        session,
        """
        SELECT id, host_id, status, error, finished_at, created_at
          FROM backup_runs
         WHERE status = 'failed'
         ORDER BY created_at DESC
         LIMIT :limit
        """,
        {"limit": limit},
    )


async def hosts_without_recent_success(session: AsyncSession, hours: int) -> list[dict[str, Any]]:
    return await _all(
        session,
        """
        SELECT h.id, h.name, max(r.finished_at) AS last_success_at
          FROM backup_hosts h
          LEFT JOIN backup_runs r ON r.host_id = h.id AND r.status = 'success'
         GROUP BY h.id, h.name
        HAVING max(r.finished_at) IS NULL OR max(r.finished_at) < now() - make_interval(hours => :hours)
        """,
        {"hours": hours},
    )
