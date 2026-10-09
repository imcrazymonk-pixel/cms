# HexaVeil CMS — Архитектура и история

> Единый документ проекта: что это, зачем менялось, как устроено сейчас.
> Заменяет `docs/MIGRATION_BRIEF.md`, `docs/MIGRATION_TO_REMNAWAVE_STACK.md`,
> `docs/MIGRATION_STATUS.md` (эти три описывали процесс миграции, который завершён).

## Что это

Сайт VPN-сервиса **HexaVeil**:

- **Публичная часть** — лендинг + блог. PHP (vanilla, без фреймворков) + PostgreSQL. Тема `hexaveil`.
- **Админ-панель** — React SPA (Vite + TypeScript + shadcn/ui) + **FastAPI** (JSON API). Визуал — копия Remnawave.

## Как к этому пришли (эволюция)

1. **PHP CMS (SSR)** — лендинг, блог, PHP-админка.
2. **Фаза 0** — JSON-API на PHP для React-фронтенда.
3. **Фаза 1** — React SPA-админка с визуалом 1:1 как в `remnawave-admin`.
4. **Фаза 2** — PHP-API заменён на **FastAPI** (этапы M0–M8). PHP-админка **удалена**; PHP обслуживает только публичный сайт.
5. **Вариант C** — внутренности `web/frontend` и `web/backend` приведены к 1:1 с Remnawave (per-domain `schemas/`, `lib`/`store`/`types`, единые паттерны) — см. ADR-002.
6. **Вариант B** — стандартный layout Remnawave: `web/frontend` + `web/backend`; импорты `web.backend.*`.

## Архитектура сейчас

```
NewWeb/
├── index.php                  # front-controller публичного сайта
├── core/                      # PHP-ядро публичного сайта (Router, TemplateEngine, Database, модели контента)
├── templates/themes/          # PHP-темы (hexaveil, default)
├── public/                    # ассеты темы, uploads, legacy css/panel
├── config/                    # PHP-конфиг (env-aware)
├── web/
│   ├── frontend/              # React SPA админки (Vite, TS, shadcn/ui, Tailwind)
│   └── backend/               # FastAPI (админский JSON API)
├── db/                        # схема PostgreSQL, миграции, дампы (см. ниже)
├── docs/                      # этот файл + ADR (decisions/)
├── plugins/, install/, tools/ # публичный сайт / установщик / сбор диагностики
├── Dockerfile, docker-compose*.yml, .docker/   # инфраструктура
└── remnawave-admin-main/      # эталон Remnawave (gitignored, дубликат внешней копии)
```

### Потоки запросов (прод)

```
браузер
  ├── /            → PHP (лендинг + блог)
  ├── /admin/*     → React SPA (web/frontend/dist)
  └── /api/*       → FastAPI (web/backend)
                     + bridge: /admin/finance/api/*, /admin/diagnostics/api/*, /admin/settings/save-*
```

nginx `nginx-selfsteal` (host :80/:443) → `hexacms_web` (:3000) → PHP-FPM / FastAPI.

## Стек

- **PHP** 8.1 (публичный сайт), PostgreSQL 16.
- **Frontend:** React 18, TypeScript, Vite, Tailwind, shadcn/ui (Radix), TanStack Query, Zustand, i18next.
- **Backend:** FastAPI, SQLAlchemy async, PyJWT, Pydantic v2, structlog.
- **Docker Compose:** сервисы `app` (PHP-FPM), `api` (FastAPI), `web` (nginx), `db` (PostgreSQL).

## Ключевые решения

- **ADR-001** `docs/decisions/ADR-001-panel-design-system.md` — дизайн-система админки (Remnawave-стиль).
- **ADR-002** `docs/decisions/ADR-002-remnawave-structure-parity.md` — структурный паритет с Remnawave; что копируем 1:1, что осознанно отклоняем.

## Деплой

См. `DEPLOY.md` (локально и прод `85.198.99.102` / `hexaveil.xyz`).

## Известные ограничения / TODO

- `notifications.ts` — рабочие только `list/unreadCount/markRead`; SMTP/alert-rules/channels — задел без backend.
- `clientLogger.init()` не вызывается (нужен эндпоинт `/api/logs/frontend`).
- `response_model=` для `web/backend/schemas/*` не включён (PHP-конверт `{success,data}`).
- RBAC: `permissionStore` есть, матрицы прав нет.
