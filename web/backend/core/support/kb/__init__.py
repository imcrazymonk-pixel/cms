"""Knowledge-base helpers (Stage B, B2a).

Public surface is intentionally small: FTS SQL builders and the slug
normalizer live in :mod:`web.backend.core.support.kb.fts`.
"""
from web.backend.core.support.kb.fts import (
    MAX_QUERY_LEN,
    build_query,
    doc_tsvector_sql,
    rank_sql,
    search_predicate,
    slugify,
    tsquery_sql,
)

__all__ = [
    "MAX_QUERY_LEN",
    "build_query",
    "doc_tsvector_sql",
    "rank_sql",
    "search_predicate",
    "slugify",
    "tsquery_sql",
]
