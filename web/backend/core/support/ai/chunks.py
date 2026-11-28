"""Нарезка статей базы знаний на куски и выбор лучших в бюджете.

Длинные статьи целиком съедают бюджет промпта; модели нужен один-два раздела,
где есть ответ. Статья режется по `#`-заголовкам, длинный раздел — по абзацам
и предложениям. Куски ранжируются основами слов запроса (простой `norm` +
prefix/contains, без внешнего стеммера).

Модуль чистый: только stdlib.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

CHUNK_TARGET = 900

_HEADING = re.compile(r"^#{1,4}\s+(.+?)\s*#*\s*$")
_SENTENCE = re.compile(r"[^.!?…]+[.!?…]*\s*")
_WORD = re.compile(r"[a-zа-я0-9]+")


def norm(text: str) -> str:
    """Нижний регистр, ё→е, схлопнутые пробелы — база для сравнения основ."""
    value = (text or "").lower().replace("ё", "е")
    return re.sub(r"\s+", " ", value).strip()


def _words(text: str) -> list[str]:
    return _WORD.findall(norm(text))


def _matches(word: str, term: str) -> bool:
    """Совпадение основы: `подключ` ↔ `подключение`, без стеммера."""
    if not word or not term:
        return False
    if word.startswith(term):
        return True
    # Короткий токен запроса внутри длинного слова — только от 4 символов,
    # иначе «как» цепляет «какой».
    return len(word) >= 4 and term.startswith(word)


@dataclass
class ArticlePart:
    section: str | None
    body: str


@dataclass
class KbChunk:
    title: str
    body: str
    rank: int
    position: int
    score: float
    section: str | None = None
    # Real article id: the prompt maps the model's citation numbers back to
    # `used[].doc_id`, so every chunk must carry it (B2b fix).
    doc_id: int | None = None


def _by_paragraphs(text: str, target: int) -> list[str]:
    """Длинный текст без заголовков — по абзацам, склеивая до target."""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    parts: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > target:
            parts.append(current)
            current = ""
        if len(paragraph) > target:
            # Абзац-простыня: режем по предложениям.
            sentences = _SENTENCE.findall(paragraph) or [paragraph]
            for sentence in sentences:
                if current and len(current) + len(sentence) > target:
                    parts.append(current.strip())
                    current = ""
                current += sentence
            continue
        current = f"{current}\n\n{paragraph}" if current else paragraph
    if current.strip():
        parts.append(current.strip())
    return parts


def split_article(body: str, target: int = CHUNK_TARGET) -> list[ArticlePart]:
    """Разделы по `#`-заголовкам; без заголовков или в длинном разделе — абзацы."""
    sections: list[dict[str, Any]] = [{"section": None, "lines": []}]
    for line in (body or "").split("\n"):
        heading = _HEADING.match(line)
        if heading:
            sections.append({"section": heading.group(1).strip(), "lines": []})
        else:
            sections[-1]["lines"].append(line)

    parts: list[ArticlePart] = []
    for section in sections:
        text = "\n".join(section["lines"]).strip()
        if not text:
            continue
        pieces = _by_paragraphs(text, target) if len(text) > target else [text]
        for piece in pieces:
            parts.append(ArticlePart(section=section["section"], body=piece))
    return parts


def _score_chunk(terms: Sequence[str], part: ArticlePart) -> float:
    if not terms:
        return 0.0
    words = _words(part.body)
    heading = _words(part.section or "")
    score = 0.0
    for term in terms:
        if any(_matches(word, term) for word in words):
            score += 1.0
        if heading and any(_matches(word, term) for word in heading):
            score += 0.5
    return score


def _field(hit: Any, name: str, default: Any = "") -> Any:
    if isinstance(hit, dict):
        return hit.get(name, default)
    return getattr(hit, name, default)


def select_chunks(
    hits: Iterable[Any],
    query: str,
    budget: int,
    max_chunk: int = 4200,
) -> list[KbChunk]:
    """Лучшие куски найденных статей в пределах общего бюджета символов.

    `hits` — элементы с `title`/`body` (dict или объект). `max_chunk` —
    потолок одного куска. Итоговый порядок — по статье и месту в ней, чтобы
    контекст читался связно.
    """
    hit_list = list(hits)
    if not hit_list or budget <= 0:
        return []

    terms = _words(query)
    all_chunks: list[KbChunk] = []
    for rank, hit in enumerate(hit_list):
        title = str(_field(hit, "title", "") or "")
        body = str(_field(hit, "body", "") or "")
        raw_doc_id = _field(hit, "doc_id", _field(hit, "id", None))
        try:
            doc_id = int(raw_doc_id) if raw_doc_id is not None else None
        except (TypeError, ValueError):
            doc_id = None
        for position, part in enumerate(split_article(body)):
            chunk_body = part.body
            if len(chunk_body) > max_chunk:
                chunk_body = f"{chunk_body[:max_chunk]}…"
            bonus = (len(hit_list) - rank) / (len(hit_list) * 4)
            all_chunks.append(
                KbChunk(
                    title=title,
                    body=chunk_body,
                    rank=rank,
                    position=position,
                    score=_score_chunk(terms, part) + bonus,
                    section=part.section,
                    doc_id=doc_id,
                )
            )

    if not all_chunks:
        return []

    ranked = sorted(all_chunks, key=lambda c: (-c.score, c.rank, c.position))
    relevant = [chunk for chunk in ranked if chunk.score >= 1.0]
    # Ни одно слово не совпало (короткий вопрос, фото): начало лучшей статьи.
    pool = relevant or [chunk for chunk in ranked if chunk.rank == 0]

    picked: list[KbChunk] = []
    used = 0
    for chunk in pool:
        size = len(chunk.title) + len(chunk.section or "") + len(chunk.body) + 8
        if used + size > budget:
            continue
        picked.append(chunk)
        used += size

    # Даже лучший кусок не влез — отдаём обрезанным: без опоры модель хуже.
    if not picked:
        best = pool[0]
        keep = max(200, budget - len(best.title) - 8)
        picked.append(
            KbChunk(
                title=best.title,
                body=f"{best.body[:keep]}…",
                rank=best.rank,
                position=best.position,
                score=best.score,
                section=best.section,
                doc_id=best.doc_id,
            )
        )

    return sorted(picked, key=lambda c: (c.rank, c.position))
