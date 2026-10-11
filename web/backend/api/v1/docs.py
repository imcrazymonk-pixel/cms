"""Docs API — CHANGELOG_CMS.md in DB + HISTORY_TECHNICAL.md (file-based, read-only).

  GET    /api/docs                     → list of available documents
  GET    /api/docs/{name}              → document content (raw + html)
  GET    /api/docs/{name}/entries      → structured entries list
  POST   /api/docs/{name}/entries      → add new entry (DB)
  PUT    /api/docs/{name}/entries/{id} → edit entry (DB, changelog only)
  DELETE /api/docs/{name}/entries/{id} → delete entry (DB, changelog only)
  POST   /api/docs/changelog/import    → import entries from .md file (multipart)
  GET    /api/docs/changelog/export    → export entries as .md file download
"""
import asyncio
import io
import logging
import re
from datetime import date as date_type, datetime
from datetime import time as time_type
from pathlib import Path

import markdown as md_lib
from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.database import get_db
from web.backend.core.errors import E, api_error

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_DOCS_DIR_CANDIDATES = [
    _PROJECT_ROOT / "docs",
    Path("/var/www/html/docs"),
]
_DOCS_DIR = _DOCS_DIR_CANDIDATES[0]
for d in _DOCS_DIR_CANDIDATES:
    if (d / "CHANGELOG_CMS.md").exists():
        _DOCS_DIR = d
        break

DOCUMENTS = {
    "changelog": {"title": "Лента изменений", "filename": "CHANGELOG_CMS.md", "editable": True},
    "history": {"title": "Техническая история", "filename": "HISTORY_TECHNICAL.md", "editable": False},
}

# ── Pydantic models ──────────────────────────────────────────────────────────
class EntryIn(BaseModel):
    date: str = Field(..., description="DD.MM.YYYY")
    time: str = Field("12:00:00", description="HH:MM:SS")
    author: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    body: str = Field("", description="Markdown body text")
    also_history: bool = False


class EntryUpdate(BaseModel):
    date: str = Field(..., description="DD.MM.YYYY")
    time: str = Field("12:00:00", description="HH:MM:SS")
    author: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    body: str = Field("", description="Markdown body text")


# ── Helpers ─────────────────────────────────────────────────────────────────
_DAY_NAMES_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
_ENTRY_HEADER_RE = re.compile(
    r"^\[(\w+)\.(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}:\d{2}:\d{2})\]\s+(.+?):\s+(.+)$"
)


def _day_name_ru(d: datetime) -> str:
    return _DAY_NAMES_RU[d.weekday()]


def _parse_date(date_str: str) -> datetime | None:
    parts = date_str.split(".")
    if len(parts) != 3:
        return None
    try:
        return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        return None


