# Ченжлог: редактируемая тех.история + backfill 24.10.2026

Дата: 2026-11-15 · Статус: план · Затрагивает: `web/backend/api/v1/docs.py`, `web/frontend/src/pages/ChangelogViewer.tsx`, `web/frontend/src/api/docs.ts`, `db/postgres/migrations/`.

## 1. Корневая причина

1. Бэкенд: `DOCUMENTS["history"]["editable"] = False` (`web/backend/api/v1/docs.py:48`); guards возвращают FORBIDDEN на POST `:347-349`, PUT `:390-392`, DELETE `:433-435`.
2. History не имеет хранилища: `GET /docs/{name}/entries` читает файл и отдаёт одной синтетической записью `id:0` (`docs.py:329-337`); записи в БД нет, писать некуда.
3. Фронтенд: `isEditable = activeTab === 'changelog'` (`ChangelogViewer.tsx:199`), кнопки «Импорт/Экспорт/Новая запись» скрыты для history (`:215-258`); history рендерится read-only (`:337-338`, `renderHistoryView :458-504`).
4. `also_history` — мёртвый флаг: принимается в `EntryIn` (`docs.py:58`) и отправляется фронтом (`ChangelogViewer.tsx:136`), но в `create_entry` (`docs.py:340-379`) не читается.
5. Мёртвый код: `get_doc` после `return` (`docs.py:289-294`) недостижим — удалить.
6. Файл и БД расходятся: changelog в БД (`changelog_entries`), файл `docs/CHANGELOG_CMS.md` — только источник первичного импорта; history — только файл.

## 2. Модель данных: варианты и выбор

- **(a) Один markdown-документ в БД** (`docs_documents(name, content, updated_at)`) + полнотекстовый редактор. Плюс: структура секций/таблиц сохраняется 1:1, экспорт тривиален. Минус: нет CRUD отдельных записей, `also_history` = только append в конец, удаление блока — ручная правка.
- **(b) Плоские записи в `changelog_entries` + колонка `doc`.** Минус: ломает структуру `## N. Фаза` + таблицы; требует `WHERE doc='changelog'` во всех существующих выборках (`docs.py:272-274, 309-311, 357, 472-474`), риск сломать импорт/экспорт; таблица перестаёт быть «лентой».
- **Выбор: гибрид (a) + append-блоки.** Базовый документ — `docs_documents` (структура неприкосновенна, редактируется целиком); дополнения — записи `history_entries` (CRUD, `also_history`); при рендере/экспорте блоки добавляются секцией `## Дополнения` в конец. Структура сохранена, пользователь может вносить/править/удалять информацию точечно.

## 3. Backend (`web/backend/api/v1/docs.py`)

| Метод/путь | Изменение | Ошибки |
|---|---|---|
| `GET /api/docs/{name}` | history: читать `docs_documents` (если пусто — seed из файла), `editable: true`, добавить `updated_at`; changelog без изменений | 404 NOT_FOUND |
| `GET /api/docs/history/entries` | `data.document={raw,html,updated_at}` + `data.entries` = блоки `history_entries` (date/time/author/title/body/origin), `editable:true` | 404 |
| `POST /api/docs/history/entries` | вставка в `history_entries`; `EntryIn`, `also_history` игнорируется | 400 INVALID_INPUT, 500 DB_ERROR |
| `PUT/DELETE /api/docs/history/entries/{id}` | CRUD блока; `EntryUpdate` без изменений | 404, 500 |
| `PUT /api/docs/history` | **новый**: `DocumentUpdate{content: str(1..1_000_000), expected_updated_at: str\|None}` → `{success,data:{updated_at}}`; `UPDATE docs_documents ... WHERE name='history'`; при несовпадении `expected_updated_at` — 409 | 400, 404, 409 `CONFLICT` |
| `POST /api/docs/history/import` | **новый**: multipart `.md` → заменить `content` (перезапись, UI подтверждает); блоки не трогать | 400 INVALID_INPUT, 413 FILE_TOO_LARGE |
| `GET /api/docs/history/export` | **новый**: `content` + секция `## Дополнения` из блоков, `History...md` | — |
| `POST /api/docs/changelog/entries` | при `also_history=true` — вторая вставка в `history_entries` (`source_changelog_id`, `origin='changelog'`) | 500 DB_ERROR при сбое |
| `/api/docs/changelog/import|export` | без изменений; `_import_file_to_db` не трогает `docs_documents`/`history_entries` | — |

