"""`support_qa_pair` — обучение на ответах операторов (plan §2.4, §4.1, §5.4).

Pairs are stored only after cleaning: secrets are removed by
:func:`web.backend.core.support.ai.scrub.scrub` and long order/payment numbers
are masked. The whole deduplication story is ``external_key`` — a SHA-256 of
the normalized question and answer joined by ``\\x1f`` — with
``ON CONFLICT (external_key) DO NOTHING``.

Normalization is intentionally order-insensitive (lowercase, ё→е, punctuation
and whitespace collapsed, words sorted): «Германия не подключается» and
«не подключается германия» are the same learning example. This is the one
deliberate widening of §7.4, required by the B2b dedupe acceptance.

The module follows ``store/*`` conventions: an ``AsyncSession`` in, **no
commit** — the ``SupportStore`` facade owns the transaction.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Iterable

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.support.ai.scrub import scrub
from web.backend.core.support.kb.fts import build_query

SOURCES = ("operator", "import", "feedback")

MAX_QUESTION = 4000
MAX_ANSWER = 8000
EXAMPLES_LIMIT = 3
EXAMPLE_MAX = 600
EXAMPLE_QUERY_LIMIT = 10

_SEPARATOR = "\x1f"
_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_SPACES_RE = re.compile(r"\s+")
_LONG_NUMBER_RE = re.compile(r"(?<!\w)\d{6,}(?!\w)")
_ORDER_RE = re.compile(r"#\d{3,}")

# Same filler set as the reference implementation (ai-support/examples.ts):
# confirmations carry no reusable wording.
_FILLER_RE = re.compile(
    r"^(?:ок(?:ей)?|хорошо|понял[аи]?|принял[аи]?|ага|да|нет|"
    r"минут(?:у|очку)|секунд(?:у|очку)|сейчас(?: посмотрю| проверю| гляну)?|"
    r"смотрю|проверяю|проверим|уточняю|ждите|здравствуйте|"
    r"добрый (?:день|вечер|утро)|привет|спасибо|пожалуйста|"
    r"рад[аы]? помочь|обращайтесь|всего доброго)$",
    re.IGNORECASE | re.UNICODE,
)

_QA_COLUMNS = "id, conversation_id, source, question, answer, created_at"
_MESSAGE_COLUMNS = "id, conversation_id, direction, author, text, created_at"

# Vector must match the GIN index in 006 exactly: two-argument to_tsvector.
_QA_VECTOR = (
    "to_tsvector('russian', coalesce(question, '') || ' ' || coalesce(answer, ''))"
)
_SIMILAR_SQL = (
    f"SELECT id, question, answer, ts_rank_cd({_QA_VECTOR}, "
    "websearch_to_tsquery('russian', :q)) AS rank "
    "FROM support_qa_pair "
    f"WHERE {_QA_VECTOR} @@ websearch_to_tsquery('russian', :q) "
    "ORDER BY rank DESC, id DESC "
    "LIMIT :limit"
)


class QaError(Exception):
    """Base class for QA-store errors."""


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row._mapping)


def normalize(text: str | None) -> str:
    """Normalize text for ``external_key`` (case/punctuation/spaces/order)."""
    value = unicodedata.normalize("NFKC", str(text or "")).lower().replace("ё", "е")
    value = _PUNCT_RE.sub(" ", value)
    words = [word for word in value.split() if word]
    return " ".join(sorted(words))


def external_key(question: str, answer: str) -> str:
    """Stable SHA-256 key for a QA pair (plan §2.4)."""
    payload = f"{normalize(question)}{_SEPARATOR}{normalize(answer)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clean_example(text: str | None, max_chars: int = EXAMPLE_MAX) -> str:
    """Scrub + mask order numbers + collapse newlines; clip to ``max_chars``."""
    cleaned = scrub(str(text or ""))
    cleaned = _LONG_NUMBER_RE.sub("[номер]", cleaned)
    cleaned = _ORDER_RE.sub("#[номер]", cleaned)
    cleaned = re.sub(r"\s*\n\s*", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if max_chars > 0 and len(cleaned) > max_chars:
        cleaned = f"{cleaned[: max(max_chars - 1, 0)].rstrip()}…"
    return cleaned


def is_meaningful(
    text: str | None,
    *,
    min_chars: int = 12,
    min_words: int = 3,
) -> bool:
    """Does the text teach anything? «ок», «спасибо», «минуту» do not."""
    normalized = normalize(text)
    if len(normalized) < min_chars:
        return False
    if _FILLER_RE.match(normalized):
        return False
    return len(normalized.split()) >= min_words


def _validate_source(source: str) -> str:
    value = (source or "operator").strip().lower()
    if value not in SOURCES:
        raise ValueError(f"unknown QA source: {source!r}")
    return value


def _prepare_pair(
    question: str,
    answer: str,
    external_key: str | None = None,
) -> tuple[str, str, str] | None:
    """Clean + validate one pair; ``None`` when it teaches nothing.

    Shared by the single-pair and batch insert paths so import behaves exactly
    like operator learning.
    """
    clean_question = clean_example(question, MAX_QUESTION)
    clean_answer = clean_example(answer, MAX_ANSWER)
    if not clean_question or not clean_answer:
        return None
    if not is_meaningful(clean_question, min_chars=8, min_words=1):
        return None
    if not is_meaningful(clean_answer):
        return None

    key = (external_key or "").strip() or external_key_value(clean_question, clean_answer)
    if len(key) > 128:
        raise ValueError("external_key is too long")
    return clean_question, clean_answer, key


_INSERT_PAIR_SQL = """
    INSERT INTO support_qa_pair (
        conversation_id, source, question, answer, external_key
    ) VALUES (
        :conversation_id, :source, :question, :answer, :external_key
    )
    ON CONFLICT (external_key) DO NOTHING
    RETURNING id
