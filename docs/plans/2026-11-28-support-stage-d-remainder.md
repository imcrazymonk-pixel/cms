# Этап D — остаток: медиа-лимиты, вкладка, активация бота, история

**Статус:** D-1, D-2, D-4a и D-4b выполнены 2026-11-28; D-3/D-5 (прод) и D-4c (тела истории) ждут подтверждения владельца.
**База:** коммит `ae1900e`; после реализации — `pytest` 754 passed, `tsc` 0, `build` ок.
**Связанные документы:** `TASK.md`, `docs/plans/2026-11-28-support-completion.md` (§5), `docs/plans/2026-11-28-support-bot-activation-and-history.md`, `docs/CODEBASE_INDEX.md`.

## 0. Порядок и границы

Порядок строго такой:

1. **D-1. Медиа-лимиты из настроек** — код + тесты.
2. **D-2. Вкладка «Поддержка» в настройках** — код + тесты.
3. **D-3. Активация CMS-бота / cutover (D1 плана активации)** — прод-операция, только с явным подтверждением владельца; код не меняется.
4. **D-4. История (D3 плана активации)** — mapping-only по умолчанию + `is_backfill`; тела — отдельное решение владельца.
5. **D-5. Пост-смоук: остановка `vpn_support_bot`** — отдельный чек-лист после успешного D-3, не раньше.

Границы: не трогаем `remnawave_bot`, панель Remnawave, `ai-support` (в проде его нет). Новых npm/pip-зависимостей нет. Прод-конфиги руками не правим. Живые серверы — только чтение, кроме шагов D-3/D-5, на которые нужно отдельное подтверждение владельца.

---

## 1. D-1. Медиа-лимиты из настроек

### 1.1. Цель

Один лимит размера файла для всех путей саппорта задаётся в настройках CMS, а не тремя разными константами. Сейчас:

| Место | Факт |
|---|---|
| `web/backend/api/v1/support/attachments.py:35` | `DEFAULT_MAX_UPLOAD_SIZE = 8 * 1024 * 1024` |
| `web/backend/api/v1/support/attachments.py:137-141` | `service.upload_max_size or DEFAULT_MAX_UPLOAD_SIZE` → 413 `FILE_TOO_LARGE` |
| `web/backend/core/support/__init__.py:53` | `SupportService.upload_max_size: int \| None = None` — нигде не заполняется |
| `web/backend/core/support/__init__.py:159,177,199` | poller/forum получают `service.upload_max_size or MAX_UPLOAD_SIZE` |
| `web/backend/core/support/tg/media.py:23` | `MAX_UPLOAD_SIZE = 8 * 1024 * 1024` |
| `web/backend/main.py:242`, `core/config.py:104` | глобальный middleware `Content-Length` ≤ 64 МБ |
| `.docker/nginx/default.conf:33` | `client_max_body_size 64M` |

### 1.2. Контракт настройки

Новый ключ в `web/backend/core/settings_registry.py` рядом с остальными `support_tg_*`:

```python
SettingDef(
    "support_media_max_mb", "Лимит файла, МБ", "Telegram / Саппорт",
    tab="support",                    # появится в D-2; до неё можно "integrations"
    type="number", default="8", env_var="SUPPORT_MEDIA_MAX_MB",
    description="Максимальный размер файла в чате: 1–50 МБ. Жёсткий потолок сервера — 64 МБ.",
    sort_order=70,
)
```

