# NewWeb CMS — Project Overview

## Что это за проект

Собственная **PHP CMS** (vanilla, без фреймворков) на PostgreSQL.
Изначально — стандартный блог-движок, сейчас — **многофункциональный сайт VPN-сервиса**:

- **Публичная часть** — лендинг HexaVeil (тема `hexaveil`) с 3D-глобусом серверов,
  тарифами, FAQ и **блогом**
- **Админ-панель** — собственная система управления контентом с редизайном в стиле
  remnawave (тёмная тема, mesh-фон, glass-эффекты, командная палитра)

### Деплоймент (production, 26.09.2026)

| Параметр | Значение |
|---|---|
| **Домен** | `https://hexaveil.xyz` |
| **Админка** | `https://hexaveil.xyz/admin/` |
| **Логин** | `admn` |
| **Пароль** | `Cke;bkb2Njdfhbof` |
| **Сервер** | Ubuntu, Docker Compose |
| **PHP** | 8.1-FPM (Debian-based) |
| **Web** | Nginx (alpine), 2 уровня: nginx-selfsteal (reverse proxy) → hexacms_web (FastCGI) |
| **БД** | PostgreSQL 16 (alpine) |
| **Сеть** | 2 IP: `159.194.221.84` (нода) + `85.198.99.102` (CMS) |
| **SSL** | Let's Encrypt, `hexaveil.xyz` |
| **Reverse proxy** | nginx-selfsteal (`network_mode: host`) на портах 80/443 |
| **Node** | Remnawave node (VLESS/Reality + XTLS-Vision) на порту 2222 |

### Локальная разработка (Docker)

```bash
docker compose up --build -d
```
(PHP 8.1 + Nginx + PostgreSQL 16)

---

## Архитектура

```
NewWeb/
├── index.php              # Front-контроллер (маршрутизация)
├── Dockerfile             # PHP 8.1-FPM (docker)
├── docker-compose.yml     # Nginx + PHP + PostgreSQL
├── docker-entrypoint.sh   # Инициализация при старте
├── .env                   # Переменные окружения
├── .env.example           # Шаблон окружения
├── .docker/
│   ├── nginx/default.conf # Nginx vhost
│   └── php/php.ini        # PHP настройки
├── config/config.php      # Настройки БД, путей, константы (env-aware)
├── core/                  # Ядро CMS
│   ├── Router.php         # Маршрутизатор (GET/POST, паттерны {slug})
│   ├── routes.php         # Все маршруты сайта
│   ├── TemplateEngine.php # Шаблонизатор (set/display, layouts)
│   ├── Database.php          # PDO-обёртка (pgsql)
│   ├── Post.php           # Модель постов (CRUD, категории, теги, комменты)
│   ├── Category.php       # Модель категорий
│   ├── Page.php           # Модель страниц
│   ├── User.php           # Модель пользователей
│   ├── Auth.php           # Аутентификация (admin)
│   ├── helpers.php        # Утилиты (truncate, format_date, createTemplate)
│   ├── helpers_icons.php  # Inline Lucide SVG-иконки (icon())
│   ├── DataGrid.php       # Рендерер таблиц для списков админки
│   ├── Hooks.php          # Система хуков (do_action, add_action)
│   ├── Request.php        # HTTP-запрос (post/get/clean)
│   ├── Session.php        # Сессии
│   ├── Crypto.php         # AES-256 шифрование
│   └── Autoloader.php     # PSR-4 автозагрузка
├── admin/                 # Админ-панель
│   ├── controllers/       # 11 контроллеров (Posts, Pages, Categories, Media, etc.)
│   ├── templates/         # 13 папок с PHP-шаблонами
│   ├── js/
│   │   ├── panel.js       # JS панели (настройки вида, DataGrid, превью)
│   │   └── command-palette.js # Командная палитра (Ctrl+K)
│   └── css/admin.css      # Наследие (не используется)
├── templates/
│   └── themes/
│       ├── hexaveil/      # АКТИВНАЯ ТЕМА — VPN лендинг + блог
│       ├── modern/        # Запасная блог-тема
│       ├── minimal/       # Запасная блог-тема
│       └── default/       # Базовая блог-тема
├── public/
│   ├── hexaveil/          # CSS/JS/ассеты темы HexaVeil
│   │   ├── css/
│   │   │   ├── variables.css  # CSS-переменные (цвета, шрифты)
│   │   │   ├── global.css     # Глобальные стили (контейнер, кнопки, типографика)
│   │   │   ├── style.css      # Стили секций + БЛОГ
│   │   │   └── stars.css      # Звёздный фон
│   │   ├── js/
│   │   │   ├── star.js        # Particle system (Simplex Noise)
│   │   │   ├── main.js        # Основной JS
│   │   │   ├── data.js        # Данные для 3D-глобуса
│   │   │   ├── planet.js      # Three.js 3D-глобус
│   │   │   ├── server-panel.js # Панель серверов
│   │   │   └── telemetry.js   # Телеметрия
│   │   └── assets/            # earth-night.jpg, favicon и др.
│   ├── css/panel/         # Дизайн-система админки (7 файлов)
│   ├── uploads/           # Загруженные медиа
│   └── finance/           # Экспорты CSV
├── db/
│   ├── postgres/init/     # PostgreSQL авто-инициализация
│   │   └── 01-schema.sql  # Полная схема БД (307 строк)
│   └── prod_data.sql      # Дамп production БД (data-only, для локальной синхронизации)
├── plugins/               # PHP-плагины (хуки)
├── core/payments/         # Платёжные клиенты
│   └── YooKassaClient.php # YooKassa API-клиент
└── docs/
    ├── decisions/
    │   └── ADR-001-panel-design-system.md  # Документация редизайна админки
    ├── MIGRATION_BRIEF.md                  # Краткий бриф миграции на React SPA
    ├── MIGRATION_TO_REMNAWAVE_STACK.md     # Полное ТЗ миграции (3 фазы)
    └── MIGRATION_STATUS.md                 # Статус: что сделано / что осталось (handoff)
```

---

## Статус реализации

### ✅ Реализовано

#### Ядро CMS
- [x] Маршрутизация (GET/POST, параметры, catch-all `{slug}`)
- [x] PDO-обёртка (fetch, fetchAll, insert, update, delete)
- [x] Шаблонизатор (layouts, секции, PHP-шаблоны)
- [x] Аутентификация (admin/editor/author роли)
- [x] CSRF-защита
- [x] Сессии
- [x] DataGrid — единый рендерер таблиц для админки
- [x] Inline Lucide SVG-иконки (icon(), 40+ иконок)
- [x] Система хуков (Hooks.php)
- [x] AES-256 шифрование чувствительных данных (Crypto.php)

#### Блог
- [x] Таблицы: posts, categories, tags, post_tags, comments
- [x] Полный CRUD постов (админка)
- [x] TinyMCE → CKEditor 5 (ESM, все плагины, esm.sh CDN)
- [x] Категории, теги, комментарии (модерация)
- [x] Загрузка изображений (/admin/media/upload)
- [x] Счётчик просмотров
- [x] Маршруты: /blog, /post/{slug}, /category/{slug}
- [x] Шаблон блога в стиле HexaVeil (glass-карточки, pill-фильтр категорий)

