# Саппорт: аудит и план завершения

**Статус:** аудит выполнен; **Этап A, Этап B и Этап C выполнены (2026-11-28)**; следующий — Этап D
**Дата:** 2026-11-28
**Связанные документы:** `docs/INTEGRATION-SUPPORT.md`, `docs/AI-SUPPORT.md`, `docs/CHANGELOG_CMS.md`, `docs/CODEBASE_INDEX.md:340-361, 768-793, 1196-1239, 1378-1439`

---

## 1. Что задумано

Полный перенос эталонного `ai-support` (`github.com/tagashi666/ai-support`, MIT) в стек CMS: FastAPI + PostgreSQL + React SPA. Внешний Node-сервис после переноса не нужен.

Целевая картина — группа «Саппорт» из 7 экранов (`INTEGRATION-SUPPORT.md:110-118`):

| # | Экран | Назначение |
|---|-------|-----------|
| 1 | Очередь | список диалогов, переписка, статусы/приоритеты, ИИ-черновик, карточка клиента |
| 2 | Контроль SLA | таймеры первого ответа / handoff |
| 3 | База знаний | статьи, дообучение на диалогах, импорт выгрузки Telegram |
| 4 | ИИ-ассистент | режим `off/suggest/auto`, ворота качества, анти-утечки |
| 5 | Шаблоны ответов | быстрые ответы по shortcut |
| 6 | Аналитика | объёмы, время ответа, нагрузка |
| 7 | Команда | операторы, присутствие, аудит |

Каналы: Bedolaga-тикеты + Telegram-личка + форум-мост (staff group). MiniShop исключён. Один токен бота = один long-poll, второй бот на том же токене запрещён.

---

## 2. Что реализовано (фазы 0–2c) ✅

| Блок | Файлы |
|------|-------|
| Миграция БД: 16 таблиц `support_*` | `db/postgres/migrations/004-support-foundation.sql` |
| Идемпотентная схема + `ALTER` CHECK author | `web/backend/core/support/schema.py:15-160` |
| Store-слой (raw SQL, сессия на вызов) | `web/backend/core/support/store/*` |
| API: conversations/reply/read/state/assignee/customer/pollers/attachments/health/config-status/WS | `web/backend/api/v1/support/*` |
| WebSocket с JWT-кадром, backoff, ping 30s | `web/backend/core/support/ws.py`, `web/frontend/src/lib/supportSocket.ts` |
| Outbox + окно 24ч (для TG-лички отключено) | `web/backend/core/support/outbox.py` |
| Telegram: клиент, long-poll, `/start` + GREETING, `/myid`, 409 Conflict | `web/backend/core/support/tg/*` |
| Форум-мост: темы, зеркало, `/close /reopen /ban /unban`, архивация | `web/backend/core/support/tg/forum.py` |
| Bedolaga-канал: поллер 60с, импорт тикетов, синк статуса | `web/backend/core/support/channels/bedolaga.py` |
| Вложения: upload/download, allowlist, 8 МБ | `web/backend/api/v1/support/attachments.py` |
| UI «Очередь» (3 колонки, WS, вложения, pollers-панель) | `web/frontend/src/pages/support/Queue.tsx` + `components/*` |
| Настройки «Telegram / Саппорт» + in-place reload | `core/settings_registry.py:253-308`, `core/integrations.py:807-865` |
| 6 подпунктов меню-заглушек | `web/frontend/src/App.tsx:138-143`, `pages/support/Placeholder.tsx` |
| **Этап A:** фильтры очереди, динамические поллеры, seen/409, идемпотентность ответа, lease-захват, ACL вложений, TTL upload-токена, health с БД | `web/backend/api/v1/support/*`, `web/backend/core/support/schema.py`, `web/frontend/src/api/support.ts`, `pages/support/*`, `db/postgres/migrations/005-support-reply-idempotency.sql` |

---

## 3. Что НЕ реализовано

### Фаза 3 — ИИ и база знаний (выполнена в Этапе B)
На момент аудита: таблицы `support_ai_suggestion`, `support_kb_doc`, `support_kb_candidate` были созданы в 004, но не использовались; не было провайдера, `gate`, `scrub`, `responder`, FTS, импорта; экраны `/support/kb` и `/support/ai` — заглушки.