- Дефолт `8` (совпадает с прод-поведением и лимитом Bot API на фото).
- Диапазон `1..50`: нижняя граница — защита от нуля; верхняя — 50 МБ (документы Bot API), при этом middleware/nginx пропускают до 64 МБ.
- `SupportSettings` (`web/backend/core/support/settings.py:31-81`): `media_max_mb: int = Field(default=8, ge=1, le=50, ...)`.
- `SUPPORT_OVERRIDES` (`settings.py:88-118`): `"support_media_max_mb": ("field", "media_max_mb")`.
- Hot reload (`web/backend/core/integrations.py:764-781`): добавить ключ в `SUPPORT_TRIGGER_KEYS`. Полный `reload_support` пересобирает poller/forum с новым лимитом; это безопасно, но кратко перезапускает long-poll — приемлемо для смены лимита.
- `SUPPORT_KEYS` (`settings_registry.py:623-654`) — добавить ключ для консистентности прокси-проверки интеграции.

### 1.3. Проброс в рантайм

В `web/backend/core/support/__init__.py:258-318` (`init_support`), **после** выбора `settings` и **до** `_wire_telegram`:

```python
service.upload_max_size = settings.media_max_mb * 1024 * 1024
```

Ставить в обеих ветках (новый сервис и `existing`) или один раз после блока `if existing ... else ...`. Тогда существующие чтения `service.upload_max_size or MAX_UPLOAD_SIZE` (`:177`, `:199`) и `attachments.py:137` автоматически получают значение настройки; сигнатуры `TelegramPoller`, `ForumBridge`, `fetch_and_store_media` менять не нужно.

Поведение путей:

- **Web-загрузка** — 413 `FILE_TOO_LARGE` при превышении настройки;
- **Входящее из Telegram** — `tg/media.py` тихо пропускает файл больше лимита (warning), это оставляем: отправителю Bot API всё равно не даст скачать файл >20 МБ;
- **Исходящее в Telegram** — документы Bot API до 50 МБ, фото до 10 МБ; при лимите >10 МБ фото может быть отклонено Telegram — отразить в подсказке UI;
- **Глобальный middleware 64 МБ и nginx 64M** остаются верхним потолком; менять `.docker/nginx/default.conf` не требуется.

### 1.4. API и UI

- `web/backend/api/v1/support/status.py:79-96` — в `config-status` добавить `"media_max_mb"` (и при желании `"upload_max_bytes"`), читая через `_registry_int(stored, "support_media_max_mb", settings.media_max_mb)`, с клампом `1..50`.
- `web/frontend/src/api/support.ts:119-123` — в `SupportConfigStatus` добавить `media_max_mb: number`. Заодно отметить долг: тип не описывает `ai`, который бэкенд уже отдаёт; добавить `ai?: {...}` или оставить как есть — не блокер.
- `web/frontend/src/pages/support/Queue.tsx` уже запрашивает `getConfigStatus` для панели поллеров (Этап A). Прокинуть `mediaMaxMb` в `MessageThread`/композер; если пропса нет — один `getConfigStatus` на страницу, без нового эндпоинта.
- `web/frontend/src/pages/support/components/MessageThread.tsx:349-370,574-580` — рядом с кнопкой «Файл» подпись «до N МБ»; перед `uploadAttachment` клиентская проверка `file.size > mediaMaxMb * 1024 * 1024` с понятным тостом. Серверная проверка остаётся источником истины.

### 1.5. Тесты

- `web/backend/tests/test_support_settings_keys.py` — регистрация ключа, `env_var`, `tab`, дефолт; `support_media_max_mb=0` и `51` отвергаются pydantic, `1` и `50` проходят.
- `web/backend/tests/test_round2_status.py` — `config-status` отдаёт `media_max_mb` из реестра и фолбэк из env.
- `web/backend/tests/test_support_stage_a.py` — 413 `FILE_TOO_LARGE` при `service.upload_max_size = 1 МБ` (обновить/дополнить существующий кейс).
- `web/backend/tests/test_support_tg_endpoints.py` (или профильный тест медиа) — входящий файл больше лимита не сохраняется, warning без падения.
- Фронт-тестов в проекте нет — проверка `tsc` + `build` + ручной прогон.

### 1.6. Риски и откат