**`also_history` семантика.** Дописывается блок в `history_entries` (не в файл): `entry_date/entry_time/author` из changelog-записи, `title`, `body`, `origin='changelog'`, `source_changelog_id=<id>`. Формат блока при рендере/экспорте:
```
### ДД.ММ.ГГГГ ЧЧ:ММ — <title>

*Автор: <author> · источник: лента изменений #<id>*

<body>
```
Секция-контейнер: `\n\n---\n\n## Дополнения\n\n` + блоки по `entry_date, entry_time, id` ASC. `UNIQUE(source_changelog_id)` + `ON CONFLICT DO NOTHING` — идемпотентно (NULL-значения не конфликтуют).

**Атомарность.** Changelog-запись и history-блок — один `session`, один `commit()`; при исключении `rollback()` и `return api_error(500, E.DB_ERROR, ...)`. Существующие guard-ответы оставить в конверте `{success:false}` (совместимость), новые PUT/import — через `api_error` (как `auth.py:45`). В `errors.py` добавить `CONFLICT = "CONFLICT"` (после `ALREADY_EXISTS`).

**Seed/автоимпорт.** `ensure_docs_tables()` + `seed_history_document()` в lifespan рядом с `ensure_changelog_table`/`migrate_file_to_db` (`main.py:51-55`): `INSERT INTO docs_documents(name, content) VALUES ('history', <file>) ON CONFLICT (name) DO NOTHING` — БД выигрывает после первой правки, ошибки только логируются.

**Совместимость.** `/docs/list` теперь отдаёт `history.editable=true`. Старый ответ history/entries (одна запись с raw в body) заменяется на `document`+блоки — единственный потребитель `ChangelogViewer`; внешних клиентов нет. Changelog-эндпоинты, импорт/экспорт `.md` и формат `_generate_md` не меняются.

## 4. Миграция SQL

⚠ `004-support-foundation.sql` уже занят — новый файл **`db/postgres/migrations/005-docs-history.sql`**. Идемпотентно:

```sql
CREATE TABLE IF NOT EXISTS docs_documents (
    name TEXT PRIMARY KEY, content TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS history_entries (
    id SERIAL PRIMARY KEY, entry_date DATE NOT NULL,
    entry_time TIME NOT NULL DEFAULT '12:00:00',
    author VARCHAR(255) NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '',
    origin VARCHAR(16) NOT NULL DEFAULT 'manual',
    source_changelog_id INTEGER UNIQUE REFERENCES changelog_entries(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_history_entries_date ON history_entries(entry_date, entry_time);
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='update_history_entries_updated_at') THEN
    CREATE TRIGGER update_history_entries_updated_at BEFORE UPDATE ON history_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF; END $$;
```
`ensure_docs_tables()` повторяет этот DDL (как `ensure_changelog_table :178-215`), миграция — для ручного/CI применения.

## 5. Frontend

- `web/frontend/src/api/docs.ts`: `DocEntry` + `origin?: 'manual'|'changelog'`; `EntriesResponse.data.document?: {raw,html,updated_at}`; новые `putDocument(name, content, expectedUpdatedAt?)`, `importDocument(name, file)`, `getExportUrl(name = 'changelog')` (обратная совместимость вызова на `ChangelogViewer.tsx:182`).
- `ChangelogViewer.tsx`:
  - убрать `isEditable = activeTab === 'changelog'` (`:199`); хранить `editable` из ответа (`:76`).
  - history: `loadHistory()` = `getEntries('history')` → `historyDoc` + блоки; кнопки вкладки: «Редактировать документ» (`HistoryDocumentEditor`), «Импорт .md» (confirm «перезапишет текст документа»), «Экспорт .md», «Новая запись»; changelog-кнопки — только на своей вкладке.
  - `renderHistoryView(document, blocks, ...)`: документ через `dangerouslySetInnerHTML` в `prose` (html с бэка, как `get_doc`), ниже карточки блоков с Pencil/Trash2 и `ConfirmDialog` удаления (как `:357-367`).
  - поиск фильтрует только блоки, документ виден всегда.
