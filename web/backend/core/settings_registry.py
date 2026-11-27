"""Declarative registry of editable CMS settings.

Single source of truth for every whitelisted setting: its type, tab/category,
label, description, default, env override and select options. The API resolves
each setting's effective value and its source (`db` | `env` | `default`) and the
frontend renders controls generically from this list.

Mirrors the idea of Remnawave's config registry (schema/settings), simplified
for the CMS: no readonly DB-backed rows yet, no subcategories-by-DB.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SettingDef:
    key: str
    label: str
    category: str
    tab: str = "basic"          # "basic" | "seo" | "theme" | "finance" | "integrations"
    type: str = "text"          # text | textarea | number | bool | select | secret | json
    default: str = ""
    description: str = ""
    options: Optional[Tuple[str, ...]] = None      # fixed select options
    options_source: Optional[str] = None           # dynamic options, e.g. "themes"
    is_secret: bool = False
    is_readonly: bool = False
    env_var: Optional[str] = None
    store: str = "settings"     # "settings" | "fin_settings"
    sort_order: int = 0


REGISTRY: List[SettingDef] = [
    # ── Общие ─────────────────────────────────────────────────────────
    SettingDef(
        "admin_title", "Название CMS", "Общие", tab="basic",
        default="HexaVeil CMS",
        description="Отображается в сайдбаре и на странице входа",
        sort_order=10,
    ),
    SettingDef(
        "browser_title", "Заголовок вкладки браузера", "Сайт", tab="theme",
        default="",
        description="Если пусто — используется название CMS",
        sort_order=20,
    ),
    SettingDef(
        "title_separator", "Разделитель заголовков", "Сайт", tab="theme",
        default="—",
        description="Например: — или |",
        sort_order=30,
    ),
    SettingDef(
        "favicon_url", "URL favicon", "Сайт", tab="theme",
        default="",
        description="Пусто — встроенная иконка",
        sort_order=40,
    ),
    SettingDef(
        "site_name", "Название сайта", "Сайт", tab="theme",
        default="HexaVeil VPN", env_var="SITE_NAME",
        description="Заголовок публичной части",
        sort_order=50,
    ),
    SettingDef(
        "site_description", "Описание сайта", "Сайт", tab="theme",
        default="",
        sort_order=60,
    ),
    SettingDef(
        "site_url", "URL сайта", "Сайт", tab="theme",
        default="",
        description="Начинается с http://, https:// или /",
        sort_order=70,
    ),
    SettingDef(
        "admin_email", "Email администратора", "Общие", tab="basic",
        default="", env_var="ADMIN_EMAIL",
        sort_order=80,
    ),
    SettingDef(
        "timezone", "Часовой пояс", "Сайт", tab="theme",
        default="Europe/Moscow",
        sort_order=90,
    ),
    SettingDef(
        "locale", "Язык (locale)", "Сайт", tab="theme",
        type="select", options=("ru", "en"),
        default="ru",
        sort_order=100,
    ),

    # ── Контент ───────────────────────────────────────────────────────
    SettingDef(
        "posts_per_page", "Постов на страницу", "Контент", tab="basic",
        type="number",
        default="10",
        sort_order=10,
    ),
    SettingDef(
        "comments_auto_approve", "Автоодобрение комментариев", "Контент", tab="basic",
        type="bool",
        default="0",
        description="Новые комментарии публикуются без модерации",
        sort_order=20,
    ),
    SettingDef(
        "maintenance_mode", "Режим обслуживания", "Сайт", tab="theme",
        type="bool",
        default="0",
        description="Публичная часть показывает заглушку",
        sort_order=30,
    ),

    # ── SEO ───────────────────────────────────────────────────────────
    SettingDef(
        "meta_description", "Meta Description", "SEO", tab="seo",
        type="textarea",
        default="",
        description="SEO-описание по умолчанию (используется в <meta name=\"description\">)",
        sort_order=10,
    ),
    SettingDef(
        "meta_keywords", "Meta Keywords", "SEO", tab="seo",
        default="",
        description="Ключевые слова через запятую",
        sort_order=20,
    ),
    SettingDef(
        "og_image", "OG-изображение", "Сайт", tab="theme",
        default="",
        description="Картинка для превью в соцсетях (og:image). URL или путь",
        sort_order=30,
    ),
    SettingDef(
        "google_verification", "Google Search Console", "SEO", tab="seo",
        default="",
        description="Код подтверждения Google (мета-тег google-site-verification)",
        sort_order=40,
    ),
    SettingDef(
        "yandex_verification", "Яндекс.Вебмастер", "SEO", tab="seo",
        default="",
        description="Код подтверждения Яндекс (мета-тег yandex-verification)",
        sort_order=50,
    ),

    # ── Тема оформления ───────────────────────────────────────────────
    SettingDef(
        "active_theme", "Активная тема", "Внешний вид", tab="theme",
        type="select", options_source="themes",
        default="hexaveil",
        description="Тема, применяемая к лендингу и блогу",
        sort_order=10,
    ),

    # ── Финансы (store: fin_settings) ─────────────────────────────────
    SettingDef(
        "currency", "Валюта", "Финансы", tab="finance",
        default="₽", store="fin_settings",
        sort_order=10,
    ),
    SettingDef(
        "decimals", "Знаков после запятой", "Финансы", tab="finance",
        type="number", default="2", store="fin_settings",
        sort_order=20,
    ),
    SettingDef(
        "auto_refresh", "Автообновление, сек", "Финансы", tab="finance",
        type="number", default="0", store="fin_settings",
        description="0 — выключено",
        sort_order=30,
    ),
    SettingDef(
        "avg_period", "Период средних", "Финансы", tab="finance",
        type="select", options=("day", "week", "month", "year"),
        default="day", store="fin_settings",
        sort_order=40,
    ),
    SettingDef(
        "avg_exclude_categories", "Исключить категории (JSON)", "Финансы", tab="finance",
        type="json", default="[]", store="fin_settings",
        description="Массив категорий, исключаемых из расчёта средних",
        sort_order=50,
    ),
    SettingDef(
        "avg_exclude_income_keywords", "Исключить ключевые слова доходов (JSON)", "Финансы", tab="finance",
        type="json", default="[]", store="fin_settings",
        sort_order=60,
    ),
    SettingDef(
        "avg_exclude_expense_keywords", "Исключить ключевые слова расходов (JSON)", "Финансы", tab="finance",
        type="json", default="[]", store="fin_settings",
        sort_order=70,
    ),
    SettingDef(
        "quick_categories", "Быстрые категории (JSON)", "Финансы", tab="finance",
        type="json", default="[]", store="fin_settings",
        sort_order=80,
    ),
    SettingDef(
        "quick_participants", "Быстрые участники (JSON)", "Финансы", tab="finance",
        type="json", default="[]", store="fin_settings",
        sort_order=90,
    ),

    # ── Интеграции: Bedolaga Bot ──────────────────────────────────────
    SettingDef(
        "bedolaga_enabled", "Включить интеграцию", "Bedolaga Bot", tab="integrations",
        type="bool", default="1", env_var="BEDOLAGA_ENABLED",
        description="0 — /api/bedolaga/* отвечает 503 «отключено в настройках»",
        sort_order=10,
    ),
    SettingDef(
        "bedolaga_api_url", "URL Bot API", "Bedolaga Bot", tab="integrations",
        default="", env_var="BEDOLAGA_API_URL",
        description="Базовый URL Bot Web API, например https://bot.fortf.ru",
        sort_order=20,
    ),
    SettingDef(
        "bedolaga_api_token", "Web API token", "Bedolaga Bot", tab="integrations",
        type="secret", is_secret=True, default="", env_var="BEDOLAGA_API_TOKEN",
        description="Уходит в заголовок X-API-Key",
        sort_order=30,
    ),
    SettingDef(
        "bedolaga_timeout_seconds", "Таймаут, сек", "Bedolaga Bot", tab="integrations",
        type="number", default="15", env_var="BEDOLAGA_TIMEOUT_SECONDS",
        description="Таймаут HTTP-клиента, от 1 до 120 секунд",
        sort_order=40,
    ),
    SettingDef(
        "bedolaga_proxy_mode", "Режим прокси", "Bedolaga Bot", tab="integrations",
        type="select", options=("inherit", "direct", "custom"),
        default="inherit",
        description="«Как по умолчанию» — взять глобальный прокси, «Напрямую» — без прокси",
        sort_order=50,
    ),
    SettingDef(
        "bedolaga_proxy_url", "Свой прокси", "Bedolaga Bot", tab="integrations",
        type="secret", is_secret=True, default="",
        description="Применяется при режиме «custom». Оставьте пустым, чтобы не менять",
        sort_order=60,
    ),
    SettingDef(
        "bedolaga_proxy_no_proxy", "Исключения прокси", "Bedolaga Bot", tab="integrations",
        default="",
        description="Хосты через запятую, которые идут напрямую (например bot.fortf.ru)",
        sort_order=70,
    ),

    # ── Интеграции: Telegram / Саппорт ────────────────────────────────
    SettingDef(
        "support_tg_enabled", "Канал Telegram", "Telegram / Саппорт", tab="integrations",
        type="select", options=("auto", "on", "off"),
        default="auto", env_var="SUPPORT_TG_ENABLED",
        description="Авто — как раньше (по наличию токена); включено — требовать токен; выключено — не поднимать канал",
        sort_order=10,
    ),
    SettingDef(
        "support_tg_token", "Токен бота", "Telegram / Саппорт", tab="integrations",
        type="secret", is_secret=True, default="", env_var="SUPPORT_TG_TOKEN",
        description="Токен бота личных сообщений. Оставьте пустым, чтобы не менять",
        sort_order=20,
    ),
    SettingDef(
        "support_tg_bot_name", "Имя бота", "Telegram / Саппорт", tab="integrations",
        default="", env_var="SUPPORT_TG_BOT_NAME",
        description="Короткое имя для ключей offset (tg:<name>:offset). Пусто — main",
        sort_order=30,
    ),
    SettingDef(
        "support_tg_staff_group_id", "Id группы операторов", "Telegram / Саппорт", tab="integrations",
        default="", env_var="SUPPORT_TG_STAFF_GROUP_ID",
        description="Id группы-форума. Может быть отрицательным (например -1001234567890)",
        sort_order=40,
    ),
    SettingDef(
        "support_tg_forum", "Форум-мост", "Telegram / Саппорт", tab="integrations",
        type="bool", default="0", env_var="SUPPORT_TG_FORUM",
        description="Требует токен и id группы операторов",
        sort_order=50,
    ),
    SettingDef(
        "support_tg_archive_days", "Архивация тем, дней", "Telegram / Саппорт", tab="integrations",
        type="number", default="7", env_var="SUPPORT_TG_ARCHIVE_DAYS",
        description="Дней неактивности до архивации темы (не меньше 1)",
        sort_order=60,
    ),
    SettingDef(
        "support_poll_interval_seconds", "Интервал опроса, сек", "Telegram / Саппорт", tab="integrations",
        type="number", default="60", env_var="SUPPORT_POLL_INTERVAL_SECONDS",
        description="Период опроса каналов (не меньше 5 секунд)",
        sort_order=70,
    ),
    SettingDef(
        "support_window_hours", "Окно ответа, ч", "Telegram / Саппорт", tab="integrations",
        type="number", default="24", env_var="SUPPORT_WINDOW_HOURS",
        description="Окно ответа оператора для не-Telegram каналов (не меньше 1 часа)",
        sort_order=80,
    ),
    SettingDef(
        "support_bedolaga_enabled", "Канал Bedolaga", "Telegram / Саппорт", tab="integrations",
        type="select", options=("auto", "on", "off"),
        default="auto", env_var="SUPPORT_BEDOLAGA_ENABLED",
        description="Канал заявок Bedolaga в Саппорте",
        sort_order=90,
    ),
    SettingDef(
        "support_proxy_mode", "Режим прокси", "Telegram / Саппорт", tab="integrations",
        type="select", options=("inherit", "direct", "custom"),
        default="inherit",
        description="«Как по умолчанию» — взять глобальный прокси, «Напрямую» — без прокси",
        sort_order=100,
    ),
    SettingDef(
        "support_proxy_url", "Свой прокси", "Telegram / Саппорт", tab="integrations",
        type="secret", is_secret=True, default="",
        description="Применяется при режиме «custom». Оставьте пустым, чтобы не менять",
        sort_order=110,
    ),
    SettingDef(
        "support_proxy_no_proxy", "Исключения прокси", "Telegram / Саппорт", tab="integrations",
        default="",
        description="Хосты через запятую, которые идут напрямую (например api.telegram.org)",
        sort_order=120,
    ),

    # ── Интеграции: Bedolaga БД (прокси не применим) ──────────────────
    SettingDef(
        "bot_db_host", "Хост PostgreSQL", "Bedolaga БД", tab="integrations",
        default="", env_var="BOT_DB_HOST",
        description=(
            "Пусто — используется BOT_DB_HOST из окружения; если и он пуст, тарифы отключены. "
            "Прокси не применим — это TCP-подключение к PostgreSQL. Нужен SSH-туннель/VPN на хосте CMS."
        ),
        sort_order=10,
    ),
    SettingDef(
        "bot_db_port", "Порт", "Bedolaga БД", tab="integrations",
        type="number", default="5434", env_var="BOT_DB_PORT",
        description="Порт PostgreSQL бота (от 1 до 65535)",
        sort_order=20,
    ),
    SettingDef(
        "bot_db_name", "Имя БД", "Bedolaga БД", tab="integrations",
        default="remnawave_bot", env_var="BOT_DB_NAME",
        sort_order=30,
    ),
    SettingDef(
        "bot_db_user", "Пользователь", "Bedolaga БД", tab="integrations",
        default="cms_ro", env_var="BOT_DB_USER",
        description="Read-only пользователь БД бота",
        sort_order=40,
    ),
    SettingDef(
        "bot_db_pass", "Пароль", "Bedolaga БД", tab="integrations",
        type="secret", is_secret=True, default="", env_var="BOT_DB_PASS",
        description="Оставьте пустым, чтобы не менять сохранённый пароль",
        sort_order=50,
    ),

    SettingDef(
        "platega_merchant_id", "Merchant ID", "Platega", tab="integrations",
        default="", store="fin_settings", env_var="PLATEGA_MERCHANT_ID",
        sort_order=10,
    ),
    SettingDef(
        "platega_secret", "Секрет", "Platega", tab="integrations",
        type="secret", is_secret=True, default="", store="fin_settings",
        env_var="PLATEGA_SECRET",
        description="Оставьте пустым, чтобы не менять сохранённый ключ",
        sort_order=20,
    ),
    SettingDef(
        "platega_days_back", "Дней назад", "Platega", tab="integrations",
        type="number", default="150", store="fin_settings", env_var="PLATEGA_DAYS_BACK",
        sort_order=30,
    ),
    SettingDef(
        "platega_auto_sync", "Автоимпорт", "Platega", tab="integrations",
        type="bool", default="0", store="fin_settings", env_var="PLATEGA_AUTO_SYNC",
        sort_order=40,
    ),
    SettingDef(
        "platega_cron_token", "Cron-токен", "Platega", tab="integrations",
        type="secret", is_secret=True, default="", store="fin_settings",
        env_var="PLATEGA_CRON_TOKEN",
        description="Токен для запуска синхронизации по cron",
        sort_order=60,
    ),
    SettingDef(
        "platega_proxy_mode", "Режим прокси", "Platega", tab="integrations",
        type="select", options=("inherit", "direct", "custom"),
        default="inherit",
        description="Прокси для запросов к app.platega.io",
        sort_order=70,
    ),
    SettingDef(
        "platega_proxy_url", "Свой прокси", "Platega", tab="integrations",
        type="secret", is_secret=True, default="",
        description="Применяется при режиме «custom». Оставьте пустым, чтобы не менять",
        sort_order=80,
    ),
    SettingDef(
        "platega_proxy_no_proxy", "Исключения прокси", "Platega", tab="integrations",
        default="",
        description="Хосты через запятую, которые идут напрямую",
        sort_order=90,
    ),

    SettingDef(
        "yookassa_shop_id", "Shop ID", "YooKassa", tab="integrations",
        default="", store="fin_settings", env_var="YOOKASSA_SHOP_ID",
        sort_order=10,
    ),
    SettingDef(
        "yookassa_secret_key", "Секретный ключ", "YooKassa", tab="integrations",
        type="secret", is_secret=True, default="", store="fin_settings",
        env_var="YOOKASSA_SECRET_KEY",
        description="Оставьте пустым, чтобы не менять сохранённый ключ",
        sort_order=20,
    ),
    SettingDef(
        "yookassa_days_back", "Дней назад", "YooKassa", tab="integrations",
        type="number", default="150", store="fin_settings", env_var="YOOKASSA_DAYS_BACK",
        sort_order=30,
    ),
    SettingDef(
        "yookassa_auto_sync", "Автоимпорт", "YooKassa", tab="integrations",
        type="bool", default="0", store="fin_settings", env_var="YOOKASSA_AUTO_SYNC",
        sort_order=40,
    ),
    SettingDef(
        "yookassa_commissions", "Комиссии по методам (JSON)", "YooKassa", tab="integrations",
        type="json",
        default='{"bank_card":3,"sbp":0.5,"yoo_money":3,"sberbank":3,"tinkoff_bank":3,"mobile":6,"cash":3,"qiwi":3}',
        store="fin_settings", env_var="YOOKASSA_COMMISSIONS",
        sort_order=50,
    ),
    SettingDef(
        "yookassa_cron_token", "Cron-токен", "YooKassa", tab="integrations",
        type="secret", is_secret=True, default="", store="fin_settings",
        env_var="YOOKASSA_CRON_TOKEN",
        description="Токен для запуска синхронизации по cron",
        sort_order=60,
    ),
    SettingDef(
        "yookassa_proxy_mode", "Режим прокси", "YooKassa", tab="integrations",
        type="select", options=("inherit", "direct", "custom"),
        default="inherit",
        description="Прокси для запросов к api.yookassa.ru",
        sort_order=70,
    ),
    SettingDef(
        "yookassa_proxy_url", "Свой прокси", "YooKassa", tab="integrations",
        type="secret", is_secret=True, default="",
        description="Применяется при режиме «custom». Оставьте пустым, чтобы не менять",
        sort_order=80,
    ),
    SettingDef(
        "yookassa_proxy_no_proxy", "Исключения прокси", "YooKassa", tab="integrations",
        default="",
        description="Хосты через запятую, которые идут напрямую",
        sort_order=90,
    ),

    # ── Интеграции: Прокси по умолчанию ───────────────────────────────
    SettingDef(
        "outbound_proxy_url", "URL прокси по умолчанию", "Прокси по умолчанию", tab="integrations",
        type="secret", is_secret=True, default="", env_var="OUTBOUND_PROXY_URL",
        description="http://, https://, socks5:// или socks5h:// (+ user:pass@). Пусто — все интеграции идут напрямую",
        sort_order=10,
    ),
    SettingDef(
        "outbound_proxy_no_proxy", "Исключения (no_proxy)", "Прокси по умолчанию", tab="integrations",
        default="", env_var="OUTBOUND_PROXY_NO_PROXY",
        description="Хосты через запятую: api.telegram.org, .local, *. Хост из списка идёт напрямую",
        sort_order=20,
    ),
    SettingDef(
        "outbound_proxy_test_url", "URL проверки egress-IP", "Прокси по умолчанию", tab="integrations",
        default="https://api.ipify.org", env_var="OUTBOUND_PROXY_TEST_URL",
        description="Адрес, который возвращает внешний IP для проверки прокси",
        sort_order=30,
    ),
]

REGISTRY_BY_KEY: Dict[str, SettingDef] = {s.key: s for s in REGISTRY}

# Keys accepted by POST /api/settings (registry + JSON blobs handled specially).
BLOB_KEYS = ("docker_config", "loki_config")
ALLOWED_KEYS: List[str] = [s.key for s in REGISTRY] + list(BLOB_KEYS)

# Integration key groups — used by core.integrations for runtime invalidation
# so prefix parsing is not duplicated there.
BEDOLAGA_KEYS: Tuple[str, ...] = (
    "bedolaga_enabled",
    "bedolaga_api_url",
    "bedolaga_api_token",
    "bedolaga_timeout_seconds",
    "bedolaga_proxy_mode",
    "bedolaga_proxy_url",
    "bedolaga_proxy_no_proxy",
)
SUPPORT_KEYS: Tuple[str, ...] = (
    "support_tg_enabled",
    "support_tg_token",
    "support_tg_bot_name",
    "support_tg_staff_group_id",
    "support_tg_forum",
    "support_tg_archive_days",
    "support_poll_interval_seconds",
    "support_window_hours",
    "support_bedolaga_enabled",
    "support_proxy_mode",
    "support_proxy_url",
    "support_proxy_no_proxy",
)
BOT_DB_KEYS: Tuple[str, ...] = (
    "bot_db_host",
    "bot_db_port",
    "bot_db_name",
    "bot_db_user",
    "bot_db_pass",
)
PROXY_KEYS: Tuple[str, ...] = (
    "outbound_proxy_url",
    "outbound_proxy_no_proxy",
    "outbound_proxy_test_url",
    "bedolaga_proxy_mode",
    "bedolaga_proxy_url",
    "bedolaga_proxy_no_proxy",
    "support_proxy_mode",
    "support_proxy_url",
    "support_proxy_no_proxy",
    "platega_proxy_mode",
    "platega_proxy_url",
    "platega_proxy_no_proxy",
    "yookassa_proxy_mode",
    "yookassa_proxy_url",
    "yookassa_proxy_no_proxy",
)


def env_value(defn: SettingDef) -> str:
    """Read the definition's env override (empty string if none/unset)."""
    if not defn.env_var:
        return ""
    return os.environ.get(defn.env_var, "") or ""