Что сделано в Этапе B (2026-11-28):
- миграция `006-support-ai-kb.sql` + `AiRuntime`; портированы `gate`, `scrub`, `outbound`, `links`, `repair`, `chunks`, `examples`, `confidence_level`;
- воркер ИИ, режимы `off/shadow/suggest/auto`, пауза, `require_kb`, порог уверенности, лимит автоответов, debounce; кадр WS `ai_suggestion`;
- база знаний: CRUD, публикация/архив/восстановление, русский поиск на `tsvector` (ADR-007), идеи статей, фидбек «Это неверно» → `qa_pair`/кандидат;
- импорт текста чата и `result.json` через `support_job` (dry-run, прогресс, отмена);
- экраны `/support/kb` и `/support/ai` — реальные страницы (`pages/support/Kb.tsx`, `pages/support/Assistant.tsx`), плюс ИИ-черновик в треде очереди.

### Фаза 4 — SLA, шаблоны, уведомления, аналитика, команда (выполнена в Этапе C)
На момент аудита: `support_sla_policy` засеяна, но расчёта SLA нет; таблицы `support_template`, `support_operator_presence`, `support_customer_note`, `support_audit_log` созданы, кода нет; уведомлений операторам нет; экраны `/support/sla|templates|analytics|team` — заглушки.

Что сделано в Этапе C (2026-11-28):
- SLA: `support_sla_event`, политики по приоритетам с редактированием, `SlaWatcher` раз в минуту, одно уведомление на событие (≤5 за проход), кадр WS `sla_alert`, дубль в staff-группу форум-моста; экран `/support/sla`;
- шаблоны ответов: CRUD с уникальным `shortcut`, счётчик `uses`, вставка в композер кнопкой и слэш-подсказкой; экран `/support/templates`;
- заметки о клиенте (внутренние, в карточке), присутствие `viewing|typing` (TTL 120 с, троттлинг 5 с, кадр WS `presence`), аудит действий; экран `/support/team` (операторы + журнал);
- аналитика `/support/analytics`: объёмы, медиана/P90 первого ответа только по людям, каналы/приоритеты, нагрузка операторов, метрики ИИ;
- миграция `008-support-stage-c.sql` (`support_message.author_id` и поля/индексы Этапа C).

### Фаза 5 — Полировка (не начата)
- Remnawave deep-карточка — заглушка `integrations/bedolaga_customer.py:139` и `CustomerCard.tsx:126-132`.
- Медиа-лимиты не настраиваются (`SupportService.upload_max_size` всегда `None`).
- Отдельной вкладки «Поддержка» в настройках нет — только блок «Telegram / Саппорт» в «Интеграциях».
- Удаление Node-сервиса `ai-support` не выполнено.

### Публичный чат на сайте
**Не задумывался и не реализован.** На сайте только ссылка на Telegram-бот в футере (`layouts/main.php:259-267`). Открытое решение: нужен ли веб-виджет чата с сайта (тогда — отдельный канал в саппорте).

---

## 4. Технический долг и баги (найдено при аудите)

| # | Проблема | Файл:строка |
|---|----------|-------------|
| 1 | `getConfigStatus()` объявлен, но не вызывается | `api/support.ts:201-202` |
| 2 | Фильтры `channel/priority/assignee_id/customer_id/unread_only` бэкенд поддерживает, UI — нет | `ConversationList.tsx:11-16` |
| 3 | В футере списка `items.length` вместо `total`, счётчик занижен | `ConversationList.tsx:193` |
| 4 | Панель поллеров захардкожена на `telegram`/`bedolaga` | `Queue.tsx:111-112` |
| 5 | Назначение только на себя, снять/передать нельзя | `Queue.tsx:278-281` |
| 6 | `reply_to_external_id` / `reply_excerpt` не рендерятся — нет цитирования | `MessageThread.tsx:120-157` |
| 7 | `suspicious`, `sub_link`, `first_response_at`, `claimed_at` не показываются | `pages/support/*` |
| 8 | Приоритет не синхронизируется в Bedolaga (`set_ticket_priority` не вызывается) | `conversations.py:341-364` |
| 9 | Bedolaga-медиа: `upload_media/download_media` объявлены, не вызываются; `send_media` → 501 | `bedolaga_client.py:272-294`, `channels/bedolaga.py` |
| 10 | `GET /attachments/{id}` без привязки к диалогу — любой админ по id | `attachments.py:139-164` |
| 11 | У upload-токенов нет TTL, текст ошибки врёт про «истекло» | `attachments.py:47-66`, `conversations.py:190` |
| 12 | `/health` возвращает `db: True` константой | `health.py:31` |
| 13 | Нет пагинации сообщений через API (`list_messages` не подключён) | `store/queries.py:260-283` |
| 14 | Нет валидации query-параметров списка (неверный status → пусто, не 422) | `conversations.py:69-77` |
| 15 | `author='bot'` только в рантайм-ALTER, не в миграции | `004:70` vs `schema.py:15-46` |
| 16 | EventBus in-memory + один uvicorn-воркер — не масштабируется | `core/support/events.py`, `backend/Dockerfile:43` |
| 17 | Нет фронтенд-тестов вообще | `web/frontend/**` |
| 18 | Строки UI захардкожены по-русски, без i18n | `pages/support/*` |
| 19 | Namespace `plugins.smart_support` в локалях без кода | `locales/ru:4513+` |
| 20 | TODO в nginx: WS-заголовки нужно продублировать в прод-конфиге | `.docker/nginx/default.conf:76-78` |
| 21 | *(добавлено при работе над Этапом B)* `suggestion` в детали диалога появлялся сырым полем строки БД (служебные `gate_*`, `chunk` внутри `used`) — **закрыто в Этапе B**, отдаётся публичная форма (`level/gate/used` без `chunk`) | `core/support/ai/public.py`, `conversations.py:118-131` |

