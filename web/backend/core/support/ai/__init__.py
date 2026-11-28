"""Чистое ИИ-ядро саппорта: конфиг, разбор ответа, КБ-куски, ссылки, замки, гейт.

Пакет не делает I/O и не знает про store/API. Провайдер, промпт, responder и
воркер живут отдельно (B1b-2) и импортируют эти модули.
"""
from __future__ import annotations

from web.backend.core.support.ai.chunks import (
    CHUNK_TARGET,
    ArticlePart,
    KbChunk,
    norm,
    select_chunks,
    split_article,
)
from web.backend.core.support.ai.config import MODES, AiConfig
from web.backend.core.support.ai.gate import (
    CHECK_BAND,
    confidence_level,
    decide,
    is_aggressive,
    is_sensitive,
    tone_of,
)
from web.backend.core.support.ai.links import (
    DEFAULT_TITLES,
    LINK_KEYS,
    MAX_LINKS,
    CustomerLink,
    ExpandedLinks,
    expand_links,
    links_block,
    mask_links,
    normalize_links,
)
from web.backend.core.support.ai.outbound import check, check_outbound
from web.backend.core.support.ai.prompt import (
    DRAFT_SCHEMA,
    Citation,
    PromptBundle,
    build_prompt,
)
from web.backend.core.support.ai.provider import AiCompletion, AiProvider, ProviderError
from web.backend.core.support.ai.repair import (
    DRAFT_KEYS,
    LenientResult,
    LenientValue,
    MergeResult,
    extract_json,
    lenient_parse,
    merge_pairs,
    parse_response,
    strip_thinking,
)
from web.backend.core.support.ai.responder import AiResponder, AiRuntime
from web.backend.core.support.ai.scrub import looks_sensitive, scrub

__all__ = [
    "AiCompletion",
    "AiProvider",
    "AiResponder",
    "AiRuntime",
    "ArticlePart",
    "AiConfig",
    "CHUNK_TARGET",
    "CHECK_BAND",
    "Citation",
    "CustomerLink",
    "DEFAULT_TITLES",
    "DRAFT_KEYS",
    "DRAFT_SCHEMA",
    "ExpandedLinks",
    "KbChunk",
    "LINK_KEYS",
    "LenientResult",
    "LenientValue",
    "MAX_LINKS",
    "MODES",
    "MergeResult",
    "PromptBundle",
    "ProviderError",
    "build_prompt",
    "check",
    "check_outbound",
    "confidence_level",
    "decide",
    "expand_links",
    "extract_json",
    "is_aggressive",
    "is_sensitive",
    "lenient_parse",
    "links_block",
    "looks_sensitive",
    "mask_links",
    "merge_pairs",
    "norm",
    "normalize_links",
    "parse_response",
    "scrub",
    "select_chunks",
    "split_article",
    "strip_thinking",
    "tone_of",
]
