# TASK — Round 2: остаточные статусы «не подключено» и безопасность двух Telegram-ботов

> Статус: **план, к реализации**
> Дата: 2026-11-21
> Роль: архитектор/планировщик
> Предыдущий план: `docs/plans/2026-11-21-integration-status-registry.md`
> Предыдущий (UI интеграций): `docs/plans/2026-11-21-settings-integrations-visible.md`

---

## 1. Что осталось после первого фикса

Первый фикс сделал `/api/bedolaga/status` и гейт `/api/bedolaga/*` реестро-зависимыми. Остались независимые источники «не подключено»:

| # | Файл | Проблема |
|---|---|---|
| R1 | `web/backend/core/integrations.py:875-888` | `bootstrap()` выполняет Bedolaga и bot_db в одном `try`/сессии: ошибка одной интеграции отменяет вторую. |
| R2 | `web/backend/main.py:100-116` | Стартовый лог читает `bot_db.is_configured()` = `_config or env_config()` — реестр не читается. Если bootstrap не применил bot_db, лог врёт. |
| R3 | `web/backend/core/settings_values.py:28-41` | `stored_merged()` падает, если таблицы `settings`/`fin_settings` нет → bootstrap целиком падает. |
| R4 | `web/backend/api/v1/bedolaga/dashboard.py:22-24` | `_CAPABILITIES_TTL = 600` — статус возможностей 10 минут не обновляется после смены настроек. |
| R5 | `web/backend/api/v1/bedolaga/dashboard.py:129-133` | `/api/bedolaga/tariffs` отдаёт только `items/total`; ошибка bot_db неотличима от пустого каталога. |
| R6 | `web/frontend/src/pages/Settings.tsx:233-246` | `isIntegrationKey` не включает `support_*`; в `BEDOLAGA_QUERY_KEYS` нет `bedolaga-tariffs`, `bedolaga-capabilities`, `bedolaga-maintenance`, `bedolaga-customers`, `support-pollers`, `support-config-status`. |
| R7 | `web/frontend/src/pages/Settings.tsx:639-656` | `runTest()` инвалидирует кэши только при `ok`; при провале старые статусы остаются. |
| R8 | `web/backend/api/v1/support/health.py:7-20` | Всегда `pollers: {}` — реальный статус поллеров не отдаётся. |
| R9 | `web/backend/api/v1/support/status.py:19-29` | `config-status` читает ENV + `support_setting`, игнорируя реестр `support_*`. |
| R10 | `web/backend/core/support/tg/api.py:276-295` | 409 Conflict от Telegram не выделен в отдельный тип. |
| R11 | `web/backend/core/support/tg/poller.py:86-89,132-141` | 409 попадает в generic-обработчик: поллер ретраит каждые 60 с, offset не двигается, сообщения «воюют» с другим ботом. |

## 2. Цели

- Стартовый лог и статусы отражают реестр даже при частично неудачном bootstrap.
- Одна сломанная интеграция не блокирует вторую.
- Ошибка bot_db видна в UI «Тарифы» как «БД недоступна», а не «Нет результатов».
- Фронт инвалидирует все зависимые кэши после сохранения/теста.
- Support отдаёт реальный статус поллеров и читает интервал из реестра.
- Конфликт двух ботов на одном токене определяется явно и не спамит лог каждую минуту.

## 3. План правок

### R1 — изоляция bootstrap

`web/backend/core/integrations.py` → `bootstrap()`:

- для каждой интеграции отдельная сессия и свой `try/except`:
  - `bedolaga` → `apply_bedolaga(session)`;
  - `bot_db` → `_refresh_bot_db(session)`;
- результат: `"applied" | "skipped" | "error"`, при ошибке — `<name>_error = type(exc).__name__`;
- `_invalidate_analytics_snapshot()` вызывать всегда в конце.

### R2 — стартовый лог по реестру

`web/backend/main.py` (перед итоговым `logger.info`):

- `await ensure_configured_async()` (из `core.bedolaga_client`) в `try/except`;
- `await ensure_config()` (из `core.bot_db`) в `try/except`;
- лог оставить по `bedolaga_client.is_configured/disabled` и `bot_db_configured()` — после ensure они отражают реестр;
- `bootstrap=%s` уже есть, сохранить.

### R3 — устойчивость `stored_merged`

`web/backend/core/settings_values.py`:

- обернуть запрос по каждой таблице в `try/except ProgrammingError`;
- продолжать только если ошибка — отсутствие таблицы (`UndefinedTableError` / `does not exist` / `undefined table`);
- логировать warning один раз на таблицу (module-level `set`), трактовать как пустую;
- остальные ошибки пробрасывать.

### R4 — TTL capabilities

`web/backend/api/v1/bedolaga/dashboard.py`:

- `_CAPABILITIES_TTL = 60` (было 600), чтобы статус обновлялся вместе с остальными 60-секундными кэшами.

### R5 — статус в `/tariffs`

`web/backend/api/v1/bedolaga/dashboard.py`:

- импортировать `get_tariffs_result` вместо `get_tariffs`;
- ответ: `{"items": result.get("tariffs") or [], "total": len(items), "status": result["status"], "error": result.get("error")}`.