#### Тема HexaVeil (лендинг)
- [x] 3D-глобус с серверами (Three.js)
- [x] Tagline + Hero-секция
- [x] Преимущества, тарифы (пробный доступ), сервисы
- [x] Технологии, реферальная программа
- [x] FAQ (аккордеон)
- [x] Подвал с меню и соцсетями
- [x] Звёздный фон (canvas + particle system с Simplex Noise)
- [x] Glassmorphism-карточки, тёмная киберпанк-эстетика
- [x] Адаптивность (мобильные планшеты)
- [x] **Блог** — добавлен недавно (маршрут + шаблон + стили + ссылка в навигации)
- [x] **Страница категории** — обновлена в стиле блога
- [x] **Блог-секция на главной** — реальные посты из БД, настройки в теме
- [x] **Floating-виджет блога** — фиксированная glass-панель, вкл/выкл в настройках
- [x] **Particle-фон при reduced-motion** — рисует статический кадр вместо пустого canvas

#### Админ-панель
- [x] Редизайн: тёмная тема, mesh-фон, glass-эффекты
- [x] 6 акцентных пресетов (Obsidian, Halo, Arctic, Sakura, Twilight, Ember)
- [x] Светлая тема ([data-mode="light"])
- [x] Командная палитра (Ctrl+K)
- [x] Настройки вида (тема/режим/плотность/радиус/шрифт) — per-user в БД
- [x] DataGrid-таблицы для всех списков
- [x] CKEditor 5 (import map через esm.sh, все плагины)
- [x] Кастомный адаптер загрузки изображений для CKEditor
- [x] **Категории → подменю Постов** — управление категориями перенесено в интерфейс постов (табы Посты/Категории, сайдбар: подпункт с отступом)
- [x] **isActive() — подсветка родительского пункта** — при открытой категории подсвечивается и пункт «Посты»
- [x] **Полный визуальный рефакторинг админ-панели (Remnawave-style):** усилен фон, glass-эффекты, кастомный dropzone, мини-мокап превью тем, скруглённые бары графика с HTML-легендой, приглушённые цвета KPI, KPI-иконки в тонированных квадратах, хедер с колокольчиком и pill Онлайн, page-subtitle, аккордеон с иконками и счётчиками, единая высота инпутов 44px, DataGrid-чекбоксы + mass-actions + kebab-меню, бейджи soft-bg, ghost-кнопки действий, dot-grid текстура фона, все радиусы через токены
- [x] **Починен ₽** — добавлен Segoe UI в font-stack + cyrillic subset в Google Fonts
- [x] Финансовый модуль: YooKassa + Platega интеграции, CSV-экспорт, bulk actions

#### Технические исправления
- [x] **Удалены остатки Nova VPN** — ссылка `t.me/nova_vpn` заменена на `t.me/HexaVeil_bot` в theme.php и layouts/main.php
- [x] **Удалена совместимость с Open Server Panel** — `_deploy.bat` удалён, дефолтный DB_HOST изменён на `db`, драйвер по умолчанию `pgsql`, домен `http://hexacms` → `http://localhost`, очищены все упоминания OSP в документации и конфигах
- [x] **Исправлен Nginx root** — `/var/www/html/public` → `/var/www/html` (админ-панель лежит вне public/)
- [x] **entrypoint генерирует пароль** — `docker-entrypoint.sh` автоматически заменяет плейсхолдер bcrypt-хеша в seed-данных при первом запуске (через переменную `ADMIN_PASSWORD`)

---

## 🎨 Визуальный аудит админ-панели (14.09.2026)

> Проведён сравнительный анализ скриншотов текущей админки vs эталон Remnawave (React UI).
> Выявлены критические и косметические расхождения. Структура верная, проблема в слое оформления.

### 🔴 Критические — бросаются в глаза сразу

| Проблема | Где | Решение |
|----------|-----|---------|
| **Превью тем** — плоские цветные прямоугольники | `/admin/theme` | Мини-мокап браузера с градиентом + тень + hover-lift |
| **Raw `<input type="file">`** — системный виджет | `/admin/theme` | Кастомный dropzone (пунктирная рамка, иконка, drag-over) |
| **График** — дефолтный Chart.js (30 повёрнутых дат, иголки-бары, сырая легенда) | `/admin/finance` | Скруглённые бары с градиентом, адаптивные тики, HTML-легенда, pill-переключатели |
| **Рубль — `P` вместо `₽`** | Везде | Подключить шрифт с нормальным глифом ₽ |

### 🟡 Средние — визуальный шум / неаккуратно

| Проблема | Где | Решение |
|----------|-----|---------|
| **Тёплое свечение фона отсутствует** | body/layout | Radial gradient amber сверху-центр + faint glow по правому краю |
| **Glass-токены слишком прозрачные** | `.card`, `.finance-*` | Усилить рамку, тень, внутренний хайлайт |
| **Бейджи outline вместо soft-bg** | Везде | Залить цветным фоном 12%, убрать outline-варианты |
| **Иконки действий — крошечные outline-квадраты** | DataGrid таблицы | Ghost-кнопки 36px с hover-фоном |
| **Строки таблицы ~46px (тесно)** | DataGrid | Поднять до 56–64px, добавить hover |
| **Карточки метрик сливаются с фоном** | Финансы | Заметно светлее фона, иконка-акцент, мягкая тень |
| **Цифры #22c55e / #ef4444 — «игрушечные»** | Финансы | Десатурированные tinted-цвета |

### 🟢 Мелкая полировка

| Проблема | Решение |
|----------|---------|
| Нет subtitle под H1 на страницах | `<p class="page-subtitle">...</p>` |
| Аккордеон без иконок и счётчиков | Иконка + бейдж `[6]` в заголовке секции |
| Инпуты разной высоты | Единый `height: 44px` + amber focus-ring |
| Нет масс-экшенов в таблице | Чекбоксы + mass actions bar (JS) |
| Нет kebab-меню `⋮` в строках | Dropdown с действиями |
| Фильтры над таблицей, а не под заголовками | Inline-фильтры под `<th>` |
| Нет хедера-действий (колокольчик, pill Онлайн) | Дополнить layout |

### 📐 План доработок (по приоритету)

1. **Превью тем** + dropzone — ~1 час (CSS + шаблон)
2. **График** — ~1 час (Chart.js config, HTML-легенда)
3. **Glass-токены + фон** — ~30 мин (CSS-переменные)
4. **Бейджи + кнопки + иконки** — ~30 мин (CSS)
5. **Таблица: чекбоксы + mass actions** — ~1 час (шаблон + JS)
6. **Инпуты + аккордеон** — ~30 мин (CSS)
7. **Хедер + subtitle** — ~30 мин (layout)

**Итого:** ~2 дня, 7–10 файлов, преимущественно CSS/шаблоны. Бэкенд-логика не меняется.

---

## 🗺️ План развития (по фазам)

### 🔵 Фаза 1 — Быстрые фичи (следующие 2–3 часа)

Базовый функционал блога, который пишется на чистом PHP без фреймворков.

#### Блог (доработки)
- [ ] **RSS-лента** — `/blog/rss.xml`, последние посты в RSS 2.0
- [ ] **Поиск по постам** — полнотекстовый поиск (PostgreSQL tsvector), строка поиска, результаты
- [ ] **Related posts на странице поста** — отобразить (метод `getRelated()` уже есть в Post, в роуте тоже)
- [ ] **Пагинация на /blog** — ссылки «далее/назад» (сейчас только `POSTS_PER_PAGE`)

