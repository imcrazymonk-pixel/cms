"""Support settings keys — registry contract + generic override applier.

Covers §8 of docs/plans/2026-11-28-support-stage-b.md:
  * registry keys are unique and `is_secret` is set only on the API key;
  * every `support_ai_*` key declares the env var from the plan table §1.2;
  * `SupportSettings` accepts the new `ai_*` fields and ignores unknown ones;
  * legacy `support_tg_*` / `support_poll_*` / `support_window_hours` still map
    into the settings object after the generic `_apply_registry_overrides`
    refactor (the main regression risk of B1a).

No network, no DB.
"""
import pytest

from web.backend.core.settings_registry import REGISTRY, REGISTRY_BY_KEY, SUPPORT_KEYS
from web.backend.core.support.settings import (
    SUPPORT_OVERRIDES,
    SupportSettings,
    _apply_registry_overrides,
)

# §1.2 — registry key → env var (verbatim from the plan table).
AI_ENV_BY_KEY = {
    "support_ai_mode": "SUPPORT_AI_MODE",
    "support_ai_base_url": "SUPPORT_AI_BASE_URL",
    "support_ai_model": "SUPPORT_AI_MODEL",
    "support_ai_fallback_model": "SUPPORT_AI_FALLBACK_MODEL",
    "support_ai_api_key": "SUPPORT_AI_API_KEY",
    "support_ai_min_confidence": "SUPPORT_AI_MIN_CONFIDENCE",
    "support_ai_require_kb": "SUPPORT_AI_REQUIRE_KB",
    "support_ai_auto_per_hour": "SUPPORT_AI_AUTO_PER_HOUR",
    "support_ai_human_hold_minutes": "SUPPORT_AI_HUMAN_HOLD_MINUTES",
    "support_ai_max_tokens": "SUPPORT_AI_MAX_TOKENS",
    "support_ai_temperature": "SUPPORT_AI_TEMPERATURE",
    "support_ai_timeout_seconds": "SUPPORT_AI_TIMEOUT_SECONDS",
    "support_ai_debounce_seconds": "SUPPORT_AI_DEBOUNCE_SECONDS",
    "support_ai_kb_budget_chars": "SUPPORT_AI_KB_BUDGET_CHARS",
    "support_ai_allowed_domains": "SUPPORT_AI_ALLOWED_DOMAINS",
    "support_ai_language": "SUPPORT_AI_LANGUAGE",
    "support_ai_brand": "SUPPORT_AI_BRAND",
    "support_ai_proxy": "SUPPORT_AI_PROXY_MODE",
}


# ── Registry contract ─────────────────────────────────────────────────────

def test_registry_keys_are_unique():
    keys = [d.key for d in REGISTRY]
    assert len(keys) == len(set(keys))


def test_every_ai_key_is_registered():
    ai_keys = {d.key for d in REGISTRY if d.key.startswith("support_ai_")}
    assert ai_keys == set(AI_ENV_BY_KEY)
    assert len(ai_keys) == 18
    assert ai_keys <= set(SUPPORT_KEYS)


def test_only_api_key_is_secret():
    secret_ai = {d.key for d in REGISTRY if d.key.startswith("support_ai_") and d.is_secret}
    assert secret_ai == {"support_ai_api_key"}
    assert REGISTRY_BY_KEY["support_ai_api_key"].type == "secret"


def test_ai_keys_share_group_and_tab():
    for key in AI_ENV_BY_KEY:
        defn = REGISTRY_BY_KEY[key]
        assert defn.category == "ИИ / Саппорт", key
        assert defn.tab == "integrations", key


def test_ai_env_names_match_plan_table():
    for key, env in AI_ENV_BY_KEY.items():
        assert REGISTRY_BY_KEY[key].env_var == env, key


def test_ai_env_names_match_settings_fields():
    """env_var is `SUPPORT_` + the SupportSettings field it feeds."""
    for key, (kind, target) in SUPPORT_OVERRIDES.items():
        if not key.startswith("support_ai_"):
            continue
        assert kind == "field", key
        defn = REGISTRY_BY_KEY[key]
        assert defn.env_var == f"SUPPORT_{target.upper()}", key


# ── SupportSettings ───────────────────────────────────────────────────────

def test_settings_accepts_ai_fields():
    settings = SupportSettings(
        ai_mode="auto",
        ai_base_url="https://llm.example/v1",
        ai_model="gpt-x",
        ai_fallback_model="gpt-mini",
        ai_api_key="sk-test",
        ai_min_confidence=0.75,
        ai_require_kb=False,
        ai_auto_per_hour=0,
        ai_human_hold_minutes=15,
        ai_max_tokens=500,
        ai_temperature=0.1,
        ai_timeout_seconds=45,
        ai_debounce_seconds=5,
        ai_kb_budget_chars=2000,
        ai_allowed_domains="hexaveil.xyz",
        ai_language="en",
        ai_brand="HexaVeil",
        ai_proxy_mode="custom",
    )
    assert settings.ai_mode == "auto"
    assert settings.ai_min_confidence == 0.75
    assert settings.ai_require_kb is False
    assert settings.ai_language == "en"
    assert settings.ai_proxy_mode == "custom"


def test_settings_ignores_unknown_fields():
    settings = SupportSettings(ai_mode="shadow", some_unknown_field="ignored")
    assert settings.ai_mode == "shadow"
    assert not hasattr(settings, "some_unknown_field")


