"""Support attachments — upload (multipart) + download (?download=1) (фаза 2).

POST /attachments сохраняет файл в {upload_dir}/support/ и возвращает токен;
настоящая строка support_attachment создаётся при отправке (schema: message_id
NOT NULL — привязка возможна только к существующему сообщению).
GET /attachments/{id} отдаёт файл записи (инлайн для image/*, иначе скачивание).
"""
import asyncio
import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.tg.types import guess_kind

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".ogg", ".mp3", ".mp4",
    ".pdf", ".doc", ".docx", ".txt",
})
DEFAULT_MAX_UPLOAD_SIZE = 8 * 1024 * 1024
# Upload tokens live 24h by default; override with SUPPORT_UPLOAD_TOKEN_TTL_HOURS.
UPLOAD_TOKEN_TTL_HOURS = int(os.getenv("SUPPORT_UPLOAD_TOKEN_TTL_HOURS", "24") or 24)
_BLOCKED_MIMES = frozenset({"image/svg+xml", "text/html", "application/xhtml+xml"})
_BLOCKED_EXTS = frozenset({".svg", ".html", ".htm"})


def _upload_dir(service: SupportService) -> Path:
    if service.upload_dir is not None:
        return service.upload_dir
    from web.backend.core.config import get_cms_settings

    cms = get_cms_settings()
    return (Path(getattr(cms, "upload_dir", "/var/www/html/public/uploads")) / "support").resolve()


def _meta_created_at(meta: dict[str, Any]) -> datetime | None:
    """Parse meta `created_at` (UTC ISO); None for legacy/broken metas (no TTL)."""
    raw = meta.get("created_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _is_expired(meta: dict[str, Any]) -> bool:
    created_at = _meta_created_at(meta)
    if created_at is None:
        return False
    return datetime.now(timezone.utc) - created_at > timedelta(hours=UPLOAD_TOKEN_TTL_HOURS)


def _drop_expired(meta_path: Path, file_path: Path) -> None:
    """Best-effort removal of an expired token's file and meta."""
    for path in (file_path, meta_path):
        try:
            path.unlink(missing_ok=True)
        except OSError as e:  # noqa: BLE001 — TTL-уборка не должна ронять запрос
            logger.debug("support upload cleanup failed for %s: %s", path, e)


def resolve_upload_token(service: SupportService, token: str) -> dict[str, Any] | None:
    """Метаданные загруженного ранее файла по токену (None — нет/сломалось/устарело)."""
    if not token or token != token.strip() or "/" in token or "\\" in token or ".." in token:
        return None
    upload_dir = _upload_dir(service)
    meta_path = upload_dir / f"up_{token}.json"
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(meta, dict):
        return None
    file_path = upload_dir / f"up_{token}{meta.get('ext', '')}"
    if _is_expired(meta):
        _drop_expired(meta_path, file_path)
        return None
    if not file_path.is_file():
        return None
    meta["token"] = token
    meta["local_path"] = str(file_path)
    return meta



def _write_meta(path: Path, meta: dict[str, Any]) -> None:
    path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


# ── POST /attachments ─────────────────────────────────────────────────────────

@router.post("/attachments")
async def upload_attachment(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Загрузить файл для последующей отправки (в токен ответа)."""
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    mime = (file.content_type or "").lower()

    if ext in _BLOCKED_EXTS or mime in _BLOCKED_MIMES:
        raise HTTPException(
            status_code=415,
            detail={"success": False, "error": "Тип файла не разрешён", "code": "UNSUPPORTED_MEDIA_TYPE"},
        )
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail={"success": False, "error": "Расширение вне разрешённого списка", "code": "UNSUPPORTED_MEDIA_TYPE"},
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail={"success": False, "error": "Пустой файл", "code": E.INVALID_INPUT.value})

    max_size = service.upload_max_size or DEFAULT_MAX_UPLOAD_SIZE
    if len(data) > max_size:
        raise HTTPException(
            status_code=413,
            detail={"success": False, "error": "Файл слишком большой", "code": "FILE_TOO_LARGE"},
        )

    token = secrets.token_hex(16)
    upload_dir = _upload_dir(service)
    await asyncio.to_thread(upload_dir.mkdir, parents=True, exist_ok=True)

    meta: dict[str, Any] = {
        "token": token,
        "ext": ext,
        "original_name": filename,
        "mime_type": mime or "application/octet-stream",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "media_type": guess_kind(mime, filename),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await asyncio.to_thread((upload_dir / f"up_{token}{ext}").write_bytes, data)
    await asyncio.to_thread(_write_meta, upload_dir / f"up_{token}.json", meta)

    return {
        "success": True,
        "data": {
            "token": token,
            "media_type": meta["media_type"],
            "mime_type": meta["mime_type"],
            "original_name": filename,
            "bytes": len(data),
            "sha256": meta["sha256"],
        },
    }


# ── GET /attachments/{id} ─────────────────────────────────────────────────────

@router.get("/attachments/{attachment_id}")
async def download_attachment(
    attachment_id: int,
    download: bool = Query(False),
    conversation_id: int | None = Query(None),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Отдать файл записи support_attachment (инлайн для просмотра, ?download=1 — скачать).

    ACL: attachment → support_message → support_conversation (INNER JOIN);
    битая связка и чужой `conversation_id` дают 404, не 403.
    """
    att = await service.store.get_attachment_with_conversation(
        attachment_id, conversation_id=conversation_id
    )
    if att is None:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "error": "Attachment not found", "code": E.NOT_FOUND.value},
        )

    local_path = att.get("local_path")
    path = Path(local_path) if local_path else None
    if path is None or not path.is_file():
        raise HTTPException(
            status_code=404,
            detail={"success": False, "error": "Attachment file not found", "code": E.NOT_FOUND.value},
        )
    filename = att.get("original_name") or path.name
    media_type = att.get("mime_type") or "application/octet-stream"
    if download:
        return FileResponse(str(path), media_type="application/octet-stream", filename=filename)
    return FileResponse(str(path), media_type=media_type, content_disposition_type="inline", filename=filename)
