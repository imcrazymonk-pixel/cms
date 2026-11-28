"""B1b-1 — чистый разбор ответа, нарезка КБ и ссылки.

Покрывает §8 плана `docs/plans/2026-11-28-support-stage-b.md`:
  * `repair`: фенсы, thinking, лишний текст, баланс скобок, одинарные
    кавычки, висячие запятые, обрыв, повторы ключей;
  * `chunks`: нарезка по заголовкам/абзацам, бюджет, `max_chunk`, регрессия
    по русским основам;
  * `links`: нормализация, маска/раскрытие, неизвестный ключ, `MAX_LINKS`.

Без сети, БД и настроек.
"""
import pytest

from web.backend.core.support.ai.chunks import (
    CHUNK_TARGET,
    norm,
    select_chunks,
    split_article,
)
from web.backend.core.support.ai.links import (
    LINK_KEYS,
    MAX_LINKS,
    CustomerLink,
    expand_links,
    links_block,
    mask_links,
    normalize_links,
)
from web.backend.core.support.ai.repair import (
    DRAFT_KEYS,
    extract_json,
    lenient_parse,
    merge_pairs,
    parse_response,
    strip_thinking,
)


# ── repair ────────────────────────────────────────────────────────────────

def test_draft_keys_contract():
    assert DRAFT_KEYS == (
        "reply",
        "operator_note",
        "reason",
        "needs_human",
        "no_request",
        "clarify",
        "used",
        "confidence",
    )


def test_strip_thinking_removes_fences():
    raw = '```json\n{"reply": "ok", "confidence": 0.9}\n```'
    cleaned = strip_thinking(raw)
    assert cleaned.startswith('{"reply"')
    assert "```" not in cleaned


def test_strip_thinking_removes_comments_and_tags():
    raw = '<!-- служебное --><thinking>долго думал</thinking>{"reply": "ok"}'
    assert strip_thinking(raw) == '{"reply": "ok"}'


def test_strip_thinking_drops_unclosed_think_tail():
    raw = '<think>не успел ответить'
    assert strip_thinking(raw) == ""


def test_extract_json_balances_braces_inside_strings():
    raw = 'Вот ответ: {"reply": "нажмите } и всё", "used": [1]} лишний хвост {x}'
    assert extract_json(raw) == '{"reply": "нажмите } и всё", "used": [1]}'


def test_extract_json_returns_none_without_object():
    assert extract_json("просто текст без json") is None
    assert extract_json('{"reply": "обрыв"') is None


def test_lenient_parse_single_quotes_fences_and_trailing_comma():
    raw = "```json\n{reply: 'привет', confidence: 0.9,}\n```"
    parsed = lenient_parse(raw)
    assert parsed is not None
    merged = merge_pairs(parsed.pairs)
    assert merged.fields["reply"] == "привет"
    assert merged.fields["confidence"] == 0.9
    assert parsed.truncated is False


def test_lenient_parse_unescaped_quotes_and_extra_text():
    raw = 'Вот ответ: {"reply": "Нажмите "Подключить" и готово", "confidence": 0.91} конец'
    parsed = lenient_parse(raw)
    assert parsed is not None
    fields = merge_pairs(parsed.pairs).fields
    assert fields["reply"] == 'Нажмите "Подключить" и готово'
    assert fields["confidence"] == 0.91


def test_lenient_parse_truncated_reply_is_marked():
    parsed = lenient_parse('{"reply": "Обрыв текста')
    assert parsed is not None
    assert parsed.truncated is True
    merged = merge_pairs(parsed.pairs)
    assert merged.fields["reply"] == "Обрыв текста"
    assert "reply" in merged.truncated


def test_merge_pairs_repeated_reply_keeps_first_nonempty():
    parsed = lenient_parse('{"reply": "Первый", "reply": "", "confidence": 0.9}')
    merged = merge_pairs(parsed.pairs)
    assert merged.fields["reply"] == "Первый"


def test_merge_pairs_repeated_scalar_last_wins():
    parsed = lenient_parse('{"confidence": 0.1, "confidence": 0.8}')
    merged = merge_pairs(parsed.pairs)
    assert merged.fields["confidence"] == 0.8


def test_lenient_parse_camel_case_aliases():
    parsed = lenient_parse('{"reply": "x", "needsHuman": true, "operatorNote": "заметка"}')
    fields = merge_pairs(parsed.pairs).fields
    assert fields["needs_human"] is True
    assert fields["operator_note"] == "заметка"


def test_parse_response_prefers_strict_json():
    merged = parse_response('{"reply": "ok", "confidence": 0.9}')
    assert merged is not None
    assert merged.fields["reply"] == "ok"
    assert merged.truncated == set()


# ── chunks ────────────────────────────────────────────────────────────────

def test_norm_lowercases_and_collapses():
    assert norm("  ГЕРМАНИЯ   не  подключается ") == "германия не подключается"
    assert norm("Ёлка") == "елка"


def test_split_article_by_headings():
    body = "# Германия\nНе подключается.\n\n## Проверка\nОбновите подписку.\n"
    parts = split_article(body)
    assert [part.section for part in parts] == ["Германия", "Проверка"]
    assert parts[0].body == "Не подключается."
    assert parts[1].body == "Обновите подписку."


