# Фаза 0 — Настройки: чистка + брендинг + смена пароля

**Goal:** Довести страницу «Настройки» до рабочего вида без введения реестра настроек (это Фаза 1):
редактирование названия CMS и заголовка вкладки, динамический список тем, смена пароля,
базовая валидация, удаление рудимента `use_react_admin`. Финансы остаются отдельной вкладкой.

**Constraints:**
- Прод не трогать. Ничего не коммитить в рамках этой задачи (коммит — отдельным решением).
- Формат ответов PHP-совместимый: `{"success": true, ...}` / `{"success": false, "error": "...", "code": "..."}`.
- Инструментарий UI: `components/ui` (Card, Input, Label, Button, Select, Switch, Tabs, Skeleton), тосты — `sonner`.
- Язык UI — русский, как в текущем `Settings.tsx` (i18n не обязателен для этой фазы).
- `web/frontend/dist` коммитится в репо → после правок фронта выполнить `npm run build`.

**Tech:** React 18 + TS + Vite + Tailwind + TanStack Query? (текущая CMS-Settings использует сырой `useState/useEffect`/`fetch`; допустимо сохранить стиль), FastAPI + SQLAlchemy async.

---

## Файловая карта

| Файл | Что делаем |
|---|---|
| `web/backend/api/v1/settings.py` | расширить `ALLOWED_KEYS`, добавить валидацию |
| `web/backend/api/v1/public.py` (new) | `GET /api/public/branding` без авторизации |
| `web/backend/api/v1/themes.py` | `GET /api/themes` — список тем |
| `web/backend/api/v1/auth.py` | `POST /api/auth/change-password` |
| `web/backend/schemas/auth.py` | `ChangePasswordRequest` |
| `web/backend/main.py` | зарегистрировать `public` роутер |
| `web/frontend/src/api/public.ts` (new) | `getBranding()` |
| `web/frontend/src/api/themes.ts` | `list()` |
| `web/frontend/src/api/auth.ts` | `changePassword()` |
| `web/frontend/src/store/useBrandingStore.ts` (new) | состояние брендинга + `load()` |
| `web/frontend/src/components/BrandingProvider.tsx` (new) | загрузка брендинга + `document.title` |
| `web/frontend/src/App.tsx` | обернуть в `BrandingProvider` |
| `web/frontend/src/pages/Login.tsx` | имя из брендинга вместо «HexaVeil CMS» |
| `web/frontend/src/components/layout/Sidebar.tsx` | имя из брендинга |
| `web/frontend/src/pages/Settings.tsx` | основные поля + брендинг, темы из API, убрать `use_react_admin`, вкладка «Безопасность» |
| `web/frontend/index.html` | `<title>` — фолбэк (без хардкода бренда? оставить как фолбэк) |

---

## Настройки (ключи)

Новые ключи в `settings` (брендинг + мелкие):
`admin_title`, `browser_title`, `title_separator`, `favicon_url`, `admin_email`, `site_url`, `timezone`, `locale`.

Уже разрешены и используются: `site_name`, `site_description`, `meta_description`, `meta_keywords`, `active_theme`, `posts_per_page`, `comments_auto_approve`, `maintenance_mode`, `docker_config`, `loki_config`.

Дефолты (если в БД нет):
- `admin_title` = `"HexaVeil CMS"`
- `browser_title` = `""` (фолбэк → `admin_title`)
- `title_separator` = `"—"`
- `favicon_url` = `""`
- `locale` = `"ru"`, `timezone` = `"Europe/Moscow"`
- `admin_email` = из `settings` seed, `site_url` = из seed

---

## T1 — backend: расширить settings + валидация

**Files:** `web/backend/api/v1/settings.py`

- Добавить в `ALLOWED_KEYS`: `admin_title, browser_title, title_separator, favicon_url, admin_email, site_url, timezone, locale`.
- В `update_settings` перед upsert провалидировать:
  - `posts_per_page` → int > 0, иначе `api_error(400, E.INVALID_INPUT, "posts_per_page должен быть положительным числом")`.
  - `admin_email` (если непустой) → простая проверка `@`/regex; иначе 400.
  - `site_url`, `favicon_url` (если непустые) → начинаются с `http://`/`https://` или `/`; иначе 400.
- Порт ответа ошибки — существующий `api_error`.

**Verify:** `cd web/backend && python -m pytest -q` (без новых падений).

---

## T2 — backend: публичный брендинг

**Files:** `web/backend/api/v1/public.py` (new), `web/backend/main.py`

- `router = APIRouter()`, эндпоинт без `get_current_admin`:
  `GET /public/branding` → `{ "success": true, "data": { site_name, admin_title, browser_title, title_separator, favicon_url } }`.
- Читает `settings` таблицу, применяет дефолты (см. выше). Никаких секретов.
- В `main.py`: `from web.backend.api.v1 import public as public_api` + `app.include_router(public_api.router, prefix="/api", tags=["public"])`.

**Verify:** ручной `curl /api/public/branding` после поднятия (или тест), возвращает 200 без токена.

---

## T3 — backend: список тем

**Files:** `web/backend/api/v1/themes.py`