#### SEO — встроенная SEO-система (аналог Yoast SEO)

> **Анализ Yoast SEO**: плагин для WordPress с ~13 млн установок. Ключевые возможности:
> - **Per-post SEO** — отдельный meta-box для каждого поста/страницы: SEO-заголовок, meta-description, focus keyphrase, readability score
> - **XML Sitemaps** — автоматическая генерация sitemap.xml (посты, страницы, категории, теги)
> - **Social preview** — как пост будет выглядеть в Facebook / Twitter, с редактированием og:title, og:description, og:image
> - **Schema.org structured data** — Article, BreadcrumbList, SiteNavigationElement, Organization
> - **Технический SEO** — canonical URL, robots meta, noindex для архивов, redirect manager
> - **Bulk editor** — массовое редактирование SEO-заголовков и мета-описаний
> - **Content analysis** — readability checks, keyphrase density, internal linking suggestions
> - **AI-драфтинг** — генерация meta description через AI (премиум)
>
> В **нашем проекте** уже есть: canonical URL, per-page og:title/og:description, общий meta-description в настройках, robots:noindex на 404. Нужно построить аналогичную систему.

##### База данных (таблица `post_seo` или расширение `posts`)
- [ ] **Добавить колонки в `posts`**: `seo_title VARCHAR(255)`, `seo_description TEXT`, `seo_keywords VARCHAR(255)`, `og_image VARCHAR(255)`
- [ ] **Или отдельная таблица** `post_seo(post_id, seo_title, seo_description, seo_keywords, og_image, focus_keyphrase, is_noindex BOOLEAN, is_nofollow BOOLEAN)`

##### Админ-панель — SEO-метабокс в форме поста
- [ ] **SEO-вкладка/секция** в боковой колонке формы поста (развернуть по клику)
- [ ] **Поля**: SEO-заголовок (с предзаполнением из title), Meta-description (счётчик символов, лимит 160), Ключевые слова, Focus keyphrase
- [ ] **OG-image override** — предпросмотр Open Graph изображения
- [ ] **Social preview** — миниатюра как пост выглядит в Facebook (заголовок + описание + картинка)
- [ ] **Bulk editor** — страница `/admin/seo/bulk` со списком всех постов/страниц, массовое редактирование SEO-полей

##### Технический SEO (автоматика)
- [ ] **Sitemap.xml** — `/sitemap.xml` с постами + страницами + категориями + тегами (приоритеты, lastmod)
- [ ] **robots.txt** — `/robots.txt` с указанием sitemap: `Sitemap: https://site.com/sitemap.xml`
- [ ] **SEO-мета в layout** — `og:image`, `og:url`, `og:site_name`, `twitter:card` доделать во всех темах
- [ ] **Schema.org JSON-LD** — Article (для постов), BreadcrumbList, Organization (с логотипом HexaVeil)
- [ ] **noindex/nofollow** — настройка per-post + по-умолчанию для категорий/тегов/архивов

##### Глобальные SEO-настройки (страница `/admin/settings` → секция SEO)
- [ ] **SEO-раздел** в настройках: Home Title, Home Description, Default OG Image, Separator, Site Name
- [ ] **Google Search Console / Yandex Webmaster** — поле для HTML-кода верификации
- [ ] **AI-генерация meta-description** (опционально) — если есть доступ к OpenAI, сгенерировать из контента

##### Content analysis (readability + keyphrase)
- [ ] **Readability score** — проверка: длина предложений, пассивный залог, переходы (transition words), Flesch-Kincaid
- [ ] **Keyphrase density** — подсчёт вхождений ключевой фразы в текст, заголовки, alt-картинок
- [ ] **Internal linking suggestions** — предложить похожие посты для ссылки (на основе категории + тегов)

#### Админ-панель (доработка формы поста)
- [ ] **Теги в форме поста** — выбор существующих тегов (checkboxes или select multiple) + создание новых
- [ ] **Editor styling** — поправить CSS, если CKEditor отображается криво в тёмной теме
- [ ] **Кнопка «Просмотр»** — превью поста перед публикацией

#### Админ-панель — визуальный рефакторинг (Remnawave-style)
> На основе аудита от 14.09.2026. Все изменения — CSS/шаблоны, бэкенд не трогать.

**Приоритет 1 — «кричаще дешёвое» (даёт 70% визуального прироста)**
- [ ] **Превью тем** — заменить плоские прямоугольники на мини-мокап браузера (скруглённый верх, 3 точки, градиент/скриншот, тень `0 12px 32px rgba(0,0,0,.45)`, hover-lift)
- [ ] **Dropzone** — сырой `<input type="file">` → кастомный dropzone (пунктирная рамка, иконка upload, drag-over state)
- [ ] **График Finance** — скруглённые бары с градиентом, адаптивные тики (без наклона, ~6 подписей), кастомная HTML-легенда, pill-переключатели 7Д/1М/3М/1Г (amber-tint)
- [ ] **Починить ₽** — подключить шрифт с корректным глифом рубля в основном стеке

**Приоритет 2 — слои, отступы, премиальность**
- [ ] **Тёплое свечение фона** — radial gradient amber сверху-центр + faint glow по правому краю контента
- [ ] **Glass-токены** — усилить `--glass-bg`, `--glass-border`, добавить `inset 0 1px 0 rgba(255,255,255,.04)` + `0 8px 24px rgba(0,0,0,.35)`
- [ ] **Бейджи** — залить soft-bg 12% + цветной текст, убрать outline-варианты, увеличить padding
- [ ] **Иконки действий в DataGrid** — ghost-кнопки 36px с hover-фоном, единый stroke-width
- [ ] **Строки таблицы** — поднять высоту с 46px до 56–64px, hover-подсветка
- [ ] **Карточки метрик (Finance)** — заметно светлее фона, иконка-акцент, мягкая тень, числа `font-variant-numeric: tabular-nums`
- [ ] **Цвета цифр** — десатурировать `#22c55e`/`#ef4444` до tinted-вариантов

**Приоритет 3 — мелкая полировка**
- [ ] **Page subtitle** — `<p class="page-subtitle">...</p>` под H1 на всех страницах админки
- [ ] **Аккордеон** — иконка в круге слева, бейдж `[N]` в заголовке секции, chevron поворот, hover-фон строки, анимация раскрытия
- [ ] **Инпуты** — единая высота 44px, тёмная заливка, amber focus-ring, helper-текст снизу
- [ ] **Mass actions bar** — чекбоксы в первой колонке + панель массовых действий при выборе строк
- [ ] **Kebab-меню `⋮`** — выпадающий glass-dropdown с действиями в каждой строке таблицы
- [ ] **Inline-фильтры** — фильтры под заголовками колонок (select/input под `<th>`), а не отдельной строкой сверху
- [ ] **Хедер** — добавить кнопки `⟳ Обновить`, `↻ Синхр.`, колокольчик с бейджем, pill `● Онлайн`
- [ ] **Единый радиус** — карточки 16px, инпуты/кнопки 10–12px, пилы 999px
- [ ] **Транзишены** — `transition: .18s` на hover/focus/лифт карточек/кнопок/пилов

