"""Media API — list + upload + delete endpoints.

  GET  /api/media        → { success, data: [...] }  (walks uploads dir)
  POST /api/media/upload → { success, data: { path, url, name } }  (multipart)
  POST /api/media/delete → { success }
"""
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile

from backend.api.deps import AdminUser, get_current_admin
from backend.core.config import get_cms_settings
from backend.core.errors import E, api_error
from backend.core.request_utils import json_body

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


@router.post("/media/upload")
async def upload_media(
    admin: AdminUser = Depends(get_current_admin),
    file: UploadFile | None = File(None),
    image: UploadFile | None = File(None),
    upload: UploadFile | None = File(None),
):
    src = file or image or upload
    if src is None or not src.filename:
        return api_error(400, E.INVALID_INPUT, "Файл не загружен")

    settings = get_cms_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = src.filename.rsplit(".", 1)[-1].lower() if "." in src.filename else ""
    if ext not in ALLOWED_EXTS:
        return api_error(400, E.INVALID_INPUT, "Недопустимый тип файла")

    filename = (
        datetime.now().strftime("%Y%m%d_%H%M%S")
        + "_"
        + os.urandom(4).hex()
        + "."
        + ext
    )
    dest = upload_dir / filename
    content = await src.read()
    dest.write_bytes(content)

    rel = f"/public/uploads/{filename}"
    return {"success": True, "data": {"path": rel, "url": rel, "name": filename}}


@router.post("/media/delete")
async def delete_media(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
):
    body = await json_body(request)
    path = str(body.get("path") or "")

    if path != "":
        settings = get_cms_settings()
        public_dir = Path(settings.public_dir)
        # path is like "/public/uploads/x.jpg" → strip "/public/" → place under public_dir
        rel = path[len("/public/"):] if path.startswith("/public/") else path.lstrip("/")
        full = public_dir / rel
        try:
            if full.is_file():
                full.unlink()
        except OSError:
            pass

    return {"success": True}