- **Новый** `web/frontend/src/components/changelog/HistoryDocumentEditor.tsx`: Dialog, `Textarea` (monospace, ~24 строки, `h-[60vh]`), табы «Редактирование/Предпросмотр», счётчик символов; сохраняет с `expected_updated_at`; на 409 — сообщение «документ изменён» + кнопка «Перезагрузить».
- `ChangelogEntryModal.tsx`: новый prop `docName?: 'changelog'|'history'` (default changelog); для history скрыть блок `also_history` (`:228-236`), тексты «Добавьте запись в техническую историю».
- `mdToHtml` (`ChangelogEntryModal.tsx:98-119`) вынести в `web/frontend/src/lib/markdown.ts` и переиспользовать в редакторе.

## 6. Backfill 24.10.2026

9 коммитов (`git log --since=2026-10-23 --until=2026-10-26`): `8800aa6`, `ace9b42`, `d9318d6`, `a358997`, `b0d6e5d`, `3c172a6`, `f52d053`, `f99cb3e`, `200ef03`. В `CHANGELOG_CMS.md` записей за 24.10 нет (11 записей, последняя 15.11 — строки 163-190, только проверить полноту, не дублировать).

Создать через `POST /api/docs/changelog/entries` (date `24.10.2026`, time `03:24:00`, author `Администратор`, **`also_history: true`**), title «🛠 Саппорт: фазы 0–2c, Telegram-канал и форум-мост», body:
- Фаза 0: 16 таблиц `support_*`, API очереди, WS, поллер Bedolaga, тесты (`8800aa6`, `ace9b42`); фронт «Очередь» + WS-клиент (`d9318d6`).
- Фаза 1: TG-личка — attachments API, поллер, outbox/без окна, тесты +2078 (`a358997`); docs/TASK (`b0d6e5d`).
- Фаза 2b: JOIN attachment, превью/скачивание, reply с файлами, тесты +96, пересборка dist (`3c172a6`).
- Фаза 2c: форум-мост — `tg/forum.py` +330, `tg/media.py` +89, `poller.py` переработан (203), `workers/api`, `test_support_tg_forum.py` +431, `docs/INTEGRATION-SUPPORT.md`, `TASK.md` (`f52d053`, `f99cb3e`, `200ef03`).

**Защита от дублей.** Перед вставкой: `SELECT 1 FROM changelog_entries WHERE entry_date='2026-10-24' AND title ILIKE '%Саппорт%'` — если есть, пропустить; блок history идемпотентен через `UNIQUE(source_changelog_id)`. После вставки — `GET /api/docs/changelog/export` и записать результат в `docs/CHANGELOG_CMS.md` (иначе следующий импорт старого файла удалит запись: `_import_file_to_db` делает `DELETE FROM changelog_entries`, `docs.py:225`).

## 7. Шаги реализации

