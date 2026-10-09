"""Diagnostics API — migrates PHP AdminDiagnosticsController.

  GET  /admin/diagnostics/api/data     → { success, collected_at, nodes, summary, is_collecting }
  POST /admin/diagnostics/api/collect  → { success, message } | 409 | 404

Reads `nodes_stats.json` (produced by tools/collect_stats.py) and spawns the
collector in the background with a lock file, exactly like PHP.
"""
import json
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.config import get_cms_settings
from web.backend.core.errors import E, api_error

router = APIRouter()


def _paths() -> tuple[Path, Path, Path]:
    root = Path(get_cms_settings().root_path)
    return (
        root / "nodes_stats.json",
        root / "nodes_stats.lock",
        root / "tools" / "collect_stats.py",
    )


def _load_stats() -> dict:
    stats_file, _lock, _script = _paths()
    if not stats_file.exists():
        return {}
    try:
        content = stats_file.read_text(encoding="utf-8")
        if not content:
            return {}
        decoded = json.loads(content)
        return decoded if isinstance(decoded, dict) else {}
    except Exception:
        return {}


def _build_summary(data: dict) -> dict:
    nodes = data.get("nodes") or []
    total = len(nodes)
    reachable = 0
    unreachable = 0
    problems = 0
    avg_load = 0.0
    load_count = 0

    for n in nodes:
        if n.get("reachable"):
            reachable += 1
            d = n.get("data") or {}
            load = (d.get("load") or {}).get("1m")
            if load:
                avg_load += float(load)
                load_count += 1
            tcp = d.get("tcp") or {}
            if tcp.get("retrans_pct") is not None and tcp.get("retrans_pct") >= 2:
                problems += 1
            if (d.get("speed_download_mbps") if d.get("speed_download_mbps") is not None else 100) < 3:
                problems += 1
            if (load or 0) > 0.8:
                problems += 1
            if (d.get("nginx") or {}).get("status") == "error":
                problems += 1
        else:
            unreachable += 1
            problems += 1

    return {
        "total": total,
        "reachable": reachable,
        "unreachable": unreachable,
        "problems": problems,
        "avgLoad": round(avg_load / load_count, 2) if load_count > 0 else 0,
    }


@router.get("/data")
async def api_data(admin: AdminUser = Depends(get_current_admin)):
    _stats, lock, _script = _paths()
    data = _load_stats()
    return {
        "success": True,
        "collected_at": data.get("collected_at"),
        "nodes": data.get("nodes") or [],
        "summary": _build_summary(data),
        "is_collecting": lock.exists(),
    }


@router.post("/collect")
async def api_collect(admin: AdminUser = Depends(get_current_admin)):
    stats_file, lock, script = _paths()

    if lock.exists():
        return api_error(409, E.ALREADY_EXISTS, "Сбор уже запущен")

    if not script.exists():
        return api_error(404, E.NOT_FOUND, "Скрипт не найден: tools/collect_stats.py")

    # Background: touch lock && python3 script --save stats; rm lock  (mirrors PHP exec ... &)
    cmd = (
        f"touch {lock} && python3 {script} --save {stats_file} 2>&1; rm -f {lock}"
    )
    try:
        subprocess.Popen(cmd, shell=True, start_new_session=True)
    except Exception as e:  # pragma: no cover - best effort, like PHP
        return api_error(500, E.INTERNAL_ERROR, f"Не удалось запустить сбор: {e}")

    return {"success": True, "message": "Сбор статистики запущен в фоне"}
