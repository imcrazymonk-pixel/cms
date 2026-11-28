# AI Support — референс эталона (для внедрения в HexaVeil CMS)

> Справочник по репозиторию-эталону `ai-support` (панель техподдержки с ИИ).
> Составлен по результатам полного анализа кода (окт 2026). Когда нужны ответы
> по ai-support — сначала смотри сюда, сканировать код заново не нужно.

## 1. Паспорт

| Поле | Значение |
|---|---|
| Репозиторий | `github.com/tagashi666/ai-support` (public) |
| Локальный путь | `C:\Users\Andre\Desktop\VPN\NewWeb\ai-support` (gitignored, upstream цел — можно `git pull`) |
| Версия | **3.0.0** (`package.json`), локальный клон обновлён 2026-11-28 (коммит `ee05237`) |
| Лицензия | **MIT** (внедрение и форк легальны) |
| Язык | TypeScript (strict, ESM), Node.js **22+** |
| Стек | Fastify 5 + WebSocket, better-sqlite3 (WAL, **25 миграций**), grammy (Telegram), lottie-web |
| UI панели | новая SPA React 18 + Vite (`web/`), классическая ванильная панель осталась в `public/`; переключатель `?ui=classic|next` и `PANEL_UI` |
| Деплой | Docker (build-stage Vite, non-root uid 1000, read_only FS), публикация `${PANEL_BIND:-127.0.0.1}:${PANEL_PUBLISH_PORT:-8080}`, systemd host-updater |
| Автор/поддержка | 29 звёзд, активная разработка, CI + релизы с SHA-256 |

## 2. Что это

Self-hosted центр поддержки для VPN-сервиса. Единая очередь входящих из
**Telegram Business / Telegram-ботов / Bedolaga-тикетов / MiniShop** +
**AI-ассистент** на любом OpenAI-совместимом провайдере + операторская панель.

Возможности:
- двусторонние ответы и статусы тикетов, изображения/вложения с локальным защищённым хранением;
- карточка клиента из Bedolaga, MiniShop, Remnawave и собственного Support API;
- роли операторов, назначения, присутствие, журнал аудита;
- SLA + уведомления в Telegram (алерты только важного);
- AI-черновики (suggest) и автоответы (auto) с базой знаний и защитой от утечки секретов;
- безопасное обновление и откат из панели (SHA-256, backup, rollback).

Запускается «голой» панелью без каналов — каналы подключаются по мере готовности.

## 1a. Дельта v2.5.0 → v3.0.0 (обновлено 2026-11-28)

Локальный клон `ai-support/` обновлён с `6a04eae` (v2.5.0+2) до `ee05237` (v3.0.0). 169 коммитов, 399 файлов, +56k строк. Релизы: v2.6.1 (26.10), v2.7.0 (09.11), v3.0.0 (11.11).

**База.** Миграции 020–025 (было 19 → стало 25): `conversation.hidden_at` + частичный индекс видимых, `last_resolved_at`; `ai_suggestion.final_text`, `answer_message_id`, `operator_note`; новая `qa_pair` + FTS5 `qa_fts` (обучение на ответах операторов); чистка `audit_log` от presence/read. Таблица `operator_draft` (черновик ответа на сервере) создаётся вне миграций — `src/core/drafts.ts:45-58`. Откат с 25-й схемы на 2.5.0 невозможен.

**Новые backend-модули.**
- `core/drafts.ts` — серверные черновики `(actor_key, conversation_id)`, TTL 30 дней, `mode reply|note`, цитата, `device`, `from_suggestion`.
- `core/pause.ts` — пауза помощника ключом `aiPause` в `setting` (не меняет режим).
- `core/attention.ts` + `shared/attention.ts` — серверное состояние «кому нужен ответ», секции, причины, SLA, пауза, окно.
- `shared/conversation-order.ts` — серверный ранг списка, клиент больше не сортирует.
- `shared/confidence.ts` — уровни `sure|check|unsure` вместо голого числа.
- `core/fts.ts` — русский стеммер + `ftsExpression()` для FTS5.
- `core/channels.ts` — единый справочник каналов и `file_ref`-префиксов.
- `core/netdiag.ts` — человеческие диагнозы DNS/порт/TLS/HTML-вместо-JSON.
- `ai/chunks.ts` — нарезка статей КБ на куски и выбор лучших в бюджете.
- `ai/links.ts` — метки `[[link:key]]`, маскирование/раскрытие ссылок.
- `ai/repair.ts` — терпимый разбор почти-JSON от модели.
- `ai/examples.ts` — пары «вопрос→ответ оператора» (`qa_pair`), похожие примеры в промпт.
- `ai/interface-kb.ts` — справочник интерфейса кабинета Bedolaga (`interface-kb/`, режимы full/lite).
- `ai/eval.ts` + `cli/aieval.ts` — регрессионный прогон качества.
- `cli/setup.ts` + `install.sh --setup/--check` — мастер первичной настройки.
- `store.ts` разбит на 12 репозиториев `core/store/*`.
- `panel/*` разнесён по маршрутам; новая read-модель inbox/thread/live.

