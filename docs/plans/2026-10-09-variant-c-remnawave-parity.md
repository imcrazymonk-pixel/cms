# Вариант C — Приведение структуры к Remnawave (parity) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` (или `subagent-driven-development`) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Привести `NewWeb/` к структурному паритету с `remnawave-admin-main/`, чтобы код был взаимно переносим (копировать из Remnawave в CMS и наоборот), не ломая текущий прод.

**Architecture:** Вариант C = «не двигать папки, довести внутренности до 1:1». Эталон: `remnawave-admin-main/web/backend` (FastAPI control-plane) + `remnawave-admin-main/web/frontend` (React SPA). Наш CMS работает с собственной БД (posts/users/...), поэтому `schemas/` строим 1:1, data-access оставляем в `core/` (аналог `shared/data_access.py` в эталоне). Позже — Вариант B (перенос в `web/frontend` + `web/backend`).

**Tech Stack:** FastAPI, SQLAlchemy async, PyJWT, Pydantic v2, structlog; React 18, TypeScript, Vite, Tailwind, shadcn/ui (Radix), TanStack Query, Zustand, i18next.

## Global Constraints

- **Не менять** имена полей БД, URL-путей существующих эндпоинтов, имена форм — прод работает.
- **Формат ответов остаётся PHP-совместимым** `{"success":true,"data":...}` / `{"success":false,"error":...}` (React зависит). Это осознанное отклонение от Remnawave (`{data}`/`{detail}`) — задокументировать в ADR.
- **UI-слой (components/ui, layout)** — копия Remnawave 1:1, менять только пункты навигации/данные.
- **React API-модуль** = тонкая обёртка над axios, свой на домен (`posts.ts`, `pages.ts`, ...) — как в эталоне.
- **Имена модулей backend** повторяют домены эталона (`users.py`, `logs.py`, `settings.py`, `notifications.py`).
- Никаких npm-сборщиков на PHP-стороне; React использует Vite.
- Прод-nginx (`85.198.99.102`) не трогать без подтверждения.
- PHP 8.1+.

---

## Файловая карта (что создаётся/меняется)

| Файл | Ответственность |
|---|---|
| `backend/api/v1/media.py` | безопасное удаление файлов (в C1) |
| `admin-react/src/components/CommandPalette.tsx` | навигация Ctrl+K под CMS (C1) |
| `admin-react/src/locales/{ru,en}/translation.json` | CMS-ключи `nav.*`, `commandPalette.*` (C1) |
| `admin-react/src/api/notifications.ts` | только реализованные методы (C1) |
| `admin-react/src/pages/MenuEdit.tsx` | реальный редактор меню (C1) |
| `admin-react/src/api/categories.ts` | убрать мёртвый `get()`/`parent_id` (C1) |
| `backend/schemas/*.py` | Pydantic-схемы per-domain (C2) |
| `backend/api/v1/*.py` | `response_model=` (опц.) (C2) |
| `admin-react/src/types/*.ts` | типы сущностей CMS (C3) |
| `admin-react/src/lib/*.ts` | перенос полезных хуков эталона (C3) |
| `admin-react/src/store/permissionStore.ts` | задел под RBAC (C3) |
| `docs/decisions/ADR-002-remnawave-structure-parity.md` | фиксация отклонений (C4) |

---

## C1 — Безопасность и чистота (выполняется сейчас)

### Task 1: Защита от path traversal в удалении медиа

**Files:**
- Modify: `backend/api/v1/media.py`
- Test: `backend/tests/test_media_security.py` (create)

**Interfaces:**
- Produces: `safe_public_path(path: str) -> Optional[Path]` — возвращает путь внутри `public_dir` или `None`, если выход за пределы.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_media_security.py
from backend.api.v1.media import safe_public_path


def test_safe_path_ok(monkeypatch):
    monkeypatch.setenv("PUBLIC_DIR", "/tmp/pub")
    from backend.core.config import get_cms_settings
    get_cms_settings.cache_clear()
    p = safe_public_path("/public/uploads/a.jpg")
    assert p is not None
    assert "uploads" in str(p) and "a.jpg" in str(p)


def test_safe_path_traversal_rejected(monkeypatch):
    monkeypatch.setenv("PUBLIC_DIR", "/tmp/pub")
    from backend.core.config import get_cms_settings
    get_cms_settings.cache_clear()
    assert safe_public_path("/public/../etc/passwd") is None
    assert safe_public_path("../../etc/passwd") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_media_security.py -v`
Expected: FAIL with `ImportError: cannot import name 'safe_public_path'`

- [ ] **Step 3: Write minimal implementation**

В `backend/api/v1/media.py` добавить функцию и использовать её в `delete_media`:

```python
from typing import Optional

