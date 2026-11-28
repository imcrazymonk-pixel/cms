# Саппорт — Этап B: ИИ-ассистент + база знаний

**Статус:** выполнен 2026-11-28 (B1–B4; pytest 665, tsc/build зелёные).
**Исходный статус плана:** утверждён к исполнению (B1 → B4)
**Дата:** 2026-11-28
**Основание:** `TASK.md` (Этап A закрыт), `docs/plans/2026-11-28-support-completion.md` §5 (Этап B), `docs/AI-SUPPORT.md` §1a и §7
**Эталон:** `ai-support` v3.0.0 (`ee05237`), `src/ai/*`, `src/core/store/{kb,suggestions}.ts`, `src/core/pause.ts`, `src/panel/routes/{knowledge,assistant}.ts`
**Не переносим:** React-панель апстрима (`ai-support/web/**`), SQLite/FTS5/`bm25`, `better-sqlite3`, Node-сервис, демо-режим, ⌘K, onboarding.
**Стек переноса:** FastAPI + PostgreSQL + React SPA админки CMS, vanilla PHP-сайт не затрагивается.

---

## 0. Факты кодовой базы, на которых стоит план

| Факт | Где | Что из него следует |
|---|---|---|
| Роутер саппорта монтируется с префиксом `/api/support` | `web/backend/main.py:293,327` | новые эндпоинты — `web/backend/api/v1/support/*.py`, без своего префикса |
| Конверт ответа `{success, data}`; ошибки `HTTPException(detail={success,error,code})` | `api/v1/support/conversations.py:1-10,72-78` | контракты B пишем так же; коды — только из `core/errors.py:class ErrorCode` |
| `ensure_support_schema()` проигрывает 004 и 005 и режет SQL по top-level `;` | `core/support/schema.py:14-17,165-193` | **миграцию 006 обязательно добавить в `_MIGRATION_FILENAMES`**; `CREATE INDEX CONCURRENTLY` невозможен (один транзакционный проход) |
| Частичный индекс и `DO $$` блоки поддерживаются сплиттером | `core/support/schema.py:86-162` | расширение CHECK-констрейнтов делаем `DO $$` блоком, как `_AUTHOR_CHECK_SQL` (`:21-49`) |
| Настройки: `env → support_setting → реестр` | `core/support/settings.py:1-10,56-66,175-219` | новые `support_ai_*` идут тем же путём; реестр важнее env (ключ в БД поверх env) |
| Реестр: `SettingDef(key, label, group, tab=...)` | `core/settings_registry.py:16-30,253-330` | новая группа `«ИИ / Саппорт»` внутри `tab="integrations"` — фронт настроек не переписываем |
| Перезагрузка сервиса на месте сохраняет store/outbox/event_bus | `core/support/__init__.py:210-262` | достаточно обновить `service.settings` и `service.ai`; воркеры держат тот же объект |
| Единственный выход наружу — `Outbox.send(conversation, text)` + `check_window` | `core/support/outbox.py:94-122` | автоответ ИИ обязан идти через Outbox, никаких `bot.api` |
| Исходящее пишется `record_outbound(author='bot'|'agent')`, CHECK допускает `bot` | `store/conversations.py:159-200`, `schema.py:44-47` | автоответ ИИ = `author='bot'` (отличим в UI и в счётчике «12/ч») |
| Шина событий in-memory, WS-тип по `EventKind` | `core/support/events.py:13-21`, `ws.py:26-31` | ИИ триггерится подпиской на `MESSAGE_CREATED`; новый кадр `ai_suggestion` |
| Воркеры — список `asyncio.Task` из `start_support_workers` | `core/support/workers.py:22-31` | ИИ-воркер добавляется туда же, один на процесс |
| `support_job`, `support_kb_doc`, `support_kb_candidate`, `support_ai_suggestion` созданы в 004, но не используются | `docs/plans/2026-11-28-support-completion.md:52-56` | 006 — только расширение (`ADD COLUMN IF NOT EXISTS`), не пересоздание |
| API-клиент фронта: `api.get('/support/...')`, `unwrap<T>` | `web/frontend/src/api/support.ts:236,251-295` | новый клиент ложится в тот же файл |
| Маршруты `/support/kb` и `/support/ai` — заглушки `SupportPlaceholder` | `web/frontend/src/App.tsx:139-140` | заменяются на реальные страницы; `navigation.ts:97-100` править не нужно |
| Тесты: фейковый сервис через `app.dependency_overrides[get_support_service]` | `web/backend/tests/test_support_stage_a.py:1-30` | тесты B — тот же приём, без БД и сети |

---

## 1. Решение: конфиг провайдера

### 1.1 Провайдер

OpenAI-совместимый `POST {base_url}/chat/completions` на **httpx.AsyncClient** (уже в `requirements.txt`, новых зависимостей нет).

