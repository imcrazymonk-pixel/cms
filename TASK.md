# TASK — Round 3: пустая вкладка «Интеграции» из Саппорта и запуск Telegram-бота

> Статус: **план, к реализации**
> Дата: 2026-11-21
> Предыдущий план: `docs/plans/2026-11-21-round2-status-robustness.md`

---

## 1. Жалобы

**A.** «Когда я в Саппорте перехожу в настройки, ничего не отображается в меню Интеграции».

**B.** «Вбил настройку токена, но когда в боте написал старт, ничего не произошло. Надо ли добавить канал этого бота? Что нужно сделать, чтобы его запустить?»

## 2. Диагноз

### A. Пустая вкладка

Пункт «Саппорт → Настройки» ведёт на `/settings?tab=integrations&from=support` (`navigation.ts:102`), отдельной страницы настроек Саппорта нет. Вкладка пуста визуально, если:

1. **Backend вернул пустой реестр интеграций.** В `HEAD` нет ни одного `SettingDef` с `tab="integrations"` — ключи `support_*`/`bedolaga_*`/`bot_db_*` есть только в рабочем дереве. Если фронт новый, а backend старый/не перезапущен → `byTab.integrations` пуст → только SearchBar (`Settings.tsx:877-886`). **Основная причина.**
2. **`from` не сопоставился категории** → `focusCategory=''`, `fromParam` truthy → `defaultOpen=false` у всех блоков (`Settings.tsx:681`): видны только свёрнутые заголовки.
3. **Остался поисковый запрос** с прошлого визита: `search` не сбрасывается при смене `from` → `filtered.length===0` → `return null` для всех категорий (`Settings.tsx:672`).
4. `GET /api/settings` вернул ошибку → вкладок нет вообще (`Settings.tsx:787-789`).
5. Устаревший frontend-bundle.

Категории посимвольно совпадают (`Telegram / Саппорт` и др.), рассинхрона строк нет.

### B. Бот не реагирует на `/start`

Главная причина: `/start` **намеренно игнорируется** — `_PRIVATE_SKIP_COMMANDS = {"/start", "/myid"}` (`tg/poller.py:33`), `_handle_private` при этом возвращает 0 (`:196-197`). Ни диалога, ни приветствия, ни события. Обычный текст создаёт диалог, но автоответа тоже нет — отвечает оператор.

Дополнительно:
- канал поднимается только при токене и `support_tg_enabled != off` (`support/__init__.py:84-89,136-148`);
- `auto` не перетирает legacy `support_setting.tg.main.enabled=0` (`support/settings.py:132-137`);
- при 409 (второй бот/webhook на том же токене) поллер спит 300 с, `last_error="conflict"`;
- **статус поллера нигде в UI не виден**: `supportApi.getPollers()` объявлен, но не используется (`api/support.ts:189`, `pages/support/Queue.tsx`); `/api/support/config-status` не содержит состояния поллера;
- Telegram-канал/группа **не нужны** для лички; `support_tg_staff_group_id` + `support_tg_forum` — только для операторских тем форума. «Канал» в UI — это флаг `auto|on|off`.

## 3. Границы

- Не менять маршруты и формы существующих ответов; только добавлять поля/сообщения.
- Не добавлять webhook-режим.
- Не менять поведение Bedolaga-канала.
- Прод не трогать.

## 4. План правок

### A1 — вкладка «Интеграции» не бывает пустой

`web/frontend/src/pages/Settings.tsx`:

1. `renderIntegrationCategory`: `defaultOpen={!!q || !focusCategory || focusCategory === category || !fromParam}` — если `from` не сопоставлен, раскрывать всё, а не сворачивать.
2. Сбрасывать `search` при изменении `from`:
   `useEffect(() => { setSearch('') }, [fromParam])`.
3. В `TabsContent value="integrations"` при `Object.keys(byTab.integrations || {}).length === 0` рендерить заметную карточку-объяснение вместо пустоты:
   - заголовок «Настройки интеграций недоступны»;
   - текст: backend не вернул ни одной категории интеграций; проверьте, что API перезапущен с актуальным реестром настроек и что `GET /api/settings` отвечает `items` с `tab="integrations"`;
   - кнопка «Повторить» → `load()`.
   Использовать `EmptyState` (как в `pages/support/Placeholder.tsx`) либо `Card`/`Button` из UI-кита.

### B1 — `/start` и `/myid` в личке

`web/backend/core/support/tg/poller.py`:

