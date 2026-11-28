# Саппорт — Этап C: SLA, шаблоны, присутствие, аналитика, команда

**Статус:** выполнен 2026-11-28 (C1–C5; pytest 722, tsc/build зелёные).
**Опирается на:** `docs/plans/2026-11-28-support-completion.md` §5 (Этап C), `docs/plans/2026-11-28-support-stage-b.md` (формат), `docs/AI-SUPPORT.md` (attention/SLA/presence).

---

## 0. Факты кодовой базы

- `db/postgres/migrations/004-support-foundation.sql:188-250` — таблицы `support_operator_presence` (PK `actor_key,conversation_id`), `support_customer_note`, `support_template` (`shortcut UNIQUE`, `uses`), `support_sla_policy` (сиды low/normal/high/urgent), `support_audit_log`. Кода нет.
- `support_conversation` хранит `first_inbound_at`, `first_response_at`, `status`, `priority`, `assignee_id`.
- `support_message` **не хранит автора-оператора** — только `author='agent'`. Аналитика по операторам без этого невозможна ⇒ миграция добавляет `author_id`.
- `web/backend/core/support/store/*` — raw SQL, сессия на вызов, коммит в фасаде; `web/backend/api/v1/support/*` — `{success,data}` + коды `core/errors.py`.
- `web/backend/core/support/workers.py` — точка запуска фоновых циклов (`start_support_workers`).
- `web/backend/core/support/events.py` — `EventKind` (in-memory, один uvicorn-воркер).
- Фронт: `/support/{sla,templates,analytics,team}` — `SupportPlaceholder` (`App.tsx:139-144`).
- Следующий номер миграции — **008**: 007 зарезервирован под docs-history (`docs/plans/2026-11-15-changelog-history-editable.md`), файла 007 в каталоге нет.

## 1. Решения

1. **SLA-состояние** — новая таблица `support_sla_event` (одна строка на `conversation_id+kind`), сбрасывается при повторном открытии диалога. Политики берутся из `support_sla_policy` по `priority`.
2. **Уведомления** — по умолчанию **в панели** кадром WS `sla_alert`; дополнительно — сообщение в staff-группу форум-моста, если мост поднят. Новых ENV/ключей не вводим.
3. **Лимит уведомлений** — `UPDATE … FOR UPDATE SKIP LOCKED … LIMIT 5` за цикл, `notified_at` гарантирует «один раз на событие».
4. **Шаблоны** — `shortcut` `^[a-z0-9][a-z0-9_-]{0,31}$`, уникален; `category` свободная строка; правят все админы (нет ролей).
5. **Заметки** — только о клиенте (`support_customer_note`), внутренние; заметка ИИ (`operator_note`) не дублируется.
6. **Присутствие** — HTTP-heartbeat `viewing|typing` + WS-кадр; TTL 120 с; запись не чаще 5 с на пару.
7. **Аудит** — `assign`, `state`, `reply`, `template.create/update/delete`, `note.create/delete`, `ai.pause/resume`, `sla.notify`; ошибка аудита не ломает действие.
8. **Аналитика** — `percentile_cont` (медиана/P90) только по сообщениям `author='agent'` с `author_id`; ИИ (`bot`) исключён из человеческих метрик.
9. **Экраны** — 4 страницы в существующей дизайн-системе, без новых npm-зависимостей.

## 2. Миграция `008-support-stage-c.sql`

Идемпотентно (`IF NOT EXISTS`), без изменения прод-конфигов:

```sql
ALTER TABLE support_message
    ADD COLUMN IF NOT EXISTS author_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_support_message_author
    ON support_message (author_id, created_at) WHERE direction='out';

ALTER TABLE support_template ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE support_template ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE support_template ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
CREATE INDEX IF NOT EXISTS idx_support_template_category ON support_template (category, title);

CREATE TABLE IF NOT EXISTS support_sla_event (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES support_conversation(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN ('first_response','resolution')),
    due_at          TIMESTAMPTZ NOT NULL,
    breached_at     TIMESTAMPTZ,
    notified_at     TIMESTAMPTZ,
    closed_at       TIMESTAMPTZ,
    UNIQUE (conversation_id, kind)
);
CREATE INDEX IF NOT EXISTS idx_support_sla_event_due
    ON support_sla_event (due_at) WHERE notified_at IS NULL AND closed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_support_presence_seen
    ON support_operator_presence (conversation_id, seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_audit_created
    ON support_audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_audit_action
    ON support_audit_log (action, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_customer_note_customer
    ON support_customer_note (customer_id, created_at DESC);
```

Схема применяется через `core/support/schema.py` (добавить 008 в список).

## 3. API (prefix `/api/support`)

| Метод | Путь | Тело/query | Ответ |
|---|---|---|---|
| GET | `/sla/policies` | — | `{items:[{name,first_response_minutes,resolution_minutes}]}` |
| PUT | `/sla/policies/{name}` | `{first_response_minutes>=1, resolution_minutes>=1}` | политика |
| GET | `/sla/overview` | `?days=7..90` | `{breaches:[{conversation_id,kind,due_at,overdue_minutes,notified_at,subject,priority}], totals:{first_response,resolution}, by_priority:[...]}` |
| GET | `/templates` | `?q<=200&category<=64` | `{items:[...],total}` |
| POST | `/templates` | `{shortcut,title<=120,body<=4000,category?<=64}` | шаблон; 409 `TEMPLATE_EXISTS` |
| PUT | `/templates/{id}` | те же поля | шаблон |
| DELETE | `/templates/{id}` | — | `{deleted:true}` |
| POST | `/templates/{id}/use` | — | `{id,uses}` |
| GET | `/customers/{customer_id}/notes` | — | `{items:[{id,text,actor_id,actor_name,created_at}]}` |
| POST | `/customers/{customer_id}/notes` | `{text 1..2000}` | заметка |
| DELETE | `/notes/{id}` | — | `{deleted:true}` |
| POST | `/presence` | `{conversation_id,state:viewing|typing}` | `{ok:true,throttled?:true}` |
| GET | `/presence/{conversation_id}` | — | `{items:[{actor_id,actor_name,state,seen_at}]}` |
| GET | `/audit` | `?action=&actor_id=&page=&per_page=` | `{items,total,page,per_page}` |
| GET | `/operators` | — | `{items:[{id,login,display_name,status,active_dialogs,replies_30d,present}]}` |
| GET | `/analytics` | `?days=7..365` | `{totals,by_day,by_channel,by_priority,first_response{median_minutes,p90_minutes,count},by_operator[],ai{...}}` |

Новые коды: `TEMPLATE_EXISTS`, `SLA_POLICY_NOT_FOUND`, `NOTE_NOT_FOUND`.

## 4. WS

- `sla_alert` — `{conversation_id, kind, due_at, overdue_minutes}` (только операторам; фронт инвалидирует `/sla/overview` и список).
- `presence` — `{conversation_id, actor_id, state}` после heartbeat (не чаще 5 с).

## 5. Backend-модули

- `store/templates.py`, `store/notes.py`, `store/presence.py`, `store/audit.py`, `store/sla.py`, `store/analytics.py` (+ методы фасада `SupportStore`).
- `api/v1/support/{sla,templates,notes,presence,analytics,team}.py`; регистрация в `api/v1/support/__init__.py`.
- `core/support/sla.py` — `SlaWatcher`: `sync_events()`, `claim_alerts(limit=5)`, `notify()` (WS + staff-группа).
- `core/support/audit.py` — `record(service, actor, action, …)` (best-effort).
- `core/support/workers.py` — `_sla_loop` каждые 60 с.
- `core/support/events.py` — `SLA_ALERT`, `PRESENCE`.
- `schema.py` — подключить 008; `conversations.record_outbound(author_id=…)` и reply-эндпоинт прокидывают `admin.id`.

## 6. Frontend

