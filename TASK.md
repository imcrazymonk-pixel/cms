# TASK — Фаза 0: фундамент «Саппорта» в CMS

> План согласован владельцем 2026-10-23. Полный контекст: `docs/INTEGRATION-SUPPORT.md`, `docs/AI-SUPPORT.md`.
> Исполнитель реализует ТОЛЬКО Фазу 0. Фаза 1 (поллер/очередь/WS) — следующими задачами.

## Цель фазы 0
Заложить схему БД и каркас модуля поддержки в стеке CMS, не ломая существующее API.
Код — на стиле CMS: FastAPI + SQLAlchemy async (raw SQL через `text()`), Pydantic v2,
формат ответов `{success,data}`, ошибки `E.*` через `api_error`, auth `get_current_admin`,
structlog. Идемпотентная схема применяется из lifespan (паттерн `ensure_changelog_table` в `api/v1/docs.py`).

## 1. Миграция `db/postgres/migrations/004-support-foundation.sql` + `ensure_support_schema()`

Один файл, идемпотентный (`CREATE TABLE IF NOT EXISTS`), `timestamptz DEFAULT now()`.

### Живые таблицы (фазы 0-1)
- `support_conversation`: `id bigint identity PK`, `channel text NOT NULL`, `external_id text NOT NULL`,
  `UNIQUE(channel, external_id)`, `tg_user_id bigint`, `source_id text`, `status text` CHECK('open','pending','resolved','closed') default 'open',
  `priority text` CHECK('low','normal','high','urgent') default 'normal', `subject text`, `assignee_id bigint NULL` REFERENCES `users(id)` ON DELETE SET NULL,
  `claimed_at timestamptz`, `first_inbound_at/last_inbound_at/first_response_at/last_message_at timestamptz`,
  `unread int not null default 0`, `suspicious bool default false`, `sub_link text`,
  `customer_profile_id bigint NULL` REFERENCES `support_customer_profile(id)` ON DELETE SET NULL,
  `created_at/updated_at timestamptz default now()`.
  Индексы: `(status, last_message_at DESC)`, `(last_message_at DESC)`, `(customer_profile_id)`, `(assignee_id)`.
- `support_message`: `id identity PK`, `conversation_id bigint NOT NULL` REFERENCES support_conversation ON DELETE CASCADE,
  `direction text` CHECK('in','out'), `author text` CHECK('client','agent','system'), `text text`, `media_type text`, `media_file_id text`,
  `external_msg_id text`, `reply_to_external_id text`, `reply_excerpt text`, `is_backfill bool default false`, `created_at timestamptz default now()`.
  Индексы: **`UNIQUE (conversation_id, external_msg_id) WHERE direction='in' AND external_msg_id IS NOT NULL`** (дедуп входящих),
  `(conversation_id, id)`, partial `(created_at, conversation_id) WHERE direction='in' AND NOT is_backfill`.
- `support_customer_profile`: `id identity PK`, `identity_key text UNIQUE` (например 'bedolaga:123'), `tg_user_id bigint`, `username text`, `display_name text`,
  `email text`, `phone text`, `meta jsonb default '{}'`, `created_at/updated_at`. Индексы `(tg_user_id)`, `(username)`.
- `support_poll_state`: `key text PK`, `value text`, `updated_at timestamptz`.
- `support_setting`: `key text PK`, `value text`, `updated_at timestamptz`.

### Каркасы будущих фаз (создать, но не использовать)
`support_ai_suggestion`, `support_kb_doc`, `support_kb_candidate`, `support_job`, `support_attachment`,
`support_operator_presence`, `support_customer_note`, `support_source_account`, `support_template`,
`support_sla_policy` (seed: low 240/2880, normal 60/1440, high 20/480, urgent 5/120 — колонки: name, first_response_minutes, resolution_minutes),
`support_audit_log` (id, actor_id, action, resource text, resource_id text, payload jsonb, ip text, created_at).

Полнотекстовые индексы НЕ создавать (КБ — фаза 3; будет pg_trgm GIN + tsvector append-only).

## 2. Модули `web/backend/core/support/`

