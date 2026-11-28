"""Иммутабельный снапшот настроек ИИ-ассистента.

Модуль чистый: не читает env/БД сам, не делает I/O. `AiConfig.from_settings`
принимает уже разрешённый объект настроек (`SupportSettings` или совместимый
dict) и фиксирует значения на момент вызова.

Инвариант плана §1.2: пустой `api_key` ⇒ `effective_mode='off'` независимо от
запрошенного режима. Ключ в снапшоте не участвует в repr (не попадает в логи).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

MODES = ("off", "shadow", "suggest", "auto")

_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_DOMAINS = ("hexaveil.xyz", "cabinet.fortf.ru")


def _pick(source: Any, name: str, default: Any) -> Any:
    """Достать поле из dict/объекта, не падая на отсутствии."""
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on", "вкл"):
        return True
    if text in ("0", "false", "no", "off", "выкл"):
        return False
    return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _domains(value: Any) -> tuple[str, ...]:
    """Список доменов: строка через запятую, iterable или пусто."""
    if value is None:
        return ()
    if isinstance(value, str):
        raw: Iterable[str] = value.split(",")
    elif isinstance(value, (list, tuple, set, frozenset)):
        raw = value
    else:
        raw = (value,)
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
    return tuple(result)


@dataclass(frozen=True)
class AiConfig:
    """Снимок настроек ИИ. Все поля неизменяемы после создания."""

    mode: str = "off"
    effective_mode: str = "off"
    has_key: bool = False
    base_url: str = _DEFAULT_BASE_URL
    model: str = _DEFAULT_MODEL
    fallback_model: str = ""
    api_key: str = field(default="", repr=False)
    min_confidence: float = 0.90
    require_kb: bool = True
    auto_per_hour: int = 12
    human_hold_minutes: int = 30
    max_tokens: int = 900
    temperature: float = 0.2
    timeout: int = 30
    debounce_seconds: int = 8
    kb_budget_chars: int = 3500
    allowed_domains: tuple[str, ...] = _DEFAULT_DOMAINS
    language: str = "ru"
    brand: str = "HexaVeil"

    @classmethod
    def from_settings(cls, settings: Any) -> "AiConfig":
        """Собрать снапшот из `SupportSettings` (или dict с `ai_*` полями).

        Пустой ключ переводит `effective_mode` в `off`; сам `mode` сохраняется,
        чтобы UI мог показать «запрошен N, фактически выключен».
        """
        mode = _as_str(_pick(settings, "ai_mode", "off")).lower()
        if mode not in MODES:
            mode = "off"

        api_key = _as_str(_pick(settings, "ai_api_key", ""))
        has_key = bool(api_key)
        effective_mode = mode if has_key else "off"

        language = _as_str(_pick(settings, "ai_language", "ru")).lower()
        if language not in ("ru", "en"):
            language = "ru"

        brand = _as_str(_pick(settings, "ai_brand", "HexaVeil")) or "HexaVeil"
        base_url = _as_str(_pick(settings, "ai_base_url", _DEFAULT_BASE_URL))
        if not base_url:
            base_url = _DEFAULT_BASE_URL
        model = _as_str(_pick(settings, "ai_model", _DEFAULT_MODEL))
        if not model:
            model = _DEFAULT_MODEL

        domains = _domains(_pick(settings, "ai_allowed_domains", _DEFAULT_DOMAINS))

        return cls(
            mode=mode,
            effective_mode=effective_mode,
            has_key=has_key,
            base_url=base_url.rstrip("/"),
            model=model,
            fallback_model=_as_str(_pick(settings, "ai_fallback_model", "")),
            api_key=api_key,
            min_confidence=_as_float(_pick(settings, "ai_min_confidence", 0.90), 0.90),
            require_kb=_as_bool(_pick(settings, "ai_require_kb", True), True),
            auto_per_hour=_as_int(_pick(settings, "ai_auto_per_hour", 12), 12),
            human_hold_minutes=_as_int(_pick(settings, "ai_human_hold_minutes", 30), 30),
            max_tokens=_as_int(_pick(settings, "ai_max_tokens", 900), 900),
            temperature=_as_float(_pick(settings, "ai_temperature", 0.2), 0.2),
            timeout=_as_int(_pick(settings, "ai_timeout_seconds", 30), 30),
            debounce_seconds=_as_int(_pick(settings, "ai_debounce_seconds", 8), 8),
            kb_budget_chars=_as_int(_pick(settings, "ai_kb_budget_chars", 3500), 3500),
            allowed_domains=domains,
            language=language,
            brand=brand,
        )
