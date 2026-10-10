# HexaVeil CMS — Архитектура и история

> **Единый документ архитектуры.** Заменяет устаревшие `docs/MIGRATION_*.md`, которые описывали процесс миграции (все фазы выполнены).

---

## 1. Что это

Сайт VPN-сервиса **HexaVeil**. Состоит из двух независимых частей:

| Часть | Технологии | Назначение |
|-------|-----------|-----------|
| **Публичный сайт** | PHP 8.1 (vanilla) + PostgreSQL | Лендинг + блог |
| **Админ-панель** | React SPA (Vite + TypeScript + shadcn/ui) + FastAPI | Управление контентом |

Обе части работают под одним доменом `hexaveil.xyz`, через один nginx.

---

## 2. Как к этому пришли (эволюция)

```
Фаза 0     PHP JSON API для React
Фаза 1     React SPA-админка (копия Remnawave 1:1)
Фаза 2     FastAPI вместо PHP-API (M0→M8)
Вариант C  Структурный паритет с Remnawave (schemas/, lib/, store/, types/)
Вариант B  Стандартный layout Remnawave: web/frontend + web/backend
```

Все этапы **выполнены**. PHP в админке больше не используется — только для публичного сайта.

---

## 3. Архитектура (текущая)

```
NewWeb/
├── index.php                  # Front-controller публичного сайта (PHP)
│
├── web/
│   ├── frontend/              # React SPA админки
│   │   ├── src/               # Исходники (TypeScript + компоненты)
│   │   │   ├── App.tsx        # Роутинг
│   │   │   ├── main.tsx       # Entry point
│   │   │   ├── index.css      # Дизайн-система Remnawave
│   │   │   ├── api/           # API-клиенты (auth, posts, pages, ...)
│   │   │   ├── components/    # layout/ + ui/ (23 shadcn компонента)
│   │   │   ├── pages/         # Все страницы админки
│   │   │   ├── store/         # Zustand (auth, appearance, filters)
│   │   │   └── lib/           # Утилиты (useTabParam, mutationToast, ...)
│   │   ├── public/            # config.js, favicon, logo
│   │   ├── dist/              # Сборка (коммитится в репо)
│   │   └── vite.config.ts     # Прокси /api → FastAPI
│   │
│   └── backend/               # FastAPI (JSON API)
│       ├── main.py            # FastAPI app + CORS + middleware
│       ├── api/v1/            # Роутеры (auth, posts, pages, users, ...)
│       ├── core/              # config, security, database, errors
│       ├── schemas/           # Pydantic-модели per-domain
│       └── tests/             # 47 unit + 25 e2e smoke
│
├── core/                      # PHP-ядро публичного сайта
│   ├── Router.php             # Маршрутизация
│   ├── routes.php             # Все маршруты публичного сайта
│   ├── TemplateEngine.php     # Шаблонизатор
│   ├── Database.php           # PDO-обёртка
│   ├── models/                # Post, Category, Page, User, ...
│   ├── helpers.php            # Утилиты
│   └── helpers_icons.php      # Inline Lucide SVG-иконки
│
├── templates/themes/          # PHP-темы (hexaveil — активная)
├── public/                    # Ассеты тем, uploads, дизайн-система
├── config/config.php          # PHP-конфиг (env-aware)
├── db/                        # Схема PostgreSQL, миграции, дампы
├── docs/                      # Документация
├── plugins/                   # PHP-плагины
├── .docker/                   # Nginx + PHP конфиги
├── Dockerfile                 # PHP 8.1-FPM
├── docker-compose.yml         # dev
├── docker-compose.prod.yml    # prod
└── docker-entrypoint.sh       # Инициализация при старте
```

---

## 4. Потоки запросов (прод)

