# 🔬 HexaVeil CMS — Техническая история (14.09.2026 → 11.10.2026)

> Техническая хронология всех работ по CMS с хэшами коммитов, статистикой
> изменений, затронутыми файлами и архитектурными решениями.
> Лента в «человеческом» формате — `docs/CHANGELOG_CMS.md`.

---

## 0. Сводка

| Метрика | Значение |
|---|---|
| Коммитов (с 14.09) | **100** (95 содержательных + 5 merge) |
| Автор | ImCrazyMonk (деплой-мержи: `deploy`, `root`) |
| Затронуто файлов | ~3 107 |
| Вставлено строк | ~88 701 |
| Удалено строк | ~50 539 |
| Сентябрь | 45 коммитов |
| Октябрь | 55 коммитов |
| Ветки | `main` (активная), `feat/panel-redesign` (пуста — не содержит уникальных коммитов) |

**Главная линия эволюции:**

```
PHP-админка (MySQL) → Docker + PostgreSQL → React SPA (копия Remnawave 1:1)
                      → FastAPI-бэкенд (M0→M7) → PHP только публичный сайт
                      → web/frontend + web/backend (Remnawave layout)
                      → Bedolaga-интеграция (прокси + БД бота)
```

**Границы периода:** до 14.09 существовали Finance-модуль (с 28.08, Platega, bulk actions), логи, TinyMCE 7, ремаппинг сайдбара (commit `f3ed494` от 13.09).

---

## 1. Фаза A — Визуальный редизайн панели (15.09)

**15.09.2026**

| Хэш | Время | Сообщение | Файлов | +/- |
|---|---|---|---|---|
| `eae9fb1` | 15:40 | checkpoint перед визуальным оверхаулом — AGENTS.md pipeline, PROJECT.md audit, categories под posts, SEO plan, nova cleanup | 25 | +2402/−134 |
| `91cecdc` | 15:42 | docs: визуальный аудит в roadmap Phase 1 (PROJECT.md) | 1 | +29 |
| `58663f7` | 19:15 | **feat: visual refactoring complete — glass, chart, datagrid, header, theme previews, radius tokens** | 15 | +829/−127 |

**Детали `eae9fb1`:**
- `AGENTS.md` (+пайплайн агентов overseer/vision/coder/thinker — появился в этот период)
- `PROJECT.md` +409 — полный аудит проекта
- `admin/templates/posts/categories.php` +124 — категории под «Посты»
- `admin/controllers/PostsController.php` +117 — новый контроллер категорий
- `templates/themes/hexaveil/` — тема: `index.php` +56, layouts/main.php +70, theme.php +14
- `public/hexaveil/css/style.css` +496 — стили темы
- `sql/migrate_panel_ui_state.sql` +52 — миграция настроек вида панели (per-user, JSON-блоб)
- `core/routes.php` +33 — новые маршруты
- `public/hexaveil/js/star.js` — анимация

**Детали `58663f7` (редизайн):**
- `public/css/panel/` — переработаны 7 файлов:
  - `components.css` +193/−18 (glass-карточки, формы, кнопки)
  - `table.css` +142/−3 (DataGrid-стили)
  - `layout.css` +66/−7 (хедер, навигация)
  - `finance.css` +71/−15 (графики, KPI)
  - `base.css`, `themes.css`, `tokens.css` (radius-токены `--radius-*`)
- `core/DataGrid.php` +157/−13 — компонент таблиц
- `admin/js/finance/chart.js` +115 — новый график
- `admin/templates/theme/index.php` +93 — превью тем
- `CHANGELOG_visual_refactor.txt` +56 (удалён позже, в `22a14e5`)

---

## 2. Фаза B — Редактор постов v2 (16.09)

**16.09.2026 — 18 коммитов (самый плотный день).**