```
__init__.py        init_support() -> SupportService (store+outbox+eventbus), кладётся в app.state
schema.py          ensure_support_schema() — идемпотентный DDL (файл 004)
settings.py        SupportSettings (pydantic, env SUPPORT_*: POLL_INTERVAL_SECONDS=60, WINDOW_HOURS=24…) 
                   + чтение рантайм-значений из support_setting
events.py          EventBus: async pub/sub — subscribe(kind) -> asyncio.Queue, publish(kind, payload);
                   EventKind enum: MESSAGE_CREATED, MESSAGE_UPDATED, CONVERSATION_CHANGED, POLLER_STATUS
store/conversations.py  record_inbound (дедуп INSERT..ON CONFLICT DO NOTHING + first_inbound_at),
                        record_outbound (first_response_at), set_status, set_priority, set_assignee, touch_last_message
store/customers.py      upsert_customer_profile (ON CONFLICT identity_key), get_customer_profile(id/key)
store/queries.py        list_conversations (фильтры: status/channel/priority/assignee/customer_id/unread_only/q по тексту; пагинация page/per_page; сортировка last_message_at DESC),
                        get_conversation_with_messages(id), list_messages(conv_id, before_id, limit)
store/poll_state.py     get_poll_state(key)/set_poll_state(key, value)
outbox.py               ЕДИНЫЙ выход наружу: reply_window(conversation, now, window_hours) — чистая функция
                        (открыто/закрыто/граница; WindowClosedError), send(conv,text) через зарегистрированный sender
channels/base.py        ChannelSender Protocol (send_text) + registry
channels/telegram.py    заглушка (raise NotImplementedError, фаза 2)
workers.py              start_support_workers(service)/stop_support_workers — asyncio.create_task циклов (пока пустое: health loop)
deps.py                 get_support_service (из app.state)
```
Доступ к БД — raw SQL `text()` на существующем async engine из `core/database.py` (как `db_helpers.py`).
Никакого ORM, второго движка, второй БД.

## 3. Роутер `web/backend/api/v1/support/` (папка; префикс `/api/support`)

- `__init__.py` — include_router.
- `health.py` — `GET /api/support/health` (открытый): `{success:true, data:{status:'ok', db:true, pollers:{}}}`.
- `status.py` — `GET /api/support/config-status` (за `get_current_admin`): каналы/интервалы/окно (из settings + support_setting).
- Регистрация в `main.py`: `app.include_router(support_router, prefix="/api/support", tags=["support"])`.
  В `lifespan`: `await ensure_support_schema()` (try/except best-effort) → `app.state.support = await init_support()` →
  `start_support_workers(...)` → на shutdown cancel задач.

## 4. Тесты `web/backend/tests/test_support_foundation.py` (без сети и БД)
- EventBus: публикация → N подписчиков получают, порядок, отписка не ломает шину.
- `reply_window`: открыто/закрыто/граница (чистая функция), `WindowClosedError`.
- `SupportSettings` из env (monkeypatch).
- Pydantic-схемы (ремня?) — минимум: envelope `{success,data}` для health.

## 5. Запуск/проверка
`cd web/backend && python -m pytest -q tests/test_support_foundation.py` — зелёные.
`python -m pytest -q` (весь набор, 30+ тестов) — без регрессий.

## НЕ ДЕЛАТЬ в этой фазе
- Поллер Bedolaga (ф1), эндпоинты conversations/reply/... (ф1), WebSocket (ф1), UI (ф1),
  ИИ/КБ/SLA/Telegram/форум-мост (ф2+). Только каркасные таблицы и модули-заглушки.
- Не менять существующие роутеры/API вне добавления support-роутера и lifespan-блока.

---

# ФАЗА 1 — канал Bedolaga + очередь в API (бэкенд). Статус: ⬜ в работе

> Фаза 0 завершена: таблицы `support_*` применены, `core/support` каркас готов, `/api/support/health` работает.
> Детальный план фаз 0-1 (thinker): см. `docs/INTEGRATION-SUPPORT.md` и отчёт thinker (в этом диалоге).

## Цель фазы 1 (бэкенд)
Наполнить очередь живыми тикетами Bedolaga и дать оператору API: список, переписка, ответы,
статусы, «взять диалог», карточка клиента; WebSocket для живых обновлений. UI (React) — отдельно (следующая задача).

## 1. Канал Bedolaga: `web/backend/core/support/channels/bedolaga.py`

- Поллер-цикл (интервал из `SupportSettings.poll_interval_seconds`, 60 с), запускается в `workers.py`
  ТОЛЬКО если канал включён (есть флаг в `support_setting` ключ `bedolaga.enabled`, default = наличие
  `BEDOLAGA_API_URL`+`BEDOLAGA_API_TOKEN` в env → `core/bedolaga_client.py`) иначе — канал молчит.
- Используй существующий `core/bedolaga_client.py` (добавь недостающие методы, если их нет:
  list_tickets(status), get_ticket(id), reply_ticket(id, text), set_ticket_status(id, status),
  get_priority/set_priority — сверься с реальным стилем клиента и прокси `api/v1/bedolaga/*`).
