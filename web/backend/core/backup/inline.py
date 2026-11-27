"""Inline executor: backs up the CMS itself (no agent, runs in the API process)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import tarfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from web.backend.core.backup import manifest as manifest_mod
from web.backend.core.backup import repository as repo
from web.backend.core.backup.storage import get_storage
from web.backend.core.config import get_cms_settings
from web.backend.core.database import get_session_factory

logger = logging.getLogger(__name__)

# Locations where uploads may live inside the API container (first existing wins).
_UPLOAD_CANDIDATES = (
    "/var/www/html/public/uploads",
    "/var/www/html/uploads",
    "/app/uploads",
    "/var/lib/hexaveil/uploads",
    "/var/www/uploads",
)


def _sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 512)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


async def _pg_dump(target: Path) -> None:
    settings = get_cms_settings()
    env = dict(os.environ)
    password = getattr(settings, "db_pass", None)
    if password:
        env["PGPASSWORD"] = password
    args = [
        "pg_dump",
        "-Fc",
        "-h", str(settings.db_host),
        "-p", str(settings.db_port),
        "-U", str(settings.db_user),
        "-d", str(settings.db_name),
        "-f", str(target),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pg_dump не установлен в образе api (postgresql-client)") from exc
    _, err = await proc.communicate()
    if (proc.returncode or 0) != 0:
        raise RuntimeError(f"pg_dump failed: {err.decode('utf-8', 'replace')[:400]}")


def _tar_uploads(target: Path) -> Optional[str]:
    source = next((Path(p) for p in _UPLOAD_CANDIDATES if Path(p).is_dir()), None)
    if source is None:
        return None
    with tarfile.open(target, "w:gz") as tar:
        tar.add(source, arcname="uploads")
    return str(source)


async def _progress(db, run_id: str, progress: int, steps: list[dict] | None = None) -> None:
    fields: dict[str, Any] = {"progress": progress}
    if steps is not None:
        fields["steps"] = steps
    await repo.update_run(db, run_id, fields)
    await db.commit()


async def run_inline_backup(run_id: str, job: dict[str, Any], host_id: str) -> None:
    """Collect CMS artifacts locally and push them to the configured storages."""
    factory = await get_session_factory()
    workdir = Path(os.environ.get("BACKUP_TMP_DIR", "/tmp")) / f"hexaveil-inline-{run_id}"
    workdir.mkdir(parents=True, exist_ok=True)
    steps = [
        {"id": "preflight", "title": "Проверка окружения", "status": "running"},
        {"id": "collect", "title": "Сбор артефактов CMS", "status": "pending"},
        {"id": "upload", "title": "Загрузка в хранилища", "status": "pending"},
        {"id": "manifest", "title": "Манифест", "status": "pending"},
    ]
    started = time.time()
    try:
        async with factory() as db:
            await _progress(db, run_id, 5, steps)
            steps[0]["status"] = "done"
            steps[1]["status"] = "running"
            await _progress(db, run_id, 15, steps)

            produced: list[dict[str, Any]] = []
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

            dump = workdir / f"hexacms_{stamp}.dump"
            await _pg_dump(dump)
            produced.append(
                {
                    "path": dump,
                    "artifact_type": "database",
                    "object_key": f"{run_id}/{dump.name}",
                    "sha256": _sha256(dump)[0],
                    "size": dump.stat().st_size,
                    "encrypted": False,
                }
            )

            scope = job.get("scope") or "full"
            if scope in ("full", "files"):
                uploads_tar = workdir / f"uploads_{stamp}.tar.gz"
                source = _tar_uploads(uploads_tar)
                if source:
                    produced.append(
                        {
                            "path": uploads_tar,
                            "artifact_type": "files",
                            "object_key": f"{run_id}/{uploads_tar.name}",
                            "sha256": _sha256(uploads_tar)[0],
                            "size": uploads_tar.stat().st_size,
                            "encrypted": False,
                        }
                    )

            steps[1]["status"] = "done"
            steps[2]["status"] = "running"
            await _progress(db, run_id, 60, steps)

            storage_ids = job.get("storage_ids") or await repo.enabled_storage_ids(db)
            if not storage_ids:
                raise RuntimeError("нет включённых хранилищ")

            expires = datetime.now(timezone.utc) + timedelta(days=int(job.get("retention_days") or 14))
            for item in produced:
                for storage_id in storage_ids:
                    storage_row = await repo.get_storage_raw(db, str(storage_id))
                    if not storage_row:
                        continue
                    storage = get_storage(storage_row)
                    with item["path"].open("rb") as fh:
                        await storage.put(item["object_key"], fh.read())
                    await repo.create_artifact(
                        db,
                        {
                            "run_id": run_id,
                            "storage_id": str(storage_id),
                            "artifact_type": item["artifact_type"],
                            "object_key": item["object_key"],
                            "size_bytes": item["size"],
                            "sha256": item["sha256"],
                            "encrypted": item["encrypted"],
                            "manifest": {},
                            "expires_at": expires,
                        },
                    )
                await db.commit()

            steps[2]["status"] = "done"
            steps[3]["status"] = "running"
            await _progress(db, run_id, 90, steps)

            manifest = manifest_mod.build_manifest(
                backup_id=run_id,
                host={"id": host_id, "name": "hexaveil-cms"},
                components=[
                    {
                        "recipe": "hexaveil-cms",
                        "recipe_version": 1,
                        "artifacts": [
                            {
                                "type": item["artifact_type"],
                                "file": item["path"].name,
                                "size": item["size"],
                                "sha256": item["sha256"],
                                "encrypted": False,
                            }
                            for item in produced
                        ],
                    }
                ],
                consistency_group=job.get("consistency_group"),
                tool_version="cms-inline",
            )
            manifest_path = workdir / "manifest.json"
            manifest_path.write_text(manifest_mod.dumps(manifest), encoding="utf-8")
            sha, size = _sha256(manifest_path)
            for storage_id in storage_ids:
                storage_row = await repo.get_storage_raw(db, str(storage_id))
                if not storage_row:
                    continue
                storage = get_storage(storage_row)
                with manifest_path.open("rb") as fh:
                    await storage.put(f"{run_id}/manifest.json", fh.read())
                await repo.create_artifact(
                    db,
                    {
                        "run_id": run_id,
                        "storage_id": str(storage_id),
                        "artifact_type": "manifest",
                        "object_key": f"{run_id}/manifest.json",
                        "size_bytes": size,
                        "sha256": sha,
                        "encrypted": False,
                        "manifest": {},
                        "expires_at": expires,
                    },
                )
            await db.commit()

            steps[3]["status"] = "done"
            await _progress(db, run_id, 100, steps)
            await repo.update_run(
                db,
                run_id,
                {
                    "status": "success",
                    "finished_at": datetime.now(timezone.utc),
                    "size_bytes": sum(item["size"] for item in produced),
                },
            )
            await repo.append_run_log(
                db, run_id, f"Готово: {len(produced)} артефактов за {int(time.time() - started)} с\n"
            )
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Inline backup %s failed", run_id)
        async with factory() as db:
            await repo.append_run_log(db, run_id, f"ОШИБКА: {type(exc).__name__}: {exc}\n")
            await repo.update_run(
                db,
                run_id,
                {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "finished_at": datetime.now(timezone.utc),
                },
            )
            await db.commit()
    finally:
        import shutil

        shutil.rmtree(workdir, ignore_errors=True)