**Новые API v3.0.0.** `/api/inbox`, `/api/events?since&epoch`, `/api/bootstrap`, `/api/thread/:id`, `/api/conversations/:id/{draft,presence,intent,engage,release,note}`, `/api/presence`, `/api/team/names`, `/api/suggestions/:id[/decide]`, `/api/assistant/{settings,pause,activity}`, `/api/messages/:id/feedback`, `/api/learning/candidates*`, `/api/kb*` (+ `mine`, `publish`, version-conflict 409), `/api/interface-kb*`, `/api/filters`, `/api/operators`, `/api/roles`, `/api/audit`, `/api/system/{problems,notifications,panel}`, `/api/connections`, `/api/nodes*`, `/api/ai/*`. WS `?v=2` с кадрами `invalidate`, `problems`, `me`, `settings`, `intent`, `draft`, `presence`, `handover_request`; буфер seq/epoch и догон событий.

**Семантика, которую важно перенести.**
- `POST /state` принимает `seen` (ms последнего увиденного входящего) и отдаёт **409 `client_wrote`** — «Решено» не закрывает диалог, где клиент написал после просмотра.
- Идемпотентный ответ: `clientMsgId` + `RepeatGuard` (сейчас in-memory, 24 ч), вложения батчами с `x-client-msg-id`.
- `claim`/lease 15 мин, 409 `locked_by_other` при чужом захвате; `operator_active_at` подавляет AI 45 с.
- Присутствие: `viewing|typing`, окно 90 с, `typing` без захвата.
- «Попросить передать» — заметка + аудит + кадр владельцу, не чаще 1/мин.
- Права: матрица `viewer|agent|lead|admin`, deny-by-default по карте «метод+шаблон → permission», переопределения `role_permission`, отзыв прав на лету (WS close 1008). Новое право `setting:uiDefault`.
- Медиа/WS-билет: HMAC на 10 мин, cookie только для GET медиа.

**ИИ.** Режимы `off|shadow|suggest|auto` (появился `shadow`). Ответы только по фактам: трафик/срок/устройства считает код, модель не арифметизирует; `used[]` обязателен; уточняющий вопрос — один и только при неясности; `operator_note` отдельно от текста клиенту; ссылки через `[[link:key]]`; fallback-модель; «печатает…» и `sendMessageDraft`; бюджет КБ 3500 симв., кусок 4200; `AI_MIN_CONFIDENCE` 0.75 → 0.9; `BEDOLAGA_POLL_SECONDS` 60 → 20; обучение на `qa_pair`.

**Что это значит для CMS.** Все фичи фаз 3–5 из `docs/INTEGRATION-SUPPORT.md` уже реализованы в апстриме — переносить нужно не «с нуля», а портировать готовую логику: `attention`, `conversation-order`, `confidence`, `gate`, `links`, `repair`, `chunks`, `examples`, `drafts`, `pause`, `sla`. Заменить при переносе: FTS5/`bm25` → PostgreSQL `tsvector`/`ts_rank_cd`; `PRAGMA user_version` → миграции CMS; `MAX(x+1, ?)` → `GREATEST`; `INSERT OR IGNORE` → `ON CONFLICT DO NOTHING`; in-memory `RepeatGuard`/`Job`-локи → Postgres/Redis при нескольких воркерах.

## 3. Архитектура (правила, которые нельзя нарушать)

Слои в одну сторону: `channels`/`ai` → `core`; `core` не знает про каналы; панель знает всех.