1. Убрать `"/start"` и `"/myid"` из «молчаливого» skip; оставить константу пустой/удалить.
2. В `_handle_private` до обычной обработки:
   - `token == "/start"`:
     - `record_inbound(...)` с текстом `/start` (создаёт диалог, чтобы оператор видел обращение);
     - если `message_created`: publish `MESSAGE_CREATED`, `ensure_topic` (если bridge), затем `await self.client.send_message(chat_id, GREETING)`;
     - `record_outbound(conversation_id=..., text_value=GREETING, author="bot", external_msg_id=<id из ответа>)`;
     - ошибку отправки логировать warning, но не ронять тик.
   - `token == "/myid"`: ответить `Ваш Telegram ID: <id>` и **не** создавать диалог.
3. `GREETING` — константа: «Здравствуйте! Опишите ваш вопрос одним сообщением — оператор ответит здесь.»
4. Если диалог уже существует и `/start` прислан повторно — `record_inbound` вернёт `message_created=true` для нового сообщения; приветствие отправить один раз за сообщение, без спама.

### B2 — видимый статус поллера

`web/frontend/src/pages/support/Queue.tsx`:

- добавить `useQuery({ queryKey: ['support-pollers'], queryFn: supportApi.getPollers, refetchInterval: 30_000, refetchOnWindowFocus: true })`;
- над очередью — компактная панель:
  - `telegram`: `enabled`, `running`, `last_poll`, `last_error`;
  - `bedolaga`: то же;
- если `last_error === 'conflict'` — явный текст «Тот же токен опрашивает другой бот/webhook: остановите второй поллер или используйте отдельный токен»;
- если поллера `telegram` нет — «Telegram-канал не запущен: проверьте токен и `support_tg_enabled` в Настройки → Интеграции»;
- остальное — нейтральный бейдж.

`web/frontend/src/api/support.ts`: типизировать ответ `getPollers` (`{ pollers: Record<string, PollerStatus> }`), без `any`.

### B3 — тест интеграции support информативнее

`web/backend/core/integrations.py` → `_test_support`:

- после успешного `getMe` добавить в сообщение `@username` и предупреждение, если канал не запущен/`last_error` (если доступен runtime) — не обязательно, но желательно;
- минимально: включить `bot_username` в ответ, чтобы UI показывал, какой бот проверен.

### Тесты

- `/start` создаёт диалог, отправляет приветствие и пишет outbound (mock client/store);
- `/myid` отвечает и не создаёт диалог;
- повторный `/start` не дублирует приветствие при `message_created=false`;
- Settings: пустой `byTab.integrations` → empty-state (если есть frontend-тесты — иначе ручная проверка);
- Queue: `last_error='conflict'` → предупреждение (ручная проверка).

## 5. Что НЕ нужно пользователю (ответ на вопрос)

- **Telegram-канал добавлять не нужно.** Модуль работает с личными сообщениями; канал/группа не используется.
- **Staff group + темы форума** нужны только для ответов операторов из Telegram; для лички и веб-очереди не обязательны.
- Для запуска достаточно: валидный токен в «Настройки → Интеграции → Telegram / Саппорт», `support_tg_enabled = auto|on`, поллер `telegram` в `/api/support/pollers` с `running=true`, отсутствие 409, и сообщение **обычным текстом** (после правки — и `/start`).
- На одном токене с прод-ботом CMS работать не может: нужен отдельный бот или выключенный Telegram-канал CMS.

## 6. Проверка

- `python -m pytest tests -q` в `web/backend`.
- `npm run typecheck`, `npm run build` в `web/frontend`.
- Ручные шаги:
  1. «Саппорт → Настройки» → вкладка «Интеграции» показывает блоки; при старом backend — понятное объяснение, а не пустота.
  2. Написать боту `/start` → в очереди появляется диалог, в Telegram приходит приветствие.
  3. Написать обычный текст → диалог появляется (как раньше).
  4. `/myid` → приходит ID, диалог не создаётся.
  5. Панель статуса на «Очереди» показывает `telegram` и `bedolaga`; при двух ботах на одном токене — предупреждение `conflict`.

## 7. Документация (DoD)

`docs/CODEBASE_INDEX.md`:

- `tg/poller`: обработка `/start` и `/myid`, приветствие, `record_outbound`;
- `Settings.tsx`: fallback `defaultOpen`, сброс поиска, empty-state вкладки «Интеграции»;
- `pages/support/Queue.tsx`: панель статуса поллеров;
- `api/support.ts`: тип `PollerStatus` и `getPollers`;
- `integrations._test_support`: `bot_username` в ответе.

`PROJECT.md` — без изменений.

## 8. Риски

1. Автоответ на `/start` может дублироваться, если `record_inbound` вернёт `message_created=true` при повторной доставке — проверять `message_created` и `external_msg_id`.
2. Прямой `send_message` в обход Outbox не учитывает окно ответа — для приветствия это допустимо (ответ на входящее сообщение).
3. Панель статуса добавляет запрос раз в 30 с — приемлемо.
4. Empty-state не должен показываться при загрузке (`isPending`) и при ошибке API (там уже `QueryError`).
