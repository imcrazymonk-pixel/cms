"""Docs API — CHANGELOG_CMS.md in DB + editable HISTORY_TECHNICAL.md.

  GET    /api/docs                     → list of available documents
  GET    /api/docs/{name}              → document content (raw + html)
  GET    /api/docs/{name}/entries      → structured entries list
  POST   /api/docs/{name}/entries      → add new entry (DB, also_history for changelog)
  PUT    /api/docs/{name}/entries/{id} → edit entry (DB)
  DELETE /api/docs/{name}/entries/{id} → delete entry (DB)
  PUT    /api/docs/history             → replace history document (optimistic lock)
  POST   /api/docs/history/import      → replace history document from .md (multipart)
  GET    /api/docs/history/export      → export history document + appended blocks
  POST   /api/docs/changelog/import    → import entries from .md file (multipart)
  GET    /api/docs/changelog/export    → export entries as .md file download

Storage: `docs_documents` (base history document, edited as a whole) and
`history_entries` (append-blocks: manual + `also_history` copies of changelog
entries). Files are used as the initial seed and for exports only.
"""
import asyncio
import io
import json
import logging
import re
from datetime import date as date_type, datetime
from datetime import time as time_type
from pathlib import Path

import markdown as md_lib
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
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
    "history": {"title": "Техническая история", "filename": "HISTORY_TECHNICAL.md", "editable": True},
}

# Maximum size of the history document (chars / bytes of an uploaded .md file).
_MAX_DOCUMENT_BYTES = 1_000_000

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


class DocumentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=_MAX_DOCUMENT_BYTES)
    expected_updated_at: str | None = Field(
        None, description="ISO timestamp from the previous read (optimistic lock)"
    )


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


def _wrap_html(text: str) -> str:
    return f'<div class="prose max-w-none">{_markdown_to_html(text)}</div>'


# ── Section splitting (for the "technical history" reader) ──────────────────
_H1_RE = re.compile(r"^#\s+(.+?)\s*#*\s*$")
_H2_RE = re.compile(r"^##\s+(.+?)\s*#*\s*$")
_FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def _is_fence_close(line: str, char: str, length: int) -> bool:
    """True when `line` closes a fence opened with `char` repeated `length`+ times."""
    trimmed = line.strip()
    return len(trimmed) >= length and set(trimmed) == {char}


def _split_markdown_sections(raw: str) -> list[dict]:
    """Split markdown into ordered sections by `## ` (H2) headings.

    The leading part before the first H2 becomes a `level: 1` section titled by
    its first `# ` heading (or "Введение"). Each returned item is
    `{title, level, html}` where `html` is rendered from the section text
    *including* its own heading. Empty sections are dropped. `## ` inside a
    fenced code block does not split anything.
    """
    if not raw or not raw.strip():
        return []

    chunks: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in raw.split("\n"):
        if in_fence:
            current.append(line)
            if _is_fence_close(line, fence_char, fence_len):
                in_fence = False
            continue

        fence_match = _FENCE_OPEN_RE.match(line)
        if fence_match:
            in_fence = True
            fence_char = fence_match.group(1)[0]
            fence_len = len(fence_match.group(1))
            current.append(line)
            continue

        if _H2_RE.match(line):
            chunks.append(current)
            current = [line]
            continue

        current.append(line)
    chunks.append(current)

    sections: list[dict] = []
    for chunk in chunks:
        text = "\n".join(chunk).strip()
        if not text:
            continue

        first_line = next((line for line in chunk if line.strip()), "")
        h2_match = _H2_RE.match(first_line)
        if h2_match:
            title = h2_match.group(1).strip()
            level = 2
        else:
            h1_match = next(
                (m for m in (_H1_RE.match(line) for line in chunk) if m), None
            )
            title = h1_match.group(1).strip() if h1_match else "Введение"
            level = 1

        sections.append({
            "title": title or "Введение",
            "level": level,
            "html": _markdown_to_html(text),
        })
    return sections



