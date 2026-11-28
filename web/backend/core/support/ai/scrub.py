"""Чистка переписки перед отправкой в модель.

Ключи подписок, ссылки, платёжные реквизиты и идентификаторы не должны
покидать сервер. Порядок правил важен: сначала длинные конструкции (ссылки
целиком), потом их обломки. Всё заменяется на `[скрыто]`.

Модуль чистый: только stdlib, функция не имеет побочных эффектов.
"""
from __future__ import annotations

import re

MASK = "[скрыто]"

_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    # Ключи подписок и конфиги — самое ценное, что может утечь.
    (
        re.compile(
            r"\b(?:vless|vmess|trojan|ss|ssr|hysteria2?|hy2|tuic|wireguard|sub)://\S+",
            re.I,
        ),
        MASK,
    ),
    # Ссылки на подписку: в пути и query часто зашит токен.
    (re.compile(r"https?://\S*/(?:sub|subscription|json|clash|mihomo|singbox)/\S+", re.I), MASK),
    # Прочие ссылки.
    (re.compile(r"https?://\S+", re.I), MASK),
    # Почта.
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), MASK),
    # UUID.
    (
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            re.I,
        ),
        MASK,
    ),
    # Длинные hex-ключи.
    (re.compile(r"\b[0-9a-f]{32,}\b", re.I), MASK),
    # Ключ провайдера (sk-…, gsk_…, xai-…).
    (re.compile(r"\b(?:sk|gsk|xai|api)[-_][A-Za-z0-9_-]{8,}\b"), MASK),
    # Токен Telegram-бота.
    (re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"), MASK),
    # Номер карты: 13–19 цифр, в том числе разбитых пробелами/дефисами.
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), MASK),
    # Телефон.
    (re.compile(r"\b\+?[78][ -]?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}\b"), MASK),
    # IP.
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), MASK),
    # Telegram-упоминание.
    (re.compile(r"@[A-Za-z][A-Za-z0-9_]{4,31}\b"), MASK),
    # Telegram id — 9–10 цифр подряд. Идёт последним: карты и телефоны
    # отрабатывают раньше, иначе он съел бы их куски.
    (re.compile(r"\b\d{9,10}\b"), MASK),
)

_SENSITIVE = re.compile(r"\b[0-9a-f]{32,}\b|://|\b\d{9,}\b", re.I)


def scrub(text: str) -> str:
    """Вырезать секреты и лишние пробелы. Чистая функция."""
    if not text:
        return ""
    cleaned = text
    for pattern, replacement in _RULES:
        cleaned = pattern.sub(replacement, cleaned)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def looks_sensitive(text: str) -> bool:
    """Осталось ли в тексте что-то похожее на секрет — страховка перед отправкой."""
    return bool(_SENSITIVE.search(text or ""))
