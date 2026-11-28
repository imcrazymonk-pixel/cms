# Саппорт — активация Telegram-бота и перенос истории

**Статус:** план принят 2026-11-28; выполнение — D1 → D4.
**Связанные документы:** `docs/plans/2026-11-28-support-completion.md` (Этап D), `docs/INTEGRATION-SUPPORT.md`, `docs/AI-SUPPORT.md`.

---

## 0. Факты

### 0.1 Прод-бот (read-only, панель 144.31.156.172)

| Что | Значение | Где задано |
|---|---|---|
| Контейнер | `vpn_support_bot`, `node:20-alpine`, `restart: always`, портов наружу нет | compose `/opt/support-bot` |
| Пакет | `telegram-support-in-topics-bot@1.0.0` | `package.json` |
| Токен | `SUPPORT_BOT_TOKEN` | `/opt/support-bot/.env` |
| Группа операторов | `SUPPORT_STAFF_GROUP_ID` (отрицательный id супергруппы) | `.env` |
| Хранилище | `SUPPORT_STORE_PATH=/app/data/topics.json` | `.env` |
| Ссылка «в VPN-бот» | `https://t.me/HexaVeil_bot` | `src/handlers.ts` (хардкод) |
| Автоочистка | `INACTIVITY_DAYS=7`, проверка раз в час | `src/handlers.ts` |
| Имя темы | до 128 символов: `Имя (@username)` | `src/handlers.ts` |
| Антиспам | 10 сообщений / 20 с, мьют 60 с | `src/handlers.ts` |
| `/start` | «Добро пожаловать в поддержку! 👋» + `HELP_TEXT` + кнопки «Завершить чат» / «Вернуться в VPN Бот» | `src/handlers.ts` |
| Очистка чата | `PRIVACY_CLEANUP_MSG` (обещание «не храним переписку») | `src/handlers.ts` |
| История | сообщений в `topics.json` нет; каждое сообщение **форвардится в тему** staff-группы | `handlers.ts` |
| `topics.json` | `topics[{userId,topicId}]` — 24 пары; `banned`, `lastActivity`, `pendingCleanup` | `data/topics.json` |

### 0.2 CMS

- `core/support/tg/poller.py` — личка, `/start` → `self.greeting` (новый ключ `support_tg_greeting`), `/myid`.
- `core/support/tg/forum.py` — темы, зеркало, `/close /reopen /ban /unban`, архивация.
- `support_message.is_backfill` (`004:77`); `record_inbound(..., is_backfill=True)` не растит unread и не двигает `last_inbound_at`.
- Bedolaga-история тикетов уже импортируется как backfill (`channels/bedolaga.py:230-306`).
- `support_job` подходит для аудита/прогресса импорта; новых таблиц не требуется.
- `SUPPORT_TRIGGER_KEYS` (`core/integrations.py`) — hot reload каналов при сохранении ключей.

### 0.3 Расхождения CMS и прод-бота (важно для cutover)

| Поведение | Прод-бот | CMS |
|---|---|---|
| `/start` | только текст + кнопки, без форварда | пишет `/start` входящим и **форвардит в тему** |
| Inline-кнопки | `close_mychat`, «Вернуться в VPN Бот» | `reply_markup` не поддержан, `callback_query` не разбирается |
| Неактивность | предлагает оператору кнопку «Очистить чат», mapping удаляется | закрывает тему, пишет клиенту «закрыт 7 дней», mapping остаётся; тема переоткрывается |
| Автоответ | — | `GREETING` на `/start` |

---

## 1. Решения

