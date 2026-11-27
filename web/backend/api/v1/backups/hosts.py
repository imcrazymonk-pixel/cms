"""Backup hosts: CRUD, diagnostics, agent installation."""
from __future__ import annotations

import asyncio
import secrets

from fastapi import APIRouter, Query, Request

from web.backend.core.backup import recipes as recipes_mod
from web.backend.core.backup import repository as repo
from web.backend.core.config import get_cms_settings
from web.backend.core.crypto import decrypt, encrypt
from web.backend.schemas.backup import (
    AgentInstall,
    Host,
    HostCreate,
    HostTestResult,
    HostUpdate,
)

from .common import CurrentAdmin, DbSession, bad_request, commit, not_found

router = APIRouter()


def _public_base(request: Request) -> str:
    """Base URL for copy-paste commands: CMS_PUBLIC_URL wins over the request host."""
    configured = (get_cms_settings().public_url or "").strip()
    return (configured or str(request.base_url)).rstrip("/")


def _extract_ssh_key(data: dict) -> dict:
    """Move a write-only private key into the encrypted column."""
    private_key = data.pop("ssh_private_key", None)
    if private_key is not None:
        data["ssh_key_enc"] = encrypt(private_key) if private_key.strip() else None
    return data


async def _install_via_ssh(db, host: dict, base: str, token: str) -> dict:
    """Run install.sh on the host over SSH using the stored private key."""
    if not host.get("ssh_key_enc"):
        return {"ok": False, "message": "SSH-ключ не задан для этого хоста"}
    if not host.get("ssh_user"):
        return {"ok": False, "message": "Не указан SSH-пользователь"}

    private_key = decrypt(host["ssh_key_enc"])
    if not private_key:
        return {"ok": False, "message": "Не удалось расшифровать SSH-ключ"}

    remote = (
        'set -e; '
        'if [ "$(id -u)" -eq 0 ]; then RUN="bash"; else RUN="sudo -n bash"; fi; '
        f'curl -sSL {base}/api/backup-agent/v1/install.sh | $RUN -s -- '
        f"--url {base} --host-id {host['id']} --token {token}"
    )

    try:
        import asyncssh  # lazy: only needed for SSH install

        key = asyncssh.import_private_key(private_key)
        conn = await asyncio.wait_for(
            asyncssh.connect(
                host["address"],
                port=int(host.get("ssh_port") or 22),
                username=host["ssh_user"],
                client_keys=[key],
                known_hosts=None,
                connect_timeout=15,
            ),
            timeout=25,
        )
        async with conn:
            result = await asyncio.wait_for(conn.run(remote, check=False), timeout=600)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"{type(exc).__name__}: {exc}"}

    output = ((result.stdout or "") + (result.stderr or ""))[-4000:]
    return {
        "ok": (result.exit_status or 0) == 0,
        "exit_status": result.exit_status,
        "output": output,
    }


def _validate_host(data: HostCreate | HostUpdate) -> None:
    if data.role not in ("server", "node", "self"):
        raise bad_request("role должен быть server, node или self")
    if data.transport not in ("agent", "inline", "ssh"):
        raise bad_request("transport должен быть agent, inline или ssh")


@router.get("")
async def list_hosts(db: DbSession, _admin: CurrentAdmin):
    items = await repo.list_hosts(db)
    return {"success": True, "data": items, "total": len(items)}


@router.post("", status_code=201)
async def create_host(payload: HostCreate, db: DbSession, _admin: CurrentAdmin):
    _validate_host(payload)
    existing = await repo.list_hosts(db)
    if any(h["name"] == payload.name for h in existing):
        raise bad_request(f"Хост с именем {payload.name!r} уже существует")

    payload_data = _extract_ssh_key(payload.model_dump())
    host = await repo.create_host(db, payload_data)

    if host["role"] == "self" or host["transport"] == "inline":
        for matched in recipes_mod.match_all({}, host_role="self"):
            await repo.upsert_component(
                db,
                host_id=host["id"],
                recipe_id=matched.recipe_id,
                name=matched.name,
                container_name=matched.container_name,
                image=matched.image,
                image_digest=matched.image_digest,
                version=matched.version,
                confidence=matched.confidence,
                detect_meta=matched.detect_meta,
            )

    await commit(db)
    full = await repo.get_host(db, host["id"])
    return {"success": True, "data": full}