#### Тема HexaVeil (доработки)
- [x] **Блог-секция на лендинге (Вариант A)** — 3 glass-карточки с реальными постами, ссылка «Читать все статьи» (c привязкой к slug)
- [x] **Floating-виджет блога (Вариант B)** — фиксированная glass-панель в правом нижнем углу, раскрывается по клику, 3 превью, кнопка закрытия
- [x] **Настройки блога и виджета** — добавлены в `theme.php`: вкл/выкл секции, количество постов, заголовки, вкл/выкл виджета
- [ ] Хлебные крошки на странице поста
- [ ] Счётчик слов/время чтения на статье
- [ ] Tеги на карточках постов

---

### 🟡 Фаза 2 — Инфраструктура + API-интеграции (1–2 недели)

Подготовка кода к PostgreSQL и расширение финансового модуля внешними API.

#### Инфраструктура (подготовка к PostgreSQL)
- [ ] **Query Builder** — обёртка над PDO вместо голых SQL-строк (цепочки: `table()->where()->get()`)
- [x] **Убрать MySQL-специфику** во всех моделях: backtick-кавычки, `LIMIT` без биндинга, `ON DUPLICATE KEY` → аналоги для PostgreSQL
- [x] **Миграции через SQL-файлы** — `db/postgres/init/01-schema.sql` (авто-инициализация через docker-entrypoint-initdb.d)

#### Финансы + API-интеграции
- [ ] **Remnawave API-клиент** — HTTP-клиент (паттерн уже есть: `httpGet/httpPost` в FinanceController)
- [ ] **Статусы, подписки, пользователи Remnawave** — получение через API, отображение в DataGrid
- [ ] **BEdolagabot API-клиент** — интеграция с данными бота (транзакции, пользователи)
- [ ] **Сводка по всем источникам** — Platega + Remnawave + бот в одном дашборде
- [ ] **Автосинхронизация** — cron-эндпоинты для Remnawave и бота (паттерн `apiPlategaCronSync` готов)
- [ ] **Exports** — расширить CSV-экспорт данными из API (сейчас только из БД)

#### Админ-панель
- [ ] CRUD тегов
- [ ] CRUD комментариев
- [ ] Dashboard с графиками (Chart.js — уже подключён)

#### Общее
- [ ] Валидация slug-ов (если пост удалён, slug может конфликтовать)
- [ ] Кеширование (APCu или файловый кеш)
- [ ] Автосохранение черновиков (есть закомментированный код в CKEditor config)

---

### 🟠 Фаза 3 — Углубление функционала

Функции, которые требуют либо очередей, либо более серьёзной архитектуры.

#### Тема HexaVeil
- [ ] Секция тарифов (сейчас закомментирована в навигации)
- [ ] Страница «Политика конфиденциальности»
- [ ] Страница «Условия использования»
- [ ] Оптимизация Three.js для мобильных (сейчас грузит текстуру всегда)

#### Админ-панель
- [ ] CRUD меню
- [ ] CRUD виджетов
- [ ] Управление темой (активация/деактивация/настройки)
- [ ] Логи (просмотр системных ошибок)
- [ ] Экспорт постов в Markdown/HTML

#### Общее
- [ ] Резервное копирование БД
- [ ] Мультиязычность (RU/en)
- [ ] Тесты (хотя бы smoke-тесты для маршрутов)

---

### 🟢 Фаза 4 — Переезд на свой сервер + PostgreSQL ✅

> **Статус: выполнено (26.09.2026).** Проект полностью контейнеризирован, работает на PostgreSQL, развёрнут на production-сервере с SSL.

#### Docker-инфраструктура
- [x] `Dockerfile` — PHP 8.1-FPM (Debian) с pdo_pgsql, pdo_mysql, intl, mbstring, opcache
- [x] `docker-compose.yml` — 3 сервиса: app (PHP-FPM), web (Nginx), db (PostgreSQL 16)
- [x] `.docker/nginx/default.conf` — Nginx vhost с deny доступа к служебным директориям
- [x] `.docker/php/php.ini` — upload 64M, memory 256M, opcache
- [x] `docker-entrypoint.sh` — ожидание PG, создание install.lock, автогенерация bcrypt-хеша пароля админа, запуск PHP-FPM
- [x] `db/postgres/init/01-schema.sql` — полная PostgreSQL-схема (307 строк, все таблицы + seed-данные)
- [x] `.env` / `.env.example` — переменные окружения для Docker

#### PostgreSQL-миграция (код)
- [x] `Database.php` — динамический DSN (pgsql/mysql) через DB_DRIVER
- [x] `config/config.php` — все константы читаются из env с fallback (дефолты под Docker, PostgreSQL-only)
- [x] `UserPreference.php` — `ON DUPLICATE KEY` → `ON CONFLICT DO UPDATE`
- [x] `FinSetting.php` — `ON DUPLICATE KEY` → `ON CONFLICT DO UPDATE`
- [x] `FinTransaction.php` — убраны backtick-кавычки, `LIMIT a,b` → `LIMIT b OFFSET a`
- [x] `AppLog.php` — убраны backtick-кавычки, `LIMIT a,b` → `LIMIT b OFFSET a`
- [x] `index.php` — убран редирект на установщик, install.lock создаётся автоматически

#### Настройка reverse proxy (nginx-selfsteal)
- [x] На сервере стоит nginx-selfsteal (network_mode: host) для Reality ноды
- [x] CMS поднята на отдельном IP `85.198.99.102` через reverse proxy
- [x] Конфиг: `/opt/nginx-selfsteal/conf.d/cms.conf`
- [x] HTTP (порт 80) → HTTPS редирект
- [x] HTTPS (порт 443) → proxy_pass 127.0.0.1:3000 → hexacms_web

#### HTTPS
- [x] Выпущен сертификат Let's Encrypt для `hexaveil.xyz`
- [x] Авто-обновление через cron (docker + certbot)

#### Использование

```bash
# Запуск
docker compose up --build -d

# Админка
open http://localhost/admin        # admn / Cke;bkb2Njdfhbof
```

#### Если решено переезжать на Laravel
Оценивается, когда:
- Появляются задачи с очередями (email-рассылки, webhooks)
- Количество моделей превышает 15–20
- Начинают требоваться события/слушатели/уведомления
- Размер кодовой базы начинает тормозить добавление нового функционала

План переезда:
- [ ] Laravel установка + настройка PostgreSQL
- [ ] Перенос маршрутов → Laravel routes
- [ ] Перенос моделей → Eloquent ORM
- [ ] Перенос шаблонов → Blade
- [ ] Перенос админки → Blade + Livewire (или оставить server-rendered)
- [ ] Подключение Spatie-пакетов (sitemap, seo, permissions)
- [ ] Перенос API-клиентов (Remnawave, бот, Platega) → Laravel services

---

## Ключевые паттерны и решения

### Добавление новой страницы

1. Добавить маршрут в `core/routes.php` (ДО catch-all `{slug}`)
2. Создать шаблон в `templates/themes/hexaveil/`
3. Стили — в `public/hexaveil/css/style.css`
4. Если нужно в навигации — добавить ссылку в `layouts/main.php`

### Обработка форм

```php
$router->post('admin/posts/store', function() {
    Auth::requireAdmin();
    if (!verify_csrf()) die('CSRF token invalid');
    $title = trim(Request::post('title', ''));
    // ... process & redirect
});
```

### Шаблонизатор