| Хэш | Время | Сообщение | Файлов | +/- |
|---|---|---|---|---|
| `fe3b548` | 10:39 | pre-merge checkpoint — deploy scripts, chart fix, template engine, icon helpers, panel CSS | 9 | +251/−23 |
| `9be23a1` | 11:49 | **feat: новый редактор постов v2** | 8 | +1446/−1 |
| `f2e367a` | 12:07 | fix: глобальный `.hidden` класс в base.css (модалки были всегда видны) | 1 | +3 |
| `f52ad64` | 12:37 | fix: status select, glass-карточка сайдбара, топбар-кнопки, шире редактор | 3 | +181/−168 |
| `510e3f6` | 13:47 | fix: удалён орфанный мёртвый код editor.js (SyntaxError → onclick undefined) | 1 | −9 |
| `a72aba6` | 15:35 | refactor: дропдаун draft/publish, glass-обёртка, стандартные кнопки | 1 | +90/−191 |
| `7c2496c` | 19:41 | chore: .gitignore корневые .txt (временные заметки) | 1 | +3 |
| `fe15fd9` | 19:39 | fix: post-content стили блога (абзацы/списки/заголовки — не было отступов) | 1 | +114 |
| `fd07ff1` | 19:53 | refactor: сайдбар на panel-sidebar glass, 360px, табы, top-aligned | 2 | +65/−86 |
| `f2f8c64` | 20:24 | refactor: radius-токены карточки, убран статус-селект, архив в дропдаун | 4 | +36/−33 |
| `70cbd4a` | 20:38 | fix: glass-карточка overflow hidden, padding, выравнивание, фикс SEO-оверфлоу | 2 | +35/−75 |
| `922dded` | 20:50 | fix: видимые границы полей, табы как в сайдбаре, заметный select категории | 2 | +26/−21 |
| `4e31a78` | 21:22 | fix: нижние границы полей, табы 1:1 с сайдбаром | 1 | +14/−10 |
| `51e3b2f` | 21:29 | fix: индивидуальные border-свойства (border:none подавлял border-bottom) | 1 | +4/−4 |
| `75f144a` | 21:45 | fix: editor.css только на ВАЛИДНЫХ CSS-переменных панели | 1 | +85/−94 |
| `13f0d52` | 21:57 | feat: /admin/posts/edit/{id} → новый редактор v2 (editor.php) | 1 | +2/−2 |
| `8135224` | 22:01 | chore: ссылка «Редактор v2» убрана из сайдбара | 1 | −1 |

**Новые файлы редактора (`9be23a1`):**
- `admin/js/editor.js` +568 — логика (WYSIWYG, вкладки, SEO, tags, AI, publish modal)
- `admin/templates/posts/editor.php` +389 — разметка
- `admin/controllers/PostsController.php` +187 — сохранение/загрузка поста
- `public/css/panel/editor.css` +270 — стили
- `core/helpers_icons.php` +23 — новые lucide-иконки
- `core/routes.php` +7 — маршруты редактора

**Скрипты деплоя (`fe3b548`):** `_deploy.bat` +72, `_deploy.ps1` +111, `_deploy_list.txt` +50 — ручной SFTP-деплой (заменён позже на `deploy.sh`).

---

## 3. Фаза C — Docker + PostgreSQL (26.09)

**26.09.2026**

| Хэш | Время | Сообщение | Файлов | +/- |
|---|---|---|---|---|
| `17768a4` | 03:45 | **feat: Docker + PostgreSQL migration** | 20 | +1049/−426 |
| `1bb74a3` | 03:47 | fix: postgresql-dev (сборка pdo_pgsql) | 1 | +6 |
| `0239d42` | 03:52 | fix: debian-based PHP-образ (быстрее компиляция) | 1 | +11/−16 |
| `f589d06` | 03:59 | fix: libonig-dev (mbstring) | 1 | +2/−1 |
| `a389b8c` | 04:09 | fix: postgresql-client в Dockerfile, убран composer | 1 | +1/−2 |
| `a7598ea` | 12:03 | docs: PROJECT.md — прод-статус | 1 | +50/−13 |

**Детали `17768a4`:**
- `Dockerfile` +30 — PHP 8.1-FPM
- `docker-compose.yml` +59, `docker-compose.prod.yml` +94
- `.docker/nginx/default.conf` +37, `.docker/php/php.ini` +12
- `db/postgres/init/01-schema.sql` +307 — полная схема PostgreSQL
- `core/Database.php` — PDO → pgsql; модели AppLog/FinSetting/FinTransaction/UserPreference адаптированы
- `config/config.php` +48 — env-aware
- `DEPLOY.md` +170, README переписан (−526/+52), PROJECT.md +84
- `docker-entrypoint.sh` +20

---

## 4. Фаза D — Финансы, логи (Docker/Loki), Users, прод (27.09)

**27.09.2026**

| Хэш | Время | Сообщение | Файлов | +/- |
|---|---|---|---|---|
| `a2b8dc4` | 14:58 | fix: finance sequence sync, PG insert quoting, error logging + YooKassa/Platega | 28 | +2909/−221 |
| `935c86e` | 23:27 | **feat: Docker/Loki лог-сервисы, Users CRUD, settings/logs UI, DB-миграции** | 33 | +2595/−380 |
| `d592e98` | 23:27 | (дубль того же коммита) | 33 | +2586/−380 |
| `bb3d80f` | 23:46 | fix: test.hexaveil.xyz → hexaveil.xyz, nginx CMS → 3000 | 3 | +10/−10 |
| `685bc77` | 23:54 | merge: resolve conflicts — accept pushed version | — | — |

