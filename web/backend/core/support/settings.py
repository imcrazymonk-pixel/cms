"""Support settings — SUPPORT_* env defaults + runtime overrides from support_setting.

Pattern mirrors core/config.py (pydantic-settings), but runtime values may be
overridden from the DB (`support_setting` table) and from the integration
registry (`support_*` keys in `settings`). Priority:

    env defaults → legacy support_setting → registry overrides

`read_runtime_settings`/`RUNTIME_KEYS` stay for the status endpoint; the
bootstrap path uses `load_support_config`.
"""
import logging
from typing import Any, Dict, Literal, Optional, Tuple, Union, get_args, get_origin

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Ключи support_setting, переопределяющие env-дефолты
RUNTIME_KEYS = ("poll_interval_seconds", "window_hours")

_TRI_ON = ("on", "1", "true", "yes", "вкл")
_TRI_OFF = ("off", "0", "false", "no", "выкл")


class SupportSettings(BaseSettings):
    """Support module settings — env prefix SUPPORT_ (compatible with CmsSettings)."""

    model_config = SettingsConfigDict(
        env_prefix="SUPPORT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_assignment=True,
    )

    # Частота опроса каналов (поллер — фаза 1)
    poll_interval_seconds: int = Field(default=60, ge=5, description="Период опроса каналов, сек")
    # Окно ответа на входящее (outbox)
    window_hours: int = Field(default=24, ge=1, description="Окно ответа на входящее, ч")
    # Telegram-канал «личка» (фаза 2) — env SUPPORT_TG_TOKEN / SUPPORT_TG_BOT_NAME
    tg_token: str | None = Field(default=None, description="Токен Telegram-бота (личка)")
    tg_bot_name: str | None = Field(default=None, description="Короткое имя бота для ключей состояния поллера")
    # Форум-мост (фаза 2c) — env SUPPORT_TG_STAFF_GROUP_ID / SUPPORT_TG_FORUM / SUPPORT_TG_ARCHIVE_DAYS
    tg_staff_group_id: int | None = Field(default=None, description="Id группы-форума (операторская тема)")
    tg_forum: bool = Field(default=False, description="Включить форум-мост (тема на клиента)")
    tg_archive_days: int = Field(default=7, ge=1, description="Неактивность (дней) до архивации диалога")

    # ── ИИ-ассистент (Этап B) — env SUPPORT_AI_* ───────────────────────
    ai_mode: Literal["off", "shadow", "suggest", "auto"] = Field(
        default="off", description="Режим ИИ-помощника",
    )
    ai_base_url: str = Field(
        default="https://api.openai.com/v1", description="OpenAI-совместимый корень API",
    )
    ai_model: str = Field(default="gpt-4o-mini", description="Основная модель")
    ai_fallback_model: str = Field(default="", description="Фолбэк-модель при 429/5xx")
    ai_api_key: str = Field(default="", description="Ключ провайдера (секрет)")
    ai_min_confidence: float = Field(default=0.90, ge=0.0, le=1.0, description="Порог уверенности")
    ai_require_kb: bool = Field(default=True, description="Требовать опору на базу знаний")
    ai_auto_per_hour: int = Field(default=12, ge=0, description="Лимит автоответов в час (0 — без лимита)")
    ai_human_hold_minutes: int = Field(default=30, ge=0, description="Тишина после ответа оператора, мин")
    ai_max_tokens: int = Field(default=900, ge=1, description="Потолок ответа, токенов")
    ai_temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Температура генерации")
    ai_timeout_seconds: int = Field(default=30, ge=5, le=120, description="Таймаут запроса, сек")
    ai_debounce_seconds: int = Field(default=8, ge=3, le=60, description="Склейка серии сообщений, сек")
    ai_kb_budget_chars: int = Field(default=3500, ge=0, description="Бюджет выдержек КБ, символов")
    ai_allowed_domains: str = Field(
        default="hexaveil.xyz,cabinet.fortf.ru", description="Разрешённые домены через запятую",
    )
    ai_language: Literal["ru", "en"] = Field(default="ru", description="Язык ответа")
    ai_brand: str = Field(default="HexaVeil", description="Название сервиса для клиента")
    ai_proxy_mode: Literal["inherit", "direct", "custom"] = Field(
        default="direct", description="Режим прокси ИИ",
    )