def safe_public_path(path: str) -> Optional[Path]:
    """Resolve `path` (e.g. '/public/uploads/x.jpg') inside PUBLIC_DIR.

    Returns None if the resolved path escapes PUBLIC_DIR (path traversal).
    """
    settings = get_cms_settings()
    public_dir = Path(settings.public_dir).resolve()
    rel = path[len("/public/"):] if path.startswith("/public/") else path.lstrip("/")
    candidate = (public_dir / rel).resolve()
    if candidate == public_dir or public_dir in candidate.parents:
        return candidate
    return None
```

Заменить тело `delete_media`:
```python
    if path != "":
        full = safe_public_path(path)
        if full and full.is_file():
            try:
                full.unlink()
            except OSError:
                pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_media_security.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run full backend test suite**

Run: `cd backend && python -m pytest -q`
Expected: без новых падений

---

### Task 2: CommandPalette под CMS + i18n-ключи

**Files:**
- Modify: `admin-react/src/components/CommandPalette.tsx`
- Modify: `admin-react/src/locales/ru/translation.json`
- Modify: `admin-react/src/locales/en/translation.json`

**Interfaces:**
- Consumes: `nav.*` / `commandPalette.*` из i18n.

- [ ] **Step 1: Add CMS i18n keys**

В `nav` добавить: `posts`, `categories`, `pages`, `menus`, `media`, `widgets`, `themes`, `finance`, `diagnostics`.
В `commandPalette` добавить `posts` (и при необходимости аналоги).

ru: `"posts":"Посты","categories":"Категории","pages":"Страницы","menus":"Меню","media":"Медиа","widgets":"Виджеты","themes":"Темы","finance":"Финансы","diagnostics":"Диагностика"`
en: `"posts":"Posts","categories":"Categories","pages":"Pages","menus":"Menus","media":"Media","widgets":"Widgets","themes":"Themes","finance":"Finance","diagnostics":"Diagnostics"`

- [ ] **Step 2: Rewrite navigation group**

Заменить Remnawave-пункты (nodes/fleet/hosts/violations/automations/mailserver/analytics/billing/backups/api-keys/admins/audit) на CMS:
```
Дашборд → /, Посты → /posts, Категории → /posts/categories, Страницы → /pages,
Меню → /menus, Медиа → /media, Виджеты → /widgets, Темы → /themes,
Финансы → /finance, Пользователи → /users, Настройки → /settings,
Логи → /logs, Диагностика → /diagnostics
```

- [ ] **Step 3: Remove user-search block**

Удалить `useQuery(['command-search-users'])` и его `CommandGroup` — backend `/api/users` не поддерживает `search`, а navigation ведёт на `/users/{id}`, не `{uuid}`.

- [ ] **Step 4: Verify types + build**

Run: `cd admin-react && npx tsc --noEmit`
Expected: 0 ошибок

---

### Task 3: Урезать нерабочие методы notifications.ts

**Files:**
- Modify: `admin-react/src/api/notifications.ts`

- [ ] **Step 1: Keep only implemented endpoints**

Оставить типы `Notification`, `PaginatedResponse` и методы: `list` (GET /notifications), `unreadCount` (GET /notifications/unread-count), `markRead` (POST /notifications/mark-read).
Удалить: `delete`, `deleteOld`, `create`, `listChannels`, `createChannel`, `updateChannel`, `deleteChannel`, `getSmtpConfig`, `updateSmtpConfig`, `testSmtp`, `listAlertRules`, `createAlertRule`, `updateAlertRule`, `deleteAlertRule`, `toggleAlertRule`, `listAlertLogs`, `acknowledgeAlerts`, `listAlertTemplates`, `activateAlertTemplate`, типы `NotificationChannel`, `SmtpConfig`, `AlertRule`, `AlertLog`, `AlertTemplate`.

- [ ] **Step 2: Verify consumers compile**

Run: `cd admin-react && npx tsc --noEmit`
Expected: 0 ошибок (Header использует только unreadCount/list/markRead)

---

### Task 4: Реальный редактор меню (MenuEdit)

**Files:**
- Modify: `admin-react/src/pages/MenuEdit.tsx`
- Test (manual): открыть `/admin/menus/{id}`

**Interfaces:**
- Consumes: `menusApi.get(id)`, `menusApi.update(id, data)` из `../api/menus`; `MenuItem { id, name, url, location }`.