- Поведение (проекция `ai-support/src/channels/bedolaga.ts`):
  - опрос статусов `open/answered/pending`, пагинация 50;
  - дедуп входящих: `INSERT ... ON CONFLICT (conversation_id, external_msg_id) WHERE direction='in' DO NOTHING`
    (partial unique уже есть в БД) — 0 затронутых строк → пропуск;
  - cold-start: `baseline = poll_state['bedolaga:last_poll']`; сообщения старше baseline импортируются
    с `is_backfill=true` (unread не растёт, событий не шлём), самое свежее входящее — live-событие `MESSAGE_CREATED`;
  - после baseline всё свежее — live; в конце цикла `set_poll_state('bedolaga:last_poll', now())`;
  - маппинг статусов: `answered→pending`, `pending→open` (в обе стороны через /status-синк);
  - `repair`: известные тикеты (наш список) сверяются и при расхождении обновляются;
  - события поллера `POLLER_STATUS` (last_poll, last_error, ingested) — для WS/health;
  - ошибки не убивают цикл (try/except + log через app_log), как `core/auto_sync.py`.
- Sender для reply: регистрируется в `Outbox` (registry) — `send_text(conv, text)` → `bedolaga_client.reply_ticket`
  **retries=0** (API неидемпотентен), на 5xx/таймаут НЕ повторяем автоматически; фиксируем ответный `external_msg_id`, если HTTP вернул.

## 2. Эндпоинты `api/v1/support/` (все под `get_current_admin`, формат `{success,data}`, ошибки `E.*`)

| Метод | Путь | Логика |
|---|---|---|
| GET | `/conversations` | список: фильтры status/channel/priority/assignee/customer_id/unread_only, `q` по тексту, пагинация page/per_page, сортировка `last_message_at DESC` (store/queries уже готовы) |
| GET | `/conversations/{id}` | переписка: {conversation, messages, customer(кратко)} |
| POST | `/conversations/{id}/reply` | {text,…} → `outbox.send()`; окно 24ч закрыто → 409 `WindowClosedError` (понятный текст: «Клиент давно не писал, отправка ограничена») |
| POST | `/conversations/{id}/read` | unread→0 |
| POST | `/conversations/{id}/state` | {status, priority?} → локально + синк `/status` в Bedolaga (сравнение перед записью, защита от зацикливания) |
| POST | `/conversations/{id}/assignee` | {assignee_id: int\|null} «взять диалог» (claimed_at при первом назначении) |
| GET | `/conversations/{id}/customer` | карточка (см. п.4), кэш 60 с |
| POST | `/conversations/{id}/customer/refresh` | сброс кэша |
| GET | `/pollers` | статусы поллеров (из EventBus/последнего POLLER_STATUS) |
| WS | `/ws` | см. п.3 |

Monтируется: `ws` — отдельный `router` (WebSocketRoute) или в `health.py`/своём `ws.py`; остальное — `__init__.py`.

## 3. WebSocket `/api/support/ws`

- **Auth-кадр**: сервер ждёт до 5 с первый JSON `{"type":"auth","token":"<JWT>"}`; валидирует
  `decode_token` + user в `users` (как `get_current_admin`), иначе close 4401. Токен не в URL.
- Кадры данных: `{"type":"message"|"message_updated"|"message_deleted"|"conversation"|"poller","data":{...}}`
  — события берутся из `EventBus` (подписка при коннекте, отписка при disconnect).
- Heartbeat: server ping каждые 30 с (текстовый `{"type":"ping"}` или WS ping).
- Реализация: FastAPI `WebSocket` + `asyncio` задачи на чтение/запись; фабрика менеджера в `core/support/ws.py`.

## 4. Карточка клиента (мин. Ф1): `core/support/integrations/bedolaga_customer.py`

- Связка поведения (из `ai-support/src/integrations/bedolaga-customer.ts` + `customers.ts`):
  conversation → `tg_user_id`/`external_id` → `bedolaga_client.get_user`, `list_subscriptions`,
  `list_tickets(user_id)`, `list_transactions(user_id)` (+ `get_user_activity` если есть).
- Поля карточки: id, telegram_id, username, имя, баланс (руб/коп), подписка {status,end_date,is_trial,traffic},
  счётчик тикетов, последняя активность.
- Кэш 60 с: `support_customer_profile.meta` (jsonb) + `updated_at`; refresh сбрасывает.
- Remnawave deep — НЕ в этой фазе (только заглушка/пусто, ф5).

## 5. nginx (dev): добавить WS-прокси для `/api/support/ws`

- `.docker/nginx/default.conf` (или где location `/api/`): для этого пути `proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`.
- Прод-конфиг НЕ трогать (он биндится на сервере) — оставить комментарий/TODO в файле, сообщить координатору.

## 6. Тесты
- `web/backend/tests/test_support_bedolaga.py`: поллер на заглушке (`httpx.MockTransport` или подменённый
  client в инъекции): 2 тикета → импорт; повтор → 0 новых; cold-start (всё backfill + одно live); статус-синк.
- `web/backend/tests/test_support_endpoints.py`: ASGI client + dependency override `get_current_admin`
  и `get_support_service` (фейковый store): envelope, 404, 409 окно 24ч, reply, state, assignee, ws auth-кадр (bad token → 4401).
