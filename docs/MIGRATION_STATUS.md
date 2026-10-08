# HexaVeil CMS — Статус миграции (handoff)

> **Назначение:** состояние работ + что осталось, чтобы продолжить в новом диалоге.
> **Основное ТЗ:** `docs/MIGRATION_TO_REMNAWAVE_STACK.md` · **Бриф:** `docs/MIGRATION_BRIEF.md`
> **Главное правило:** React-админка — **копия Remnawave** (структура/стили/id), меняются только данные/страницы. Потом будет совмещение.
> **Эталон копирования:** `C:\Users\Andre\Desktop\VPN\remnawave-admin-main\web\backend\` — вся структура бэкенда там.

**Дата обновления:** 2026-10-08
**Последний коммит:** `2fc5b39` — рабочие изменения **НЕ закоммичены** (см. §7 «Git»).

Легенда: ✅ готово · 🟡 частично · ❌ нет · 📌 блокер

---

## 1. Статус фаз

| Фаза | Статус | Комментарий |
|------|--------|-------------|
| **0 — PHP API** | ✅ | Все `/api/*` эндпоинты (43), формат `{success,data}` |
| **1 — React SPA** | ✅ исходники / 🟡 прод | Локально всё проверено; прод-nginx не тронут |
| **2 — FastAPI** | 🟡 | **M0–M3 ✅** (каркас, auth, read+write эндпоинты). Осталось M4 (cutover), M5, M6 — см. §4.0 |

---

## 2. ✅ Что сделано

### 2.1 База (коммиты `6b8b2cd` → `2fc5b39`)
- PHP API для React (auth, dashboard, posts, categories, pages, users, logs, widgets, menus, themes, settings, media, finance, diagnostics) — **43 эндпоинта**.
- React SPA `admin-react/` со всеми страницами, дизайн-токены Remnawave, гибридный переключатель.

### 2.2 Ревизия и починка (сессия 2026-10-08, НЕ закоммичено)

**Критические баги (PHP):**
- `core/Router.php` — терялись числовые группы `(\d+)` → падало редактирование **posts/users/pages**. Исправлено.
- `core/routes.php` `jwtBridge()` — читал `payload['user_id']`, а JWT отдаёт `sub`; плюс ранний выход при живой сессии не ставил `jwt_authed` → **finance/diagnostics/preferences** отдавали 403/302. Исправлено (использует `sub`, ставит флаг при любом валидном Bearer).
- `core/helpers.php` + `FinanceController.php` — пропуск CSRF для Bearer-запросов (`$GLOBALS['jwt_authed']`).
- `core/routes.php` `/api/settings` POST — в белый список добавлены `active_theme`, `docker_config`, `loki_config`.
- Добавлены заглушки `api/notifications*` (колокольчик больше не 404).

**Финансы (React, `Finance.tsx` + `api/finance.ts`):**
- График починен, добавлены период, тип, аномалии, линия баланса.
- Фильтры месяц/тип/категория/участник/поиск работают.
- Выбор 25/50/100/200, массовые, экспорт CSV, усреднения KPI.

**Настройки (React, `Settings.tsx`):**
- 4 вкладки, кнопка «Сохранить всё», открытие по `?tab=`.

**Редактор постов (React, `PostEdit.tsx`):**
- Дата, теги, featured, комментарии, SEO (title/meta/canonical/SERP), метрики, обложка (drag&drop), предпросмотр.

**Медиа (`MediaList.tsx`):** DataGrid-таблица.

**БД:** `posts` — добавлены колонки seo; сиквенсы сброшены.

**Деплой:** nginx SPA `/admin/`, тома uploads, favicon, basename.

---

## 3. ❌ Что осталось

### P0 — прод и фиксация
- [ ] **Закоммитить** рабочее состояние (~60 изменённых/новых файлов не в git).
- [ ] **Применить миграции на прод-БД**: `2026-10-08-posts-metadata.sql`, `2026-10-08-fix-sequences.sql`.
- [ ] **Прод-nginx** (`85.198.99.102`): блок `/admin/` → SPA — только с подтверждением.
- [ ] Убрать `IMG_2468.heic`, `tools/`.
- [ ] E2E в браузере всех разделов на проде.

### P1 — доработки
- [ ] Diagnostics: сбор нод не настроен (`nodes: []`).
- [ ] PHP v2-редактор постов не сохраняет seo/tags.
- [ ] `notifications` — заглушки (бэкенда нет).
- [ ] Сверить все разделы в браузере.

### P2 — Фаза 2 (FastAPI)
- [x] **M0–M5** — каркас, auth, read+write, cutover nginx, PHP deprecated (см. §4.0)
- [x] **M6 (частично)** — structlog + request-лог (паттерн Remnawave)
- [ ] **M6 (остаток, опц.)** — RBAC, rate-limit (slowapi), audit-middleware

---

## 4. Фаза 2: PHP API → FastAPI

### 4.0 Прогресс (обновлено 2026-10-08, вечер)

> **Все эндпоинты из §4.1 ниже — ПЕРЕНЕСЕНЫ (✅).** Колонка «Status ❌» в таблице §4.1 устарела — она показывает исходное состояние до миграции; фактически каждый путь уже обслуживается FastAPI.

| Этап | Статус | Доказательство |
|------|--------|----------------|
| **M0** — каркас `backend/` | ✅ | `GET /api/health` → `{"status":"ok","database":"connected"}` |
| **M1** — Auth (JWT) | ✅ | login через nginx → FastAPI вернул PHP-формат; **PHP-токен принят FastAPI** (interop-тест) |
| **M2** — read-only | ✅ | все GET вернули реальные данные (posts/users/categories/settings/media/themes) |
| **M3** — write | ✅ | 25 e2e smoke-тестов (CRUD posts/categories/pages/menus/widgets/users + settings/themes/media) |
| **M4** — cutover nginx | ✅ | `location /api/ → api:8000`; React-эндпоинты работают через nginx без правок |
| **M5** — PHP deprecated | ✅ | `core/routes.php` — блок `/api/*` помечен `DEPRECATED` (оставлен как fallback) |
| **M6** — remnawave-модули | 🟡 | сделано: structlog (+ротация JSON-файла) и request-лог `api_call … (ms)` как в Remnawave. Осталось (опц.): RBAC, slowapi rate-limit, audit-middleware |

**Ключевые находки при интеграции (исправлено):**
- SQLAlchemy 2.1: `execute("SELECT 1")` → `text(...)`.
- PyJWT ≥2.10 отвергал integer `sub` (PHP использует int) → `options={"verify_sub": False}`.
- asyncpg требует `datetime` для TIMESTAMP (не строку) → `datetime.now()`.
- **Схема `pages`** не имела колонок `status`/`updated_at`, хотя и PHP-роут, и React их используют → создана миграция `db/migrations/2026-10-08-pages-status.sql` (применена локально).

**Тесты:** 47 pytest (unit/auth/route-registration) + 25 e2e smoke (реальная БД через nginx) — **все зелёные**.

**Browser E2E — ВСЕ 15 разделов админки (React против FastAPI, `http://localhost/admin/`):**

| Раздел | Результат |
|--------|-----------|
| Login | вход `admn`, редирект на Dashboard ✅ |
| Dashboard | реальные KPI (2 поста, 1 юзер, 2 категории) ✅ |
| Posts (список) | реальные данные, даты `DD.MM.YYYY`, категория, автор ✅ |
| PostEdit | заголовок/excerpt/рубрика/статус/дата/теги/SEO/обложка (uploads-volume) ✅ |
| **Создание поста (UI)** | `POST /api/posts` → редирект `/posts/{id}` ✅ |
| Categories | 2 категории (name/slug/description) ✅ |
| Pages | пустое состояние «Страниц пока нет» ✅ |
| Menus | пустое состояние ✅ |
| Widgets | пустое состояние ✅ |
| Media | 4 файла + превью, размеры, даты ✅ |
| Themes | активная тема `hexaveil`, все опции из `theme_config.py` ✅ |
| Users | 1 юзер (login/email/role/date) ✅ |
| Settings | реальные настройки (site_name, description, meta, posts_per_page) ✅ |
| Logs | реальные `app_logs` (дата/уровень/категория/канал/сообщение) ✅ |
| Finance (PHP bridge) | реальные суммы (Доходы 49193.8 ₽ / Расходы 35816.0 ₽ / Баланс 13377.8 ₽) ✅ |
| Diagnostics (PHP bridge) | рендерится (сбор нод не настроен — вне Фазы 2) ✅ |

Консоль: только pre-existing warning TinyMCE (не связан с миграцией) ✅

**UI write-paths проверены кликом (все 200):**

| Действие | Эндпоинт | Результат |
|----------|----------|-----------|
| Создать пост | `POST /api/posts` (FastAPI) | редирект на `/posts/{id}` ✅ |
| Settings → «Сохранить всё» | `POST /api/settings` (FastAPI) + `finance/api/settings` + `save-preference` (PHP) | ок, без ошибок ✅ |
| Themes → «Сохранить» | `POST /api/themes/settings` (FastAPI) | 200 ✅ |
| Media → «Загрузить» | `POST /api/media/upload` (FastAPI, multipart) | файл появился (4→5), тест-файл удалён ✅ |

---

### 4.1 Полная карта эндпоинтов PHP API (что заменяем)

Все эндпоинты, которые React вызывает по `/api/*`. Формат ответа: `{"success":true, "data":...}` / `{"success":false, "error":"..."}`.

| # | Метод | Путь | Описание | Status |
|---|-------|------|----------|--------|
| 1 | POST | `/api/auth/login` | JWT логин (login+password → token) | ❌ |
| 2 | GET | `/api/auth/me` | Текущий пользователь по JWT | ❌ |
| 3 | GET | `/api/dashboard/stats` | KPI (posts, comments, users, categories) | ❌ |

**Posts (6):**
| 4 | GET | `/api/posts` | Список (page, per_page, sort, dir, search) | ❌ |
| 5 | GET | `/api/posts/{id}` | Один пост | ❌ |
| 6 | POST | `/api/posts` | Создать | ❌ |
| 7 | POST | `/api/posts/{id}` | Обновить (+ tags, seo, featured, cover) | ❌ |
| 8 | OPTIONS | `/api/posts` | CORS preflight | ❌ |
| 9 | OPTIONS | `/api/posts/{id}` | CORS preflight | ❌ |

**Categories (5):**
| 10 | GET | `/api/categories` | Список | ❌ |
| 11 | POST | `/api/categories` | Создать | ❌ |
| 12 | POST | `/api/categories/{id}` | Обновить | ❌ |
| 13 | DELETE | `/api/categories/{id}` | Удалить | ❌ |

**Pages (5):**
| 14 | GET | `/api/pages` | Список | ❌ |
| 15 | GET | `/api/pages/{id}` | Одна страница | ❌ |
| 16 | POST | `/api/pages` | Создать | ❌ |
| 17 | POST | `/api/pages/{id}` | Обновить | ❌ |
| 18 | DELETE | `/api/pages/{id}` | Удалить | ❌ |

**Users (5):**
| 19 | GET | `/api/users` | Список | ❌ |
| 20 | GET | `/api/users/{id}` | Один пользователь | ❌ |
| 21 | POST | `/api/users` | Создать | ❌ |
| 22 | POST | `/api/users/{id}` | Обновить | ❌ |
| 23 | DELETE | `/api/users/{id}` | Удалить | ❌ |

**Logs (2):**
| 24 | GET | `/api/logs` | Список (page, per_page, level, search) | ❌ |
| 25 | POST | `/api/logs/clear` | Очистить логи | ❌ |

**Widgets (5):**
| 26 | GET | `/api/widgets` | Список | ❌ |
| 27 | GET | `/api/widgets/{id}` | Один виджет | ❌ |
| 28 | POST | `/api/widgets` | Создать | ❌ |
| 29 | POST | `/api/widgets/{id}` | Обновить | ❌ |
| 30 | DELETE | `/api/widgets/{id}` | Удалить | ❌ |

**Menus (5):**
| 31 | GET | `/api/menus` | Список | ❌ |
| 32 | GET | `/api/menus/{id}` | Одно меню | ❌ |
| 33 | POST | `/api/menus` | Создать | ❌ |
| 34 | POST | `/api/menus/{id}` | Обновить | ❌ |
| 35 | DELETE | `/api/menus/{id}` | Удалить | ❌ |

**Themes (2):**
| 36 | GET | `/api/themes/settings` | Настройки активной темы | ❌ |
| 37 | POST | `/api/themes/settings` | Сохранить настройки темы | ❌ |

**Settings (2):**
| 38 | GET | `/api/settings` | Все настройки CMS | ❌ |
| 39 | POST | `/api/settings` | Сохранить настройки | ❌ |

**Notifications (3):**
| 40 | GET | `/api/notifications/unread-count` | Счётчик непрочитанных | ❌ |
| 41 | GET | `/api/notifications` | Список уведомлений | ❌ |
| 42 | POST | `/api/notifications/mark-read` | Отметить прочитанным | ❌ |

**Media (3):**
| 43 | GET | `/api/media` | Список файлов | ❌ |
| 44 | POST | `/api/media/upload` | Загрузить файл (multipart) | ❌ |
| 45 | POST | `/api/media/delete` | Удалить файл | ❌ |

**Итого: 45 эндпоинтов (включая OPTIONS), 14 модулей.**

> **Не входят в Фазу 2** (остаются на PHP bridge): `/admin/finance/api/*` (15+ эндпоинтов), `/admin/diagnostics/api/*`, `/admin/settings/save-preference`, `/admin/settings/save-all-preferences`.

### 4.2 JWT-совместимость (критично для M1)

PHP (`core/JWTAuth.php`) создаёт токены так:

| Параметр | Значение PHP | FastAPI должен |
|----------|-------------|----------------|
| **Алгоритм** | HS256 (`sha256` HMAC) | `HS256` |
| **Секрет** | `getenv('JWT_SECRET')` → `getenv('APP_ENCRYPTION_KEY')` → hardcoded fallback | читать из `JWT_SECRET` env |
| **Payload** | `{ sub, login, role, iat, exp }` | те же поля, тот же формат |
| **TTL** | 86400s (24ч) | 86400s |
| **Формат** | base64url(header).base64url(payload).base64url(signature) | стандартный JWT |

**Важно:** FastAPI и PHP должны **разделять один и тот же секрет** — только тогда оба бэкенда смогут принимать токены друг друга в переходный период (M1–M4).

### 4.3 Формат ответа (критично — React зависит от этого)

```json
// Успех
{"success": true, "data": { ... }}  // один объект
{"success": true, "data": [...]}     // список
{"success": true, "data": { "items": [...], "total": N, "page": P, "per_page": PP }}

// Ошибка
{"success": false, "error": "Текст ошибки"}
```

> Remnawave использует другой формат (без `success`-обёртки, `detail` вместо `error`). CMS должен **обернуть** ответы в PHP-совместимый формат через middleware или хелпер.

### 4.4 Схема БД (read-only mapping, не менять)

Таблицы CMS (PostgreSQL, схема в `db/postgres/init/01-schema.sql`):
`users`, `posts`, `categories`, `tags`, `post_tags`, `comments`, `pages`, `media`, `menus`, `menu_items`, `widgets`, `settings`, `fin_transactions`, `fin_settings`, `user_preferences`, `app_logs`, `sessions`.

SQLAlchemy-модели **зеркалят существующую схему** — никаких `autoincrement` изменений, точные имена колонок, типы.

### 4.5 Что копируем из Remnawave (backend-эталон)

```
remnawave-admin-main/web/backend/
├── main.py                          → backend/main.py (упрощённый — без lifespan-сервисов Remnawave)
├── requirements.txt                 → backend/requirements.txt (облегчённый — только нужное)
├── Dockerfile                       → backend/Dockerfile
├── core/
│   ├── config.py                    → backend/core/config.py (CMS-настройки)
│   ├── security.py                  → backend/core/security.py (JWT — совместимый с PHP)
│   ├── errors.py                    → backend/core/errors.py (наш ErrorCode + api_error)
│   └── ...                          → НЕ берём: rbac, rate_limit, audit, plugins и т.д. (M6)
├── api/
│   ├── deps.py                      → backend/api/deps.py (наш get_current_admin, но без RBAC)
│   └── v2/                           → backend/api/v1/ (наша версия)
│       └── auth.py                   → справочно (паттерны)
├── schemas/
│   ├── common.py                    → backend/schemas/common.py (наши CMS-схемы)
│   ├── auth.py                       → справочно
│   └── ...                          → свои Pydantic-модели под CMS
└── tests/                           → backend/tests/
```

### 4.6 Структура backend/ (цель)

```
NewWeb/backend/
├── main.py                  # FastAPI app + CORS + middleware + health
├── requirements.txt
├── Dockerfile
├── core/
│   ├── __init__.py
│   ├── config.py            # Pydantic BaseSettings (.env)
│   ├── database.py          # SQLAlchemy async engine + session
│   ├── security.py          # JWT create/decode (совместимо с PHP)
│   └── errors.py            # ErrorCode + api_error helper
├── api/
│   ├── __init__.py
│   ├── deps.py              # get_current_admin (JWT → AdminUser)
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── auth.py          # /api/auth/login, /api/auth/me
│   │   ├── dashboard.py     # /api/dashboard/stats
│   │   ├── posts.py         # /api/posts/*
│   │   ├── categories.py    # /api/categories/*
│   │   ├── pages.py         # /api/pages/*
│   │   ├── users.py         # /api/users/*
│   │   ├── logs.py          # /api/logs/*
│   │   ├── widgets.py       # /api/widgets/*
│   │   ├── menus.py         # /api/menus/*
│   │   ├── themes.py        # /api/themes/settings
│   │   ├── settings.py      # /api/settings
│   │   ├── notifications.py # /api/notifications/*
│   │   └── media.py         # /api/media/*
├── models/                  # SQLAlchemy models (read-only映射)
│   ├── __init__.py
│   ├── post.py
│   ├── category.py
│   ├── page.py
│   ├── user.py
│   ├── log.py
│   ├── widget.py
│   ├── menu.py
│   ├── theme.py
│   ├── setting.py
│   ├── notification.py
│   └── media.py
├── schemas/                 # Pydantic request/response
│   ├── __init__.py
│   ├── common.py            # ApiResponse[T], PaginatedResponse, ErrorResponse
│   ├── auth.py
│   ├── post.py
│   ├── category.py
│   ├── page.py
│   ├── user.py
│   ├── log.py
│   ├── widget.py
│   ├── menu.py
│   ├── theme.py
│   ├── setting.py
│   ├── notification.py
│   ├── media.py
│   └── dashboard.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_auth.py
    ├── test_posts.py
    └── ...
```

### 4.7 Детальный план M-этапов

#### M0 — Каркас backend/ (1 файл конфиг, ~50 строк core)

**Файлы создать:**
- `backend/main.py` — FastAPI app, CORS, health endpoint, подключение роутеров
- `backend/core/__init__.py`
- `backend/core/config.py` — `CmsSettings(BaseSettings)` из .env (DB_*, JWT_SECRET, APP_ENCRYPTION_KEY)
- `backend/core/database.py` — async engine + sessionmaker (зеркало схемы)
- `backend/core/security.py` — `create_token()`, `decode_token()` — HS256, тот же секрет, те же claims
- `backend/core/errors.py` — `api_error()` + CMS-ErrorCode
- `backend/api/__init__.py`
- `backend/api/deps.py` — `get_current_admin` (JWT → админ из БД)
- `backend/api/v1/__init__.py`
- `backend/schemas/__init__.py`
- `backend/schemas/common.py` — `ApiResponse`, `PaginatedResponse`
- `backend/Dockerfile` — python:3.11-slim, uvicorn
- `backend/requirements.txt` — fastapi, uvicorn, asyncpg, sqlalchemy[asyncio], python-jose, pydantic-settings
- `backend/tests/__init__.py`, `backend/tests/conftest.py`

**Проверка:** `curl http://localhost:8000/api/health` → `{"status": "ok"}`
**Docker:** новый сервис `api` в `docker-compose.yml` (uvicorn на порт 8000, за тем же nginx)

#### M1 — Auth (критично, JWT-совместимость)

**Файлы создать:**
- `backend/api/v1/auth.py` — POST /api/auth/login, GET /api/auth/me
- `backend/schemas/auth.py` — LoginRequest, TokenResponse, UserInfo
- `backend/tests/test_auth.py`

**Проверка:** `curl -X POST .../api/auth/login -d '{"login":"admn","password":"... "}'` → тот же JWT, что и PHP. GET /api/auth/me с этим токеном работает.

#### M2 — Read-only эндпоинты (14 файлов)

Создать для каждого модуля: `models/*.py`, `schemas/*.py`, `api/v1/*.py`. Только GET.

| Файл | Роутер | Модель | Схема |
|------|---------|--------|-------|
| `api/v1/dashboard.py` | GET /api/dashboard/stats | `models/dashboard.py` | `schemas/dashboard.py` |
| `api/v1/posts.py` | GET /api/posts, GET /api/posts/{id} | `models/post.py` | `schemas/post.py` |
| `api/v1/categories.py` | GET /api/categories | `models/category.py` | `schemas/category.py` |
| `api/v1/pages.py` | GET /api/pages, GET /api/pages/{id} | `models/page.py` | `schemas/page.py` |
| `api/v1/users.py` | GET /api/users, GET /api/users/{id} | `models/user.py` | `schemas/user.py` |
| `api/v1/logs.py` | GET /api/logs | `models/log.py` | `schemas/log.py` |
| `api/v1/widgets.py` | GET /api/widgets, GET /api/widgets/{id} | `models/widget.py` | `schemas/widget.py` |
| `api/v1/menus.py` | GET /api/menus, GET /api/menus/{id} | `models/menu.py` | `schemas/menu.py` |
| `api/v1/themes.py` | GET /api/themes/settings | `models/theme.py` | `schemas/theme.py` |
| `api/v1/settings.py` | GET /api/settings | `models/setting.py` | `schemas/setting.py` |
| `api/v1/notifications.py` | GET /api/notifications/* | `models/notification.py` | `schemas/notification.py` |
| `api/v1/media.py` | GET /api/media | `models/media.py` | `schemas/media.py` |

#### M3 — Write эндпоинты

Добавить POST/PUT/DELETE в те же роутеры, что и M2. Order: auth → posts → categories → pages → users → logs/clear → widgets → menus → themes → settings → notifications → media.

#### M4 — Cutover nginx

```nginx
# В .docker/nginx/default.conf
location /api/ {
    proxy_pass http://api:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
# Исключения — finance/api/, diagnostics/api/, preferences — остаются на PHP
location ^~ /admin/finance/api/ { try_files $uri /index.php?$query_string; }
location ^~ /admin/diagnostics/api/ { try_files $uri /index.php?$query_string; }
```

После каждого модуля: проверить, что React работает без изменений.

#### M5 — Отключить PHP API

Пометить PHP-эндпоинты `/api/*` как `// DEPRECATED — migrated to FastAPI`. Выключить роуты.

#### M6 — (Опц.) remnawave-модули

`core/rbac.py`, `core/rate_limit.py`, `core/audit_middleware.py`, `core/plugins.py` — скопировать из эталона.

---

## 5. Ключевые архитектурные решения

### 5.1 `ApiResponse` — единая обёртка ответа

Remnawave не использует `{"success":true,"data":...}`. Нам нужен middleware или декоратор, который оборачивает FastAPI-ответ в PHP-совместимый формат.

```python
# schemas/common.py
from typing import Generic, TypeVar, Any
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
```

### 5.2 JWT — общий секрет

FastAPI читает тот же `JWT_SECRET` из `.env`, что и PHP (`core/JWTAuth.php`). Если `JWT_SECRET` не задан — падает с ошибкой (в отличие от PHP, который использует fallback).

### 5.3 Media upload

FastAPI обрабатывает multipart/form-data через `UploadFile`. Сохраняет в `public/uploads/`. Возвращает URL как PHP.

### 5.4 Finance, Diagnostics, Preferences

**НЕ входят в Фазу 2.** Остаются на PHP bridge (`/admin/finance/api/*`, `/admin/diagnostics/api/*`, `/admin/settings/save-preference`, `/admin/settings/save-all-preferences`). Cutover — только после полной готовности.

### 5.5 Docker-интеграция

Новый сервис `api` в `docker-compose.yml`:

```yaml
api:
  build: ./backend
  container_name: hexacms_api
  restart: unless-stopped
  env_file: .env
  depends_on:
    - db
  volumes:
    - ./backend:/app
    - uploads_data:/app/uploads
  networks:
    - cms-network
```

---

## 6. Remnawave-эталон: структура для копирования

```
C:\Users\Andre\Desktop\VPN\remnawave-admin-main\web\backend\
├── main.py                  # 1030 строк — FastAPI app, CORS, lifespan, middleware, 40+ роутеров
├── requirements.txt         # 55 строк — 19 зависимостей
├── Dockerfile               # 45 строк — python:3.11-slim
├── core/
│   ├── __init__.py
│   ├── config.py            # 142 строки — WebSettings(BaseSettings)
│   ├── security.py           # 318 строк — JWT, Telegram auth, password verify
│   ├── errors.py             # 195 строк — ErrorCode enum + api_error()
│   ├── rbac.py               # 1004 строки — RBAC (скопировать опционально, M6)
│   ├── crypto.py             # шифрование (для финансов)
│   ├── rate_limit.py         # slowapi (M6)
│   ├── audit_middleware.py   # (M6)
│   ├── login_guard.py        # (M6)
│   ├── token_blacklist.py    # (M6)
│   ├── totp.py               # 2FA (M6)
│   ├── fail2ban_logger.py    # (M6)
│   ├── notifier.py           # Telegram-уведомления (M6)
│   ├── cache.py              # Redis-кэш (M6)
│   ├── metrics.py            # Prometheus (M6)
│   └── ... (ещё 25+ модулей — не копировать до M6)
├── api/
│   ├── deps.py               # 407 строк — AdminUser, get_current_admin, require_permission
│   └── v2/                   # 40 модулей
│       ├── __init__.py
│       ├── auth.py           # 866 строк — /api/v2/auth/* (Telegram, password, 2FA, refresh)
│       ├── users.py
│       ├── nodes.py
│       ├── settings.py
│       ├── logs.py
│       ├── notifications.py
│       └── ... (33+ модуля)
├── schemas/
│   ├── __init__.py
│   ├── common.py             # 37 строк — PaginatedResponse, ErrorResponse, SuccessResponse
│   ├── auth.py               # 117 строк — LoginRequest, TokenResponse, AdminInfo...
│   ├── user.py
│   ├── node.py
│   └── ... (8+ схем)
└── tests/                    # 50+ тестовых файлов
    ├── __init__.py
    ├── conftest.py
    ├── test_auth_api.py
    └── ...
```

---

## 7. Git — текущее состояние

```
Последний коммит: 2fc5b39 (Finance charts with recharts + fix 500 error handling)
Ветка: main (или master)
```

**Изменённые файлы (все не закоммичены, ~60 файлов):**

`M .docker/nginx/default.conf` · `M admin-react/src/App.tsx` · `M admin-react/src/api/*` (6 файлов) · `M admin-react/src/pages/*` (14 файлов) · `M admin/controllers/FinanceController.php` · `M admin/templates/layouts/main.php` · `M core/Router.php` · `M core/helpers.php` · `M core/models/FinTransaction.php` · `M core/models/Post.php` · `M core/routes.php` · `M docker-compose.yml` · `M index.php`

`?? IMG_2468.heic` · `?? admin-react/public/` · `?? admin-react/src/api/diagnostics.ts` · `?? db/migrations/*` · `?? docs/MIGRATION_*` · `?? admin/controllers/DiagnosticsController.php` · `?? admin/templates/diagnostics/` · `?? tools/`

**Удалены:** `CHANGELOG_visual_refactor.txt`, `_deploy_list.txt`, `docs/superpowers/*`, `Текстовый документ.txt`

---

## 8. Как продолжить (следующий диалог)

### Вариант A — P0: зафиксировать и выкатить

```bash
# 1) Коммит
git add -A
git commit -m "fix: PHP API (router, jwt, CSRF), finance, settings, post editor, media, uploads"

# 2) Проверка локально
docker compose up -d                              # http://localhost/admin/
cd admin-react && npm run build && npx tsc --noEmit

# 3) Прод-миграции (после подтверждения владельца)
psql "$DATABASE_URL" -f db/migrations/2026-10-08-posts-metadata.sql
psql "$DATABASE_URL" -f db/migrations/2026-10-08-fix-sequences.sql

# 4) Прод-nginx: добавить /admin/ → SPA (как в .docker/nginx/default.conf)
```

### Вариант B — M0: старт Фазы 2

```bash
mkdir -p backend/{core,api/v1,models,schemas,tests}

# Создать файлы (по порядку):
# 1. backend/requirements.txt
# 2. backend/core/__init__.py + config.py + database.py + security.py + errors.py
# 3. backend/api/__init__.py + deps.py
# 4. backend/api/v1/__init__.py
# 5. backend/schemas/__init__.py + common.py
# 6. backend/main.py (FastAPI app, health endpoint)
# 7. backend/Dockerfile
# 8. docker-compose.yml — добавить сервис api
# 9. .docker/nginx/default.conf — добавить /api/ → api:8000

# Запуск
docker compose up --build -d
curl http://localhost:8000/api/health
```

**Порядок (оптимальный):** сначала **P0** (коммит страховки), затем **M0** (каркас). Если времени нет — можно сразу M0, но без коммита весь прогресс Фазы 1 не сохранён.

### С чего начать в новом окне

1. Прочитать этот файл (особенно §4.1 — карта эндпоинтов, §4.2 — JWT-спека)
2. Прочитать `docs/MIGRATION_TO_REMNAWAVE_STACK.md` §5 (Фаза 2)
3. Посмотреть эталон: `C:\Users\Andre\Desktop\VPN\remnawave-admin-main\web\backend\main.py`
4. Выбрать путь: **P0** (коммит + прод) → **M0** (каркас backend/) → **M1** (auth)

---

## 9. Известные особенности

- Локально всё на `docker-compose.yml` (порт `80:80`). Прод — `docker-compose.prod.yml`.
- Эталон копирования: `C:\Users\Andre\Desktop\VPN\remnawave-admin-main\web\backend\`.
- React-админка затеняет PHP-SSR по `/admin/*`. PHP-API под `/api/*` жив — его и заменяем.
- **Finance/Diagnostics/Preferences** — НЕ входят в Фазу 2. Остаются на PHP bridge.
- **JWT**: PHP использует `JWT_SECRET` из env, fallback `APP_ENCRYPTION_KEY`. FastAPI должен читать тот же секрет.
- **Формат ответа**: `{"success":true, "data":...}` — нестандартный для Remnawave, нужна обёртка.
- PHP `JWTAuth.php` (130 строк) — чистый HMAC-SHA256, без библиотек. python-jose должен быть совместим.
- `.env` содержит `APP_ENCRYPTION_KEY=140ce5c3fc65a29787e350261b047dc01997ce19a76d7dbe760d2106e371dcab` — может использоваться как JWT_SECRET.
- В корне лежат мусорные файлы (`IMG_2468.heic`, `tools/`) — удалить при P0.