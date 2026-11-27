"""Agent-facing API (mounted at ``/api/backup-agent/v1``).

Auth: ``Authorization: Bearer <token>`` where the token is stored encrypted in
``backup_agents.token_enc``. The CMS keeps only the ciphertext.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.backup import recipes as recipes_mod
from web.backend.core.backup import repository as repo
from web.backend.core.backup.storage import get_storage
from web.backend.core.crypto import decrypt
from web.backend.core.database import get_db
from web.backend.schemas.backup import (
    AgentHeartbeat,
    AgentInventory,
    AgentRegister,
    AgentRegisterResult,
    AgentRunUpdate,
)

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_INSTALL_SCRIPTS = (
    _PROJECT_ROOT / "backup-agent" / "install.sh",
    Path("/var/www/html/backup-agent/install.sh"),
)


def _install_script_path() -> Optional[Path]:
    for candidate in _INSTALL_SCRIPTS:
        if candidate.is_file():
            return candidate
    return None


def _image_tarball_path() -> Optional[Path]:
    """Optional pre-built agent image (`docker save`) served to nodes."""
    candidates = [
        Path(os.environ["AGENT_IMAGE_TARBALL_PATH"]) if os.environ.get("AGENT_IMAGE_TARBALL_PATH") else None,
        _PROJECT_ROOT / "backup-agent" / "agent-image.tar",
        Path("/var/www/html/backup-agent/agent-image.tar"),
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    return None


def _unauthorized(reason: str = "invalid agent token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"success": False, "error": reason},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized("missing bearer token")
    return authorization.split(" ", 1)[1].strip()


async def _find_agent(db: AsyncSession, token: str) -> dict[str, Any]:
    for row in await repo.list_agent_rows(db):
        stored = decrypt(row.get("token_enc") or "")
        if stored and hmac.compare_digest(stored, token):
            return row
    raise _unauthorized()


async def get_agent(
    db: DbSession,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    return await _find_agent(db, _bearer(authorization))


AgentRow = Annotated[dict[str, Any], Depends(get_agent)]


# ------------------------------------------------------------------- install/register

@router.get("/install.sh", response_class=PlainTextResponse)
async def install_script():
    script = _install_script_path()
    if script is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"success": False, "error": "install.sh не найден в образе API (каталог backup-agent отсутствует)"},
        )
    return PlainTextResponse(script.read_text(encoding="utf-8"), media_type="text/x-shellscript")


@router.get("/image")
async def agent_image():
    """Serve a pre-built agent image archive so nodes can install without a registry."""
    tarball = _image_tarball_path()
    if tarball is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": "образ агента не опубликован: выполните docker save и положите файл в "
                "backup-agent/agent-image.tar (или задайте AGENT_IMAGE_TARBALL_PATH)",
            },
        )
    return FileResponse(
        str(tarball),
        media_type="application/gzip",
        filename="hexaveil-backup-agent.tar",
    )


@router.post("/register")
async def register(payload: AgentRegister, db: DbSession):
    host = await repo.get_host(db, payload.host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"success": False, "error": "host not found"})

    agent = await _find_agent(db, payload.token)
    if agent["host_id"] != payload.host_id:
        raise _unauthorized("token does not belong to host")

    await repo.touch_agent(db, str(agent["id"]), version=payload.agent_version)
    await repo.set_agent_status(db, str(agent["id"]), "online")
    await repo.mark_host_scanned(db, payload.host_id, status="reachable")
    await db.commit()

    result = AgentRegisterResult(agent_id=str(agent["id"]), host_id=payload.host_id)
    return {"success": True, "data": result.model_dump()}


@router.post("/heartbeat")
async def heartbeat(payload: AgentHeartbeat, agent: AgentRow, db: DbSession):
    await repo.touch_agent(
        db,
        str(agent["id"]),
        version=payload.agent_version,
        spool_bytes=payload.spool_bytes,
        disk_free=payload.disk_free,
    )
    await db.commit()
    return {"success": True, "data": {"desired_version": agent.get("desired_version")}}


# ---------------------------------------------------------------------------- state

def _serialize_recipes() -> list[dict[str, Any]]:
    return [recipe.model_dump() for recipe in recipes_mod.list_recipes()]


async def _policies_for_host(db: AsyncSession, host_id: str) -> list[dict[str, Any]]:
    default_storages = await repo.enabled_storage_ids(db)
    result: list[dict[str, Any]] = []
    for policy in await repo.list_policies(db, host_id=host_id):
        tiers = await repo.list_tiers(db, str(policy["id"]))
        result.append(
            {
                "id": policy["id"],
                "name": policy["name"],
                "timezone": policy["timezone"],
                "enabled": policy["enabled"],
                "tiers": [
                    {
                        "id": tier["id"],
                        "name": tier["name"],
                        "scope": tier["scope"],
                        "component_ids": tier.get("component_ids") or [],
                        "schedule_kind": tier["schedule_kind"],
                        "cron": tier.get("cron"),
                        "interval_minutes": tier.get("interval_minutes"),
                        "retention_mode": tier.get("retention_mode"),
                        "retention_copies": tier.get("retention_copies"),
                        "retention_days": tier.get("retention_days"),
                        "storage_ids": tier.get("storage_ids") or default_storages,
                        "encrypt": tier.get("encrypt", True),
                        "include_logs": tier.get("include_logs", False),
                        "enabled": tier.get("enabled", True),
                    }
                    for tier in tiers
                ],
            }
        )
    return result


@router.get("/state")
async def get_state(
    agent: AgentRow,
    db: DbSession,
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
):
    components = await repo.list_components(db, host_id=str(agent["host_id"]))
    payload = {
        "version": "1",
        "desired_version": agent.get("desired_version"),
        "recipes": _serialize_recipes(),
        "components": [
            {
                "id": c["id"],
                "recipe_id": c["recipe_id"],
                "name": c["name"],
                "container_name": c.get("container_name"),
                "enabled": c.get("enabled", True),
            }
            for c in components
        ],
        "policies": await _policies_for_host(db, str(agent["host_id"])),
        "agent_settings": {
            "heartbeat_interval": 30,
            "poll_interval": 15,
            "concurrency": 1,
        },
    }
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    etag = '"' + hashlib.sha256(body.encode()).hexdigest()[:32] + '"'
    if if_none_match and if_none_match.strip() == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})
    return Response(
        content=body,
        media_type="application/json",
        headers={"ETag": etag, "Cache-Control": "no-store"},
    )


# ------------------------------------------------------------------------ inventory

@router.post("/inventory")
async def post_inventory(payload: AgentInventory, agent: AgentRow, db: DbSession):
    host = await repo.get_host(db, str(agent["host_id"]))
    if not host:
        raise _unauthorized("host not found")

    inventory = payload.model_dump()
    matched = recipes_mod.match_all(inventory, host_role=str(host.get("role") or "server"))

    saved = []
    for component in matched:
        row = await repo.upsert_component(
            db,
            host_id=str(host["id"]),
            recipe_id=component.recipe_id,
            name=component.name,
            container_name=component.container_name,
            image=component.image,
            image_digest=component.image_digest,
            version=component.version,
            confidence=component.confidence,
            detect_meta=component.detect_meta,
        )
        saved.append(row)

    await repo.mark_host_scanned(db, str(host["id"]), status="reachable")
    await repo.touch_agent(db, str(agent["id"]), version=agent.get("agent_version"))
    await db.commit()
    return {"success": True, "data": {"components": saved, "matched": len(saved)}}


# ----------------------------------------------------------------------------- runs

@router.post("/runs", status_code=201)
async def create_agent_run(payload: dict[str, Any], agent: AgentRow, db: DbSession):
    client_run_id = payload.get("client_run_id")
    if client_run_id:
        existing = await repo.get_run_by_client_id(db, str(client_run_id))
        if existing:
            return {"success": True, "data": existing}

    run = await repo.create_run(
        db,
        host_id=str(agent["host_id"]),
        tier_id=payload.get("tier_id"),
        kind=payload.get("kind", "backup"),
        trigger=payload.get("trigger", "schedule"),
        artifact_scope=payload.get("scope"),
        client_run_id=client_run_id,
        consistency_group=payload.get("consistency_group"),
        agent_id=str(agent["id"]),
        steps=payload.get("steps") or [],
    )
    await repo.update_run(db, str(run["id"]), {"status": "running"})
    await db.commit()
    return {"success": True, "data": run}


@router.patch("/runs/{run_id}")
async def update_agent_run(run_id: str, payload: AgentRunUpdate, agent: AgentRow, db: DbSession):
    run = await repo.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"success": False, "error": "run not found"})
    if str(run.get("host_id")) != str(agent["host_id"]):
        raise _unauthorized("run belongs to another host")

    if run.get("cancel_requested") and payload.status not in ("cancelled",):
        return {"success": True, "data": {**run, "cancel_requested": True, "status": "cancelled"}}

    fields: dict[str, Any] = {}
    if payload.status:
        fields["status"] = payload.status
    if payload.progress is not None:
        fields["progress"] = max(0, min(100, int(payload.progress)))
    if payload.steps is not None:
        fields["steps"] = payload.steps
    if payload.error:
        fields["error"] = payload.error
    if payload.finished:
        fields["finished_at"] = datetime.now(timezone.utc)
        if not payload.status:
            fields["status"] = "success"
    if fields:
        await repo.update_run(db, run_id, fields)
    if payload.log_append:
        await repo.append_run_log(db, run_id, payload.log_append)
    await db.commit()

    updated = await repo.get_run(db, run_id)
    return {"success": True, "data": updated}


# ------------------------------------------------------------------------ artifacts

@router.post("/runs/{run_id}/artifacts")
async def register_artifact(run_id: str, payload: dict[str, Any], agent: AgentRow, db: DbSession):
    run = await repo.get_run(db, run_id)
    if not run or str(run.get("host_id")) != str(agent["host_id"]):
        raise HTTPException(status_code=404, detail={"success": False, "error": "run not found"})

    artifact = await repo.create_artifact(
        db,
        {
            "run_id": run_id,
            "component_id": payload.get("component_id"),
            "storage_id": payload.get("storage_id"),
            "artifact_type": payload.get("artifact_type", "files"),
            "object_key": payload.get("object_key"),
            "size_bytes": payload.get("size_bytes"),
            "sha256": (payload.get("sha256") or "").lower() or None,
            "encrypted": bool(payload.get("encrypted", True)),
            "manifest": payload.get("manifest") or {},
            "expires_at": payload.get("expires_at"),
        },
    )
    await db.commit()
    return {
        "success": True,
        "data": {
            **artifact,
            "upload_url": f"/api/backup-agent/v1/upload/{artifact['id']}",
        },
    }


@router.put("/upload/{artifact_id}")
async def upload_artifact(artifact_id: str, request: Request, agent: AgentRow, db: DbSession):
    artifact = await repo.get_artifact(db, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail={"success": False, "error": "artifact not found"})
    if not artifact.get("storage_id"):
        raise HTTPException(status_code=400, detail={"success": False, "error": "artifact has no storage"})

    storage_row = await repo.get_storage_raw(db, str(artifact["storage_id"]))
    if not storage_row:
        raise HTTPException(status_code=400, detail={"success": False, "error": "storage not found"})
    storage = get_storage(storage_row)

    digest = hashlib.sha256()
    size = 0

    async def _stream():
        nonlocal size
        async for chunk in request.stream():
            if not chunk:
                continue
            digest.update(chunk)
            size += len(chunk)
            yield chunk

    await storage.put(str(artifact["object_key"]), _stream())

    expected = (artifact.get("sha256") or "").lower()
    if expected and digest.hexdigest() != expected:
        try:
            await storage.delete(str(artifact["object_key"]))
        except Exception:  # noqa: BLE001
            pass
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "sha256 mismatch", "expected": expected, "actual": digest.hexdigest()},
        )

    await db.execute(
        text(
            "UPDATE backup_artifacts SET size_bytes = :size, sha256 = :sha WHERE id = :id"
        ),
        {"id": artifact_id, "size": size, "sha": digest.hexdigest()},
    )
    await db.commit()
    return {"success": True, "data": {"size_bytes": size, "sha256": digest.hexdigest()}}


@router.get("/download/{artifact_id}")
async def agent_download_artifact(artifact_id: str, agent: AgentRow, db: DbSession):
    artifact = await repo.get_artifact(db, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail={"success": False, "error": "artifact not found"})
    if not artifact.get("storage_id"):
        raise HTTPException(status_code=400, detail={"success": False, "error": "artifact has no storage"})
    storage_row = await repo.get_storage_raw(db, str(artifact["storage_id"]))
    if not storage_row:
        raise HTTPException(status_code=400, detail={"success": False, "error": "storage not found"})
    storage = get_storage(storage_row)

    async def _stream():
        async for chunk in storage.get(str(artifact["object_key"])):
            yield chunk

    return StreamingResponse(_stream(), media_type="application/octet-stream")


# ------------------------------------------------------------------------- commands

@router.get("/commands")
async def poll_commands(agent: AgentRow, db: DbSession, limit: int = Query(10, ge=1, le=50)):
    commands = await repo.take_commands(db, str(agent["host_id"]), limit=limit)
    await db.commit()
    return {"success": True, "data": commands}


@router.post("/commands/{command_id}/finish")
async def finish_command(command_id: str, payload: dict[str, Any], agent: AgentRow, db: DbSession):
    await repo.finish_command(db, command_id, payload.get("status", "done"))
    await db.commit()
    return {"success": True}
