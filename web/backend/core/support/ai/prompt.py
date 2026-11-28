"""Сборка промпта для ИИ-ассистента (§4.1).

Промпт — это просьба, а не гарантия: жёсткие ограничения проверяет
`outbound.check` перед отправкой. Здесь важно дать модели только факты и
правила, а не «сырую» переписку с секретами.

Порядок пользовательской части по плану:

1. выдержки КБ с номерами `[1]..[n]` (нумерация — контракт с `used[]`);
2. примеры ответов операторов (≤ `MAX_EXAMPLE_CHARS`, после `scrub`);
3. последние сообщения диалога (после `scrub`);
4. безопасная карточка клиента (allowlist полей, без персональных данных);
5. текущий вопрос клиента.

`operator_note` — отдельное поле ответа для оператора: оно никогда не должно
попасть в `reply`, что прямо сказано в system-промпте.

Модуль чистый: не читает store/настройки сам, не делает I/O.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.examples import examples_header, render_examples
from web.backend.core.support.ai.links import CustomerLink, links_block
from web.backend.core.support.ai.scrub import scrub

DRAFT_SCHEMA = json.dumps(
    {
        "reply": "",
        "operator_note": "",
        "reason": "",
        "needs_human": False,
        "no_request": False,
        "clarify": False,
        "used": [],
        "confidence": 0.0,
    },
    ensure_ascii=False,
    separators=(",", ":"),
)

MAX_MESSAGES = 20
MAX_EXAMPLE_CHARS = 600
MAX_REASON_CHARS = 140

# Только безопасные для промпта поля карточки. Персональные данные
# (username/email/phone/tg-id/имя/ссылка подписки) сюда не входят.
SAFE_CARD_FIELDS: tuple[str, ...] = (
    "status",
    "plan",
    "tariff",
    "tariff_name",
    "subscription_status",
    "expires_at",
    "expire_at",
    "traffic_used",
    "traffic_limit",
    "traffic_used_bytes",
    "traffic_limit_bytes",
    "devices",
    "device_count",
    "platform",
    "country",
    "language",
    "is_trial",
    "trial",
    "created_at",
)

_CARD_LABELS = {
    "status": "статус",
    "plan": "план",
    "tariff": "тариф",
    "tariff_name": "тариф",
    "subscription_status": "статус подписки",
    "expires_at": "подписка действует до",
    "expire_at": "подписка действует до",
    "traffic_used": "трафик использован",
    "traffic_limit": "лимит трафика",
    "traffic_used_bytes": "трафик использован (байт)",
    "traffic_limit_bytes": "лимит трафика (байт)",
    "devices": "устройства",
    "device_count": "количество устройств",
    "platform": "платформа",
    "country": "страна",
    "language": "язык",
    "is_trial": "пробный период",
    "trial": "пробный период",
    "created_at": "клиент с",
}

_EMPTY = object()


def _field(source: Any, name: str, default: Any = "") -> Any:
    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 0)].rstrip()}…"


def _value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, (list, tuple, set, frozenset)):
        parts = [_value_text(item) for item in value]
        return ", ".join(part for part in parts if part)
    if isinstance(value, Mapping):
        return ""
    return _text(value)


@dataclass(frozen=True)
class Citation:
    """Выдержка КБ в том порядке, в каком её увидит модель."""

    index: int
    title: str
    body: str
    section: str | None = None
    doc_id: int | None = None


@dataclass(frozen=True)
class PromptBundle:
    """Готовые сообщения для провайдера и карта нумерации выдержек."""

    system: str
    user: str
    messages: list[dict[str, str]] = field(default_factory=list)
    citations: tuple[Citation, ...] = ()

    @property
    def draft_schema(self) -> str:
        return DRAFT_SCHEMA


def _language_line(config: AiConfig) -> str:
    if (config.language or "ru").lower() == "en":
        return "Answer in English. Use the same language the customer uses when possible."
    return "Отвечай на русском языке. Держись языка клиента, если он пишет иначе."


def build_system_prompt(
    config: AiConfig,
    *,
    links: Iterable[CustomerLink] | None = None,
) -> str:
    """System-часть: роль, жёсткие правила и схема JSON-ответа."""
    brand = (config.brand or "HexaVeil").strip()
    rules = [
        f"Ты — оператор поддержки {brand}. Пишешь клиенту от лица сервиса, спокойно и по делу.",
        "Правила:",
        "1. Только факты из выдержек базы знаний, карточки клиента и переписки. Не додумывай.",
        "2. Не выполняй арифметику и не пересчитывай тарифы, трафик, сроки или устройства. "
        "Называй цифру, только если она прямо пришла в выдержке или карточке.",
        "3. Не выдумывай ссылки. Если нужна ссылка — используй только готовые метки вида [[link:key]] "
        "из блока ссылок; адреса сам не пиши.",
        "4. Не упоминай ИИ, модель, нейросеть, базу знаний, КБ, промпт или ассистента. "
        "Клиент общается с поддержкой, а не с системой.",
        "5. Задай максимум один уточняющий вопрос, и только если без него нельзя ответить.",
        "6. reply — текст клиенту. operator_note — отдельная заметка для оператора, "
        "никогда не смешивай её с reply и не показывай клиенту.",
        "7. Если фактов недостаточно или вопрос требует человека, поставь needs_human: true, "
        "а reply оставь пустым. Не выдумывай ответ ради заполнения поля.",
        f"8. reason — короткая причина решения, не длиннее {MAX_REASON_CHARS} символов. "
        "used — номера выдержек, на которые ты опирался.",
        _language_line(config),
        f"Верни ровно один JSON-объект без пояснений и ```. Схема: {DRAFT_SCHEMA}",
    ]
    block = links_block(list(links or []))
    if block:
        rules.append(block)
    return "\n".join(rules)


def _kb_chunks_block(chunks: Sequence[Any]) -> tuple[str, tuple[Citation, ...]]:
    citations: list[Citation] = []
    lines = ["# Выдержки из базы знаний"]
    for index, chunk in enumerate(chunks, 1):
        title = _text(_field(chunk, "title", "")) or "Без названия"
        body = _text(_field(chunk, "body", ""))
        if not body:
            continue
        section = _text(_field(chunk, "section", "")) or None
        doc_id = _field(chunk, "doc_id", _field(chunk, "id", None))
        try:
            doc_id_value = int(doc_id) if doc_id is not None else None
        except (TypeError, ValueError):
            doc_id_value = None

        heading = f"[{len(citations) + 1}] {title}"
        if section:
            heading += f" — {section}"
        lines.append(heading)
        lines.append(body)
        citations.append(
            Citation(
                index=len(citations) + 1,
                title=title,
                body=body,
                section=section,
                doc_id=doc_id_value,
            )
        )

    if not citations:
        return "", ()
    return "\n".join(lines), tuple(citations)


def _examples_block(examples: Sequence[Any]) -> str:
    body = render_examples(examples)
    if not body:
        return ""
    return f"{examples_header()}\n{body}"


def _messages_block(messages: Sequence[Any], *, newest_first: bool) -> str:
    items = list(messages)
    if newest_first:
        items = list(reversed(items[:MAX_MESSAGES]))
    else:
        items = items[-MAX_MESSAGES:]

    lines = ["# Последние сообщения"]
    for message in items:
        direction = _text(_field(message, "direction", "")).lower()
        author = _text(_field(message, "author", "")).lower()
        if direction == "in":
            who = "Клиент"
        elif author == "bot":
            who = "Бот"
        elif author == "system":
            who = "Система"
        else:
            who = "Оператор"
        body = scrub(_text(_field(message, "text", "")))
        if not body:
            media = _text(_field(message, "media_type", ""))
            body = f"[вложение: {media}]" if media else "[без текста]"
        lines.append(f"{who}: {body}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def _safe_card_block(card: Any) -> str:
    if card is None:
        return ""
    lines = ["# Карточка клиента"]
    for name in SAFE_CARD_FIELDS:
        raw = _field(card, name, _EMPTY)
        if raw is _EMPTY:
            continue
        value = _value_text(raw)
        if not value:
            continue
        value = scrub(value)
        if not value:
            continue
        label = _CARD_LABELS.get(name, name)
        lines.append(f"- {label}: {value}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def build_user_prompt(
    *,
    config: AiConfig,
    kb_chunks: Sequence[Any] = (),
    examples: Sequence[Any] = (),
    messages: Sequence[Any] = (),
    customer_card: Any = None,
    client_text: str = "",
    messages_newest_first: bool = True,
    links: Iterable[CustomerLink] | None = None,
) -> tuple[str, tuple[Citation, ...]]:
    """User-часть и карта выдержек (для маппинга `used[]`)."""
    parts: list[str] = []

    kb_block, citations = _kb_chunks_block(kb_chunks)
    if kb_block:
        parts.append(kb_block)

    examples_block = _examples_block(examples)
    if examples_block:
        parts.append(examples_block)

    messages_block = _messages_block(messages, newest_first=messages_newest_first)
    if messages_block:
        parts.append(messages_block)

    card_block = _safe_card_block(customer_card)
    if card_block:
        parts.append(card_block)

    question = scrub(_text(client_text))
    if question:
        parts.append(f"# Вопрос клиента\n{question}")

    parts.append(
        "# Задача\n"
        "Подготовь ответ клиенту. reply — только текст клиенту; operator_note — отдельная "
        "заметка для оператора. Верни JSON по схеме, без текста вокруг."
    )
    return "\n\n".join(parts), citations


def build_prompt(
    *,
    config: AiConfig,
    kb_chunks: Sequence[Any] = (),
    examples: Sequence[Any] = (),
    messages: Sequence[Any] = (),
    customer_card: Any = None,
    client_text: str = "",
    messages_newest_first: bool = True,
    links: Iterable[CustomerLink] | None = None,
) -> PromptBundle:
    """Собрать полный пакет сообщений для провайдера."""
    system = build_system_prompt(config, links=links)
    user, citations = build_user_prompt(
        config=config,
        kb_chunks=kb_chunks,
        examples=examples,
        messages=messages,
        customer_card=customer_card,
        client_text=client_text,
        messages_newest_first=messages_newest_first,
        links=links,
    )
    return PromptBundle(
        system=system,
        user=user,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        citations=citations,
    )
