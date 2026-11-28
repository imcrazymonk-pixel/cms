"""PostgreSQL full-text helpers for the support knowledge base (plan §2.2, §5.1).

Rules encoded here:

* the indexable vector is the **two-argument** ``to_tsvector('russian', text)``
  (one-argument form is STABLE and cannot back a GIN index);
* the user query goes through ``websearch_to_tsquery('russian', :q)`` — it
  tolerates quotes, ``|`` and ``:`` and never raises on arbitrary input;
* ranking is ``ts_rank_cd``;
* slugs are transliterated RU→EN and reduced to ``[a-z0-9-]``; uniqueness is
  added by the store (``base``, ``base-2``, …).

The module is pure: no I/O, no imports from the store/API layers.
"""
from __future__ import annotations

import re
import unicodedata

MAX_QUERY_LEN = 200
MAX_SLUG_LEN = 80
REG_CONFIG = "russian"

_ALIAS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.$")
_PARAM_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
    "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
    # Ukrainian/Belarusian letters that may appear in pasted copy.
    "і": "i", "ї": "yi", "є": "ye", "ґ": "g", "ў": "u",
}


def _prefix(alias: str) -> str:
    """Validate a table alias used inside generated SQL.

    Aliases are internal constants, but validating keeps the SQL builder safe
    if a caller ever passes user-influenced text by mistake.
    """
    if not alias:
        return ""
    if not _ALIAS_RE.match(alias):
        raise ValueError(f"invalid SQL alias: {alias!r}")
    return alias


def _param(name: str) -> str:
    if not _PARAM_RE.match(name):
        raise ValueError(f"invalid bind parameter name: {name!r}")
    return name


def build_query(q: str) -> str:
    """Normalize a user query for ``websearch_to_tsquery('russian', :q)``.

    Quotes, ``|``, ``:``, ``AND``/``OR`` are intentionally kept: the websearch
    parser understands them and degrades to an empty query instead of raising.
    NUL and other control characters are removed (PostgreSQL rejects NUL in
    text values); whitespace is collapsed and the length is capped.
    """
    if q is None:
        return ""
    value = unicodedata.normalize("NFKC", str(q))
    value = _CONTROL_RE.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:MAX_QUERY_LEN].strip()


def doc_tsvector_sql(alias: str = "") -> str:
    """``to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(body,''))``.

    ``alias`` is either empty or a validated ``"d."``-style prefix.
    """
    table = _prefix(alias)
    return (
        f"to_tsvector('{REG_CONFIG}', "
        f"coalesce({table}title, '') || ' ' || coalesce({table}body, ''))"
    )


def tsquery_sql(param: str = "q") -> str:
    """``websearch_to_tsquery('russian', :param)`` with a validated bind name."""
    return f"websearch_to_tsquery('{REG_CONFIG}', :{_param(param)})"


def search_predicate(alias: str = "", param: str = "q") -> str:
    """FTS match predicate with a bound query parameter."""
    return f"{doc_tsvector_sql(alias)} @@ {tsquery_sql(param)}"


def rank_sql(alias: str = "", param: str = "q") -> str:
    """``ts_rank_cd(vector, query)`` for ordering FTS results."""
    return f"ts_rank_cd({doc_tsvector_sql(alias)}, {tsquery_sql(param)})"


def slugify(title: str) -> str:
    """Russian title → lowercase ASCII slug (``[a-z0-9-]``).

    Falls back to ``article`` when nothing usable remains. The result is not
    unique; the store appends ``-2``, ``-3``, … as needed.
    """
    value = unicodedata.normalize("NFKC", str(title or "")).strip().lower()
    parts: list[str] = []
    for char in value:
        transliterated = _TRANSLIT.get(char)
        if transliterated is not None:
            parts.append(transliterated)
        elif char.isascii() and char.isalnum():
            parts.append(char)
        else:
            parts.append("-")

    slug = "".join(parts)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:MAX_SLUG_LEN].strip("-") or "article"