- `cd web/backend && python -m pytest -q` — весь набор зелёный (сейчас 124).

## НЕ ДЕЛАТЬ в фазе 1
- React-страницы, меню «Саппорт» (отдельная задача), ИИ/КБ/SLA/уведомления/Telegram/форум-мост, MiniShop.
- Не трогать `db/postgres/*` (там deny; таблицы уже применены). Миграции НЕ создавать.
- Не менять существующие роутеры/API вне добавления новых файлов в `api/v1/support/` и локализованных правок `core/support/workers.py`.

---

# ФАЗА 1 (фронтенд) — React «Очередь» + меню «Саппорт». Статус: ⬜ в работе

> Бэкенд фазы 1 готов (поллер+API+WS). Теперь видимая часть в админке (React SPA, стиль Remnawave).

## 1. API-клиенты (изучи стиль `web/frontend/src/api/*.ts`, особенно `bedolaga/*` и `client.ts`)
- `api/support.ts` — axios-клиент на `/api/support/*`: `listConversations(params)`, `getConversation(id)`,
  `replyConversation(id, {text})`, `readConversation(id)`, `setState(id, {status,priority?})`,
  `setAssignee(id, {assignee_id})`, `getCustomer(id)`, `refreshCustomer(id)`, `getPollers()`, `getConfigStatus()`.
- Следуй стилю обработки `{success,data}` / ошибок (как в api/bedolaga.ts и mutationToast).

## 2. WebSocket-клиент `lib/supportSocket.ts` (или в `api/`)
- Подключение к `ws[s]://<host>/api/support/ws` (в dev Vite-проксирует /api → FastAPI; уточни, нужен ли ws-прокси в `vite.config.ts` — добавь, если требуется).
- Auth-кадр: первый JSON `{"type":"auth","token":<JWT>}` (токен из authStore/localStorage, как client.ts).
- Reconnect с backoff (2с→5с→10с, кап 30с), переподписка событий.
- Обработка кадров `message|message_updated|conversation|poller` → колбэки/стор.
- UE: сброс при 4401 (токен протух — выйти/редирект на /login).

## 3. Страница «Очередь» `pages/support/Queue.tsx` (стиль: `pages/bedolaga/BedolagaCustomers.tsx`, дизайн Remnawave)
- Левая колонка: список диалогов (TanStack Query: useQuery listConversations; фильтры статус/поиск; активный выделен; live-обновление списка через WS).
- Правая: переписка (useQuery getConversation): сообщения (входящие/исходящие пузыри: direction in/out, author client/agent/system; время; «история/backfill» помечать бейджем), поля статуса/приоритета сверху, кнопки: «Взять диалог» (setAssignee) / «Решено» (setState resolved), поле ответа (textarea) + Enter/Ctrl+Enter + кнопка «Отправить» (replyConversation; mutationToast; ошибка 409 окна — показать понятно), 
- Справа (или вкладкой) — карточка клиента (getCustomer: имя, telegram_id, username, баланс, подписка {status,end_date,traffic}, тикеты; кнопка «Обновить»).
- Live: подписываемся на события для открытого диалога и списка (refetch или локальный аппенд).
- Empty state: «Диалог не выбран» / «Очередь пуста» (компонент EmptyState).
- Всё на shadcn-компонентах (Button, Input, Select, Badge, ScrollArea, Skeleton, Avatar) + токены Remnawave.

## 4. Меню «Саппорт» + заглушки
- `config/navigation.ts`: новая секция «Саппорт» с группой (паттерн группы «Bedolaga Bot» — посмотри как устроена bedolaga-группа и воспроизведи):
  - Очередь → `/support` (главный, иконка)
  - Контроль SLA → `/support/sla`
  - База знаний → `/support/kb`
  - ИИ-ассистент → `/support/ai`
  - Шаблоны → `/support/templates`
  - Аналитика → `/support/analytics`
  - Команда → `/support/team`
- `App.tsx`: lazy-роуты `/support`, `/support/sla|kb|ai|templates|analytics|team` (под RequireAuth+Layout, как остальные).
- `pages/support/Placeholder.tsx` — красивый экран «Раздел в разработке» (иконка, заголовок, описание) для 6 подпунктов.

## 5. Проверка (обязательно, верни вывод)
- Если `web/frontend/node_modules` отсутствует: `cd web/frontend && npm ci` (затем `npm run build`).
- `cd web/frontend && npm run build` — сборка без ошибок типов.
- Не ломать существующую сборку (build полностью).

## НЕ ДЕЛАТЬ
- Не трогать бэкенд (поллер/API — готов), ИИ/КБ/SLA наполнение, db/postgres, PHP.
- Не добавлять новые npm-зависимости (только shadcn-компоненты — можно скопировать из `components/ui/`, они есть).