- Риск: смена лимита перезапускает поллер (hot reload) — несколько секунд без приёма сообщений. Откат: вернуть `support_media_max_mb=8`.
- Риск: лимит >20 МБ не влияет на входящие Telegram — это ограничение Bot API, не баг.
- Риск: лимит >10 МБ ломает отправку фото — подсказка в UI + дефолт 8.

**Оценка:** 3–4 ч.

---

## 2. D-2. Вкладка «Поддержка» в настройках

### 2.1. Цель

Все ключи саппорта — в отдельной вкладке «Поддержка», а не внутри «Интеграций». Миграция БД не нужна: `tab` — это метаданные реестра.

### 2.2. Бэкенд

`web/backend/core/settings_registry.py`:

- строки `:255-336` — все `support_tg_*`, `support_poll_interval_seconds`, `support_window_hours`, `support_bedolaga_enabled`, `support_proxy_*`: `tab="integrations"` → `tab="support"`;
- строки `:338-444` — все 18 `support_ai_*`: `tab="integrations"` → `tab="support"`;
- новый `support_media_max_mb` сразу с `tab="support"`;
- категории оставить прежними («Telegram / Саппорт», «ИИ / Саппорт»), чтобы не плодить сущности.

### 2.3. Фронтенд

`web/frontend/src/pages/Settings.tsx`:

- `:811-817` — добавить `<TabsTrigger value="support">Поддержка</TabsTrigger>` (между «Финансы» и «Интеграции»).
- Добавить `TabsContent value="support"` по образцу `integrations`: `SearchBar` + рендер `byTab.support` (`byTab` уже строится из `it.tab`, `:476-484`).
- `:217-225` `FROM_TO_CATEGORY` (`support`, `support_ai`) — deep-link из сайдбара должен открывать вкладку `support`, а не `integrations`; проверить место, где по `from` выбирается вкладка и якорь (`:227-236`), и переключить на `support`.
- `:207-214` `INTEGRATION_TEST_IDS` — долг №7: у категории «ИИ / Саппорт» тест-эндпоинта нет. Решение: не добавлять фиктивный id; кнопка «Проверить» для этой категории просто не рендерится. Зафиксировать это в TASK.md как «закрыто by design», а не как баг.
- `isIntegrationKey` (`:239-244`) уже покрывает `support_*` — смена вкладки не влияет на инвалидацию кэша.

### 2.4. Тесты

- `web/backend/tests/test_support_settings_keys.py` — все `support_*` и `support_ai_*` имеют `tab == "support"`.
- `web/backend/tests/test_support_ai_settings.py` (или где проверяется общая группа/вкладка ИИ) — обновить ожидаемый `tab`.
- `tsc --noEmit` + `npm run build`.

### 2.5. Риски и откат

- Риск: deep-link `?from=support_ai` перестанет находить категорию — покрыть ручной проверкой и, при необходимости, оставить редирект на вкладку `support`.
- Откат: вернуть `tab="integrations"` и убрать `TabsTrigger`/`TabsContent`.

**Оценка:** 2–3 ч.

---

## 3. D-3. Активация CMS-бота и cutover (D1)

Прод-операция. **Требует явного подтверждения владельца.** Код в репозитории не меняется; на сервере — только действия из чек-листа.

### 3.1. Ключи (Настройки → Поддержка / до D-2 — Интеграции)

| Ключ | Значение |
|---|---|
| `support_tg_enabled` | сначала `off` |
| `support_tg_token` | тот же токен, что у `vpn_support_bot` |
| `support_tg_bot_name` | короткое имя бота без `@` |
| `support_tg_staff_group_id` | тот же отрицательный id staff-группы |
| `support_tg_forum` | `on` |
| `support_tg_archive_days` | `7` |
| `support_poll_interval_seconds` | как у прода (по умолчанию из env) |
| `support_window_hours` | `24` |
| `support_tg_greeting` | шапка «Добро пожаловать…» + `HELP_TEXT` прод-бота |
| `support_media_max_mb` | `8` (или согласованное значение) |

