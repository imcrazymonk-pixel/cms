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
    tab: str = "basic"          # "basic" | "appearance"
    type: str = "text"          # text | textarea | number | bool | select | secret
    default: str = ""
    description: str = ""
    options: Optional[Tuple[str, ...]] = None      # fixed select options
    options_source: Optional[str] = None           # dynamic options, e.g. "themes"
    is_secret: bool = False
    is_readonly: bool = False
    env_var: Optional[str] = None
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
        "browser_title", "Заголовок вкладки браузера", "Общие", tab="basic",
        default="",
        description="Если пусто — используется название CMS",
        sort_order=20,
    ),
    SettingDef(
        "title_separator", "Разделитель заголовков", "Общие", tab="basic",
        default="—",
        description="Например: — или |",
        sort_order=30,
    ),
    SettingDef(
        "favicon_url", "URL favicon", "Общие", tab="basic",
        default="",
        description="Пусто — встроенная иконка",
        sort_order=40,
    ),
    SettingDef(
        "site_name", "Название сайта", "Общие", tab="basic",
        default="HexaVeil VPN", env_var="SITE_NAME",
        description="Заголовок публичной части",
        sort_order=50,
    ),
    SettingDef(
        "site_description", "Описание сайта", "Общие", tab="basic",
        default="",
        sort_order=60,
    ),
    SettingDef(
        "site_url", "URL сайта", "Общие", tab="basic",
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
        "timezone", "Часовой пояс", "Общие", tab="basic",
        default="Europe/Moscow",
        sort_order=90,
    ),
    SettingDef(
        "locale", "Язык (locale)", "Общие", tab="basic",
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
        "maintenance_mode", "Режим обслуживания", "Контент", tab="basic",
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
        "og_image", "OG-изображение", "SEO", tab="seo",
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
]

REGISTRY_BY_KEY: Dict[str, SettingDef] = {s.key: s for s in REGISTRY}

# Keys accepted by POST /api/settings (registry + JSON blobs handled specially).
BLOB_KEYS = ("docker_config", "loki_config")
ALLOWED_KEYS: List[str] = [s.key for s in REGISTRY] + list(BLOB_KEYS)


def env_value(defn: SettingDef) -> str:
    """Read the definition's env override (empty string if none/unset)."""
    if not defn.env_var:
        return ""
    return os.environ.get(defn.env_var, "") or ""


def resolve(defn: SettingDef, db_value: Optional[str]) -> Dict[str, object]:
    """Resolve effective value + source for a setting.

    Priority: database → environment → default. `is_env_override` is true when
    an env var is present (even if the DB value wins).
    """
    env = env_value(defn)
    if db_value is not None and db_value != "":
        source, value = "db", db_value
    elif env:
        source, value = "env", env
    else:
        source, value = "default", defn.default
    return {
        "key": defn.key,
        "label": defn.label,
        "description": defn.description,
        "category": defn.category,
        "tab": defn.tab,
        "type": defn.type,
        "default": defn.default,
        "value": value,
        "source": source,
        "options": list(defn.options) if defn.options else None,
        "options_source": defn.options_source,
        "is_secret": defn.is_secret,
        "is_readonly": defn.is_readonly,
        "is_env_override": bool(env),
        "env_var_name": defn.env_var,
        "sort_order": defn.sort_order,
    }
