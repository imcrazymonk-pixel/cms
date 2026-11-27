"""Spool: artifacts not yet uploaded, with a hard size limit."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable


class Spool:
    def __init__(self, root: str, limit_bytes: int = 10 * 1024**3):
        self.root = Path(root) / "spool"
        self.limit_bytes = limit_bytes
        for sub in ("pending", "uploading", "done"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        path = self.root / "pending" / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def path(self, run_id: str, name: str) -> Path:
        return self.run_dir(run_id) / name

    def mark_uploading(self, path: Path) -> Path:
        target = self.root / "uploading" / path.name
        if path.exists():
            shutil.move(str(path), str(target))
        return target

    def mark_done(self, path: Path) -> None:
        target = self.root / "done" / path.name
        if path.exists():
            shutil.move(str(path), str(target))

    def drop(self, run_id: str) -> None:
        shutil.rmtree(self.root / "pending" / run_id, ignore_errors=True)

    def size(self) -> int:
        total = 0
        for base in (self.root / "pending", self.root / "uploading"):
            for path in base.rglob("*"):
                if path.is_file():
                    total += path.stat().st_size
        return total

    def pending_files(self) -> Iterable[Path]:
        return (self.root / "pending").rglob("*")

    def enforce_limit(self) -> int:
        """Delete the oldest pending files until under the limit. Returns count."""
        if self.limit_bytes <= 0 or self.size() <= self.limit_bytes:
            return 0
        files = sorted(
            (p for p in self.pending_files() if p.is_file()),
            key=lambda p: p.stat().st_mtime,
        )
        removed = 0
        for path in files:
            if self.size() <= self.limit_bytes:
                break
            try:
                os.unlink(path)
                removed += 1
            except OSError:
                continue
        return removed

    def usage_percent(self) -> int:
        if self.limit_bytes <= 0:
            return 0
        return min(100, int(self.size() * 100 / self.limit_bytes))