def _iso(value) -> str | None:
    """Serialize a DB timestamp to ISO-8601 (or None)."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _same_timestamp(current, expected: str) -> bool:
    """Compare a DB timestamp with the client-provided `expected_updated_at`."""
    if not isinstance(current, datetime):
        return str(current) == expected
    try:
        exp = datetime.fromisoformat(expected.replace("Z", "+00:00"))
    except ValueError:
        return False
    cur = current
    # Tolerate a missing/extra tzinfo on either side (round-trip of isoformat()).
    if cur.tzinfo is not None and exp.tzinfo is None:
        cur = cur.replace(tzinfo=None)
    elif cur.tzinfo is None and exp.tzinfo is not None:
        exp = exp.replace(tzinfo=None)
    return cur == exp


# ── History document / append-blocks helpers ────────────────────────────────
def _format_history_block(entry: dict) -> str:
    """Render one history block (see plan §3).

    ### ДД.ММ.ГГГГ ЧЧ:ММ — <title>

    *Автор: <author> · источник: лента изменений #<id>*

    <body>
    """
    date_str = entry.get("date") or ""
    time_str = (entry.get("time") or "")[:5]
    title = entry.get("title") or ""
    author = entry.get("author") or ""
    source_id = entry.get("source_changelog_id")
    meta = f"*Автор: {author}"
    if source_id is not None:
        meta += f" · источник: лента изменений #{source_id}"
    meta += "*"

    lines = [f"### {date_str} {time_str} — {title}", "", meta, ""]
    body = (entry.get("body") or "").strip()
    if body:
        lines.append(body)
    return "\n".join(lines).rstrip("\n")


def _compose_history_md(document: str, blocks: list[dict]) -> str:
    """Document content + `## Дополнения` section built from history blocks."""
    doc = (document or "").rstrip("\n")
    if not blocks:
        return doc + "\n" if doc else ""
    section = "\n\n---\n\n## Дополнения\n\n" + "\n\n".join(
        _format_history_block(b) for b in blocks
    )
    return doc + section + "\n"


async def _read_history_file() -> str:
    """Read HISTORY_TECHNICAL.md (seed source). Missing file → empty string."""
    path = _file_path("history")
    if not path.exists():
        return ""
    try:
        return await asyncio.to_thread(path.read_text, encoding="utf-8")
    except OSError as e:
        logger.warning("read history file failed: %s", e)
        return ""


async def _get_history_document(db: AsyncSession) -> dict:
    """Return the history document as {raw, html, updated_at}.

    Empty DB → seed from HISTORY_TECHNICAL.md and return the stored row.
    """
    select_sql = text("SELECT content, updated_at FROM docs_documents WHERE name = 'history'")
    row = None
    try:
        row = (await db.execute(select_sql)).fetchone()
    except Exception as e:
        logger.warning("docs_documents read failed: %s", e)

    if row is None:
        raw = await _read_history_file()
        if raw:
            try:
                await db.execute(
                    text(
                        "INSERT INTO docs_documents (name, content) VALUES ('history', :content) "
                        "ON CONFLICT (name) DO NOTHING"
                    ),
                    {"content": raw},
                )
                await db.commit()
                row = (await db.execute(select_sql)).fetchone()
            except Exception as e:
                logger.warning("docs_documents seed failed: %s", e)
        if row is None:
            return {"raw": raw, "html": _wrap_html(raw), "updated_at": None}

    raw = row.content or ""
    return {"raw": raw, "html": _wrap_html(raw), "updated_at": _iso(row.updated_at)}


async def _history_entries(db: AsyncSession) -> list[dict]:
    """Append-blocks ordered by date, time, id (ASC)."""
    rows = (await db.execute(
        text(
            "SELECT id, entry_date, entry_time, author, title, body, origin, source_changelog_id "
            "FROM history_entries ORDER BY entry_date ASC, entry_time ASC, id ASC"
        )
    )).fetchall()

    result: list[dict] = []
    for r in rows:
        d = r.entry_date
        if hasattr(d, "day"):
            date_str = f"{d.day:02d}.{d.month:02d}.{d.year}"
        else:
            date_str = str(d)
        t = r.entry_time
        if hasattr(t, "hour"):
            time_str = f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}"
        else:
            time_str = str(t)
        result.append({
            "id": r.id,
            "date": date_str,
            "time": time_str,
            "author": r.author,
            "title": r.title,
            "body": r.body,
            "body_html": _markdown_to_html(r.body or ""),
            "origin": getattr(r, "origin", None) or "manual",
            "source_changelog_id": getattr(r, "source_changelog_id", None),
        })
    return result


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


async def ensure_docs_tables() -> None:
    """Create docs_documents + history_entries tables if not exist (idempotent).

    Mirrors db/postgres/migrations/005-docs-history.sql for runtime/CI-less setups.
    """
    from web.backend.core.database import get_session_factory
    try:
        factory = await get_session_factory()
        async with factory() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS docs_documents (
                    name TEXT PRIMARY KEY,
                    content TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """))
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS history_entries (
                    id SERIAL PRIMARY KEY,
                    entry_date DATE NOT NULL,
                    entry_time TIME NOT NULL DEFAULT '12:00:00',
                    author VARCHAR(255) NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL DEFAULT '',
                    origin VARCHAR(16) NOT NULL DEFAULT 'manual',
                    source_changelog_id INTEGER UNIQUE
                        REFERENCES changelog_entries(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_history_entries_date
                ON history_entries(entry_date, entry_time)
            """))
            await session.execute(text("""
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_history_entries_updated_at') THEN
                        CREATE TRIGGER update_history_entries_updated_at
                        BEFORE UPDATE ON history_entries
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                    END IF;
                END $$;
            """))
            await session.commit()
    except Exception as e:
        logger.warning("ensure_docs_tables failed: %s", e)


async def seed_history_document() -> int:
    """Seed docs_documents('history') from HISTORY_TECHNICAL.md.

    `ON CONFLICT (name) DO NOTHING` — the DB wins after the first edit.
    Errors are logged only; returns number of inserted rows (0/1).
    """
    from web.backend.core.database import get_session_factory

    raw = await _read_history_file()
    if not raw:
        return 0
    try:
        factory = await get_session_factory()
        async with factory() as session:
            result = await session.execute(
                text(
                    "INSERT INTO docs_documents (name, content) VALUES ('history', :content) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {"content": raw},
            )
            await session.commit()
            return result.rowcount or 0
    except Exception as e:
        logger.warning("seed_history_document failed: %s", e)
        return 0


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


@router.post("/docs/render")
async def render_markdown(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
):
    """Render arbitrary markdown with the same engine as the documents.

    Body: `{"markdown": "<text>"}` (≤ 1 МБ, empty allowed). Returns
    `{"success": true, "data": {"html": "<rendered>"}}` — no HTML wrapper, the
    UI adds its own `prose` container. This is the single renderer behind the
    editor preview, so preview and page always match.
    """
    raw = await request.body()
    if len(raw) > _MAX_DOCUMENT_BYTES + 1024:
        return api_error(413, E.FILE_TOO_LARGE, "Markdown больше 1 МБ")

    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        return api_error(400, E.INVALID_INPUT, "Ожидается корректный JSON")
    if not isinstance(payload, dict):
        return api_error(400, E.INVALID_INPUT, "Ожидается JSON-объект")

    markdown = payload.get("markdown", "")
    if markdown is None:
        markdown = ""
    if not isinstance(markdown, str):
        return api_error(400, E.INVALID_INPUT, "Поле markdown должно быть строкой")
    if len(markdown.encode("utf-8")) > _MAX_DOCUMENT_BYTES:
        return api_error(413, E.FILE_TOO_LARGE, "Markdown больше 1 МБ")

    try:
        html = _markdown_to_html(markdown)
    except Exception as e:  # curious input must not 500 the UI preview
        logger.warning("markdown render failed: %s", e)
        return api_error(400, E.INVALID_INPUT, "Не удалось обработать markdown")

    return {"success": True, "data": {"html": html}}


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

    # history — base document lives in docs_documents (seeded from the file)
    try:
        doc = await _get_history_document(db)
    except Exception as e:
        logger.error("history document read failed: %s", e)
        return api_error(500, E.DB_ERROR, "Не удалось прочитать документ")

    return {"success": True, "data": {
        "name": "history",
        "title": info["title"],
        "editable": True,
        "raw": doc["raw"],
        "html": doc["html"],
        "sections": _split_markdown_sections(doc["raw"]),
        "updated_at": doc["updated_at"],
    }}


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
    # history — document (raw/html/updated_at) + append-blocks
    try:
        doc = await _get_history_document(db)
        blocks = await _history_entries(db)
    except Exception as e:
        logger.error("history entries read failed: %s", e)
        return api_error(500, E.DB_ERROR, "Не удалось прочитать историю")

    return {"success": True, "data": {
        "name": "history",
        "title": info["title"],
        "editable": True,
        "header": "",
        "document": doc,
        "sections": _split_markdown_sections(doc["raw"]),
        "entries": blocks,
    }}


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
    entry_time = _parse_time(body.time) or time_type(12, 0)

    if name == "history":
        # Manual append-block (`also_history` is ignored here — it is changelog-only)
        try:
            row = await db.execute(
                text("""
                    INSERT INTO history_entries (entry_date, entry_time, author, title, body, origin)
                    VALUES (:entry_date, :entry_time, :author, :title, :body, 'manual')
                    RETURNING id
                """),
                {
                    "entry_date": parsed_date.date(),
                    "entry_time": entry_time,
                    "author": body.author,
                    "title": body.title,
                    "body": body.body.strip(),
                },
            )
            new_id = row.fetchone()[0]
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error("history entry insert failed: %s", e)
            return api_error(500, E.DB_ERROR, "Не удалось сохранить запись")
        return {"success": True, "data": {"id": new_id}}

    day_of_week = _day_name_ru(parsed_date)

    try:
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
                "entry_time": entry_time,
                "author": body.author,
                "title": body.title,
                "body": body.body.strip(),
                "sort_order": next_sort,
            },
        )
        new_id = row.fetchone()[0]

        if body.also_history:
            # Same transaction: a failed history insert rolls the changelog entry back.
            await db.execute(
                text("""
                    INSERT INTO history_entries
                        (entry_date, entry_time, author, title, body, origin, source_changelog_id)
                    VALUES
                        (:entry_date, :entry_time, :author, :title, :body, 'changelog', :source_changelog_id)
                    ON CONFLICT (source_changelog_id) DO NOTHING
                """),
                {
                    "entry_date": parsed_date.date(),
                    "entry_time": entry_time,
                    "author": body.author,
                    "title": body.title,
                    "body": body.body.strip(),
                    "source_changelog_id": new_id,
                },
            )

        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("changelog entry insert failed: %s", e)
        return api_error(500, E.DB_ERROR, "Не удалось сохранить запись")

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
    entry_time = _parse_time(body.time) or time_type(12, 0)

    if name == "history":
        try:
            result = await db.execute(
                text("""
                    UPDATE history_entries
                    SET entry_date = :entry_date,
                        entry_time = :entry_time,
                        author = :author,
                        title = :title,
                        body = :body
                    WHERE id = :id
                """),
                {
                    "id": entry_id,
                    "entry_date": parsed_date.date(),
                    "entry_time": entry_time,
                    "author": body.author,
                    "title": body.title,
                    "body": body.body.strip(),
                },
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error("history entry update failed: %s", e)
            return api_error(500, E.DB_ERROR, "Не удалось обновить запись")
        if result.rowcount == 0:
            return api_error(404, E.NOT_FOUND, "Запись не найдена")
        return {"success": True}

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
            "entry_time": entry_time,
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

    table = "history_entries" if name == "history" else "changelog_entries"
    try:
        result = await db.execute(
            text(f"DELETE FROM {table} WHERE id = :id"),
            {"id": entry_id},
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("%s entry delete failed: %s", table, e)
        return api_error(500, E.DB_ERROR, "Не удалось удалить запись")

    if result.rowcount == 0:
        if name == "history":
            return api_error(404, E.NOT_FOUND, "Запись не найдена")
        return {"success": False, "error": "Entry not found", "code": "NOT_FOUND"}
    return {"success": True}


# ── History document: replace / import / export ──────────────────────────────
@router.put("/docs/history")
async def update_history_document(
    body: DocumentUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Replace the history document content (optimistic lock → 409 on stale)."""
    select_sql = text("SELECT updated_at FROM docs_documents WHERE name = 'history'")
    try:
        row = (await db.execute(select_sql)).fetchone()
        if row is None:
            # First write before seed — seed from the file, then retry once.
            raw = await _read_history_file()
            await db.execute(
                text(
                    "INSERT INTO docs_documents (name, content) VALUES ('history', :content) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {"content": raw},
            )
            await db.commit()
            row = (await db.execute(select_sql)).fetchone()
        if row is None:
            return api_error(404, E.NOT_FOUND, "Документ не найден")

        current = row.updated_at

        if body.expected_updated_at is not None:
            try:
                datetime.fromisoformat(body.expected_updated_at.replace("Z", "+00:00"))
            except ValueError:
                return api_error(400, E.INVALID_INPUT, "Некорректный expected_updated_at")
            if not _same_timestamp(current, body.expected_updated_at):
                return api_error(409, E.CONFLICT, "Документ был изменён. Перезагрузите его.")

        result = await db.execute(
            text("""
                UPDATE docs_documents
                SET content = :content, updated_at = now()
                WHERE name = 'history' AND updated_at = :current
            """),
            {"content": body.content, "current": current},
        )
        if result.rowcount == 0:
            await db.rollback()
            return api_error(409, E.CONFLICT, "Документ был изменён. Перезагрузите его.")
        await db.commit()

        row = (await db.execute(select_sql)).fetchone()
    except Exception as e:
        await db.rollback()
        logger.error("history document update failed: %s", e)
        return api_error(500, E.DB_ERROR, "Не удалось сохранить документ")

    return {"success": True, "data": {"updated_at": _iso(row.updated_at if row else None)}}


@router.post("/docs/history/import")
async def import_history_document(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """Replace the history document content from an uploaded .md file.

    Append-blocks in `history_entries` are not touched.
    """
    content = await file.read(_MAX_DOCUMENT_BYTES + 1)
    if len(content) > _MAX_DOCUMENT_BYTES:
        return api_error(413, E.FILE_TOO_LARGE, "Файл больше 1 МБ")
    if file.filename and not file.filename.lower().endswith(".md"):
        return api_error(400, E.INVALID_INPUT, "Ожидается файл .md")

    try:
        raw = content.decode("utf-8")
    except UnicodeDecodeError:
        return api_error(400, E.INVALID_INPUT, "Файл должен быть в кодировке UTF-8")
    if not raw.strip():
        return api_error(400, E.INVALID_INPUT, "Файл пуст")

    select_sql = text("SELECT updated_at FROM docs_documents WHERE name = 'history'")
    try:
        await db.execute(
            text("""
                INSERT INTO docs_documents (name, content) VALUES ('history', :content)
                ON CONFLICT (name) DO UPDATE SET content = EXCLUDED.content, updated_at = now()
            """),
            {"content": raw},
        )
        await db.commit()
        row = (await db.execute(select_sql)).fetchone()
    except Exception as e:
        await db.rollback()
        logger.error("history document import failed: %s", e)
        return api_error(500, E.DB_ERROR, "Не удалось импортировать документ")

    return {"success": True, "data": {
        "updated_at": _iso(row.updated_at if row else None),
        "chars": len(raw),
    }}


@router.get("/docs/history/export")
async def export_history_document(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Download the history document with the `## Дополнения` section appended."""
    try:
        doc = await _get_history_document(db)
        blocks = await _history_entries(db)
    except Exception as e:
        logger.error("history document export failed: %s", e)
        return api_error(500, E.DB_ERROR, "Не удалось экспортировать документ")

    md_content = _compose_history_md(doc["raw"], blocks)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"HISTORY_TECHNICAL_{now}.md"

    return StreamingResponse(
        io.BytesIO(md_content.encode("utf-8")),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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