```
браузер → hexaveil.xyz (85.198.99.102)
  │
  ├── /, /blog, /*           → PHP (core/ + templates/) — публичный сайт
  │
  ├── /admin/*               → React SPA (web/frontend/dist/)
  │     └── API calls        → /api/* → FastAPI
  │
  └── /api/*                 → FastAPI (web/backend/)
        ├── /api/auth/*       — JWT логин / me
        ├── /api/posts/*      — CRUD постов
        ├── /api/pages/*      — CRUD страниц
        ├── /api/users/*      — CRUD пользователей
        ├── /api/categories/* — CRUD категорий
        ├── /api/media/*      — Список/загрузка/удаление медиа
        ├── /api/menus/*      — CRUD меню
        ├── /api/widgets/*    — CRUD виджетов
        ├── /api/themes/*     — Настройки темы
        ├── /api/settings     — Настройки CMS
        ├── /api/logs/*       — Системные логи
        ├── /api/dashboard/*  — Статистика
        ├── /api/notifications/* — Уведомления
        └── bridge:
            /admin/finance/api/*     → PHP (Finance)
            /admin/diagnostics/api/* → PHP
            /admin/settings/save-*   → PHP
```

**Архитектура сервера:**
- `nginx-selfsteal` (host network, порты 80/443) → reverse proxy → `hexacms_web` (:3000)
- `hexacms_web` (Nginx) → PHP-FPM / FastAPI / статика
- `hexacms_app` (PHP 8.1-FPM)
- `hexacms_api` (FastAPI + uvicorn)
- `hexacms_db` (PostgreSQL 16)

---

## 5. Стек

| Компонент | Технология | Версия |
|-----------|-----------|--------|
| Публичный сайт | PHP (vanilla) | 8.1+ |
| Фронтенд админки | React + TypeScript + Vite + Tailwind | 18 / 5 / 6 / 3 |
| UI-библиотека | shadcn/ui (Radix UI + Lucide) | — |
| Бэкенд админки | FastAPI + SQLAlchemy async + PyJWT + Pydantic v2 + structlog | — |
| База данных | PostgreSQL | 16 |
| Веб-сервер (внешний) | nginx + njs (selfsteal) | — |
| Веб-сервер (CMS) | nginx (alpine) | — |
| Инфраструктура | Docker Compose | — |

---

## 6. Что откуда берется (паритет с Remnawave)

### Из `remnawave-admin-main` скопировано 1:1

| Компонент | Путь в эталоне | Путь в CMS |
|-----------|---------------|-----------|
| Layout (Header + Sidebar) | `web/frontend/src/components/layout/` | `web/frontend/src/components/layout/` |
| 23 UI-компонента | `web/frontend/src/components/ui/` | `web/frontend/src/components/ui/` |
| Глобальные компоненты | CommandPalette, ConfirmDialog, AppearancePanel, EmptyState, ErrorBoundary, ExportDropdown | То же |
| Zustand store | `useAppearanceStore`, `useFiltersStore` | То же |
| lib/ | `utils`, `useFormatters`, `export`, `useTabParam`, `mutationToast` и др. | То же |
| Backend-структура | `web/backend/` (api, core, schemas, tests) | То же |

### Осознанные отклонения (см. ADR-002)

| Аспект | В Remnawave | В CMS | Причина |
|--------|-------------|-------|---------|
| Формат ответа | `{data}` / `{detail}` | `{success, data}` / `{success, error}` | PHP-совместимость, React depends |
| Версия API | `/api/v2`, `/api/v3` | `/api/v1` | Независимое версионирование |
| models/ | нет (control-plane) | удалена (data-access в `core/db_helpers.py`) |
| RBAC | rbac.py + permissionStore | задел (только role) |
| auth | access+refresh токены | один JWT |

---

## 7. Эталон Remnawave

`C:\Users\Andre\Desktop\VPN\remnawave-admin-main` — копия оригинального репозитория `github.com/Case211/remnawave-admin`, синхронизирована через upstream (ветка `main`, 2150 коммитов, v5.2.0).