```php
$template = createTemplate();  // автоматически выбирает активную тему
$template->set('title', 'Заголовок');
$template->set('seo', ['title' => '...', 'description' => '...']);
$template->set('menuItems', loadMenuItems('main', 'current-slug'));
$template->set('footerMenu', loadFooterMenu());
$template->setLayout('layouts/main');
$template->display('template-name'); // templates/themes/{theme}/template-name.php
```

### Тема HexaVeil — дизайн-токены (CSS-переменные)

```css
--bg-primary: #0a0a1a;        /* основной фон */
--bg-glass: rgba(24,24,27,0.6); /* glass-карточки */
--accent-primary: #a855f7;     /* purple (кнопки, ссылки) */
--accent-glow: rgba(168,85,247,0.4); /* свечение */
--text-primary: #fafafa;
--text-secondary: #a1a1aa;
--border-color: rgba(168,85,247,0.2);
--font-heading: 'Noto Serif', Georgia, serif;
--font-body: 'Inter', system-ui, sans-serif;
```

### Админ-панель — дизайн-токены

```css
--bg-base: hsl(222 22% 8%);        /* фон */
--bg-surface: hsl(222 18% 12%);   /* поверхности */
--glass-bg: hsla(222 18% 18% / 0.4); /* glassmorphism */
--accent: hsl(239 84% 67%);       /* акцент (по умолчанию Obsidian) */
--text-primary: hsl(210 17% 92%);
--text-secondary: hsl(215 14% 65%);
```

---

## Как запустить

### Production (сервер, 26.09.2026)

```bash
# Сайт: https://hexaveil.xyz
# Админка: https://hexaveil.xyz/admin/  (admn / Cke;bkb2Njdfhbof)
```

**Архитектура сервера:**
- nginx-selfsteal (`network_mode: host`, порты 80/443) — reverse proxy для CMS + selfsteal для Reality ноды
- hexacms_web (Nginx, порт 127.0.0.1:3000) — FastCGI
- hexacms_app (PHP 8.1-FPM) — обработка PHP
- hexacms_db (PostgreSQL 16) — база данных

### Docker (локальная разработка)

```bash
docker compose up --build -d
# Сайт: http://localhost
# Админка: http://localhost/admin  (admn / Cke;bkb2Njdfhbof)
```

### Синхронизация БД с production

После деплоя новой версии кода на сервер локальную БД можно обновить дампом с прода:

```bash
# Дамп с сервера:
ssh -p 356 ImCrazyMonk@85.198.99.102 \
  "cd /opt/HexaVeil_CMS && docker compose exec db pg_dump -U cms -d cms \
  --data-only --column-inserts --exclude-table=app_logs --disable-triggers" \
  > db/prod_data.sql

# Очистка локальных таблиц и импорт:
docker compose exec -T db psql -U cms -d cms -c "SET session_replication_role = 'replica';"
docker compose exec -T db psql -U cms -d cms -c "TRUNCATE users, posts, categories, tags, post_tags, comments, pages, media, menus, menu_items, widgets, settings, fin_transactions, fin_settings, user_preferences RESTART IDENTITY CASCADE;"
Get-Content db/prod_data.sql | docker compose exec -T db psql -U cms -d cms
docker compose exec -T db psql -U cms -d cms -c "SET session_replication_role = 'origin';"
# Сбросить пароль администратора (если импортирован плейсхолдер):

docker compose exec app php -r "\$pdo = new PDO('pgsql:host=db;port=5432;dbname=cms','cms','cms_secret_2026'); \$pdo->prepare('UPDATE users SET password=? WHERE login=?')->execute([password_hash('Cke;bkb2Njdfhbof',PASSWORD_BCRYPT),'admn']); echo 'done';"
```

---

## 🎯 React CMS Admin — новая архитектура (план)

> **Статус:** план. К реализации не приступали.

### Цель

Перенести PHP-рендереную админ-панель на **React SPA** с **визуалом 1:1 как в Remnawave-admin** (React + Tailwind + Radix UI).

### Архитектура (гибрид)

```
hexaveil.xyz (один сервер, один Docker-контейнер)
  │
  ├── /*                   → PHP (публичная часть: лендинг + блог) — НЕ ТРОГАЕТСЯ
  │
  ├── /cms-admin/          → React SPA (новая админка, Vite + React 18 + TypeScript)
  │     └── API calls → /api/* → PHP JSON-эндпоинты
  │
  └── /api/*               → PHP (JWT-аутентификация, JSON-ответы)
```

### Что копируется из Remnawave-admin-main

| Компонент | Откуда | Что меняется |
|-----------|--------|-------------|
| Layout (sidebar + header + mesh-фон) | `remnawave-admin/.../layout/` | Навигация под CMS |
| 23 UI-компонента (button, table, card...) | `remnawave-admin/.../ui/` | Без изменений |
| Система тем (5 пресетов + dark/light) | `remnawave-admin/.../useAppearanceStore.ts` | Ключ localStorage |
| Command Palette (Ctrl+K) | `remnawave-admin/.../CommandPalette.tsx` | Поиск по страницам CMS |
| Auth (JWT) | `remnawave-admin/.../authStore.ts` | Адаптирован под PHP |
| API-клиент (axios) | `remnawave-admin/.../api/client.ts` | baseURL = '/' |

### Стратегия миграции (страница за страницей)

1. **JWT Auth** (PHP) — новый эндпоинт `/api/auth/login`, middleware
2. **Login** (React) — форма входа, authStore
3. **Dashboard** (React + PHP API) — статистика, 4 glass-карточки
4. **Posts** + **Categories** (React + PHP API) — DataGrid, CRUD
5. **Post Form** (React) — CKEditor 5, title, status
6. **Pages** (React + PHP API)
7. **Users** (React + PHP API)
8. **Media** (React + PHP API)
9. **Finance** (React + PHP API)
10. **Settings** (React + PHP API)
11. **Nginx cutover** — `/admin` → React (когда всё готово)

### Размещение

- React-сборка (Vite build) → `public/cms-admin/`
- Nginx: `/cms-admin/*` → статика React
- PHP: `/api/*` → JSON-эндпоинты
- Оба сервиса в **одном Docker-контейнере** (`hexacms_web`)

### Проект React

```
cms-admin/                          # Новый React SPA
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── src/
│   ├── App.tsx                     # Роутинг
│   ├── main.tsx                    # Entry point
│   ├── index.css                   # Tailwind + CSS variables
│   ├── api/
│   │   ├── client.ts               # Axios + JWT interceptor
│   │   ├── auth.ts
│   │   ├── posts.ts
│   │   ├── pages.ts
│   │   ├── users.ts
│   │   ├── media.ts
│   │   ├── finance.ts
│   │   ├── settings.ts
│   │   ├── dashboard.ts
│   │   └── categories.ts
│   ├── store/
│   │   ├── authStore.ts            # JWT (Zustand + localStorage)
│   │   └── appearanceStore.ts      # Темизация
│   ├── config/
│   │   └── navigation.ts           # Навигация CMS
│   ├── components/
│   │   ├── layout/                 # Layout, Sidebar, Header
│   │   └── ui/                     # 23 Radix UI-компонента
│   └── pages/                      # Страницы админки
│       ├── Login.tsx
│       ├── Dashboard.tsx
│       ├── posts/
│       ├── pages/
│       ├── users/
│       ├── media/
│       ├── finance/
│       └── settings/
```

