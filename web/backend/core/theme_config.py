"""Theme configuration — mirrors templates/themes/{theme}/theme.php.

The active theme's options are used by GET /api/themes/settings.
Until themes are fully migrated to Python, the option definitions live
here as static dicts. When a theme.php changes, update the matching
entry below.

Structure mirrors theme.php:
  {
    "name": "...",
    "options": {
        "Group label": {
            "key": {"label": ..., "type": ..., "default": ..., ...}
        }
    }
  }
"""
from typing import Any, Dict

# ── hexaveil (landing) ────────────────────────────────────────────
_HEXAVEIL: Dict[str, Any] = {
    "name": "HexaVeil (лендинг)",
    "options": {
        "Ссылки и контакты": {
            "cabinet_url": {"label": "URL личного кабинета", "type": "text", "default": "https://cabinet.fortf.ru/login"},
            "referral_url": {"label": "URL реферальной программы", "type": "text", "default": "https://cabinet.fortf.ru/referral"},
            "telegram_url": {"label": "Ссылка Telegram", "type": "text", "default": "https://t.me/HexaVeil_bot"},
            "cta_label": {"label": "Кнопка в шапке (личный кабинет)", "type": "text", "default": "Личный кабинет"},
        },
        "Tagline (заголовок над hero)": {
            "tagline_line1": {"label": "Первая строка заголовка", "type": "text", "default": "Ваш надежный VPN&nbsp;провайдер", "hint": "HTML-сущности разрешены (например &amp;nbsp;)"},
            "tagline_line2": {"label": "Вторая строка (акцент)", "type": "text", "default": "в мир интернета"},
            "tagline_subtitle": {"label": "Подзаголовок", "type": "textarea", "rows": 2, "default": "Смотрите любимые сериалы, работайте с международными сервисами и общайтесь без ограничений."},
            "tagline_btn1": {"label": "Кнопка 1", "type": "text", "default": "Попробовать бесплатно"},
            "tagline_btn2": {"label": "Кнопка 2", "type": "text", "default": "Как это работает"},
        },
        "Преимущества под tagline (4 шт.)": {
            "benefit1": {"label": "Преимущество 1", "type": "text", "default": "Все мировые сервисы: Instagram, YouTube без рекламы, ChatGPT, Netflix, Discord"},
            "benefit2": {"label": "Преимущество 2", "type": "text", "default": "Российские сервисы работают - VPN не нужно выключать"},
            "benefit3": {"label": "Преимущество 3", "type": "text", "default": "Живая поддержка 24/7 - решает вопросы, а не кормит ответами бота"},
            "benefit4": {"label": "Преимущество 4", "type": "text", "default": "Стабильная работа благодаря распределённым серверам"},
        },
        "Панель серверов (hero)": {
            "hero_note": {"label": "Подпись под панелью серверов", "type": "text", "default": "Выберите сервер — планета подлетит к нему"},
        },
        "Статистика (4 шт.)": {
            "stat1_num": {"label": "Число 1", "type": "text", "default": "10+"},
            "stat1_label": {"label": "Подпись 1", "type": "text", "default": "Стран с серверами"},
            "stat2_num": {"label": "Число 2", "type": "text", "default": "99.9%"},
            "stat2_label": {"label": "Подпись 2", "type": "text", "default": "Время работы (Uptime)"},
            "stat3_num": {"label": "Число 3", "type": "text", "default": "10 Гбит/с"},
            "stat3_label": {"label": "Подпись 3", "type": "text", "default": "Пропускная способность"},
            "stat4_num": {"label": "Число 4", "type": "text", "default": "10K+"},
            "stat4_label": {"label": "Подпись 4", "type": "text", "default": "Активных пользователей"},
        },
        "Пробный доступ (Trial)": {
            "trial_badge": {"label": "Бейдж", "type": "text", "default": "Без оплаты и обязательств"},
            "trial_title": {"label": "Заголовок", "type": "text", "default": "Попробуйте HexaVeil бесплатно"},
            "trial_subtitle": {"label": "Подзаголовок", "type": "textarea", "rows": 3, "default": "Получите 24 часа полного доступа - без ввода карты и автоматических списаний. Убедитесь в скорости и стабильности на реальных сервисах, и только потом решайте."},
            "trial_step1_title": {"label": "Шаг 1: заголовок", "type": "text", "default": "Авторизуйтесь"},
            "trial_step1_text": {"label": "Шаг 1: текст", "type": "text", "default": "Авторизуйтесь в личном кабинете удобным для тебя способом"},
            "trial_step2_title": {"label": "Шаг 2: заголовок", "type": "text", "default": "Получите конфиг"},
            "trial_step2_text": {"label": "Шаг 2: текст", "type": "text", "default": "Бот пришлёт готовую конфигурацию для вашего устройства"},
            "trial_step3_title": {"label": "Шаг 3: заголовок", "type": "text", "default": "Подключайтесь"},
            "trial_step3_text": {"label": "Шаг 3: текст", "type": "text", "default": "Импортируйте в любой клиент - и пользуйтесь 72 часа"},
            "trial_button": {"label": "Текст кнопки", "type": "text", "default": "Получить бесплатный доступ"},
            "trial_note": {"label": "Примечание", "type": "textarea", "rows": 2, "default": "Триал ограничен одним устройством на аккаунт. Без автосписаний - решение за вами."},
        },
        "Возможности (4 карточки)": {
            "feature1_title": {"label": "Карточка 1: заголовок", "type": "text", "default": "Доступ к любимым сервисам"},
            "feature1_text": {"label": "Карточка 1: текст", "type": "text", "default": "YouTube, ChatGPT, Netflix, Spotify и другие международные платформы - стабильно, быстро и без лишних действий."},
            "feature2_title": {"label": "Карточка 2: заголовок", "type": "text", "default": "Защищённое соединение"},
            "feature2_text": {"label": "Карточка 2: текст", "type": "text", "default": "Ваш трафик шифруется и проходит через наши серверы. Провайдер не видит, какие ресурсы вы посещаете."},
            "feature3_title": {"label": "Карточка 3: заголовок", "type": "text", "default": "10+ стран мира"},
            "feature3_text": {"label": "Карточка 3: текст", "type": "text", "default": "Серверы в Европе, Азии и Америке. Выбирайте локацию для минимальной задержки и максимальной скорости."},
            "feature4_title": {"label": "Карточка 4: заголовок", "type": "text", "default": "Стриминг без буферизации"},
            "feature4_text": {"label": "Карточка 4: текст", "type": "text", "default": "Видео в 4K и музыка в высоком качестве - без задержек и прерываний. Выделенные каналы для медиа-трафика."},
        },
        "Сервисы": {
            "services_title": {"label": "Заголовок секции", "type": "text", "default": "Открой любимые сервисы"},
            "services_intro": {"label": "Вступление", "type": "textarea", "rows": 2, "default": "Мы гарантируем стабильное соединение с самыми популярными международными платформами."},
            "services_list": {"label": "Список сервисов (по одному в строке)", "type": "textarea", "rows": 8, "default": "YouTube\nChatGPT\nNetflix\nSpotify\nClaude AI\nX (Twitter)\nDiscord"},
            "services_note": {"label": "Примечание", "type": "textarea", "rows": 2, "default": "Список сервисов регулярно расширяется. Если нужной платформы нет в списке - напишите в поддержку, добавим."},
        },
        "Технологии (3 карточки)": {
            "tech1_title": {"label": "Карточка 1: заголовок", "type": "text", "default": "Современный протокол"},
            "tech1_text": {"label": "Карточка 1: текст", "type": "text", "default": "VLESS - для скорости и незаметности трафика."},
            "tech2_title": {"label": "Карточка 2: заголовок", "type": "text", "default": "Без журналов подключений"},
            "tech2_text": {"label": "Карточка 2: текст", "type": "text", "default": "Мы не отслеживаем ваши действия и не сохраняем историю посещений. Ваша приватность для нас действительно важна!"},
            "tech3_title": {"label": "Карточка 3: заголовок", "type": "text", "default": "Шифрование AES-256"},
            "tech3_text": {"label": "Карточка 3: текст", "type": "text", "default": "Ваши данные защищены военным стандартом шифрования. Трафик невозможно перехватить и прочитать."},
        },
        "Реферальная программа": {
            "referral_title": {"label": "Заголовок", "type": "text", "default": "Приглашайте друзей - получайте бонусы"},
            "referral_intro": {"label": "Вступление", "type": "textarea", "rows": 3, "default": "Делитесь персональной ссылкой: вы и друг получите по 50 ₽, а вы - ещё 20% с его пополнений. Чем больше друзей - тем выгоднее."},
            "referral_card1_value": {"label": "Карточка 1: значение", "type": "text", "default": "+50 ₽"},
            "referral_card1_title": {"label": "Карточка 1: заголовок", "type": "text", "default": "Вам за друга"},
            "referral_card1_text": {"label": "Карточка 1: текст", "type": "text", "default": "За каждого друга, который оплатит подписку по вашей ссылке"},
            "referral_card2_value": {"label": "Карточка 2: значение", "type": "text", "default": "+50 ₽"},
            "referral_card2_title": {"label": "Карточка 2: заголовок", "type": "text", "default": "Другу на старт"},
            "referral_card2_text": {"label": "Карточка 2: текст", "type": "text", "default": "Подарок другу к первой оплате по вашей ссылке"},
            "referral_card3_value": {"label": "Карточка 3: значение", "type": "text", "default": "20%"},
            "referral_card3_title": {"label": "Карточка 3: заголовок", "type": "text", "default": "С пополнений"},
            "referral_card3_text": {"label": "Карточка 3: текст", "type": "text", "default": "Процент с пополнений ваших рефералов - навсегда"},
            "referral_button": {"label": "Текст кнопки", "type": "text", "default": "Получить реферальную ссылку"},
            "referral_note": {"label": "Примечание", "type": "textarea", "rows": 2, "default": "Бонусы начисляются автоматически в личном кабинете после оплаты минимальной суммы в 150 ₽ рефералом."},
        },
        "Подвал": {
            "footer_copyright": {"label": "Копирайт", "type": "text", "default": "© 2026 HexaVeil. Защищённый доступ к мировому интернету."},
        },
        "Блог на главной": {
            "blog_preview_enabled": {"label": "Показывать секцию блога на лендинге", "type": "select", "options": {"1": "Да", "0": "Нет"}, "default": "1"},
            "blog_preview_count": {"label": "Количество постов в секции", "type": "number", "default": "3"},
            "blog_preview_title": {"label": "Заголовок секции", "type": "text", "default": "Последние из блога"},
            "blog_preview_desc": {"label": "Описание секции", "type": "textarea", "rows": 2, "default": "Новости, советы и инструкции по настройке VPN — для тех, кто ценит скорость, приватность и свободу в интернете."},
        },
        "Floating-виджет блога": {
            "widget_enabled": {"label": "Показывать плавающий виджет", "type": "select", "options": {"1": "Да", "0": "Нет"}, "default": "1"},
            "widget_title": {"label": "Заголовок виджета", "type": "text", "default": "Последние статьи"},
        },
    },
}

# ── default / modern / minimal — no custom options ────────────────
_EMPTY: Dict[str, Any] = {"name": "", "options": {}}

_THEMES: Dict[str, Dict[str, Any]] = {
    "hexaveil": _HEXAVEIL,
}


def get_theme_config(theme: str) -> Dict[str, Any]:
    """Return theme config.

    Prefers parsing templates/themes/<theme>/theme.php (single source of
    truth); falls back to the static mirror below if the file is missing or
    cannot be parsed.
    """
    from web.backend.core.config import get_cms_settings
    from web.backend.core.theme_php import load_theme_options

    parsed = load_theme_options(get_cms_settings().root_path, theme)
    if parsed is not None:
        return parsed

    cfg = _THEMES.get(theme)
    if cfg is None:
        return {"name": theme, "options": {}}
    return {"name": cfg.get("name", theme), "options": cfg.get("options", {})}
