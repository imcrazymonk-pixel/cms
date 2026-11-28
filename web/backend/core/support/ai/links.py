"""Ссылки, которые ИИ может дать клиенту.

Модель не пишет адрес сама, а ставит метку `[[link:key]]`; точный URL
подставляется после проверки ответа. Так секрет прокси не искажается при
пересказе, а замок `outbound` остаётся строгим: адрес, написанный моделью от
себя, клиенту по-прежнему не уходит. Неизвестный ключ остаётся меткой как
есть — его заблокирует `outbound`.

Модуль чистый: только stdlib.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

# Фиксированный набор ключей, которые понимает модель.
LINK_KEYS: tuple[str, ...] = (
    "cabinet",
    "bot",
    "faq",
    "tariffs",
    "subscription",
    "support",
)

MAX_LINKS = 20

DEFAULT_TITLES: dict[str, str] = {
    "cabinet": "Личный кабинет",
    "bot": "Telegram-бот",
    "faq": "Частые вопросы",
    "tariffs": "Тарифы",
    "subscription": "Подписка",
    "support": "Поддержка",
}

_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_URL = re.compile(r"^(?:https?|tg)://\S+$", re.I)
_TAG = re.compile(r"\[\[\s*(?:link\s*:\s*)?([a-z0-9][a-z0-9_-]{0,31})\s*\]\]", re.I)


@dataclass(frozen=True)
class CustomerLink:
    key: str
    title: str
    url: str
    when: str = ""


@dataclass(frozen=True)
class ExpandedLinks:
    """Результат раскрытия метк: текст клиенту, probe для замка и used."""

    text: str
    probe: str
    used: tuple[CustomerLink, ...] = ()


def _item(raw: Any, key_hint: str | None = None) -> dict[str, Any] | None:
    """Нормализовать один элемент ввода в dict с key/title/url/when."""
    if isinstance(raw, str):
        if key_hint is None:
            return None
        return {"key": key_hint, "url": raw}
    if isinstance(raw, dict):
        data = dict(raw)
        if key_hint is not None:
            data.setdefault("key", key_hint)
        return data
    if isinstance(raw, (list, tuple)) and len(raw) >= 2 and key_hint is None:
        return {"key": raw[0], "url": raw[1]}
    return None


def normalize_links(value: Any) -> list[CustomerLink] | None:
    """Проверить и нормализовать ссылки из настроек.

    Принимает dict `{key: url | {url, title, when}}` или список dict/пар.
    Невалидный элемент, неизвестный ключ или превышение `MAX_LINKS`
    отклоняют весь набор (None) — лучше не дать ссылок, чем дать неверную.
    """
    if value is None:
        return None

    items: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, raw in value.items():
            item = _item(raw, str(key))
            if item is None:
                return None
            items.append(item)
    elif isinstance(value, (list, tuple)):
        for raw in value:
            item = _item(raw)
            if item is None:
                return None
            items.append(item)
    else:
        return None

    if len(items) > MAX_LINKS:
        return None

    seen: set[str] = set()
    result: list[CustomerLink] = []
    for item in items:
        key = str(item.get("key", "")).strip().lower()
        url = str(item.get("url", "")).strip()
        when = str(item.get("when", "") or "").strip()
        title = str(item.get("title", "") or "").strip() or DEFAULT_TITLES.get(key, "")
        if not _KEY.match(key) or key not in LINK_KEYS or key in seen:
            return None
        if not title or len(title) > 80 or len(when) > 300:
            return None
        if len(url) > 600 or not _URL.match(url):
            return None
        seen.add(key)
        result.append(CustomerLink(key=key, title=title, url=url, when=when))
    return result


def links_block(links: Iterable[CustomerLink]) -> str:
    """Блок для промпта; пустой список — пустая строка (токены не тратим)."""
    items = list(links)
    if not items:
        return ""
    lines = [
        "# Ссылки, которые можно дать клиенту",
        "Если ссылка отвечает на вопрос — вставь в reply её метку целиком, адрес подставится сам; "
        "не обещай «могу отправить», а сразу давай. Сам адреса не пиши.",
    ]
    for link in items:
        suffix = f". Когда давать: {link.when}" if link.when else ""
        lines.append(f"- [[link:{link.key}]] — {link.title}{suffix}")
    return "\n".join(lines)


def mask_links(text: str, links: Iterable[CustomerLink]) -> str:
    """Спрятать известные адреса в тексте: модель увидит метку, а не секрет."""
    result = text or ""
    # Длинные адреса первыми: один может начинаться с другого.
    for link in sorted(links, key=lambda item: len(item.url), reverse=True):
        if link.url:
            result = result.replace(link.url, f"[[link:{link.key}]]")
    return result


def expand_links(text: str, links: Iterable[CustomerLink]) -> ExpandedLinks:
    """Раскрыть известные метки в URL; неизвестные оставить как есть."""
    by_key = {link.key: link for link in links}
    used: dict[str, CustomerLink] = {}

    def replace(fill):
        def _sub(match: re.Match[str]) -> str:
            tag = match.group(0)
            link = by_key.get(match.group(1).lower())
            if link is None:
                return tag
            used[link.key] = link
            return fill(link)

        return _TAG.sub(_sub, text or "")

    real = replace(lambda link: link.url)
    probe = replace(lambda link: "«ссылка»")
    return ExpandedLinks(text=real, probe=probe, used=tuple(used.values()))