Закрытие по этапам: **1–5, 6, 8, 10–12, 14** — Этап A (см. §5); **21** — Этап B. Пункты 7, 9, 13, 15–20 в Этапе B не закрывались.

---

## 5. План завершения

### Этап A — Стабилизация текущего ✅ (выполнен 2026-11-28)
Цель: очередь без известных багов, честные статусы.

Закрыто из таблицы долга: **1, 2, 3, 4, 5, 8, 10, 11, 12, 14**.
Дополнительно закрыто вне списка: **6** — цитирование `reply_excerpt` в треде.

1. [x] **1** — `getConfigStatus()` вызывается; панель поллеров строится по `/pollers` + `/config-status`.
2. [x] **2** — фильтры `channel/priority/unread_only` в UI очереди (и статус «Закрытые»).
3. [x] **3** — футер списка показывает `total` из ответа, а не `items.length`.
4. [x] **4** — поллеры рендерятся динамически, без захардкоженных `telegram`/`bedolaga`.
5. [x] **5** — назначение: взять / освободить / передать (API assignee + кнопки в треде).
6. [x] **8** — приоритет синхронизируется в Bedolaga (`priority_synced: synced|unchanged|skipped|error`).
7. [x] **10** — `GET /attachments/{id}` проверяет ACL через join attachment → message → conversation (404 на чужое).
8. [x] **11** — TTL upload-токена 24 ч (`SUPPORT_UPLOAD_TOKEN_TTL_HOURS`), истёкшие файлы удаляются, текст ошибки честный.
9. [x] **12** — `/health` делает реальный `SELECT 1`, при сбое `status:"degraded"`, `db:false`.
10. [x] **14** — regex-валидация query-параметров списка (неверный status/channel/priority → 422).
11. [x] Тесты бэкенда: `web/backend/tests/test_support_stage_a.py` — валидация фильтров, `CLIENT_WROTE`, идемпотентность ответа, lease/force, sync приоритета, TTL/ACL вложений, health с БД.
12. [x] `docs/CODEBASE_INDEX.md` обновлён (эндпоинты, `ReplyIn`/`StateIn`, `support.ts`, `support_reply_key` + миграция 005).

Не закрыто в Этапе A (остаётся в долге):
- **13** — пагинации сообщений через API нет: `store.list_messages` есть, но `GET /conversations/{id}` его не использует (жёсткий лимит 200).
- **20** — `TODO(prod)` про WS-заголовки в прод-конфиге nginx остаётся (`.docker/nginx/default.conf:75-78`): прод-конфиг живёт на сервере, не в репозитории.
- Пункты **15–19** (author='bot' в миграции, EventBus/один воркер, фронт-тесты, i18n, namespace локалей) в Этап A не входили.

**Следующий шаг — Этап C (Фаза 4: SLA, шаблоны, аналитика, команда).**

### Этап B — Фаза 3: ИИ + КБ ✅
**выполнен 2026-11-28: B1–B4, тесты 665** (плюс `tsc` и `vite build` зелёные).
1. [x] Миграция: следующий свободный номер (005 занят идемпотентностью саппорта, 006 зарезервирован планом docs-history) — индексы `support_kb_doc` FTS, поля `support_ai_suggestion`. Фактически выполнено как `006-support-ai-kb.sql`, docs-history переехал на 007 (ADR-007).
2. [x] Провайдер ИИ + режимы `off/suggest/auto`, ворота `confidence ≥ 0.75`, `AI_REQUIRE_KB`.
3. [x] KB CRUD API + экран `/support/kb`.
4. [x] Экран `/support/ai`: черновик в карточке диалога, кнопки принять/отклонить.
5. [x] Импорт: вставка копии чата текстом, Telegram Desktop `result.json`.
6. [x] `scrub` — анти-утечки (токены, ссылки, персональные данные).