# Registry key → where its value goes.
#   field   → SupportSettings attribute
#   runtime → support_setting-style runtime key
#   tri     → runtime key with on/off/auto semantics (auto = leave untouched)
SUPPORT_OVERRIDES: Dict[str, Tuple[str, str]] = {
    "support_tg_token": ("field", "tg_token"),
    "support_tg_bot_name": ("field", "tg_bot_name"),
    "support_tg_staff_group_id": ("runtime", "tg.main.staff_group_id"),
    "support_tg_forum": ("runtime", "tg.main.forum"),
    "support_tg_archive_days": ("runtime", "tg.main.archive_days"),
    "support_poll_interval_seconds": ("runtime", "poll_interval_seconds"),
    "support_window_hours": ("runtime", "window_hours"),
    "support_tg_enabled": ("tri", "tg.main.enabled"),
    "support_bedolaga_enabled": ("tri", "bedolaga.enabled"),
    # ИИ-ассистент (Этап B): значения идут в поля SupportSettings.ai_*
    "support_ai_mode": ("field", "ai_mode"),
    "support_ai_base_url": ("field", "ai_base_url"),
    "support_ai_model": ("field", "ai_model"),
    "support_ai_fallback_model": ("field", "ai_fallback_model"),
    "support_ai_api_key": ("field", "ai_api_key"),
    "support_ai_min_confidence": ("field", "ai_min_confidence"),
    "support_ai_require_kb": ("field", "ai_require_kb"),
    "support_ai_auto_per_hour": ("field", "ai_auto_per_hour"),
    "support_ai_human_hold_minutes": ("field", "ai_human_hold_minutes"),
    "support_ai_max_tokens": ("field", "ai_max_tokens"),
    "support_ai_temperature": ("field", "ai_temperature"),
    "support_ai_timeout_seconds": ("field", "ai_timeout_seconds"),
    "support_ai_debounce_seconds": ("field", "ai_debounce_seconds"),
    "support_ai_kb_budget_chars": ("field", "ai_kb_budget_chars"),
    "support_ai_allowed_domains": ("field", "ai_allowed_domains"),
    "support_ai_language": ("field", "ai_language"),
    "support_ai_brand": ("field", "ai_brand"),
    "support_ai_proxy": ("field", "ai_proxy_mode"),
}


def get_support_settings() -> SupportSettings:
    """Build SupportSettings from the environment (not cached: runtime-overridable)."""
    return SupportSettings()


async def read_runtime_settings(db: AsyncSession) -> dict[str, str]:
    """Read all runtime overrides from support_setting (raw SQL).

    Returns {"key": "value"}; an empty dict when the table is missing.
    """
    try:
        rows = (await db.execute(text("SELECT key, value FROM support_setting"))).fetchall()
        return {r.key: r.value for r in rows if r.value is not None}
    except Exception as e:  # noqa: BLE001 — схема может быть ещё не применена
        logger.debug("read_runtime_settings failed: %s", e)
        return {}


def _flag(raw: Optional[str]) -> Optional[bool]:
    value = (raw or "").strip().lower()
    if value in _TRI_ON:
        return True
    if value in _TRI_OFF:
        return False
    return None


def _positive_int(raw: Any) -> Optional[int]:
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _apply_legacy_numbers(settings: SupportSettings, runtime: Dict[str, str]) -> None:
    """Mirror legacy runtime numbers into the settings object (init uses them)."""
    poll = _positive_int(runtime.get("poll_interval_seconds"))
    if poll is not None and poll >= 5:
        settings.poll_interval_seconds = poll
    window = _positive_int(runtime.get("window_hours"))
    if window is not None:
        settings.window_hours = window


def _field_annotation(settings: SupportSettings, target: str) -> Any:
    """Return the declared annotation of a settings field (None if unknown)."""
    info = type(settings).model_fields.get(target)
    return info.annotation if info is not None else None


def _unwrap_annotation(annotation: Any) -> Any:
    """Strip Optional[...] down to the single payload type."""
    if get_origin(annotation) is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        return args[0] if args else annotation
    return annotation