- [ ] **Step 1: Implement form**

Загрузить меню по `useParams().id`, форма `name` / `url` / `location` (select: main/footer/sidebar), кнопка «Сохранить» → `menusApi.update(id, payload)` → toast + `navigate('/menus')`. Использовать компоненты `Card`, `Input`, `Label`, `Button`, `Select` (как в `MenusList.tsx`).

- [ ] **Step 2: Verify**

Run: `cd admin-react && npx tsc --noEmit && npm run build`
Expected: сборка без ошибок

---

### Task 5: Убрать мёртвый метод categories.get

**Files:**
- Modify: `admin-react/src/api/categories.ts`

- [ ] **Step 1: Remove `get` and `parent_id`**

У метода `get(id)` нет backend-эндпоинта (`GET /categories/{id}` отсутствует); поля `parent_id` нет в схеме БД. Удалить оба.

- [ ] **Step 2: Verify**

Run: `cd admin-react && npx tsc --noEmit`
Expected: 0 ошибок (метод нигде не вызывается)

---

## C2 — Backend: `schemas/` per-domain (parity)

> Строим 1:1 с `remnawave-admin-main/web/backend/schemas/`: один файл на домен. Формат ответов — PHP-совместимый (наш `common.py`), т.е. `ApiResponse[T]`.

### Task 6: Набор схем

**Files (create):** `backend/schemas/post.py`, `category.py`, `page.py`, `user.py`, `menu.py`, `widget.py`, `log.py`, `media.py`, `theme.py`, `setting.py`, `notification.py`, `finance.py`, `dashboard.py`

**Interfaces:**
- Produces: Pydantic-модели (Response) для каждого домена + Request-модели (Create/Update) с теми же полями, что принимает соответствующий роутер.

- [ ] **Step 1:** Для каждого роутера `backend/api/v1/{domain}.py` выписать поля из INSERT/UPDATE-словарей и SELECT.
- [ ] **Step 2:** Создать `schemas/<domain>.py` с моделями `XxxResponse`, `XxxCreate`, `XxxUpdate` (поля = реальные колонки).
- [ ] **Step 3:** (опц.) Добавить `response_model=ApiResponse[XxxResponse]` в GET-эндпоинты.
- [ ] **Step 4:** `cd backend && python -m pytest -q` — зелёно.

### Task 7: Решение по `models/`

Эталон `web/backend` **не имеет `models/`** (control-plane ходит во внешний API). У нас data-access в `core/db_helpers.py`. Варианты:
- **(7a)** удалить пустую `backend/models/` и задокументировать data-access в `core/`;
- **(7b)** наполнить SQLAlchemy-моделями (большой рефактор роутеров, низкая ценность — raw SQL уже PHP-parity).

**Решение по умолчанию: 7a** (ближе к эталону, меньше риска). Выполнить после подтверждения владельца.

---

## C3 — Frontend: `types/`, `lib/`, `store/` (parity)

### Task 8: `types/`

**Files (create):** `admin-react/src/types/models.ts` — типы CMS-сущностей (Post, Page, User, Category, Menu, Widget, MediaItem, LogEntry, FinanceTransaction), вынесенные из `api/*.ts` (эталон держит `types/` отдельно).
- [ ] Создать файл, реэкспортировать типы.
- [ ] `npx tsc --noEmit` — 0 ошибок.

### Task 9: `lib/` — перенос полезных хуков эталона

**Files (copy из эталона, адаптировать):**
- `useTabParam.ts`, `useUrlParam.ts`, `mutationToast.ts`, `useDeferredAction.ts`, `useOrderPreference.ts`, `useChartTheme.ts`, `clientLogger.ts`
- НЕ переносить: `useOpenUser.ts` (uuid), `plugins.ts` (плагин-система Remnawave).
- [ ] Скопировать, поправить импорты на `@/lib/...`.
- [ ] `npx tsc --noEmit` — 0 ошибок.

### Task 10: `store/permissionStore.ts` (задел под RBAC)

**Files (create):** `admin-react/src/store/permissionStore.ts` — минимальный стор: `isLoaded`, `loadPermissions()` (зовёт `/api/auth/me`, кладёт role), `clearPermissions()`. Без RBAC-матрицы (её нет в CMS).
- [ ] Создать, подключить очистку при logout (как в эталонном `App.tsx`).
- [ ] `npx tsc --noEmit` — 0 ошибок.

---

## C4 — Документация

### Task 11: ADR-002