- `api/support.ts`: типы и методы по таблице §3.
- `pages/support/Sla.tsx` — политики (редактирование минут), сводка по приоритетам, список просрочек.
- `pages/support/Templates.tsx` — список + редактор + предпросмотр `body`.
- `pages/support/Analytics.tsx` — метрики, CSS-бары по дням, таблица операторов, блок ИИ.
- `pages/support/Team.tsx` — операторы (presence/нагрузка) + журнал аудита.
- `components/support/TemplatePicker`-подобный поповер в `MessageThread`: ввод `/shortcut` + кнопка «Шаблоны» → вставка в композер.
- `CustomerCard` — блок «Заметки» (добавить/удалить).
- `Queue` — присутствие: пинг `viewing` при открытии, `typing` при вводе (троттлинг 5 с), показ «смотрит: …».
- `App.tsx` — 4 маршрута без заглушек.

## 7. Тесты

| Файл | Что проверяет |
|---|---|
| `tests/test_support_templates.py` | валидация shortcut, дубль → 409, CRUD, инкремент `uses`, запись аудита |
| `tests/test_support_notes.py` | CRUD заметок, ACL по `customer_id`, пустой текст → 400 |
| `tests/test_support_presence.py` | heartbeat + TTL-фильтр, троттлинг, `GET` отдаёт только свежих |
| `tests/test_support_sla.py` | расчёт due по приоритету, `sync_events`, сброс при reopen, `claim_alerts` ≤5 и ровно один раз, закрытие события |
| `tests/test_support_analytics.py` | медиана/P90 только по `author='agent'`, исключение `bot`, суммы по дням/каналам |
| `tests/test_support_audit.py` | запись действий, фильтры, best-effort при ошибке store |
| `tests/test_support_operators.py` | список операторов, нагрузка, `present` |

## 8. Нарезка

- [x] **C1 — backend ядро:** миграция 008, store (шаблоны, заметки, присутствие, аудит), API, `author_id` в reply, тесты.
- [x] **C2 — SLA:** `support_sla_event`, `store/sla.py`, `SlaWatcher`, WS `sla_alert`, staff-группа, `/sla/*` API, тесты.
- [x] **C3 — аналитика и команда:** `store/analytics.py`, `/analytics`, `/operators`, `/audit`, тесты.
- [x] **C4 — фронтенд:** 4 страницы, шаблоны в композере, заметки в карточке, presence, кадры WS, роуты.
- [x] **C5 — приёмка:** `pytest`, `tsc`, `build`, `CODEBASE_INDEX`, `CHANGELOG`, `TASK.md`.

**Acceptance C1:** миграция применяется дважды без ошибок; шаблоны/заметки/присутствие/аудит работают через API; тесты зелёные.
**Acceptance C2:** просрочка фиксируется один раз, повторно после reopen; `/sla/overview` показывает актуальные.
**Acceptance C3:** метрики совпадают с ручным SQL на сиде; операторы без ролей.
**Acceptance C4:** все 4 экрана без `SupportPlaceholder`; `/shortcut` вставляет текст; ошибки показываются тостами.

## 9. Definition of Done

1. C1–C5 смёржены, `pytest`/`tsc`/`build` зелёные.
2. `CODEBASE_INDEX.md` — эндпоинты, модели, методы `support.ts`, кадры WS, таблицы 008.
3. `CHANGELOG_CMS.md` — запись «Саппорт: Этап C».
4. `TASK.md` — Этап C закрыт, следующий — D.
5. Ни одного `TODO` без владельца.

## 10. Открытые вопросы (с дефолтом)

1. **Канал SLA-уведомлений.** Дефолт: WS + staff-группа форум-моста. Если владелец захочет отдельный чат — добавляем ключ `support_sla_notify_chat_id` без миграции.
2. **Порог «просрочки» для resolution.** Дефолт: `first_inbound_at + resolution_minutes`, диалог закрыт — событие закрывается.
3. **Присутствие при нескольких вкладках.** Дефолт: последняя запись побеждает; TTL 120 с.