### Этап C — Фаза 4: SLA, шаблоны, аналитика, команда ✅ (выполнен 2026-11-28)
1. [x] SLA-вотчер: первый ответ / resolution, 1 уведомление на событие, ≤5 за цикл.
2. [x] Уведомления в staff-группу форум-моста (если мост поднят) + кадр WS `sla_alert`.
3. [x] Шаблоны: CRUD + вставка по `/shortcut` и кнопкой в композере.
4. [x] Внутренние заметки, присутствие (viewing/typing), аудит действий.
5. [x] Аналитика: объём, медиана/P90 первого ответа только по людям, нагрузка по операторам.

### Этап D — Фаза 5: полировка
1. Remnawave deep-карточка (read-only) в `CustomerCard`.
2. Медиа-лимиты из настроек, TTL upload-токенов.
3. Вкладка «Поддержка» в настройках.
4. Остановка/удаление Node-сервиса `ai-support` после smoke.

### Этап E — Публичный чат (решение владельца)
Нужен ли виджет чата на `hexaveil.xyz` (канал `web` в саппорте) или остаёмся на Telegram-ссылке. Без решения не начинать.

---

## 6. Критерии готовности
1. Все 7 экранов работают, без заглушек.
2. `docs/CODEBASE_INDEX.md` отражает все новые роуты/модели/методы API/сторы.
3. Тесты: бэкенд-юниты по store/outbox/SLA, фронт — минимум smoke-тесты очереди.
4. Смоук на проде: WS 101, `/start` в боте, ответ из веба доходит в Telegram и обратно.
5. `CHANGELOG_CMS.md` дополнен.

---

## 7. Синхронизация с апстримом v3.0.0 (2026-11-28)

Локальный `ai-support/` обновлён с v2.5.0 до v3.0.0 (`ee05237`). Детали — `docs/AI-SUPPORT.md`, раздел «1a. Дельта v2.5.0 → v3.0.0».

**Что меняется в плане:**

- **Этап A** дополняется серверной защитой от гонок: `seen` + 409 `client_wrote` при «Решено»/скрытии, идемпотентность ответа (`client_msg_id`), lease 15 мин + 409 `locked_by_other`. Без этого параллельные вкладки/операторы ломают статусы.
- **Этап B (фаза 3)** теперь не «с нуля»: портировать готовые `ai/chunks`, `ai/links`, `ai/repair`, `ai/examples`, `ai/interface-kb`, `shared/confidence`, `core/fts` (заменить FTS5 на PostgreSQL `tsvector`). Добавляются: пауза помощника (`aiPause`), режим `shadow`, `operator_note`, «Почему так?» (`/api/suggestions/:id`), «Это неверно» → идея статьи, справочник интерфейса Bedolaga, прогон `aieval` как регрессия.
- **Этап C (фаза 4)** получает готовую модель: `shared/attention` + `conversation-order` (серверный порядок и секции), SLA по приоритетам с эпизодами ожидания, `support_operator_draft`, присутствие `viewing|typing`, «попросить передать», внутренние заметки, `qa_pair` для обучения, отчёты (медиана/P90 только по человеку, `aiUsage`).
- **Новая сквозная тема: права.** В апстриме матрица `viewer|agent|lead|admin`, deny-by-default, переопределения `role_permission`, отказы на лету. Сейчас в CMS «все админы = операторы». Решение владельца из `INTEGRATION-SUPPORT.md:118` можно оставить, но контракты API лучше сразу делать с проверкой прав.
- **Новая сквозная тема: live-протокол.** seq/epoch-журнал + `GET /api/events` + `invalidate`-кадры. Текущий CMS-WS шлёт данные напрямую и не умеет догонять после сна вкладки — при переносе phases 3–4 это станет заметно.

**Не переносим:** новая React-панель `web/**` (у нас своя дизайн-система), демо-режим, onboarding/tutorial, палитра ⌘K, device-настройки — это UI-only апстрима.

**Требуется решение:** обновлять ли `docs/INTEGRATION-SUPPORT.md` (там зафиксирован апстрим v2.5.0 и статусы фаз) или вести дельту только здесь. Предлагается: `INTEGRATION-SUPPORT.md` оставить как план переноса, а версию апстрима и дельту держать в `AI-SUPPORT.md`.

