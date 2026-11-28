"""Ворота автоответа: единственное место, где решается, уходит ли текст клиенту.

Порядок проверок фиксирован планом §3.2 (17 пунктов). Черновик сохраняется
всегда; вопрос только в действии: `skip` / `shadow` / `suggest` / `auto`.

Модуль чистый: не читает store/БД сам — состояние диалога, runtime и пауза
передаются аргументами. Только stdlib.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

CHECK_BAND = 0.1

MODES = ("off", "shadow", "suggest", "auto")
_MISSING = object()

# ── Чувствительные темы (RU + EN) ────────────────────────────────────────
# Текст перед проверкой нормализуется: lower + ё→е.
_SENSITIVE: tuple[re.Pattern[str], ...] = (
    re.compile(r"возврат|верните|вернуть деньг|refund|chargeback|чарджбэк", re.I),
    re.compile(r"списал[а-я]*|двойн(?:ая|ое|ой) оплат|не приш(?:ел|ла|ло)? плат|дважды снял", re.I),
    re.compile(r"обман|мошенн|развод|скам|(?<![а-яa-z])scam(?![а-яa-z])|кинул|fraud", re.I),
    re.compile(
        r"(?<![а-я])(?:суд(?:а|у|ом|е|ы|ов|ам|ами|ах)?|судебн[а-я]*|засуд[а-я]*)(?![а-я])"
        r"|юрист|адвокат|жалоб|жаловать|пожалуюсь|прокуратур|роскомнадзор|полици"
        r"|(?<![a-z])(?:lawyer|attorney|court|lawsuit)(?![a-z])|legal action",
        re.I,
    ),
    re.compile(
        r"взлом|украл|угнал|доступ к аккаунту|сменил пароль"
        r"|(?<![a-z])(?:hack(?:ed)?|stolen|unauthorized access|account compromised)(?![a-z])",
        re.I,
    ),
    re.compile(
        r"партн[её]рств|сотрудничеств|оптом|реселл"
        r"|(?<![a-z])(?:partnership|advertis\w*|investment)(?![a-z])|инвестиц|реклам",
        re.I,
    ),
    re.compile(r"угроз|оскорб|уничтож|засужу|(?<![a-z])(?:threat\w*|insult\w*)(?![a-z])", re.I),
    re.compile(
        r"персональн|паспорт|снилс|(?<![а-я])инн(?![а-я])|данные карты"
        r"|(?<![a-z])personal data(?![a-z])|passport",
        re.I,
    ),
    re.compile(
        r"бесплатн|пробн[а-я]* без оплат|(?<![a-z])free trial(?![a-z])|give .* free",
        re.I,
    ),
)

_PROFANITY = re.compile(
    r"бляд|хуй|хуя|пизд|ебат|ебал|ебан|сука|долбоеб|мудак|мудил"
    r"|(?<![a-z])(?:fuck|shit|bitch|asshole)(?![a-z])",
    re.I,
)


def _norm(text: str) -> str:
    return (text or "").lower().replace("ё", "е")


def is_sensitive(text: str) -> bool:
    """Чувствительная тема: деньги, юристы, взлом, партнёрство, угрозы и т.п."""
    normalized = _norm(text)
    return any(pattern.search(normalized) for pattern in _SENSITIVE)


def is_aggressive(text: str) -> bool:
    """Простая эвристика тона: брань, капс (≥60% букв), две и более `!`."""
    value = text or ""
    if _PROFANITY.search(_norm(value)):
        return True
    letters = [ch for ch in value if ch.isalpha()]
    if len(letters) >= 10:
        upper = sum(1 for ch in letters if ch.isupper())
        if upper / len(letters) >= 0.6:
            return True
    return value.count("!") >= 2


def tone_of(text: str) -> str:
    """Тон в терминах плана: «агрессивный» / «нейтральный»."""
    return "агрессивный" if is_aggressive(text) else "нейтральный"


def confidence_level(
    score: float,
    min_confidence: float,
    has_sources: bool,
    needs_human: bool,
    has_text: bool,
    passed: bool | None = None,
) -> str:
    """Уровень уверенности от порога настроек, а не от своей константы.

    * `sure` — score ≥ порога, есть источники, модель не просила человека;
    * `unsure` — текста нет, модель просила человека и гейт не пропустил,
      или score ниже `min_confidence - CHECK_BAND`;
    * иначе `check`.
    """
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = 0.0
    try:
        threshold = float(min_confidence)
    except (TypeError, ValueError):
        threshold = 0.0

    if not has_text:
        return "unsure"
    if needs_human and passed is not True:
        return "unsure"
    if value < threshold - CHECK_BAND:
        return "unsure"
    if value >= threshold and has_sources and not needs_human:
        return "sure"
    return "check"


def _get(source: Any, name: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on", "вкл")


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _pause_active(pause: Any, now: datetime) -> bool:
    """Пауза: bool, ISO-строка или dict/объект с `until`."""
    if pause is None:
        return False
    if isinstance(pause, bool):
        return pause
    if isinstance(pause, str):
        until = _parse_dt(pause)
        return bool(until and until > now)
    if isinstance(pause, dict):
        if "until" in pause:
            until = _parse_dt(pause.get("until"))
            return bool(until and until > now)
        return _as_bool(pause.get("active"))
    until = _parse_dt(getattr(pause, "until", None))
    return bool(until and until > now)


def _human_hold_active(conversation: Any, runtime: Any, now: datetime) -> bool:
    explicit = _get(conversation, "human_hold", _MISSING)
    if explicit is not _MISSING:
        return _as_bool(explicit)

    until = _parse_dt(_get(conversation, "human_hold_until", None))
    if until and until > now:
        return True

    last = _parse_dt(_get(conversation, "last_human_reply_at", None))
    if last is None:
        return False
    try:
        minutes = int(_get(runtime, "human_hold_minutes", 30) or 0)
    except (TypeError, ValueError):
        minutes = 0
    if minutes <= 0:
        return False
    return (now - last).total_seconds() < minutes * 60


def _window_open(conversation: Any) -> bool:
    value = _get(conversation, "window_open", _MISSING)
    if value is not _MISSING:
        return _as_bool(value)
    value = _get(conversation, "reply_window_open", _MISSING)
    if value is not _MISSING:
        return _as_bool(value)
    window = _get(conversation, "window", _MISSING)
    if isinstance(window, dict) and "open" in window:
        return _as_bool(window.get("open"))
    return True


def _profile_available(conversation: Any) -> bool:
    for name in ("profile_available", "profile", "customer_profile"):
        value = _get(conversation, name, _MISSING)
        if value is not _MISSING:
            return bool(value)
    return False


def _clarify_already_asked(conversation: Any) -> bool:
    for name in ("clarify_already_asked", "clarify_asked"):
        value = _get(conversation, name, _MISSING)
        if value is not _MISSING:
            return _as_bool(value)
    return False


def decide(
    conversation: Any,
    client_text: str,
    draft: Any,
    kb_hits: int = 0,
    runtime: Any = None,
    pause: Any = None,
    recent_auto_count: int = 0,
    tone: str | None = None,
    *,
    human_hold: bool | None = None,
    window_open: bool | None = None,
    profile_available: bool | None = None,
    clarify_already_asked: bool | None = None,
    now: datetime | None = None,
) -> dict[str, str]:
    """Решить судьбу черновика по точному порядку §3.2.

    Вход: диалог, текст клиента, черновик модели, число найденных выдержек,
    runtime-настройки (`AiConfig`/dict), пауза, счётчик автоответов за час,
    тон. Возвращает `{action, reason, level}`.
    """
    moment = now or datetime.now(timezone.utc)

    mode = str(_get(runtime, "effective_mode", None) or _get(runtime, "mode", "off")).lower()
    if mode not in MODES:
        mode = "off"

    reply = str(_get(draft, "reply", "") or "").strip()
    needs_human = _as_bool(_get(draft, "needs_human", False))
    clarify = _as_bool(_get(draft, "clarify", False))
    used = _get(draft, "used", _MISSING)
    try:
        confidence = float(_get(draft, "confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0

    if used is _MISSING or used is None:
        has_sources = int(kb_hits or 0) > 0
    else:
        has_sources = bool(used)

    require_kb = _as_bool(_get(runtime, "require_kb", True))
    try:
        min_confidence = float(_get(runtime, "min_confidence", 0.90) or 0.0)
    except (TypeError, ValueError):
        min_confidence = 0.90
    try:
        auto_per_hour = int(_get(runtime, "auto_per_hour", 12) or 0)
    except (TypeError, ValueError):
        auto_per_hour = 0

    hold = _human_hold_active(conversation, runtime, moment) if human_hold is None else bool(human_hold)
    opened = _window_open(conversation) if window_open is None else bool(window_open)
    profile = _profile_available(conversation) if profile_available is None else bool(profile_available)
    clarified_before = (
        _clarify_already_asked(conversation)
        if clarify_already_asked is None
        else bool(clarify_already_asked)
    )
    escalated = _as_bool(_get(conversation, "escalated", False))
    handoff = _get(conversation, "handoff_at", None)

    def result(action: str, reason: str) -> dict[str, str]:
        passed = action in ("auto", "shadow", "suggest")
        level = confidence_level(
            confidence,
            min_confidence,
            has_sources,
            needs_human,
            bool(reply),
            passed=passed,
        )
        return {"action": action, "reason": reason, "level": level}

    # 1. Глобальный рубильник.
    if mode == "off":
        return result("skip", "ИИ выключен")

    # 2. Пауза помощника: клиенту ничего, черновик человеку остаётся.
    if _pause_active(pause, moment):
        if mode == "shadow":
            return result("shadow", "теневой режим: только внутренний черновик")
        return result("suggest", "пауза помощника: только предложка")

    # 3. Ответ оператора важнее любых свойств черновика; раньше доверия/КБ.
    if hold:
        if mode == "shadow":
            return result("shadow", "теневой режим: только внутренний черновик")
        return result("suggest", "пауза после ответа оператора: только предложка")

    # 4. Диалог ждёт специалиста.
    if handoff:
        if mode == "shadow":
            return result("shadow", "теневой режим: только внутренний черновик")
        return result("suggest", "диалог ждёт специалиста: только предложка")

    # 5. Теневой режим.
    if mode == "shadow":
        return result("shadow", "теневой режим: только внутренний черновик")

    # 6. Не auto — только предложка.
    if mode != "auto":
        return result("suggest", f"режим {mode}")

    # 7. Пустой текст.
    if not reply:
        return result("suggest", "нет текста для клиента")

    # 8. Повторный уточняющий вопрос.
    if clarify and clarified_before:
        return result("suggest", "уточняющий вопрос уже задавали")

    # 9. Опора на КБ × профиль клиента (§3.3).
    if not has_sources and not clarify:
        if require_kb:
            return result("suggest", "ответ не опирается на базу знаний")
        if not profile:
            return result("suggest", "ответ не опирается на базу знаний")

    # 10. Модель сама просит человека.
    if needs_human and (require_kb or confidence < 0.85):
        return result("suggest", "модель сама просит человека")

    # 11. Ниже порога уверенности.
    if confidence < min_confidence:
        return result("suggest", f"уверенность {confidence:.2f} ниже порога")

    # 12. Эскалация.
    if escalated:
        return result("suggest", "диалог эскалирован")

    # 13. Чувствительная тема.
    if is_sensitive(client_text):
        return result("suggest", "чувствительная тема")

    # 14. Клиент на взводе.
    effective_tone = tone if tone is not None else tone_of(client_text)
    if effective_tone in ("агрессивный", "aggressive") or is_aggressive(client_text):
        return result("suggest", "клиент на взводе — нужен человек")

    # 15. Окно ответа закрыто.
    if not opened:
        return result("skip", "окно ответа закрыто")

    # 16. Лимит автоответов в час (0 — без лимита).
    if auto_per_hour > 0:
        try:
            recent = int(recent_auto_count or 0)
        except (TypeError, ValueError):
            recent = 0
        if recent >= auto_per_hour:
            return result("suggest", f"в этом диалоге уже {recent} автоответов за час")

    # 17. Всё чисто.
    return result("auto", f"уверенность {confidence:.2f}")