@router.get("/{host_id}")
async def get_host(host_id: str, db: DbSession, _admin: CurrentAdmin):
    host = await repo.get_host(db, host_id)
    if not host:
        raise not_found("Хост")
    return {"success": True, "data": host}


@router.patch("/{host_id}")
async def update_host(host_id: str, payload: HostUpdate, db: DbSession, _admin: CurrentAdmin):
    host = await repo.get_host(db, host_id)
    if not host:
        raise not_found("Хост")
    _validate_host(payload)
    updated = await repo.update_host(db, host_id, _extract_ssh_key(payload.model_dump(exclude_unset=True)))
    await commit(db)
    return {"success": True, "data": updated}


@router.delete("/{host_id}")
async def delete_host(host_id: str, db: DbSession, _admin: CurrentAdmin):
    host = await repo.get_host(db, host_id)
    if not host:
        raise not_found("Хост")
    if host["role"] == "self":
        raise bad_request("Нельзя удалить хост самой CMS")
    await repo.delete_host(db, host_id)
    await commit(db)
    return {"success": True}


@router.post("/{host_id}/test")
async def test_host(host_id: str, db: DbSession, _admin: CurrentAdmin) -> dict:
    host = await repo.get_host(db, host_id)
    if not host:
        raise not_found("Хост")

    if host["role"] == "self" or host["transport"] == "inline":
        return {
            "success": True,
            "data": HostTestResult(ok=True, message="Локальный хост: проверка не требуется").model_dump(),
        }

    port = int(host.get("ssh_port") or 22)
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host["address"], port), timeout=5
        )
        banner = b""
        try:
            banner = await asyncio.wait_for(reader.read(64), timeout=2)
        except asyncio.TimeoutError:
            pass
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        await repo.update_host(db, host_id, {"status": "unreachable"})
        await commit(db)
        return {
            "success": True,
            "data": HostTestResult(ok=False, ssh=False, message=f"TCP {host['address']}:{port} — {exc}").model_dump(),
        }

    ssh_ok = banner.startswith(b"SSH-")
    await repo.update_host(db, host_id, {"status": "reachable"})
    await commit(db)
    return {
        "success": True,
        "data": HostTestResult(
            ok=ssh_ok,
            ssh=ssh_ok,
            message="SSH отвечает" if ssh_ok else "Порт открыт, но это не SSH-баннер",
        ).model_dump(),
    }


@router.post("/{host_id}/agent-install")
async def agent_install(
    host_id: str,
    request: Request,
    db: DbSession,
    _admin: CurrentAdmin,
    via: str = Query("command", pattern="^(command|ssh)$"),
):
    host = await repo.get_host(db, host_id)
    if not host:
        raise not_found("Хост")
    if host["transport"] == "inline":
        raise bad_request("Для inline-хоста агент не требуется")

    token = secrets.token_urlsafe(32)
    await repo.upsert_agent(db, host_id, token)
    await commit(db)

    base = _public_base(request)
    command = (
        f"curl -sSL {base}/api/backup-agent/v1/install.sh | sudo bash -s -- "
        f"--url {base} --host-id {host_id} --token {token}"
    )

    install_result = None
    if via == "ssh":
        raw_host = await repo.get_host_raw(db, host_id)
        if not raw_host:
            raise not_found("Хост")
        install_result = await _install_via_ssh(db, raw_host, base, token)

    payload = AgentInstall(host_id=host_id, token=token, install_command=command).model_dump()
    if install_result is not None:
        payload["install_result"] = install_result
    return {"success": True, "data": payload}


@router.post("/{host_id}/scan")
async def scan_host(host_id: str, db: DbSession, _admin: CurrentAdmin):
    host = await repo.get_host(db, host_id)
    if not host:
        raise not_found("Хост")
    command = await repo.enqueue_command(db, host_id, "scan", {}, created_by=_admin.username)
    await commit(db)
    return {"success": True, "data": command}


@router.get("/{host_id}/components")
async def list_host_components(host_id: str, db: DbSession, _admin: CurrentAdmin):
    host = await repo.get_host(db, host_id)
    if not host:
        raise not_found("Хост")
    items = await repo.list_components(db, host_id)
    return {"success": True, "data": items, "total": len(items)}