### Планирование (ссылка на план)

Полное ТЗ миграции — `docs/MIGRATION_TO_REMNAWAVE_STACK.md`
Текущий статус (что сделано / что осталось, handoff) — `docs/MIGRATION_STATUS.md`

---

## Технические ограничения

- **Никаких npm/сборщиков на PHP-стороне** — весь код vanilla
- React-админка использует npm (Vite + TypeScript) — это ок, она отдельный проект
- **Избегать монолитных файлов** — разделять на логические модули
- **Не трогать публичную часть** (если задача только про админку)
- **Не менять маршруты/контроллеры/логику/имена полей форм** без необходимости
- **PHP 8.1+**
- **Не коммитить папку `Fin/`**
- **React-админка:** `cms-admin/` использует npm (Vite + TypeScript) — это отдельный проект, не влияет на PHP-сторону

---

---

# ════════════════════════════════════════
# НОВЫЕ СЕКЦИИ — инфраструктура нод + Bedolaga
# ════════════════════════════════════════

---

# * * * ВНИМАНИЕ * * *
# Секции ниже добавлены при объединении с проектом «Заглушка»
# (C:\Users\Andre\Desktop\VPN\Заглушка) — инфраструктура нод,
# панель, бот, кабинет Bedolaga. Содержат credentials.
# НЕ КОММИТИТЬ с секретами.
# * * *

---

# 🖥 ИНФРАСТРУКТУРА НОД (Remnawave + Xray)

## Общая архитектура

```
Клиент (VLESS+Reality/Hysteria2/XHTTP)
    │
    ▼
Нода (сервер, remnanode Docker)
    │  rw-core (Xray 26.7.28) на :443
    │  rw-node (агент) на :2222
    │  nginx-decoy на 127.0.0.1:9443 (fallback Reality)
    │
    ├──→ Панель Remnawave (144.31.156.172)
    │       ├── Управление нодами/пользователями
    │       ├── Bedolaga Bot (@HexaVeil_bot)
    │       └── Bedolaga Cabinet (cabinet.fortf.ru)
    │
    └──→ DNS-маршрутизация (сплит-туннель)
            ├── Российские сервисы → DIRECT
            ├── Telegram/Social/TikTok → VLESS_BALANCER
            ├── YouTube → RU_BALANCER
            ├── AI/Dev-tools → VLESS_BALANCER
            └── Остальное → VLESS_BALANCER / fallback HYSTERIA2
```

## Состав инфраструктуры (7 нод)

| Нода | IP | Роль | Протоколы | Decoy-страница |
|------|----|------|-----------|----------------|
| **files.monolist.art** | 144.31.96.78 | DE-origin, CDN-релей | VLESS+Reality | Файловый конвертер |
| **audio.monolist.art** | 31.77.128.251 | FI | VLESS+Reality | Аудио-конвертер |
| **photo.monolist.art** | 31.77.146.75 | NL | VLESS+Reality + Hysteria2 | Фото/фильтры |
| **video.monolist.art** | 159.194.221.84 | RU (Beget) | VLESS+Reality | Видео-конвертер |
| **data.monolist.art** | 162.217.248.186 | US (RemnaSetup) | VLESS+Reality | Конвертер данных |
| **istra.pwrngers.ru** | 85.198.98.18 | VK CDN-релей | XHTTP (LTE БС) | — |
| **vps.zaqxs1.ru** | 155.212.131.4 | Yandex CDN-релей | XHTTP → files(DE) | — |

Панель Remnawave **3.4.3** («HexaVeil») на `panel.fortf.ru`.

---

## Панельный сервер — 144.31.156.172

- **Роль:** Remnawave-панель + Bedolaga-бот + админка + контрол Spectral/Happ
- **SSH:** порт **356**, user `kilo` / `kilorules123` (sudo). Сохранена учётка `ImCrazyMonk`/`Vjyr356jyr!`
- **Hostname:** `RemnaDashFin`. ОС Ubuntu 24.04
- **Docker-сервисы (все в `/opt/...`):**
  - `remnawave-panel` (+`-db`, `-redis`) — панель Remnawave
  - `remnawave-subscription-page`, `remnawave-web-frontend`, `remnawave-web-backend`
  - `remnawave_bot` (+`_db`, `_redis`) — Bedolaga v4.7.0, код `/opt/remnawave-bedolaga-telegram-bot`
  - Кабинет Bedolaga: **v1.71.0**, статика `/srv/cabinet`, источник `ghcr.io/bedolaga-dev/bedolaga-cabinet:latest`
  - `caddy-remnawave`: домены `panel.fortf.ru`, `bot.fortf.ru`, `cabinet.fortf.ru`, `admin.fortf.ru`
  - `remnawave-admin-bot-1`, `remnawave-admin-db`, `vpn_support_bot`

### Обновление панели и бота
- Апгрейд 04–06.09.2026: панель 2.8.0→3.4.3, бот 3.67.0→4.4.0
- Бот+кабинет 08.09.2026: 4.4.0→4.7.0 (+кабинет→1.71.0)
- Снапшот/откат: `/home/ImCrazyMonk/pre-update-20260904/` (+`rollback.sh`)
- **Правило:** при правках `.env` бота — пересоздавать контейнер (`--force-recreate`), простой `docker restart` env_file НЕ перечитывает
- v3 требует `APP_SECRET` (не `change_me`) — ставим = старому `JWT_AUTH_SECRET`

### Отложенные задачи:
- **Сменить дефолтный `POSTGRES_PASSWORD` БД бота** (`secure_password_123`) — отложено 08.09.2026

---

## Spectral / GhostOS (контрольный слой)

- Панель управления (Happ/Spectral) — на 144.31.156.172 («Master IP»)
- Аккаунт/license: `GHOST_ID=8ba4d3a41eab359c`, `GHOST_LIC=7b036dbf`
- Хосты: `sh.ghostos.space` (скрипты/шаблоны), `info.ghostos.space` (справка)
- Установочные скрипты:
  - `nk-f6.sh @ --nginx install` — ядро + nginx-decoy (GhostCloak 2.9.0)
  - `sc-decoy.sh` (env `GHOST_DECOY=convertit`, `GHOST_DECOY_NGINX=1`, `GHOST_DECOY_DOMAIN=<домен>`)
  - Менеджер decoy: `/usr/local/bin/selfsteal`
- Установка в неинтерактивном режиме требует `TERM=xterm-256color`

---

## Ноды — доступ, состав, особенности

**Общие правила:**
- SSH на **356** (кроме data: 22). Операционный пользователь: `kilo`/`kilorules123` (sudo+docker)
- Всё в контейнере **remnanode** (host-network, `remnawave/node:latest`, Xray 26.7.28)
- Конфиг: `/opt/remnanode/docker-compose.yml`
- Decoy-nginx: на files/audio/video — docker `nginx-selfsteal`; на photo/data — системный nginx
- **Грабли:** в контейнере remnanode обязан существовать `/var/log/remnanode/` (иначе ядро падает при старте). Лечение: `docker exec remnanode mkdir -p /var/log/remnanode`
- Reality: `serverNames` = decoy-домен, `target` = `127.0.0.1:9443`, `xver: 1`
- Decoy-сертификаты: LE через acme.sh, аккаунт-email `admin@monolist.art`
- ufw: ВКЛЮЧЁН на всех; открыты 80,443/tcp,443/udp,2222, ssh-порт, 4443, 8443, 8080. На data-ноде ufw НЕ настроен.