- `GET /themes` (auth) → `{ "success": true, "data": [ { "value": "hexaveil", "label": "HexaVeil (лендинг)" }, ... ] }`.
- Сканировать `Path(get_cms_settings().root_path) / "templates" / "themes"` — подпапки, содержащие `theme.php`.
- `label` — из `theme_config.get_theme_config(name).get("name")`, иначе имя папки.
- Фолбэк, если каталога нет: `[{"value":"hexaveil","label":"HexaVeil (лендинг)"},{"value":"default","label":"Default"}]`.

**Verify:** эндпоинт возвращает ≥2 темы на dev.

---

## T4 — backend: смена пароля

**Files:** `web/backend/api/v1/auth.py`, `web/backend/schemas/auth.py`

- Схема `ChangePasswordRequest { current_password: str, new_password: str }`.
- `POST /auth/change-password` (auth обязательна):
  1. загрузить `password` текущего пользователя из БД;
  2. `verify_admin_password(current_password, hash)` — иначе `api_error(400, E.INVALID_CREDENTIALS, "Неверный текущий пароль")`;
  3. `len(new_password) >= 8` — иначе 400;
  4. новый пароль ≠ текущий (по verify) — иначе 400;
  5. `hash_password(new_password)` → `UPDATE users SET password=... WHERE id=:id`; commit;
  6. `{ "success": true }`.
- Использовать `login_guard`? Не обязательно; можно не трогать.

**Verify:** тест/ручной: неверный текущий → 400; валидный → 200, затем вход новым паролем.

---

## T5 — frontend: брендинг

**Files:** `web/frontend/src/api/public.ts` (new), `web/frontend/src/store/useBrandingStore.ts` (new), `web/frontend/src/components/BrandingProvider.tsx` (new), `web/frontend/src/App.tsx`, `Login.tsx`, `Sidebar.tsx`

- `public.ts`: `getBranding(): Promise<{success:boolean; data:{...}}>` → `api.get('/public/branding')`.
- `useBrandingStore` (zustand): `{ admin_title, browser_title, title_separator, site_name, favicon_url, loaded, load() }`.
  - `load()`: fetch, применить дефолты, `document.title = browser_title || admin_title`, обновить `<link rel="icon">` если `favicon_url`.
  - Ошибки глотать (фолбэк-бренд), не блокировать приложение.
- `BrandingProvider`: `useEffect(() => load(), [])`; рендерит `children`.
- `App.tsx`: обернуть дерево в `<BrandingProvider>` (внутри `AppearanceProvider`).
- `Login.tsx` (стр. ~84) и `Sidebar.tsx` (стр. ~95): вместо `HexaVeil CMS` → `useBrandingStore(s => s.admin_title) || 'HexaVeil CMS'`.
- `index.html` `<title>HexaVeil CMS</title>` оставить как фолбэк до загрузки.

**Verify:** `cd web/frontend && npx tsc --noEmit`.

---

## T6 — frontend: страница «Настройки»

**Files:** `web/frontend/src/pages/Settings.tsx`, `api/themes.ts`, `api/auth.ts`

- Вкладки: **Основные**, **Внешний вид**, **Безопасность** (new), **Финансы** (как есть), **Логи** (как есть).
- «Основные»:
  - Брендинг: `admin_title`, `browser_title`, `title_separator`, `favicon_url`.
  - Сайт: `site_name`, `site_description`, `site_url`, `admin_email`, `timezone`, `locale`.
  - Контент: `posts_per_page`, `comments_auto_approve` (switch), `maintenance_mode` (switch).
  - SEO: `meta_description`, `meta_keywords`.
  - Валидация на клиенте: число > 0; email; url. Инлайн-подсказки.
  - После сохранения — повторный `load()` и обновить брендинг (`useBrandingStore.getState().load()`) чтобы вкладка/сайдбар сразу обновились.
- «Внешний вид»:
  - `active_theme` — из `themesApi.list()` (динамически), сохранение как есть.
  - **Убрать** блок «Панель управления» с `use_react_admin` и функцию `toggleReactAdmin`.
- «Безопасность» (new):
  - Блок смены пароля: current / new / confirm, проверка совпадения и min 8, кнопка → `authApi.changePassword`, тосты успех/ошибка.
- `api/themes.ts`: добавить `list()`.
- `api/auth.ts`: добавить `changePassword(current_password, new_password)`.

**Verify:** `npx tsc --noEmit && npm run build` (обновит `dist`).

---

## T7 — финальная верификация

- `cd web/backend && python -m pytest -q` — зелёно.
- `cd web/frontend && npx tsc --noEmit` — 0 ошибок; `npm run build` — ok.
- `docker compose config -q` (dev) — ok.
- Ручной smoke (если поднимается): логин → Настройки → меняем `admin_title` → сохранить → имя в сайдбаре и заголовок вкладки изменились; смена пароля 200.

---

## Вне скоупа Фазы 0
- Реестр настроек (метаданные, source db/env/default, reset-to-default, бейджи) — Фаза 1.
- Интеграции Remnawave/Bedolaga, SEO-вкладка целиком, IP-whitelist, FAQ, легенда, статус-синк — Фазы 2–3.
- Удаление `use_react_admin` из бэкенд-whitelist `preferences.py` — не требуется.
