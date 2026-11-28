"""B1b-1 — ворота автоответа: полная матрица §3.2 и §3.3.

17 шагов проверяются по порядку: off, пауза, human-hold, handoff, shadow,
suggest, пустой reply, повторный clarify, require_kb × профиль, needs_human,
confidence, escalated, чувствительные темы, тон, окно, лимит/час, auto.
Плюс `confidence_level` от порога с `CHECK_BAND`.

Без сети, БД и store: состояние передаётся аргументами.
"""
from datetime import datetime, timedelta, timezone

import pytest

from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.gate import (
    CHECK_BAND,
    confidence_level,
    decide,
    is_aggressive,
    is_sensitive,
    tone_of,
)

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)


def make_runtime(mode: str = "auto", **overrides) -> AiConfig:
    has_key = overrides.pop("has_key", mode != "off")
    values = dict(
        mode=mode,
        effective_mode=mode if has_key else "off",
        has_key=has_key,
        require_kb=True,
        min_confidence=0.90,
        auto_per_hour=12,
        human_hold_minutes=30,
    )
    values.update(overrides)
    return AiConfig(**values)


def make_draft(**overrides) -> dict:
    data = dict(
        reply="Обновите подписку в личном кабинете.",
        operator_note="",
        reason="",
        needs_human=False,
        no_request=False,
        clarify=False,
        used=["1"],
        confidence=0.95,
    )
    data.update(overrides)
    return data


# ── 1. off ────────────────────────────────────────────────────────────────

def test_step_01_off_skips():
    result = decide({}, "вопрос", make_draft(), runtime=make_runtime("off"), now=NOW)
    assert result["action"] == "skip"
    assert result["reason"] == "ИИ выключен"


def test_effective_mode_off_wins_even_if_mode_saved():
    runtime = make_runtime("auto", has_key=False)
    assert runtime.effective_mode == "off"
    result = decide({}, "вопрос", make_draft(), runtime=runtime, now=NOW)
    assert result["action"] == "skip"


# ── 2. пауза помощника ────────────────────────────────────────────────────

def test_step_02_pause_gives_suggest_in_auto():
    result = decide({}, "вопрос", make_draft(), runtime=make_runtime("auto"), pause=True, now=NOW)
    assert result["action"] == "suggest"
    assert "пауза помощника" in result["reason"]


def test_step_02_pause_keeps_shadow():
    result = decide({}, "вопрос", make_draft(), runtime=make_runtime("shadow"), pause=True, now=NOW)
    assert result["action"] == "shadow"


def test_step_02_pause_until_dict():
    future = (NOW + timedelta(hours=1)).isoformat()
    result = decide(
        {}, "вопрос", make_draft(), runtime=make_runtime("auto"),
        pause={"until": future}, now=NOW,
    )
    assert result["action"] == "suggest"
    assert "пауза помощника" in result["reason"]


def test_step_02_expired_pause_is_inactive():
    past = (NOW - timedelta(minutes=1)).isoformat()
    result = decide(
        {}, "вопрос", make_draft(), runtime=make_runtime("auto"),
        pause={"until": past}, now=NOW,
    )
    assert result["action"] == "auto"


def test_pause_precedes_human_hold():
    result = decide(
        {"human_hold": True}, "вопрос", make_draft(),
        runtime=make_runtime("auto"), pause=True, now=NOW,
    )
    assert "пауза помощника" in result["reason"]


# ── 3. ответ оператора (human-hold) ───────────────────────────────────────

def test_step_03_human_hold_precedes_kb():
    conversation = {"last_human_reply_at": NOW - timedelta(minutes=5)}
    result = decide(
        conversation, "вопрос", make_draft(used=[]),
        kb_hits=0, runtime=make_runtime("auto"), now=NOW,
    )
    assert result["action"] == "suggest"
    assert "пауза после ответа оператора" in result["reason"]


def test_step_03_human_hold_shadow():
    conversation = {"last_human_reply_at": NOW - timedelta(minutes=5)}
    result = decide(
        conversation, "вопрос", make_draft(), runtime=make_runtime("shadow"), now=NOW,
    )
    assert result["action"] == "shadow"


def test_step_03_human_hold_expires():
    conversation = {"last_human_reply_at": NOW - timedelta(minutes=60)}
    result = decide(conversation, "вопрос", make_draft(), runtime=make_runtime("auto"), now=NOW)
    assert result["action"] == "auto"


# ── 4. handoff ────────────────────────────────────────────────────────────

def test_step_04_handoff_precedes_kb():
    conversation = {"handoff_at": NOW.isoformat()}
    result = decide(
        conversation, "вопрос", make_draft(used=[]),
        kb_hits=0, runtime=make_runtime("auto"), now=NOW,
    )
    assert result["action"] == "suggest"
    assert "ждёт специалиста" in result["reason"]