### 3.2. Порядок

1. Заполнить ключи, `support_tg_enabled=off`.
2. Бэкап `/opt/support-bot/.env` и `/opt/support-bot/data/topics.json`.
3. Остановить старый поллер: `docker update --restart=no vpn_support_bot` + `docker compose stop` (иначе второй `getUpdates` получит 409).
4. `support_tg_enabled=on` → hot reload поднимает поллер.
5. Смоук:
   - `/start` → пришёл текст из `support_tg_greeting`;
   - сообщение клиента → появилось в очереди CMS **и** в теме staff-группы;
   - ответ из веба → пришёл клиенту в личку;
   - ответ в теме → появился в вебе;
   - `/myid` → вернул ID;
   - «Решено» → тема закрыта/архивирована.
6. Проверить логи: один consumer, нет 409, нет ошибок `getUpdates`.

### 3.3. Откат

1. `support_tg_enabled=off`.
2. `docker update --restart=always vpn_support_bot` + `docker compose up -d`.
3. `topics.json` не трогать; CMS-диалоги, созданные за окно, остаются (не удалять).

**Оценка:** 0,5–1 день оператора (включая окно наблюдения).

---

## 4. D-4. История (D3 плана активации)

### 4.1. D-4a. Mapping-only (дефолт, приватность не нарушается)

Новый CLI `tools/support_import_history.py` (stdlib + уже имеющиеся SQLAlchemy/asyncpg, без новых зависимостей):

- вход: `--topics /opt/support-bot/data/topics.json`, `--dry-run` **по умолчанию**, `--apply` явно;
- для каждой пары `{userId, topicId}`:
  - `store.upsert_conversation(channel="telegram", external_id=str(userId), tg_user_id=userId, source_id=str(topicId), subject=f"Telegram {userId}")`;
  - если диалог уже существует (`ON CONFLICT (channel, external_id) DO NOTHING`, `store/conversations.py:23-58`) — не перезаписывать непустые `source_id`/`tg_user_id`, вывести «exists»;
  - после создания/обновления — `set_status(conversation_id, "closed")`, чтобы старые диалоги не попали в авто-архив и клиенты не получили «диалог закрыт»;
  - тела сообщений **не писать**, `Outbox` не использовать.
- dry-run печатает: `create / exists / conflict`, количество пар, какие `source_id` будут заполнены; `--apply` делает то же в транзакции с коммитом на диалог.
- идемпотентность: повторный запуск не создаёт дублей (`UNIQUE(channel, external_id)`), не меняет `closed` на `open`;
- `banned`, `lastActivity`, `pendingCleanup` из `topics.json` в v1 не импортируются (banned — отдельное решение, см. §8 плана активации).

Тесты: `web/backend/tests/test_support_history.py` — dry-run не пишет, apply создаёт пары, повторный apply — 0 create, существующий `source_id` не перетирается, статус `closed`, `Outbox.send` не вызывается.

### 4.2. D-4b. `is_backfill` в `record_outbound`

`web/backend/core/support/store/conversations.py:159-206`:

```python
async def record_outbound(..., is_backfill: bool = False) -> int:
```

- `INSERT` добавляет колонку `is_backfill` (она уже есть в `004-support-foundation.sql:77`);
- `UPDATE support_conversation`:
  - `first_response_at = CASE WHEN :is_backfill THEN first_response_at ELSE COALESCE(first_response_at, :ts) END`;
  - `last_message_at = GREATEST(last_message_at, :ts)`;
  - `last_inbound_at` не трогается (для outbound и так не трогается);
- все текущие вызовы (`outbox`, ИИ, ответ оператора) продолжают работать с дефолтом `False`;
- тела истории, если владелец разрешит, пишутся через `record_outbound(..., is_backfill=True)` с `external_msg_id='staff:<topicId>:<msgId>'`; дедуп — `message_exists` (unique по outbound `external_msg_id` нет).