**Files (create):** `docs/decisions/ADR-002-remnawave-structure-parity.md`
- [ ] Зафиксировать: цель паритета; что копируем 1:1 (ui/layout/lib/store/структура backend); что осознанно отклоняется (формат ответов `{success,data}`, версия API `v1`, отсутствие `models/`, RBAC).
- [x] Разделы «Вариант C/B» перенесены в `docs/ARCHITECTURE.md`.

---

## Вариант B — ВЫПОЛНЕН (2026-10-09)

Перенос `admin-react/` → `web/frontend/`, `backend/` → `web/backend/`; импорты `backend.*` → `web.backend.*`; правки `web/backend/Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`, `.docker/nginx/default.conf`, `vite.config.ts`, `index.php`, `.env.example`, `.kilo/agent/design.md`.
Проверено: `pytest` 101 · `tsc --noEmit` 0 · `npm run build` ok · `docker compose config` (dev+prod) ok · `docker compose build api` ok. Прод не выкатывался.

---

## Статус выполнения (обновлено при исполнении)

### C1 — сделано, с решениями владельца
- **Task 1** ✅ path traversal в `media.py` (`safe_public_path`), тесты `test_media_security.py` (2), полный suite зелёный.
- **Task 2** ✅ `CommandPalette.tsx` переписан под CMS-навигацию (по ТЗ «скопировать, поменять пункты»); добавлены ключи `nav.posts/categories/pages/menus/media/widgets/themes/finance/diagnostics` в `locales/{ru,en}`.
- **Task 3** — **ОТМЕНЕНО по решению владельца:** `notifications.ts` **восстановлен** полностью (218 строк) как задел под перенос Remnawave-страниц (Notifications/MailServer). Причина: цель — паритет/переносимость важнее чистоты.
- **Task 4** — **изменено:** `MenuEdit.tsx` реализован как **настоящая страница** (create `/menus/create` + edit `/menus/:id`), как `PostEdit`/`PageEdit`. `MenusList` переведён с диалога на навигацию к странице (единый detail-паттерн).
- **Task 5** — **ОТМЕНЕНО:** `categories.ts` восстановлен (`get()` + `parent_id`) для паритета.

### C2 — сделано
- **Task 6** ✅ созданы per-domain схемы: `backend/schemas/{post,category,page,user,menu,widget,log,media,theme,setting,notification,dashboard,finance}.py`; `__init__.py` обновлён; smoke-тесты `test_schemas.py` (17 кейсов).
- Task 6 Step 3 (`response_model=`) — **отложено**: конверт `{"success":...,"data":...}` и лишние поля (`category_name`, `author_name`) делают жёсткий `response_model` рискованным для работающих эндпоинтов. Помечено как опциональное.
- **Task 7 → 7a** ✅ пустая `backend/models/` удалена (в эталоне `web/backend` моделей нет; data-access остаётся в `core/db_helpers.py`). Проверено: никто не импортировал `backend.models`.

### C3 — сделано
- **Task 9** ✅ перенесены `lib/`: `useTabParam`, `useUrlParam`, `useDeferredAction`, `useOrderPreference`, `useChartTheme`, `mutationToast` (адаптирован под `{error}`), `clientLogger`. НЕ перенесены: `useOpenUser` (uuid), `plugins.ts` (плагин-система), `authBridge` (токен-архитектура).
- **Task 8** ✅ `admin-react/src/types/models.ts` — реэкспорт типов CMS-сущностей.
- **Task 10** ✅ `store/permissionStore.ts` (адаптирован под CMS, без RBAC) + подключён в `RequireAuth` (`App.tsx`) — стор живой.
- Проверка: `tsc --noEmit` ✅, `npm run build` ✅.

### C4 — сделано
- **Task 11** ✅ `docs/decisions/ADR-002-remnawave-structure-parity.md` (что копируем 1:1, что отклоняем и почему). Разделы «Вариант C/B» — в `docs/ARCHITECTURE.md`.



---

## Self-Review

- **Coverage:** C1 (Tasks 1–5) закрывает P0/P1 из аудита; C2 (6–7) — паритет `schemas/`; C3 (8–10) — паритет `types/lib/store`; C4 (11) — фиксация; B — отдельно.
- **Placeholder scan:** Task 6 перечисляет конкретные файлы/поля; полный код схем генерируется по факту чтения роутеров (поля известны из C1-аудита).
- **Type consistency:** `MenuItem` (id/name/url/location) един в `api/menus.ts` и `MenuEdit`; `safe_public_path` определён в Task 1 и используется в `delete_media`.
