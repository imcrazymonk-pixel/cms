# NewWeb CMS — Project Overview

## Что это за проект

Собственная **PHP CMS** (без фреймворков) поверх MySQL. Изначально — стандартный
блог-движок, сейчас превращается в **многофункциональный сайт VPN-сервиса**:

- **Публичная часть** — лендинг HexaVeil (тема `hexaveil`) с 3D-глобусом серверов,
  тарифами, FAQ и **блогом** (добавлено недавно, см. `/blog`)
- **Админ-панель** — собственная система управления контентом с редизайном в стиле
  remnawave (тёмная тема, mesh-фон, glass-эффекты, командная палитра)

### Домен и окружение

- **Docker**: `http://localhost` (PHP 8.1 + Nginx + PostgreSQL 16)
- **Локально**: `http://hexacms` (Open Server Panel, Apache + MySQL)
- Поддержка MySQL и PostgreSQL через `DB_DRIVER` в config.php

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
│   ├── Database.php       # PDO-обёртка
│   ├── Post.php           # Модель постов (CRUD, категории, теги, комменты)
│   ├── Category.php       # Модель категорий
│   ├── Page.php           # Модель страниц
│   ├── User.php           # Модель пользователей
│   ├── Auth.php           # Аутентификация (admin)
│   ├── helpers.php        # Утилиты (truncate, format_date, createTemplate)
│   ├── helpers_icons.php  # Inline Lucide SVG-иконки (icon())
│   ├── DataGrid.php       # Рендерер таблиц для списков админки
│   └── Autoloader.php     # PSR-4 автозагрузка
├── admin/                 # Админ-панель
│   ├── controllers/       # Контроллеры (Posts, Pages, Categories, Media, etc.)
│   ├── templates/         # PHP-шаблоны (layouts/main, posts/form, login, etc.)
│   ├── js/panel.js        # JS панели (настройки вида, DataGrid, превью)
│   └── js/command-palette.js # Командная палитра (Ctrl+K)
├── templates/
│   └── themes/
│       ├── hexaveil/      # АКТИВНАЯ ТЕМА — VPN лендинг + блог
│       ├── modern/        # Запасная блог-тема
│       ├── minimal/       # Запасная блог-тема
│       └── default/       # Базовая блог-тема
├── public/
│   ├── hexaveil/          # CSS/JS/ассеты темы HexaVeil
│   │   └── css/
│   │       ├── variables.css  # CSS-переменные (цвета, шрифты)
│   │       ├── global.css     # Глобальные стили (контейнер, кнопки, типографика)
│   │       └── style.css      # Стили секций + БЛОГ (добавлено недавно)
│   └── css/panel/         # Дизайн-система админки (7 файлов)
├── db/
│   ├── postgres/init/     # PostgreSQL авто-инициализация
│   │   └── 01-schema.sql  # Полная схема БД (PG)
│   └── migrations/        # MySQL-миграции (legacy)
├── database.sql           # MySQL схема (legacy)
└── docs/decisions/
    └── ADR-001-panel-design-system.md  # Документация редизайна админки
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
- [x] Inline Lucide SVG-иконки (icon())

#### Блог
- [x] Таблицы: posts, categories, tags, post_tags, comments (MySQL)
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

#### Технические исправления
- [x] **Удалены остатки Nova VPN** — ссылка `t.me/nova_vpn` заменена на `t.me/HexaVeil_bot` в theme.php и layouts/main.php

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
- [ ] **Поиск по постам** — MySQL FULLTEXT, строка поиска, результаты
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

> **Статус: выполнено (26.09.2026).** Проект полностью контейнеризирован и работает на PostgreSQL.

#### Docker-инфраструктура
- [x] `Dockerfile` — PHP 8.1-FPM (alpine) с pdo_pgsql, pdo_mysql, intl, mbstring, opcache
- [x] `docker-compose.yml` — 3 сервиса: app (PHP-FPM), web (Nginx), db (PostgreSQL 16)
- [x] `.docker/nginx/default.conf` — Nginx vhost с deny доступа к служебным директориям
- [x] `.docker/php/php.ini` — upload 64M, memory 256M, opcache
- [x] `docker-entrypoint.sh` — ожидание PG, создание install.lock, запуск PHP-FPM
- [x] `db/postgres/init/01-schema.sql` — полная PostgreSQL-схема (307 строк, все таблицы + seed-данные)
- [x] `.env` / `.env.example` — переменные окружения для Docker

#### PostgreSQL-миграция (код)
- [x] `Database.php` — динамический DSN (pgsql/mysql) через DB_DRIVER
- [x] `config/config.php` — все константы читаются из env с fallback
- [x] `UserPreference.php` — `ON DUPLICATE KEY` → `ON CONFLICT DO UPDATE`
- [x] `FinSetting.php` — `ON DUPLICATE KEY` → `ON CONFLICT DO UPDATE`
- [x] `FinTransaction.php` — убраны backtick-кавычки, `LIMIT a,b` → `LIMIT b OFFSET a`
- [x] `AppLog.php` — убраны backtick-кавычки, `LIMIT a,b` → `LIMIT b OFFSET a`
- [x] `index.php` — убран редирект на установщик, install.lock создаётся автоматически

#### Установщик
- [x] Убран редирект на `/install/` — в Docker приложение стартует сразу
- [x] `install.lock` удалён из `.gitignore` для config.php (теперь это универсальный шаблон)

#### Использование

```bash
# Запуск
docker compose up --build -d

# Админка
open http://localhost/admin        # admin / admin12345
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

### Docker (рекомендуется)

```bash
docker compose up --build -d
# Сайт: http://localhost
# Админка: http://localhost/admin  (admin / admin12345)
```

### Локальная разработка (Open Server Panel)

Проект также работает на **Open Server Panel**:
- Домен: `http://hexacms`
- Админка: `http://hexacms/admin`
- Логин: `admin`
- Пароль: `admin12345`
- MySQL: `127.127.126.26`, БД: `cms`

Обычная установка:
1. Скопировать файлы в `C:\OSPanel\home\HexaCMS\public\`
2. Импортировать `database.sql` в MySQL
3. Создать `install.lock` в корне проекта
4. Настроить `config/config.php` (или использовать переменные окружения)
5. Открыть `http://hexacms` в браузере

---

## Технические ограничения

- **Никаких npm/сборщиков** — весь код vanilla
- **Избегать монолитных файлов** — разделять на логические модули
- **Не трогать публичную часть** (если задача только про админку)
- **Не менять маршруты/контроллеры/логику/имена полей форм** без необходимости
- **PHP 7.4+** для совместимости с OSPanel
- **Не коммитить папку `Fin/`**