Используется как:
- Источник для копирования компонентов, layout, lib, store
- Референс для структуры backend (api + core + schemas)
- Канон визуального стиля

**Обновление:** `git pull upstream main` (если нужно подтянуть свежие изменения оригинала).

---

## 8. Ключевые файлы

### CMS — публичный сайт
| Файл | Назначение |
|------|-----------|
| `index.php` | Front-controller (маршрутизация на PHP) |
| `core/routes.php` | Все маршруты публичного сайта |
| `core/models/Post.php` | Модель постов |
| `templates/themes/hexaveil/theme.php` | Конфиг темы (настройки, виджеты) |
| `templates/themes/hexaveil/` | Шаблоны лендинга и блога |
| `public/hexaveil/css/style.css` | Стили темы |
| `public/css/panel/*.css` | Дизайн-система админки (исторический, не используется) |

### CMS — админка (React SPA)
| Файл | Назначение |
|------|-----------|
| `web/frontend/src/App.tsx` | Роутинг React SPA |
| `web/frontend/src/pages/*.tsx` | Все страницы админки |
| `web/frontend/src/api/*.ts` | API-клиенты |
| `web/frontend/src/components/layout/Sidebar.tsx` | Навигация |
| `web/frontend/src/index.css` | Дизайн-система Remnawave |
| `web/frontend/vite.config.ts` | Прокси `/api` → FastAPI |

### CMS — бэкенд (FastAPI)
| Файл | Назначение |
|------|-----------|
| `web/backend/main.py` | FastAPI app + CORS + middleware |
| `web/backend/api/v1/*.py` | 15 роутеров (все API-эндпоинты) |
| `web/backend/core/config.py` | Pydantic-настройки (.env) |
| `web/backend/core/security.py` | JWT (совместим с PHP) |
| `web/backend/schemas/*.py` | 13 per-domain Pydantic-схем |
| `web/backend/requirements.txt` | Зависимости |

---

## 9. Известные ограничения / TODO

| Проблема | Описание |
|----------|---------|
| `notifications.ts` | Рабочие только `list/unreadCount/markRead`; SMTP/alert-rules/channels — задел без backend |
| `clientLogger.init()` | Не вызывается (нет эндпоинта `/api/logs/frontend`) |
| `response_model=` | Не включён для `schemas/*` (конфликт с PHP-конвертом `{success, data}`) |
| RBAC | `permissionStore` есть, матрицы прав нет |
| Сбор нод Diagnostics | Не настроен (`nodes: []`) |
| PHP bridge | Finance / Diagnostics / Preferences — всё ещё на PHP (план: перенести на FastAPI) |
| `/admin/logout` | Не реализован для SPA (только PHP-сессия) |

---

## 10. Прод (85.198.99.102)

**Важные особенности:**
- Порт 80/443 заняты `nginx-selfsteal` (host network, для Xray Reality)
- CMS слушает на порту 3000, доступна через reverse proxy от selfsteal
- Деплой через `git pull` + `docker compose up -d --build`
- `docker-compose.override.yml` (gitignored) с `web.ports: ["3000:80"]` — защита от занятия порта 80

**Не трогать:**
- `nginx-selfsteal` (host network, порты 80/443)
- `remnanode` (Xray Reality)
- `/opt/remnawave-panel/`, `/opt/remnanode/`, `/opt/nginx-selfsteal/`
- Контейнеры на 144.31.156.172 (панель, бот, кабинет)

---

## 11. Ссылки

- `docs/decisions/ADR-001-panel-design-system.md` — дизайн-система админки
- `docs/decisions/ADR-002-remnawave-structure-parity.md` — структурный паритет с Remnawave
- `CONTRIBUTING.md` — правила коммитов
- `DEPLOY.md` — инструкция по деплою
- `AGENTS.md` — инструкции для ИИ-агентов
- `PROJECT.md` — полное описание проекта (сводный)