def resolve(defn: SettingDef, db_value: Optional[str]) -> Dict[str, object]:
    """Resolve effective value + source for a setting.

    Priority for regular settings: database → environment → default.
    Finance settings (store='fin_settings') flip the first two — env → database
    → default — so providers can be configured from .env without touching the DB.
    `is_env_override` is true when an env var is present. Secret values are never
    exposed: `value` is blanked out and `is_set` reports whether one is stored.
    """
    env = env_value(defn)
    env_first = defn.store == "fin_settings"

    if env and env_first:
        source, raw = "env", env
    elif db_value is not None and db_value != "":
        source, raw = "db", db_value
    elif env:
        source, raw = "env", env
    else:
        source, raw = "default", defn.default

    is_set = bool(db_value)
    return {
        "key": defn.key,
        "label": defn.label,
        "description": defn.description,
        "category": defn.category,
        "tab": defn.tab,
        "type": defn.type,
        "default": "" if defn.is_secret else defn.default,
        "value": "" if defn.is_secret else raw,
        "source": source,
        "is_set": is_set,
        "store": defn.store,
        "options": list(defn.options) if defn.options else None,
        "options_source": defn.options_source,
        "is_secret": defn.is_secret,
        "is_readonly": defn.is_readonly,
        "is_env_override": bool(env),
        "env_var_name": defn.env_var,
        "sort_order": defn.sort_order,
    }