Тесты: `test_support_history.py` — при `is_backfill=True` `first_response_at` не выставляется, `last_message_at` не уменьшается, при `False` поведение прежнее.

### 4.3. D-4c. Тела переписки — только по решению владельца

Не делать в этом этапе. Перед включением нужно:

1. явное согласие владельца (обещание «не храним переписку» в `PRIVACY_CLEANUP_MSG`);
2. источник: Telegram Desktop export (JSON, stdlib) — предпочтительно; MTProto (`api_id`/`api_hash`) потребует **новой pip-зависимости**, что запрещено без отдельного разрешения;
3. обновить `PRIVACY_CLEANUP_MSG` или отключить авто-очистку;
4. ADR о retention (дефолт: тела 90 дней, mapping бессрочно);
5. медиа — только метаданные, без скачивания файлов.

**Оценка:** D-4a — 4–6 ч; D-4b — 1–2 ч; D-4c — 1,5–3 дня после решения владельца.

---

## 5. D-5. Пост-смоук: остановка старого `vpn_support_bot`

Выполняется **только после** успешного D-3 и недели наблюдения. Это не `ai-support` (в проде не развёрнут) и не `remnawave_bot`.

1. Убедиться: один consumer токена, нет 409, зеркало в обе стороны работает.
2. Бэкап `/opt/support-bot/data/topics.json` и `/opt/support-bot/.env` вне каталога.
3. `docker update --restart=no vpn_support_bot`; `docker compose stop`.
4. Не удалять `/opt/support-bot` 7 дней; затем архивировать.
5. Откат: `--restart=always` + `docker compose up -d`, CMS-канал `off`.

---

## 6. Чек-лист приёмки

- [x] `support_media_max_mb` виден в настройках, меняется без рестарта, применяется к web-загрузке (413) и к poller/forum.
- [x] `config-status` отдаёт `media_max_mb`; композер показывает «до N МБ» и режет файл на клиенте.
- [x] Все `support_*` и `support_ai_*` — во вкладке «Поддержка»; deep-link из сайдбара открывает её.
- [x] Долг №7 зафиксирован как «by design» (нет тест-эндпоинта ИИ).
- [x] `record_outbound` принимает `is_backfill`, тесты на поведение зелёные.
- [x] `tools/support_import_history.py --dry-run` по умолчанию; `--apply` идемпотентен; повторный запуск — 0 create.
- [x] `pytest` 754 passed, `tsc` 0, `npm run build` — зелёные.
- [x] `docs/CODEBASE_INDEX.md`, `docs/CHANGELOG_CMS.md`, `TASK.md` обновлены.
- [ ] D-3/D-5 (прод) — только с подтверждением владельца; D-4c — только по отдельному решению.

## 7. Что требует подтверждения владельца

| # | Решение | Блокирует |
|---|---|---|
| 1 | Окно cutover D1 (стоп старого бота + включение CMS-канала) | D-3, D-5 |
| 2 | Импортировать ли тела переписки | D-4c |
| 3 | Источник тел: Desktop export или MTProto (+ новая зависимость) | D-4c |
| 4 | Retention тел (дефолт 90 дней) и правка `PRIVACY_CLEANUP_MSG` | D-4c |
| 5 | Перенос `banned`-списка | вне D-4a |

## 8. Оценка

| Блок | Часы |
|---|---|
| D-1 медиа-лимиты | 3–4 |
| D-2 вкладка | 2–3 |
| D-3 активация (оператор) | 4–8 |
| D-4a mapping | 4–6 |
| D-4b `is_backfill` | 1–2 |
| D-4c тела (после решения) | 12–24 |
| D-5 остановка старого бота | 1 + 7 дней наблюдения |

Итого по коду без тел истории: **10–15 ч** (+ прод-окно и неделя наблюдения).