### files.monolist.art — 144.31.96.78 (DE-origin)
- Хостнейм `RemnanodeDE01`, DE. **Origin для CDN-цепочек** (на него PROXY-уходят zaqxs1-ноды)
- Decoy: docker `nginx-selfsteal`, страница `files/index.html`

### audio.monolist.art — 31.77.128.251
- Хостнейм `RemnaNODEFI01`, FI. Decoy: docker `nginx-selfsteal`

### photo.monolist.art — 31.77.146.75 (NL)
- Хостнейм `RemnanodeNL01`. **Decoy = системный nginx** (НЕ docker)
- **Hysteria2 активна** (UDP 443) — профиль `/opt/remnanode/hysteria2-config-profile.json`

### video.monolist.art — 159.194.221.84 (RU, Beget)
- Хостнейм `qvkhlqltsa`. Decoy: docker `nginx-selfsteal`

### data.monolist.art — 162.217.248.186 (US)
- Хостнейм `CLY787435`. Ubuntu 26.04, Docker 29.8.0. SSH **22**: `kilo` и `root`
- Установлена через **RemnaSetup** v2.5 (`/opt/remnasetup`)
- Decoy: системный nginx, сертификат certbot (ECDSA secp384r1)
- **TODO:** cron renewal для certbot НЕ настроен

### istra.pwrngers.ru — 85.198.98.18 (VK-Cloud)
- Роль: **VK CDN-релей** (xhttp, LTE БС). Inbound `VKCDN`, путь `/api/product/include` ✅ кастомный
- Host в панели: `LTE | БС | №1` (address `new.pwrngers.ru`, port 443, path `/api/product/include`)

### vps.zaqxs1.ru — 155.212.131.4
- Роль: **CDN-релей** (Yandex). Inbound `yandex-cdn-inbound01`
- **⚠️ XHTTP-путь `/uploadfiles/` — стандартный, запланирована смена**

---

## Порты (сводно)

| Порт | Что | Кто |
|------|-----|-----|
| 22 / 356 | SSH | sshd |
| 2222 | Агент rw-node, связь с панелью | ноды |
| 443/tcp | VLESS+Reality + HTTPS-decoys | rw-core (xray) |
| 443/udp | Hysteria2 (QUIC) — photo | rw-core |
| 80 | HTTP→HTTPS / ACME-challenge | nginx |
| 4443, 8443, 8080 | Доп. порты Spectral/CDN | по стеку |
| 9443 | Decoy-nginx (loopback, proxy_protocol) | nginx |
| /dev/shm/nginx.sock | unix-сокет nginx | nginx (host-core) |
| 3001 / 8080 / 2222 на панели | health панели / health бота / (node) | 144.31.156.172 |

---

## Типовые операции (чеклисты)

### Обновление remnanode на ноде
```bash
docker compose -f /opt/remnanode/docker-compose.yml pull remnanode
docker compose -f /opt/remnanode/docker-compose.yml up -d remnanode
docker exec remnanode mkdir -p /var/log/remnanode
# подождать ~60–70 c, проверить: ss -ltnp | grep ':443' ; decoy https = 200
```
На data-ноде шаг `docker exec mkdir` не нужен — `/var/log/remnanode` смонтирован с хоста.

### Установка decoy/selfsteal (GhostOS/nk-f6)
```bash
curl -sL https://sh.ghostos.space/spectral/u/8ba4d3a41eab359c/spectral/core/net/nk-f6.sh -o /tmp/nk-f6.sh
TERM=xterm-256color bash /tmp/nk-f6.sh @ --nginx --force --domain <ДОМЕН> install
# затем: docker exec remnanode mkdir -p /var/log/remnanode
# добавить TCP-листенер 127.0.0.1:9443 в conf.d selfsteal (для container-core)
# в панели Spectral: serverNames = <домен>, target = 127.0.0.1:9443, xver 1
```

### data-нода через RemnaSetup
```bash
DOMAIN=data.monolist.art MONITOR_PORT=9443 NODE_PORT=2222 SECRET_KEY='<key>' \
WEBSERVER=nginx USE_PROXY_PROTOCOL=y CERT_METHOD=2 LE_EMAIL=admin@monolist.art \
SKIP_WARP=true BBR_ANSWER=y NON_INTERACTIVE=true \
bash /opt/remnasetup/remnasetup.sh install-node
# после: заменить /var/www/site/index.html на decoy; nginx -t && systemctl reload nginx
# Reality: target 127.0.0.1:9443, xver 1
# ВАЖНО: cron renew для certbot добавить вручную
```

### Типовые неисправности и причины
- Нода не поднимается / ядро падает → чаще всего отсутствует `/var/log/remnanode`
- Decoy по https молчит → target в панели указывает на сокет, а ядро в контейнере → ставить `127.0.0.1:9443`
- acme.sh «invalidContact» → в `/root/.acme.sh/account.conf` битый email (домен `.local`) → заменить на `admin@monolist.art`
- YouTube «через Германию» → правило роутинга google→PROXY(files DE) — это норма
- Бот спамит `RemnaWaveConfigurationError` → в `.env` бота добавить `REMNAWAVE_API_URL=http://remnawave-panel:3000`
- `docker logs` бота «короткий» → полная история в `/opt/remnawave-bedolaga-telegram-bot/logs/bot.log`

### Смена домена на ноде
1. Поменять домен везде: nginx, `/etc/letsencrypt/live`, профили `/opt/remnanode/*-profile.json`
2. Перевыпустить LE на новый домен
3. В панели Spectral: Reality `serverNames` + все упоминания домена

---

## Ключевые пути/файлы (шпаргалка)