```
src/
  config.ts          чтение .env, валидация, версия сборки
  index.ts           порядок инициализации всего приложения
  core/              домен (не знает ни про Telegram, ни про AI)
    db.ts            SQLite, миграции по PRAGMA user_version (только дописывать)
    store.ts         диалоги, сообщения, КБ, статистика (EventEmitter = события message/suggestion/...)
    outbox.ts        ЕДИНСТВЕННЫЙ выход наружу (окно ответа 24 ч живёт здесь)
    settings.ts      настройки из панели (Runtime + FIELDS валидатор)
    notify.ts        уведомления оператору, определение тона
    sla.ts           кто ждёт ответа слишком долго
    media.ts         скачивание/потоковая загрузка вложений, сигнатуры, расшифровка голосовых
    templates.ts     заготовки ответов
    operations.ts    очередь (приоритет+время), 579 стр.
    sources.ts       добавление источников через root-only файл-обмен
    update.ts, http.ts, nodes.ts, lifecycle.ts (мёртвый!), outbox.ts
  channels/          источники: tgdm.ts (личка Business), bedolaga.ts, minishop.ts
  ai/                provider, responder, gate, kb, cluster, scrub, mining, outbound, sublink
  integrations/      внешние системы ТОЛЬКО на чтение (customers, remnawave, tgexport)
  panel/             server.ts (Fastify HTTP+WS, 1816 стр.), kbfiles.ts
  cli/               selfcheck.ts, kbmine.ts, rwprobe.ts
public/index.html    панель целиком (разметка+стили+логика)
deploy/minishop-plugin/  узкий service-token API поверх Plugin API v1 MiniShop
```

Жёсткие правила (из их ARCHITECTURE.md):
1. **Наружу пишет только Outbox** (`outbox.send()`). Прямые `bot.api` в логике запрещены.
2. **Загруженному файлу нельзя доверять**: имя для показа, путь из случайного `file_ref`, MIME по сигнатуре; лимиты 45 МБ/10 файлов.
3. **Окно 24 часа — состояние**, проверяется в Outbox, не в панели.
4. **Миграции только дописываются** (массив MIGRATIONS в db.ts, `PRAGMA user_version`).
5. **Черновики КБ вне `kb/`** — в `data/kb-draft/`; в ответы клиентам попадает только опубликованное.
6. **Опора на КБ по названным выдержкам**: модель обязана вернуть номера статей (`used[]`); совпадения по словам недостаточно.
7. **Модель не вызывает действий**: в запросе нет `tools`, в `ai/` нет обращений к Remnawave; разрушающие действия — только оператор из панели с подтверждением.
8. **Переписка чистится перед отправкой в модель** (`scrub.ts`): ключи, ссылки, карты, телефоны, tg-id.
9. **Handoff атомарен**: AI написал «передал специалисту» → уведомление обязано уйти.

## 4. Тикет-конвейер (кратко)

- Входящее → `store.recordInbound()` (дедуп по `external_msg_id`, вложение регистрируется ДО события) → событие `message` → панель (WS), оператору (notify), `responder.schedule()`.
- Debounce 12 с (клиент дописывает мысль); в одном диалоге последовательно, rerun по свежему состоянию.
- Статусы: `open → pending → resolved → closed`; first_response_at — при первом исходящем.
- Handoff — явное состояние `handoff_at`: после него AI молчит по существу, только «ожидайте» раз в handoffRepeatMinutes.
- AI suggest создаёт предложку `ai_suggestion` (pending/sent/edited/rejected/superseded).
- SLA: `SlaWatcher` ловит «нет первого ответа» и «handoff без ответа агента», 1 уведомление/диалог, ≤5 за цикл (SLA_MAX_ALERTS_PER_CYCLE=5).
- Ключевые статусы тикетов Bedolaga: `open / answered / pending` (поллер 60 с).

## 5. БД (better-sqlite3)

- WAL, FK ON, `PRAGMA user_version`, **19 миграций** (дописывать в конец) — `src/core/db.ts:10-553`.
- Таблицы: `conversation`, `message` (+ `attachment`), `business_connection`, `customer` (устар. snapshot), `event` (лог), `ai_suggestion`, `kb_doc` + **FTS5** `kb_fts` (unigram, remove_diacritics), `template`, `poll_state` (курсоры поллинга), `setting`, `job` (mine/auto-learn), `operator_account` (SHA-256 `token_hash`), `operator_presence`, `customer_profile`/`customer_tag`/`customer_note`, `audit_log`, `kb_candidate`, `sla_policy` (seeded: urgent 5/120 … low 240/2880), `saved_filter`, `update_history`, `source_account`, `conversation_source`, `inbox_folder(+_source)`, `role_permission`, `operator_activity`.
- Наша CMS — это НЕ SQLite; при переносе модулей в FastAPI таблицы переносятся в PostgreSQL.

