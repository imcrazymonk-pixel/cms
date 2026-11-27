# TASK — Статусы интеграций расходятся с проверками (Bedolaga / Bot DB)

> Статус: **план, к реализации**
> Дата: 2026-11-21
> Роль: архитектор/планировщик
> Предыдущий план сохранён: `docs/plans/2026-11-21-settings-integrations-visible.md`

---

## 1. Жалоба

> «Интеграции подключены, но при старте проекта пишется, что Bedolaga не подключён, БД не подключено, хотя в Интеграциях проверки проходятся».

## 2. Диагноз

Два независимых пути к конфигу:

- «Проверить» → `settingsApi.testIntegration` → `core/integrations.py::_test_bedolaga/_test_bot_db` читает **реестр настроек из БД** (`effective(db, ...)`) — поэтому проходит.
- Статусы/лог/аналитика → **ENV-снимок** (`get_cms_settings()`) и **in-memory состояние** (`bedolaga_client`, `bot_db._config`), которое заполняется один раз в `lifespan` через `integrations.bootstrap`; ошибки bootstrap глушатся и не ретраятся.

| # | Файл:строка | Дефект |
|---|---|---|
| D1 | `web/backend/main.py:33, 71-75, 94-107` | Стартовый лог `bedolaga=…, bot_db=…` берётся из ENV, результат bootstrap не используется. |
| D2 | `web/backend/core/integrations.py:859-871` | `bootstrap()` глушит ошибки в `result["error"]`, ретрая нет. |
| D3 | `web/backend/core/bedolaga_client.py:389-403` | `ensure_configured()` синхронный, при неконфигурированном клиенте читает только ENV. |
| D4 | `web/backend/api/v1/bedolaga/dashboard.py:123-126` | `/bedolaga/status` → `ensure_configured()` (ENV). |
| D5 | `web/backend/api/v1/bedolaga/__init__.py:16-28` | Гейт 503 для всех `/api/bedolaga/*` по ENV. |
| D6 | `web/backend/core/bot_db.py:106-154, 239-292` | `_config` только из `refresh_config()`; иначе ENV; `refresh_config()` не сбрасывает `_circuit_until`. |
| D7 | `web/backend/core/bedolaga_analytics.py:1038, 1086-1094, 1166-1214` | Аналитика использует `bot_db.get_tariffs_result()`; snapshot-кэш не инвалидируется в проде. |
| D8 | `web/backend/api/v1/settings.py:337-383` | Успешный тест не применяет bot_db-конфиг, не сбрасывает circuit/error-кэш. |
| D9 | `web/frontend/src/pages/Settings.tsx:456-489, 529-546, 612-627` | Нет инвалидации `['bedolaga-status']`, `['bedolaga-overview']` после сохранения/теста. |
| D10 | `web/frontend/src/locales/{ru,en}/translation.json:3960-3961, 4258-4259` | Текст просит ENV вместо «Настройки → Интеграции». |

`@lru_cache` в `get_cms_settings()` — **не корневая причина**; реестр читается через `settings_values` напрямую.

## 3. Границы

- Не менять маршруты и публичные схемы; меняется только семантика `configured`.
- Не менять жизненный цикл httpx-клиента (`aclose` в `configure()` не добавлять).
- Не трогать прод и серверы.

## 4. План правок

### Шаг 1 — Стартовый лог (D1)

`web/backend/main.py` → `lifespan`:

- `integration_status: dict = {}`; в `try` — `integration_status = await bootstrap_integrations(app)`; в `except` — `{"error": type(e).__name__}`.
- Итоговый `logger.info`: `bedolaga` по `bedolaga_client.is_configured` / `bedolaga_client.disabled`; `bot_db` по новому `bot_db.is_configured()`; в конец — `bootstrap=%s`.
- Импорты: `bedolaga_client`, `is_configured as bot_db_configured` (рядом с `close_engine`).
- `settings` оставить только для host/port/DB.

### Шаг 2 — Async-гейт Bedolaga из реестра (D2-D5)

`web/backend/core/bedolaga_client.py`:

- `async def ensure_configured_async(db: Any = None) -> bool`:
  1. `disabled` → `False` (hard-off приоритетнее);
  2. `is_configured` → `True`;
  3. модульный `asyncio.Lock` (ленивое создание) + double-check;
  4. `db` есть → `await apply_bedolaga(db)`; иначе сессия через `get_session_factory`;
  5. ленивый импорт `apply_bedolaga` внутри функции;
  6. при ошибке чтения реестра — warning + fallback на sync `ensure_configured()`.
- Sync `ensure_configured()` не менять по логике; обновить docstring — ENV-only fallback.

`web/backend/api/v1/bedolaga/__init__.py`:

- `async def is_configured() -> bool` → `await _configure_client_async()`;
- `async def ensure_configured() -> None` — прежний 503 с текстом «Bedolaga API не настроена: укажите URL и Web API token в Настройки → Интеграции».

Обязательно обновить вызовы:

- `api/v1/bedolaga/analytics.py:55` → `await ensure_configured()`;
- `api/v1/bedolaga/customers.py:407` → `await ensure_configured()`;
- `api/v1/bedolaga/dashboard.py:13, 123-126` → `await is_configured()`;
- `core/support/__init__.py:67-81` → `await ensure_configured_async()`;
- `core/support/integrations/bedolaga_customer.py:81-96` → `_bedolaga_client` сделать async, вызов `await`.

### Шаг 3 — Ленивый конфиг bot_db и сброс circuit (D6)

`web/backend/core/bot_db.py`:

- state: `_config_checked_at`, `_CONFIG_RETRY_TTL = 60.0`, `_config_lock`;
- `def is_configured() -> bool`;
- `async def ensure_config() -> bool`: fast path → negative TTL → lock/double-check → сессия `get_session_factory` → `await asyncio.wait_for(refresh_config(session), 3.0)`; ошибки — warning, `False`; `finally` — обновить `_config_checked_at`;
- `refresh_config()`: сбрасывать `_circuit_until = 0.0` (глобально), сохранив `clear_cache()`;
- `get_tariffs_result()`: если `_config is None` — `await ensure_config()` до `_get_engine()`; `env_config()` оставить fallback.

### Шаг 4 — Инвалидация аналитики (D7, D8)

`web/backend/core/integrations.py`:

- helper `_invalidate_analytics_snapshot()` — ленивый импорт `bedolaga_analytics.invalidate_snapshot_cache()`, ошибки глушить;
- вызывать в `on_settings_changed()` после веток Bedolaga/Bot DB и в `bootstrap()`.

`web/backend/api/v1/settings.py` → `test_integration`:

- при `ok` и `integration_id in ("bedolaga", "bot_db")`: инвалидировать snapshot;
- для `bot_db` — `await bot_db.refresh_config(db)`;
- всё в `try/except` + warning.

### Шаг 5 — Фронт (D9)

`web/frontend/src/pages/Settings.tsx`:

- `useQueryClient`; helper `invalidateBedolagaRuntime()` для `['bedolaga-status']`, `['bedolaga-overview']`, `['bedolaga-full']`, `['bedolaga-health']`, `['bedolaga-analytics-overview'|'forecast'|'tariffs']`;
- вызывать в `onSave`, `onReset`, `saveAll` (если среди изменённых ключей есть префиксы `bedolaga_`/`bot_db_`/`outbound_proxy_`) и в `runTest` при `ok`.

### Шаг 6 — Тексты (D10)

- `locales/ru/translation.json:3961, 4259` и `locales/en/...` — заменить ENV-инструкции на «Настройки → Интеграции»;
- `api/v1/bedolaga/__init__.py:24-25` — убрать «Set BEDOLAGA_API_URL…»;
- `core/bot_db.py:288` — убрать «или BOT_DB_HOST в окружении».

### Не делать

- Не менять `get_cms_settings()`/`lru_cache`.
- Не добавлять sleep/ретраи в `lifespan`.
- Не прокидывать `Depends(get_db)` во все эндпоинты.
- Не менять `staleTime` в `BedolagaDashboard`.

## 5. Проверка

Backend (`web/backend`):

- `python -m pytest tests -q`; прицельно `test_bedolaga_disabled.py`, `test_integrations.py`, `test_integration_endpoints.py`, `test_settings_runtime.py`, `test_bedolaga_analytics.py`, `test_bedolaga_analytics_api.py`, `test_support_bedolaga.py`.
- Добавить/обновить тесты:
  - `/status` = `true` при ENV пустом и заполненном реестре; `bedolaga_enabled=0` → `false`;
  - `/api/bedolaga/overview` не 503 при настроенном реестре (мок клиента);
  - `bot_db.ensure_config()` при `_config=None`;
  - `refresh_config()` сбрасывает `_circuit_until`;
  - успешный тест `bot_db` инвалидирует snapshot и применяет конфиг;
  - поправить `test_bedolaga_analytics_api.py:114-120` под async-резолвер.
- `rg "ensure_configured\(" web/backend` — только определения, `await`-вызовы и fallback.

Frontend (`web/frontend`): `npm run typecheck`, `npm run build`; `lint` не настроен (pre-existing).

Ручные шаги:

1. Очистить ENV (`BEDOLAGA_*`, `BOT_DB_*`), настроить в UI, перезапустить backend → лог `bedolaga=настроен`, `bot_db=настроен`, `bootstrap={…applied…}`.
2. `/api/bedolaga/status` → `true`, `/api/bedolaga/overview` → 200.
3. Остановить CMS-БД на старте, поднять API, поднять БД → без рестарта API статусы восстанавливаются.
4. Сохранить/проверить интеграцию → `/bedolaga` не показывает «не настроен» и warning `bot_db_disabled` исчезает.

## 6. Документация (DoD)

`docs/CODEBASE_INDEX.md`:

- стр. ~236 — `GET /api/bedolaga/status`: `configured` учитывает реестр, ENV-fallback, hard-off приоритетнее;
- стр. ~138-145 — тест интеграций: инвалидация snapshot, `refresh_config` для `bot_db`;
- стр. ~384-386 — инвалидация снимка аналитики при сохранении/тесте;
- стр. ~527-545 — `bot_db`: `is_configured()`, `ensure_config()`, сброс circuit;
- стр. ~625-631 — `bedolaga_client`: `ensure_configured_async`, sync — ENV-only fallback;
- стр. ~734-738 — `integrations`: применение настроек инвалидирует snapshot;
- стр. ~1372-1380 — Settings: инвалидация react-query после сохранения/теста.

`PROJECT.md` — без изменений.

## 7. Риски

1. Лишние чтения CMS-БД на request-пути → fast path + lock + negative TTL.
2. Гонка `configure()`/`reset()` с in-flight запросами — lock, без `aclose` в `configure()`.
3. Пропущенный `await` → `RuntimeWarning` и отсутствие гейта; обязателен grep.
4. `apply_bedolaga` при пустых значениях делает `reset()` — early-return на `disabled`.
5. Ложное «настроен»: в логе писать «настроен», не «работает».
6. JSON-локали — проверять build.