**Детали `a2b8dc4` (финансы против прода):**
- `admin/controllers/FinanceController.php` +707 — синк, фильтры, агрегации
- `core/payments/YooKassaClient.php` +223 (новый) — платежи YooKassa
- `core/Crypto.php` +86 (новый) — шифрование секретов
- `db/migrations/2026-09-25-yookassa-integration.sql` +19
- `db/prod_data.sql` +876 — боевые данные
- `admin/templates/settings/index.php` +370 — настройки провайдеров
- `cms.conf` +40 — конфиг nginx CMS
- `core/Database.php`, `FinTransaction.php` — фиксы

**Детали `935c86e` (логи + юзеры):**
- `core/models/DockerLogService.php` +214 (новый) — логи контейнеров (SSH/exec)
- `core/models/LokiLogService.php` +215 (новый) — Loki API
- `admin/controllers/LogController.php` +197 — табы Docker/Loki + live-превью
- `admin/controllers/SettingsController.php` +88 — JSON-конфиги логов
- `admin/templates/logs/index.php` +345 — страница логов
- `admin/templates/users/form.php` +118 (новый), `UsersController.php` +38 — CRUD юзеров
- `core/models/AppLog.php` +128 — фильтры/пагинация/поиск
- `db/migrations/2026-09-27-app-logs-expand.sql` +32, `db/postgres/migrations/001-add-user-fields.sql` +36
- `public/css/panel/logs.css` +385
- `core/Auth.php` +21

**Прод (`bb3d80f`):** домен `hexaveil.xyz`, внутренний порт CMS 3000 (занят selfsteal на 80/443).

---

## 5. Фаза E — План React-миграции + прототип (28.09)

**28.09.2026 — 12 коммитов, ночная сессия.**

| Хэш | Время | Сообщение | Файлов | +/- |
|---|---|---|---|---|
| `7bfdfa9` | 03:21 | feat: план миграции + PROJECT.md | 1 | +17 |
| `d8859e9` | 03:22 | docs: план миграции (force-add, был gitignored) | 1 | +1378 |
| `ad80e28` | 03:32 | chore: удалён мусорный cms-admin (запутавшийся агент) | 54 | −7219 |
| `5a49cca` | 03:16 | docs: коррекция — копировать Remnawave 1:1, не изобретать | 1 | +65 |
| `2e1b4f0` | 03:59 | docs: детальная спека миграции (Login, Dashboard, all pages) | 1 | +315 |
| `f56a822` | 04:09 | docs: спека — Recharts, TanStack Query, Finance | 1 | +52/−12 |
| `f1aa1e7` | 02:07 | feat: Task 0 — JWT Auth API endpoint | 4 | +369/−1 |
| `3ab1cd8` | 02:14 | feat: Task 1 — React SPA scaffold (Vite+React+TS+Router+Login) | 29 | +2996 |
| `d0ec6b4` | 02:16 | feat: Task 2 — UI-компоненты (Button, Input, Card, Badge, DataGrid) | 6 | +356 |
| `f4186c3` | 02:24 | feat: Task 5 — Posts CRUD (PHP API + React List + Form) | 6 | +490/−1 |
| `3446bca` | 02:29 | feat: CRUD API categories/pages/users + Router PUT/DELETE | 2 | +186/−1 |
| `11db649` | 02:31 | feat: Categories/Pages/Users CRUD (React) | 9 | +494/−3 |
| `ae38291` | 03:01 | **feat: Remnawave visual 1:1 — CSS, UI, Layout, Login, все CRUD** | 32 | +4226/−1195 |
| `286a692` | 03:09 | feat: секции сайдбара (Контент/Внешний вид/Пользователи/Система) | 2 | +41/−20 |

**Примечания:**
- Прототип собран в `cms-admin/` (Task 0–5), затем удалён (`ad80e28`, −7219) как «мусорный»; с 05.10 пересобран заново под `admin-react/` с шadcn/ui.
- Из прототипа в финал перешли: подход 1:1, структура SPA, JWT-endpoint.

---

## 6. Фаза F — PHP API + React SPA (05.10)

**05.10.2026 — создан `admin-react/` (shadcn/ui, Remnawave-канон).**

| Хэш | Время | Сообщение | Файлов | +/- |
|---|---|---|---|---|
| `6b8b2cd` | 22:48 | **Phase 0 + Phase 1 (partial): PHP API endpoints + React SPA scaffolding** | 98 | +16132/−1 |
| `4a87b25` | 23:10 | Finance page (React) + fix vite proxy redirect loop + JWT bridge | 5 | +555/−54 |
| `2fc5b39` | 23:23 | Finance charts (recharts) + fix 500 error handling | 2 | +76/−34 |