1. **Mapping до тел.** Сначала переносим 24 пары `userId↔topicId` в `support_conversation` (иначе CMS создаст дубли тем), тела сообщений — отдельным решением.
2. **Приватность.** В боте обещание «мы не храним переписку»; импорт тел в PostgreSQL ему противоречит. Дефолт: **mapping-only**, тела — только по явному решению владельца + обновление текста обещания + ADR о retention.
3. **Источник истории** — темы staff-группы. Bot API историю не отдаёт: только MTProto (`getForumTopics` + `getReplies`/`getHistory`) или Telegram Desktop export.
4. **Backfill** — добавить `is_backfill` в `record_outbound` (колонка уже есть). При `True`: не писать `first_response_at`, не двигать `last_inbound_at`, `last_message_at = GREATEST(...)`.
5. **Дедуп** — inbound: существующий partial unique `(conversation_id, external_msg_id)`; outbound: `message_exists`; импортные id неймспейсить `staff:<topic_id>:<msg_id>`.
6. **Старые диалоги** после импорта — сразу `closed`, чтобы авто-архив не разослал 24 клиентам «диалог закрыт».
7. **Приветствие** — ключ `support_tg_greeting` (textarea, env `SUPPORT_TG_GREETING`), hot reload через `SUPPORT_TRIGGER_KEYS`. Inline-кнопки — отдельная задача (D2b).
8. **Cutover** — только после mirror-проверки; один `getUpdates` на токен.

---

## 2. D1 — активация CMS-бота

Ключи в «Настройки → Интеграции → Telegram / Саппорт»:

| Ключ | Значение |
|---|---|
| `support_tg_enabled` | `on` |
| `support_tg_token` | тот же токен, что у `vpn_support_bot` |
| `support_tg_bot_name` | короткое имя бота (без `@`), для ключей poll-state |
| `support_tg_staff_group_id` | тот же отрицательный id группы |
| `support_tg_forum` | `on` |
| `support_tg_archive_days` | `7` (сохранить поведение) |
| `support_poll_interval_seconds` | как у прода (по умолчанию из env) |
| `support_window_hours` | 24 |
| `support_tg_greeting` | текст `HELP_TEXT` прод-бота + шапка «Добро пожаловать…» (перенос как есть) |

Порядок:
1. Заполнить ключи, **не включая** `support_tg_enabled` (или `off`).
2. Остановить `vpn_support_bot` (`docker compose stop`, `--restart=no`) — иначе второй поллер получит 409.
3. Включить `support_tg_enabled=on` → hot reload поднимет поллер.
4. Смоук:
   - `/start` → пришёл текст из настройки;
   - сообщение клиента → появилось в очереди и в теме форума;
   - ответ из веба → клиенту в личку;
   - ответ в теме → в веб;
   - `/myid` → ID;
   - «Решено» → тема закрыта.
5. Откат: `support_tg_enabled=off`, `docker compose up -d` для старого бота, `topics.json` не трогать.

---

## 3. D2 — приветствие и тексты

Сделано в CMS:
- `support_tg_greeting` — редактор в настройках, применяется без рестарта;
- дефолт — прежний короткий текст.

Осталось решить:
- перенести ли полный `HELP_TEXT` прод-бота (рекомендуется: да, как значение настройки);
- нужны ли inline-кнопки `close_mychat` / «Вернуться в VPN Бот» (требует `reply_markup` в `TelegramClient.send_message` и разбор `callback_query` в `parse_update` + обработчик `callback` → `set_status(closed)`);
- нужен ли редактор `PRIVACY_CLEANUP_MSG` (если авто-очистка остаётся).

---

## 4. D3 — история

### 4.1 Вариант A — mapping-only (дефолт)

- из `topics.json` переносим 24 пары → `support_conversation` (`channel='telegram'`, `external_id=str(userId)`, `source_id=str(topicId)`, `tg_user_id=userId`);
- тела не переносим, старые диалоги `closed`;
- приватность не нарушается, объём работ минимальный.

### 4.2 Вариант B — тела сообщений

Источник — темы staff-группы. Способы:

| Способ | Плюсы | Минусы |
|---|---|---|
| Telegram Desktop export (JSON/HTML) | без API-ключей | JSON может не содержать `message_thread_id`; нужен HTML-экспорт с заголовками тем |
| MTProto (Telethon/Pyrogram) | точные `message_thread_id`, `fwd_from`, `getForumTopics` | нужны `api_id`/`api_hash` и сессия владельца |