def test_settings_reads_legacy_env(monkeypatch):
    monkeypatch.setenv("SUPPORT_POLL_INTERVAL_SECONDS", "120")
    monkeypatch.setenv("SUPPORT_WINDOW_HOURS", "8")
    monkeypatch.setenv("SUPPORT_TG_TOKEN", "legacy-token")
    monkeypatch.setenv("SUPPORT_TG_BOT_NAME", "legacy-bot")
    monkeypatch.setenv("SUPPORT_TG_FORUM", "1")

    settings = SupportSettings()
    assert settings.poll_interval_seconds == 120
    assert settings.window_hours == 8
    assert settings.tg_token == "legacy-token"
    assert settings.tg_bot_name == "legacy-bot"
    assert settings.tg_forum is True


# ── Generic `_apply_registry_overrides` ───────────────────────────────────

def test_legacy_field_overrides_still_apply():
    settings = SupportSettings()
    runtime: dict[str, str] = {}

    _apply_registry_overrides(
        settings,
        runtime,
        {
            "support_tg_token": "tok-registry",
            "support_tg_bot_name": "bot-registry",
        },
    )

    assert settings.tg_token == "tok-registry"
    assert settings.tg_bot_name == "bot-registry"


def test_legacy_runtime_and_tri_overrides_still_apply():
    settings = SupportSettings()
    runtime: dict[str, str] = {}

    _apply_registry_overrides(
        settings,
        runtime,
        {
            "support_tg_staff_group_id": "-1001234567890",
            "support_tg_forum": "1",
            "support_tg_archive_days": "14",
            "support_poll_interval_seconds": "90",
            "support_window_hours": "12",
            "support_tg_enabled": "off",
            "support_bedolaga_enabled": "on",
        },
    )

    assert settings.tg_staff_group_id == -1001234567890
    assert settings.tg_forum is True
    assert settings.tg_archive_days == 14
    assert settings.poll_interval_seconds == 90
    assert settings.window_hours == 12
    assert runtime["tg.main.staff_group_id"] == "-1001234567890"
    assert runtime["tg.main.forum"] == "1"
    assert runtime["tg.main.archive_days"] == "14"
    assert runtime["poll_interval_seconds"] == "90"
    assert runtime["window_hours"] == "12"
    assert runtime["tg.main.enabled"] == "0"
    assert runtime["bedolaga.enabled"] == "1"


def test_legacy_empty_values_never_clobber():
    settings = SupportSettings(tg_token="keep-me", poll_interval_seconds=77)
    runtime: dict[str, str] = {}

    _apply_registry_overrides(settings, runtime, {"support_tg_token": "", "support_poll_interval_seconds": "  "})

    assert settings.tg_token == "keep-me"
    assert settings.poll_interval_seconds == 77
    assert runtime == {}


def test_ai_overrides_apply_with_coercion():
    settings = SupportSettings()
    runtime: dict[str, str] = {}

    _apply_registry_overrides(
        settings,
        runtime,
        {
            "support_ai_mode": "suggest",
            "support_ai_min_confidence": "0.8",
            "support_ai_require_kb": "0",
            "support_ai_auto_per_hour": "0",
            "support_ai_timeout_seconds": "60",
            "support_ai_language": "en",
            "support_ai_proxy": "custom",
            "support_ai_api_key": "sk-live",
        },
    )

    assert settings.ai_mode == "suggest"
    assert settings.ai_min_confidence == 0.8
    assert settings.ai_require_kb is False
    assert settings.ai_auto_per_hour == 0
    assert settings.ai_timeout_seconds == 60
    assert settings.ai_language == "en"
    assert settings.ai_proxy_mode == "custom"
    assert settings.ai_api_key == "sk-live"


def test_ai_invalid_values_are_skipped():
    settings = SupportSettings(ai_mode="off", ai_timeout_seconds=30)
    runtime: dict[str, str] = {}

    _apply_registry_overrides(
        settings,
        runtime,
        {
            "support_ai_mode": "bogus",       # not in select options
            "support_ai_timeout_seconds": "999",  # outside 5..120
            "support_ai_language": "de",      # outside ru|en
        },
    )

    assert settings.ai_mode == "off"
    assert settings.ai_timeout_seconds == 30
    assert settings.ai_language == "ru"


def test_tri_auto_leaves_runtime_untouched():
    settings = SupportSettings()
    runtime: dict[str, str] = {}

    _apply_registry_overrides(settings, runtime, {"support_tg_enabled": "auto"})

    assert runtime == {}


# ── Приветствие бота (Stage D) ─────────────────────────────────────────────

def test_greeting_key_registered_and_mapped():
    """Ключ приветствия рендерится textarea и попадает в SupportSettings."""
    definition = REGISTRY_BY_KEY["support_tg_greeting"]
    assert definition.type == "textarea"
    assert definition.is_secret is False
    assert definition.env_var == "SUPPORT_TG_GREETING"
    assert SUPPORT_OVERRIDES["support_tg_greeting"] == ("field", "tg_greeting")

    settings = SupportSettings()
    runtime: dict[str, str] = {}
    _apply_registry_overrides(
        settings,
        runtime,
        {"support_tg_greeting": "Свой текст"},
    )
    assert settings.tg_greeting == "Свой текст"
