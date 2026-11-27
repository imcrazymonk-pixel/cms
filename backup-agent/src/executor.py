"""Backup and restore execution on the host.

All heavy lifting goes through the Docker CLI (pg_dump inside the DB container,
tar for volumes). Artifacts are written to the spool, hashed, optionally
encrypted with age, then uploaded to every destination configured by the CMS.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shlex
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from .api_client import ApiClient, CmsUnavailable
from .config import AgentConfig
from .spool import Spool

logger = logging.getLogger(__name__)


class Cancelled(Exception):
    pass


class Executor:
    def __init__(self, cfg: AgentConfig, client: ApiClient, spool: Spool):
        self.cfg = cfg
        self.client = client
        self.spool = spool

    # ------------------------------------------------------------------ helpers

    def host_path(self, path: str) -> Path:
        direct = Path(path)
        if direct.exists():
            return direct
        prefixed = Path(self.cfg.host_prefix.rstrip("/") + path)
        return prefixed if prefixed.exists() else direct

    async def _run(self, *args: str, timeout: int = 3600, stdin: Optional[bytes] = None) -> tuple[int, bytes, bytes]:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(stdin), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"{args[0]} timed out after {timeout}s")
        return proc.returncode or 0, out, err

    async def _stream_to_file(self, args: list[str], target: Path, timeout: int = 3600) -> None:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        with target.open("wb") as fh:
            while True:
                chunk = await proc.stdout.read(1024 * 512)
                if not chunk:
                    break
                fh.write(chunk)
        _, err = await proc.communicate()
        if (proc.returncode or 0) != 0:
            raise RuntimeError(f"{args[0]} failed: {err.decode('utf-8', 'replace')[:400]}")

    async def _container_env(self, container: str, key: str) -> Optional[str]:
        code, out, _ = await self._run("docker", "exec", container, "printenv", key, timeout=30)
        return out.decode().strip() if code == 0 and out.strip() else None

    @staticmethod
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

    async def _encrypt(self, path: Path) -> tuple[Path, bool]:
        if not self.cfg.age_recipient:
            return path, False
        encrypted = path.with_suffix(path.suffix + ".age")
        code, _, err = await self._run(
            "age", "-r", self.cfg.age_recipient, "-o", str(encrypted), str(path), timeout=3600
        )
        if code != 0:
            raise RuntimeError(f"age encryption failed: {err.decode('utf-8', 'replace')[:300]}")
        path.unlink(missing_ok=True)
        return encrypted, True

    async def _progress(self, run_id: str, *, progress: int, steps: Optional[list[dict]] = None) -> None:
        payload: dict[str, Any] = {"progress": progress}
        if steps is not None:
            payload["steps"] = steps
        try:
            response = await self.client.patch_run(run_id, payload)
            data = (response or {}).get("data") or {}
            if data.get("cancel_requested"):
                raise Cancelled()
        except CmsUnavailable:
            pass

    async def _log(self, run_id: str, text: str) -> None:
        line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {text}\n"
        logger.info(text)
        try:
            await self.client.patch_run(run_id, {"log_append": line})
        except CmsUnavailable:
            pass

    async def _finish(self, run_id: str, status: str, error: Optional[str] = None) -> None:
        payload: dict[str, Any] = {"status": status, "finished": True, "progress": 100 if status == "success" else 0}
        if error:
            payload["error"] = error
        try:
            await self.client.patch_run(run_id, payload)
        except CmsUnavailable:
            logger.error("Cannot report run %s completion to CMS", run_id)

    # ------------------------------------------------------------------- backup

    async def run_backup(self, run_id: str, job: dict[str, Any], state: dict[str, Any]) -> None:
        started = time.time()
        steps = [
            {"id": "preflight", "title": "Проверка окружения", "status": "running"},
            {"id": "collect", "title": "Сбор артефактов", "status": "pending"},
            {"id": "upload", "title": "Загрузка в хранилища", "status": "pending"},
            {"id": "manifest", "title": "Манифест и проверка", "status": "pending"},
        ]
        produced: list[dict[str, Any]] = []
        try:
            await self._progress(run_id, progress=5, steps=steps)
            await self._log(run_id, f"Старт бэкапа, scope={job.get('scope') or 'full'}")

            components = self._select_components(state, job)
            if not components:
                raise RuntimeError("нет включённых компонентов для бэкапа")

            steps[0]["status"] = "done"
            steps[1]["status"] = "running"
            await self._progress(run_id, progress=15, steps=steps)

            run_dir = self.spool.run_dir(run_id)
            index = 0
            for component in components:
                recipe = self._recipe(state, component.get("recipe_id"))
                if not recipe:
                    continue
                for artifact in await self._collect_component(run_id, component, recipe, job, run_dir):
                    produced.append(artifact)
                index += 1
                await self._progress(run_id, progress=15 + int(45 * index / max(1, len(components))), steps=steps)

            if not produced:
                raise RuntimeError("не удалось собрать ни одного артефакта")

            steps[1]["status"] = "done"
            steps[2]["status"] = "running"
            await self._progress(run_id, progress=65, steps=steps)

            storage_ids = job.get("storage_ids") or []
            if not storage_ids:
                raise RuntimeError("CMS не передал ни одного хранилища")

            for item in produced:
                await self._upload_everywhere(run_id, item, storage_ids)

            steps[2]["status"] = "done"
            steps[3]["status"] = "running"
            await self._progress(run_id, progress=90, steps=steps)

            manifest = self._build_manifest(run_id, job, state, produced)
            manifest_path = run_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            sha, size = self._sha256(manifest_path)
            await self._upload_everywhere(
                run_id,
                {
                    "path": manifest_path,
                    "artifact_type": "manifest",
                    "encrypted": False,
                    "sha256": sha,
                    "size": size,
                    "component_id": None,
                    "object_key": f"{run_id}/manifest.json",
                },
                storage_ids,
            )

            steps[3]["status"] = "done"
            await self._progress(run_id, progress=100, steps=steps)
            await self._log(run_id, f"Готово: {len(produced)} артефактов за {int(time.time() - started)} с")
            await self._finish(run_id, "success")
            self.spool.drop(run_id)
        except Cancelled:
            await self._log(run_id, "Отменено CMS")
            await self._finish(run_id, "cancelled")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Backup run %s failed", run_id)
            await self._log(run_id, f"ОШИБКА: {type(exc).__name__}: {exc}")
            await self._finish(run_id, "failed", f"{type(exc).__name__}: {exc}")

    def _select_components(self, state: dict[str, Any], job: dict[str, Any]) -> list[dict[str, Any]]:
        components = [c for c in state.get("components") or [] if c.get("enabled", True)]
        ids = job.get("component_ids") or []
        if ids:
            wanted = {str(i) for i in ids}
            components = [c for c in components if str(c.get("id")) in wanted]
        return components

    @staticmethod
    def _recipe(state: dict[str, Any], recipe_id: Optional[str]) -> Optional[dict[str, Any]]:
        for recipe in state.get("recipes") or []:
            if recipe.get("id") == recipe_id:
                return recipe
        return None

    async def _collect_component(
        self,
        run_id: str,
        component: dict[str, Any],
        recipe: dict[str, Any],
        job: dict[str, Any],
        run_dir: Path,
    ) -> list[dict[str, Any]]:
        artifacts = recipe.get("artifacts") or {}
        scope = job.get("scope") or "full"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        base = f"{component.get('name') or recipe.get('id')}_{timestamp}"
        out: list[dict[str, Any]] = []

        database = artifacts.get("database")
        if database and scope in ("full", "database"):
            target = run_dir / f"{base}_db.dump"
            await self._log(run_id, f"pg_dump: {database.get('container')}")
            await self._dump_database(database, target)
            out.append(await self._prepare(run_id, target, "database", component, job))

        if scope in ("full", "files", "env"):
            for file_spec in artifacts.get("files") or []:
                path = file_spec.get("path")
                if not path:
                    continue
                target = run_dir / f"{base}_{Path(path).name or 'files'}.tar.zst"
                await self._log(run_id, f"tar: {path}")
                await self._tar_path(path, target, file_spec.get("exclude") or [])
                if target.exists():
                    out.append(await self._prepare(run_id, target, "files", component, job))

        if job.get("include_logs") and artifacts.get("logs"):
            for path in (artifacts["logs"].get("paths") or []):
                target = run_dir / f"{base}_logs_{abs(hash(path)) % 10**6}.tar.zst"
                if await self._tar_path(path, target, []):
                    out.append(await self._prepare(run_id, target, "logs", component, job))

        return out

    async def _dump_database(self, database: dict[str, Any], target: Path) -> None:
        container = database.get("container")
        if not container:
            raise RuntimeError("в рецепте не указан контейнер БД")
        user = await self._container_env(container, "POSTGRES_USER") or "postgres"
        dbname = await self._container_env(container, "POSTGRES_DB") or "postgres"
        password = await self._container_env(container, "POSTGRES_PASSWORD") or ""

        args = ["docker", "exec", "-i"]
        if password:
            args += ["-e", f"PGPASSWORD={password}"]
        args += [container, "pg_dump", "-Fc", "-U", user, "-d", dbname]
        await self._stream_to_file(args, target)

    async def _tar_path(self, path: str, target: Path, exclude: list[str]) -> bool:
        source = self.host_path(path)
        exclude_args: list[str] = []
        for pattern in exclude:
            exclude_args += ["--exclude", pattern]

        if source.exists():
            code, _, err = await self._run(
                "tar", "--zstd", "-cf", str(target), *exclude_args, "-C", str(source), "."
            )
            if code != 0:
                raise RuntimeError(f"tar failed for {path}: {err.decode('utf-8', 'replace')[:300]}")
            return True

        # Host path hidden by the container mount: ask the host Docker daemon.
        target_dir = target.parent
        code, _, err = await self._run(
            "docker", "run", "--rm",
            "-v", f"{path}:/src:ro",
            "-v", f"{target_dir}:/out",
            "alpine:3.20", "tar", "--zstd", "-cf", f"/out/{target.name}", *exclude_args, "-C", "/src", ".",
        )
        if code != 0:
            raise RuntimeError(f"docker tar failed for {path}: {err.decode('utf-8', 'replace')[:300]}")
        return True

    async def _prepare(
        self,
        run_id: str,
        path: Path,
        artifact_type: str,
        component: dict[str, Any],
        job: dict[str, Any],
    ) -> dict[str, Any]:
        encrypted = False
        if job.get("encrypt", True):
            path, encrypted = await self._encrypt(path)
        sha, size = self._sha256(path)
        return {
            "path": path,
            "artifact_type": artifact_type,
            "encrypted": encrypted,
            "sha256": sha,
            "size": size,
            "component_id": component.get("id"),
            "object_key": f"{run_id}/{path.name}",
        }

    async def _upload_everywhere(self, run_id: str, item: dict[str, Any], storage_ids: list[str]) -> None:
        expires = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        for storage_id in storage_ids:
            response = await self.client.register_artifact(
                run_id,
                {
                    "component_id": item.get("component_id"),
                    "storage_id": storage_id,
                    "artifact_type": item["artifact_type"],
                    "object_key": item["object_key"],
                    "size_bytes": item["size"],
                    "sha256": item["sha256"],
                    "encrypted": item["encrypted"],
                    "expires_at": expires,
                },
            )
            upload_url = (response.get("data") or {}).get("upload_url")
            if not upload_url:
                raise RuntimeError("CMS не вернул upload_url")
            await self.client.upload_file(upload_url, item["path"])
        # Only after every destination accepted the bytes may the spool copy go.
        self.spool.mark_done(item["path"])

    def _build_manifest(
        self,
        run_id: str,
        job: dict[str, Any],
        state: dict[str, Any],
        produced: list[dict[str, Any]],
    ) -> dict[str, Any]:
        by_component: dict[str, list[dict[str, Any]]] = {}
        for item in produced:
            by_component.setdefault(str(item.get("component_id")), []).append(item)

        components = []
        for component in state.get("components") or []:
            cid = str(component.get("id"))
            items = by_component.get(cid)
            if not items:
                continue
            components.append(
                {
                    "name": component.get("name"),
                    "recipe": component.get("recipe_id"),
                    "container": component.get("container_name"),
                    "artifacts": [
                        {
                            "type": i["artifact_type"],
                            "file": i["path"].name,
                            "size": i["size"],
                            "sha256": i["sha256"],
                            "encrypted": i["encrypted"],
                        }
                        for i in items
                    ],
                }
            )
        return {
            "manifest_version": 1,
            "backup_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "host": {"id": self.cfg.host_id},
            "consistency_group": job.get("consistency_group"),
            "components": components,
            "tool": {"name": "hexaveil-backup-agent", "version": self.cfg.version},
        }

    # ------------------------------------------------------------------ restore

    async def run_restore(self, restore_id: str, job: dict[str, Any], state: dict[str, Any]) -> None:
        plan = job.get("plan") or {}
        artifacts = plan.get("artifacts") or []
        run_id = job.get("run_id") or restore_id
        workdir = self.spool.run_dir(run_id)
        try:
            await self._log(run_id, f"Restore: {len(artifacts)} артефактов")
            downloaded: list[tuple[dict[str, Any], Path]] = []
            for index, artifact in enumerate(artifacts):
                target = workdir / f"{index:02d}_{artifact.get('object_key', 'artifact').rsplit('/', 1)[-1]}"
                await self.client.download_artifact(str(artifact.get("id")), target)
                if target.suffix == ".age" and self.cfg.age_identity:
                    plain = target.with_suffix("")
                    code, _, err = await self._run("age", "-d", "-i", self.cfg.age_identity, "-o", str(plain), str(target))
                    if code != 0:
                        raise RuntimeError(f"age decrypt failed: {err.decode('utf-8', 'replace')[:300]}")
                    target = plain
                downloaded.append((artifact, target))
                await self._progress(run_id, progress=int(70 * (index + 1) / max(1, len(artifacts))))

            for artifact, path in downloaded:
                await self._apply_artifact(artifact, path, state)
            await self._finish(run_id, "success")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Restore %s failed", restore_id)
            await self._log(run_id, f"ОШИБКА restore: {exc}")
            await self._finish(run_id, "failed", str(exc))

    async def _apply_artifact(self, artifact: dict[str, Any], path: Path, state: dict[str, Any]) -> None:
        kind = artifact.get("artifact_type")
        if kind == "database":
            container = self._db_container(state)
            if not container:
                raise RuntimeError("не найден контейнер БД")
            user = await self._container_env(container, "POSTGRES_USER") or "postgres"
            dbname = await self._container_env(container, "POSTGRES_DB") or "postgres"
            password = await self._container_env(container, "POSTGRES_PASSWORD") or ""
            catalog = await self._run("pg_restore", "--list", str(path)) if os.name != "nt" else (0, b"", b"")
            args = ["docker", "exec", "-i"]
            if password:
                args += ["-e", f"PGPASSWORD={password}"]
            args += [container, "pg_restore", "--clean", "--if-exists", "-U", user, "-d", dbname]
            code, _, err = await self._run(*args, stdin=path.read_bytes())
            if code != 0:
                raise RuntimeError(f"pg_restore failed: {err.decode('utf-8', 'replace')[:400]}")
            return
        if kind in ("files", "logs", "env"):
            target = path.parent / (path.name + ".untar")
            target.mkdir(exist_ok=True)
            code, _, err = await self._run("tar", "--zstd", "-xf", str(path), "-C", str(target))
            if code != 0:
                raise RuntimeError(f"tar extract failed: {err.decode('utf-8', 'replace')[:300]}")
            return

    @staticmethod
    def _db_container(state: dict[str, Any]) -> Optional[str]:
        for recipe in state.get("recipes") or []:
            database = (recipe.get("artifacts") or {}).get("database")
            if database and database.get("container"):
                return database["container"]
        return None
