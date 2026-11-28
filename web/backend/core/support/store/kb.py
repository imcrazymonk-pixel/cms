"""Raw-SQL access to the support knowledge base (plan §2.2, §2.6, §5.1).

Style follows ``store/*``: functions take an ``AsyncSession`` and **never
commit** — the ``SupportStore`` facade owns the transaction. SQL identifiers
are controlled constants; every value is a bound parameter.

Tables (004 + 006):

* ``support_kb_doc`` — articles: id, source, ext_id, title, body, slug,
  status, version, tags, updated_by, published_at, archived_at, updated_at.
  ``ext_id`` is NOT NULL and UNIQUE(source, ext_id); this module keeps it in
  sync with ``slug`` so the legacy column stays satisfied.
* ``support_kb_candidate`` — article ideas; accepting one creates a draft
  article with ``source='candidate'`` and links ``doc_id``.

FTS: ``to_tsvector('russian', …)`` + ``websearch_to_tsquery`` + ``ts_rank_cd``
(see :mod:`web.backend.core.support.kb.fts`). Search is restricted to
``status='published'`` — drafts and archived articles must never leak into
operator or AI answers.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.support.kb.fts import (
    MAX_SLUG_LEN,
    build_query,
    rank_sql,
    search_predicate,
    slugify,
)

_UTC = timezone.utc

STATUSES = ("draft", "published", "archived")
SOURCES = ("manual", "import", "candidate", "faq")
CANDIDATE_STATUSES = ("new", "accepted", "rejected")

MAX_PER_PAGE = 100
MAX_SEARCH_LIMIT = 20
MAX_CONTEXT_LIMIT = 20
MAX_TAGS = 20
MAX_TAG_LEN = 64
EXCERPT_LEN = 200
SNIPPET_LEN = 300

_DOC_COLUMNS = (
    "id, slug, title, body, status, version, tags, source, updated_by, "
    "published_at, archived_at, updated_at"
)
_SEARCH_SQL = (
    f"SELECT d.id, d.slug, d.title, d.body, {rank_sql('d.')} AS rank "
    "FROM support_kb_doc d "
    "WHERE d.status = 'published' "
    f"AND {search_predicate('d.')} "
    "ORDER BY rank DESC, d.updated_at DESC "
    "LIMIT :limit"
)
_CONTEXT_SQL = (
    f"SELECT d.id AS doc_id, d.title, d.body, {rank_sql('d.')} AS rank "
    "FROM support_kb_doc d "
    "WHERE d.status = 'published' "
    f"AND {search_predicate('d.')} "
    "ORDER BY rank DESC, d.updated_at DESC "
    "LIMIT :limit"
)

_WHITESPACE_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[0-9a-zA-Zа-яА-ЯёЁ]+")
_MARKUP_RE = re.compile(r"[#*_`>]+")


class KbError(Exception):
    """Base class for knowledge-base store errors."""


class KbNotFound(KbError):
    """Article/candidate does not exist."""


class KbVersionConflict(KbError):
    """``expected_version`` does not match the stored version."""

    def __init__(self, current_version: int):
        self.current_version = int(current_version)
        super().__init__(f"version conflict: current version is {self.current_version}")


class KbDocPublished(KbError):
    """Published articles must be archived before deletion."""


def _now() -> datetime:
    return datetime.now(_UTC)


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row._mapping)
    tags = data.get("tags")
    if tags is None:
        data["tags"] = []
    elif isinstance(tags, str):
        # Defensive: a text[] returned as a literal by a non-asyncpg driver.
        data["tags"] = [part for part in tags.strip("{}").split(",") if part]
    else:
        data["tags"] = list(tags)
    return data


def _normalize_tags(tags: Iterable[Any] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in tags or []:
        value = str(raw or "").strip()[:MAX_TAG_LEN]
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= MAX_TAGS:
            break
    return result


def _pg_text_array(values: Sequence[str]) -> str:
    """Serialize a list to a PostgreSQL array literal for ``CAST(:x AS text[])``."""
    if not values:
        return "{}"

    def escape(value: str) -> str:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    return "{" + ",".join(escape(str(value)) for value in values) + "}"


def _with_suffix(base: str, number: int) -> str:
    suffix = f"-{number}"
    keep = max(1, MAX_SLUG_LEN - len(suffix))
    return f"{base[:keep].rstrip('-')}{suffix}"


def _pick_slug(base: str, used: Iterable[str]) -> str:
    """Choose a unique slug from ``base``, ``base-2``, ``base-3``, …."""
    normalized = slugify(base)
    used_set = set(used or ())
    if normalized not in used_set:
        return normalized
    for number in range(2, 10_000):
        candidate = _with_suffix(normalized, number)
        if candidate not in used_set:
            return candidate
    return _with_suffix(f"{normalized[:60]}-{uuid.uuid4().hex[:8]}", 2)[:MAX_SLUG_LEN]


async def _unique_slug(
    db: AsyncSession,
    base: str,
    *,
    exclude_id: int | None = None,
) -> str:
    rows = (
        await db.execute(
            sql_text(
                "SELECT slug FROM support_kb_doc "
                "WHERE slug IS NOT NULL AND (CAST(:exclude_id AS bigint) IS NULL OR id <> CAST(:exclude_id AS bigint))"
            ),
            {"exclude_id": exclude_id},
        )
    ).fetchall()
    used = {row.slug for row in rows if row.slug}
    return _pick_slug(base, used)


def _validate_source(source: str) -> str:
    value = (source or "manual").strip().lower()
    if value not in SOURCES:
        raise ValueError(f"unknown knowledge-base source: {source!r}")
    return value


def _require_text(value: str | None, field: str, *, max_len: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must not be empty")
    if len(text) > max_len:
        raise ValueError(f"{field} is too long")
    return text


async def _fetch_doc(
    db: AsyncSession,
    doc_id: int,
    columns: str = _DOC_COLUMNS,
) -> dict[str, Any] | None:
    row = (
        await db.execute(
            sql_text(f"SELECT {columns} FROM support_kb_doc WHERE id = :id"),
            {"id": int(doc_id)},
        )
    ).fetchone()
    return _row_to_dict(row)


async def create_doc(
    db: AsyncSession,
    *,
    title: str,
    body: str,
    slug: str | None = None,
    tags: Iterable[Any] | None = None,
    source: str = "manual",
    updated_by: int | None = None,
) -> dict[str, Any]:
    """Create a draft article; the store allocates a unique slug."""
    clean_title = _require_text(title, "title", max_len=200)
    clean_body = _require_text(body, "body", max_len=200_000)
    clean_source = _validate_source(source)
    final_slug = await _unique_slug(db, slug or clean_title)
    clean_tags = _normalize_tags(tags)

    row = (
        await db.execute(
            sql_text(
                """
                INSERT INTO support_kb_doc (
                    source, ext_id, title, body, slug, status, version, tags,
                    updated_by, updated_at
                ) VALUES (
                    :source, :ext_id, :title, :body, :slug, 'draft', 1,
                    CAST(:tags AS text[]), :updated_by, now()
                )
                RETURNING id, slug, version, status, updated_at
                """
            ),
            {
                "source": clean_source,
                "ext_id": final_slug,
                "title": clean_title,
                "body": clean_body,
                "slug": final_slug,
                "tags": _pg_text_array(clean_tags),
                "updated_by": updated_by,
            },
        )
    ).fetchone()
    return dict(row._mapping)


async def get_doc(db: AsyncSession, doc_id: int) -> dict[str, Any] | None:
    """Full article (body included) or ``None``."""
    doc = await _fetch_doc(db, doc_id)
    if doc is not None and "created_at" not in doc:
        # 004 never added created_at; updated_at is a safe proxy for the API
        # contract until a dedicated column ships.
        doc["created_at"] = doc.get("updated_at")
    return doc


async def update_doc(
    db: AsyncSession,
    doc_id: int,
    *,
    title: str | None = None,
    body: str | None = None,
    slug: str | None = None,
    tags: Iterable[Any] | None = None,
    expected_version: int | None = None,
    updated_by: int | None = None,
) -> dict[str, Any]:
    """Update an article in place (published stays published).

    Optimistic lock: ``expected_version`` must match; a stale editor gets
    :class:`KbVersionConflict`. The version is always bumped on success.
    """
    current = await _fetch_doc(db, doc_id, "id, version, status, slug")
    if current is None:
        raise KbNotFound(f"article {doc_id} not found")

    stored_version = int(current["version"])
    expected = stored_version if expected_version is None else int(expected_version)
    if expected != stored_version:
        raise KbVersionConflict(stored_version)

    updates: list[str] = ["version = version + 1", "updated_at = now()"]
    params: dict[str, Any] = {"id": int(doc_id), "current_version": stored_version}

    if title is not None:
        params["title"] = _require_text(title, "title", max_len=200)
        updates.append("title = :title")
    if body is not None:
        params["body"] = _require_text(body, "body", max_len=200_000)
        updates.append("body = :body")
    if slug is not None:
        params["slug"] = await _unique_slug(db, slug, exclude_id=int(doc_id))
        updates.append("slug = :slug")
    if tags is not None:
        params["tags"] = _pg_text_array(_normalize_tags(tags))
        updates.append("tags = CAST(:tags AS text[])")
    if updated_by is not None:
        params["updated_by"] = updated_by
        updates.append("updated_by = :updated_by")

    row = (
        await db.execute(
            sql_text(
                f"UPDATE support_kb_doc SET {', '.join(updates)} "
                "WHERE id = :id AND version = :current_version "
                "RETURNING id, slug, version, status, updated_at"
            ),
            params,
        )
    ).fetchone()
    if row is None:
        latest = await _fetch_doc(db, doc_id, "id, version")
        raise KbVersionConflict(int(latest["version"]) if latest else stored_version)
    return dict(row._mapping)


async def publish_doc(
    db: AsyncSession,
    doc_id: int,
    *,
    expected_version: int | None = None,
    updated_by: int | None = None,
) -> dict[str, Any]:
    """Publish a draft (or re-publish an archived article)."""
    current = await _fetch_doc(db, doc_id, "id, version, status, published_at")
    if current is None:
        raise KbNotFound(f"article {doc_id} not found")

    stored_version = int(current["version"])
    expected = stored_version if expected_version is None else int(expected_version)
    if expected != stored_version:
        raise KbVersionConflict(stored_version)

    if current["status"] == "published":
        return {
            "id": int(current["id"]),
            "status": "published",
            "published_at": current.get("published_at"),
        }

    row = (
        await db.execute(
            sql_text(
                "UPDATE support_kb_doc SET status = 'published', published_at = now(), "
                "archived_at = NULL, version = version + 1, updated_at = now(), "
                "updated_by = COALESCE(:updated_by, updated_by) "
                "WHERE id = :id AND version = :current_version "
                "RETURNING id, status, published_at, version"
            ),
            {
                "id": int(doc_id),
                "current_version": stored_version,
                "updated_by": updated_by,
            },
        )
    ).fetchone()
    if row is None:
        latest = await _fetch_doc(db, doc_id, "id, version")
        raise KbVersionConflict(int(latest["version"]) if latest else stored_version)
    data = dict(row._mapping)
    data.pop("version", None)
    return data


async def archive_doc(
    db: AsyncSession,
    doc_id: int,
    *,
    updated_by: int | None = None,
) -> dict[str, Any]:
    """Move an article to ``archived`` (idempotent)."""
    current = await _fetch_doc(db, doc_id, "id, version, status, archived_at")
    if current is None:
        raise KbNotFound(f"article {doc_id} not found")
    if current["status"] == "archived":
        return {
            "id": int(current["id"]),
            "status": "archived",
            "archived_at": current.get("archived_at"),
        }

    row = (
        await db.execute(
            sql_text(
                "UPDATE support_kb_doc SET status = 'archived', archived_at = now(), "
                "version = version + 1, updated_at = now(), "
                "updated_by = COALESCE(:updated_by, updated_by) "
                "WHERE id = :id AND version = :current_version "
                "RETURNING id, status, archived_at"
            ),
            {
                "id": int(doc_id),
                "current_version": int(current["version"]),
                "updated_by": updated_by,
            },
        )
    ).fetchone()
    if row is None:
        latest = await _fetch_doc(db, doc_id, "id, version")
        raise KbVersionConflict(int(latest["version"]) if latest else int(current["version"]))
    return dict(row._mapping)


async def restore_doc(
    db: AsyncSession,
    doc_id: int,
    *,
    updated_by: int | None = None,
) -> dict[str, Any]:
    """Return an archived article to ``draft``.

    Published articles are deliberately left untouched: unpublishing is a
    separate, explicit action (archive first).
    """
    current = await _fetch_doc(db, doc_id, "id, version, status")
    if current is None:
        raise KbNotFound(f"article {doc_id} not found")
    if current["status"] != "archived":
        return {"id": int(current["id"]), "status": current["status"]}

    row = (
        await db.execute(
            sql_text(
                "UPDATE support_kb_doc SET status = 'draft', archived_at = NULL, "
                "published_at = NULL, version = version + 1, updated_at = now(), "
                "updated_by = COALESCE(:updated_by, updated_by) "
                "WHERE id = :id AND version = :current_version "
                "RETURNING id, status"
            ),
            {
                "id": int(doc_id),
                "current_version": int(current["version"]),
                "updated_by": updated_by,
            },
        )
    ).fetchone()
    if row is None:
        latest = await _fetch_doc(db, doc_id, "id, version")
        raise KbVersionConflict(int(latest["version"]) if latest else int(current["version"]))
    return dict(row._mapping)


async def delete_doc(db: AsyncSession, doc_id: int) -> bool:
    """Delete a non-published article; published ones raise."""
    current = await _fetch_doc(db, doc_id, "id, status")
    if current is None:
        raise KbNotFound(f"article {doc_id} not found")
    if current["status"] == "published":
        raise KbDocPublished(f"article {doc_id} is published; archive it first")

    row = (
        await db.execute(
            sql_text(
                "DELETE FROM support_kb_doc WHERE id = :id AND status <> 'published' "
                "RETURNING id"
            ),
            {"id": int(doc_id)},
        )
    ).fetchone()
    if row is None:
        latest = await _fetch_doc(db, doc_id, "id, status")
        if latest is not None and latest.get("status") == "published":
            raise KbDocPublished(f"article {doc_id} is published; archive it first")
        raise KbNotFound(f"article {doc_id} not found")
    return True


def _like_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def list_docs(
    db: AsyncSession,
    *,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """Admin list: ``status=None``/``published`` → published only.

    ``status='all'`` removes the status filter (drafts + archived included).
    """
    page = max(int(page or 1), 1)
    per_page = min(max(int(per_page or 20), 1), MAX_PER_PAGE)

    where: list[str] = []
    params: dict[str, Any] = {}
    if status not in (None, "all"):
        if status not in STATUSES:
            raise ValueError(f"unknown article status: {status!r}")
        where.append("status = :status")
        params["status"] = status
    elif status is None:
        where.append("status = 'published'")

    query = build_query(q or "")
    if query:
        where.append(
            "(title ILIKE :q OR body ILIKE :q OR coalesce(slug, '') ILIKE :q)"
        )
        params["q"] = _like_pattern(query)

    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    total = int(
        (
            await db.execute(
                sql_text(f"SELECT COUNT(*) AS total FROM support_kb_doc{where_sql}"),
                params,
            )
        ).fetchone().total
    )

    offset = (page - 1) * per_page
    rows = (
        await db.execute(
            sql_text(
                "SELECT id, slug, title, source, status, version, updated_at, updated_by, "
                "LEFT(regexp_replace(coalesce(body, ''), '[[:space:]]+', ' ', 'g'), "
                f"{EXCERPT_LEN}) AS excerpt "
                f"FROM support_kb_doc{where_sql} "
                "ORDER BY updated_at DESC, id DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": per_page, "offset": offset},
        )
    ).fetchall()
    return {
        "items": [dict(row._mapping) for row in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def _snippet(body: str | None, query: str, limit: int = SNIPPET_LEN) -> str:
    """Plain-text snippet ≤ ``limit`` characters around the earliest match."""
    text = _MARKUP_RE.sub(" ", body or "")
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if not text:
        return ""

    terms = [word.lower() for word in _WORD_RE.findall(query or "") if len(word) >= 3]
    lowered = text.lower()
    best: int | None = None
    for term in terms:
        # Prefix match approximates stemming: «подключение» ↔ «подключается».
        stem = term[:5] if len(term) > 5 else term
        index = lowered.find(stem)
        if index >= 0 and (best is None or index < best):
            best = index

    start = max(0, (best or 0) - 40)
    window = text[start : start + limit]
    if start > 0:
        window = "…" + window[1:]
    if start + limit < len(text):
        window = window[: limit - 1] + "…"
    return window[:limit]


async def search_docs(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Operator search over **published** articles only.

    Returns ``[{id, slug, title, rank, snippet}]``; ``snippet`` is plain text
    no longer than 300 characters.
    """
    normalized = build_query(query)
    if not normalized:
        return []
    limit = min(max(int(limit or 10), 1), MAX_SEARCH_LIMIT)

    rows = (
        await db.execute(sql_text(_SEARCH_SQL), {"q": normalized, "limit": limit})
    ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        data = dict(row._mapping)
        items.append(
            {
                "id": int(data["id"]),
                "slug": data.get("slug"),
                "title": data.get("title"),
                "rank": float(data.get("rank") or 0.0),
                "snippet": _snippet(data.get("body"), normalized),
            }
        )
    return items


async def get_published_context(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Top-N published articles for the AI prompt (body included)."""
    normalized = build_query(query)
    if not normalized:
        return []
    limit = min(max(int(limit or 8), 1), MAX_CONTEXT_LIMIT)

    rows = (
        await db.execute(sql_text(_CONTEXT_SQL), {"q": normalized, "limit": limit})
    ).fetchall()
    return [
        {
            "doc_id": int(row._mapping["doc_id"]),
            "title": row._mapping["title"],
            "body": row._mapping["body"],
            "rank": float(row._mapping["rank"] or 0.0),
        }
        for row in rows
    ]


async def list_candidates(
    db: AsyncSession,
    *,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """Article ideas with optional status filter and pagination."""
    page = max(int(page or 1), 1)
    per_page = min(max(int(per_page or 20), 1), MAX_PER_PAGE)

    where: list[str] = []
    params: dict[str, Any] = {}
    if status not in (None, "all"):
        if status not in CANDIDATE_STATUSES:
            raise ValueError(f"unknown candidate status: {status!r}")
        where.append("status = :status")
        params["status"] = status

    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    total = int(
        (
            await db.execute(
                sql_text(f"SELECT COUNT(*) AS total FROM support_kb_candidate{where_sql}"),
                params,
            )
        ).fetchone().total
    )

    offset = (page - 1) * per_page
    rows = (
        await db.execute(
            sql_text(
                "SELECT id, topic, question, answer, occurrences, source, status, "
                "created_at, decided_at, decided_by, doc_id, reason "
                f"FROM support_kb_candidate{where_sql} "
                "ORDER BY occurrences DESC, created_at DESC, id DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": per_page, "offset": offset},
        )
    ).fetchall()
    items = []
    for row in rows:
        data = dict(row._mapping)
        items.append(
            {
                "id": int(data["id"]),
                "topic": data.get("topic"),
                "question": data.get("question"),
                "answer": data.get("answer"),
                "occurrences": int(data.get("occurrences") or 1),
                "source": data.get("source"),
                "status": data.get("status"),
                "created_at": data.get("created_at"),
                "doc_id": data.get("doc_id"),
            }
        )
    return {"items": items, "total": total, "page": page, "per_page": per_page}


async def create_candidate(
    db: AsyncSession,
    *,
    question: str,
    answer: str | None = None,
    source: str = "feedback",
    topic: str | None = None,
    title: str | None = None,
    file_name: str | None = None,
) -> int:
    """Record an article idea; repeated ``feedback`` topics bump ``occurrences``.

    ``support_kb_candidate`` has legacy NOT NULL ``title``/``file_name``
    columns (004) and a partial unique index on ``topic`` where
    ``status='new'`` (006), so the insert is an upsert on that index.
    """
    clean_question = _require_text(question, "question", max_len=4000)
    clean_answer = str(answer or "").strip()[:8000] or None
    clean_source = (source or "feedback").strip().lower()[:32] or "feedback"
    digest = hashlib.sha1(clean_question.lower().encode("utf-8")).hexdigest()[:16]
    topic_value = (str(topic or "").strip() or f"feedback-{digest}")[:200]
    title_value = (str(title or "").strip() or clean_question)[:200]
    file_value = (str(file_name or "").strip() or f"feedback-{digest}.md")[:200]

    row = (
        await db.execute(
            sql_text(
                """
                INSERT INTO support_kb_candidate (
                    title, file_name, source, status, question, answer, topic,
                    occurrences
                ) VALUES (
                    :title, :file_name, :source, 'new', :question, :answer, :topic, 1
                )
                ON CONFLICT (topic) WHERE status = 'new'
                DO UPDATE SET
                    occurrences = support_kb_candidate.occurrences + 1,
                    question = EXCLUDED.question,
                    answer = COALESCE(EXCLUDED.answer, support_kb_candidate.answer)
                RETURNING id
                """
            ),
            {
                "title": title_value,
                "file_name": file_value,
                "source": clean_source,
                "question": clean_question,
                "answer": clean_answer,
                "topic": topic_value,
            },
        )
    ).fetchone()
    return int(row._mapping["id"])


async def _fetch_candidate(db: AsyncSession, candidate_id: int) -> dict[str, Any] | None:
    row = (
        await db.execute(
            sql_text(
                "SELECT id, title, topic, question, answer, source, status, doc_id, "
                "occurrences FROM support_kb_candidate WHERE id = :id"
            ),
            {"id": int(candidate_id)},
        )
    ).fetchone()
    return _row_to_dict(row)


async def decide_candidate(
    db: AsyncSession,
    candidate_id: int,
    *,
    decision: str,
    reason: str | None = None,
    title: str | None = None,
    body: str | None = None,
    updated_by: int | None = None,
) -> dict[str, Any]:
    """Accept (create a draft article + link ``doc_id``) or reject an idea."""
    decision = (decision or "").strip().lower()
    if decision not in ("accept", "reject"):
        raise ValueError(f"unknown candidate decision: {decision!r}")

    candidate = await _fetch_candidate(db, candidate_id)
    if candidate is None:
        raise KbNotFound(f"candidate {candidate_id} not found")

    if decision == "accept" and candidate.get("doc_id"):
        return {
            "id": int(candidate["id"]),
            "status": candidate.get("status") or "accepted",
            "doc_id": int(candidate["doc_id"]),
        }

    decided_by = str(updated_by) if updated_by is not None else None

    if decision == "accept":
        doc_title = (
            (title or "").strip()
            or str(candidate.get("title") or "").strip()
            or str(candidate.get("topic") or "").strip()
            or "Статья"
        )
        doc_body = (body or "").strip()
        if not doc_body:
            parts = [
                str(part).strip()
                for part in (candidate.get("question"), candidate.get("answer"))
                if part and str(part).strip()
            ]
            doc_body = "\n\n".join(parts)
        if not doc_body:
            doc_body = doc_title

        tags = [candidate["topic"]] if candidate.get("topic") else None
        doc = await create_doc(
            db,
            title=doc_title,
            body=doc_body,
            tags=tags,
            source="candidate",
            updated_by=updated_by,
        )
        doc_id = int(doc["id"])
        row = (
            await db.execute(
                sql_text(
                    "UPDATE support_kb_candidate SET status = 'accepted', reason = :reason, "
                    "decided_at = now(), decided_by = :decided_by, doc_id = :doc_id "
                    "WHERE id = :id RETURNING id, status, doc_id"
                ),
                {
                    "id": int(candidate_id),
                    "reason": reason,
                    "decided_by": decided_by,
                    "doc_id": doc_id,
                },
            )
        ).fetchone()
        if row is None:
            raise KbNotFound(f"candidate {candidate_id} not found")
        data = dict(row._mapping)
        data["doc_id"] = int(data["doc_id"])
        return data

    row = (
        await db.execute(
            sql_text(
                "UPDATE support_kb_candidate SET status = 'rejected', reason = :reason, "
                "decided_at = now(), decided_by = :decided_by "
                "WHERE id = :id RETURNING id, status"
            ),
            {
                "id": int(candidate_id),
                "reason": reason,
                "decided_by": decided_by,
            },
        )
    ).fetchone()
    if row is None:
        raise KbNotFound(f"candidate {candidate_id} not found")
    return dict(row._mapping)