def test_split_article_without_headings_uses_paragraphs():
    body = ("Первый абзац про подключение. " * 5 + "\n\n") * 3
    parts = split_article(body, target=120)
    assert len(parts) >= 3
    assert all(len(part.body) <= 125 for part in parts)


def test_select_chunks_prefers_keyword_regression():
    hits = [
        {"title": "Германия", "body": "# Германия\nГермания не подключается, обновите подписку."},
        {"title": "Тарифы", "body": "Тарифы и оплата."},
    ]
    chunks = select_chunks(hits, "подключение Германия", budget=2000)
    assert len(chunks) == 1
    assert "Германия" in chunks[0].body
    assert chunks[0].rank == 0


def test_select_chunks_respects_max_chunk():
    hits = [{"title": "Длинная", "body": "Германия " * 200}]
    chunks = select_chunks(hits, "Германия", budget=5000, max_chunk=100)
    assert chunks
    assert len(chunks[0].body) == 101  # 100 символов + многоточие
    assert chunks[0].body.endswith("…")


def test_select_chunks_respects_budget():
    hits = [
        {"title": "A", "body": "Германия " * 40},
        {"title": "B", "body": "Германия " * 40},
    ]
    chunks = select_chunks(hits, "Германия", budget=250)
    assert chunks
    total = sum(len(c.title) + len(c.section or "") + len(c.body) + 8 for c in chunks)
    # Один кусок может быть обрезан под бюджет, но не оба целиком.
    assert total <= 250 or len(chunks) == 1


def test_select_chunks_zero_budget_is_empty():
    assert select_chunks([{"title": "A", "body": "текст"}], "текст", budget=0) == []


def test_select_chunks_orders_by_article_and_position():
    hits = [
        {"title": "A", "body": "# Первый\nГермания один\n\n# Второй\nГермания два"},
        {"title": "B", "body": "# Третий\nГермания три"},
    ]
    chunks = select_chunks(hits, "Германия", budget=5000)
    assert [(c.rank, c.position) for c in chunks] == sorted((c.rank, c.position) for c in chunks)


def test_chunk_target_default():
    assert CHUNK_TARGET == 900


# ── links ─────────────────────────────────────────────────────────────────

def test_link_keys_are_fixed():
    assert LINK_KEYS == ("cabinet", "bot", "faq", "tariffs", "subscription", "support")


def test_normalize_links_from_mapping_uses_default_titles():
    links = normalize_links(
        {"cabinet": "https://cabinet.fortf.ru", "bot": "https://t.me/HexaVeil_bot"}
    )
    assert links is not None
    assert [link.key for link in links] == ["cabinet", "bot"]
    assert links[0].title == "Личный кабинет"


def test_normalize_links_from_list_of_pairs():
    links = normalize_links(
        [
            {"key": "faq", "url": "https://hexaveil.xyz/faq", "title": "FAQ", "when": "вопросы"},
            ("support", "https://hexaveil.xyz/support"),
        ]
    )
    assert links is not None
    assert [link.key for link in links] == ["faq", "support"]
    assert links[0].when == "вопросы"


def test_normalize_links_rejects_unknown_key():
    assert normalize_links({"proxy": "https://example.com"}) is None


def test_normalize_links_rejects_bad_url():
    assert normalize_links({"cabinet": "javascript:alert(1)"}) is None


def test_normalize_links_rejects_duplicates():
    assert normalize_links(
        [
            {"key": "cabinet", "url": "https://cabinet.fortf.ru"},
            {"key": "cabinet", "url": "https://cabinet.fortf.ru/2"},
        ]
    ) is None


def test_normalize_links_rejects_too_many():
    values = [
        {"key": "cabinet", "url": f"https://cabinet.fortf.ru/{i}"}
        for i in range(MAX_LINKS + 1)
    ]
    assert normalize_links(values) is None


def test_links_block_mentions_tag():
    links = [CustomerLink(key="cabinet", title="Личный кабинет", url="https://cabinet.fortf.ru")]
    block = links_block(links)
    assert "[[link:cabinet]]" in block
    assert "Личный кабинет" in block
    assert links_block([]) == ""


def test_mask_and_expand_roundtrip():
    links = [CustomerLink(key="cabinet", title="Кабинет", url="https://cabinet.fortf.ru")]
    masked = mask_links("Зайдите в https://cabinet.fortf.ru и проверьте", links)
    assert "https://cabinet.fortf.ru" not in masked
    assert "[[link:cabinet]]" in masked

    expanded = expand_links(masked, links)
    assert expanded.text == "Зайдите в https://cabinet.fortf.ru и проверьте"
    assert "https://cabinet.fortf.ru" not in expanded.probe
    assert expanded.used == (links[0],)


def test_expand_links_keeps_unknown_key_for_outbound():
    expanded = expand_links("см. [[link:unknown]]", [])
    assert expanded.text == "см. [[link:unknown]]"
    assert expanded.probe == "см. [[link:unknown]]"
    assert expanded.used == ()


def test_expand_links_accepts_spaces_and_case():
    links = [CustomerLink(key="faq", title="FAQ", url="https://hexaveil.xyz/faq")]
    expanded = expand_links("Смотри [[ link : FAQ ]]", links)
    assert expanded.text == "Смотри https://hexaveil.xyz/faq"
    assert len(expanded.used) == 1