1. **SQL+DDL**: `005-docs-history.sql`; `ensure_docs_tables()`/`seed_history_document()` в `docs.py`; вызов в `main.py:51-55`. Критерий: повторный запуск без ошибок, таблицы/триггер/индекс есть.
2. **Хелперы**: `_format_history_block()`, `_compose_history_md(doc, blocks)`, `_get_history_document(db)` (seed из файла), `_history_entries(db)`; удалить мёртвый код `:289-294`. Критерий: unit-тесты формата блока/композиции.
3. **Чтение**: history в `get_doc` и `list_entries` из БД, `editable:true`, `document` в ответе. Критерий: `GET` отдаёт файл при пустой БД и БД после seed.
4. **Запись**: CRUD history-блоков (branch по `name`), `PUT /docs/history`, import/export history; guards по `editable` оставить, но history сделать editable. Критерий: 200/400/404/409 по таблице §3.
5. **`also_history`**: вторая вставка в `create_entry`, один commit, `ON CONFLICT DO NOTHING`, 500+rollback при сбое. Критерий: одна changelog-запись → ровно один блок; повтор с тем же id не дублирует.
6. **Тесты** `web/backend/tests/test_docs_history.py`: формат блока, композиция, `also_history` (мок/транзакция), 409 stale. Критерий: `pytest` зелёный.
7. **API-клиент** `docs.ts` + `lib/markdown.ts`. Критерий: `tsc --noEmit`.
8. **UI** `HistoryDocumentEditor.tsx`, правки `ChangelogViewer.tsx`, `ChangelogEntryModal.tsx` (`docName`). Критерий: ручной чек-лист §8.
9. **Backfill** 24.10 через API (`also_history=true`), экспорт changelog → `docs/CHANGELOG_CMS.md`; проверить запись 15.11 на полноту. Критерий: в ленте 12 записей, в history — блок 24.10, повторный запуск не создаёт дубль.
10. **Документация**: `CODEBASE_INDEX.md` (§1.25 `:290-300`, §3.13 `:839-855`, inline-схемы `:432`), `ARCHITECTURE.md` (хранилище docs), `docs/decisions/ADR-004-docs-storage.md`. Критерий: индекс совпадает с фактическими сигнатурами.

## 8. Проверка

```powershell
cd web/backend; python -m pytest -q
cd web/frontend; npm run typecheck; npm run build
# миграция (dev): psql $env:DATABASE_URL -f db/postgres/migrations/005-docs-history.sql  (дважды — идемпотентность)
```
UI-чек-лист: history → «Редактировать документ» → правка → preview → сохранить → перезагрузить (видна); параллельная вкладка со старым `updated_at` → 409 и сообщение; «Новая запись» в history → карточка + edit/delete; changelog «Новая запись» + «Также в тех.историю» → блок в history с датой/автором/заголовком; «Импорт .md» changelog не стирает блоки history; «Экспорт .md» history содержит `## Дополнения`; dist пересобран и закоммичен.

## 9. Definition of Done (AGENTS.md)

- `docs/CODEBASE_INDEX.md`: §1.25 — новые/изменённые роуты (`PUT /docs/history`, `POST /docs/history/import`, `GET /docs/history/export`, `also_history` в POST entries, `editable:true`); §3.13 — `putDocument/importDocument/getExportUrl(name)`; inline-схемы — `DocumentUpdate`.
- `docs/ARCHITECTURE.md`: docs-хранилище = `docs_documents` + `history_entries`, файлы — seed/экспорт.
- ADR: **да**, `docs/decisions/ADR-004-docs-storage.md` (файл → БД, гибрид документ+блоки, атомарность `also_history`).
- `PROJECT.md` не меняется (нет изменений нод/портов/ENV).

## Риски

1. **Импорт changelog затирает ручные записи**: `_import_file_to_db` делает `DELETE FROM changelog_entries` (`docs.py:225`); после backfill обязательно коммитить экспортированный `CHANGELOG_CMS.md`, иначе повторный импорт старого файла удалит 24.10.
2. **Потеря блоков при переимпорте**: `ON DELETE SET NULL` обнуляет `source_changelog_id`; новые импортированные записи получат новые id — блоки останутся, но связь с записью теряется (дубли возможны только вручную).
3. **Конкурентное редактирование документа**: без `expected_updated_at` последний сохранивший затрёт чужое; поэтому 409 обязателен, а UI должен перезагружать документ, а не молча повторять.
4. **Размер документа**: `HISTORY_TECHNICAL.md` 439 строк; лимит 1 МБ и рендер всего HTML в DOM — приемлемо, но при росте нужен лимит/пагинация блоков.
5. **Старый формат ответа history/entries** меняется (была одна запись id:0) — если внешние скрипты читают `entries[0].body` как raw, они сломаются; в репозитории таких потребителей нет (проверено grep по `docs/history`).