def test_step_04_handoff_shadow():
    conversation = {"handoff_at": NOW.isoformat()}
    result = decide(conversation, "вопрос", make_draft(), runtime=make_runtime("shadow"), now=NOW)
    assert result["action"] == "shadow"


# ── 5–6. shadow / suggest ─────────────────────────────────────────────────

def test_step_05_shadow_mode():
    result = decide({}, "вопрос", make_draft(), runtime=make_runtime("shadow"), now=NOW)
    assert result["action"] == "shadow"
    assert "теневой режим" in result["reason"]


def test_step_06_suggest_mode():
    result = decide({}, "вопрос", make_draft(), runtime=make_runtime("suggest"), now=NOW)
    assert result["action"] == "suggest"
    assert "режим suggest" in result["reason"]


# ── 7. пустой reply ───────────────────────────────────────────────────────

def test_step_07_empty_reply():
    result = decide({}, "вопрос", make_draft(reply="   "), runtime=make_runtime("auto"), now=NOW)
    assert result["action"] == "suggest"
    assert "нет текста" in result["reason"]


# ── 8. повторный clarify ──────────────────────────────────────────────────

def test_step_08_repeated_clarify():
    draft = make_draft(reply="На каком устройстве не работает?", clarify=True, used=[])
    result = decide(
        {"clarify_already_asked": True}, "не работает", draft,
        runtime=make_runtime("auto"), now=NOW,
    )
    assert result["action"] == "suggest"
    assert "уточняющий вопрос уже задавали" in result["reason"]


def test_step_08_first_clarify_passes_kb_requirement():
    draft = make_draft(reply="На каком устройстве не работает?", clarify=True, used=[])
    result = decide({}, "не работает", draft, runtime=make_runtime("auto"), now=NOW)
    assert result["action"] == "auto"


# ── 9. require_kb × профиль (§3.3) ────────────────────────────────────────

@pytest.mark.parametrize(
    ("require_kb", "used", "profile", "expected"),
    [
        (True, ["1"], False, "auto"),
        (True, ["1"], True, "auto"),
        (True, [], False, "suggest"),
        (True, [], True, "suggest"),   # профиль не отменяет главный предохранитель
        (False, ["1"], False, "auto"),
        (False, [], True, "auto"),     # профиль заменяет опору только при require_kb=off
        (False, [], False, "suggest"),
    ],
)
def test_step_09_require_kb_profile_matrix(require_kb, used, profile, expected):
    draft = make_draft(used=used)
    result = decide(
        {}, "вопрос", draft,
        runtime=make_runtime("auto", require_kb=require_kb),
        now=NOW, profile_available=profile,
    )
    assert result["action"] == expected
    if expected == "suggest":
        assert "не опирается на базу знаний" in result["reason"]


def test_step_09_kb_hits_fallback_when_used_not_returned():
    draft = make_draft()
    draft.pop("used")
    result = decide({}, "вопрос", draft, kb_hits=2, runtime=make_runtime("auto"), now=NOW)
    assert result["action"] == "auto"


# ── 10. модель просит человека ────────────────────────────────────────────

def test_step_10_needs_human_with_require_kb():
    draft = make_draft(needs_human=True, confidence=0.99)
    result = decide({}, "вопрос", draft, runtime=make_runtime("auto", require_kb=True), now=NOW)
    assert result["action"] == "suggest"
    assert "просит человека" in result["reason"]


def test_step_10_needs_human_low_confidence_without_kb():
    draft = make_draft(needs_human=True, confidence=0.80)
    result = decide({}, "вопрос", draft, runtime=make_runtime("auto", require_kb=False), now=NOW)
    assert result["action"] == "suggest"
    assert "просит человека" in result["reason"]


def test_step_10_needs_human_high_confidence_without_kb_passes():
    draft = make_draft(needs_human=True, confidence=0.90)
    result = decide({}, "вопрос", draft, runtime=make_runtime("auto", require_kb=False), now=NOW)
    assert result["action"] == "auto"
    assert result["level"] == "check"  # needs_human не даёт «sure», но гейт пропустил


# ── 11. confidence ────────────────────────────────────────────────────────

def test_step_11_confidence_below_threshold():
    result = decide(
        {}, "вопрос", make_draft(confidence=0.80),
        runtime=make_runtime("auto", min_confidence=0.90), now=NOW,
    )
    assert result["action"] == "suggest"
    assert "ниже порога" in result["reason"]


def test_step_11_confidence_at_threshold_passes():
    result = decide(
        {}, "вопрос", make_draft(confidence=0.90),
        runtime=make_runtime("auto", min_confidence=0.90), now=NOW,
    )
    assert result["action"] == "auto"


# ── 12. escalated ─────────────────────────────────────────────────────────

def test_step_12_escalated():
    result = decide({"escalated": True}, "вопрос", make_draft(), runtime=make_runtime("auto"), now=NOW)
    assert result["action"] == "suggest"
    assert "эскалирован" in result["reason"]