def _parse_time(time_str: str) -> time_type | None:
    """Parse HH:MM:SS → time object, or None."""
    parts = time_str.split(":")
    if len(parts) < 2:
        return None
    try:
        return time_type(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except (ValueError, IndexError):
        return None


def _format_entry_header(day: str, date: str, time: str, author: str, title: str) -> str:
    return f"[{day}.{date} {time}] {author}: {title}"


def _file_path(name: str) -> Path:
    info = DOCUMENTS.get(name)
    if not info:
        raise ValueError(f"Unknown document: {name}")
    return _DOCS_DIR / info["filename"]


def _generate_md(entries: list[dict]) -> str:
    """Generate full CHANGELOG_CMS.md content from DB entries."""
    lines = ["# 📣 HexaVeil CMS — Лента изменений (с 14.09.2026)", ""]
    lines.append("> Лента в стиле релизных анонсов. Хронология: 100 коммитов, ~88 700 добавленных")
    lines.append("> и ~50 500 удалённых строк. Автор всех работ — ImCrazyMonk.")
    lines.append("> Техническая версия с хэшами и статистикой — `docs/HISTORY_TECHNICAL.md`.")
    lines.append("")
    lines.append("---")
    lines.append("")
    for i, entry in enumerate(entries):
        if i > 0:
            lines.append("")
        header_line = _format_entry_header(
            day=entry["day_of_week"],
            date=entry["date"],
            time=entry["time"],
            author=entry["author"],
            title=entry["title"],
        )
        lines.append(header_line)
        lines.append("")
        lines.append(entry.get("body", "").strip())
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Лента составлена автоматически из базы данных.*")
    return "\n".join(lines) + "\n"


def _parse_changelog_file(raw: str) -> list[dict]:
    """Parse CHANGELOG_CMS.md content into structured entry dicts."""
    lines = raw.split("\n")
    entries: list[dict] = []
    current: dict | None = None
    body_lines: list[str] = []

    for line in lines:
        m = _ENTRY_HEADER_RE.match(line)
        if m:
            if current is not None:
                current["body"] = "\n".join(body_lines).strip()
                entries.append(current)
            current = {
                "day_of_week": m.group(1),
                "date": f"{m.group(2)}.{m.group(3)}.{m.group(4)}",
                "time": m.group(5),
                "author": m.group(6),
                "title": m.group(7),
                "body": "",
            }
            body_lines = []
        elif current is not None:
            body_lines.append(line)

    if current is not None:
        current["body"] = "\n".join(body_lines).strip()
        entries.append(current)

    return entries


def _markdown_to_html(text: str) -> str:
    return md_lib.markdown(text, extensions=["tables", "fenced_code", "nl2br", "sane_lists"])


# ── DB helpers ──────────────────────────────────────────────────────────────
async def ensure_changelog_table() -> None:
    """Create changelog_entries table if not exists (idempotent)."""
    from web.backend.core.database import get_session_factory
    try:
        factory = await get_session_factory()
        async with factory() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS changelog_entries (
                    id SERIAL PRIMARY KEY,
                    day_of_week VARCHAR(2) NOT NULL,
                    entry_date DATE NOT NULL,
                    entry_time TIME NOT NULL DEFAULT '12:00:00',
                    author VARCHAR(255) NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            # Trigger for updated_at
            await session.execute(text("""
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_changelog_entries_updated_at') THEN
                        CREATE TRIGGER update_changelog_entries_updated_at
                        BEFORE UPDATE ON changelog_entries
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                    END IF;
                END $$;
            """))
            # Index
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_changelog_entries_sort
                ON changelog_entries(sort_order)
            """))
            await session.commit()
    except Exception as e:
        logger.warning("ensure_changelog_table failed: %s", e)


async def _import_file_to_db(db: AsyncSession, raw: str) -> int:
    """Parse CHANGELOG_CMS.md and insert entries into DB. Returns count."""
    entries = _parse_changelog_file(raw)
    if not entries:
        return 0

    # Clear existing data
    await db.execute(text("DELETE FROM changelog_entries"))
    max_order = len(entries) - 1

    for i, entry in enumerate(entries):
        parsed = _parse_date(entry["date"])
        if parsed is None:
            continue
        sort_order = max_order - i  # newest first
        await db.execute(
            text("""
                INSERT INTO changelog_entries (day_of_week, entry_date, entry_time, author, title, body, sort_order)
                VALUES (:day_of_week, :entry_date, :entry_time, :author, :title, :body, :sort_order)
            """),
            {
                "day_of_week": entry["day_of_week"],
                "entry_date": parsed.date(),
                "entry_time": _parse_time(entry["time"]) or time_type(12, 0),
                "author": entry["author"],
                "title": entry["title"],
                "body": entry["body"],
                "sort_order": sort_order,
            },
        )
    await db.commit()
    return len(entries)


# ── API Endpoints ────────────────────────────────────────────────────────────
@router.get("/docs/list")
async def list_docs(admin: AdminUser = Depends(get_current_admin)):
    data = [{"name": n, "title": i["title"], "editable": i["editable"]} for n, i in DOCUMENTS.items()]
    return {"success": True, "data": data}


@router.get("/docs/{name}")
async def get_doc(
    name: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Return document content (raw + html)."""
    info = DOCUMENTS.get(name)
    if not info:
        return {"success": False, "error": "Document not found", "code": "NOT_FOUND"}

    if name == "changelog":
        # Generate from DB
        rows = (await db.execute(
            text("SELECT day_of_week, entry_date, entry_time, author, title, body FROM changelog_entries ORDER BY sort_order ASC, id DESC")
        )).fetchall()
        entries = []
        for r in rows:
            d = r.entry_date
            entries.append({
                "day_of_week": r.day_of_week,
                "date": f"{d.day:02d}.{d.month:02d}.{d.year}",
                "time": str(r.entry_time),
                "author": r.author,
                "title": r.title,
                "body": r.body,
            })
        raw = _generate_md(entries)
        html = _markdown_to_html(raw)
        return {"success": True, "data": {"name": "changelog", "title": info["title"], "editable": True, "raw": raw, "html": f'<div class="prose max-w-none">{html}</div>'}}
        path = _file_path(name)
        if not path.exists():
            return {"success": False, "error": "File not found", "code": "NOT_FOUND"}
        raw = await asyncio.to_thread(path.read_text, encoding="utf-8")
        html = _markdown_to_html(raw)
        return {"success": True, "data": {"name": name, "title": info["title"], "editable": False, "raw": raw, "html": f'<div class="prose max-w-none">{html}</div>'}}


@router.get("/docs/{name}/entries")
async def list_entries(
    name: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    info = DOCUMENTS.get(name)
    if not info:
        return {"success": False, "error": "Document not found", "code": "NOT_FOUND"}

    if name == "changelog":
        # From DB
        rows = (await db.execute(
            text("SELECT id, day_of_week, entry_date, entry_time, author, title, body FROM changelog_entries ORDER BY sort_order ASC, id DESC")
        )).fetchall()
        result = []
        for r in rows:
            d = r.entry_date
            date_str = f"{d.day:02d}.{d.month:02d}.{d.year}"
            t = r.entry_time
            _t = t if hasattr(t, 'hour') else time_type(12, 0)
            time_str = f"{_t.hour:02d}:{_t.minute:02d}:{_t.second:02d}"
            result.append({
                "id": r.id,
                "day_of_week": r.day_of_week,
                "date": date_str,
                "time": time_str,
                "author": r.author,
                "title": r.title,
                "body": r.body,
            })
        return {"success": True, "data": {"name": "changelog", "title": info["title"], "editable": True, "header": "", "entries": result}}
    else:
        # From file (read-only)
        path = _file_path(name)
        if not path.exists():
            return {"success": False, "error": "File not found", "code": "NOT_FOUND"}
        raw = await asyncio.to_thread(path.read_text, encoding="utf-8")
        lines = raw.split("\n")
        # For history, just return the raw content as a single entry
        return {"success": True, "data": {"name": "history", "title": info["title"], "editable": False, "header": "", "entries": [{"id": 0, "day_of_week": "", "date": "", "time": "", "author": "", "title": "Техническая история", "body": raw}]}}


@router.post("/docs/{name}/entries", status_code=201)
async def create_entry(
    name: str,
    body: EntryIn,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    info = DOCUMENTS.get(name)
    if not info or not info["editable"]:
        return {"success": False, "error": "Document not found or read-only", "code": "FORBIDDEN"}

    parsed_date = _parse_date(body.date)
    if parsed_date is None:
        return {"success": False, "error": "Invalid date format. Use DD.MM.YYYY", "code": "INVALID_INPUT"}
    day_of_week = _day_name_ru(parsed_date)

    # Get max sort_order
    max_row = (await db.execute(text("SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_sort FROM changelog_entries"))).fetchone()
    next_sort = max_row.next_sort if max_row else 0

    row = await db.execute(
        text("""
            INSERT INTO changelog_entries (day_of_week, entry_date, entry_time, author, title, body, sort_order)
            VALUES (:day_of_week, :entry_date, :entry_time, :author, :title, :body, :sort_order)
            RETURNING id
        """),
        {
            "day_of_week": day_of_week,
            "entry_date": parsed_date.date(),
            "entry_time": _parse_time(body.time) or time_type(12, 0),
            "author": body.author,
            "title": body.title,
            "body": body.body.strip(),
            "sort_order": next_sort,
        },
    )
    await db.commit()
    new_id = row.fetchone()[0]

    return {"success": True, "data": {"id": new_id}}


@router.put("/docs/{name}/entries/{entry_id}")
async def update_entry(
    name: str,
    entry_id: int,
    body: EntryUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    info = DOCUMENTS.get(name)
    if not info or not info["editable"]:
        return {"success": False, "error": "Document not found or read-only", "code": "FORBIDDEN"}

    parsed_date = _parse_date(body.date)
    if parsed_date is None:
        return {"success": False, "error": "Invalid date format. Use DD.MM.YYYY", "code": "INVALID_INPUT"}
    day_of_week = _day_name_ru(parsed_date)

    result = await db.execute(
        text("""
            UPDATE changelog_entries
            SET day_of_week = :day_of_week,
                entry_date = :entry_date,
                entry_time = :entry_time,
                author = :author,
                title = :title,
                body = :body
            WHERE id = :id
        """),
        {
            "id": entry_id,
            "day_of_week": day_of_week,
            "entry_date": parsed_date.date(),
            "entry_time": _parse_time(body.time) or time_type(12, 0),
            "author": body.author,
            "title": body.title,
            "body": body.body.strip(),
        },
    )
    await db.commit()
    if result.rowcount == 0:
        return {"success": False, "error": "Entry not found", "code": "NOT_FOUND"}
    return {"success": True}


@router.delete("/docs/{name}/entries/{entry_id}")
async def delete_entry(
    name: str,
    entry_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    info = DOCUMENTS.get(name)
    if not info or not info["editable"]:
        return {"success": False, "error": "Document not found or read-only", "code": "FORBIDDEN"}

    result = await db.execute(
        text("DELETE FROM changelog_entries WHERE id = :id"),
        {"id": entry_id},
    )
    await db.commit()
    if result.rowcount == 0:
        return {"success": False, "error": "Entry not found", "code": "NOT_FOUND"}
    return {"success": True}


# ── Import / Export ──────────────────────────────────────────────────────────
@router.post("/docs/changelog/import")
async def import_changelog(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """Import entries from an uploaded CHANGELOG_CMS.md file.
    
    The file is parsed, existing DB data is replaced, and entries are stored.
    """
    content = await file.read()
    raw = content.decode("utf-8")
    count = await _import_file_to_db(db, raw)
    if count == 0:
        return {"success": False, "error": "No entries found in file", "code": "INVALID_INPUT"}
    return {"success": True, "data": {"imported": count}}


@router.get("/docs/changelog/export")
async def export_changelog(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Generate and download CHANGELOG_CMS.md from DB entries."""
    rows = (await db.execute(
        text("SELECT day_of_week, entry_date, entry_time, author, title, body FROM changelog_entries ORDER BY sort_order ASC, id DESC")
    )).fetchall()

    entries = []
    for r in rows:
        d = r.entry_date
        date_str = f"{d.day:02d}.{d.month:02d}.{d.year}"
        t = r.entry_time
        t = r.entry_time
        _t = t if hasattr(t, 'hour') else time_type(12, 0)
        time_str = f"{_t.hour:02d}:{_t.minute:02d}:{_t.second:02d}"
        entries.append({
            "day_of_week": r.day_of_week,
            "date": date_str,
            "time": time_str,
            "author": r.author,
            "title": r.title,
            "body": r.body,
        })

    md_content = _generate_md(entries)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"CHANGELOG_CMS_{now}.md"

    return StreamingResponse(
        io.BytesIO(md_content.encode("utf-8")),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def migrate_file_to_db() -> int:
    """On first run, import existing CHANGELOG_CMS.md into DB."""
    from web.backend.core.database import get_session_factory

    path = _file_path("changelog")
    if not path.exists():
        return 0

    try:
        raw = path.read_text(encoding="utf-8")
        entries = _parse_changelog_file(raw)
        if not entries:
            return 0

        factory = await get_session_factory()
        async with factory() as session:
            # Check if DB has data already
            existing = (await session.execute(text("SELECT COUNT(*) FROM changelog_entries"))).fetchone()
            if existing and existing[0] > 0:
                return 0  # already imported

            await _import_file_to_db(session, raw)
            logger.info("Migrated %d entries from CHANGELOG_CMS.md into DB", len(entries))
            return len(entries)
    except Exception as e:
        logger.warning("migrate_file_to_db failed: %s", e)
        return 0