Правила:
- `response_format={"type":"json_object"}`, `temperature` из настроек, `max_tokens` из настроек.
- Таймаут из настроек (connect 5 s, read = timeout).
- `429` → backoff по `Retry-After` (1 попытка), `5xx`/таймаут → 1 retry, затем **fallback_model**.
- `401/403` → провайдер помечается `dead` до перезагрузки настроек, наружу — понятная ошибка, диалог не ломается.
- Ответ чистится: `strip_thinking` (снять ```` ```json ````, `<!-- -->`, ` Thinking`), затем `extract_json` по балансу скобок, затем `repair.lenient_parse`.
- Никакого `tools`, никаких вызовов Remnawave/Bedolaga из ИИ-слоя (правило апстрима №7).
- httpx-клиент создаётся лениво на первый запрос и живёт на `service.ai`, чтобы не открывать соединения на старте при `mode=off`.
- Прокси: `trust_env=False`; при необходимости переиспользовать `core/outbound_proxy.resolve_proxy(session, "support")`, как в `_telegram_proxy_kwargs` (`core/support/__init__.py:117-137`). В B1 — прямое соединение, прокси — флагом `support_ai_proxy` (см. 1.3, опционально).

### 1.2 Ключи реестра (все `support_ai_*`)

Группа `«ИИ / Саппорт»`, `tab="integrations"`, `sort_order` 100+. Порядок разрешения: **env → `support_setting` → реестр** (реестр побеждает; пустое значение секрета не затирает сохранённое — как `api/v1/settings.py:208-220`).

| Ключ | Тип | env | Дефолт | Смысл |
|---|---|---|---|---|
| `support_ai_mode` | select `off\|shadow\|suggest\|auto` | `SUPPORT_AI_MODE` | `off` | режим помощника |
| `support_ai_base_url` | text | `SUPPORT_AI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-совместимый корень |
| `support_ai_model` | text | `SUPPORT_AI_MODEL` | `gpt-4o-mini` | основная модель |
| `support_ai_fallback_model` | text | `SUPPORT_AI_FALLBACK_MODEL` | `` (пусто) | фолбэк при 429/5xx |
| `support_ai_api_key` | **secret** | `SUPPORT_AI_API_KEY` | `` | ключ (шифруется, `settings_values` + `crypto`) |
| `support_ai_min_confidence` | number 0..1 | `SUPPORT_AI_MIN_CONFIDENCE` | `0.90` | порог осторожности (апстрим v3: 0.75 → 0.9) |
| `support_ai_require_kb` | bool | `SUPPORT_AI_REQUIRE_KB` | `1` | требовать опору на КБ |
| `support_ai_auto_per_hour` | number | `SUPPORT_AI_AUTO_PER_HOUR` | `12` | лимит автоответов в час на диалог, `0` = без лимита |
| `support_ai_human_hold_minutes` | number | `SUPPORT_AI_HUMAN_HOLD_MINUTES` | `30` | тишина после ответа оператора |
| `support_ai_max_tokens` | number | `SUPPORT_AI_MAX_TOKENS` | `900` | потолок ответа |
| `support_ai_temperature` | number 0..2 | `SUPPORT_AI_TEMPERATURE` | `0.2` | температура |
| `support_ai_timeout_seconds` | number 5..120 | `SUPPORT_AI_TIMEOUT_SECONDS` | `30` | таймаут запроса |
| `support_ai_debounce_seconds` | number 3..60 | `SUPPORT_AI_DEBOUNCE_SECONDS` | `8` | склейка серии сообщений |
| `support_ai_kb_budget_chars` | number | `SUPPORT_AI_KB_BUDGET_CHARS` | `3500` | бюджет выдержек КБ в промпте |
| `support_ai_allowed_domains` | text | `SUPPORT_AI_ALLOWED_DOMAINS` | `hexaveil.xyz,cabinet.fortf.ru` | домены, которые можно называть клиенту |
| `support_ai_language` | select `ru\|en` | `SUPPORT_AI_LANGUAGE` | `ru` | язык ответа |
| `support_ai_brand` | text | `SUPPORT_AI_BRAND` | `HexaVeil` | как называть сервис клиенту |
| `support_ai_proxy` | select `inherit\|direct\|custom` | `SUPPORT_AI_PROXY_MODE` | `direct` | опционально, если понадобится |

**Инвариант:** если `support_ai_api_key` пуст → **эффективный режим = `off`**, независимо от `support_ai_mode`; API отдаёт `has_key:false`, UI показывает баннер «Ключ не задан». Никаких автоответов без ключа.

### 1.3 Реализация в коде

- `SupportSettings` (`core/support/settings.py:29-49`): добавить поля `ai_*` с `Field(default=..., ge/le=...)`.
- `SUPPORT_OVERRIDES` (`:56-66`): добавить адресацию `("field", "ai_...")`; ветку `_apply_registry_overrides` (`:114-172`) переписать на **generic-применение** по `SettingDef.type` (`bool/number/select/text`) с сохранением существующих спец-случаев `tg_*`. Это единственное место с реальным риском регресса — покрыть тестом на старые ключи (см. B1 AC).
- `AiConfig` — иммутабельный снапшот (`dataclass(frozen=True)`) в `core/support/ai/config.py`: `mode, effective_mode, has_key, base_url, model, fallback_model, api_key, min_confidence, require_kb, auto_per_hour, human_hold_minutes, max_tokens, temperature, timeout, debounce, kb_budget, allowed_domains, language, brand`.
- `SupportService.ai: AiRuntime | None` (`core/support/__init__.py:49-58`); `init_support` в обеих ветках (`:240-252`) вызывает `AiRuntime.from_settings(settings)`. In-place reload настроек (`on_settings_changed`) подхватывается воркером без рестарта.
- `aiPause` **не** отдельный ключ реестра: JSON в `support_setting` (`store.get_json_setting/set_json_setting`, `store/__init__.py:196-203`), как у апстрима (`pause.ts`, `PAUSE_MAX_MS` = 31 день). Пауза не меняет режим.
- `redact` для API: `GET /assistant/settings` никогда не отдаёт `api_key`; `base_url` — как есть (не секрет).

---

## 2. Схема БД — миграция `006-support-ai-kb.sql`

### 2.0 Номер миграции

`docs/plans/2026-11-15-changelog-history-editable.md:52,100,116` резервирует `006-docs-history.sql`. **Занимаем 006 под саппорт, docs-history сдвигаем на 007.**

Причина: саппорт-схема накатывается автоматически на старте (`ensure_support_schema`), а docs-history ещё не реализована (файла `006-docs-history.sql` в репозитории нет). Нумерация кода, который реально едет, идёт первой.
Обязательно: поправить три строки в плане docs-history (`006` → `007`) в том же коммите, что и B1.

### 2.1 Общие правила файла

- Стиль 004: только идемпотентный DDL (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `DO $$ ... $$` для констрейнтов).
- **Перед написанием** сверить фактические колонки 004 (`support_ai_suggestion`, `support_kb_doc`, `support_kb_candidate`, `support_job`) — колонки, которые уже есть, не пересоздавать; расхождения типов решать через `ALTER ... TYPE` только при необходимости.
- `CREATE INDEX CONCURRENTLY` запрещён (сплиттер + одна транзакция).
- Никакого FTS5, `bm25`, `PRAGMA`. Полнотекст = `tsvector` + GIN, ранг = `ts_rank_cd`.

### 2.2 `support_kb_doc` (статьи)

Добавить недостающее:

| Колонка | Тип | Заметка |
|---|---|---|
| `slug` | `TEXT` | транслит-слаг, генерируется приложением |
| `status` | `TEXT NOT NULL DEFAULT 'draft'` | `draft\|published\|archived` |
| `version` | `INT NOT NULL DEFAULT 1` | оптимистичная блокировка |
| `source` | `TEXT NOT NULL DEFAULT 'manual'` | `manual\|import\|candidate\|faq` |
| `tags` | `TEXT[] DEFAULT '{}'` | поиск/группировка |
| `updated_by` | `BIGINT` | id админа |
| `published_at` / `archived_at` | `TIMESTAMPTZ` | |

CHECK `status IN ('draft','published','archived')` — через `DO $$` (drop+add, как `_AUTHOR_CHECK_SQL`).
Индексы:
- `idx_support_kb_doc_fts` — `USING GIN (to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(body,'')))`. Именно **двухаргументная** форма `to_tsvector(regconfig, text)` — она IMMUTABLE и годится для индекса; одноаргументная STABLE — не годится.
- `idx_support_kb_doc_status` — `(status, updated_at DESC)`.
- `uq_support_kb_doc_slug` — `UNIQUE (slug) WHERE slug IS NOT NULL`.

Поиск (в `kb/fts.py`): предикат `to_tsvector('russian', title||' '||body) @@ websearch_to_tsquery('russian', :q)`, сортировка `ts_rank_cd(...) DESC, updated_at DESC`. `websearch_to_tsquery`, не `plainto_tsquery` — не падает на кавычках/`|` из пользовательского ввода.

### 2.3 `support_ai_suggestion` (предложки и автоответы)

Добавить: `final_text TEXT`, `answer_message_id BIGINT REFERENCES support_message(id) ON DELETE SET NULL`, `operator_note TEXT`, `model TEXT`, `gate_action TEXT`, `gate_reason TEXT`, `latency_ms INT`, `tokens_in INT`, `tokens_out INT`.
Колонки `used` (JSONB со ссылками на статьи), `confidence`, `status`, `conversation_id`, `message_id` — уже в 004, **не дублировать**.
Статусы: расширить CHECK до `pending|sent|edited|rejected|superseded` (`DO $$`, идемпотентно).
Индексы:
- `idx_support_ai_suggestion_conv` — `(conversation_id, created_at DESC)`.
- `idx_support_ai_suggestion_status` — `(status, created_at DESC)`.
- `uq_support_ai_suggestion_pending` — `UNIQUE (conversation_id) WHERE status='pending'`, **после** нормализации: `UPDATE support_ai_suggestion SET status='superseded' WHERE status='pending' AND id NOT IN (SELECT max(id) ... GROUP BY conversation_id)`.

Семантика записи:
| gate_action | status после генерации | Кто видит |
|---|---|---|
| `auto` | `sent` (+`final_text`, `answer_message_id`) | клиент получил ответ, оператор видит в треде |
| `suggest` | `pending` | карточка в треде + `/support/ai` |
| `shadow` | `pending` (без показа в треде, виден в активности) | только `/support/ai` |
| `skip` | строка не создаётся | — |

`aiRepliesSince` = `count(*) WHERE conversation_id=? AND gate_action='auto' AND status='sent' AND created_at >= now()-1h`.

### 2.4 `support_qa_pair` (обучение на ответах операторов)

```sql
CREATE TABLE IF NOT EXISTS support_qa_pair (
  id BIGSERIAL PRIMARY KEY,
  conversation_id BIGINT REFERENCES support_conversation(id) ON DELETE SET NULL,
  source TEXT NOT NULL DEFAULT 'operator' CHECK (source IN ('operator','import','feedback')),
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  external_key TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
UNIQUE (external_key);
GIN (to_tsvector('russian', question || ' ' || answer));
```

`external_key = sha256(normalize(question) + '\x1f' + normalize(answer))` — весь дедуп на нём (`ON CONFLICT (external_key) DO NOTHING`).

### 2.5 `support_operator_draft` (серверный черновик)

```sql
CREATE TABLE IF NOT EXISTS support_operator_draft (
  actor_id BIGINT NOT NULL,
  conversation_id BIGINT NOT NULL REFERENCES support_conversation(id) ON DELETE CASCADE,
  text TEXT NOT NULL DEFAULT '',
  mode TEXT NOT NULL DEFAULT 'reply' CHECK (mode IN ('reply','note')),
  quote TEXT,
  from_suggestion_id BIGINT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (actor_id, conversation_id)
);
```
Таблица нужна уже в B1: кнопка «Править» в ИИ-черновике сохраняет правку, чтобы она выжила перезагрузку вкладки.

### 2.6 `support_kb_candidate` (идеи статей)

Добавить недостающее: `status TEXT NOT NULL DEFAULT 'new'` (`new|accepted|rejected`), `reason TEXT`, `decided_at`, `decided_by BIGINT`, `doc_id BIGINT`, `question TEXT`, `answer TEXT`, `topic TEXT`, `occurrences INT NOT NULL DEFAULT 1`, `source TEXT NOT NULL DEFAULT 'mining'`.
CHECK через `DO $$`; `uq_support_kb_candidate_topic` — `UNIQUE (topic) WHERE status='new'` (одна идея на тему).

### 2.7 `support_job` (фоновые задачи)

Добавить недостающее: `kind TEXT`, `status TEXT NOT NULL DEFAULT 'queued'` (`queued|running|done|error`), `payload JSONB`, `result JSONB`, `error TEXT`, `progress INT NOT NULL DEFAULT 0`, `total INT`, `created_by BIGINT`, `started_at`, `finished_at`.
`uq_support_job_active` — `UNIQUE (kind) WHERE status IN ('queued','running')` (второй импорт того же типа → 409).

### 2.8 Что таблиц не получает

- Пауза — `support_setting['aiPause']`.
- Настройки — реестр `settings` (не новая таблица).
- Статистика использования — считается из `support_ai_suggestion` (`tokens_in/out`, `gate_action`), отдельной таблицы нет.

---

## 3. Режимы и ворота

### 3.1 Режимы

`off` — ничего не делает (событие игнорируется, черновики не пишутся).
`shadow` — генерирует, пишет строку `pending` с `gate_action='shadow'`, **клиенту не отправляет и в треде не показывает** (виден в `/support/ai` → активность). Нужен, чтобы набрать статистику до включения `suggest`.
`suggest` — генерирует, кладёт предложку оператору.
`auto` — отправляет сам, если ворота вернули `auto`.

Решение: `shadow` **оставляем** — это единственный безопасный способ проверить качество на живом трафике; стоит ~0 кода (одна ветка гейта).

### 3.2 `gate.decide()` — точный порядок (порт `ai-support/src/ai/gate.ts:147-243`)

Вход: `conversation`, `client_text`, `draft{reply, operator_note, reason, needs_human, no_request, clarify, used[], confidence}`, `kb_hits`, `runtime`, `pause`, `recent_auto_count`, `tone`.

1. `mode == off` → `skip`.
2. Пауза помощника активна → `shadow`→`shadow` / иначе `suggest` (причина «пауза помощника»).
3. Ответ оператора за `human_hold_minutes` → `shadow`/`suggest` (причина «пауза после ответа оператора»). **Проверяется раньше доверия/КБ** — иначе ИИ снова влезает в диалог.
4. `handoff_at` стоит → `shadow`/`suggest` («диалог ждёт специалиста»).
5. `mode == shadow` → `shadow`.
6. `mode != auto` → `suggest` («режим …»).
7. Пустой `reply` → `suggest` («нет текста для клиента»).
8. Уточняющий вопрос: если `clarify` и уточнение уже задавалось в диалоге → `suggest` («уточняющий вопрос уже задавали»).
9. `require_kb` и `used[]` пуст и не `clarify` → `suggest` («ответ не опирается на базу знаний»).
10. `needs_human` и (`require_kb` или `confidence < 0.85`) → `suggest`.
11. `confidence < min_confidence` → `suggest`.
12. `conversation.escalated` → `suggest`.
13. Чувствительная тема → `suggest`.
14. Агрессивный тон → `suggest` («клиент на взводе»).
15. Окно ответа закрыто → `skip`.
16. `auto_per_hour > 0` и автоответов за час ≥ лимита → `suggest`.
17. Иначе → `auto`.

### 3.3 Наше уточнение к п.9 (фиксируем как решение)

Формулировка задачи: «`used[]` не пуст **или** профиль клиента». Реализуем так:

| `require_kb` | `used[]` | профиль клиента | Итог |
|---|---|---|---|
| on | не пуст | любой | проходим дальше |
| on | пуст | любой | `suggest` («нет опоры на КБ») |
| off | не пуст | любой | проходим |
| off | пуст | есть | проходим (ответ на общих основаниях, но с опорой на карточку) |
| off | пуст | нет | `suggest` |

Обоснование: при `require_kb=on` профиль не отменяет главный предохранитель от выдумок; профиль как замена опоры работает только когда оператор сознательно снял требование КБ. Фиксируется в ADR (см. B1).

Чувствительные темы (регэкспы, RU+EN): возврат/деньги/чарджбэк, мошенничество/скам, юрист/суд/претензия, взлом/угнали аккаунт/чужой доступ, партнёрство/реклама/инвестиции, угрозы/оскорбления, запрос персональных данных, «дайте бесплатно/пробный без оплаты».
Уровни уверенности (`shared/confidence`): `CHECK_BAND = 0.1`; `sure` если `score ≥ min_confidence` и есть источники и модель не просила человека; `unsure` если текста нет, или модель просила человека и гейт не пропустил, или `score < min_confidence-0.1`; иначе `check`. Считается **от порога из настроек**, а не от своей константы — подпись не спорит с гейтом.

### 3.4 Пауза

`aiPause` в `support_setting`: `{"until": ISO, "by": "<login>", "at": ISO, "note": "..."}`; `until` ≤ now + 31 день; истёкшая пауза считается неактивной и вычищается лениво. API: `POST /assistant/pause {hours}` (1..744) или `{until}`, `DELETE /assistant/pause`. Пауза не меняет `support_ai_mode`.

---

## 4. Генерация

### 4.1 Конвейер (`ai/responder.py`)

1. Прочитать диалог + последние ≤20 сообщений (`store.list_messages`), карточку клиента (`build_customer_card`, кэш 60 с) — **только для контекста, в промпт без персональных данных** (см. 4.3).
2. Поиск по КБ: `q = последние 2–3 входящих`, `limit 8` по `ts_rank_cd`, затем `chunks.select_chunks(hits, query, budget=kb_budget_chars, maxChunk=4200)`. `CHUNK_TARGET = 900` (порт `chunks.ts`).
3. Похожие пары операторов: `examples.similar_examples(q, limit=3)` из `support_qa_pair` (FTS + лексический отбор), каждая ≤ 600 символов, чистится `scrub`.
4. `interface-kb` **не переносим** в B (это каталог экранов Bedolaga Cabinet и отдельный редактор картинок — дорого, ценности в B мало). Вместо него — статические факты о кабинете в КБ (`source='faq'`).
5. Сборка промпта (`ai/prompt.py`):
   - system: роль «оператор поддержки {brand}», **только факты из выдержек**, не арифметизировать (трафик/срок/устройства — только если цифра пришла в выдержке или карточке), не выдумывать ссылки, не упоминать ИИ/модель/базу знаний, язык `language`, максимум один уточняющий вопрос, `operator_note` отдельно от `reply`.
   - user: выдержки КБ с номерами `[1]..[n]`, примеры операторов, состояние диалога (последние сообщения, очищенные `scrub`), карточка клиента (только безопасные поля), вопрос.
   - `DRAFT_SCHEMA`: `{"reply":"","operator_note":"","reason":"","needs_human":false,"no_request":false,"clarify":false,"used":[],"confidence":0.0}`; `reason ≤ 140` символов.
6. Вызов провайдера, `repair` при невалидном JSON (1 повтор, затем фолбэк-модель, затем `failed` → `suggest` с пустым текстом не создаётся).
7. Пост-обработка:
   - `links.expand(text, links)` — модель пишет `[[link:cabinet]]`, код раскрывает в разрешённый URL; ключи: `cabinet, bot, faq, tariffs, subscription, support`; `MAX_LINKS = 20`.
   - `outbound.check(text, allowed_domains)` — замок (см. 4.3). Нарушение → действие понижается до `suggest`, причина `outbound_blocked`, в `gate_reason`.
   - `used[]` нормализуется в `[{doc_id,title,chunk}]` (модель возвращает номера — маппим на реальные id; неизвестный номер отбрасываем).
8. `gate.decide()` → запись `support_ai_suggestion` + событие `AI_SUGGESTION` + при `auto`: `outbox.send()` → `record_outbound(author='bot')` → `UPDATE support_ai_suggestion SET status='sent', answer_message_id=…`.

### 4.2 Замок `outbound` и `scrub`

- `scrub` (переписка → модель): URL, `vless://`/`sub://`, e-mail, UUID, 32+ hex, номера карт, телефоны, IP, tg-id, `sk-…`, bot-token `\d{8,10}:[A-Za-z0-9_-]{30,}` → `[скрыто]`; схлопывание пробелов.
- `outbound` (ответ → клиент): блокируем, если есть IP, домен вне `allowed_domains`, UUID, ключи/токены, PAN, 32+ hex, иероглифы (`\p{Script=Han|Hiragana|Katakana|Hangul}`), мета-слова «ИИ», «искусственный интеллект», «нейросеть», «модель», «база знаний», «КБ», «промпт», «ассистент». Вердикт `{ok, reason, hits[]}`.
- Обе функции — чистые, без I/O, тестируются юнит-тестами.

### 4.3 Триггер и debounce (без multi-worker)

- Воркер `ai/worker.py` подписывается на `EventBus.subscribe(EventKind.MESSAGE_CREATED)` и читает очередь в цикле — как остальные воркеры.
- На событие: перечитать диалог; если последнее сообщение не `direction='in'` → игнор; если `mode=off` → игнор; если канал не поддерживает ответ (нет сендера в `outbox.has_sender`) → игнор.
- Debounce: `dict[conversation_id, asyncio.Task]`; новый входящий **отменяет** предыдущую задачу и создаёт новую `sleep(debounce_seconds)` → генерация. Один диалог — одна генерация за раз.
- Ограничение параллелизма: `asyncio.Semaphore(2)` на провайдерские вызовы (защита от 429 при всплеске).
- Перед отправкой автоответа — повторная проверка: не появился ли ответ оператора за время генерации (`last_human_reply_at`), не включили ли паузу, не сменился ли режим. Если да → `suggest`.
- Так как uvicorn-воркер один, in-process debounce корректен. Частичные индексы из 2.3/2.7 держат защиту и при гипотетическом масштабировании.

---

## 5. API (точные контракты)

Все — под `get_current_admin` (`api/deps.py`), конверт `{success, data}`, ошибки через `HTTPException(detail={success:false, error, code})`. Новые коды в `core/errors.py:ErrorCode`: `AI_DISABLED`, `AI_PAUSED`, `KB_VERSION_CONFLICT`, `KB_DOC_PUBLISHED`, `IMPORT_TOO_LARGE`, `IMPORT_PARSE_FAILED`, `JOB_BUSY`, `PROVIDER_ERROR`.

### 5.1 `api/v1/support/kb.py`

| Метод | Путь | Тело/Query | Ответ `data` |
|---|---|---|---|
| GET | `/kb` | `status=draft\|published\|archived\|all`(all), `q<=200`, `page>=1`, `per_page 1..100` | `{items:[{id,slug,title,source,status,version,updated_at,updated_by,excerpt}],total,page,per_page}` |
| GET | `/kb/{id}` | — | `{doc:{id,slug,title,body,status,version,tags,source,created_at,updated_at,published_at}}` |
| POST | `/kb` | `KbDocIn{title 1..200, body 1..200000, slug?, tags?[]<=20, source='manual'}` | `{id,slug,version:1,status:'draft'}` |
| PUT | `/kb/{id}` | `KbDocIn + expected_version:int` | `{id,version:expected+1,status}`; рассинхрон → **409 `KB_VERSION_CONFLICT`** |
| POST | `/kb/{id}/publish` | `{expected_version}` | `{id,status:'published',published_at}` |
| POST | `/kb/{id}/archive` | `{}` | `{id,status:'archived'}` |
| POST | `/kb/{id}/restore` | `{}` | `{id,status:'draft'}` |
| DELETE | `/kb/{id}` | — | `{deleted:true}`; `published` → **409 `KB_DOC_PUBLISHED`** (сначала archive) |
| GET | `/kb/search` | `q 1..200`, `limit 1..20` | `{items:[{id,title,rank,snippet<=300}]}` (операторский поиск) |
| GET | `/kb/candidates` | `status=new\|accepted\|rejected`, `page`, `per_page` | `{items:[{id,topic,question,answer,occurrences,source,status,created_at}],total}` |
| POST | `/kb/candidates/{id}` | `{decision:'accept'\|'reject', reason?, title?, body?}` | `{id,status,doc_id?}`; `accept` создаёт `support_kb_doc` (`status='draft'`, `source='candidate'`) |

Правило публикации: **поиск ИИ и операторов видит только `status='published'`**. Правка опубликованной статьи меняет её на месте (version++), не уводя в draft — иначе статья мгновенно исчезает из ответов. Защита от потери правок — `expected_version`, не черновик.

### 5.2 `api/v1/support/suggestions.py`

| Метод | Путь | Тело/Query | Ответ `data` |
|---|---|---|---|
| GET | `/suggestions` | `status=pending\|sent\|edited\|rejected\|superseded\|all`, `conversation_id?`, `page`, `per_page` | `{items:[…],total}` |
| GET | `/suggestions/{id}` | — | `{id,conversation_id,message_id,text,final_text,operator_note,confidence,level:'sure'\|'check'\|'unsure',used:[{doc_id,title}],reason,gate:{action,reason},model,status,created_at}` — питает «Почему так?» |
| POST | `/suggestions/{id}/decide` | `{decision:'send'\|'edit'\|'reject', final_text?<=4000, reason?}` | `send` → `{status:'sent',message_id}`; `edit` → `{status:'edited',text}`; `reject` → `{status:'rejected'}` |

`send`: проверка окна/lease (как `POST /conversations/{id}/reply`), `outbox.send` → `record_outbound(author='agent')` → `final_text`, `answer_message_id`, `status='sent'`, событие `MESSAGE_CREATED`. Не `bot` — отправил человек, кнопкой.
`edit` — не отправляет, возвращает текст в композер и сохраняет `support_operator_draft` (автосохранение правки).
Причина отказа — из фиксированного набора (`REJECT_REASONS`): `wrong_facts, unclear, off_topic, too_formal, sensitive, other`; пишется в `operator_note`, при `verdict`-фидбеке — в `qa_pair`.

### 5.3 `api/v1/support/assistant.py`

| Метод | Путь | Тело/Query | Ответ `data` |
|---|---|---|---|
| GET | `/assistant/settings` | — | `{mode,effective_mode,has_key,paused:{until,by,note}\|null,model,fallback_model,base_url,min_confidence,require_kb,auto_per_hour,human_hold_minutes,debounce_seconds,kb_budget_chars,language,brand,allowed_domains}` — **без api_key** |
| PUT | `/assistant/settings` | `{mode?, min_confidence?, require_kb?, auto_per_hour?, debounce_seconds?}` | те же поля после применения; пишется в реестр через общий сервис записи (см. 5.5), затем `on_settings_changed` → hot reload |
| POST | `/assistant/pause` | `{hours 1..744}` \| `{until:ISO}` | `{until,by,note?}` |
| DELETE | `/assistant/pause` | — | `{paused:false}` |
| GET | `/assistant/activity` | `since?`, `before?` (id), `limit 1..100` | `{items:[{id,conversation_id,action,gate_reason,confidence,model,tokens_in,tokens_out,status,created_at}]}` |
| GET | `/assistant/stats` | `days 1..90` | `{generated,sent,edited,rejected,superseded,auto_sent,suggest_sent,shadow,sent_rate,avg_confidence,tokens_in,tokens_out,by_day:[{date,generated,sent}]}` |
| POST | `/assistant/try` | `{text 1..2000, assume_auto?=false}` | `{draft:{reply,operator_note,used,confidence,clarify,needs_human},gate:{action,reason,level}}` — песочница, **ничего не пишет в БД** |

`PUT /assistant/settings` — единственная точка записи `support_ai_*` из экрана ИИ. Экран «Настройки» показывает те же ключи (единый реестр, один источник истины).

Расширение существующего `GET /config-status` (`conversations.py:tail`): добавить `ai:{mode,effective_mode,has_key,paused,model}` — фронт уже вызывает этот эндпоинт в панели поллеров.

### 5.4 `api/v1/support/feedback.py`

| Метод | Путь | Тело | Ответ |
|---|---|---|---|
| POST | `/messages/{id}/feedback` | `{verdict:'correct'\|'wrong'\|'partial', note?<=1000, correct_answer?<=4000}` | `{qa_pair_id?}` |

`correct`/`partial` → `support_qa_pair` (`source='feedback'`, `question` = входящее, на которое отвечали, `answer` = `correct_answer` или отправленный текст). `wrong` + `correct_answer` → то же **плюс** `support_kb_candidate` (`status='new'`, `source='feedback'`).

### 5.5 Запись настроек

`_upsert_in`/`_store_value`/`_table_for` живут внутри `api/v1/settings.py:135-160`. Вынести их в `core/settings_values.py` как `async def upsert_value(db, key, value) -> None` (шифрование секретов внутри) и переиспользовать в `api/v1/settings.py` и `api/v1/support/assistant.py`. Прямой SQL из саппорта в таблицу настроек — запрещён.

---

## 6. Фронтенд

### 6.1 `/support/kb` — `pages/support/Kb.tsx`

Раскладка: две колонки (`xl:grid-cols-[320px_minmax(0,1fr)]`), как в `Queue.tsx:435`.
- Левая: поиск (debounce 300 мс), табы `Статьи / Черновики / Идеи`, список с бейджем статуса и `version`.
- Правая: редактор — `title`, `tags`, `body` (textarea, monospace, ≥20 строк), счётчик символов; кнопки «Сохранить» (`expected_version`), «Опубликовать», «В архив», «Удалить» (только для неопубликованных). При 409 `KB_VERSION_CONFLICT` — диалог «Статья изменена, перезагрузить?».
- Кнопка «Импорт» открывает `ImportPanel`: выбор `Текст чата` / `result.json`, вставка текста или загрузка файла, `dry_run`-чекбокс, прогресс по `job_id` (поллинг 1.5 с, затем стоп).
- Компоненты: `components/kb/KbList.tsx`, `KbEditor.tsx`, `CandidateList.tsx`, `ImportPanel.tsx`.
- Стиль — существующие классы (`glass-card`, `page-header`, `btn-*`), токены из `index.css`, без новых npm-зависимостей.

### 6.2 `/support/ai` — `pages/support/Assistant.tsx`

- Карточка «Режим»: 4 радио-сегмента `off/shadow/suggest/auto`, текущий `effective_mode`; если `has_key:false` — баннер «Ключ API не задан» со ссылкой на настройки; если `effective_mode != mode` — вторая строка «фактически выключен: нет ключа».
- Карточка «Пауза»: до какого времени, кем, кнопки `1 ч / 4 ч / 24 ч / до утра` и «Снять».
- Карточка «Параметры»: `min_confidence` (slider 0.5–1.0 с шагом 0.05), `require_kb` (switch), `auto_per_hour` (number), `debounce_seconds` (number) → `PUT /assistant/settings`.
- Карточка «Статистика»: за 7/30 дней — сгенерировано/отправлено/правок/отклонено, `sent_rate`, средняя уверенность, токены; мини-график по дням — **CSS-бары** (без chart-библиотек).
- Карточка «Песочница»: textarea + «Проверить» → `POST /assistant/try`, показывает `reply`, `level`, `used[]`, вердикт гейта. Это главный инструмент настройки порога.
- Компоненты: `components/assistant/{ModeCard,PauseCard,ParamsCard,StatsCard,TryPanel}.tsx`.

### 6.3 Блок ИИ-черновика в треде

- Новый `components/AiDraftCard.tsx`, рендерится в `MessageThread.tsx` **над композером** (после списка сообщений).
- Данные: `suggestion` приходит в `GET /conversations/{id}` (`SupportConversationDetail.suggestion`) — без отдельного запроса на каждый тред; обновление по WS-кадру `ai_suggestion`.
- Содержимое: бейдж уровня (`Уверен · Проверьте · Не уверен`), текст, `used[]` как чипы статей, раскрывающийся «Почему так?» (`reason` + `gate.reason` + `operator_note`), кнопки «Отправить» (`decide:send`), «Править» (`decide:edit` → текст в композер), «Отклонить» (выбор причины). В `shadow` карточка не показывается.
- `operator_note` рендерится отдельным серым блоком «Заметка для оператора», **никогда** не попадает в текст клиенту.
- «Это неверно» → `POST /messages/{id}/feedback` с `verdict:'wrong'`, поле «Как правильно?».

### 6.4 `api/support.ts`

Добавить типы: `SupportAiSuggestion`, `SupportAiGate`, `SupportAiSettings`, `SupportAiPause`, `SupportAiStats`, `SupportKbDoc`, `SupportKbListItem`, `SupportKbCandidate`, `SupportImportJob`, `SupportFeedbackPayload`.
Добавить методы: `listKb, getKb, createKb, updateKb, publishKb, archiveKb, restoreKb, deleteKb, searchKb, listCandidates, decideCandidate, importKb, getImportJob, getSuggestion, decideSuggestion, getAssistantSettings, updateAssistantSettings, pauseAssistant, resumeAssistant, assistantActivity, assistantStats, tryAssistant, messageFeedback`.
Расширить `SupportErrorCode` и `SupportConversationDetail` (`suggestion`).

### 6.5 Настройки

Новые ключи появляются автоматически как группа `«ИИ / Саппорт»` в `tab="integrations"`. Проверить `pages/Settings.tsx`, что рендерятся `type="secret"` (маска + «оставить пустым, чтобы не менять»), `select`, `number`, `bool` — если группы сортируются по жёсткому списку, добавить новую группу в этот список (единственная правка).

### 6.6 WS

`lib/supportSocket.ts` + `core/support/ws.py:26-31`: новый кадр `{"type":"ai_suggestion","data":{conversation_id,suggestion_id,status}}`. Фронт по нему инвалидирует текущий тред и (опционально) список.

---

## 7. Импорт

Фоновый, через `support_job`, всегда `asyncio.to_thread` для парсинга и батчевая запись (500 пар за транзакцию).

### 7.1 Общие лимиты

`20 МБ` текстовая вставка, `50 МБ` файл `result.json`, `200 000` сообщений, `200` кандидатов за прогон, бюджет 120 с. Превышение → **413 `IMPORT_TOO_LARGE`**. Второй активный джоб того же `kind` → **409 `JOB_BUSY`**.

### 7.2 Текст чата

Формат (экспорт Telegram Desktop / копипаста):
```
[28.11.2026 12:34:56] Поддержка HexaVeil: Здравствуйте! ...
[28.11.2026 12:35:10] Иван: Не подключается Германия
```
Парсер `import/tg_text.py`:
- строка-заголовок: `^\[(\d{1,2})\.(\d{1,2})\.(\d{2,4})[ ,]+(\d{1,2}):(\d{2})(?::(\d{2}))?\]\s*([^:\n]{1,80}):\s?(.*)$`
- строки без заголовка — продолжение предыдущего сообщения (склейка через `\n`);
- участники: множество имён; оператор — из набора `operator_names` (по умолчанию `Поддержка HexaVeil, Поддержка, Support, HexaVeil, Администратор`), настраивается в `payload.operator_names`.
- пары: подряд идущие `клиент → оператор` (не более 3 сообщений с каждой стороны склеиваются в один блок).
- кодировка: `utf-8-sig`; при `UnicodeDecodeError` — `cp1251` (экспорт старых клиентов Windows). Ошибка обеих → **422 `IMPORT_PARSE_FAILED`**.
- если заголовков не найдено ни одного → 422 с подсказкой формата.

### 7.3 `result.json`

`import/tg_json.py`:
- корень: объект с `messages[]`; элементы `type != "message"` пропускаются.
- `text`: строка **или** массив (строки и объекты `{"type":"link"|"bold"|"code"|"mention","text":…}`) → плоский текст конкатенацией `text` объектов.
- пары: приоритет `reply_to_message_id` (ответ на сообщение клиента); иначе — по двум участникам (`from_id`), чередование.
- `from` может отсутствовать у служебных — пропуск.
- `date` — ISO-строка, приводится к `datetime` для сортировки.
- битый JSON → **422 `IMPORT_PARSE_FAILED`** с позицией ошибки.

### 7.4 Дедуп и результат

`external_key = sha256(norm(question) + '\x1f' + norm(answer))`, `norm` — lower, схлопнутые пробелы, срезанная пунктуация по краям. Вставка `ON CONFLICT (external_key) DO NOTHING` → `skipped_duplicates`.
Идеи статей (`import/cluster.py`): нормализация → стоп-слова RU → топ-3 токена как `topic`; группы с ≥ 2 парами и одинаковым `topic` → `support_kb_candidate(status='new', occurrences=n)`. Максимум 200 групп, сортировка по `occurrences`.
Результат джоба: `{questions, pairs_created, skipped_duplicates, candidates_created, errors[]}` в `support_job.result`.

### 7.5 API импорта

| Метод | Путь | Тело | Ответ |
|---|---|---|---|
| POST | `/kb/import` | `{kind:'text'\|'result_json', text?, payload?, operator_names?[], dry_run?}` | `{job_id}` (202-семантика в теле, HTTP 200) |
| GET | `/kb/import/{job_id}` | — | `{id,kind,status,progress,total,result?,error?,started_at,finished_at}` |
| POST | `/kb/import/{job_id}/cancel` | — | `{status:'error',error:'cancelled'}` |

`dry_run=true` — парсинг и подсчёт без записи; результат в `result` (`would_create`, `would_skip`).

---

## 8. Тесты

Внешние вызовы — только фейки. Ни сети, ни БД, ни ключей.

| Файл | Что проверяет |
|---|---|
| `tests/test_support_ai_gate.py` | `decide()`: полная матрица п.3.2 (off/shadow/suggest/auto, пауза, human-hold, handoff, пустой reply, require_kb on/off × профиль, confidence, sensitive, тон, окно, лимит/час, clarifying-повтор). `confidence_level` от порога и `CHECK_BAND`. |
| `tests/test_support_ai_scrub.py` | `scrub`: URL/UUID/IP/карта/телефон/tg-id/token → `[скрыто]`. `outbound`: IP, домен вне allowlist, `vless://`, CJK, мета-слова → `ok=False`; allowlist-домен → `ok=True`; допустимый текст не ломается. |
| `tests/test_support_ai_parse.py` | `repair`: обрезанный JSON, ```-фенсы, лишний текст до/после, `strip_thinking`, одинарные кавычки; `chunks.splitArticle/selectChunks` бюджет и `maxChunk`; `links.mask/expand`, неизвестный ключ, `MAX_LINKS`. |
| `tests/test_support_import.py` | `tg_text`: два формата дат, продолжения, cp1251, нет заголовков → ошибка, лимиты. `tg_json`: массив `text`, `reply_to`, служебные сообщения, битый JSON. Дедуп-ключ стабилен (порядок/регистр/пробелы). |
| `tests/test_support_kb.py` | `fts`: построение `websearch_to_tsquery`, экранирование кавычек/`|`; endpoints CRUD через фейковый store: publish, `expected_version` → 409 `KB_VERSION_CONFLICT`, DELETE published → 409 `KB_DOC_PUBLISHED`, search отдаёт только `published`. |
| `tests/test_support_ai_endpoints.py` | `assistant/settings` без `api_key`; `PUT /assistant/settings` пишет и перезагружает; pause/resume; `stats` считает по фейковым строкам; `try` не пишет в store (проверка «ни одного вызова записи»); `suggestions/{id}/decide` send/edit/reject + окно закрыто; `messages/{id}/feedback` wrong → кандидат. |
| `tests/test_support_ai_worker.py` | debounce: два события → одна генерация; отмена предыдущей задачи; `direction='out'` → игнор; ответ оператора во время генерации → `suggest` вместо `auto`; `mode=off` → ноль вызовов провайдера. |
| `tests/test_support_settings_keys.py` | новые `support_ai_*` в реестре: уникальность ключей, `is_secret` только у ключа, `env_var` совпадает с `SupportSettings`, старые `support_tg_*`/`support_poll_*` не сломаны после generic-рефактора. |

Фейки: `FakeProvider` (`complete_json` → заданный ответ/ошибку/429), `FakeStore` (dict-реализация нужных методов), подмена `get_support_service` и `get_current_admin` как в `test_support_stage_a.py:1-30`.

Команды:
```powershell
cd web/backend; python -m pytest tests/test_support_ai_gate.py tests/test_support_ai_scrub.py tests/test_support_ai_parse.py tests/test_support_import.py tests/test_support_kb.py tests/test_support_ai_endpoints.py tests/test_support_ai_worker.py tests/test_support_settings_keys.py -q
cd web/backend; python -m pytest tests -q          # регресс (было 391 зелёных)
cd web/frontend; npx tsc --noEmit
```

Смоук (вручную, после B3):
1. `mode=shadow`, входящее в бота → строка в `/support/ai` → активность, в треде карточки нет, клиенту ничего.
2. `mode=suggest` → карточка в треде, «Почему так?» показывает `used[]`, «Отправить» → сообщение у клиента, `status='sent'`.
3. `confidence` ниже порога → кнопка «Отправить» есть, но бейдж «Не уверен», автоответа нет.
4. Пауза 1 ч → новые входящие дают предложку, автоответов нет; после снятия — как было.
5. `mode=auto`, вопрос из опубликованной статьи → автоответ у клиента, `author='bot'`, 13-й за час → снова предложка.
6. Вопрос с «верните деньги» → всегда предложка.
7. Импорт текста 500 сообщений → `qa_pair` + идеи, повторный импорт → `skipped_duplicates=500`.
8. `result.json` из Telegram Desktop на 5 МБ → джоб `done`, прогресс доходит до 100%.

---

## 9. Нарезка на задачи

### B1 — Ядро: конфиг, миграция, провайдер, ворота, воркер

**Порядок:**
1. `db/postgres/migrations/006-support-ai-kb.sql` (по §2) + сдвиг docs-history на 007 в `docs/plans/2026-11-15-changelog-history-editable.md:52,100,116`.
2. `core/support/schema.py` — `_MIGRATION_FILENAMES += ("006-support-ai-kb.sql",)`.
3. `core/settings_registry.py` — 18 ключей (§1.2), группа «ИИ / Саппорт», `SUPPORT_KEYS`.
4. `core/support/settings.py` — `SupportSettings.ai_*`, `SUPPORT_OVERRIDES`, generic-applier.
5. `core/support/ai/{__init__,config,provider,prompt,repair,chunks,links,scrub,outbound,gate,responder,worker}.py`.
6. `core/support/store/ai.py` + методы в `store/__init__.py` (suggestions CRUD, `ai_replies_since`, `last_human_reply_at`, `human_hold_active`, pause через `get_json_setting`, drafts `get/put/delete`).
7. `core/support/events.py` (+`AI_SUGGESTION`), `ws.py` (+кадр), `workers.py` (+`support-ai-worker`), `__init__.py` (+`service.ai`).
8. `api/v1/support/{suggestions,assistant}.py`, `api/v1/support/__init__.py`, `GET /config-status` + поле `ai`, `core/settings_values.upsert_value` + переиспользование в `api/v1/settings.py`.
9. `core/errors.py` — новые коды.
10. `docs/decisions/ADR-007-support-ai-gate-and-fts.md` — 4 решения: FTS на `tsvector` вместо FTS5; порядок гейта и трактовка `require_kb`×профиль; `shadow` как обязательный этап; миграция 006 vs docs-history 007.

**Acceptance:**
- `ensure_support_schema()` на чистой и на уже мигрированной БД проходит дважды без ошибок; `\d support_kb_doc` содержит `status/version`, GIN-индекс существует.
- `GET /assistant/settings` при пустом ключе: `effective_mode='off'`, `has_key=false`, `api_key` отсутствует в JSON.
- `PUT /assistant/settings {mode:'suggest'}` → `on_settings_changed` → без рестарта следующее входящее даёт предложку.
- Гейт-матрица зелёная (`test_support_ai_gate.py`), worker-тесты зелёные.
- Старые тесты саппорта и весь `pytest tests` зелёные.
- В логах нет `api_key`.

**Риск:** средний. Главный источник — generic-рефактор `_apply_registry_overrides` (ломает `tg_*`); страхует `test_support_settings_keys.py` и прогон `test_support_foundation.py`.

### B2 — База знаний, обучение, импорт

**Файлы:** `core/support/store/{kb,qa,jobs,drafts}.py`; `core/support/kb/fts.py`; `core/support/import/{tg_text,tg_json,cluster,runner}.py`; `core/support/ai/examples.py`; `api/v1/support/{kb,imports,feedback}.py`; `api/v1/support/__init__.py`.

**Порядок:** `kb/fts.py` → `store/kb.py` → API KB (+кандидаты) → `store/qa.py` + `examples.py` (подключить в `responder.py`) → `import/*` → `store/jobs.py` → API импорта → feedback.

**Acceptance:**
- CRUD/publish/archive/restore/delete по §5.1; `expected_version` реально защищает (два параллельных PUT — второй 409).
- Поиск по-русски: «подключение германия» находит статью с «Германия не подключается»; стоп-слова не мешают.
- `GET /kb` по умолчанию не отдаёт `archived`, `q` фильтрует.
- Импорт текста и `result.json` по §7, прогресс в `support_job` растёт, повторный импорт дедуплицируется на 100%.
- `accept` кандидата создаёт draft-статью и линкуется `doc_id`; опубликованная статья сразу находится поиском.
- `messages/{id}/feedback` пишет `qa_pair`; `wrong` создаёт кандидата.
- Похожие пары операторов попадают в промпт (проверяется в `test_support_ai_worker.py` на фейковом store).

**Риск:** средний. FTS-ранжирование и парсеры Telegram — самые «шумные» места; закрываются юнит-тестами на реальных кусках экспорта до интеграции.

### B3 — Фронтенд

**Файлы:** `web/frontend/src/api/support.ts`; `pages/support/{Kb,Assistant}.tsx`; `pages/support/components/kb/{KbList,KbEditor,CandidateList,ImportPanel}.tsx`; `pages/support/components/assistant/{ModeCard,PauseCard,ParamsCard,StatsCard,TryPanel}.tsx`; `pages/support/components/AiDraftCard.tsx`; `pages/support/components/MessageThread.tsx`; `pages/support/Queue.tsx`; `lib/supportSocket.ts`; `App.tsx` (заменить два `SupportPlaceholder` на `lazy`); при необходимости — список групп в `pages/Settings.tsx`.

**Порядок:** `api/support.ts` → `App.tsx` + `/support/kb` → `/support/ai` → `AiDraftCard` + `MessageThread`/`Queue` + WS.

**Acceptance:**
- `npx tsc --noEmit` чистый; `npm run build` проходит.
- Оба маршрута без `SupportPlaceholder`.
- Конфликт версии статьи показывает диалог, а не молчаливую потерю правок.
- Карточка ИИ: видна только при `gate_action != 'shadow'`; «Править» кладёт текст в композер; «Отклонить» требует причину.
- При `has_key=false` на `/support/ai` — баннер, кнопки включения `suggest/auto` заблокированы с подсказкой.
- WS-кадр `ai_suggestion` обновляет тред без перезагрузки.
- Новые ключи видны в «Настройки → Интеграции → ИИ / Саппорт», секрет маскируется.

**Риск:** низкий-средний. Дизайн-система своя, новых зависимостей нет; риск — только объём и аккуратность с существующими классами.

### B4 — Тесты, документация, приёмка

**Файлы:** 8 тестовых файлов из §8; `docs/CODEBASE_INDEX.md` (§1.26 — новые эндпоинты; §3.16 — новые методы/типы `api/support.ts`; раздел «Support: настройки и runtime» — `ai_*`, `AiRuntime`, `aiPause`; новый раздел «Support: ИИ и КБ» — модули `core/support/ai/*`, `kb/fts.py`, `import/*`; таблицы 006); `docs/CHANGELOG_CMS.md`; `docs/AI-SUPPORT.md` (в §1a — пометка «портировано в CMS: gate/scrub/links/repair/chunks/examples, FTS→tsvector, interface-kb не переносим»); `docs/plans/2026-11-28-support-completion.md` (Этап B — выполнен, список долга обновить); `PROJECT.md` — только если там есть таблица `SUPPORT_*` env.

**Acceptance:**
- Все команды §8 зелёные.
- `CODEBASE_INDEX.md` соответствует фактическим путям/полям (сверка по grep, не по памяти).
- Смоук-лист §8 пройден, результаты — в CHANGELOG/плане.
- Ни одного `TODO` без владельца в новом коде.

**Риск:** низкий. Единственная ловушка — расхождение индекса и кода; закрывается финальным grep-проходом.

---

## 10. Definition of Done (на весь Этап B)

1. Код B1–B4 смёржен, тесты и `tsc` зелёные.
2. `docs/CODEBASE_INDEX.md` отражает: 20+ новых эндпоинтов, Pydantic-модели, поля `support.ts`, методы `supportApi`, таблицы 006, `AiRuntime`, `aiPause`, кадр WS `ai_suggestion`.
3. `docs/CHANGELOG_CMS.md` — запись «Саппорт: Этап B — ИИ-ассистент (off/shadow/suggest/auto), база знаний с русским FTS, обучение на ответах, импорт Telegram».
4. `docs/decisions/ADR-007-support-ai-gate-and-fts.md` создан.
5. Новые env (`SUPPORT_AI_*`) отражены там, где проект ведёт реестр env.
6. `docs/plans/2026-11-15-changelog-history-editable.md` — миграция docs-history переномерована на 007.
7. Этап C (SLA/шаблоны/присутствие) не затронут: `support_operator_draft` создана, но UI черновиков и presence — не в B.

---

## 11. Открытые вопросы

Блокирующих B1 нет — все девять решений из постановки зафиксированы выше. Ниже — то, что можно решить по ходу, с дефолтом «если не решено, делаем так»:

1. **Порог по умолчанию `min_confidence`.** Принято `0.90` (как в v3.0.0). Если на смоуке окажется, что предложек слишком мало, снижаем до `0.80` через настройки, без миграции.
2. **Список операторских имён для импорта текста.** Дефолт: `Поддержка HexaVeil, Поддержка, Support, HexaVeil, Администратор`. Если в реальных выгрузках имя иное — задаётся в `payload.operator_names`, править код не нужно.
3. **`support_ai_proxy`.** В B1 не реализуем (прямое соединение). Если провайдер недоступен с сервера — добавляем ключ и `outbound_proxy.resolve_proxy(session, "support")` в тот же провайдер, миграция не нужна.
4. **Автообучение на ответах оператора (`sync_examples`).** В B2 пишем `qa_pair` только по фидбеку и импорту. Автоматический сбор всех исходящих ответов операторов — сознательно не включаем (шум, дубли, утечки в примерах). Кандидаты из «мины» диалогов — Этап C.
5. **Кто пишет в `support_kb_doc.updated_by`.** `AdminUser.id` (`api/deps.py`); отдельной таблицы операторов нет — это согласуется с решением «все админы = операторы» (`2026-11-28-support-completion.md:175`).