# ── 13. чувствительные темы ───────────────────────────────────────────────

@pytest.mark.parametrize(
    "text",
    [
        "Верните деньги за подписку",
        "Хочу чарджбэк",
        "Это мошенничество и скам",
        "Я подам в суд и напишу юристу",
        "Мой аккаунт взломали",
        "Предлагаю партнёрство и рекламу",
        "Дайте бесплатно, пробный без оплаты",
        "I want a refund",
        "This is a scam, I will sue you",
        "My account was hacked",
    ],
)
def test_step_13_sensitive_topics(text):
    result = decide({}, text, make_draft(), runtime=make_runtime("auto"), now=NOW)
    assert result["action"] == "suggest"
    assert "чувствительная тема" in result["reason"]


def test_step_13_sensitive_precedes_closed_window():
    result = decide(
        {"window_open": False}, "Верните деньги", make_draft(),
        runtime=make_runtime("auto"), now=NOW,
    )
    assert result["action"] == "suggest"
    assert "чувствительная тема" in result["reason"]


# ── 14. агрессивный тон ───────────────────────────────────────────────────

def test_step_14_aggressive_tone():
    text = "ПОЧЕМУ НЕ РАБОТАЕТ!!! УЖЕ ЧАС ЖДУ!!!"
    result = decide({}, text, make_draft(), runtime=make_runtime("auto"), now=NOW)
    assert result["action"] == "suggest"
    assert "на взводе" in result["reason"]


def test_step_14_explicit_tone_argument():
    result = decide(
        {}, "спокойный текст", make_draft(),
        runtime=make_runtime("auto"), tone="агрессивный", now=NOW,
    )
    assert result["action"] == "suggest"
    assert "на взводе" in result["reason"]


# ── 15. окно ответа ───────────────────────────────────────────────────────

def test_step_15_closed_window_skips():
    result = decide({"window_open": False}, "вопрос", make_draft(), runtime=make_runtime("auto"), now=NOW)
    assert result["action"] == "skip"
    assert "окно ответа закрыто" in result["reason"]


# ── 16. лимит автоответов ─────────────────────────────────────────────────

def test_step_16_auto_per_hour_limit():
    result = decide(
        {}, "вопрос", make_draft(),
        runtime=make_runtime("auto", auto_per_hour=12),
        recent_auto_count=12, now=NOW,
    )
    assert result["action"] == "suggest"
    assert "12 автоответов" in result["reason"]


def test_step_16_zero_means_no_limit():
    result = decide(
        {}, "вопрос", make_draft(),
        runtime=make_runtime("auto", auto_per_hour=0),
        recent_auto_count=999, now=NOW,
    )
    assert result["action"] == "auto"


# ── 17. auto ──────────────────────────────────────────────────────────────

def test_step_17_auto_answer():
    result = decide({}, "Как обновить подписку?", make_draft(), runtime=make_runtime("auto"), now=NOW)
    assert result["action"] == "auto"
    assert "уверенность 0.95" in result["reason"]
    assert result["level"] == "sure"


# ── confidence_level ──────────────────────────────────────────────────────

def test_check_band_value():
    assert CHECK_BAND == 0.1


def test_confidence_level_sure():
    assert confidence_level(0.95, 0.90, True, False, True) == "sure"


def test_confidence_level_check_inside_band():
    assert confidence_level(0.85, 0.90, True, False, True) == "check"
    assert confidence_level(0.80, 0.90, True, False, True) == "check"


def test_confidence_level_unsure_below_band():
    assert confidence_level(0.79, 0.90, True, False, True) == "unsure"


def test_confidence_level_without_text_is_unsure():
    assert confidence_level(0.99, 0.90, True, False, False) == "unsure"


def test_confidence_level_needs_human_blocked_is_unsure():
    assert confidence_level(0.95, 0.90, True, True, True, passed=False) == "unsure"


def test_confidence_level_needs_human_passed_is_check():
    assert confidence_level(0.95, 0.90, True, True, True, passed=True) == "check"


def test_confidence_level_without_sources_is_check():
    assert confidence_level(0.95, 0.90, False, False, True) == "check"


# ── чувствительность и тон как отдельные предикаты ────────────────────────

def test_is_sensitive_plain_question_is_false():
    assert is_sensitive("Германия не подключается, что делать?") is False


def test_is_sensitive_money_is_true():
    assert is_sensitive("Верните деньги") is True


def test_is_aggressive_profanity():
    assert is_aggressive("ты что, блядь, сделал") is True


def test_is_aggressive_caps_and_exclamations():
    assert is_aggressive("ВСЁ СЛОМАНО!!!") is True
    assert is_aggressive("Спокойно, всё работает") is False


def test_tone_of_labels():
    assert tone_of("Спокойно, всё работает") == "нейтральный"
    assert tone_of("ВСЁ СЛОМАНО!!!") == "агрессивный"