## 6. Интеграции (важно для совместимости с нашей CMS)

### Bedolaga (`channels/bedolaga.ts`, 630 стр.)
- Аутентификация: **`X-API-Key`** — тот же Bot Web API, который CMS уже проксирует (`web/backend/api/v1/bedolaga/`). Конфликтов нет: CMS использует админ-доступ, ai-support — тикетный.
- Эндпоинты Bedolaga Web API, которые он дёргает:
  - `GET /tickets?status` (пагинация 200×50; статусы open/answered/pending), `GET /tickets/{id}`, `POST /tickets/{id}/reply` (**неидемпотентно — retries=0**), `GET /priority`, `GET /status`
  - `GET /messages/{id}/media`, `GET /media/{fileId}`
  - `GET /users/by-telegram-id/{id}`, `GET /users?search`, `GET /users/{id}`, `GET /transactions?user_id`, `GET /subscriptions`, `GET /tickets?user_id`, `GET /partners/referrers/{id}`, `POST /subscriptions/{id}/extend` (retries 0)
  - `GET /pages/faq` — FAQ как база знаний
- Поллер 60 с; cold-start baseline (`bedolaga:last_poll`) — импорт истории, AI/SLA не реагируют на старые сообщения; repair архивных медиа.
- Ограничения: исходящий ответ — только текст; входящие вложения отображаются.

### Remnawave (`integrations/remnawave.ts`, 556 стр.)
- Bearer; мульти-пути `firstWorking` для API v2/v3; capabilities autodetect (profile/devices/reset/revoke).
- **`REMNAWAVE_READONLY=true` по умолчанию — мутации отсекаются до HTTP**.
- Индекс пользователей страницами `/api/users` (кэш 1 ч); поиск клиента по telegramId → шаблону `user_{tg}_*` → description-haystack.
- `nodes()` с `publicNodeName` — срезает IP/домены/порты (для вопросов модели «всё ли в порядке с Германией»).
- Несколько панелей: `REMNAWAVE_PANELS_JSON`.

### Остальные
- `customers.ts` — единая карточка (Support API + Bedolaga + несколько Remnawave + MiniShop), кэш 1 ч с `builtBy=version`, не найден → `suspicious`.
- `bedolaga-customer.ts` — полная карточка (подписки/платежи/тикеты/рефералы/лента); `identityVerified` только по ticket_user_id/tg_id (username прав на финансы не даёт); `safeNote` прячет URI/токены.
- `tgexport.ts` — разбор `result.json` Telegram Desktop → пары «вопрос-ответ» (для майнинга КБ).
- MiniShop: режим plugin (X-API-Key, постоянный service token) / admin (временный AdminBearer); поллер 30 с.

## 7. AI-подсистема

| Модуль | Назначение |
|---|---|
| `provider.ts` | OpenAI-совместимый `/chat/completions`, `response_format:json_object`, ротация ключей (429→след. ключ, 401→мёртвый), Retry-After/backoff, фолбэк-модель на RateLimited/ModelUnavailable, vision только для allowlist-моделей (`AI_VISION_MODELS`), `stripThinking`+`extractJson` по балансу скобок, транскрибация `/audio/transcriptions` (whisper) |
| `responder.ts` | сборка контекста: SYSTEM_PROMPT + KB-выдержки + карточка клиента + состояние нод + история; `visionImages` (≤3 фото); анти-гонка оператора до/после генерации; `parseDraft` → `{reply, confidence, needs_human, no_request, used[], reason}` |
| `gate.ts` | ВСЕ условия автоответа в одном файле: human-hold, режимы shadow/suggest/auto, requireKb + kbHits==0 → suggest, confidence (<0.75), escalated, sensitive-темы (возвраты/мошенничество/юристы/взлом/партнёрства), тон, окно 24 ч, autoPerHour (12/ч) |
| `kb.ts` | файлы `kbDir/*.md` (O_NOFOLLOW, ≤1 МБ), FAQ Bedolaga; FTS5 поиск |
| `scrub.ts` | вырезает ссылки подписок, URL, email, UUID, 32+hex, номера карт, телефоны, IP, tg-id |
| `outbound.ts` | запрещённые IP/домены/uuid/ключи/токены ботов + allowlist доменов (`AI_ALLOWED_DOMAINS`) |
| `mining.ts` | статьи из реальных диалогов (archive/отклонённые предложки/export), scrub до отправки, группировка моделью (`cluster.ts`, лексический fallback cosine+IDF), батчинг по токен-бюджету, черновики → `data/kb-draft` |
| `sublink.ts` | детект ссылки подписки → ref для поиска в Remnawave |

