"""Media API — read endpoint.

Mirrors PHP GET /api/media: walks the uploads directory on disk and
returns image files (path / url / name / size / modified).
"""
import os
from pathlib import Path

from fastapi import APIRouter, Depends

from backend.api.deps import AdminUser, get_current_admin
from backend.core.config import get_cms_settings

router = APIRouter()

ALLOWED_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "svg"}


@router.get("/media")
async def list_media(admin: AdminUser = Depends(get_current_admin)):
    settings = get_cms_settings()
    base = Path(settings.upload_dir)

    files = []
    if base.is_dir():
        for root, _dirs, filenames in os.walk(base):
            for name in filenames:
                ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
                if ext not in ALLOWED_EXTS:
                    continue
                full = Path(root) / name
                try:
                    st = full.stat()
                except OSError:
                    continue
                rel = (Path("/public/uploads") / full.relative_to(base)).as_posix()
                files.append({
                    "path": rel,
                    "url": rel,
                    "name": name,
                    "size": st.st_size,
                    "modified": int(st.st_mtime),
                })

    return {"success": True, "data": files}