def _coerce_field_value(
    settings: SupportSettings,
    target: str,
    raw: str,
    defn: Any,
) -> Any:
    """Coerce a registry string to the target field's runtime type.

    Returns None when the value cannot be represented (the caller skips it).
    Select options are taken from the registry definition, so an unknown option
    is rejected instead of being silently stored.
    """
    if defn is not None and defn.type == "select" and defn.options and raw not in defn.options:
        return None

    annotation = _unwrap_annotation(_field_annotation(settings, target))
    if annotation is bool:
        return _flag(raw)
    if annotation is int:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    if annotation is float:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    return raw


def _apply_registry_overrides(
    settings: SupportSettings,
    runtime: Dict[str, str],
    values: Dict[str, str],
) -> None:
    """Registry values override legacy runtime; empty values never clobber.

    `field` targets are applied generically: the registry `SettingDef.type`
    (bool/number/select/text) plus the field annotation drive coercion, and
    assignment-time validation rejects out-of-range values.
    """
    from web.backend.core.settings_registry import REGISTRY_BY_KEY

    for key, (kind, target) in SUPPORT_OVERRIDES.items():
        raw = str(values.get(key) or "").strip()
        if not raw:
            continue

        if kind == "field":
            defn = REGISTRY_BY_KEY.get(key)
            value = _coerce_field_value(settings, target, raw, defn)
            if value is None:
                continue
            try:
                setattr(settings, target, value)
            except ValidationError as e:  # out-of-range / wrong Literal
                logger.debug("Support setting %s rejected by validation: %s", key, e)
            continue

        if kind == "tri":
            flag = _flag(raw)
            if flag is None:  # "auto" / unknown → leave the existing value
                continue
            runtime[target] = "1" if flag else "0"
            continue

        # kind == "runtime"
        if target == "tg.main.staff_group_id":
            if raw.lstrip("-").isdigit():
                runtime[target] = raw
                settings.tg_staff_group_id = int(raw)
            continue
        if target == "tg.main.forum":
            flag = _flag(raw)
            if flag is None:
                continue
            runtime[target] = "1" if flag else "0"
            settings.tg_forum = flag
            continue
        if target == "tg.main.archive_days":
            value = _positive_int(raw)
            if value is None:
                continue
            runtime[target] = str(value)
            settings.tg_archive_days = value
            continue
        if target == "poll_interval_seconds":
            value = _positive_int(raw)
            if value is None or value < 5:
                continue
            runtime[target] = str(value)
            settings.poll_interval_seconds = value
            continue
        if target == "window_hours":
            value = _positive_int(raw)
            if value is None:
                continue
            runtime[target] = str(value)
            settings.window_hours = value
            continue


async def load_support_config(
    db: Optional[AsyncSession] = None,
) -> Tuple[SupportSettings, Dict[str, str]]:
    """Resolve support settings: env → legacy support_setting → registry.

    `db=None` reads env only (no session is opened here). Any DB error falls
    back to env defaults; the caller keeps working.
    """
    settings = get_support_settings()
    runtime: Dict[str, str] = {}

    if db is not None:
        try:
            runtime = await read_runtime_settings(db)
        except Exception as e:  # noqa: BLE001 — read_runtime_settings is already safe
            logger.debug("Support legacy runtime settings unavailable: %s", e)
            runtime = {}

    _apply_legacy_numbers(settings, runtime)

    if db is not None:
        try:
            from web.backend.core import settings_values  # lazy: avoid import cycle
            from web.backend.core.crypto import decrypt
            from web.backend.core.settings_registry import REGISTRY_BY_KEY

            stored = await settings_values.stored_merged(db)
            values: Dict[str, str] = {}
            for key in SUPPORT_OVERRIDES:
                defn = REGISTRY_BY_KEY.get(key)
                if defn is None:
                    continue
                raw, source = settings_values.resolve_with_source(defn, stored.get(key))
                # Defaults already match SupportSettings; applying them would
                # silently clobber legacy support_setting values.
                if source == "default":
                    continue
                values[key] = decrypt(raw) if defn.is_secret else raw
        except Exception as e:  # noqa: BLE001 — без схемы остаются env-дефолты
            logger.debug("Support registry settings unavailable, using env: %s", e)
            values = {}
        _apply_registry_overrides(settings, runtime, values)

    return settings, runtime