"""


async def add_qa_pair(
    db: AsyncSession,
    question: str,
    answer: str,
    source: str = "operator",
    conversation_id: int | None = None,
    external_key: str | None = None,
) -> int | None:
    """Insert a cleaned pair; duplicate or non-meaningful input → ``None``.

    Deduplication is entirely ``ON CONFLICT (external_key) DO NOTHING``: the
    returned id is ``None`` both for a duplicate and for an entry that carries
    no reusable wording.
    """
    clean_source = _validate_source(source)
    prepared = _prepare_pair(question, answer, external_key)
    if prepared is None:
        return None
    clean_question, clean_answer, key = prepared

    row = (
        await db.execute(
            sql_text(_INSERT_PAIR_SQL),
            {
                "conversation_id": int(conversation_id) if conversation_id is not None else None,
                "source": clean_source,
                "question": clean_question,
                "answer": clean_answer,
                "external_key": key,
            },
        )
    ).fetchone()
    if row is None:
        return None
    return int(row._mapping["id"])


async def add_qa_pairs(
    db: AsyncSession,
    pairs: Iterable[Any],
    source: str = "import",
) -> tuple[int, int]:
    """Insert a batch in ONE transaction; returns ``(created, duplicates)``.

    ``pairs`` items are dicts with ``question``/``answer`` (tuples are also
    accepted). Non-meaningful pairs are dropped silently and are not counted
    as duplicates — ``skipped_duplicates`` means exactly «already in the DB».
    """
    clean_source = _validate_source(source)
    created = 0
    duplicates = 0
    for item in pairs:
        if isinstance(item, dict):
            question = item.get("question")
            answer = item.get("answer")
        else:
            question, answer = item[0], item[1]
        prepared = _prepare_pair(str(question or ""), str(answer or ""))
        if prepared is None:
            continue
        clean_question, clean_answer, key = prepared
        row = (
            await db.execute(
                sql_text(_INSERT_PAIR_SQL),
                {
                    "conversation_id": None,
                    "source": clean_source,
                    "question": clean_question,
                    "answer": clean_answer,
                    "external_key": key,
                },
            )
        ).fetchone()
        if row is None:
            duplicates += 1
        else:
            created += 1
    return created, duplicates


def external_key_value(question: str, answer: str) -> str:
    """Alias kept explicit for callers that already cleaned the texts."""
    return external_key(question, answer)


async def similar_examples(
    db: AsyncSession,
    query: str,
    limit: int = EXAMPLES_LIMIT,
) -> list[dict[str, Any]]:
    """Top-N similar operator pairs for the prompt (FTS + lexical filtering).

    Every returned ``question``/``answer`` is scrubbed and clipped to
    :data:`EXAMPLE_MAX` (600). Filler pairs and duplicate answers are dropped,
    so three copies of the same template cannot flood the prompt.
    """
    normalized_query = build_query(query)
    if not normalized_query:
        return []
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = EXAMPLES_LIMIT
    limit = min(max(limit, 1), EXAMPLE_QUERY_LIMIT)
    if limit <= 0:
        return []

    rows = (
        await db.execute(
            sql_text(_SIMILAR_SQL),
            {"q": normalized_query, "limit": limit * 4},
        )
    ).fetchall()

    picked: list[dict[str, Any]] = []
    seen_answers: set[str] = set()
    for row in rows:
        data = dict(row._mapping)
        question = clean_example(data.get("question"), EXAMPLE_MAX)
        answer = clean_example(data.get("answer"), EXAMPLE_MAX)
        if not question or not is_meaningful(question, min_chars=8, min_words=1):
            continue
        if not answer or not is_meaningful(answer):
            continue
        # Different wording matters more than three paraphrases of one answer.
        answer_key = normalize(answer)[:60]
        if answer_key in seen_answers:
            continue
        seen_answers.add(answer_key)
        picked.append(
            {
                "id": int(data["id"]) if data.get("id") is not None else None,
                "question": question,
                "answer": answer,
                "rank": float(data.get("rank") or 0.0),
            }
        )
        if len(picked) >= limit:
            break
    return picked


async def get_message(db: AsyncSession, message_id: int) -> dict[str, Any] | None:
    """One support message by id (feedback needs its conversation + text)."""
    row = (
        await db.execute(
            sql_text(
                f"SELECT {_MESSAGE_COLUMNS} FROM support_message WHERE id = :id"
            ),
            {"id": int(message_id)},
        )
    ).fetchone()
    return _row_to_dict(row)


async def last_inbound_before(
    db: AsyncSession,
    conversation_id: int,
    message_id: int,
) -> dict[str, Any] | None:
    """Latest incoming message strictly before ``message_id`` in the dialog."""
    row = (
        await db.execute(
            sql_text(
                f"SELECT {_MESSAGE_COLUMNS} FROM support_message "
                "WHERE conversation_id = :conversation_id "
                "AND direction = 'in' AND id < :message_id "
                "AND coalesce(text, '') <> '' "
                "ORDER BY id DESC LIMIT 1"
            ),
            {
                "conversation_id": int(conversation_id),
                "message_id": int(message_id),
            },
        )
    ).fetchone()
    return _row_to_dict(row)