**Детали `4a87b25` (Finance в React):**
- `admin-react/src/pages/Finance.tsx` +428: DataGrid (сортировка/фильтры/пагинация/массовое удаление), 4 KPI, модалка add/edit, таб графиков
- `core/routes.php` +72/−40: **JWT bridge** для `/admin/finance/api/*` (React-токен → PHP-сессия), `X-Requested-With`
- `vite.config.ts` +2: прокси только `/admin/finance/api` (иначе бесконечный redirect loop из-за конфликта `/admin`)
- `api/finance.ts` +97: отдельный `adminApi` (пустой baseURL — убрал двойной `/api`)
- Фикс дубликатов ключей в Sidebar (idx-based)

**Детали `2fc5b39`:**
- Recharts BarChart доход/расход по месяцам (ResponsiveContainer, CartesianGrid, Tooltip), сводная таблица
- Фикс краша при пустом фильтре месяцев (retry + safe access)

---

## 7. Фаза G — FastAPI M0→M7 (08.10)

**08.10.2026 — 17 коммитов, полный переезд бэкенда.**

| Хэш | Время | Сообщение | Файлов | +/- |
|---|---|---|---|---|
| `22a14e5` | 22:49 | fix: PHP API (router, jwt, CSRF), finance, settings, editor, media, uploads + docs | 61 | +17457/−2311 |
| `5a714c4` | 23:04 | **FastAPI M0–M2: scaffold, JWT auth, read-only (14 модулей)** | 36 | +1769/−2 |
| `662ce3b` | 23:11 | **M3: write-endpoints — полный CRUD + core-хелперы** | 19 | +934/−78 |
| `259362c` | 23:17 | M4: cutover verified — 25 e2e, JWT interop, фикс asyncpg datetime + pages.status | 8 | +54/−9 |
| `8d2aee2` | 23:18 | M5: PHP /api/* DEPRECATED | 2 | +8/−4 |
| `c3013fb` | 23:21 | docs: браузерный E2E подтверждён | 1 | +8 |
| `a0bd643` | 23:22 | **M6 partial: Remnawave-style structlog (+rotating JSON), req-logging middleware** | 3 | +127/−2 |
| `c3a6ea2` | 23:31 | docs: все 15 секций админки против FastAPI (prod untouched) | 1 | +22/−7 |
| `83ad7aa` | 23:34 | docs: UI write-пути verified (посты/настройки/темы/медиа) — 200 | 1 | +9 |
| `aaaa3bb` | 23:49 | **M7: Finance core + Crypto + Diagnostics + Preferences → FastAPI** | 16 | +1305/−16 |
| `028f60d` | 23:55 | **M7 complete: Platega + YooKassa sync → FastAPI (live-verified). PHP = только публичный сайт** | 5 | +785/−10 |

**Детали `5a714c4` (M0–M2), ключевые файлы:**
- `backend/` — новый каталог (FastAPI):
  - `main.py` +194: app, CORS, middleware, lifespan
  - `api/deps.py` +115 (JWT-зависимости), `api/v1/` — 14 роутеров: auth, categories, dashboard, logs, media, menus, notifications, pages, posts, settings, themes, users, widgets
  - `core/`: config.py +75 (pydantic-settings), database.py +72 (asyncpg), security.py +80 (JWT, совместимость с PHP), errors.py +82, serializers.py +46, theme_config.py +137 (парсинг theme.php)
  - `schemas/` (auth, common), `tests/` (conftest, test_auth, test_read_endpoints)
- `docker-compose.yml` +15: сервис api

**Детали `662ce3b` (M3):** write-эндпоинты CRUD (posts/categories/pages/users/widgets/menus/settings/themes/notifications/media) + `core/db_helpers.py`, `core/slug.py`.

**Детали `259362c` (M4):** cutover — 25 e2e smoke-тестов, JWT interop PHP↔FastAPI (один и тот же секрет), фикс asyncpg datetime, миграция `pages.status`.

**Детали `028f60d` (M7 complete):** `api/v1/finance_payments.py` — синк Platega/YooKassa на FastAPI, проверено на проде. PHP остался только для публичного сайта.

**Детали `22a14e5`:**
- Полный пакет React-страниц admin-react (все страницы обновлены: PostsList +294, PostEdit +601, Finance +560, Diagnostics +577, LogsViewer +484, Settings +410, ThemeManager +116…)
- `core/Router.php` +10, `core/routes.php` +221 (JWT bridge, admin-api)
- `core/models/Post.php` +28 (SEO/featured), `FinTransaction.php` +13
- Миграции: `2026-10-08-posts-metadata.sql` +7, `2026-10-08-pages-status.sql`, `2026-10-08-fix-sequences.sql` +14
- Занесён `IMG_2468.heic` (случайно) — позже в .gitignore

---

## 8. Фаза H — Прод Phase 2, чистка, web/-структура, Настройки (09.10)

**09.10.2026 — 21 коммит.**

| Хэш | Время | Сообщение | Файлов | +/- |
|---|---|---|---|---|
| `fd9afd6` | 00:10 | Step 1 — disable legacy PHP admin (nginx /admin/logout → 302, index.php guard 404 /admin/* и /api/*) | 3 | +24/−1 |
| `db7dc05` | 00:21 | chore(prod): FastAPI api-сервис в docker-compose.prod.yml | 1 | +27 |
| `26e83cd` | 00:37 | merge origin/main (root) | — | — |
| `27b854a` | 00:56 | **feat: git pull-and-run deploy + удаление PHP-админки (Phase 2 complete)** | 121 | +1009/−13843 |
| `5d34c52` | 00:57 | merge origin/main (deploy) | — | — |
| `c8ab0fb` | 00:57 | fix(deploy): не source'ить .env (пробелы в значениях); DB creds через grep | 1 | +13/−17 |
| `757532f` | 02:03 | chore: удалён мёртвый PHP-код после миграции | 33 | +1/−4449 |
| `d41d7dc` | 02:05 | chore(db): удалены MySQL-миграции и разовые импорт-скрипты | 13 | −974 |
| `4d42478` | 22:37 | **chore: restructure admin как web/frontend + web/backend (Remnawave layout)** | 277 | +2258/−2366 |
| `3a77427` | 23:05 | **feat(admin): Phase 0 settings — branding, dynamic themes, change password** | 84 | +941/−333 |
| `85e196b` | 23:12 | **feat(settings): registry-driven — sources, reset, autosave; collapse по умолчанию** | 72 | +811/−438 |
| `55b2135` | 23:14 | feat(settings): поиск по настройкам + легенда источников | 66 | +174/−112 |
| `060a04f` | 23:23 | feat(settings): SEO таб + тема с группировкой; сайт-настройки в <head> | 71 | +277/−135 |
| `bd5ff7e` | 23:24 | feat(settings): Enter-to-save для текста; автосейв темы на blur/select | 64 | +145/−120 |
| `bcfc432` | 23:29 | refactor(theme): theme.php — единый источник истины опций темы | 3 | +250/−2 |
| `eb80e55` | 23:35 | feat(settings): финансовые настройки в реестре (секреты шифруются) | 71 | +319/−240 |
| `fdaac44` | 00:09 | feat(finance): восстановлен UI синка Platega/YooKassa (preview, import, sync now) | 73 | +417/−154 |
| `4519a1a` | 00:12 | merge origin/main (deploy) | — | — |
| `68f7f5a` | 00:24 | **feat(finance): in-app auto-sync scheduler для Platega/YooKassa** | 2 | +72 |
| `4cbf791` | 00:25 | merge prod-master | — | — |
| `1fc9d7f` | 00:27 | fix(compose): web healthcheck 127.0.0.1 (localhost → IPv6 ::1, nginx на IPv4) | 2 | +2/−2 |
| `8655c8e` | 00:33 | feat(admin): коллапсируемые Параметры/SEO в редакторе (свёрнуты по умолчанию) | 65 | +173/−127 |
| `6eb5ac1` | 10:08 | **docs: восстановлены 11 удалённых документов из git-истории** | 11 | +8549 |

**Детали `27b854a` (Phase 2 complete):**
- `deploy.sh` +47 (новый): `docker compose up -d --build` → идемпотентные миграции (4 SQL) → `nginx -s reload`
- Удалён весь `admin/` (−13 843): 13 контроллеров, 14 шаблонов, JS (editor.js, finance.js, panel.js, command-palette.js), CSS, .htaccess
- `docker-compose.prod.yml`: `CMS_HTTP_PORT` env; nginx conf dir-mount (без inode-ловушки), DB bound localhost
- `db/postgres/init/01-schema.sql`: базовые миграции включены (posts seo/featured, pages status, app_logs category/source)
- `admin-react/dist` закоммичен (на сервере нет Node)
- `.env.prod`: `CMS_HTTP_PORT=3000`

**Детали `4d42478` (restructure):**
- `admin-react/` → `web/frontend/` (dist коммитится), `backend/` → `web/backend/` (импорты `web.backend.*`)
- Добавлены 13 Pydantic-схем per-domain (`web/backend/schemas/*.py`): post, page, user, category, menu, widget, theme, setting, media, log, dashboard, finance, notification
- Добавлены lib-хуки: `clientLogger.ts`, `mutationToast.ts`, `useChartTheme.ts`, `useDeferredAction.ts`, `useOrderPreference.ts`, `useTabParam.ts`, `useUrlParam.ts`, `permissionStore.ts`, `types/models.ts`
- Удалены: `docs/MIGRATION_*.md` (3 шт.), `admin-react` — старый CommandPalette/MenuEdit (переписан)

**Детали `3a77427` (Phase 0 settings):**
- Backend: whitelist настроек (admin_title/browser_title/title_separator/favicon_url/admin_email/site_url/timezone/locale) + валидация; `GET /api/public/branding` (без аутентификации); `GET /api/themes` (скан `templates/themes/*/theme.php`); `POST /api/auth/change-password` (проверка текущего, мин. 8, bcrypt)
- Frontend: `BrandingProvider` + `useBrandingStore` (браузерный тайтл от branding), Settings → Remnawave-аккордеон (5 табов: Основные/Внешний вид/Безопасность/Финансы/Логи), блок смены пароля, убран `use_react_admin`

**Детали `85e196b` (registry):**
- `web/backend/core/settings_registry.py` (новый): декларативные настройки (type/category/tab/default/env override/options), резолв db/env/default
- API: `GET items+categories`, `PUT/DELETE /settings/{key}`
- UI: generic renderer, бейджи источника, reset, автосейв bool/select, per-field save текста, все секции свёрнуты

**Детали `6eb5ac1` (восстановление доков):** `docs/MIGRATION_BRIEF.md` (157), `MIGRATION_STATUS.md` (644), `MIGRATION_TO_REMNAWAVE_STACK.md` (816), `docs/superpowers/plans/` — cms-redesign (3056), panel-ui (1702), cms-react-migration (1378), correction-approach (65), `specs/` — 4 документа. Force-add через `-f` (путь в .gitignore).

---

## 9. Фаза I — Дашборд, виджеты, шрифты, Bedolaga (10.10)

**10.10.2026 — 18 коммитов.**

| Хэш | Время | Сообщение | Файлов | +/- |
|---|---|---|---|---|
| `66b5902` | 10:55 | fix(ui): StatCards в стиль Remnawave; тумблеры виджетов убраны из AppearancePanel | 80 | +449/−219 |
| `104e90a` | 13:06 | style(admin): шрифты Inter + JetBrains Mono вместо Montserrat / Fira Mono | 3 | +9/−5 |
| `56af18e` | 13:06 | docs: CONTRIBUTING.md — коммиты «что реально сделано» | 1 | +62 |
| `b829454` | 13:06 | **feat(sidebar): редактируемые внешние ссылки (GitHub/Telegram/Support) + панель в хедере** | 4 | +377 |
| `627e768` | 13:06 | **feat(dashboard): меню «Настроить», drag-виджеты, виджеты Финансы/Логи** | 4 | +533/−216 |
| `7a17709` | 13:06 | chore(build): пересборка SPA | 98 | +222/−218 |
| `71a2d8f` | 14:10 | Работа над дашбордом (useWidgetSize, ExtraWidgets) | 89 | +598/−270 |
| `af3c83b` | 19:42 | **feat(dashboard): единая статистика, «Подробнее», Доход/Расход, «Логи за сутки», «Последние логи», яркий график + фикс 404** | 4 | +354/−214 |
| `95df7f3` | 19:42 | chore(build): пересборка | 77 | +182/−187 |
| `7eb43a4` | 23:28 | **Подключение Bedolaga** | 127 | +6580/−1510 |
| `1721573` | 23:31 | Исправлена ошибка после внедрения Bedolaga | 1 | +1/−1 |

**Дашборд (`627e768` + `71a2d8f` + `af3c83b`):**
- `web/frontend/src/components/SortableSection.tsx` +73 (dnd-kit, перетаскивание)
- `useWidgetVisibility.ts` +50 (localStorage), `useWidgetSize.ts` +48 (полная/половина/треть)
- `components/dashboard/ExtraWidgets.tsx` +177→204 (FinanceChartWidget, LogsWidget, LogsRecentWidget)
- `pages/Dashboard.tsx` +449: DropdownMenu «Настроить», DndContext, кликабельные StatCard со ссылкой «Подробнее»; убран виджет «Активность»
- Backend: `api/v1/dashboard.py` +21, `api/v1/logs.py` +6 (фильтр days — окно по МСК), `api/logs.ts` +2
- Фикс 404: BrowserRouter basename=/admin

**Шрифты (`104e90a`):** index.css + tailwind — Inter (UI) + JetBrains Mono (код/логи).

**Сайдбар (`b829454`):** `SidebarLinksPanel.tsx` +257 (панель настройки ссылок в хедере), `useSidebarLinksStore.ts` +58 (z-index/zustand+localStorage), Sidebar +58.

**Bedolaga (`7eb43a4`) — крупнейший единичный коммит периода:**
- Backend (новые файлы):
  - `web/backend/core/bedolaga_client.py` +356 — HTTP-клиент (headers, token, таймауты)
  - `web/backend/api/v1/bedolaga/__init__.py` +74 — прокси-хелпер `proxy_request`
  - `dashboard.py` +73 (overview/health/capabilities/maintenance/status), `customers.py` +384, `promo.py` +81, `marketing.py` +107, `referrals.py` +58
  - `config.py` +4 (BEDOLAGA_API_URL/TOKEN), `main.py` +4 (роутер)
- Frontend (новые страницы):
  - `BedolagaDashboard.tsx` +448, `BedolagaCustomers.tsx` +680, `BedolagaCustomerDetail.tsx` +1075, `BedolagaPromo.tsx` +527, `BedolagaMarketing.tsx` +550, `BedolagaReferrals.tsx` +575
  - `api/bedolaga.ts` +145, `components/bedolaga/EventsFeed.tsx` +251, `InfoTooltip.tsx` +23, `brand/icons.ts` +92, `config/navigation.ts` +19
- `dist/` — полная пересборка (все ассеты перехешированы, +522 иконок vendor)

---

## 10. Фаза J — Тарифы из БД бота, новые логи, модалка юзеров (11.10)

**11.10.2026 — 8 коммитов, актуальное состояние.**

| Хэш | Время | Сообщение | Файлов | +/- |
|---|---|---|---|---|
| `975797f` | 01:16 | **Инфа по тарифам в Bedolaga** | 4 | +125/−1 |
| `7f8ecd0` | 01:28 | **Работа с отображением тарифов** | 106 | +670/−379 |
| `6f53a9a` | 01:32 | Исправление ошибки с тарифами | 1 | −1 |
| `87d3863` | 10:59 | **Переделка логов и автосинхронизации** | 110 | +1020/−198 |
| `8094114` | 12:19 | Исправление логов | 8 | +65/−26 |
| `d295bfb` | 12:53 | Правка отображения логов | 99 | +358/−173 |
| `4c53cae` | 13:18 | **feat(users): модалка создания/редактирования, профиль с аватаром и подсказками** | 106 | +718/−375 |

**Тарифы (`975797f` + `7f8ecd0` + `6f53a9a`):**
- `web/backend/core/bot_db.py` +101 (новый): read-only движок к БД бота (asyncpg, pool_size=1, max_overflow=0, pool_recycle=300, pre_ping; **fix `6f53a9a`: убраны `connect_args` statement_cache_size/prepare_threshold — не поддерживаются asyncpg**)
- SQL: SELECT 30+ полей из таблицы `tariffs`, JSON-поля (period_prices, allowed_squads, server_traffic_limits) парсятся, `period_prices` → `period_prices_list` [{days, price_kopeks, price_rubles}], ISO timestamps
- `GET /api/bedolaga/tariffs` → `{items, total}`
- `config.py`: `BOT_DB_HOST/PORT/NAME/USER/PASS` + property `bot_database_url`; **значения по умолчанию = прод-креды (`cms_ro`/`cms_ro_pass_2026`, порт 5434)**
- ENV-доки: socat-мост `bot-db-cms-bridge` (systemd на панели, 5434), UFW `allow from 159.194.221.84` (исходящий IP CMS)
- `main.py`: `close_bot_db_engine()` на shutdown
- Frontend: `page/bedolaga/BedolagaTariffs.tsx` +236 (карточки: цены руб., бейджи триала/gift/хит, лимиты трафика/устройств, сквады, поиск; i18n ru/en +15), роутинг, навигация

**Логи (`87d3863` + `8094114` + `d295bfb`):**
- `web/backend/core/app_log.py` +319 (новый): AppLogHandler (корневой logger — **ровно один раз на запись**, в отличие от structlog foreign_pre_chain, который дублировал при нескольких форматтерах) → маппинг category/channel/source + flatten context → `asyncio.Queue` (cap 2000, overflow dumps + warning) → фоновый воркер (батч-INSERT, flush 2s или ≥50 строк, cap сообщения 4000)
- `auto_sync.py` +62: `_PROVIDERS` (platega/yookassa), `_enabled_flags()` — только включённые провайдеры, структурированное событие `{provider, source:'auto', ok, added, skipped, new, error, duration_ms}` — отображается как история синков
- `finance_payments.py` +213: пер-провайдерное логирование
- `8094114`: PHP-FPM access-логи в БД (`.env` APP_LOG_*, Dockerfile +zz-logging.conf, nginx access_log кастомный), ретраи записи, `database.py` retry, Dockerfile tzdata
- `d295bfb`: `LogsViewer.tsx` +159 (расширенный просмотр, фильтры), `.docker/nginx/default.conf` +15, ExtraWidgets +56

**Пользователи (`4c53cae`):**
- `web/frontend/src/components/UserFormModal.tsx` +296 (новый): Dialog-модалка, 9 полей, тултипы, загрузка аватара (≤2 МБ, JPG/PNG/GIF/WEBP, превью, валидация)
- `web/frontend/src/pages/UserEdit.tsx` −119 (удалена), `UsersList.tsx` +62/−30
- `web/backend/api/v1/users.py` +107: `POST /api/users/avatar`, `ensure_user_columns` (идемпотентные ALTER при старте), email → NULL вместо пустой строки (фикс UNIQUE)
- `db/postgres/init/01-schema.sql` +8: колонки профиля в базовой схеме
- Устранён баг 422: «Добавить» вела на `/users/create` → маршрут `/users/:id` → `GET /api/users/NaN`

---

## 11. Merge-коммиты периода

| Хэш | Дата | Автор | Сообщение |
|---|---|---|---|
| `685bc77` | 27.09 | root | resolve conflicts — accept pushed version |
| `26e83cd` | 09.10 | root | Merge origin/main |
| `5d34c52` | 09.10 | deploy | Merge origin/main |
| `4519a1a` | 10.10 | deploy | Merge origin/main |
| `4cbf791` | 10.10 | ImCrazyMonk | Merge branch 'prod-master' |

---

## 12. Итоговое состояние на 11.10.2026

**Публичный сайт (PHP 8.1):** `index.php` → `core/` + `templates/themes/hexaveil/` + `public/hexaveil/`.

**Бэкенд админки (FastAPI, `web/backend/`):** 19 роутеров в `api/v1/` (auth, public, posts, pages, users, categories, media, menus, widgets, themes, settings, dashboard, logs, notifications, diagnostics, finance, finance_payments, preferences, bedolaga/*), core (config/security/database/errors/serializers/slug/db_helpers/rate_limit/request_utils/crypto/logging_config/settings_registry/app_log/auto_sync/theme_config/bedolaga_client/bot_db), 13 схем, тесты (47 unit + 25 e2e).

**Фронтенд (React SPA, `web/frontend/`):** 18 страниц (Login, Dashboard, PostsList, PostEdit, CategoriesList, PagesList, PageEdit, UsersList, MediaList, MenusList, MenuEdit, WidgetsList, ThemeManager, Settings, Finance, Diagnostics, LogsViewer, NotFound, + 6 Bedolaga — внутри pages/bedolaga/), 23 shadcn-компонента, Bedolaga — 6 модулей.

**Прод-поток:** `nginx-selfsteal` (80/443) → `hexacms_web` (:3000) → PHP-FPM / FastAPI / статика; `hexacms_db` PostgreSQL 16; API → `hexacms_api`.

---

## 13. Архитектурные решения (краткий реестр)

| Решение | Где зафиксировано | Суть |
|---|---|---|
| Копировать Remnawave 1:1 | `5a49cca`, `docs/plans/2026-10-09-variant-c` | Не изобретать UI/структуру — тиражировать эталон |
| Формат ответа `{success, data}` | ADR-002 | Осознанное отклонение от `{data}` — PHP-совместимость |
| `web/frontend` + `web/backend` | ADR-002, `4d42478` | Стандартный layout Remnawave |
| dist коммитится | `27b854a` | На сервере нет Node |
| Сборка одним деплоем | `deploy.sh` | `git pull && ./deploy.sh` — idempotent |
| Настройки registry-driven | `85e196b` | db/env/default + шифрование секретов (Crypto) |
| theme.php — SSOT темы | `bcfc432` | Опции темы парсятся из одного файла |
| Логи в БД через очередь | `87d3863` | Handler → Queue → batch INSERT |
| Тарифы бота — direct DB (read-only) | `975797f` | Web API без каталога; cms_ro + socat 5434 + UFW |

---

*Составлено 11.10.2026. Полные диффы — `git show <hash>`.*