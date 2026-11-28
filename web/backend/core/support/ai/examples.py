"""Examples of operator replies for the prompt (plan §4.1 item 3).

The knowledge base tells the model *what* is true; an operator example shows
*how* to say it — short, human, often starting with one clarifying question.
Only a few similar pairs are included and the whole block is capped at
:data:`MAX_EXAMPLES_CHARS` (900) characters.

This module is a thin wrapper over the store: :func:`similar_examples` reads
through ``SupportStore.similar_examples`` (or any compatible object) and
never raises — a missing store simply means "no examples". :func:`render_examples`
is pure and is what ``ai/prompt.py`` uses.
"""
from __future__ import annotations

import inspect
from typing import Any, Sequence

from web.backend.core.support.ai.scrub import scrub

EXAMPLES_LIMIT = 3
MAX_EXAMPLE_CHARS = 600
MAX_EXAMPLES_CHARS = 900

_HEADER_HINT = "образец манеры, не источник фактов"


def _field(source: Any, name: str, default: Any = "") -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clip(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 0)].rstrip()}…"


def _sanitize_tag(text: str) -> str:
    """Не дать тексту клиента закрыть контейнер ``<client>``."""
    return text.replace("<client>", " ").replace("</client>", " ")


def render_examples(examples: Sequence[Any]) -> str:
    """Render examples for the user prompt; total length never exceeds 900.

    Each pair is scrubbed and clipped to :data:`MAX_EXAMPLE_CHARS`; pairs that
    do not fit the remaining budget are trimmed (not dropped silently) while
    the total stays within :data:`MAX_EXAMPLES_CHARS`.
    """
    blocks: list[str] = []
    used = 0
    for example in examples:
        question = scrub(_clip(_text(_field(example, "question", "")), MAX_EXAMPLE_CHARS))
        answer = scrub(_clip(_text(_field(example, "answer", "")), MAX_EXAMPLE_CHARS))
        if not question and not answer:
            continue
        if not question or not answer:
            continue
        block = (
            f"Клиент: <client>{_sanitize_tag(question)}</client>\n"
            f"Оператор: {answer}"
        )
        separator = 2 if blocks else 0
        remaining = MAX_EXAMPLES_CHARS - used - separator
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = _clip(block, remaining)
        if not block:
            break
        # Never leave a dangling "<client>" wrapper without its closing tag.
        if block.count("<client>") > block.count("</client>"):
            block = block[: block.rfind("<client>")].rstrip()
        if not block:
            break
        blocks.append(block)
        used += separator + len(block)
    return "\n\n".join(blocks).strip()


def examples_header() -> str:
    """Prompt heading that tells the model to copy the manner, not the facts."""
    return f"# Примеры ответов операторов ({_HEADER_HINT})"


async def similar_examples(
    store: Any,
    query: str,
    *,
    limit: int = EXAMPLES_LIMIT,
    exclude_conversation_id: int | None = None,
) -> list[Any]:
    """Read similar pairs through the store; errors degrade to an empty list."""
    if store is None or not (query or "").strip():
        return []
    method = getattr(store, "similar_examples", None)
    if not callable(method):
        return []
    try:
        try:
            result = method(
                query,
                limit=limit,
                exclude_conversation_id=exclude_conversation_id,
            )
        except TypeError:
            # Older/fake stores may not accept the optional keyword.
            result = method(query, limit=limit)
        if inspect.isawaitable(result):
            result = await result
        return list(result or [])
    except Exception:  # noqa: BLE001 — examples are optional for an answer
        return []


def store_examples(store: Any):
    """Bind :func:`similar_examples` to a store for ``AiRuntime.examples``."""

    async def search(query: str, *, limit: int = EXAMPLES_LIMIT) -> list[Any]:
        return await similar_examples(store, query, limit=limit)

    return search
