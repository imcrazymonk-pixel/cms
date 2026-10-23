# Эталон Remnawave — карта для агентов

`remnawave-admin-main/` — внешний эталон (`github.com/Case211/remnawave-admin`, v5.2.0, ветка `main`).
Это **не часть проекта**. Правило: читать конкретный файл по пути, каталог не сканировать.

`node_modules` эталона закрыт в `.kilocodeignore` (406 МБ). Исходники доступны.

## Что откуда брать

| Нужно | Путь в эталоне |
|-------|----------------|
| UI-компоненты (23 шт., shadcn) | `web/frontend/src/components/ui/` |
| Layout (Header, Sidebar) | `web/frontend/src/components/layout/` |
| Глобальные компоненты | `web/frontend/src/components/` (AppearancePanel, CommandPalette, ConfirmDialog, EmptyState, ErrorBoundary, ExportDropdown, OfflineIndicator, QueryError, ShortcutsDialog) |
| Утилиты | `web/frontend/src/lib/` |
| Zustand-сторы | `web/frontend/src/store/` |
| API-клиенты | `web/frontend/src/api/` |
| Страницы | `web/frontend/src/pages/` |
| Стили и токены | `web/frontend/src/index.css` |
| Backend-роутеры | `web/backend/api/` |
| Backend-ядро | `web/backend/core/` |
| Pydantic-схемы | `web/backend/schemas/` |
| Прочие подсистемы | `src/`, `shared/`, `node-agent/` |

## Правила переноса

1. Сначала назови конкретный файл-источник, потом читай его (`@remnawave-admin-main/...`).
2. Адаптируй под CMS: конверт `{success, data}`, версия `/api/v1`, нет RBAC-матрицы.
3. Осознанные отклонения зафиксированы в `docs/decisions/ADR-002-remnawave-structure-parity.md`.
4. Не копируй `package.json`, `locales/*.json` дословно — они Remnawave-специфичны.