Импорт:
- CLI `tools/support_import_history.py` (или `support_job kind='conversation_import'`), `--dry-run` по умолчанию, `--apply` явно;
- пары «тема → клиент» берём из `topics.json`, а не из имени темы;
- сообщения: `direction` по `fwd_from`/автору, `external_msg_id='staff:<topic>:<msg_id>'`, `is_backfill=True`;
- медиа — только метаданные в v1 (без скачивания файлов);
- старые диалоги `closed`, `first_response_at`/`last_inbound_at` не трогаем.

### 4.3 Приватность

Перед вариантом B:
1. обновить текст `PRIVACY_CLEANUP_MSG` (или отключить авто-очистку);
2. зафиксировать retention в ADR (дефолт: тела 90 дней, mapping бессрочно);
3. получить явное согласие владельца.

---

## 5. D4 — cutover и остановка старого бота

1. Проверить mirror на **отдельном staging-боте** и тестовой группе (если нет — окно ≤5 минут с немедленным откатом).
2. `docker update --restart=no vpn_support_bot` + `docker compose stop`.
3. Включить CMS-канал, пройти смоук §2.
4. Бэкап `/opt/support-bot/data/topics.json` и `.env`; каталог не удалять 7 дней.
5. Наблюдение неделю → архивировать `/opt/support-bot`, юниты не требуются (их нет).

---

## 6. Нарезка

- **D1 — активация:** ключи, cutover, смоук. Acceptance: `/start`, зеркало в обе стороны, `/myid`, «Решено».
- **D2 — тексты:** `support_tg_greeting` (сделано), полный `HELP_TEXT`, решение по кнопкам. Acceptance: текст меняется без рестарта.
- **D3a — mapping:** 24 пары, `closed`, dry-run. Acceptance: нет дублей тем, старые диалоги не шлют клиентам.
- **D3b — история:** CLI/импорт по выбранному варианту. Acceptance: dry-run совпадает с apply, дедуп, unread не растёт.
- **D4 — стоп старого бота:** после смоука. Acceptance: один поллер, нет 409, откат演练.

## 7. Definition of Done

1. Один `getUpdates`-консьюмер на токен.
2. Приветствие редактируется в настройках и применяется без рестарта.
3. Нет дублей диалогов/тем; mapping совпадает с `topics.json`.
4. Приватность: решение по телам зафиксировано в ADR, тексты обещаний согласованы.
5. `pytest`/`tsc`/`build` зелёные; `CODEBASE_INDEX`/`CHANGELOG`/`TASK` обновлены.

## 8. Открытые вопросы (с дефолтом)

| # | Вопрос | Дефолт |
|---|---|---|
| 1 | Импортировать тела переписки? | Нет, mapping-only до решения владельца |
| 2 | Откуда брать историю? | MTProto, если владелец даст `api_id/api_hash`; иначе Desktop export |
| 3 | Inline-кнопки прод-бота? | Не переносить; «Решено» + `/close` |
| 4 | Banned-список? | Перенести в `support_setting` `tg.main.bans` |
| 5 | Авто-архив: CMS переоткрывает тему, прод создаёт новую | Оставить CMS-поведение, убрать из текста «чат очищен» |
| 6 | Retention тел | 90 дней, ADR |
| 7 | Медиа истории | Только метаданные |
| 8 | Staging-бот | Нужен отдельный токен; иначе окно ≤5 минут |

## 9. Оценка

| Задача | Дни |
|---|---|
| D1 активация | 0,5–1 |
| D2 тексты | 0,5 (+1–2 с кнопками) |
| D3a mapping | 0,5 |
| D3b история | 1,5–3 (+1–2 с медиа) |
| D4 cutover | 0,5 + 7 дней наблюдения |

Итого: 3–5 дней без медиа/кнопок.
