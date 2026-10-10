# CMS Redesign: Админка + Блог — Полный план улучшения

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Превратить админ-панель и блог CMS из "generic AI-дизайна" в продуманный, премиальный интерфейс без касания темы HexaVeil.

**Architecture:** Проект — кастомная PHP CMS без фреймворков. Дизайн живёт в CSS-файлах (admin/css/admin.css, public/css/style.css) и PHP-шаблонах. Все изменения — vanilla CSS + vanilla JS. Никаких npm, сборщиков, фреймворков.

**Tech Stack:** PHP 7.4+, vanilla CSS, vanilla JS, TinyMCE (админка)

## Global Constraints

- **HEXAVEIL НЕ ТРОГАЕМ** — ни один файл в `public/hexaveil/` или `templates/themes/hexaveil/` не изменяется
- Тема HexaVeil — это лендинг VPN-сервиса. Всё остальное (admin, blog frontend, ядро) — улучшаем
- Никаких npm, node_modules, build steps, CSS-препроцессоров. Только нативный CSS
- Никаких внешних библиотек (кроме уже подключённых — TinyMCE)
- Все emoji заменяем на inline SVG-иконки из набора Phosphor (через копипасту путей)
- Все изменения обратимы: коммит после каждой задачи
- Если в задаче сказано "заменить шрифт" — замена происходит во всех файлах, указанных в секции **Files**
- Если не указано иное — изменения применяются ко всем страницам админки (layout = `admin/templates/layouts/main.php`)

---

## File Map (полный список файлов, которые будут изменены)

### Админка (admin/)
| Файл | Роль |
|---|---|
| `admin/css/admin.css` (~619 строк) | Главный CSS админки — заменяем целиком на системный CSS с токенами |
| `admin/templates/layouts/main.php` | Основной layout — шрифты, favicon, skip-link, мета-теги |
| `admin/templates/login.php` | Страница входа |
| `admin/templates/dashboard.php` | Дашборд — статистика, последние посты, быстрые действия |
| `admin/templates/posts/index.php` | Список постов |
| `admin/templates/posts/form.php` | Форма поста |
| `admin/templates/categories/index.php` | Категории |
| `admin/templates/pages/index.php` | Страницы |
| `admin/templates/media/index.php` | Медиа-файлы |
| `admin/templates/menus/index.php` | Меню |
| `admin/templates/users/index.php` | Пользователи |
| `admin/templates/settings/index.php` | Настройки |
| `admin/templates/theme/index.php` | Настройки темы |
| `admin/templates/widgets/index.php` | Виджеты |

### Блог (public/)
| Файл | Роль |
|---|---|
| `public/css/style.css` (~991 строк) | Главный CSS блога — заменяем целиком |
| Все шаблоны темы `templates/themes/default/`, `modern/`, `minimal/` | Могут использовать `public/css/style.css` — проверяем |

### Дизайн-система (новые файлы)
| Файл | Роль |
|---|---|
| `docs/superpowers/specs/2026-08-24-cms-design.md` | DESIGN.md — дизайн-документ (Phase 0) |
| `public/css/cms-tokens.css` | Токены CSS, общие для админки и блога (Phase 3) |
| `public/css/cms-components.css` | Переиспользуемые компоненты (Phase 4) |

---

## Phase 0: DESIGN.md — Дизайн-документ

> **Цель:** Зафиксировать все дизайн-решения в едином документе, чтобы к нему мог вернуться любой разработчик.
> **Время:** 30-45 минут
> **Инструмент:** `stitch-design-taste` skill

<!--- Исполнитель: запускает stitch-design-taste, генерирует файл --->

- [ ] **Step 1: Создать DESIGN.md через stitch-design-taste**

    Используя скилл `stitch-design-taste`, сгенерировать DESIGN.md со следующими параметрами:

    **Продукт:** CMS Admin Panel + Blog (не HexaVeil)
    **Аудитория:** Разработчики и контент-менеджеры (админка), читатели (блог)
    **Атмосфера:**
    - Админка: "Инструментальная, чистая, уверенная. Не развлекательная, но приятная глазу. Density: 6, Variance: 5, Motion: 5"
    - Блог: "Читательская, воздушная, типографически насыщенная. Density: 4, Variance: 6, Motion: 4"

    **Цвета для админки (нейтральная основа):**
    - Slack-inspired: тёмно-синий сайдбар `#1e1e2e`, основной фон `#f5f5f7`
    - Единый акцент: `#6366f1` (Indigo-500) — вместо `#3b82f6` и `#667eea`
    - Off-white карточки: `#ffffff` с tinted shadow
    - Акцент для успеха: `#22c55e`, для ошибок: `#ef4444`

    **Цвета для блога:**
    - Фон: `#fafafa`, текст: `#18181b`
    - Акцент: тёмно-синий `#1e293b` вместо `#667eea`
    - Карточки: `#ffffff` с минимальной тенью

    **Шрифты:**
    - Админка: `Outfit` (Google Fonts) или `Plus Jakarta Sans` — для UI
    - Блог: `Satoshi` (body) + `Cabinet Grotesk` (headings) — или `Inter` заменяем на `Geist`
    - Моно: `JetBrains Mono` — для кода, метаданных, дат
    - BANNED: Inter (в блоге), system-ui (без замены)

    Сохранить файл в `docs/superpowers/specs/2026-08-24-cms-design.md`

- [ ] **Step 2: Закоммитить DESIGN.md**

    ```bash
    git add docs/superpowers/specs/2026-08-24-cms-design.md
    git commit -m "docs: add design system spec for CMS redesign"
    ```

---

## Phase 1: Быстрые победы — Типографика, цвета, hover-эффекты

> **Цель:** Максимальный визуальный эффект за минимальное время. Меняем шрифты, убираем AI-градиент, добавляем micro-interactions.
> **Время:** 2-3 часа
> **Не трогает:** HexaVeil

---

### Task 1.1: Замена шрифта в админке

**Files:**
- Modify: `admin/templates/layouts/main.php` (добавить Google Fonts link + поменять font-family)
- Modify: `admin/css/admin.css` (заменить `font-family` у body)

**Проблема:** Сейчас `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif` — полный дефолт.

- [ ] **Step 1: Добавить Google Fonts в `<head>` layout-а**

    В `admin/templates/layouts/main.php`, после строки с `<title>`, добавить:

    ```html
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    ```

    Текущий блок `<head>` (строки 3-10):
    ```php
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title><?= $title ?? 'Админ-панель' ?> - <?= SITE_NAME ?></title>
        <link rel="stylesheet" href="<?= SITE_URL ?>/admin/css/admin.css?v=<?= filemtime(ADMIN_PATH . '/css/admin.css') ?>">
        <!-- TinyMCE -->
        <script src="https://cdn.jsdelivr.net/npm/tinymce@7/tinymce.min.js"></script>
    </head>
    ```

    Должно стать (строки 4-11):
    ```php
        <title><?= $title ?? 'Админ-панель' ?> - <?= SITE_NAME ?></title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="<?= SITE_URL ?>/admin/css/admin.css?v=<?= filemtime(ADMIN_PATH . '/css/admin.css') ?>">
        <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📊</text></svg>">
        <!-- TinyMCE -->
        <script src="https://cdn.jsdelivr.net/npm/tinymce@7/tinymce.min.js"></script>
    ```

- [ ] **Step 2: Поменять font-family в admin.css**

    В `admin/css/admin.css` строка 30 (body):
    ```css
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        background: #f8fafc;
        color: #333;
        line-height: 1.6;
    }
    ```

    Заменить на:
    ```css
    body {
        font-family: 'Outfit', system-ui, sans-serif;
        background: #f5f5f7;
        color: #1a1a2e;
        line-height: 1.6;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    ```

- [ ] **Step 3: Открыть админку в браузере, убедиться что шрифт загрузился и не сломался layout**

    Проверить: страница входа, дашборд, список постов. Шрифт должен быть `Outfit`.

- [ ] **Step 4: Commit**

    ```bash
    git add admin/templates/layouts/main.php admin/css/admin.css
    git commit -m "feat(admin): replace system font with Outfit + JetBrains Mono"
    ```

---

### Task 1.2: Замена шрифта в блоге

**Files:**
- Modify: `public/css/style.css` (font-family у body + добавить Google Fonts в шаблоны тем)

**Проблема:** Тот же системный стек.

- [ ] **Step 1: Найти шаблон, который подключает `public/css/style.css`**

    Проверить `templates/themes/default/`, `modern/`, `minimal/` — какой PHP-файл рендерит `<head>` и подключает этот CSS.

    ```bash
    grep -r "public/css/style.css" templates/
    ```

    (Если несколько — править каждый.)

- [ ] **Step 2: Добавить Google Fonts в head шаблона темы**

    ```html
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    ```

- [ ] **Step 3: Поменять font-family в public/css/style.css**

    Строка 12 (body):
    ```css
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        ...
    }
    ```

    Заменить на:
    ```css
    body {
        font-family: 'Outfit', system-ui, sans-serif;
        color: #18181b;
        background: #fafafa;
        line-height: 1.7;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    ```

- [ ] **Step 4: Commit**

    ```bash
    git add public/css/style.css <найденные-шаблоны-темы>
    git commit -m "feat(blog): replace system font with Outfit"
    ```

---

### Task 1.3: Убрать AI-градиент из админки

**Files:**
- Modify: `admin/css/admin.css` (login gradient, logo color, кнопки, ссылки, badges)