| Что | Где |
|-----|-----|
| compose ноды | `/opt/remnanode/docker-compose.yml` |
| access-лог (внутри контейнера!) | `/var/log/remnanode/` |
| docker-decoy (files/audio/video) | `/opt/nginx-selfsteal/` |
| системный decoy (photo) | `/etc/nginx/sites-available/decoy-9443`, root `/var/www/decoy` |
| системный decoy (data) | `/etc/nginx/conf.d/selfsteal.conf`, root `/var/www/site` |
| RemnaSetup (data) | `/opt/remnasetup/` |
| сертификаты acme.sh | `/root/.acme.sh/<домен>_ecc/` |
| сертификаты certbot | `/etc/letsencrypt/live/<домен>/` |
| профили протоколов на ноде | `/opt/remnanode/hysteria2-config-profile.json` |
| менеджер selfsteal | `/usr/local/bin/selfsteal` |
| панель .env / креды | `/opt/remnawave-panel/.env`, `/opt/remnawave-panel/admin-credentials.txt` |
| бот | `/opt/remnawave-bedolaga-telegram-bot` (.env там же) |
| полный лог бота | `/opt/remnawave-bedolaga-telegram-bot/logs/bot.log` |
| кабинет Bedolaga (статик) | `/srv/cabinet` |
| бэкап/откат панели | `/home/ImCrazyMonk/pre-update-20260904/` |
| MCP remnawave | `~/.config/kilo/kilo.json` (URL+токен panel.fortf.ru) |
| MCP ssh-mcp (ноды) | `~/.ssh/ssh-mcp-hosts.json` (8 нод) |
| исходники decoy-страниц | `C:\Users\Andre\Desktop\VPN\Заглушка\decoy\` |

---

## Доступы (сводка)

| Сервер | IP | SSH | Пользователь | Пароль |
|--------|----|-----|-------------|--------|
| Панель | 144.31.156.172 | 356 | kilo | kilorules123 |
| files | 144.31.96.78 | 356 | kilo | kilorules123 |
| audio | 31.77.128.251 | 356 | kilo | kilorules123 |
| photo | 31.77.146.75 | 356 | kilo | kilorules123 |
| video | 159.194.221.84 | 356 | kilo | kilorules123 |
| data | 162.217.248.186 | **22** | kilo (+ root) | kilorules123 / Vjyr356jyr! |
| istra.pwrngers.ru | 85.198.98.18 | 356 | kilo / ImCrazyMonk | kilorules123 / Vjyr356jyr! |
| vps.zaqxs1.ru | 155.212.131.4 | 356 | kilo | kilorules123 |

SSH-ключ: `~/.ssh/id_ed25519` (`kilo-ops@desktop`)

### OPSEC: XHTTP-пути
Каждый XHTTP-инбаунд должен иметь УНИКАЛЬНЫЙ, НЕОЧЕВИДНЫЙ путь:
| Нода | Профиль | Путь | Статус |
|------|---------|------|--------|
| VK-Cloud | `LTE_VK_BS_02` | `/api/product/include` | ✅ Кастомный |
| Yandex (vps.zaqxs1.ru) | — | `/uploadfiles/` | ⚠️ Запланирована смена |

---

---

# 🤖 BEDOLAGA BOT + CABINET — анализ и планы

## Состояние (2026-09-09)

| Способ входа | Статус | Детали |
|-------------|--------|--------|
| Telegram | ✅ | `@HexaVeil_bot`, Login Widget |
| Email | ✅ | Верификация обязательна |
| Google OAuth | ✅ | Единственный OAuth-провайдер |
| Яндекс | ❌ | В конфиге есть, `enabled:false` |
| Discord / VK | ❌ | В конфиге есть, `enabled:false` |
| Telegram OIDC | ❌ | Нет client_id |

## Функциональность связки (уже реализована в v4.7.0)

Бэкенд (бот, `/opt/remnawave-bedolaga-telegram-bot`):
- **Авторизация** (`auth.py`): Telegram (initData, Login Widget, OIDC), email (регистрация, логин, верификация, восстановление пароля), refresh, logout
- **OAuth** (`oauth.py`): Google, Яндекс, Discord, VK — авторизация и автопривязка
- **Привязка/отвязка** (`account_linking.py`): полные механики link/unlink для всех провайдеров, слияние (merge) аккаунтов, deep-link

Фронтенд (кабинет, `/srv/cabinet`):
- `/profile/accounts` — ConnectedAccounts: все провайдеры с кнопками привязать/отвязать
- `/merge/:mergeToken` — MergeAccounts: превью и слияние двух аккаунтов
- `/profile` — Profile: карточка-ссылка на `/profile/accounts`
- Dashboard `/` — компонент `uf` с приветствием, подписками, балансом, **условными баннерами**

**Вывод:** нужная механика УЖЕ полностью реализована. Не хватает заметности.

## План доработок кабинета

1. **Баннер-напоминание на главной** — если у пользователя ≤1 способ входа, показать dismissable-баннер с CTA на `/profile/accounts`
2. **Показ после регистрации** — «момент входа» (сессионный флаг `just_registered`)
3. **Включение Telegram OIDC** — если нужно, настройка client_id
4. **Включение Яндекс/Discord/VK** — credentials + redirect URI

## Локальная разработка кабинета
```bash
git clone https://github.com/BEDOLAGA-DEV/bedolaga-cabinet.git
cd bedolaga-cabinet
cp .env.example .env
# VITE_API_URL=/api, VITE_TELEGRAM_BOT_USERNAME=HexaVeil_bot
npm install
npm run dev  # dev-прокси → cabinet.fortf.ru
# после проверки: npm run build → deploy в /srv/cabinet
```

## Правила безопасности
- **На живом сервере — только чтение.** Любая запись — только с явного одобрения владельца
- Не поднимать второй бот на том же `BOT_TOKEN`
- Не давать локальному боту `REMNAWAVE_API_URL` прод-панели
- Тестовые действия — только тестовым аккаунтом
- Не коммитить секреты (`.env`, пароли, токены)

---

---

# 🔗 СВЯЗИ МЕЖДУ ПРОЕКТАМИ

| CMS NewWeb | Инфраструктура | Пояснение |
|------------|----------------|-----------|
| `hexaveil.xyz` | `panel.fortf.ru`, `cabinet.fortf.ru` | Единый бренд HexaVeil |
| 3D-глобус (координаты серверов) | Ноды monoList (DE, FI, NL, RU, US) | Визуализация локаций нод |
| `connectUrl` в 3D-глобусе → `cabinet.fortf.ru` | Bedolaga Cabinet | Пользователь с лендинга → в кабинет |
| `t.me/HexaVeil_bot` в ссылках | Bedolaga Bot `@HexaVeil_bot` | Единый Telegram-бот |
| IP `159.194.221.84` (нода на Beget) | video.monolist.art (RU-нода) | CMS и нода на одном сервере |
| nginx-selfsteal (reverse proxy для CMS) | decoy-nginx на нодах | Одинаковая схема nginx |
| Финансовый модуль (Platega/YooKassa) | Bedolaga (подписки/балансы) | В перспективе — объединение данных через API |
| `db/prod_data.sql` | Бэкапы панели в `/home/ImCrazyMonk/pre-update-*` | Разные БД, одна экосистема |

---

---

# 📁 Отдельная папка «Заглушка» — `C:\Users\Andre\Desktop\VPN\Заглушка`

Содержит параллельный проект управления инфраструктурой нод:

```
Заглушка/
├── docs/INFRASTRUCTURE.md       # Полная инфраструктурная сводка (пароли, IP, архитектура)
├── profiles/                    # Шаблоны конфигов Xray / подписок
│   ├── Autobalancer.json        # Балансировщик VLESS/Hysteria2 для клиентов
│   └── EU_Whitelist.json        # EU whitelist
├── decoy/                       # HTML-заглушки для нод
│   ├── index.html               # Главная студии
│   ├── files/index.html         # Файловый конвертер (DE)
│   ├── audio/index.html         # Аудио-конвертер (FI)
│   ├── photo/index.html         # Фото/фильтры (NL, Hysteria2)
│   ├── video/index.html         # Видео-конвертер (RU)
│   ├── data/index.html          # Конвертер данных (US)
│   ├── hash/index.html          # Хэши
│   └── qrcode/index.html        # QR-генератор
├── PROJECT.md                   # Описание проекта нод
├── AGENTS.md                    # Инструкции для агентов (стек Remnawave)
├── РАБОЧАЯ-СВОДКА-2026-09-09-Кабинет-Связка-Аккаунтов.md  # Полный анализ Bedolaga
├── _analysis_src/               # Копии исходников для анализа (read-only)
├── VPS_Security_Hardening_Menu.sh
└── rwa_plugin_live_flow-0.17.5-py3-none-any.whl
```

---

*Дата: 2026-09-27. При изменении инфраструктуры обновлять секции нод и доступов.*