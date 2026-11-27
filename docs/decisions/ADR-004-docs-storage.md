# ADR-004: Хранилище документации — документ + блоки

## Status

Accepted

## Date

2026-11-15

## Context

До этого решения техническая история (`HISTORY_TECHNICAL.md`) была только файлом:

- в реестре документов стоял `editable: false`, POST/PUT/DELETE возвращали `FORBIDDEN`;
- `GET /api/docs/history/entries` читал файл и отдавал одну синтетическую запись `id: 0`;
- отредактировать документ из админки было нельзя, а `also_history` в `EntryIn`
  принимался фронтендом, но в `create_entry` не читался — флаг был мёртвым;
- changelog уже жил в БД (`changelog_entries`), history — только в файле, поэтому
  два документа имели разную модель хранения.

## Decision

1. **Гибрид: базовый документ + блоки.**
   `docs_documents(name PK, content, updated_at)` хранит markdown технической истории
   целиком; `history_entries` хранит блоки-дополнения (ручные и копии записей ленты).
   Структура файла (`## N. Фаза`, таблицы) сохраняется 1:1, а точечные дополнения
   не ломают её.
2. **БД — источник истины после первого старта.** Файлы `docs/*.md` используются
   только как seed (`seed_history_document`, `migrate_file_to_db`) и как цель экспорта
   (`GET /api/docs/history/export`, `GET /api/docs/changelog/export`). Changelog
   по-прежнему хранится в `changelog_entries`.
3. **Оптимистичная блокировка документа.** `PUT /api/docs/history` принимает
   `DocumentUpdate{content, expected_updated_at?}` и выполняет
   `UPDATE ... WHERE name='history' AND updated_at = :current`. Несовпадение или
   гонка (0 строк) → `409 CONFLICT`; UI перезагружает документ, а не повторяет запись.
4. **Атомарность `also_history`.** В `POST /api/docs/changelog/entries` запись ленты
   и блок истории вставляются в одной сессии и одном `commit()`. Блок получает
   `origin='changelog'` и `source_changelog_id`; повтор идемпотентен через
   `ON CONFLICT (source_changelog_id) DO NOTHING`. Любая ошибка → `rollback()` и
   `500 DB_ERROR`.
5. **Импорт history не трогает блоки.** `POST /api/docs/history/import` заменяет
   только `docs_documents.content` (`.md`, UTF-8, ≤1 МБ); `history_entries` остаются.
6. **DDL дублируется.** `ensure_docs_tables()` идемпотентно создаёт таблицы, индекс
   и триггер при старте, повторяя SQL миграции `005-docs-history.sql`. Сам SQL-файл
   в репозиторий не добавлен (каталог `db/postgres/*` недоступен в рамках задачи);
   он применяется вручную из плана §4.

## Consequences

Плюсы:

- техническую историю можно редактировать из админки, не теряя структуру файла;
- `also_history` наконец работает: запись ленты и блок истории не расходятся;
- экспорт остаётся обычным markdown-файлом, блоки добавляются секцией `## Дополнения`;
- единая модель для обоих документов: БД правит, файл — seed/экспорт.

Минусы / риски:

- `POST /api/docs/changelog/import` делает `DELETE FROM changelog_entries`; после
  переимпорта блоки истории остаются, но `source_changelog_id` обнуляется
  (`ON DELETE SET NULL`) — связь с записью ленты теряется;
- повторный импорт старого `CHANGELOG_CMS.md` может удалить записи, добавленные
  после экспорта, поэтому экспортированный файл нужно коммитить;
- документ рендерится целиком в DOM (лимит 1 МБ); при росте понадобится пагинация
  блоков или лимит размера;
- старый ответ `history/entries` (одна запись `id: 0` с raw в `body`) заменён на
  `document` + блоки; внешних потребителей в репозитории нет, но сторонние скрипты
  могли читать `entries[0].body`;
- DDL живёт в двух местах (`ensure_docs_tables()` и SQL-миграция) и требует
  синхронного изменения.

## Alternatives

- **Только файлы.** Отклонено: файл нельзя безопасно редактировать из админки,
  нет optimistic lock и атомарного `also_history`, а права на запись зависят от ФС.
- **Плоские записи в `changelog_entries` с колонкой `doc`.** Отклонено: ломает
  структуру `## N. Фаза` и таблицы, требует `WHERE doc='changelog'` во всех
  существующих выборках и превращает «ленту» в свалку разнородных записей.
- **Полностью новый редактор без блоков.** Отклонено: теряется точечный CRUD
  дополнений и копирование записей ленты; любая правка требовала бы переписывать
  весь документ.

## Ссылки

- План: `docs/plans/2026-11-15-changelog-history-editable.md` (`§3`, `§4`, `§9`)
- Код: `web/backend/api/v1/docs.py`, `web/frontend/src/api/docs.ts`,
  `web/frontend/src/pages/ChangelogViewer.tsx`,
  `web/frontend/src/components/changelog/HistoryDocumentEditor.tsx`,
  `web/frontend/src/lib/markdown.ts`
- ADR-001 (дизайн-система), ADR-002 (паритет с Remnawave), ADR-003 (прокси и интеграции)