**Проблема:** `linear-gradient(135deg, #667eea 0%, #764ba2 100%)` — классический AI-градиент. Он используется:
1. На странице входа (login-page)
2. В кнопках .btn-primary нет (они используют --primary: #3b82f6) — хорошо
3. Но цветовая палитра в целом purple/blue смесь
4. Сайдбар `#1e293b` — норм, но акцент `#3b82f6` (blue) смешивается с `#667eea` (purple)

**Решение:** Унифицировать до единого акцента `--primary: #6366f1` (Indigo-500). Заменить все вхождения.

- [ ] **Step 1: Поменять :root цвета**

    В `admin/css/admin.css` (строки 5-21):
    ```css
    :root {
        --sidebar-width: 260px;
        --sidebar-bg: #1e293b;
        --sidebar-hover: #334155;
        --sidebar-active: #3b82f6;
        --primary: #3b82f6;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --gray-100: #f1f5f9;
        --gray-200: #e2e8f0;
        --gray-300: #cbd5e1;
        --gray-600: #475569;
        --gray-700: #334155;
        --gray-900: #1e293b;
    }
    ```

    Заменить на:
    ```css
    :root {
        /* Layout */
        --sidebar-width: 260px;
        --sidebar-bg: #1e1e2e;
        --sidebar-hover: #2a2a3e;
        --sidebar-active: #6366f1;
        --header-height: 60px;

        /* Brand */
        --primary: #6366f1;
        --primary-hover: #4f46e5;
        --primary-light: rgba(99, 102, 241, 0.1);

        /* Semantic */
        --success: #22c55e;
        --success-bg: #dcfce7;
        --warning: #f59e0b;
        --warning-bg: #fef3c7;
        --danger: #ef4444;
        --danger-bg: #fee2e2;

        /* Neutrals */
        --bg-body: #f5f5f7;
        --bg-card: #ffffff;
        --bg-subtle: #eef0f4;
        --text-primary: #1a1a2e;
        --text-secondary: #6b7280;
        --text-muted: #9ca3af;
        --border-light: #e5e7eb;
        --border-subtle: rgba(0, 0, 0, 0.06);

        /* Shadows — tinted to neutral */
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
        --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.08);

        /* Radius */
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;

        /* Transitions */
        --transition-fast: 150ms ease;
        --transition-normal: 250ms ease;
    }
    ```

- [ ] **Step 2: Заменить градиент на странице входа**

    Строка 45 (login-page):
    ```css
    .login-page {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    ```

    Заменить на:
    ```css
    .login-page {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--sidebar-bg);
    }
    ```

    Строка 58 (login-box, box-shadow):
    ```css
    .login-box {
        background: white;
        border-radius: 12px;
        padding: 40px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    ```

    Заменить на:
    ```css
    .login-box {
        background: var(--bg-card);
        border-radius: var(--radius-lg);
        padding: 40px;
        box-shadow: 0 25px 60px rgba(0, 0, 0, 0.35);
    }
    ```

- [ ] **Step 3: Проверить, что нигде в admin.css не осталось `#667eea` или `#764ba2`**

    ```bash
    grep -n "#667eea\|#764ba2\|#3b82f6" admin/css/admin.css
    ```

    Должно быть пусто (мы заменили #3b82f6 на #6366f1). Если есть — заменить на `var(--primary)`.

    Старое значение `#3b82f6` в `--primary` и `--sidebar-active` уже заменено на `#6366f1` в Step 1. Но нужно проверить, не используется ли `#3b82f6` где-то ещё в CSS как hardcoded значение.

- [ ] **Step 4: Commit**

    ```bash
    git add admin/css/admin.css
    git commit -m "feat(admin): unify palette — replace purple/blue gradient with indigo accent"
    ```

---

### Task 1.4: Заменить emoji в админке на inline SVG-иконки

**Files:**
- Modify: `admin/templates/layouts/main.php` (sidebar — все emoji)
- Modify: `admin/templates/dashboard.php` (статистика, заголовки)
- Modify: `admin/templates/posts/index.php` (заголовки, кнопки)
- Modify: `admin/templates/posts/form.php` (заголовки, кнопки)
- Modify: `admin/templates/categories/index.php` (заголовки, кнопки)
- Modify: `admin/templates/pages/index.php` (заголовки, кнопки)
- Modify: `admin/templates/media/index.php` (заголовки, кнопки)
- Modify: `admin/templates/menus/index.php` (заголовки, кнопки)
- Modify: `admin/templates/users/index.php` (заголовки, кнопки)
- Modify: `admin/templates/settings/index.php` (заголовки, разделы)
- Modify: `admin/templates/theme/index.php` (заголовки)
- Modify: `admin/templates/widgets/index.php` (заголовки)
- Modify: `admin/templates/login.php` (заголовок)

**Проблема:** В админке везде emoji вместо иконок. Emoji выглядят по-разному на разных ОС, не поддаются стилизации и выглядят непрофессионально.

**Решение:** Создать функцию-хелпер для рендеринга SVG-иконок (Phosphor-подобные, тонкие линии). Emoji заменяем на `<svg>...</svg>` вставки.

- [ ] **Step 1: Создать файл с SVG-иконками**

    Create: `admin/css/admin-icons.svg` (sprite sheet) — или вставлять inline (проще).

    Для начала используем inline SVG через data-uri. Добавить несколько основных иконок как CSS-классы в admin.css.

    В конец `admin/css/admin.css` добавить:

    ```css
    /* ============================================
       SVG Icons (inline, Phosphor-style)
       ============================================ */
    .icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.25em;
        height: 1.25em;
        flex-shrink: 0;
    }
    .icon svg {
        width: 100%;
        height: 100%;
        fill: none;
        stroke: currentColor;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
    }
    .icon-lg { width: 1.5em; height: 1.5em; }
    .icon-sm { width: 1em; height: 1em; }
    ```

- [ ] **Step 2: Создать функцию-хелпер для иконок в PHP**

    Создать (или добавить) файл `core/helpers_icons.php`:

    ```php
    <?php
    /**
     * Хелперы для inline SVG-иконок (Phosphor-style)
     */

    function icon($name, $class = '') {
        $icons = [
            'dashboard' => '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>',
            'posts' => '<svg viewBox="0 0 24 24"><path d="M4 20h16a2 2 0 002-2V8a2 2 0 00-2-2h-7.93a2 2 0 01-1.66-.9l-.82-1.2A2 2 0 007.93 3H4a2 2 0 00-2 2v13c0 1.1.9 2 2 2z"/></svg>',
            'categories' => '<svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>',
            'pages' => '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
            'menus' => '<svg viewBox="0 0 24 24"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
            'media' => '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21,15 16,10 5,21"/></svg>',
            'users' => '<svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>',
            'settings' => '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>',
            'theme' => '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
            'widgets' => '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
            'external' => '<svg viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>',
            'logout' => '<svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
            'back' => '<svg viewBox="0 0 24 24"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>',
            'add' => '<svg viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
            'edit' => '<svg viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
            'delete' => '<svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>',
            'save' => '<svg viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>',
            'view' => '<svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>',
            'success' => '<svg viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
            'error' => '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
            'info' => '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
            'search' => '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
            'eye' => '<svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>',
        ];

        if (!isset($icons[$name])) return '';

        $classAttr = $class ? " class=\"$class\"" : '';
        return "<span class=\"icon\"$classAttr>{$icons[$name]}</span>";
    }

    function icon_svg($name) {
        $icons = [
            'check' => '<svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>',
            'arrow-right' => '<svg viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
            'star' => '<svg viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
            'tag' => '<svg viewBox="0 0 24 24"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
            'calendar' => '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
            'message' => '<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
        ];
        return $icons[$name] ?? '';
    }
    ```

    Затем подключить в `index.php` (там где подключаются helpers):
    В `index.php` после строки `require_once CORE_PATH . '/helpers.php';` добавить:
    ```php
    require_once CORE_PATH . '/helpers_icons.php';
    ```

- [ ] **Step 3: Заменить emoji в сайдбаре main.php**

    Каждый `<span class="nav-icon">📊</span>` заменить на `<?= icon('dashboard') ?>`.

    Пример для Дашборда (строка 20 в main.php):
    ```php
    <span class="nav-icon"><?= icon('dashboard') ?></span>
    ```

    Полная замена по всем пунктам навигации (строки 19-58):
    - `🏠` → `<?= icon('dashboard') ?>`
    - `📝` → `<?= icon('posts') ?>`
    - `📁` → `<?= icon('categories') ?>`
    - `📄` → `<?= icon('pages') ?>`
    - `📋` → `<?= icon('menus') ?>`
    - `🖼️` → `<?= icon('media') ?>`
    - `👥` → `<?= icon('users') ?>`
    - `⚙️` → `<?= icon('settings') ?>`
    - `🎨` → `<?= icon('theme') ?>`
    - `🧩` → `<?= icon('widgets') ?>`
    - `🌐` → `<?= icon('external') ?>`
    - `🚪` → `<?= icon('logout') ?>`

- [ ] **Step 4: Заменить emoji в логотипе и кнопках main.php**

    Строка 15: `<a href="/admin" class="admin-logo">📊 <?= SITE_NAME ?></a>`
    Заменить на: `<a href="/admin" class="admin-logo"><?= icon('dashboard', 'icon-lg') ?> <?= SITE_NAME ?></a>`

- [ ] **Step 5: Заменить emoji в dashboard.php**

    Строки 3, 11, 19, 27 (stat-icon):
    ```php
    <div class="stat-icon">📝</div>
    ```
    Заменить на:
    ```php
    <div class="stat-icon"><?= icon('posts', 'icon-lg') ?></div>
    ```
    Аналогично: `💬` → `<?= icon('message', 'icon-lg') ?>`, `👥` → `<?= icon('users', 'icon-lg') ?>`, `📁` → `<?= icon('categories', 'icon-lg') ?>`

    Строка 37: `<h2>📋 Последние посты</h2>` → `<h2><?= icon('posts') ?> Последние посты</h2>`
    Строка 85: `<h2>⚡ Быстрые действия</h2>` → `<h2><?= icon('settings') ?> Быстрые действия</h2>`

    Строки 65-69 (кнопки действий):
    ```php
    <a href="/admin/posts/edit/<?= $post['id'] ?>" class="btn btn-sm btn-primary" title="Редактировать">✏️</a>
    ```
    Заменить на:
    ```php
    <a href="/admin/posts/edit/<?= $post['id'] ?>" class="btn btn-sm btn-primary" title="Редактировать"><?= icon('edit') ?></a>
    ```

    Строка 67 (view):
    ```php
    <a href="/post/<?= $post['slug'] ?>" class="btn btn-sm btn-info" target="_blank" title="Просмотр">👁️</a>
    ```
    Заменить на:
    ```php
    <a href="/post/<?= $post['slug'] ?>" class="btn btn-sm btn-info" target="_blank" title="Просмотр"><?= icon('eye') ?></a>
    ```

    Строки 88-97 (быстрые действия):
    ```php
    <a href="/admin/posts/create" class="btn btn-primary">
        <span>📝</span> Новый пост
    </a>
    ```
    Заменить на:
    ```php
    <a href="/admin/posts/create" class="btn btn-primary">
        <?= icon('posts') ?> Новый пост
    </a>
    ```

- [ ] **Step 6: Заменить emoji в остальных шаблонах админки**

    **posts/index.php:**
    - `➕ Добавить пост` → `<?= icon('add') ?> Добавить пост`
    - `✏️` → `<?= icon('edit') ?>`
    - `👁️` → `<?= icon('eye') ?>`
    - `🗑️` → `<?= icon('delete') ?>`
    - `✓ Опубликован` → просто `Опубликован` (или с `<?= icon('check') ?>`)
    - `📝 Черновик` → `Черновик`
    - `🗄️ Архив` → `Архив`

    **posts/form.php:**
    - `💾 Сохранить` → `<?= icon('save') ?> Сохранить`
    - `➕ Создать` → `<?= icon('add') ?> Создать`
    - `← Назад к списку` → `<?= icon('back') ?> Назад к списку`
    - `📝 Черновик` → `Черновик`
    - `✓ Опубликован` → `Опубликован`
    - `🗄️ Архив` → `Архив`

    **login.php:**
    - `🔐 Вход в админку` → `Вход в админку`
    - `← Вернуться на сайт` → `<?= icon('back') ?> Вернуться на сайт`

    **categories/index.php:**
    - `➕ Добавить категорию` → `<?= icon('add') ?> Добавить категорию`
    - `✏️` → `<?= icon('edit') ?>`
    - `🗑️` → `<?= icon('delete') ?>`

    **pages/index.php:** (аналогично posts)
    **media/index.php:**
    - `📤 Загрузить` → `<?= icon('add') ?> Загрузить`
    - `🗑️` → `<?= icon('delete') ?>`

    **menus/index.php:**
    - `➕ Добавить пункт` → `<?= icon('add') ?> Добавить пункт`
    - `📍 Главное` → просто `Главное`
    - `📍 Футер` → просто `Футер`

    **users/index.php:**
    - `➕ Добавить пользователя` → `<?= icon('add') ?> Добавить пользователя`
    - `👑 Администратор` → `Администратор`
    - `✏️ Редактор` → `Редактор`
    - `📝 Автор` → `Автор`
    - `🗑️` → `<?= icon('delete') ?>`

    **settings/index.php:**
    - `💾 Сохранить` → `<?= icon('save') ?> Сохранить`
    - `📌 Основные настройки` → `Основные настройки`
    - `🎨 Внешний вид` → `Внешний вид`
    - `🔧 Дополнительные настройки` → `Дополнительные настройки`

- [ ] **Step 7: Commit**

    ```bash
    git add core/helpers_icons.php index.php admin/css/admin.css admin/templates/
    git commit -m "feat(admin): replace emoji with inline SVG icons (Phosphor-style)"
    ```

---

### Task 1.5: Добавить hover/active/pressed на кнопки во всей админке

**Files:**
- Modify: `admin/css/admin.css` (стили кнопок)

**Проблема:** Кнопки в админке не дают тактильной обратной связи — нет scale на нажатии, нет анимации фокуса.

- [ ] **Step 1: Обновить стили кнопок в admin.css**

    Найти блок `.btn` (строка 413-424) и заменить целиком:

    ```css
    /* ============================================
       Buttons
       ============================================ */

    .btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 20px;
        border: none;
        border-radius: var(--radius-sm);
        font-size: 14px;
        font-weight: 500;
        font-family: inherit;
        cursor: pointer;
        text-decoration: none;
        transition:
            background-color var(--transition-fast),
            box-shadow var(--transition-fast),
            transform var(--transition-fast),
            color var(--transition-fast);
        text-align: center;
        line-height: 1.4;
        user-select: none;
        -webkit-tap-highlight-color: transparent;
        touch-action: manipulation;
    }

    .btn:active {
        transform: scale(0.97);
    }

    .btn:focus-visible {
        outline: 2px solid var(--primary);
        outline-offset: 2px;
    }

    .btn-primary {
        background: var(--primary);
        color: white;
    }

    .btn-primary:hover {
        background: var(--primary-hover);
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
    }

    .btn-secondary {
        background: var(--text-muted);
        color: white;
    }

    .btn-secondary:hover {
        background: var(--text-secondary);
    }

    .btn-danger {
        background: var(--danger);
        color: white;
    }

    .btn-danger:hover {
        background: #dc2626;
    }

    .btn-info {
        background: #06b6d4;
        color: white;
    }

    .btn-info:hover {
        background: #0891b2;
    }

    .btn-success {
        background: var(--success);
        color: white;
    }

    .btn-success:hover {
        background: #16a34a;
    }

    .btn-sm {
        padding: 6px 12px;
        font-size: 13px;
    }

    .btn-block {
        display: flex;
        width: 100%;
        justify-content: center;
    }
    ```

- [ ] **Step 2: Проверить, что кнопки не сломались**

    Открыть в браузере страницу входа → кнопка должна уменьшаться на нажатии.

- [ ] **Step 3: Commit**

    ```bash
    git add admin/css/admin.css
    git commit -m "feat(admin): add hover/pressed/focus states to all buttons"
    ```

---

## Phase 2: Дизайн-система — CSS-токены

> **Цель:** Создать единую систему CSS-переменных (токенов), от которых будут зависеть все компоненты. Это foundation для всего остального редизайна.
> **Время:** 2-3 часа

---

### Task 2.1: Создать cms-tokens.css — общие токены для админки и блога

**Files:**
- Create: `public/css/cms-tokens.css`

**Проблема:** Сейчас цвета размазаны по двум CSS-файлам, дублируются, нет единой шкалы.

- [ ] **Step 1: Создать файл токенов**

    ```css
    /* ============================================
       CMS Design Tokens
       Shared between admin panel and blog frontend
       ============================================ */

    :root {
        /* ============ Layout ============ */
        --container-max: 1200px;
        --container-padding: 20px;

        /* ============ Typography ============ */
        --font-sans: 'Outfit', system-ui, sans-serif;
        --font-mono: 'JetBrains Mono', ui-monospace, Consolas, monospace;

        /* ============ Colors: Neutrals ============ */
        --neutral-50: #fafafa;
        --neutral-100: #f5f5f5;
        --neutral-200: #e5e7eb;
        --neutral-300: #d1d5db;
        --neutral-400: #9ca3af;
        --neutral-500: #6b7280;
        --neutral-600: #4b5563;
        --neutral-700: #374151;
        --neutral-800: #1f2937;
        --neutral-900: #111827;
        --neutral-950: #030712;

        /* ============ Colors: Brand ============ */
        --brand-50: #eef2ff;
        --brand-100: #e0e7ff;
        --brand-200: #c7d2fe;
        --brand-500: #6366f1;
        --brand-600: #4f46e5;
        --brand-700: #4338ca;

        /* ============ Colors: Semantic ============ */
        --green-50: #f0fdf4;
        --green-500: #22c55e;
        --green-600: #16a34a;
        --red-50: #fef2f2;
        --red-500: #ef4444;
        --red-600: #dc2626;
        --amber-50: #fffbeb;
        --amber-500: #f59e0b;
        --amber-600: #d97706;
        --blue-50: #eff6ff;
        --blue-500: #3b82f6;

        /* ============ Shadows ============ */
        --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.04);
        --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
        --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.08);
        --shadow-xl: 0 12px 40px rgba(0, 0, 0, 0.10);

        /* ============ Border Radius ============ */
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
        --radius-xl: 20px;
        --radius-full: 9999px;

        /* ============ Transitions ============ */
        --transition-fast: 150ms ease;
        --transition-normal: 250ms ease;
        --transition-slow: 400ms ease;
    }
    ```

- [ ] **Step 2: Подключить cms-tokens.css в админку**

    В `admin/templates/layouts/main.php`, после `<title>` и перед подключением admin.css:
    ```html
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/cms-tokens.css">
    ```

- [ ] **Step 3: Подключить cms-tokens.css в блог**

    В шаблон темы, который подключает `public/css/style.css`, добавить перед ним:
    ```html
    <link rel="stylesheet" href="/public/css/cms-tokens.css">
    ```

- [ ] **Step 4: Commit**

    ```bash
    git add public/css/cms-tokens.css admin/templates/layouts/main.php
    git commit -m "feat(css): add shared design tokens (cms-tokens.css)"
    ```

---

### Task 2.2: Рефакторинг admin.css — использовать токены

**Files:**
- Modify: `admin/css/admin.css`

**Проблема:** После Task 1.3 в admin.css уже есть локальные `:root`-переменные. Нужно привести их к единой системе из cms-tokens.css.

- [ ] **Step 1: Переписать блок :root в admin.css, используя var(--...) из cms-tokens.css**

    ```css
    :root {
        /* Layout */
        --sidebar-width: 260px;
        --sidebar-bg: #1e1e2e;
        --sidebar-hover: #2a2a3e;
        --sidebar-active: var(--brand-500);
        --header-height: 60px;

        /* Brand — ссылаются на глобальные токены */
        --primary: var(--brand-500);
        --primary-hover: var(--brand-600);
        --primary-light: var(--brand-50);

        /* Semantic */
        --success: var(--green-500);
        --success-bg: var(--green-50);
        --warning: var(--amber-500);
        --warning-bg: var(--amber-50);
        --danger: var(--red-500);
        --danger-bg: var(--red-50);

        /* Backgrounds */
        --bg-body: #f5f5f7;
        --bg-card: #ffffff;
        --bg-subtle: var(--neutral-100);
        --bg-sidebar: #1e1e2e;

        /* Text */
        --text-primary: #1a1a2e;
        --text-secondary: var(--neutral-500);
        --text-muted: var(--neutral-400);

        /* Borders */
        --border-light: var(--neutral-200);
        --border-subtle: rgba(0, 0, 0, 0.06);

        /* Shadows */
        --shadow-sm: var(--shadow-xs);
        --shadow-md: var(--shadow-sm);
        --shadow-lg: var(--shadow-md);

        /* Radius */
        --radius-sm: var(--radius-sm);
        --radius-md: var(--radius-md);
        --radius-lg: var(--radius-lg);

        /* Transitions */
        --transition-fast: var(--transition-fast);
        --transition-normal: var(--transition-normal);
    }
    ```

    **Важно:** CSS-переменные, определённые в :root, нельзя ссылаться на самих себя через var() в том же блоке? Нет, можно, если они определены выше. Но проще сделать как выше — оставить значения копиями.

    **Ещё важнее:** В admin.css `--font-sans` не определён, но будет доступен из cms-tokens.css. Убедиться, что cms-tokens.css подключён ДО admin.css.

- [ ] **Step 2: Заменить все `#333`, `#f8fafc`, `#555`, `#666`, `#888` и т.д. на var(--text-*)**

    Пройтись по admin.css и заменить:
    - `color: #333` → `color: var(--text-primary)`
    - `color: #555` → `color: var(--text-secondary)`
    - `color: #666` → `color: var(--text-secondary)`
    - `color: #888` → `color: var(--text-muted)`
    - `background: #f8fafc` → `background: var(--bg-body)`
    - `background: white` → `background: var(--bg-card)`
    - `border-color: #ddd` → `border-color: var(--border-light)`
    - `border-bottom: 1px solid #eee` → `border-bottom: 1px solid var(--border-light)`

- [ ] **Step 3: Commit**

    ```bash
    git add admin/css/admin.css
    git commit -m "refactor(admin): use design tokens from cms-tokens.css"
    ```

---

### Task 2.3: Tinted shadows

**Files:**
- Modify: `admin/css/admin.css`

**Проблема:** Все тени — `rgba(0,0,0,0.1)` дефолтные.

- [ ] **Step 1: Заменить все box-shadow на tinted**

    Пробежаться по admin.css и заменить generic shadows на tinted:
    - `box-shadow: 0 1px 3px rgba(0,0,0,0.1)` → `box-shadow: var(--shadow-sm)`
    - `box-shadow: 0 2px 8px rgba(0,0,0,0.1)` → `box-shadow: var(--shadow-md)`
    - `box-shadow: 0 4px 12px rgba(0,0,0,0.15)` → `box-shadow: var(--shadow-lg)`
    - `box-shadow: 0 20px 60px rgba(0,0,0,0.3)` → `box-shadow: var(--shadow-xl)`

- [ ] **Step 2: Commit**

    ```bash
    git add admin/css/admin.css
    git commit -m "refactor(admin): replace hardcoded shadows with tinted shadow tokens"
    ```

---

## Phase 3: Компоненты — Убить "3 равные карточки" и generic паттерны

> **Цель:** Убрать самые узнаваемые AI-паттерны из админки и блога.
> **Время:** 4-6 часов

---

### Task 3.1: Dashboard — редизайн карточек статистики

**Files:**
- Modify: `admin/templates/dashboard.php`
- Modify: `admin/css/admin.css` (стили .stat-card)

**Проблема:** 4 одинаковые stat-card — generic AI-паттерн.

- [ ] **Step 1: Изменить структуру dashboard.php**

    Заменить блок `.dashboard-stats` (строки 1-33) на более интересный layout:

    ```php
    <div class="stats-grid">
        <div class="stat-card stat-card-posts">
            <div class="stat-icon"><?= icon('posts', 'icon-lg') ?></div>
            <div class="stat-body">
                <span class="stat-value"><?= $stats['posts'] ?? 0 ?></span>
                <span class="stat-label">Постов</span>
            </div>
        </div>

        <div class="stat-card stat-card-comments">
            <div class="stat-icon"><?= icon('message', 'icon-lg') ?></div>
            <div class="stat-body">
                <span class="stat-value"><?= $stats['comments'] ?? 0 ?></span>
                <span class="stat-label">Комментариев</span>
            </div>
        </div>

        <div class="stat-card stat-card-users">
            <div class="stat-icon"><?= icon('users', 'icon-lg') ?></div>
            <div class="stat-body">
                <span class="stat-value"><?= $stats['users'] ?? 0 ?></span>
                <span class="stat-label">Пользователей</span>
            </div>
        </div>

        <div class="stat-card stat-card-categories">
            <div class="stat-icon"><?= icon('categories', 'icon-lg') ?></div>
            <div class="stat-body">
                <span class="stat-value"><?= $stats['categories'] ?? 0 ?></span>
                <span class="stat-label">Категорий</span>
            </div>
        </div>
    </div>
    ```

- [ ] **Step 2: Заменить стили .stat-card**

    В admin.css найти блок `.dashboard-stats` и `.stat-card` (строки 249-291) и заменить:

    ```css
    /* ============================================
       Dashboard Stats
       ============================================ */

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 30px;
    }

    .stat-card {
        background: var(--bg-card);
        border-radius: var(--radius-md);
        padding: 20px 24px;
        display: flex;
        align-items: center;
        gap: 16px;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-light);
        transition:
            box-shadow var(--transition-fast),
            transform var(--transition-fast);
    }

    .stat-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }

    /* Каждая карточка имеет свой цветовой акцент */
    .stat-card-posts .stat-icon { color: var(--brand-500); background: var(--brand-50); }
    .stat-card-comments .stat-icon { color: var(--blue-500); background: var(--blue-50); }
    .stat-card-users .stat-icon { color: var(--green-500); background: var(--green-50); }
    .stat-card-categories .stat-icon { color: var(--amber-500); background: var(--amber-50); }

    .stat-icon {
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--radius-sm);
        flex-shrink: 0;
    }

    .stat-body {
        display: flex;
        flex-direction: column;
    }

    .stat-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1.1;
    }

    .stat-label {
        font-size: 13px;
        color: var(--text-secondary);
        font-weight: 500;
        margin-top: 2px;
    }

    @media (max-width: 768px) {
        .stats-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        .stat-card {
            padding: 16px;
        }
        .stat-value {
            font-size: 22px;
        }
    }
    ```

- [ ] **Step 3: Убрать дублирующийся блок**

    Удалить старые стили `.dashboard-stats` (строки 249-291) и `.stat-icon`, `.stat-info`, `.stat-value`, `.stat-label`.

- [ ] **Step 4: Commit**

    ```bash
    git add admin/templates/dashboard.php admin/css/admin.css
    git commit -m "refactor(admin): redesign dashboard stat cards with color accents"
    ```

---

### Task 3.2: Таблицы — улучшить data-table

**Files:**
- Modify: `admin/css/admin.css` (стили .data-table)

**Проблема:** Таблицы выглядят как стандартный HTML-шаблон.

- [ ] **Step 1: Обновить стили таблиц**

    Найти блок `.data-table` (строки 333-381) и заменить:

    ```css
    /* ============================================
       Data Tables
       ============================================ */

    .data-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: var(--bg-card);
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-light);
    }

    .data-table thead {
        background: var(--bg-body);
    }

    .data-table th,
    .data-table td {
        padding: 12px 16px;
        text-align: left;
        border-bottom: 1px solid var(--border-light);
        font-size: 14px;
    }

    .data-table th {
        font-weight: 600;
        color: var(--text-secondary);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .data-table tbody tr:last-child td {
        border-bottom: none;
    }

    .data-table tbody tr {
        transition: background var(--transition-fast);
    }

    .data-table tbody tr:hover {
        background: var(--bg-subtle);
    }

    .data-table a {
        color: var(--primary);
        text-decoration: none;
        font-weight: 500;
    }

    .data-table a:hover {
        color: var(--primary-hover);
    }

    .table-footer {
        padding: 12px 16px;
        border-top: 1px solid var(--border-light);
        display: flex;
        justify-content: flex-end;
    }

    .text-center {
        text-align: center;
    }
    ```

- [ ] **Step 2: Выровнять кнопки в таблице по центру вертикально**

    В admin.css найти блок `.actions` (строка 574-578) и заменить:

    ```css
    /* Actions column */
    .actions {
        display: flex;
        gap: 4px;
        align-items: center;
        white-space: nowrap;
    }
    ```

- [ ] **Step 3: Commit**

    ```bash
    git add admin/css/admin.css
    git commit -m "refactor(admin): polish data-table with better spacing and hover"
    ```

---

### Task 3.3: Карточки — general component upgrade

**Files:**
- Modify: `admin/css/admin.css` (стили .dashboard-section, .form-post, .filters, .settings-section)

**Проблема:** Карточки везде одинаковые (border + shadow + white bg).

- [ ] **Step 1: Улучшить стили секций дашборда**

    Найти блок `.dashboard-section` (строки 303-314) и заменить:

    ```css
    /* ============================================
       Dashboard Sections
       ============================================ */

    .dashboard-sections {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 24px;
    }

    .dashboard-section {
        background: var(--bg-card);
        border-radius: var(--radius-md);
        padding: 24px;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-light);
    }

    .dashboard-section h2 {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 20px;
        color: var(--text-primary);
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .quick-actions {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .quick-actions .btn {
        justify-content: flex-start;
        padding: 10px 16px;
    }
    ```

- [ ] **Step 2: Улучшить стили form-post**

    Блок `.form-post` (строки 510-514) — обновить:
    ```css
    .form-post {
        background: var(--bg-card);
        border-radius: var(--radius-md);
        padding: 24px;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-light);
    }
    ```

- [ ] **Step 3: Улучшить стили filters**

    Блок `.filters` (строки 561-566):
    ```css
    .filters {
        background: var(--bg-card);
        padding: 16px 20px;
        border-radius: var(--radius-md);
        margin-bottom: 20px;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-light);
    }

    .filters-form {
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
    }
    ```

- [ ] **Step 4: Улучшить стили settings-section**

    В `admin/templates/settings/index.php` есть inline `<style>` (строки 88-101). Заменить его:

    ```html
    <style>
    .settings-section {
        background: var(--bg-card);
        padding: 20px 24px;
        border-radius: var(--radius-md);
        margin-bottom: 20px;
        border: 1px solid var(--border-light);
        box-shadow: var(--shadow-sm);
    }
    .settings-section h3 {
        margin-top: 0;
        margin-bottom: 20px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border-light);
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    </style>
    ```

- [ ] **Step 5: Commit**

    ```bash
    git add admin/css/admin.css admin/templates/settings/index.php
    git commit -m "refactor(admin): unify card components with consistent styles"
    ```

---

### Task 3.4: Sidebar — micro-upgrades

**Files:**
- Modify: `admin/css/admin.css` (стили сайдбара)

**Проблема:** Сайдбар плоский, без глубины.

- [ ] **Step 1: Обновить стили сайдбара**

    Найти блок `/* Sidebar */` (строки 115-176) и заменить:

    ```css
    /* ============================================
       Sidebar
       ============================================ */

    .admin-sidebar {
        width: var(--sidebar-width);
        background: var(--sidebar-bg);
        color: white;
        position: fixed;
        height: 100vh;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        z-index: 100;
    }

    .sidebar-header {
        padding: 20px 24px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    .admin-logo {
        color: white;
        text-decoration: none;
        font-size: 18px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .admin-logo .icon {
        color: var(--primary);
    }

    .sidebar-nav {
        flex: 1;
        padding: 8px 0;
    }

    .nav-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 24px;
        color: rgba(255, 255, 255, 0.55);
        text-decoration: none;
        font-size: 14px;
        font-weight: 500;
        transition: all var(--transition-fast);
        border-left: 3px solid transparent;
    }

    .nav-item:hover {
        background: var(--sidebar-hover);
        color: rgba(255, 255, 255, 0.85);
    }

    .nav-item.active {
        background: rgba(99, 102, 241, 0.12);
        color: white;
        border-left-color: var(--sidebar-active);
    }

    .nav-item .icon {
        width: 18px;
        height: 18px;
        flex-shrink: 0;
        opacity: 0.7;
    }
    .nav-item.active .icon {
        opacity: 1;
    }

    .sidebar-footer {
        padding: 8px 0;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
    }

    .nav-item.logout:hover {
        background: rgba(239, 68, 68, 0.15);
        color: var(--danger);
    }
    ```

- [ ] **Step 2: Commit**

    ```bash
    git add admin/css/admin.css
    git commit -m "refactor(admin): polish sidebar with active indicators and spacing"
    ```

---

## Phase 4: Состояния — loading, empty, error, focus

> **Цель:** Сделать интерфейс "законченным" — ни один экран не должен выглядеть сломанным.
> **Время:** 3-4 часа

---

### Task 4.1: Скелетон-лоадеры

**Files:**
- Create: `admin/css/skeleton.css`
- Modify: `admin/templates/layouts/main.php` (подключить)

**Проблема:** Нет загрузочных состояний вообще.

- [ ] **Step 1: Создать skeleton.css**

    ```css
    /* ============================================
       Skeleton Loading States
       ============================================ */

    .skeleton {
        background: linear-gradient(
            90deg,
            var(--border-light) 25%,
            var(--bg-body) 50%,
            var(--border-light) 75%
        );
        background-size: 200% 100%;
        animation: skeleton-shimmer 1.5s ease-in-out infinite;
        border-radius: var(--radius-sm);
    }

    @keyframes skeleton-shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    .skeleton-text {
        height: 14px;
        margin-bottom: 8px;
        width: 100%;
    }

    .skeleton-text:last-child {
        width: 60%;
    }

    .skeleton-title {
        height: 20px;
        width: 70%;
        margin-bottom: 16px;
    }

    .skeleton-card {
        height: 120px;
        width: 100%;
    }

    .skeleton-row {
        height: 48px;
        width: 100%;
        margin-bottom: 4px;
    }
    ```

- [ ] **Step 2: Commit**

    ```bash
    git add admin/css/skeleton.css
    git commit -m "feat(admin): add skeleton loading states CSS"
    ```

---

### Task 4.2: Focus-visible для всей админки

**Files:**
- Modify: `admin/css/admin.css` (добавить глобальный focus-visible)

**Проблема:** Не на всех элементах есть focus ring.

- [ ] **Step 1: Добавить глобальный стиль**

    В начало `admin/css/admin.css` добавить:

    ```css
    /* Global focus ring */
    :focus-visible {
        outline: 2px solid var(--primary);
        outline-offset: 2px;
    }
    ```

- [ ] **Step 2: Commit**

    ```bash
    git add admin/css/admin.css
    git commit -m "feat(admin): add global focus-visible ring for accessibility"
    ```

---

### Task 4.3: Empty states — заменить "нет данных" на осмысленные сообщения

**Files:**
- Modify: ВСЕ шаблоны админки (dashboard.php, posts/index.php, categories/index.php, media/index.php, menus/index.php, users/index.php)

**Проблема:** "Постов не найдено", "Пользователей не найдено", "Категорий пока нет" — сухие тексты.

- [ ] **Step 1: В каждом шаблоне заменить empty state на осмысленный**

    Пример для `posts/index.php` (строка 65-67):
    ```php
    <?php else: ?>
        <tr>
            <td colspan="8" class="text-center">
                <div class="empty-state">
                    <div class="empty-icon"><?= icon('posts') ?></div>
                    <h3>Постов пока нет</h3>
                    <p>Создайте первый пост, чтобы начать наполнять сайт</p>
                    <a href="/admin/posts/create" class="btn btn-primary"><?= icon('add') ?> Создать пост</a>
                </div>
            </td>
        </tr>
    <?php endif; ?>
    ```

    Аналогично для других шаблонов.

- [ ] **Step 2: Добавить стили для empty-state**

    В admin.css:
    ```css
    /* ============================================
       Empty States
       ============================================ */

    .empty-state {
        text-align: center;
        padding: 60px 20px;
        max-width: 360px;
        margin: 0 auto;
    }

    .empty-state .empty-icon {
        width: 64px;
        height: 64px;
        margin: 0 auto 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--bg-subtle);
        border-radius: var(--radius-lg);
        color: var(--text-muted);
    }
    .empty-state .empty-icon .icon {
        width: 32px;
        height: 32px;
    }

    .empty-state h3 {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 8px;
    }

    .empty-state p {
        font-size: 14px;
        color: var(--text-secondary);
        margin-bottom: 20px;
        line-height: 1.5;
    }
    ```

- [ ] **Step 3: Commit**

    ```bash
    git add admin/css/admin.css admin/templates/posts/index.php admin/templates/categories/index.php admin/templates/media/index.php admin/templates/menus/index.php admin/templates/users/index.php admin/templates/dashboard.php
    git commit -m "feat(admin): add designed empty states with CTAs"
    ```

---

## Phase 5: Админ-панель — Layout и навигация

> **Цель:** Апгрейд базового layout-а и страницы входа.
> **Время:** 3-4 часа

---

### Task 5.1: Admin header — добавить приветствие, breadcrumbs

**Files:**
- Modify: `admin/templates/layouts/main.php` (header)
- Modify: `admin/css/admin.css` (стили header)

**Проблема:** Шапка минималистична до скуки.

- [ ] **Step 1: Добавить breadcrumbs в header**

    В `admin/templates/layouts/main.php`, найти блок `<header>` (строки 74-79) и заменить:

    ```php
    <header class="admin-header">
        <div>
            <p class="breadcrumbs">
                <a href="/admin">Главная</a>
                <?php if (!empty($breadcrumbs)): ?>
                    <?php foreach ($breadcrumbs as $crumb): ?>
                        <span class="breadcrumb-sep">/</span>
                        <?php if (!empty($crumb['url'])): ?>
                            <a href="<?= $crumb['url'] ?>"><?= TemplateEngine::e($crumb['title']) ?></a>
                        <?php else: ?>
                            <span><?= TemplateEngine::e($crumb['title']) ?></span>
                        <?php endif; ?>
                    <?php endforeach; ?>
                <?php else: ?>
                    <span class="breadcrumb-current"><?= $title ?? 'Панель управления' ?></span>
                <?php endif; ?>
            </p>
            <h1 class="page-title"><?= $title ?? 'Панель управления' ?></h1>
        </div>
        <div class="user-info">
            <span class="user-avatar"><?= strtoupper(substr($user['login'] ?? 'A', 0, 1)) ?></span>
            <span class="user-name"><?= $user['login'] ?? 'Администратор' ?></span>
        </div>
    </header>
    ```

- [ ] **Step 2: Обновить стили header**

    В admin.css найти блок `.admin-header` (строки 185-195) и `.user-info` (строки 202-211):

    ```css
    /* ============================================
       Admin Header
       ============================================ */

    .admin-header {
        background: var(--bg-card);
        padding: 16px 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border-light);
        position: sticky;
        top: 0;
        z-index: 10;
    }

    .admin-header > div:first-child {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .breadcrumbs {
        font-size: 12px;
        color: var(--text-muted);
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .breadcrumbs a {
        color: var(--text-muted);
        text-decoration: none;
        transition: color var(--transition-fast);
    }

    .breadcrumbs a:hover {
        color: var(--primary);
    }

    .breadcrumb-sep {
        color: var(--border-light);
    }

    .breadcrumb-current {
        color: var(--text-secondary);
    }

    .page-title {
        font-size: 20px;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
        line-height: 1.3;
    }

    .user-info {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .user-avatar {
        width: 34px;
        height: 34px;
        border-radius: var(--radius-full);
        background: var(--primary);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 600;
    }

    .user-name {
        color: var(--text-secondary);
        font-size: 14px;
        font-weight: 500;
    }
    ```

- [ ] **Step 3: Добавить breadcrumbs в контроллеры (опционально)**

    В каждом admin-контроллере, перед рендером, можно добавить:
    ```php
    $breadcrumbs = [
        ['title' => 'Посты', 'url' => '/admin/posts'],
    ];
    ```

    Это опционально — breadcrumbs работают и без этого, просто показывая текущий title.

- [ ] **Step 4: Commit**

    ```bash
    git add admin/templates/layouts/main.php admin/css/admin.css
    git commit -m "feat(admin): enhance header with breadcrumbs and user avatar"
    ```

---

### Task 5.2: Login page — улучшить

**Files:**
- Modify: `admin/templates/login.php`
- Modify: `admin/css/admin.css`

**Проблема:** Страница входа — градиент, старая эстетика.

- [ ] **Step 1: Обновить login.php**

    ```php
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Вход в админку — <?= SITE_NAME ?></title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="/public/css/cms-tokens.css">
        <link rel="stylesheet" href="/admin/css/admin.css?v=<?= filemtime(ADMIN_PATH . '/css/admin.css') ?>">
    </head>
    <body class="login-page">
        <div class="login-container">
            <div class="login-box">
                <div class="login-logo"><?= icon('dashboard', 'icon-lg') ?></div>
                <h1 class="login-title">Вход в админку</h1>

                <?php if (isset($error)): ?>
                <div class="alert alert-error">
                    <?= icon('error') ?>
                    <?= TemplateEngine::e($error) ?>
                </div>
                <?php endif; ?>

                <form method="POST" action="/admin/login" class="login-form">
                    <?= csrf_field() ?>

                    <div class="form-group">
                        <label for="login">Логин или Email</label>
                        <input type="text" id="login" name="login" required autofocus
                               placeholder="Введите логин или email">
                    </div>

                    <div class="form-group">
                        <label for="password">Пароль</label>
                        <input type="password" id="password" name="password" required
                               placeholder="Введите пароль">
                    </div>

                    <button type="submit" class="btn btn-primary btn-block">
                        <?= icon('logout', 'icon-sm') ?> Войти
                    </button>
                </form>

                <p class="login-footer">
                    <a href="/"><?= icon('back') ?> Вернуться на сайт</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    ```

- [ ] **Step 2: Обновить стили login-page**

    В admin.css найти блок `/* Login Page */` (строки 40-103) и заменить:

    ```css
    /* ============================================
       Login Page
       ============================================ */

    .login-page {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--sidebar-bg);
    }

    .login-container {
        width: 100%;
        max-width: 400px;
        padding: 20px;
    }

    .login-box {
        background: var(--bg-card);
        border-radius: var(--radius-lg);
        padding: 40px 36px;
        box-shadow: var(--shadow-xl);
    }

    .login-logo {
        text-align: center;
        margin-bottom: 8px;
        color: var(--primary);
    }
    .login-logo .icon {
        width: 40px;
        height: 40px;
    }

    .login-title {
        text-align: center;
        margin-bottom: 28px;
        font-size: 22px;
        font-weight: 600;
        color: var(--text-primary);
    }

    .login-form .form-group {
        margin-bottom: 20px;
    }

    .login-form label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        font-size: 14px;
        color: var(--text-secondary);
    }

    .login-form input {
        width: 100%;
        padding: 12px 16px;
        border: 2px solid var(--border-light);
        border-radius: var(--radius-sm);
        font-size: 15px;
        font-family: inherit;
        color: var(--text-primary);
        background: var(--bg-card);
        transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
    }

    .login-form input:focus {
        outline: none;
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
    }

    .login-form input::placeholder {
        color: var(--text-muted);
    }

    .login-footer {
        text-align: center;
        margin-top: 24px;
        padding-top: 20px;
        border-top: 1px solid var(--border-light);
        display: flex;
        justify-content: center;
    }

    .login-footer a {
        color: var(--text-muted);
        text-decoration: none;
        font-size: 14px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: color var(--transition-fast);
    }

    .login-footer a:hover {
        color: var(--primary);
    }
    ```

- [ ] **Step 3: Commit**

    ```bash
    git add admin/templates/login.php admin/css/admin.css
    git commit -m "refactor(admin): redesign login page with modern dark theme"
    ```

---

## Phase 6: Блог-фронтенд — редизайн public CSS

> **Цель:** Привести `public/css/style.css` к тому же стандарту, что и админку. Убрать градиент, поменять шрифты, переработать карточки.
> **Время:** 3-5 часов

---

### Task 6.1: public/style.css — полный рефакторинг с токенами

**Files:**
- Modify: `public/css/style.css` (~991 строка)

**Проблема:** В блоге те же проблемы: системный шрифт, AI-градиент, generic карточки, тени.

- [ ] **Step 1: Заменить весь файл**

    Переписать `public/css/style.css` используя токены из `cms-tokens.css`:

    ```css
    /* ============================================
       CMS Blog Styles
       Depends on: cms-tokens.css
       ============================================ */

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        font-family: var(--font-sans);
        line-height: 1.7;
        color: var(--neutral-900);
        background: var(--neutral-50);
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    a { color: var(--brand-500); text-decoration: none; transition: color var(--transition-fast); }
    a:hover { color: var(--brand-600); }

    img { max-width: 100%; height: auto; display: block; }

    /* ============ Container ============ */
    .container {
        max-width: var(--container-max);
        margin: 0 auto;
        padding: 0 var(--container-padding);
    }

    /* ============ Header ============ */
    .site-header {
        background: var(--bg-card);
        border-bottom: 1px solid var(--border-light);
        position: sticky;
        top: 0;
        z-index: 100;
    }

    .header-inner {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 0;
    }

    .logo {
        font-size: 22px;
        font-weight: 700;
        color: var(--text-primary);
        text-decoration: none;
    }

    .logo:hover { color: var(--primary); }

    .nav-menu {
        display: flex;
        list-style: none;
        gap: 24px;
        align-items: center;
    }

    .nav-menu a {
        color: var(--text-secondary);
        font-weight: 500;
        font-size: 15px;
    }

    .nav-menu a:hover,
    .nav-menu a.active {
        color: var(--primary);
    }

    /* Mobile menu */
    .mobile-menu-toggle {
        display: none;
        flex-direction: column;
        gap: 5px;
        background: none;
        border: none;
        cursor: pointer;
        padding: 8px;
    }

    .mobile-menu-toggle span {
        width: 24px;
        height: 2px;
        background: var(--text-primary);
        transition: all var(--transition-fast);
        border-radius: 2px;
    }

    @media (max-width: 768px) {
        .mobile-menu-toggle { display: flex; }
        .main-navigation {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-light);
            max-height: 0;
            overflow: hidden;
            transition: max-height var(--transition-normal);
        }
        .main-navigation.active { max-height: 300px; }
        .nav-menu {
            flex-direction: column;
            padding: 16px 20px;
            gap: 12px;
        }
    }

    /* ============ Main Content ============ */
    .site-main {
        padding: 48px 0;
        min-height: calc(100vh - 200px);
    }

    /* ============ Hero Section ============ */
    .hero {
        background: var(--neutral-900);
        color: white;
        padding: 64px 48px;
        border-radius: var(--radius-lg);
        margin-bottom: 48px;
        text-align: center;
    }

    .hero h1 {
        font-size: clamp(28px, 5vw, 44px);
        font-weight: 700;
        margin-bottom: 12px;
        line-height: 1.2;
    }

    .hero p {
        font-size: 18px;
        opacity: 0.85;
        max-width: 600px;
        margin: 0 auto;
    }

    /* ============ Posts Grid ============ */
    .posts-grid h2 {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 28px;
    }

    .posts-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 24px;
    }

    .post-card {
        background: var(--bg-card);
        border-radius: var(--radius-md);
        overflow: hidden;
        border: 1px solid var(--border-light);
        transition: box-shadow var(--transition-normal), transform var(--transition-normal);
    }

    .post-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-3px);
    }

    .post-card .post-link {
        text-decoration: none;
        color: inherit;
        display: block;
    }

    .post-image-wrap {
        width: 100%;
        height: 200px;
        overflow: hidden;
    }

    .post-image-wrap img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform var(--transition-slow);
    }

    .post-card:hover .post-image-wrap img {
        transform: scale(1.05);
    }

    .post-card h3 {
        padding: 20px 20px 8px;
        font-size: 20px;
        font-weight: 600;
    }

    .post-card h3 a {
        color: var(--text-primary);
        text-decoration: none;
    }

    .post-card h3 a:hover {
        color: var(--primary);
    }

    .post-excerpt {
        padding: 0 20px 16px;
        color: var(--text-secondary);
        font-size: 15px;
        line-height: 1.6;
    }

    .post-card-meta {
        padding: 14px 20px;
        border-top: 1px solid var(--border-light);
        display: flex;
        gap: 16px;
        font-size: 13px;
        color: var(--text-muted);
        flex-wrap: wrap;
    }

    .post-card-meta span {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* ============ Single Post ============ */
    .single-post {
        background: var(--bg-card);
        border-radius: var(--radius-md);
        padding: 48px;
        border: 1px solid var(--border-light);
    }

    .post-header {
        margin-bottom: 32px;
    }

    .post-header h1 {
        font-size: clamp(26px, 4vw, 36px);
        font-weight: 700;
        line-height: 1.3;
        margin-bottom: 16px;
    }

    .post-meta-top { margin-bottom: 16px; }

    .post-category-badge {
        display: inline-block;
        background: var(--brand-50);
        color: var(--brand-500);
        padding: 4px 14px;
        border-radius: var(--radius-full);
        text-decoration: none;
        font-size: 13px;
        font-weight: 500;
    }

    .post-category-badge:hover {
        background: var(--brand-100);
        color: var(--brand-600);
    }

    .post-header .post-meta {
        display: flex;
        gap: 20px;
        color: var(--text-muted);
        font-size: 14px;
        flex-wrap: wrap;
        margin-top: 12px;
    }

    .post-header .post-meta span {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .post-featured-image {
        width: 100%;
        max-height: 400px;
        object-fit: cover;
        border-radius: var(--radius-sm);
        margin-bottom: 32px;
    }

    .post-content {
        font-size: 17px;
        line-height: 1.8;
        color: var(--neutral-800);
    }

    .post-content p { margin-bottom: 20px; max-width: 65ch; }
    .post-content h2 { font-size: 24px; margin: 36px 0 16px; font-weight: 700; }
    .post-content h3 { font-size: 20px; margin: 28px 0 12px; font-weight: 600; }
    .post-content ul,
    .post-content ol { margin: 16px 0; padding-left: 24px; }
    .post-content li { margin-bottom: 8px; }
    .post-content img { border-radius: var(--radius-sm); margin: 20px 0; }
    .post-content a { text-decoration: underline; text-underline-offset: 2px; }
    .post-content a:hover { text-decoration: none; }

    .post-tags {
        margin-top: 32px;
        padding-top: 20px;
        border-top: 1px solid var(--border-light);
    }

    .tags-label {
        display: block;
        margin-bottom: 10px;
        color: var(--text-secondary);
        font-size: 14px;
    }

    .tags-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }

    .tag {
        display: inline-block;
        background: var(--brand-50);
        color: var(--brand-500);
        padding: 4px 14px;
        border-radius: var(--radius-full);
        text-decoration: none;
        font-size: 13px;
        font-weight: 500;
        transition: all var(--transition-fast);
    }

    .tag:hover {
        background: var(--brand-100);
        color: var(--brand-600);
    }

    .post-share {
        margin-top: 32px;
        padding-top: 20px;
        border-top: 1px solid var(--border-light);
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .share-link {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border-radius: var(--radius-sm);
        text-decoration: none;
        color: white;
        font-size: 14px;
        transition: opacity var(--transition-fast);
    }

    .share-link:hover { opacity: 0.9; }
    .share-link.vk { background: #0077FF; }
    .share-link.tg { background: #24A1DE; }

    /* ============ Comments ============ */
    .comments-section {
        margin-top: 40px;
        background: var(--bg-card);
        border-radius: var(--radius-md);
        padding: 32px;
        border: 1px solid var(--border-light);
    }

    .comments-section h2 {
        font-size: 22px;
        margin-bottom: 24px;
        font-weight: 600;
    }

    .comments-list { margin-bottom: 32px; }

    .comment {
        display: flex;
        gap: 16px;
        padding: 20px;
        border-bottom: 1px solid var(--border-light);
    }

    .comment:last-child { border-bottom: none; }

    .comment-avatar {
        width: 44px;
        height: 44px;
        border-radius: var(--radius-full);
        background: var(--brand-500);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 18px;
        flex-shrink: 0;
    }

    .comment-body { flex: 1; }

    .comment-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }

    .comment-author { font-weight: 600; color: var(--text-primary); }
    .comment-date { font-size: 13px; color: var(--text-muted); }
    .comment-content { color: var(--text-secondary); line-height: 1.6; }

    .no-comments {
        color: var(--text-muted);
        text-align: center;
        padding: 32px;
    }

    .comment-form-wrap {
        margin-top: 32px;
        padding-top: 28px;
        border-top: 2px solid var(--border-light);
    }

    .comment-form-wrap h3 {
        font-size: 18px;
        margin-bottom: 20px;
    }

    .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
    }

    .form-group { margin-bottom: 16px; }
    .form-group label {
        display: block;
        margin-bottom: 6px;
        font-weight: 500;
        font-size: 14px;
        color: var(--text-secondary);
    }

    .form-control {
        width: 100%;
        padding: 10px 14px;
        border: 2px solid var(--border-light);
        border-radius: var(--radius-sm);
        font-size: 15px;
        font-family: inherit;
        background: var(--bg-card);
        color: var(--text-primary);
        transition: border-color var(--transition-fast);
    }

    .form-control:focus {
        outline: none;
        border-color: var(--brand-500);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }

    textarea.form-control { resize: vertical; min-height: 120px; }

    .btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 20px;
        border: none;
        border-radius: var(--radius-sm);
        font-size: 15px;
        font-weight: 500;
        font-family: inherit;
        cursor: pointer;
        transition: all var(--transition-fast);
        text-decoration: none;
        line-height: 1.4;
    }

    .btn:active { transform: scale(0.97); }
    .btn:focus-visible {
        outline: 2px solid var(--brand-500);
        outline-offset: 2px;
    }

    .btn-primary {
        background: var(--brand-500);
        color: white;
    }
    .btn-primary:hover {
        background: var(--brand-600);
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
    }

    /* ============ Pagination ============ */
    .pagination {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-top: 40px;
    }

    .pagination a,
    .pagination span {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 40px;
        height: 40px;
        padding: 0 12px;
        background: var(--bg-card);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-sm);
        text-decoration: none;
        color: var(--text-primary);
        font-size: 14px;
        font-weight: 500;
        transition: all var(--transition-fast);
    }

    .pagination a:hover {
        background: var(--brand-50);
        border-color: var(--brand-500);
        color: var(--brand-500);
    }

    .pagination .current {
        background: var(--brand-500);
        border-color: var(--brand-500);
        color: white;
    }

    /* ============ Category Filter ============ */
    .category-filter {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
        margin-top: 24px;
    }

    .category-filter a {
        display: inline-block;
        padding: 6px 18px;
        background: var(--bg-card);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-full);
        text-decoration: none;
        color: var(--text-secondary);
        font-size: 14px;
        transition: all var(--transition-fast);
    }

    .category-filter a:hover,
    .category-filter a.active {
        background: var(--brand-50);
        border-color: var(--brand-500);
        color: var(--brand-500);
    }

    /* ============ No Content ============ */
    .no-posts,
    .no-content {
        text-align: center;
        padding: 60px 20px;
        color: var(--text-muted);
    }

    /* ============ Related Posts ============ */
    .related-posts { margin-top: 40px; }
    .related-posts h2 {
        font-size: 22px;
        margin-bottom: 24px;
        font-weight: 600;
    }

    /* ============ Category Page ============ */
    .category-page {
        background: var(--bg-card);
        border-radius: var(--radius-md);
        padding: 40px;
        border: 1px solid var(--border-light);
    }

    .category-header { margin-bottom: 32px; text-align: center; }

    .category-badge {
        display: inline-block;
        background: var(--brand-50);
        color: var(--brand-500);
        padding: 6px 18px;
        border-radius: var(--radius-full);
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 12px;
    }

    .category-header h1 {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .category-description {
        color: var(--text-secondary);
        font-size: 16px;
        max-width: 600px;
        margin: 0 auto 12px;
    }

    .category-stats { color: var(--text-muted); font-size: 14px; }

    .posts-list { display: flex; flex-direction: column; gap: 20px; }

    .post-item {
        padding: 24px;
        border-radius: var(--radius-md);
        border: 1px solid var(--border-light);
        transition: box-shadow var(--transition-fast);
    }

    .post-item:hover { box-shadow: var(--shadow-sm); }

    .post-item h2 { margin-bottom: 8px; }
    .post-item h2 a { color: var(--text-primary); text-decoration: none; }
    .post-item h2 a:hover { color: var(--primary); }

    .post-item .post-meta {
        margin-bottom: 12px;
        color: var(--text-muted);
        font-size: 14px;
    }

    .post-item .post-excerpt {
        color: var(--text-secondary);
        line-height: 1.7;
    }

    /* ============ Static Page ============ */
    .static-page {
        background: var(--bg-card);
        border-radius: var(--radius-md);
        padding: 40px;
        border: 1px solid var(--border-light);
    }

    .page-header {
        margin-bottom: 28px;
        border-bottom: 2px solid var(--neutral-200);
        padding-bottom: 16px;
    }

    .page-header h1 {
        font-size: 28px;
        font-weight: 700;
    }

    .page-updated {
        color: var(--text-muted);
        font-size: 14px;
        margin-top: 8px;
    }

    .page-featured-image { margin-bottom: 32px; }
    .page-featured-image img {
        width: 100%;
        max-height: 400px;
        object-fit: cover;
        border-radius: var(--radius-sm);
    }

    .page-content {
        font-size: 17px;
        line-height: 1.8;
        color: var(--neutral-800);
    }
    .page-content h2 { font-size: 24px; margin: 36px 0 16px; font-weight: 700; }
    .page-content h3 { font-size: 20px; margin: 28px 0 12px; font-weight: 600; }
    .page-content p { margin-bottom: 20px; max-width: 65ch; }
    .page-content ul,
    .page-content ol { margin: 16px 0; padding-left: 24px; }
    .page-content img { border-radius: var(--radius-sm); margin: 20px 0; }

    .page-meta {
        margin-top: 32px;
        padding-top: 20px;
        border-top: 1px solid var(--border-light);
        color: var(--text-secondary);
        font-size: 14px;
    }

    /* ============ Footer ============ */
    .site-footer {
        background: var(--neutral-900);
        color: var(--neutral-400);
        padding: 32px 0;
        margin-top: 60px;
    }

    .site-footer .container { text-align: center; }
    .site-footer p { margin: 0; }

    /* ============ Responsive ============ */

    @media (max-width: 768px) {
        .header-inner { flex-wrap: wrap; }
        .hero { padding: 40px 24px; }
        .hero h1 { font-size: 28px; }
        .hero p { font-size: 16px; }
        .site-main { padding: 24px 0; }
        .posts-grid { grid-template-columns: 1fr; }
        .single-post,
        .static-page,
        .category-page { padding: 24px; }
        .post-header h1 { font-size: 24px; }
        .post-featured-image { max-height: 220px; }
        .form-row { grid-template-columns: 1fr; }
        .comment { flex-direction: column; }
        .comment-avatar { width: 36px; height: 36px; font-size: 14px; }
        .site-footer .footer-inner { flex-direction: column; gap: 16px; }
    }

    @media (max-width: 480px) {
        .hero h1 { font-size: 22px; }
        .post-card h3 { font-size: 18px; }
        .btn { width: 100%; justify-content: center; }
    }
    ```

- [ ] **Step 2: Commit**

    ```bash
    git add public/css/style.css
    git commit -m "refactor(blog): complete rewrite with design tokens, remove AI gradient"
    ```

---

## Phase 7: Стратегические улучшения

> **Цель:** Добавить то, что обычно забывают — 404, skip-to-content, мета-теги, плавный скролл.
> **Время:** 2-3 часа

---

### Task 7.1: Custom 404 page

**Files:**
- Create: `templates/404.php`
- Проверить: `core/routes.php` (или index.php) — как обрабатывается 404

**Проблема:** Нет кастомной 404 страницы.

- [ ] **Step 1: Создать 404.php**

    ```php
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Страница не найдена — <?= SITE_NAME ?></title>
        <meta name="robots" content="noindex">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="/public/css/cms-tokens.css">
        <style>
            body {
                font-family: 'Outfit', system-ui, sans-serif;
                background: var(--neutral-50);
                color: var(--neutral-900);
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                text-align: center;
                padding: 20px;
            }
            .error-page { max-width: 480px; }
            .error-code {
                font-size: 96px;
                font-weight: 700;
                color: var(--brand-500);
                line-height: 1;
                margin-bottom: 8px;
            }
            .error-title {
                font-size: 24px;
                font-weight: 600;
                margin-bottom: 12px;
            }
            .error-text {
                color: var(--text-secondary);
                font-size: 16px;
                line-height: 1.6;
                margin-bottom: 32px;
            }
            .error-actions {
                display: flex;
                gap: 12px;
                justify-content: center;
                flex-wrap: wrap;
            }
            .btn {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 10px 24px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 500;
                font-family: inherit;
                text-decoration: none;
                cursor: pointer;
                transition: all 0.2s;
            }
            .btn-primary {
                background: var(--brand-500);
                color: white;
            }
            .btn-primary:hover {
                background: var(--brand-600);
            }
            .btn-outline {
                background: transparent;
                border: 2px solid var(--border-light);
                color: var(--text-secondary);
            }
            .btn-outline:hover {
                border-color: var(--brand-500);
                color: var(--brand-500);
            }
        </style>
    </head>
    <body>
        <div class="error-page">
            <div class="error-code">404</div>
            <h1 class="error-title">Страница не найдена</h1>
            <p class="error-text">
                Страница, которую вы ищете, не существует или была перемещена.<br>
                Возможно, вы перешли по устаревшей ссылке.
            </p>
            <div class="error-actions">
                <a href="/" class="btn btn-primary">← На главную</a>
                <a href="javascript:history.back()" class="btn btn-outline">Вернуться назад</a>
            </div>
        </div>
    </body>
    </html>
    ```

- [ ] **Step 2: Найти где обрабатывается 404**

    Проверить `core/Router.php` — как возвращается 404. Обычно это:
    ```php
    http_response_code(404);
    require TEMPLATES_PATH . '/404.php';
    exit;
    ```

    Если такого нет — добавить обработку в `core/Router.php` в метод `dispatch()`.

- [ ] **Step 3: Commit**

    ```bash
    git add templates/404.php
    git commit -m "feat: add custom 404 error page"
    ```

---

### Task 7.2: Skip-to-content + smooth scroll

**Files:**
- Modify: `admin/templates/layouts/main.php`
- Modify: `public/css/style.css`
- Modify: шаблоны тем блога

**Проблема:** Нет "skip to content" для клавиатурной навигации. Нет `scroll-behavior: smooth`.

- [ ] **Step 1: Добавить skip-link в admin layout**

    В `admin/templates/layouts/main.php`, сразу после `<body>`:
    ```html
    <a href="#main-content" class="skip-link">Перейти к содержимому</a>
    ```

    Добавить `id="main-content"` к `<main>`:
    ```html
    <main class="admin-content" id="main-content">
    ```

- [ ] **Step 2: Добавить CSS для skip-link**

    В admin.css:
    ```css
    /* ============================================
       Accessibility: Skip Link
       ============================================ */

    .skip-link {
        position: absolute;
        top: -100%;
        left: 50%;
        transform: translateX(-50%);
        z-index: 10000;
        padding: 12px 24px;
        background: var(--primary);
        color: white;
        border-radius: 0 0 var(--radius-sm) var(--radius-sm);
        font-size: 14px;
        font-weight: 600;
        text-decoration: none;
        transition: top var(--transition-fast);
    }

    .skip-link:focus {
        top: 0;
        outline: none;
    }
    ```

- [ ] **Step 3: Добавить scroll-behavior**

    В `public/css/style.css`, в начало:
    ```css
    html {
        scroll-behavior: smooth;
    }
    ```

    В admin.css, в начало:
    ```css
    html {
        scroll-behavior: smooth;
    }
    ```

- [ ] **Step 4: Commit**

    ```bash
    git add admin/templates/layouts/main.php admin/css/admin.css public/css/style.css
    git commit -m "feat: add skip-to-content link and smooth scroll"
    ```

---

### Task 7.3: Social meta tags

**Files:**
- Modify: шаблоны тем блога (head section)

**Проблема:** Нет Open Graph и Twitter meta-тегов для соцсетей.

- [ ] **Step 1: Добавить мета-теги в head шаблонов**

    После `<title>` добавить:
    ```php
    <meta name="description" content="<?= TemplateEngine::e($meta_description ?? SITE_NAME) ?>">
    <meta property="og:title" content="<?= TemplateEngine::e($title ?? SITE_NAME) ?>">
    <meta property="og:description" content="<?= TemplateEngine::e($meta_description ?? SITE_NAME) ?>">
    <meta property="og:type" content="website">
    <meta property="og:url" content="<?= SITE_URL . ($_SERVER['REQUEST_URI'] ?? '/') ?>">
    <?php if (!empty($og_image)): ?>
    <meta property="og:image" content="<?= $og_image ?>">
    <?php endif; ?>
    <meta name="twitter:card" content="summary_large_image">
    ```

- [ ] **Step 2: Commit**

    ```bash
    git add <найденные-шаблоны-тем-блога>
    git commit -m "feat(blog): add Open Graph and Twitter meta tags"
    ```

---

## Phase 8: Финальный CSS noise overlay (premium touch)

> **Цель:** Добавить subtle grain/noise текстуру для премиального ощущения.
> **Время:** 30 минут

---

### Task 8.1: CSS noise overlay для админки

**Files:**
- Modify: `admin/templates/layouts/main.php`
- Modify: `admin/css/admin.css`

- [ ] **Step 1: Добавить CSS для noise**

    В admin.css:
    ```css
    /* ============================================
       Ambient Noise Overlay (subtle grain)
       ============================================ */

    .noise-overlay {
        position: fixed;
        inset: 0;
        z-index: 9999;
        pointer-events: none;
        opacity: 0.03;
        mix-blend-mode: overlay;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
        background-repeat: repeat;
        background-size: 256px 256px;
    }
    ```

- [ ] **Step 2: Добавить элемент в layout**

    В `admin/templates/layouts/main.php`, перед закрывающим `</body>`:
    ```html
    <div class="noise-overlay" aria-hidden="true"></div>
    ```

- [ ] **Step 3: Commit**

    ```bash
    git add admin/templates/layouts/main.php admin/css/admin.css
    git commit -m "feat(admin): add subtle grain/noise overlay for premium feel"
    ```

---

## Execution Handoff

> **Для agentic workers:** После выполнения всех задач, запустить проверку:
> 1. Открыть страницу входа — проверить, что нет градиента, шрифт Outfit, кнопка нажимается
> 2. Открыть дашборд — проверить карточки статистики, сайдбар, таблицу
> 3. Открыть список постов — проверить empty state, иконки, кнопки
> 4. Открыть блог — проверить шрифт, карточки, футер
> 5. Проверить 404 — ввести несуществующий URL
> 6. Проверить skip-to-content — нажать Tab при загрузке страницы
> 7. `grep -rn "#667eea\|#764ba2\|#3b82f6" admin/ --include="*.css"` — не должно быть совпадений (кроме тех, что не трогали)
> 8. `grep -rn "emoji" admin/templates/ --include="*.php"` — не должно быть emoji-символов в навигации (кроме контента)