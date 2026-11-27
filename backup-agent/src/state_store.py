"""Atomic JSON state cache: the agent keeps working when the CMS is down."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional


class StateStore:
    def __init__(self, directory: str):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.dir / "state.json"
        self.local_file = self.dir / "local.json"

    # ------------------------------------------------------------------ generic

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _write(path: Path, data: dict[str, Any]) -> None:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    # -------------------------------------------------------------------- state

    def load(self) -> dict[str, Any]:
        return self._read(self.state_file)

    def save(self, data: dict[str, Any]) -> None:
        self._write(self.state_file, data)

    def etag(self) -> Optional[str]:
        data = self.load()
        return data.get("_etag")

    def save_with_etag(self, data: dict[str, Any], etag: Optional[str]) -> None:
        payload = dict(data)
        payload["_etag"] = etag
        self._write(self.state_file, payload)

    # ----------------------------------------------------- local runtime counters

    def local(self) -> dict[str, Any]:
        return self._read(self.local_file)

    def set_local(self, key: str, value: Any) -> None:
        data = self.local()
        data[key] = value
        self._write(self.local_file, data)

    def get_local(self, key: str, default: Any = None) -> Any:
        return self.local().get(key, default)