Ключевые AI-настройки (важнейшие из .env):
- `AI_MODE=off|suggest|auto` — off не трогает диалоги; **suggest** пишет предложку человеку (рекомендуется начинать с него); auto отправляет сам, когда ворота пропускают.
- `AI_BASE_URL` / `AI_API_KEY` (через запятую — ротация) / `AI_MODEL` (+ `AI_MODEL_FALLBACK`).
- `AI_REQUIRE_KB=true` — нет ответа в КБ → зовём человека, клиенту само ничего не уходит.
- `AI_HUMAN_HOLD_MINUTES=30`, `AI_MAX_AGE_MINUTES=60`, `AI_DEBOUNCE_SECONDS=12`, `AI_MIN_CONFIDENCE=0.75`.
- `AI_ALLOWED_DOMAINS` — только эти домены модель может называть клиенту.
- `TRANSCRIBE_*` — расшифровка голосовых (Groq whisper, бесплатен).

## 8. Панель (panel/server.ts, 1816 стр. — монолит)

- Fastify: auth по `PANEL_TOKEN` (timingSafeEqual) + токены операторов (SHA-256 в БД), брутфорс-локаут по IP, одноразовые HMAC-билеты для вложений/WS (чтобы не светить токен в URL), per-route permissions, rate-limit 600/мин/IP, строгий CSP (sha-256 инлайн-скрипта), аудит мутаций в `onResponse`.
- Области API: conversations/reply/attachments/note/state/profile; Bedolaga customer + extend (idempotency по UUID operationId); Remnawave subscription/explain/action; suggestions; templates; stats; health/diagnostics/search/queue/sla/filters/operators/roles/operator-stats/audit; settings (permissions `setting:*`); nodes; update/sources (root-файл-обмен); learning/candidates; KB CRUD + publish + `/kb/mine`; ai/keys|models|ping|try (песочница с вердиктом ворот); WS `/ws` (билет, origin, heartbeat).
- Экраны (`public/index.html`): Входящие (inbox), Контроль SLA (queue), База знаний (kb), AI-студия (lab), Инфраструктура (nodes), Аналитика (stats), Команда (team), Состояние системы (diagnostics), Настройки (settings). Гейт-вход по токену, глобальный поиск Ctrl+K, Bedolaga-карточка.
- Активен только `ui-v3.css` (1288 стр., токены `--ui-*`); `ui.css`/`ui-v2.css` — исторические.
- `kbfiles.ts` — защита path-traversal (`basename`+resolve), атомарная запись, `publishDraft` через копирование (EXDEV), транслит-слаг.

## 9. Деплой и обновления

- `install.sh`: генерирует `.env` + `PANEL_TOKEN` (openssl rand -hex 32), chmod 600, каталоги, `docker compose build` → self-check → up; при root ставит systemd-обновлятор.
- systemd: `*.path`-триггеры по `data/update-request.json` / `data/source-request.json`; юниты закалены (`ProtectSystem=strict`, `NoNewPrivileges`, `ReadWritePaths` точечно). **Контейнеру docker.sock НЕ передаётся** — обновления выполняет host-скрипт.
- `host-updater.sh`: валидация запроса (schema v2), скачивание релиза + `.sha256` по TLS, проверка SHA-256, python-проверка tar (нет abs/`..`), сборка образа `ai-support:release-X`, backup БД (better-sqlite3 backup + quick_check), атомарный switch, health-check, автооткат при ошибке.
- nginx (`deploy/ai-support.conf`): 80 только ACME, 443 ssl http2 + HSTS, `access_log off` (билеты в URL), `client_max_body_size 96m`, proxy на `127.0.0.1:8080` + WS-апгрейд.
- Docker: `read_only: true`, tmpfs `/tmp`, cap_drop ALL, no-new-privileges, healthcheck fetch `/`.

## 10. Качество и долги

