# ADR-002: Структурный паритет с Remnawave (Вариант C)

## Status

Accepted

## Date

2026-10-09

## Context

CMS NewWeb и `remnawave-admin-main` развиваются раздельно, но должны быть
**взаимно переносимы**: владелец хочет свободно копировать модули/страницы
из Remnawave в CMS (и наоборот), не переписывая их каждый раз.

Фактическое состояние до ADR:

- **Frontend** `admin-react/` уже повторяет эталон `web/frontend` почти 1:1
  (23 UI-компонента, layout, `lib`/`store` частично) — но `package.json` и
  `locales/*.json` дословно скопированы, а `CommandPalette.tsx` и
  `notifications.ts` остались Remnawave-специфичными, из-за чего вели в 404.
- **Backend** `backend/` повторяет `web/backend` по каркасу (`api/`, `core/`,
  `schemas/`, `tests/`, `deps.py`, `main.py`), но имел пустую `models/` и
  `schemas/` только с `auth.py`/`common.py`.
- Эталон `web/backend` — **control-plane без ORM-моделей** (ходит во внешний
  Remnawave API); наш CMS работает с собственной БД, поэтому данные тянет
  через `core/db_helpers.py` (raw SQL).

## Decision

Принят **Вариант C** — «не двигать папки, довести внутренности до 1:1 с
эталоном». **Вариант B выполнен (2026-10-09):** `admin-react/` → `web/frontend/`,
`backend/` → `web/backend/`, импорты `web.backend.*`, обновлены Dockerfile,
docker-compose (dev+prod), nginx-alias, комментарии; проверено pytest (101),
`tsc`/`build`, `docker compose config` и `docker compose build api`.

### Копируем 1:1 из Remnawave

- `components/ui/` (23 shadcn), `components/layout/` (4), глобальные
  компоненты (`AppearancePanel`, `CommandPalette`, `ConfirmDialog`,
  `EmptyState`, `ErrorBoundary`, `ExportDropdown`, `OfflineIndicator`,
  `QueryError`, `ShortcutsDialog`) — идентичны.
- `lib/`: `utils`, `useFormatters`, `export` + перенесены `useTabParam`,
  `useUrlParam`, `useDeferredAction`, `useOrderPreference`, `useChartTheme`,
  `mutationToast`, `clientLogger`.
- `store/`: `useAppearanceStore`, `useFiltersStore` (идентичны) + добавлен
  `permissionStore` (адаптирован) и `useWebSocket`.
- **Backend:** `api/` + `core/` + `schemas/` per-domain (`post, category, page,
  user, menu, widget, log, media, theme, setting, notification, dashboard,
  finance`) + `api/deps.py` (AdminUser dataclass), `errors.py` (`E.*`),
  `config.py` (pydantic-settings), `logging_config.py` (structlog).

### Осознанные отклонения (не копируем)

| Аспект | Remnawave | CMS | Причина |
|---|---|---|---|
| Формат ответа | `{data}` / `{detail}` | `{success,data}` / `{success,error}` | PHP-совместимость, React зависит; смена сломала бы все страницы |
| Версия API | `/api/v2`, `/api/v3` | `/api/v1` | независимое версионирование; не мешает переносу тел роутеров |
| `models/` | отсутствует | удалён | в эталоне моделей нет; data-access остаётся в `core/db_helpers.py` |
| RBAC | `rbac.py` + permissionStore с матрицей | нет (только `role`) | в CMS нет RBAC-матрицы; `permissionStore` — задел |
| `authBridge` | access+refresh токены | один JWT | иная токен-архитектура CMS |
| `plugins/`, `types/violations.ts`, `useOpenUser` | есть | нет | Remnawave-специфика (плагины, uuid пользователей) |
| `models/`, `shared/`, `node-agent/`, `src/` (бот) | есть | нет | отдельные подсистемы Remnawave |

## Consequences

**Плюсы:** код взаимно переносим; UI совпадает по `data-*`/классам; backend
повторяет модули и паттерны эталона; ноль риска для работающего прода (папки
не двигались).

**Минусы / долг:**

- Формат ответов остаётся несовместимым с Remnawave-фронтендом — при переносе
  Remnawave-страниц может потребоваться адаптер/обёртка.
- `schemas/*` пока не подключены как `response_model=` (риск из-за конверта и
  лишних полей) — включать точечно.
- `clientLogger` шлёт на `/api/logs/frontend`, которого в backend нет
  (вызов обёрнут в `try/catch`; `init()` не вызывается).
- Корень репозитория ещё не повторяет layout эталона — это Вариант B.

## Ссылки

- План: `docs/plans/2026-10-09-variant-c-remnawave-parity.md`
- Архитектура и история: `docs/ARCHITECTURE.md`
- Эталон: `remnawave-admin-main/web/{frontend,backend}/`
