"""Inventory: what actually runs on this host (read-only)."""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def _run(*args: str, timeout: int = 30) -> tuple[int, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")
    except FileNotFoundError:
        return 127, "", f"{args[0]}: not found"
    except asyncio.TimeoutError:
        return 124, "", f"{args[0]}: timeout"


def _parse_ports(raw: str) -> list[int]:
    ports: list[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if "->" not in part:
            continue
        left = part.split("->", 1)[0]
        if ":" in left:
            host_port = left.rsplit(":", 1)[1]
            if host_port.isdigit():
                ports.append(int(host_port))
    return sorted(set(ports))


class InventoryCollector:
    def __init__(self, host_prefix: str = "/host"):
        self.host_prefix = host_prefix.rstrip("/")

    async def collect(self) -> dict[str, Any]:
        code, out, _ = await _run("docker", "version", "--format", "{{.Server.Version}}")
        docker_version = out.strip() if code == 0 else None

        containers = await self._containers()
        return {
            "docker_version": docker_version,
            "compose_projects": await self._compose_projects(),
            "containers": containers,
            "ports": [{"port": p} for c in containers for p in c.get("ports", [])],
            "disk": self._disk(),
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _containers(self) -> list[dict[str, Any]]:
        code, out, err = await _run("docker", "ps", "--format", "{{json .}}")
        if code != 0:
            logger.warning("docker ps failed: %s", err.strip())
            return []

        raw: list[dict[str, Any]] = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        names = [c.get("Names") for c in raw if c.get("Names")]
        inspected: dict[str, dict[str, Any]] = {}
        if names:
            code, out, _ = await _run("docker", "inspect", *names, timeout=60)
            if code == 0:
                try:
                    for item in json.loads(out):
                        inspected[item.get("Name", "").lstrip("/")] = item
                except json.JSONDecodeError:
                    pass

        result: list[dict[str, Any]] = []
        for item in raw:
            name = item.get("Names")
            info = inspected.get(name) or {}
            image = item.get("Image") or (info.get("Config") or {}).get("Image")
            digest = None
            if info.get("Image"):
                code, out, _ = await _run("docker", "image", "inspect", "--format", "{{index .RepoDigests 0}}", info["Image"])
                if code == 0 and out.strip():
                    digest = out.strip().split("@")[-1]
            env_keys = sorted(
                str(entry).split("=", 1)[0]
                for entry in ((info.get("Config") or {}).get("Env") or [])
                if "=" in str(entry)
            )
            result.append(
                {
                    "name": name,
                    "image": image,
                    "image_digest": digest,
                    "status": (item.get("Status") or "").lower(),
                    "ports": _parse_ports(item.get("Ports") or ""),
                    "env_keys": env_keys,
                    "labels": (info.get("Config") or {}).get("Labels") or {},
                    "version": image.rsplit(":", 1)[1] if image and ":" in image else None,
                }
            )
        return result

    async def _compose_projects(self) -> list[dict[str, Any]]:
        code, out, _ = await _run("docker", "compose", "ls", "--format", "json")
        if code != 0:
            return []
        try:
            data = json.loads(out or "[]")
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def _disk(self) -> dict[str, Any]:
        target = self.host_prefix if shutil.os.path.exists(self.host_prefix) else "/"
        try:
            usage = shutil.disk_usage(target)
        except OSError:
            return {}
        return {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "used_percent": round(usage.used * 100 / usage.total, 1) if usage.total else 0,
        }