**Тесты** (без сети и токенов): uitest (структура панели), smoke (личка/вложения/дуп/окно/outbox), webtest (API/auth/WS), aitest (ворота/тон/склейка/handoff), minetest (выгрузка/архив/темы), notifytest, sectest, updatetest, baretest, minishoptest + `selfcheck.ts` для реального сервера. Внешние API — заглушки на localhost. Каждый прод-баг закреплён тестом.

**Долги/монолиты:**
- `panel/server.ts` — 1816 стр.; `core/store.ts` — 1771 стр. (монолиты).
- `channels/bedolaga.ts` (630), `ai/responder.ts` (623), `core/operations.ts` (579), `core/db.ts` (580), `integrations/bedolaga-customer.ts` (568), `integrations/remnawave.ts` (556), `channels/tgdm.ts` (499).
- Мёртвый код: `core/lifecycle.ts` (не подключён) — авто-close 24 ч реализовано через статус-синк поллеров.
- Наследие: таблицы `customer`/`event` частично вытеснены `customer_profile`/`audit_log`; `settings.ts` и `config.ts` держат параллельные списки AI-настроек.
- TODO/FIXME/@ts-ignore — не найдено.

## 11. Мапа внедрения в HexaVeil CMS

**Общий контракт с нашей CMS:** оба сервиса ходят в Bedolaga Bot Web API с `X-API-Key`.
CMS (`web/backend/api/v1/bedolaga/`) — административный доступ; ai-support — тикетный. Параллельная работа безопасна.

| Что взять | Откуда | Куда в CMS | Ценность |
|---|---|---|---|
| AI-отвечатель (черновики/автоответ) | `src/ai/responder.ts`, `gate.ts`, `provider.ts` | FastAPI-модуль `web/backend/ai/` + страница React | ИИ-поддержка в админке |
| База знаний с FTS | `src/ai/kb.ts` + схема kb_doc/kb_fts | PostgreSQL + админ-страница | Статьи для AI и операторов |
| SLA-контроль | `src/core/sla.ts`, `sla_policy` | FastAPI-сервис + виджет дашборда | Контроль ответов |
| Карточка клиента (Bedolaga+Remnawave) | `integrations/customers.ts`, `bedolaga-customer.ts`, `remnawave.ts` | расширение `/api/bedolaga/customers` | Полная карточка в /admin |
| Очередь обращений | `core/operations.ts`, статусы тикетов | FastAPI-роутер + React-страница | Helpdesk в админке |
| Шаблоны ответов | `core/templates.ts` | таблица templates + UI | Быстрые ответы |
| Уведомления в Telegram | `core/notify.ts` | интеграция с ботом | Оповещения операторам |
| Ссылка на панель (вариант 0) | — | сайдбар через `useSidebarLinksStore` (уже есть) | Развернуть ai-support отдельно и просто дать ссылку |

**Варианты внедрения:**
1. **Отдельный сервис + ссылка в сайдбаре** — развернуть контейнер (`support.hexaveil.xyz`), добавить внешнюю ссылку в админку. Минимум изменений, максимум пользы уже сейчас.
2. **Встраивание панели** — страница-iframe в `/admin` (аккуратно с PANEL_TOKEN/CSP) либо отдельная вкладка.
3. **Перенос модулей в стек CMS** (FastAPI + React) — дорого, теряем апдейты upstream; частично оправдан для AI/KB/SLA (см. таблицу).

**Локальный запуск для исследования:**
```bash
cd ai-support
npm ci && npm run build
# скопировать .env.example → .env, задать PANEL_TOKEN
npm start        # → http://127.0.0.1:8080
# или через Docker: <нужен Docker Engine>
```

## 12. Ключевые файлы для копирования (карта)

| Файл | Что внутри |
|---|---|
| `src/ai/gate.ts` | все условия автоответа (чистый кандидат на перенос) |
| `src/ai/scrub.ts` | защита от утечки секретов (легко переносится) |
| `src/core/sla.ts` | SLA-наблюдатель |
| `src/channels/bedolaga.ts` | клиент Bedolaga Web API (шаблон для нашего бэкенда) |
| `src/integrations/remnawave.ts` | работа с Remnawave (панель/ноды) |
| `src/integrations/bedolaga-customer.ts` | карточка клиента с identityVerified |
| `public/index.html` | вся панель (референс UI для React-страниц) |
| `docs/ARCHITECTURE.md` (их) | правила архитектуры — не нарушать при переносе |

*Дата составления: 2026-10-23. При обновлении ai-support (`git -C ai-support pull`) — сверять с CHANGELOG.md эталона и обновлять этот файл.*