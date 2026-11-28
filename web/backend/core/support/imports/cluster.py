"""Turn imported QA pairs into article ideas (plan §7.4).

Pipeline: normalize → drop RU stop-words → top-3 tokens become ``topic``.
Groups with at least two pairs sharing a topic become
``support_kb_candidate(status='new')``; at most 200 groups are returned,
sorted by ``occurrences`` descending.

Pure functions only — the runner decides whether to persist anything.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any, Iterable, Sequence

MAX_CANDIDATES = 200
MIN_GROUP_SIZE = 2
TOPIC_TOKENS = 3
MIN_TOKEN_LEN = 3

# Compact Russian stop-word list (conversational filler + service words).
RU_STOPWORDS: frozenset[str] = frozenset(
    """
    а без бы был была были было быть в вам вас ваш ваша ваше ваши вдруг ведь
    весь во вот все всё вы где да даже для до его ее её если есть еще ещё же
    за здесь и из или им их к как какая какие каким ко когда кто ли либо мне
    может можно мы на над нам нас наш наша наше наши не него нее неё нет ни но
    ну о об однако он она они оно от очень по под при про раз с со так также
    такой там те тем то тоже тот тут ты у уже хотя чего чей чем через что чтобы
    чья эта эти это этого этой этом этот я
    """.split()
)

_WORD_RE = re.compile(r"[0-9a-zа-я]+", re.UNICODE)


def normalize(text: str | None) -> str:
    """NFKC, lowercase, ё→е, punctuation → space, collapse whitespace."""
    value = unicodedata.normalize("NFKC", str(text or "")).lower().replace("ё", "е")
    value = " ".join(_WORD_RE.findall(value))
    return value


def tokenize(text: str | None) -> list[str]:
    """Meaningful tokens in original order (stop-words and short words out)."""
    tokens = [
        token
        for token in normalize(text).split()
        if len(token) >= MIN_TOKEN_LEN and token not in RU_STOPWORDS
    ]
    return tokens


def topic_for(question: str | None) -> str | None:
    """Top-3 tokens: most frequent first, alphabetical order breaks ties.

    Alphabetical tie-breaking makes «Германия не подключается» and «Не
    подключается Германия» the same topic, which is the whole point of the
    grouping.
    """
    tokens = tokenize(question)
    if not tokens:
        return None
    counts = Counter(tokens)
    ranked = sorted(counts, key=lambda token: (-counts[token], token))
    return "-".join(ranked[:TOPIC_TOKENS])


def _pick_text(values: Iterable[str]) -> str:
    """Most frequent exact text; the first one wins ties."""
    counter = Counter(values)
    best_count = max(counter.values())
    for value in values:
        if counter[value] == best_count:
            return value
    return ""


def build_candidates(
    pairs: Sequence[dict[str, Any]],
    *,
    limit: int = MAX_CANDIDATES,
    min_group_size: int = MIN_GROUP_SIZE,
) -> list[dict[str, Any]]:
    """Group pairs by topic; groups of ≥2 become candidates."""
    if limit <= 0:
        return []
    limit = min(int(limit), MAX_CANDIDATES)

    groups: dict[str, list[dict[str, Any]]] = {}
    for pair in pairs:
        question = str(pair.get("question") or "").strip()
        answer = str(pair.get("answer") or "").strip()
        if not question or not answer:
            continue
        topic = topic_for(question)
        if not topic:
            continue
        groups.setdefault(topic, []).append({"question": question, "answer": answer})

    candidates: list[dict[str, Any]] = []
    for topic, items in groups.items():
        if len(items) < min_group_size:
            continue
        candidates.append(
            {
                "topic": topic,
                "question": _pick_text(item["question"] for item in items),
                "answer": _pick_text(item["answer"] for item in items),
                "occurrences": len(items),
            }
        )

    candidates.sort(key=lambda item: (-item["occurrences"], item["topic"]))
    return candidates[:limit]
