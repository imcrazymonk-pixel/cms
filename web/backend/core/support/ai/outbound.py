"""Замок исходящего ответа клиенту.

Даже при аккуратном промпте модель может процитировать внутреннее: IP, домен
вне allowlist, ключ подписки, UUID, карту, иероглифы или «кухню» ответа
(«база знаний», «модель»). Промпт — просьба, а здесь замок: такой текст
клиенту не уходит. Разрешённые домены сервиса не блокируются.

Модуль чистый: только stdlib.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

_ALLOWED_PLACEHOLDER = "«разрешённый адрес»"

_IP = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
_DOMAIN = re.compile(
    r"(?<![\w.@-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,24})(?![\w.-])",
    re.I,
)
_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.I,
)
_HEX = re.compile(r"\b[0-9a-f]{32,}\b", re.I)
_PROVIDER_KEY = re.compile(r"\b(?:sk|gsk|xai|api)[-_][A-Za-z0-9_-]{8,}\b")
_SUB_LINK = re.compile(
    r"\b(?:vless|vmess|trojan|ss|ssr|hysteria2?|hy2|tuic|wireguard|sub)://\S+",
    re.I,
)
_BOT_TOKEN = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b")
_PAN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_SECRET_NAME = re.compile(r"\b(?:BOT_TOKEN|PANEL_TOKEN|API_KEY|Bearer)\b", re.I)
_LINK_TAG = re.compile(r"\[\[[^\]\n]{0,40}\]\]")

# Иероглифы: Han, Hiragana, Katakana, Hangul — диапазоны для Python `re`.
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff]")

# «Кухня» ответа. Клиенту незачем знать про «базу знаний» и «модель».
_META_II = re.compile(r"(?<![А-Яа-яЁёA-Za-z])ИИ(?![А-Яа-яЁёA-Za-z])")
_META_KB = re.compile(r"(?<![А-Яа-яЁёA-Za-z])КБ(?![А-Яа-яЁёA-Za-z])")
_META_WORDS = re.compile(
    r"(?<![А-Яа-яЁёA-Za-z])(?:"
    r"искусственн[а-я]*\s+интеллект[а-я]*|"
    r"нейросет[а-я]*|"
    r"модел[а-я]*|"
    r"баз[а-я]*\s+знани[а-я]*|"
    r"промпт[а-я]*|"
    r"ассистент[а-я]*|"
    r"knowledge\s+base|prompt[а-я]*|assistant[а-я]*|neural\s+network"
    r")(?![А-Яа-яЁёA-Za-z])",
    re.I,
)
_META_AI_EN = re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])")


def _domain_list(allowed_domains: Any) -> list[str]:
    """Нормализовать allowlist: без схемы/пути/порта, нижний регистр."""
    if not allowed_domains:
        return []
    if isinstance(allowed_domains, str):
        raw: Iterable[str] = allowed_domains.split(",")
    elif isinstance(allowed_domains, (list, tuple, set, frozenset)):
        raw = allowed_domains
    else:
        raw = (allowed_domains,)

    result: list[str] = []
    for item in raw:
        domain = str(item or "").strip().lower().lstrip(".")
        if not domain:
            continue
        if "://" in domain:
            domain = domain.split("://", 1)[1]
        domain = domain.split("/", 1)[0].split(":", 1)[0].strip(".")
        if domain and domain not in result:
            result.append(domain)
    return result


def _mask_allowed(text: str, domains: Iterable[str]) -> str:
    """Стереть разрешённые домены, чтобы детектор их не трогал."""
    probe = text
    for domain in sorted(domains, key=len, reverse=True):
        probe = re.sub(
            r"(?<![\w.@-])" + re.escape(domain) + r"(?![\w.-])",
            _ALLOWED_PLACEHOLDER,
            probe,
            flags=re.I,
        )
    return probe


def check(text: str, allowed_domains: Any = None) -> dict[str, Any]:
    """Проверить исходящий текст.

    Возвращает `{ok, reason, hits}`; `hits` — русские названия найденного,
    `reason` — короткая сводка (пустая при `ok=True`).
    """
    original = text or ""
    domains = _domain_list(allowed_domains)
    probe = _mask_allowed(original, domains)

    found: list[str] = []

    def add(pattern: re.Pattern[str], name: str) -> None:
        if pattern.search(probe) and name not in found:
            found.append(name)

    add(_IP, "ip-адрес")
    add(_DOMAIN, "домен вне allowlist")
    add(_UUID, "uuid")
    add(_HEX, "длинный ключ")
    add(_PROVIDER_KEY, "ключ провайдера")
    add(_SUB_LINK, "ссылка подписки")
    add(_BOT_TOKEN, "токен бота")
    add(_PAN, "номер карты")
    add(_SECRET_NAME, "имя секрета")
    add(_LINK_TAG, "неизвестная ссылка")
    add(_CJK, "иероглифы")
    add(_META_II, "упоминание ИИ")
    add(_META_KB, "упоминание базы знаний")
    add(_META_WORDS, "мета-слово")
    add(_META_AI_EN, "упоминание ИИ")

    ok = not found
    return {
        "ok": ok,
        "reason": "" if ok else "запрещено: " + ", ".join(found),
        "hits": found,
    }


# Псевдоним для читающих вызовов.
check_outbound = check