`web/frontend/src/pages/bedolaga/BedolagaTariffs.tsx`:

- типизировать новый ответ (`TariffsResponse { items, total, status?, error? }`);
- если `status && status !== 'ok'` — показать баннер над таблицей с текстом из локали (`bedolaga.revenue.warnings.bot_db_disabled` или новый ключ), включая `error` при наличии;
- при `status === 'ok'` поведение не меняется.

### R6/R7 — инвалидация на фронте

`web/frontend/src/pages/Settings.tsx`:

- `isIntegrationKey`: добавить `support_`;
- `BEDOLAGA_QUERY_KEYS`: добавить `['bedolaga-tariffs']`, `['bedolaga-capabilities']`, `['bedolaga-maintenance']`, `['bedolaga-customers']`, `['support-pollers']`, `['support-config-status']`;
- `runTest()`: инвалидировать после теста **всегда** (и при `ok`, и при ошибке), для `bedolaga|bot_db|support|global`.

### R8 — реальный support health

`web/backend/api/v1/support/health.py`:

- добавить `Request`, читать `request.app.state.support`;
- `pollers`: `{name: poller.status}` для всех поллеров, иначе `{}`;
- `status` оставить `"ok"`, `db: true` — контракт теста не ломать.

### R9 — support config-status из реестра

`web/backend/api/v1/support/status.py`:

- прочитать `support_poll_interval_seconds`, `support_window_hours` через `settings_values.effective_values(db, [...])`;
- приоритет: реестр → `read_runtime_settings` → `SupportSettings`;
- ответ не менять по форме.

### R10/R11 — 409 Conflict

`web/backend/core/support/tg/api.py`:

- `class TelegramConflict(TelegramAPIError)`;
- в `_raise_or_json`: `response.status_code == 409 or error_code == 409` → `raise TelegramConflict(...)`.

`web/backend/core/support/tg/poller.py`:

- импортировать `TelegramConflict`;
- `tick()`: отдельная ветка `except TelegramConflict: status["last_error"]="conflict"; _publish_status(...); raise` (не глотать);
- `run_loop()`: `except TelegramConflict` → `logger.error("Telegram 409 Conflict: тот же токен уже опрашивает другой процесс/бот. Остановите один из поллеров или используйте отдельный токен.")`; `status["last_error"]="conflict"`; `await asyncio.sleep(300)` (длинный backoff, цикл не умирает);
- остальные ошибки — как сейчас.

### Тесты

- `bootstrap` изолирует ошибки: `apply_bedolaga` кидает, `bot_db` применяется.
- `stored_merged` при отсутствии таблицы возвращает пустой словарь (monkeypatch `execute` → `ProgrammingError`).
- `/api/bedolaga/tariffs` отдаёт `status/error` (mock `get_tariffs_result`).
- `TelegramConflict` на 409 и поллер не двигает offset, ставит `last_error=conflict`.
- `support/health` возвращает реальные поллеры (fake `app.state.support`).
- `support/config-status` берёт интервал из реестра.

## 4. Не делать

- Не менять маршруты и существующие поля ответов; только добавлять `status/error` в `/tariffs` и наполнять `pollers`.
- Не добавлять webhook-режим и не удалять webhook Telegram.
- Не останавливать поллер навсегда при 409 (только длинный backoff).
- Не трогать прод/серверы.

## 5. Проверка

- `python -m pytest tests -q` в `web/backend`.
- `npm run typecheck`, `npm run build` в `web/frontend`.
- Ручные шаги:
  1. Рестарт с пустым ENV, настройки в UI → лог `bedolaga=настроен`, `bot_db=настроен`.
  2. Остановить CMS-БД, рестарт API, поднять БД → без рестарта API статусы восстанавливаются.
  3. `/api/bedolaga/tariffs` при недоступной БД → `status: "disabled|error"`, UI показывает баннер.
  4. Два бота на одном токене → в логе один внятный 409-warning, поллер не спамит каждую минуту.
  5. `/api/support/health` → реальные `pollers`.

## 6. Документация (DoD)

`docs/CODEBASE_INDEX.md`:

- `integrations.bootstrap` — изоляция ошибок;
- `settings_values.stored_merged` — tolerant к отсутствию таблиц;
- `/api/bedolaga/tariffs` — новые поля `status/error`;
- `dashboard` — `_CAPABILITIES_TTL = 60`;
- `support/health` — реальные `pollers`;
- `support/config-status` — реестр;
- `tg/api` — `TelegramConflict`; `tg/poller` — обработка 409;
- `Settings.tsx` — полный список инвалидируемых ключей.

`PROJECT.md` — без изменений.

## 7. Риски

1. Скрытие `ProgrammingError` может замаскировать другую ошибку схемы — фильтровать по признаку отсутствующей таблицы.
2. `ensure_config()` на старте добавляет один запрос к CMS-БД — ограничен `wait_for(3 c)`.
3. Длинный backoff при 409 (300 с) замедлит восстановление, если второй бот убрали — приемлемо, настройки можно пересохранить/перезапустить.
4. Баннер в «Тарифах» должен не ломать пустой каталог (`status=ok, items=[]` → прежнее «Нет результатов»).
