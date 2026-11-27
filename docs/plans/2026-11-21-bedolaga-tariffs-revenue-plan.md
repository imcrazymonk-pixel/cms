# TASK — Тарифы в «Клиентах» Bedolaga и автоматический доход по тарифам

> Статус: **план, к реализации**
> Дата: 2026-11-20
> Роль: архитектор/планировщик
> Предыдущий TASK сохранён: `docs/plans/2026-11-20-bedolaga-subscriptions-count.md`

---

## 0. Краткое резюме

Нужно закрыть три связанные задачи:

1. В разделе **«Клиенты»** Bedolaga показать тариф клиента — колонкой в таблице и строкой в блоке «Информация» карточки клиента.
2. Тариф должен быть **динамическим**: изменился в боте — через обновление данных изменился в CMS. Источник тарифа — `subscription.tariff_id/tariff_name` из Bot Web API, а не локальная копия.
3. В финансах показать **доход по тарифам**: распределение клиентов, MRR при 100% оплате, кассовый прогноз на следующий месяц, начислительный доход, уже оплаченные суммы, оплату вперёд, следующую оплату и динамику. Без ручного ввода.

Главная неопределённость — **цены тарифов**. В Bot Web API каталога цен нет (`GET /tariffs` → 404), а прямой доступ CMS к PostgreSQL бота в проде сейчас не работает. Рекомендуется **гибридный источник (вариант D)**:

1. Ручной override — только как аварийный/точечный инструмент, Этап 2.
2. `tariffs.period_prices` из БД бота — если доступ появится и ответит быстро.
3. **Цены, выведенные из фактических транзакций** `subscription_payment` — основной автоматический источник в MVP.
4. Если цены нет — честно показывать «цена не определена» и не подставлять 0.

Рекомендуемое размещение финансового раздела — **отдельная страница `/bedolaga/revenue`** («Доход по тарифам»), а не вкладка внутри `Finance.tsx`: другой источник данных, другая семантика, не смешивается с ручным реестром `fin_transactions`.

---

## 1. Проблема и цели

### 1.1 Что видит владелец сейчас

- В `web/frontend/src/pages/bedolaga/BedolagaCustomers.tsx` таблица содержит только:
  «Пользователь», «Статус», «Баланс», «Подписка», «Последняя активность», действия.
- В `BedolagaCustomerDetail.tsx` блок «Информация» содержит:
  Имя, Username, Telegram ID, ID, Регистрация, Последняя активность, Промо-группа, Реферальный код.
  Тарифа там нет.
- В карточке подписки есть блок тарифа, но он читает **неправильное поле**:
  `user.tariff_name || '#' + user.tariff_id` на верхнем уровне. Реальный API отдаёт
  `tariff_id/tariff_name` внутри `subscription`, поэтому блок часто не показывается.
- `Finance.tsx` работает с CMS-таблицей `fin_transactions` (ручной ввод + импорт Platega/YooKassa).
  Данные бота туда не попадают, поэтому доход по тарифам в финансах сейчас не виден.

### 1.2 Цели

| ID | Цель | Критерий |
|----|------|----------|
| G1 | Показать тариф в списке клиентов | Колонка «Тариф» + цена/мес; фильтр и сортировка; CSV; мобильные карточки |
| G2 | Показать тариф в карточке клиента | Тариф в блоке «Информация»; цена/период, оплачено до, дней осталось, всего оплачено, следующая оплата |
| G3 | Тариф динамический | Данные обновляются из Bot Web API; TTL списка ≤60 c, снимка аналитики ≤5 мин; без ручной синхронизации |
| G4 | Финансы по тарифам | Распределение клиентов, MRR, кассовый прогноз, начислительный доход, оплачено вперёд, динамика |
| G5 | Честные данные | Покрытие цен, источник цены, предупреждения; неизвестная цена не превращается в 0 |
| G6 | Ничего не ломать | Существующие контракты `/api/bedolaga/*`, `Finance.tsx`, бот и Remnawave не меняются |

### 1.3 Не-цели

- Не менять код бота, Remnawave, тарифы в боте.
- Не писать в БД бота.
- Не делать биллинг, списания, автоплатежи и изменение подписок.
- Не заменять `fin_transactions` и не смешивать ручной реестр с аналитикой бота в одной сумме.
- Не требовать ручного ввода цен в MVP.
- Не делать real-time WebSocket; достаточно TTL-обновления.

### 1.4 Глоссарий

| Термин | Значение |
|--------|----------|
| **Тариф клиента** | Тариф его активной платной подписки. Берётся из `subscription.tariff_id/tariff_name`; при нескольких подписках — по правилу первичной подписки (3.1) |
| **Активная платная подписка** | Не trial, `end_date > now`, статус активный (уточнение в 3.1). Именно она участвует в деньгах |
| **Trial** | Пробная подписка (`is_trial=true` или `status/actual_status=trial`). Показывается отдельно, в деньги не входит |
| **MRR (100% оплата)** | Сумма месячных цен всех активных платных подписок. Ответ на вопрос «сколько принесёт месяц, если все продлятся» |
| **Кассовый прогноз** | Сумма ожидаемых **фактических платежей** в календарном месяце по дате списания/оплаты, а не по дате окончания подписки |
| **Начислительный доход** | Доход, «заработанный» за дни подписки внутри месяца: `дни × дневная цена`. Не равен кассе |
| **Оплачено вперёд** | Остаток неиспользованных дней активной подписки × дневная цена. Это «незаработанная» часть уже полученных денег |
| **Реализованная цена** | Цена, выведенная из фактических платежей. Может быть ниже прайса из-за промокодов, скидок и ручных продлений |
| **Прайс-лист** | Цена из каталога бота (`tariffs.period_prices`). Точная, но в MVP может быть недоступна |
| **Покрытие цен** | Доля активных платных подписок, для которых цена известна. Показывает достоверность денежных сумм |
| **Снимок (snapshot)** | Рассчитанный и закэшированный набор данных аналитики на момент времени |
| **Первичная подписка** | Одна подписка клиента, выбранная для распределения клиентов по тарифам, чтобы не считать одного клиента дважды |
| **Дата списания (charge date)** | `end_date - autopay_days_before` для автоплатежа; иначе `end_date` |

---

## 2. Источник цен тарифов: варианты и рекомендация

### 2.1 Сводная таблица

| | A. Из транзакций | B. БД бота `tariffs` | C. Локальный каталог CMS | D. Гибрид |
|---|---|---|---|---|
| **Источник** | `GET /transactions`, парсинг `description` + `amount_kopeks` | `SELECT ... FROM tariffs` | Новая таблица/JSON в CMS | B → A, при наличии override |
| **Точность** | Средняя: фактически уплаченные цены, возможны скидки | Высокая: прайс-лист и все периоды | Зависит от человека | Высокая, но видно источник |
| **Автоматизм** | Полный | Полный, если есть доступ | Ручной | Полный с fallback |
| **Зависимости** | Только Bot Web API | UFW, env, доступ к БД, стабильность схемы | Миграция/таблица + UI | Bot Web API + опционально БД |
| **Трудозатраты** | 1.5–2 дня | 0.5 дня кода + инфраструктура | 2–3 дня | 3–4 дня |
| **Главный риск** | Парсер описаний; новый тариф не виден до первой покупки; бесплатные тарифы | В проде недоступно; таймауты до 20 c; доступ открыт только dev-IP | Расхождение с ботом; ручной труд противоречит цели | Сложнее объяснять источник |
| **Когда выбирать** | MVP в проде | Если владелец готов открыть 5434 и настроить env | Как аварийный override | Рекомендуется |

### 2.2 Вариант A — матрица цен из фактических транзакций

**Как работает**

1. Загружаются завершённые транзакции `type=subscription_payment`.
2. Из `description` извлекаются название тарифа и период в днях.
3. Цена = `abs(amount_kopeks)`.
4. Для пары `(нормализованное имя тарифа, дни)` считается медиана последних наблюдений.
5. Матрица используется для текущих активных подписок.

**Плюсы**

- Не требует БД бота и изменений инфраструктуры.
- Работает автоматически, в том числе после изменения цен в боте: новые платежи дают новые наблюдения.
- Отражает реально уплаченные суммы, включая скидки и промо.

**Минусы**

- Тариф без единой покупки не имеет цены (например, бесплатный или только что созданный).
- Медиана может быть ниже прайса из-за промокодов.
- Парсер зависит от текста описаний бота.
- При смене названия тарифа старые наблюдения могут не сопоставиться.
- `Автопродление подписки на 30 дней` не содержит названия тарифа.

**Что показывать при отсутствии данных**

`price_known=false`, `price_source=unknown`, `monthly_price=null`; тариф и клиенты видны, деньги — нет; в UI «Цена не определена», в аналитике — покрытие цен и предупреждение.

### 2.3 Вариант B — прямой доступ к БД бота

**Как работает**

- `web/backend/core/bot_db.py` уже умеет читать `tariffs`, включая `period_prices` (копейки), `price_per_day_kopeks`, `daily_price_kopeks`, `is_daily`.
- Доступ уже настроен через «Настройки → Интеграции → bot_db» (реестр `settings_registry`, `bot_db.refresh_config` без рестарта). Цены отображаются на странице «Тарифы».
- **Решение владельца (2026-11-21): это основной источник цен.** Доступность и динамичность нужно проверить и зафиксировать (раздел 2.8), а не откладывать на Этап 2.

**Плюсы**

- Самая точная цена: прайс-лист, все периоды, бесплатные тарифы, новые тарифы сразу.
- Динамика «поменяли в боте → увидели в CMS» без ожидания покупки.

**Минусы и риски**

- Исторический риск: доступ через ENV/UFW раньше не работал (timeout ~20 c из контейнера). Сейчас DSN задаётся в реестре интеграций и применяется без рестарта; ENV остаётся fallback.
- Синхронный вызов без таймаута в HTTP-запросе недопустим: нужны `connect/command/pool timeout` и разделение «ошибка» vs «пусто».
- Появляется инфраструктурная зависимость и риск, что схема бота изменится.
- Нужны отдельные работы по UFW/env и проверке с прода.

**Что показывать при отсутствии данных**

Не блокировать запрос: короткий таймаут (≤2 c), circuit breaker, fallback на вариант A.

### 2.4 Вариант C — локальный справочник тарифов в CMS

**Как работает**

- Новая таблица `bedolaga_tariff_prices` или JSON в настройках CMS.
- Поля: `tariff_id`, `tariff_name`, `period_days`, `price_kopeks`, `is_override`, `updated_at`, `updated_by`.
- Редактирование в `BedolagaTariffs.tsx`.

**Плюсы**

- Полный контроль, работает без бота.
- Можно задать 0 для бесплатных тарифов и поправить кривые historical-цены.
- Не зависит от UFW.

**Минусы**

- Противоречит требованию «без ручного ввода».
- Устаревает при изменении цен в боте.
- Нужны хранение, CRUD, права, аудит, UI.
- Дублирует каталог бота.

**Что показывать при отсутствии данных**

Если запись не задана — `unknown`, fallback на A/B.

### 2.5 Вариант D — гибрид (рекомендация)

**Приоритет источников для каждой пары `(tariff_id, period_days)`**

| Приоритет | Источник | `price_source` | `price_kind` | Условие |
|---:|---|---|---|---|
| 100 | Ручной override | `manual` | `list` | Этап 2; задан явно |
| 80 | БД бота `tariffs` | `bot_db` | `list` | `BOT_DB_*` настроен, ответ ≤2 c |
| 50 | Транзакции | `transactions` | `realized` | Есть ≥1 валидное наблюдение |
| 0 | Нет данных | `unknown` | `unknown` | Ничего не найдено |

**Уточнение по решениям владельца (2026-11-21)**

- **Основной источник цен — `bot_db`** (тарифы уже подтягиваются и цены видны). `transactions` — только fallback/сверка, `manual` — Этап 2, не блокирует MVP.
- **`0` — валидная цена, а не отсутствие данных.** Бесплатные тарифы (`VIP(MAX)`, `TheOne`, `ilbakery`, `period_prices {"999":0}`) учитываются наравне со всеми; `0` может стать ненулевым и наоборот — пересчёт при каждом обновлении каталога.
- **Учитываются все тарифы без исключения**, включая `is_active=false` (помечать бейджем «неактивен», клиентов по нему обычно 0). Не фильтровать по `is_active` в аналитике.
- `unknown` — только если тарифа нет ни в БД, ни в транзакциях; такие строки показывать отдельно, не превращая в 0.

**Правила**

- Для каждой строки тарифа возвращается `price_source` и `price_kind`; в UI — бейдж.
- Не смешивать прайс и реализованную цену в одной сумме молча. В ответе есть `mrr_basis`:
  `list`, `realized`, `mixed`, `unknown`.
- Если источники расходятся более чем на 10%, добавить warning `price_sources_disagree`
  и для MRR использовать более приоритетный источник; фактические платежи показывать отдельно.
- В MVP ручной override не обязателен; он появляется на Этапе 2 для бесплатных тарифов и аварийных случаев.

**Почему это лучший компромисс**

- Даёт автоматику уже сейчас, без ожидания изменений UFW.
- Не ломается, если БД бота недоступна.
- Позволяет позже повысить точность без переделки модели.
- Всегда показывает, насколько данным можно доверять.

### 2.6 Алгоритм вывода цен из транзакций

Псевдоправила:

```
normalize_name(s):
  убрать emoji/пиктограммы и служебные символы по краям
  casefold, ё -> е
  схлопнуть пробелы, обрезать

parse_days(description):
  искать (\d{1,4}) + (дн|день|дня|дней|day|days)
  вернуть int, если 1..3650

parse_tariff_name(description):
  "Покупка тарифа <NAME> на <N> дней"            -> NAME
  "Продление подписки на <N> дней (<NAME>)"      -> NAME
  "Автопродление подписки на <N> дней"           -> null (без имени)
```

Правила отбора наблюдений:

- Только `type == "subscription_payment"`.
- `is_completed != false`.
- `amount_kopeks < 0`; цена = `abs(amount_kopeks)`.
- `price` в диапазоне 1 ₽ … 100 000 ₽.
- Период из описания; имя из описания.
- Окно наблюдений: последние `days_back` (по умолчанию 365), не более 50 последних наблюдений на пару.
- Агрегат: **медиана**, а не среднее.
- Confidence:
  - `high`: ≥5 наблюдений и последнее ≤30 дней;
  - `medium`: ≥2 наблюдения или последнее ≤90 дней;
  - `low`: 1 наблюдение или последнее >90 дней.

Сопоставление с `tariff_id`:

- Из текущих пользователей строится карта `normalized_name -> set(tariff_id)`.
- Если имя соответствует нескольким ID — warning `ambiguous_tariff_name`; цена применяется ко всем, в UI видно предупреждение.
- Если у тарифа нет наблюдений, но есть бесплатные значения из БД — цена 0 и `is_free=true`.
- Без БД бесплатность **не угадывать**: если платежей нет, это `unknown`, а не 0. Исключение — явные нулевые завершённые платежи.

`Автопродление` без имени:

- Для каталога цен **не использовать**.
- Для персональной суммы «всего оплатил» использовать можно: это всё равно `subscription_payment` пользователя.
- Для привязки к тарифу — только если сумма совпадает с известной ценой периода текущего тарифа пользователя и дата попадает в его текущую подписку; иначе не привязывать.

### 2.7 Доступ к БД бота: фактическое состояние

- **Доступ уже работает**: тарифы и цены отображаются в админке (Настройки → Интеграции → `bot_db`; `bot_db.refresh_config` применяет новые ключи без рестарта).
- ENV `BOT_DB_*` — резервный путь (`settings_values.py`: приоритет store=settings → env → default). Очистка host в админке вернёт значение из ENV.
- Ограничения, которые надо закрыть в рамках E1:
  - в `bot_db.get_tariffs()` нет таймаутов (`connect/command/pool`) и нет кэша;
  - любое исключение превращается в `[]`, а `/api/bedolaga/tariffs` отдаёт `200 []` — ошибка неотличима от пустого каталога;
  - битая строка (JSON/ключ/цена) обнуляет весь список;
  - `bot_db.invalidate()` существует, но не вызывается.
- Требование: обернуть чтение в `asyncio.wait_for` (≤2 c), кэш успеха ≤60 c, negative-cache 30–60 c, circuit breaker 5–10 мин, ошибка → `502/503` с телом, а не `200 []`.
- Повторные 20-секундные попытки на каждый запрос запрещены.

### 2.8 Динамичность: текущее состояние и требования

**Проверено в коде (2026-11-21)**

| Слой | Кэш | Что происходит при смене цены в БД |
|---|---|---|
| PostgreSQL | — | — |
| `bot_db.get_tariffs()` | нет | свежие данные при каждом вызове |
| `GET /api/bedolaga/tariffs` | нет | свежие данные при каждом запросе |
| nginx/HTTP | нет | без `proxy_cache` |
| react-query (страница «Тарифы») | `staleTime 60 c`, хранение 5 мин | открытая страница **не обновится** (нет `refetchInterval`/`refetchOnWindowFocus`); после перезахода 0–60 c |

**Вывод:** бэкенд динамичен, UI — нет. Дополнительно ошибка БД маскируется под пустой список и кэшируется фронтом на 60 c.

**Требования к MVP (E1/E2/E5)**

- Серверный кэш тарифов ≤60 c + инвалидация при сохранении `BOT_DB_TRIGGER_KEYS` (settings) и по кнопке «Обновить».
- Различать `ok / empty / error`: при ошибке — HTTP 502/503 + `warnings`, пустой каталог — `200` с `price_source=unknown`.
- `BedolagaTariffs.tsx` и страница дохода: `refetchInterval: 60_000`, `refetchOnWindowFocus: true`, ветка `isError`, показ `updated_at`, блокировка кнопки по `isFetching`.
- В ответе аналитики — `as_of`/`generated_at`, чтобы владелец видел актуальность.

---

## 3. Модель расчёта финансов

### 3.1 Выбор подписок и тарифов

**Активная платная подписка**

```
is_paid_active(sub):
  end = parse_ts(sub.end_date)
  if end <= now_msk: false
  if sub.is_trial == true: false
  if sub.status in {"expired", "disabled", "cancelled", "deactivated"}: false
  if sub.actual_status in {"expired", "disabled", "cancelled", "deactivated"}: false
  return true
```

- `limited` считается платной активной, если `end_date > now` и `is_trial=false`:
  клиент оплатил, но исчерпал трафик. В ответе можно отдать `status`.
- Если `actual_status` противоречит `status`, приоритет у `actual_status`.

**Первичная подписка клиента**

```
primary_sub(user):
  candidates = [s for s in user.subscriptions[] if is_paid_active(s)]
  if candidates: return max(candidates, by=(end_date, tariff_id))
  if user.subscription and is_paid_active(user.subscription): return user.subscription
  if user.subscription and is_trial(user.subscription): return user.subscription  # только для trial-разреза
  return null
```

- Для распределения клиентов по тарифам используется **одна** первичная подписка.
- Для MRR, оплаты вперёд и прогноза используются **все** активные платные подписки.
- Если `active_paid_subscriptions != clients_with_paid`, вернуть warning
  `multi_subscription_clients` и показать оба числа.

**Тариф**

```
tariff_of(sub) = {id: sub.tariff_id ?? null, name: sub.tariff_name ?? "Не определён"}
```

- Если `tariff_id` есть, а имени нет — `#<id>`.
- Если нет ни id, ни имени — `Не определён`, `tariff_key = "unknown"`.
- Название тарифа всегда берётся из свежего ответа API, поэтому переименование в боте видно после TTL.

### 3.2 Формулы

**F1. Распределение клиентов по тарифам**

```
for user in all_users:
  p = primary_sub(user)
  if p is paid_active:
      clients_paid[p.tariff] += 1
  elif p is trial:
      clients_trial[p.tariff] += 1
  else:
      clients_without_subscription += 1

clients_total = users_total
```

**F2. Доля тарифа**

```
share_pct(tariff) = clients_paid[tariff] / clients_with_paid * 100
```

Trial и «без подписки» считаются отдельными строками и не входят в знаменатель долей платных тарифов.

**F3. Месячная цена тарифа**

```
price_per_day(tariff):
  if catalog[tariff].price_per_day_kopeks is not null:
      return it                                  # явное поле из БД бота
  observations = все пары (days, price) тарифа из транзакций
  if observations непусты:
      return median(price / days)                # реализованная дневная цена
  return null

price_for(tariff, days):
  exact = catalog[tariff].periods[days]
  if exact is not null: return exact             # price_basis = exact_period
  pd = price_per_day(tariff)
  if pd is not null: return round(pd * days)     # price_basis = proportional
  return null

monthly_price(tariff):
  if catalog[tariff].periods[30] exists: return it          # price_basis = 30_day
  if catalog[tariff].price_per_day_kopeks exists:
      return round(price_per_day_kopeks * 30)               # price_basis = per_day
  pd = price_per_day(tariff)
  if pd is not null: return round(pd * 30)                  # price_basis = realized_per_day
  if catalog[tariff].daily_price_kopeks exists:
      return round(daily_price_kopeks * 30)                 # price_basis = daily
  return null
```

- `price_known=false`, если `null`.
- `price_basis` возвращается в ответе: `exact_period`, `proportional`, `30_day`, `per_day`, `realized_per_day`, `daily`, `free`, `unknown`.
- Пропорциональный пересчёт (`proportional`, `realized_per_day`) понижает `confidence` на один уровень: длинный период мог быть со скидкой.
- Явно бесплатный тариф — `0`, `is_free=true`.

**F4. MRR при 100% оплате**

```
mrr = Σ over all active_paid_subscriptions:
        monthly_price(tariff_of(sub)), только если price_known
mrr_unknown_subscriptions = count(active_paid_subscriptions where not price_known)
mrr_lower_bound = (mrr_unknown_subscriptions > 0)
mrr_basis = list | realized | mixed | unknown
```

- Trial и бесплатные тарифы в MRR не входят; бесплатные показываются отдельной строкой с 0.
- Не экстраполировать неизвестные цены молча. Можно показать `mrr_min = known` и `mrr_max_estimate` только как отдельную оценку с пометкой.

**F5. Покрытие цен**

```
price_coverage_pct =
  price_known_active_paid_subscriptions / active_paid_subscriptions * 100
```

**F6. Период подписки**

```
period_days(sub):
  if sub.autopay_period_days in 1..3650: return it
  d = floor((end_date - start_date).days)
  if d in 1..3650: return d
  return 30
```

`autopay_period_days` может отсутствовать в API — это нормально, используем фактический интервал или 30 дней.

**F7. Цена периода**

```
period_price(sub):
  p = price_for(tariff_of(sub), period_days(sub))
  if p is not null: return p
  m = monthly_price(tariff_of(sub))
  if m is not null: return round(m / 30 * period_days(sub))
  return null
```

**F8. Кассовый прогноз на следующий месяц**

```
next_month = первый календарный месяц после as_of
for sub in active_paid_subscriptions:
  period = period_days(sub)
  amount = period_price(sub)
  charge_date = sub.end_date
  if sub.autopay_enabled and sub.autopay_days_before >= 0:
      charge_date = sub.end_date - sub.autopay_days_before
  if charge_date in next_month:
      if amount is known: cash_forecast += amount
      else: unknown_count += 1
```

- Это **валовая** сумма ожидаемых списаний. Если у клиента есть баланс, автоплатёж может пройти из баланса, а не новыми деньгами. Это отдельное предупреждение, не корректируем молча.
- `basis=cash` — по `charge_date`; `basis=renewal` — по `end_date`.

**F9. Продления, истекающие в месяце**

```
renewals_due(month) = Σ period_price(sub) для sub, у которых end_date в month
```

Показывается отдельно от кассы, потому что дата списания может быть в предыдущем месяце.

**F10. Начислительный доход месяца**

```
for sub in active_paid_subscriptions:
  overlap_days = max(0, min(end_date, month_end) - max(start_date, month_start) + 1)
  daily = period_price(sub) / period_days(sub)
  if daily known:
      accrual_revenue += overlap_days * daily
```

- Для текущего и будущих месяцев — корректно по текущим подпискам.
- Для прошлых месяцев это **не полная историческая выручка**, а доход по подпискам, которые живы сегодня. В графике прошлые месяцы показывать фактической кассой из транзакций; начислительный ряд для прошлого помечать как «по текущим подпискам» либо не показывать до Этапа 2.

**F11. Уже оплачено клиентом**

```
paid_total(user) =
  Σ abs(amount_kopeks) по завершённым транзакциям type=subscription_payment
  минус Σ abs(amount_kopeks) по type=refund, если такой тип встречается
```

- `gift_payment` и `withdrawal` не входят в «оплачено за свою подписку».
- `paid_last_12m`, `paid_current_month` — те же суммы с фильтром по дате.
- Если `is_completed` отсутствует — считать завершённой; исключать только `false`.

**F12. Оплачено вперёд**

```
remaining_days(sub) = max(0, ceil((end_date - now) / 1 день))
daily(sub) = period_price(sub) / period_days(sub)
paid_forward = Σ remaining_days(sub) * daily(sub)
```

- Это остаток уже оплаченного периода, а не будущий платёж.
- Для 90-дневной подписки использовать цену 90 дней / 90, а не месячную цену / 30.

**F13. Следующая оплата**

```
next_payment_date = sub.end_date
next_payment_amount = period_price(sub)
expected_charge_date =
  autopay_enabled ? end_date - autopay_days_before : end_date
autopay = sub.autopay_enabled
```

- «Когда он теперь оплатит» = `expected_charge_date` (для автоплатежа) или `next_payment_date`.

**F14. Динамика и коэффициент продления**

```
cash_received(month) = Σ abs(amount) по subscription_payment с completed_at в month
payments_count(month) = count(...)
unique_payers(month) = count(distinct user_id)
renewal_payments(month) = count(description содержит "продление" или "автопродление")
purchase_payments(month) = count(description содержит "покупка тарифа")
renewal_proxy(month) =
  if (renewal_payments + purchase_payments) == 0: null
  else: renewal_payments / (renewal_payments + purchase_payments)
```

- `renewal_proxy` — **приблизительный** показатель по текстам платежей, не строгий churn.
- Если платежей с распознанным типом нет — `null`, а не 0.
- Точный коэффициент продления требует истории подписок; в MVP API не отдаёт истёкшие подписки.
- Для «прогноз vs факт»: на текущем месяце сравнивать `cash_forecast(month)` и `cash_received(month)`;
  для прошлых месяцев прогноз без снимков будет смещён, поэтому в MVP показывать только факт, а прогноз — с Этапа 2.

**F15. Факт по месяцу**

```
actual_cash(month) = cash_received(month)
avg_payment = cash_received / payments_count
```

### 3.3 Граничные случаи

| Случай | Правило |
|--------|---------|
| Бесплатный тариф (0 ₽) | `is_free=true`, `monthly_price=0`, клиенты считаются, MRR 0; не `unknown` |
| Trial | Отдельная строка/разрез; в MRR, кассу и «оплачено вперёд» не входит |
| Нет `tariff_id` | Тариф «Не определён», клиент считается, деньги — `unknown` |
| Несколько активных подписок | Клиент в распределении — по первичной; MRR/прогноз/вперёд — по всем; warning |
| Нет `autopay_period_days` | Фактический интервал `end_date - start_date`; иначе 30 дней |
| Ручное продление без платежа | `paid_forward` растёт, касса нет; warning `manual_extension_detected` |
| Промокод/скидка | В транзакционной цене будет фактическая; `price_kind=realized`; MRR ниже прайса |
| Возврат | Если тип `refund` есть — вычитается из `paid_total`; иначе не учитывается |
| Автоплатёж с баланса | Кассовый прогноз — валовая сумма; warning `autopay_balance_unaccounted` |
| Границы месяца | Месяц в Europe/Moscow; дни включительно; остаток дней — `ceil` |
| Просроченная подписка | Не active paid; в прогноз не входит; в историю — по факту платежей |
| Переименование тарифа | Новое имя из API; старые транзакции могут не сопоставиться; warning `tariff_name_changed` |
| Частичные данные | 200 + `partial=true` + warnings; не отдавать выдуманные нули |
| Пользователь удалён, транзакции остались | Транзакции учитываются в кассе, но не в распределении клиентов |
| Отрицательный/нулевой платёж | В цену не попадает; в `paid_total` — по модулю, если завершён |

### 3.4 Валюта, округление, время

- Все суммы хранятся и считаются в **копейках** (`int`), отдаются также рубли (`float`, 2 знака).
- Округление — half-up до копейки на границе ответа.
- Бизнес-таймзона — **Europe/Moscow (UTC+3, без DST)**. Все `*_at` парсятся как ISO; naive → UTC; затем MSK.
- Границы месяца — `00:00:00 MSK` первого дня и `23:59:59.999 MSK` последнего.
- В ответах всегда есть `as_of` и `generated_at`.

---

## 4. API-контракты

### 4.1 Новые модули

| Файл | Назначение |
|------|-----------|
| `web/backend/core/bedolaga_analytics.py` | Чистая логика: нормализация, парсинг, каталог цен, выбор подписок, агрегаты, кэш снимка |
| `web/backend/api/v1/bedolaga/analytics.py` | FastAPI-роутер: 4 эндпоинта, auth, валидация, ошибки |
| `web/backend/api/v1/bedolaga/__init__.py` | Подключить `analytics_router` с `prefix="/analytics"` |
| `web/backend/tests/test_bedolaga_analytics.py` | Юнит-тесты логики |
| `web/backend/tests/test_bedolaga_analytics_api.py` | Тесты API с monkeypatch клиента |

Полные пути:

- `GET /api/bedolaga/analytics/tariffs`
- `GET /api/bedolaga/analytics/overview`
- `GET /api/bedolaga/analytics/forecast`
- `GET /api/bedolaga/analytics/customers/{user_id}`

Все — `Depends(get_current_admin)`. Только чтение.

### 4.2 Общие правила

- Формат ответа — прямой JSON-объект, как у существующих `/api/bedolaga/overview`, `/full`, `/tariffs`.
  Без конверта `{success,data}`.
- Ошибки — как в пакете `bedolaga`: `HTTPException(status_code, detail={success:false,error})`.
- Коды:
  - `503` — Bedolaga не настроен (`ensure_configured`);
  - `502` — upstream недоступен/таймаут;
  - `404` — пользователь не найден;
  - `400` — неверный `month`/`basis`/диапазон;
  - `200` с `partial=true` — часть данных не получена.
- Кэш:
  - снимок аналитики — 300 c;
  - пользователи — 60 c;
  - транзакции — 300 c;
  - `/stats/full` — 60 c;
  - цены БД бота — 600 c успех / 60 c ошибка / 10 мин circuit breaker;
  - negative-cache upstream — 30 c.
- Single-flight: одновременные запросы на один ключ ждут один расчёт, а не дублируют 12 HTTP-вызовов.
- `refresh=true` — обойти кэш снимка; повторный `refresh` чаще раза в 10 c не рекомендуется (можно отдавать текущий снимок с `refresh_throttled=true`).
- Батчинг:
  - пользователи: `limit=200`, первый запрос даёт `total`, дальше страницы 200/400/...; для 277 — 2 запроса;
  - транзакции: `limit=100`, первый даёт `total`, дальше страницы; для 996 — 10 запросов; concurrency ≤4;
  - `GET /subscriptions` не использовать: `subscription` и `subscriptions[]` уже есть в `/users`;
  - не делать 277 запросов `/users/{id}`.
- Бюджет времени: холодный снимок ≤15 c, целевой p95 ≤6 c; тёплый ≤300 мс.
- Метаданные в каждом ответе:
  `generated_at`, `as_of`, `partial`, `warnings[]`, `sources{}`.
- Коды warning:
  `transactions_unavailable`, `users_partial`, `price_unknown`, `price_sources_disagree`,
  `ambiguous_tariff_name`, `tariff_name_changed`, `multi_subscription_clients`,
  `autopay_balance_unaccounted`, `manual_extension_detected`, `bot_db_disabled`.

### 4.3 `GET /api/bedolaga/analytics/tariffs`

Каталог тарифов с ценами, количеством клиентов и деньгами.

Query:

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `days_back` | int | 365 | Окно транзакций для вывода цен, 30..3650 |
| `refresh` | bool | false | Пересчитать снимок |
| `include_inactive` | bool | true | Показывать неактивные тарифы с 0 клиентов |

Ответ:

```json
{
  "generated_at": "2026-11-20T23:30:00+03:00",
  "as_of": "2026-11-20",
  "currency": "RUB",
  "price_source_priority": ["manual", "bot_db", "transactions"],
  "sources": {
    "bot_db": {"status": "disabled|ok|error|timeout", "checked_at": "..."},
    "transactions": {"status": "ok|insufficient", "scanned": 996, "named_price_samples": 534},
    "users": {"status": "ok|partial", "loaded": 277, "total": 277}
  },
  "coverage": {
    "users_total": 277,
    "clients_with_paid": 133,
    "active_paid_subscriptions": 133,
    "trial_subscriptions": 3,
    "clients_without_subscription": 141,
    "price_known_subscriptions": 130,
    "price_unknown_subscriptions": 3,
    "price_coverage_pct": 97.7
  },
  "items": [
    {
      "tariff_id": 2,
      "tariff_name": "👤 Optimal",
      "normalized_name": "optimal",
      "is_active": true,
      "is_free": false,
      "price_known": true,
      "price_source": "transactions",
      "price_kind": "realized",
      "confidence": "high",
      "period_prices": [
        {"days": 30, "price_kopeks": 15000, "price_rubles": 150.0, "samples": 42, "last_seen_at": "..."}
      ],
      "monthly_price_kopeks": 15000,
      "monthly_price_rubles": 150.0,
      "price_per_day_kopeks": 500,
      "price_basis": "exact_period|proportional|30_day|per_day|realized_per_day|daily|free|unknown",
      "clients_paid": 57,
      "clients_trial": 0,
      "clients_total": 57,
      "share_pct": 42.9,
      "mrr_kopeks": 855000,
      "paid_forward_kopeks": 654000,
      "next_month_expected_kopeks": 720000,
      "unknown_price_clients": 0
    }
  ],
  "totals": {
    "clients_paid": 133,
    "clients_trial": 3,
    "clients_without_subscription": 141,
    "mrr_kopeks": 0,
    "mrr_basis": "mixed",
    "mrr_is_lower_bound": true,
    "paid_forward_kopeks": 0,
    "next_month_expected_kopeks": 0,
    "unknown_price_clients": 0
  },
  "warnings": [
    {"code": "price_unknown", "message": "Цена не определена для тарифов: ...", "tariff_ids": [15]}
  ],
  "partial": false
}
```

Числа в примере — только форма ответа, не факт прода.

### 4.4 `GET /api/bedolaga/analytics/overview`

KPI, распределение и динамика.

Query:

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `month` | `YYYY-MM` | текущий MSK | Отчётный месяц |
| `months` | int | 6 | Глубина истории, 1..24 |
| `days_back` | int | 365 | Окно для цен |
| `refresh` | bool | false | Пересчитать |

Ответ:

```json
{
  "generated_at": "...",
  "as_of": "2026-11-20",
  "month": "2026-11",
  "next_month": "2026-12",
  "coverage": { "...": "как в /analytics/tariffs" },
  "kpis": {
    "mrr_kopeks": 0,
    "mrr_basis": "mixed",
    "mrr_is_lower_bound": true,
    "cash_forecast_next_month_kopeks": 0,
    "cash_forecast_unknown_count": 0,
    "renewals_due_next_month_kopeks": 0,
    "renewals_due_next_month_count": 0,
    "paid_forward_kopeks": 0,
    "accrual_revenue_current_month_kopeks": 0,
    "cash_received_current_month_kopeks": 0,
    "active_paid_clients": 133,
    "active_paid_subscriptions": 133,
    "autopay_enabled_subscriptions": 103
  },
  "by_tariff": [
    {
      "tariff_id": 2,
      "tariff_name": "👤 Optimal",
      "clients_paid": 57,
      "clients_trial": 0,
      "share_pct": 42.9,
      "monthly_price_kopeks": 15000,
      "price_source": "transactions",
      "price_kind": "realized",
      "mrr_kopeks": 855000,
      "paid_forward_kopeks": 654000,
      "next_month_expected_kopeks": 720000,
      "unknown_price_clients": 0
    }
  ],
  "monthly": [
    {
      "month": "2026-06",
      "cash_received_kopeks": 0,
      "cash_received_rubles": 0.0,
      "payments_count": 0,
      "unique_payers": 0,
      "renewal_payments": 0,
      "purchase_payments": 0,
      "renewal_proxy": 0.0,
      "accrual_revenue_kopeks": null,
      "accrual_is_estimate": true
    }
  ],
  "warnings": [],
  "partial": false
}
```

Правила:

- `accrual_revenue_kopeks` для прошлых месяцев либо `null`, либо помечен `accrual_is_estimate=true`.
- `cash_received` — факт из транзакций.
- `mrr` может быть lower bound; это явно указано.

### 4.5 `GET /api/bedolaga/analytics/forecast`

Прогноз платежей на месяц.

Query:

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `month` | `YYYY-MM` | следующий месяц | Месяц прогноза |
| `basis` | `cash\|renewal` | `cash` | По дате списания или по дате окончания |
| `refresh` | bool | false | Пересчитать |

Ответ:

```json
{
  "generated_at": "...",
  "month": "2026-12",
  "basis": "cash",
  "totals": {
    "expected_kopeks": 0,
    "expected_rubles": 0.0,
    "payments_count": 0,
    "unknown_count": 0,
    "autopay_enabled_count": 0
  },
  "by_day": [
    {"date": "2026-12-01", "expected_kopeks": 0, "payments_count": 0}
  ],
  "by_tariff": [
    {"tariff_id": 2, "tariff_name": "👤 Optimal", "expected_kopeks": 0, "payments_count": 0}
  ],
  "items": [
    {
      "user_id": 1,
      "username": "user",
      "subscription_id": 10,
      "tariff_id": 2,
      "tariff_name": "👤 Optimal",
      "period_days": 30,
      "period_price_kopeks": 15000,
      "end_date": "2026-12-12T...",
      "expected_charge_date": "2026-12-09",
      "autopay_enabled": true,
      "autopay_days_before": 3,
      "amount_kopeks": 15000,
      "price_known": true,
      "price_source": "transactions"
    }
  ],
  "warnings": [],
  "partial": false
}
```

- `items` ограничить 500 строками; полный список доступен через CSV на фронте или увеличить лимит отдельным параметром на Этапе 2.
- Сортировка: `expected_charge_date`, затем `user_id`.

### 4.6 `GET /api/bedolaga/analytics/customers/{user_id}`

Финансовый профиль клиента для карточки.

Query: `days_back` (по умолчанию 3650), `refresh`.

Ответ:

```json
{
  "generated_at": "...",
  "as_of": "2026-11-20",
  "user": {"id": 1, "username": "user", "telegram_id": 123, "first_name": "Имя"},
  "primary_subscription": {
    "id": 10,
    "status": "active",
    "actual_status": "active",
    "is_trial": false,
    "tariff_id": 2,
    "tariff_name": "👤 Optimal",
    "start_date": "...",
    "end_date": "...",
    "days_left": 12,
    "autopay_enabled": true,
    "autopay_days_before": 3,
    "autopay_period_days": null,
    "period_days": 30
  },
  "tariff": {
    "price_known": true,
    "price_source": "transactions",
    "price_kind": "realized",
    "price_basis": "exact_period",
    "monthly_price_kopeks": 15000,
    "period_price_kopeks": 15000,
    "period_days": 30,
    "price_per_day_kopeks": 500
  },
  "money": {
    "paid_total_kopeks": 45000,
    "paid_last_12m_kopeks": 30000,
    "paid_current_month_kopeks": 0,
    "paid_forward_kopeks": 6000,
    "next_payment_date": "2026-12-12",
    "expected_charge_date": "2026-12-09",
    "next_payment_kopeks": 15000,
    "next_payment_known": true
  },
  "subscriptions": [
    {"id": 10, "tariff_id": 2, "tariff_name": "👤 Optimal", "end_date": "...", "is_trial": false}
  ],
  "payments": [
    {"id": 1, "created_at": "...", "amount_kopeks": -15000, "description": "...", "type": "subscription_payment"}
  ],
  "warnings": [],
  "partial": false
}
```

- Если у клиента нет подписки — `primary_subscription=null`, деньги по подписке `null`, но `paid_total` из истории остаётся.
- `payments` — последние 50; полная история — в существующем `/customers/transactions?user_id=`.
- Кэш 120 c на пользователя.

### 4.7 Изменения существующих контрактов (аддитивные)

`GET /api/bedolaga/customers` в `web/backend/api/v1/bedolaga/customers.py`:

- Добавить query-параметры:
  - `tariff_id: int | None`;
  - `tariff_missing: bool = false`;
  - `sort=tariff` (новое допустимое значение).
- Условие локальной обработки расширить: `need_local` включает `tariff_id`, `tariff_missing`, `sort=tariff`.
- В локальной ветке фильтровать по `primary subscription`:
  - `tariff_id` — совпадение `subscription.tariff_id`;
  - `tariff_missing` — нет активной подписки или нет `tariff_id`.
- Сортировка `tariff` — по нормализованному `tariff_name`; пустые в конце.
- Ключ кэша включает новые параметры.
- Ответ не меняется по форме; `tariff_id/tariff_name` уже внутри `subscription`, но нужно добавить нормализацию:
  если `subscription` отсутствует, а `subscriptions[]` непуст — подставить первичную в `subscription` (аддитивно).
- Не менять upstream-поведение без локальной необходимости.

`GET /api/bedolaga/customers/{id}`: та же нормализация `subscription` (если нужно).
`GET /api/bedolaga/tariffs`: не трогать; это каталог из БД и он может быть пустым.
`GET /api/bedolaga/overview`: не трогать.

### 4.8 Тесты API и логики

Юнит (`test_bedolaga_analytics.py`):

- нормализация имён с emoji и пробелами;
- парсинг трёх шаблонов описаний;
- медиана и confidence;
- несколько тарифов с одинаковым именем;
- выбор первичной подписки при нескольких;
- trial и отсутствие `tariff_id`;
- MRR с known/unknown/free;
- кассовый прогноз на границе месяца MSK;
- начислительный доход на границе месяца;
- `paid_forward` для 30/90 дней;
- `paid_total` без gift/withdrawal, с refund;
- partial data и warning-коды.

API (`test_bedolaga_analytics_api.py`):

- без auth → 401/403;
- не настроенный бот → 503;
- успешный ответ на monkeypatched данных;
- падение транзакций → 200 + `partial=true`;
- `refresh=true` обходит снимок;
- существующий `test_bedolaga_overview_subscriptions.py` не сломан.

---

## 5. UI/UX

### 5.1 Список клиентов (`BedolagaCustomers.tsx`)

**Колонка «Тариф»**

- Разместить между «Подписка» и «Последняя активность».
- Показывать:
  - название тарифа (с emoji, как в боте);
  - цену `150 ₽/мес` мелким текстом, если цена известна;
  - `Не определён` для отсутствующего тарифа;
  - `Бесплатный` для `is_free=true`;
  - `—` для клиента без подписки.
- Для trial показывать тариф trial, но бейдж `Trial` уже есть в колонке «Подписка»; в колонке тарифа — название.

**Данные**

- Тариф уже приходит в `user.subscription.tariff_id/tariff_name`.
- Цена — из `GET /api/bedolaga/analytics/tariffs` (кэш 5 мин), мапа `tariff_id -> monthly_price`.
- Если аналитика недоступна — показывать только название, без цены; не ломать таблицу.

**Фильтр**

- Новый select «Тариф» в панели фильтров.
- Опции: «Все тарифы», список из аналитики, «Без тарифа».
- Передавать `tariff_id` или `tariff_missing=true` в `/customers`.
- Чип активного фильтра и сброс — как у существующих.

**Сортировка**

- Заголовок «Тариф» с `SortIcon`, `sort=tariff`, `order=asc|desc`.
- Локальная сортировка в бэкенде; пустые/неопределённые — в конце.

**CSV**

- Добавить колонки: `Tariff`, `Tariff price (RUB/month)`, `Paid until`.
- Сохранить существующие колонки и порядок, новые — после `Subscription`.

**Мобильные карточки**

- Добавить строку `Тариф: <name> · <price>/мес` под балансом/подпиской.
- Если тарифа нет — `Тариф: —`.

**Состояния**

- Skeleton для новой колонки.
- Пустой результат фильтра — существующий `noResults`.
- Ошибка аналитики цен — тихо, без toast на каждый рендер; максимум один warning.

### 5.2 Карточка клиента (`BedolagaCustomerDetail.tsx`)

**Исправить источник тарифа**

- Сейчас блок тарифа читает `user.tariff_name` (верхний уровень) — заменить на:
  `sub?.tariff_name || user.primary_subscription?.tariff_name || user.subscription?.tariff_name`.
- Если `sub` отсутствует, но есть `subscriptions[]`, выбрать первичную тем же правилом, что и бэкенд.
- Убрать условие, из-за которого блок скрывается при наличии данных только внутри `subscription`.

**Блок «Информация»**

Добавить строку:

- `Тариф` — `sub?.tariff_name || 'Не определён'`, иконка `Star`.
- Желательно после `ID` и перед разделителем, чтобы тариф был рядом с идентификаторами.

**Карточка «Подписка»**

Добавить/сохранить:

- `Цена`: `150 ₽ / 30 дней` или `—`;
- `Оплачено до`: `end_date`;
- `Осталось`: `N дн.`;
- `Автоплатёж`: бейдж и `за N дн.` (если есть).

**Новая карточка «Финансы клиента»**

Разместить в колонке 2 или 3, после подписки:

- `Всего оплатил` — `paid_total_kopeks`;
- `Оплачено вперёд` — `paid_forward_kopeks`;
- `Следующая оплата` — дата + сумма;
- `Дата списания` — `expected_charge_date` + бейдж `авто`;
- `Оплачено за 12 мес.` — опционально.

Источник — `GET /api/bedolaga/analytics/customers/{id}`.
При ошибке — карточка показывает «Финансовые данные временно недоступны», остальная страница работает.

**Кнопки**

- Не добавлять ручное редактирование цен.
- Ссылка «Все платежи» — на существующую историю транзакций/раздел.

### 5.3 Финансы: отдельная страница или вкладка

**Рекомендация: отдельная страница `/bedolaga/revenue` («Доход по тарифам»).**

**Решение владельца (2026-11-21): принято.** Сначала отдельная страница; позже — связать с вкладкой «Финансы» (ссылка/встраивание), без объединения сумм.

Причины:

1. `Finance.tsx` — ручной реестр `fin_transactions` с импортом Platega/YooKassa; аналитика бота — другой источник и другая семантика. Смешивание в одном экране провоцирует неверные итоги.
2. `Finance.tsx` уже 682 строки; добавление KPI, таблицы тарифов, календаря и графика усложнит поддержку.
3. Bedolaga-раздел уже группирует данные бота (Дашборд, Клиенты, Тарифы); логично держать доход там.
4. Отдельная страница позволяет независимо кэшировать и обновлять аналитику.
5. В `Finance.tsx` добавить заметную ссылку-карточку «Доход по тарифам бота →», чтобы владелец не искал.

**Альтернатива, если владелец хочет всё в «Финансах»**

- 4-я вкладка `Тарифы и доход` в `Finance.tsx`.
- Обязательный баннер «Источник: Bedolaga Bot; не смешивается с ручным реестром».
- Не объединять итоги с `fin_transactions`.
- Компоненты вынести в `web/frontend/src/components/bedolaga/Revenue*`, чтобы не раздувать `Finance.tsx`.

### 5.4 Страница `/bedolaga/revenue`

**Шапка**

- Заголовок «Доход по тарифам».
- Подзаголовок «Данные Bedolaga Bot · обновлено <время>».
- Бейдж источника: `Bot Web API` / `+ БД бота` / `только транзакции`.
- Кнопка обновления.

**Управление**

- Селектор месяца (`YYYY-MM`).
- Глубина истории: 6 / 12 месяцев.
- Переключатель `Кассовый | Начислительный`.
- Кнопка `Экспорт CSV`.

**KPI-карточки**

1. `MRR (100% оплата)` — сумма + `lower bound`, если покрытие <100%.
2. `Ожидаемо в следующем месяце` — касса + число платежей.
3. `Оплачено вперёд` — остаток уже оплаченного.
4. `Начислено за месяц` — accrual.
5. `Получено за месяц` — факт.
6. `Активных платных` — клиенты/подписки, trial отдельно.

**Покрытие цен**

- Полоса/индикатор `97.7%` и список тарифов с неизвестной ценой.
- Клик по тарифу — фильтр таблицы.

**Таблица по тарифам**

Колонки:

`Тариф | Клиенты (платные/trial) | Доля | Цена/30 дн. | Источник цены | MRR | Оплачено вперёд | Ожидаемо в след. месяце | Без цены`

- Сортировка по MRR/клиентам.
- Футер с итогами.
- Бейдж `Прайс` / `Факт` / `Вручную` / `Нет цены`.
- Строка `Не определён` и `Trial` отдельно.

**График динамики**

- Recharts (уже есть в проекте): `ComposedChart`.
- X — месяцы, Y — рубли.
- Ряды: фактическая касса (bar) и начислительный доход (line) для текущего/будущего; прошлые — только факт.
- Легенда «Факт / Прогноз / Оценка».
- Tooltip: суммы, число платежей, покрытие.

**Календарь/таймлайн следующего месяца**

- Сетка по дням с суммой и количеством платежей.
- Ниже список ближайших платежей (top 50): дата, клиент, тариф, сумма, `авто`.
- Клик по клиенту — карточка.
- Если `basis=renewal` — подписи «по окончанию», иначе «по списанию».

**Предупреждения**

- Баннер сверху, если `partial`, `price_unknown`, `price_sources_disagree`,
  `autopay_balance_unaccounted`.
- Не скрывать предупреждения в tooltip.

**Пустые состояния**

- Бот не настроен → «Интеграция Bedolaga не настроена» + ссылка в Настройки.
- Нет транзакций → «Нет данных о платежах за период», таблица тарифов всё равно показывается.
- Все цены неизвестны → «Недостаточно данных для денежных сумм», показывать клиентов и покрытие 0%.

### 5.5 Маршруты, навигация, i18n

- `web/frontend/src/App.tsx`: lazy import `BedolagaRevenue`, route `/bedolaga/revenue`.
- `web/frontend/src/config/navigation.ts`: пункт «Доход по тарифам» в группе Bedolaga после «Тарифы», иконка `TrendingUp`/`Wallet`.
- `web/frontend/src/locales/ru/translation.json` и `en/translation.json`: новые ключи.
- Ключи (минимум):
  - `bedolaga.customers.tariff`, `tariffUnknown`, `tariffFree`, `filterTariff`, `allTariffs`, `noTariff`, `pricePerMonth`;
  - `bedolaga.customerDetail.tariffPrice`, `paidUntil`, `daysLeft`, `paidTotal`, `paidForward`, `nextPayment`, `autopayCharge`, `financeUnavailable`;
  - `bedolaga.revenue.title`, `subtitle`, `kpi.*`, `table.*`, `chart.*`, `warnings.*`, `empty.*`.
- Не хардкодить русский текст в новых компонентах, кроме уже существующих мест.

---

## 6. Эпики и задачи

### MVP

#### E1. Backend: аналитическое ядро

**T1.1 — Модуль `web/backend/core/bedolaga_analytics.py`**

- Нормализация имён тарифов.
- Парсер описаний платежей.
- Построение каталога цен из транзакций.
- Опциональное чтение цен из `bot_db` с таймаутом и circuit breaker.
- Выбор активной/первичной подписки.
- Формулы F1–F15.
- Таймзона MSK, копейки.
- Кэш снимка и single-flight.

**Зависимости:** нет.
**Приёмка:** юнит-тесты на фикстурах; функции чистые, без FastAPI; нет запросов к БД бота, если `BOT_DB_*` пуст.
**Тесты:** `test_bedolaga_analytics.py`.

**T1.2 — Сбор данных и пагинация**

- `fetch_all_users()` — 200 на страницу, 2 запроса для 277.
- `fetch_all_transactions()` — 100 на страницу, 10 запросов для 996, concurrency ≤4.
- `fetch_full_stats()` — 1 запрос.
- Partial-режим при сбое страниц.
- Лимит времени и предупреждения.

**Зависимости:** T1.1.
**Приёмка:** на моках 277/996 проходят все страницы; при падении одной страницы — `partial=true`, остальные данные есть.
**Тесты:** unit с моками.

#### E2. Backend: API аналитики

**T2.1 — `web/backend/api/v1/bedolaga/analytics.py`**

- 4 эндпоинта из раздела 4.
- Auth, валидация `month`/`basis`, коды ошибок.
- Метаданные `generated_at`, `as_of`, `partial`, `warnings`, `sources`.

**Зависимости:** T1.1, T1.2.
**Приёмка:** контракты совпадают с разделом 4; 503/502/404/400 как описано.
**Тесты:** `test_bedolaga_analytics_api.py`.

**T2.2 — Подключение роутера**

- `web/backend/api/v1/bedolaga/__init__.py`: импорт и `include_router(..., prefix="/analytics")`.

**Зависимости:** T2.1.
**Приёмка:** `/api/bedolaga/analytics/overview` доступен, старые роуты не сломаны.
**Тесты:** smoke в API-тестах.

**T2.3 — Аддитивные изменения `customers.py`**

- `tariff_id`, `tariff_missing`, `sort=tariff`.
- Локальная фильтрация/сортировка, ключ кэша.
- Нормализация `subscription` из `subscriptions[]`.

**Зависимости:** T1.1 (нормализация).
**Приёмка:** фильтр по тарифу возвращает корректный `total`; старые запросы без параметров дают прежний результат.
**Тесты:** расширить тесты customers (если есть) или добавить API-тест.

#### E3. Frontend: типы и список клиентов

**T3.1 — `web/frontend/src/api/bedolaga.ts`**

- Исправить `BedolagaUser`:
  - `tariff_id/tariff_name` перенести внутрь `subscription`;
  - добавить `subscriptions?: BedolagaSubscription[]`;
  - добавить `email`, `referral_code`, `referred_by_id`.
- Добавить типы аналитики: `BedolagaAnalyticsTariffs`, `BedolagaRevenueOverview`,
  `BedolagaForecast`, `BedolagaCustomerFinance`.
- Добавить методы:
  - `getAnalyticsTariffs(params)`;
  - `getAnalyticsOverview(params)`;
  - `getAnalyticsForecast(params)`;
  - `getCustomerFinance(userId, params)`.
- Сохранить обратную совместимость: старые поля можно оставить optional, но новые компоненты используют вложенные.

**Зависимости:** T2.1/T2.2 (контракты).
**Приёмка:** `npm run typecheck` проходит.
**Тесты:** typecheck; при наличии — unit.

**T3.2 — `BedolagaCustomers.tsx`**

- Колонка «Тариф» + цена.
- Фильтр по тарифу, «Без тарифа».
- Сортировка `tariff`.
- CSV-колонки.
- Мобильная строка тарифа.
- Skeleton/empty/error.

**Зависимости:** T3.1, T2.3.
**Приёмка:** на проде у 133 платных клиентов виден тариф; у остальных — `—`/«Не определён»; фильтр и CSV работают.
**Тесты:** typecheck, build, ручная проверка.

**T3.3 — i18n списка**

- Ключи в `ru/en`.
**Зависимости:** T3.2.
**Приёмка:** нет хардкода новых подписей.

#### E4. Frontend: карточка клиента

**T4.1 — Исправить блок тарифа**

- `BedolagaCustomerDetail.tsx`: читать `sub?.tariff_name`, fallback на `subscriptions[]`.
- Убрать зависимость от `user.tariff_name`.

**Зависимости:** T3.1.
**Приёмка:** тариф отображается у клиентов, где API отдаёт его внутри `subscription`.

**T4.2 — Тариф в блоке «Информация»**

- Новая строка `InfoRow` «Тариф».
- Значение: название или «Не определён».

**Зависимости:** T4.1.
**Приёмка:** владелец видит тариф в блоке «Информация» без перехода в другие блоки.

**T4.3 — Карточка «Финансы клиента»**

- Запрос `/analytics/customers/{id}`.
- Цена/период, оплачено до, дней осталось, всего оплатил, оплачено вперёд, следующая оплата, дата списания.
- Fallback при ошибке.

**Зависимости:** T2.1, T3.1.
**Приёмка:** данные совпадают с транзакциями и подпиской; при недоступности аналитики страница не падает.

#### E5. Frontend: страница «Доход по тарифам»

**T5.1 — Роут и навигация**

- `App.tsx`, `navigation.ts`, lazy import.
**Зависимости:** T2.1.
**Приёмка:** `/bedolaga/revenue` открывается, пункт меню активен.

**T5.2 — KPI и покрытие**

- 6 KPI-карточек, индикатор покрытия, предупреждения.
**Зависимости:** T5.1, T3.1.
**Приёмка:** числа соответствуют `/analytics/overview`; unknown не показан как 0.

**T5.3 — Таблица по тарифам**

- Колонки из 5.4, сортировка, футер, бейджи источника.
**Зависимости:** T5.2.
**Приёмка:** сумма строк MRR равна итогу; trial/unknown отдельно.

**T5.4 — График и календарь**

- Recharts `ComposedChart`; календарь следующего месяца; список ближайших платежей.
- Переключатель `Кассовый/Начислительный`.
**Зависимости:** T5.2, `/analytics/forecast`.
**Приёмка:** переключатель меняет подписи и данные; прошлые месяцы не показывают ложный accrual.

**T5.5 — CSV и пустые состояния**

- Экспорт таблицы и прогноза.
- Empty/error/loading.
**Зависимости:** T5.3, T5.4.
**Приёмка:** CSV открывается в Excel (BOM, разделитель `;` или `,` — как в проекте).

**T5.6 — Ссылка из `Finance.tsx`**

- Карточка/кнопка «Доход по тарифам бота →».
**Зависимости:** T5.1.
**Приёмка:** переход работает, ручной реестр не изменён.

#### E6. Документация и проверка

**T6.1 — `docs/CODEBASE_INDEX.md`**

Обновить:

- §1.20: без изменений контрактов, но отметить, что `/tariffs` — БД-каталог, не источник аналитики.
- §1.21: новые query-параметры `tariff_id`, `tariff_missing`, `sort=tariff`.
- Новый §1.25 `api/v1/bedolaga/analytics.py` — 4 эндпоинта, параметры, форма ответа, кэш.
- §3.15 `bedolaga.ts`: новые типы и методы; исправить `BedolagaUser`.
- §5.1: маршрут `/bedolaga/revenue`.
- Добавить `core/bedolaga_analytics.py` в раздел core-модулей (сигнатуры, TTL).

**T6.2 — Проверки**

- `cd web/backend && python -m pytest -q`.
- `cd web/frontend && npm run typecheck && npm run build`.
- Ручная проверка на проде (read-only):
  - `/users` → total 277;
  - `/stats/full` → paid 133, active 136, trial 3;
  - `/transactions` → total 996;
  - аналитика: `clients_with_paid` = 133, `trial` = 3, `mrr_unknown_subscriptions` объяснён.
- Проверить, что время ответа холодного снимка ≤15 c, тёплого ≤1 c.

### Этап 2

| ID | Задача | Зачем |
|----|--------|-------|
| S1 | Таблица/JSON ручных override-цен + UI в `BedolagaTariffs.tsx` | Бесплатные тарифы, спорные цены, аварийный режим |
| S2 | Ежедневные снимки подписок в CMS | Точная история, churn, прогноз vs факт |
| S3 | Точный коэффициент продления по снимкам/событиям | Заменить `renewal_proxy` |
| S4 | Включение БД бота: UFW, env, мониторинг таймаутов | Точный прайс-лист |
| S5 | Алерты: покрытие цен <90%, расхождение источников >10%, всплеск unknown | Контроль качества данных |
| S6 | Фоновый пересчёт снимка (cron/worker) | Мгновенная выдача без холодного расчёта |
| S7 | Экспорт персональных финансов и прогноза в CSV/XLSX | Бухгалтерия |

---

## 7. Риски и открытые вопросы

### 7.1 Риски

| Риск | Влияние | Меры |
|------|---------|------|
| Нет цены у части тарифов | MRR занижен, покрытие <100% | `price_known`, `mrr_lower_bound`, покрытие, список unknown |
| Транзакционная цена ниже прайса из-за промо | MRR выглядит ниже реального прайса | `price_kind=realized`, бейдж, warning при расхождении с БД |
| Парсер описаний сломается после обновления бота | Цены пропадут | Юнит-тесты на шаблоны, warning `price_unknown`, fallback на БД/override |
| Новый тариф без покупок | Цена неизвестна | Честный unknown; override на Этапе 2 |
| Переименование тарифа | Старые наблюдения не сопоставляются | Нормализация, warning, приоритет `tariff_id` из текущих подписок |
| Автоплатёж с баланса | Касса завышена | Warning `autopay_balance_unaccounted`; не вычитать молча |
| Несколько подписок у клиента | Двойной счёт | Первичная для распределения, все для MRR; warning |
| Таймзоны и границы месяца | Суммы съезжают | MSK, тесты на 1-е/последнее число |
| 996 транзакций и 277 пользователей | Медленный холодный запрос | Батчи, concurrency, TTL, partial, single-flight |
| БД бота недоступна/медленная | Запрос висит | Таймаут 2 c, circuit breaker, disabled по умолчанию |
| Смешение с `fin_transactions` | Неверные итоги | Отдельная страница, явный источник, не суммировать |
| Утечка персональных финансов | Приватность | Только admin-auth, не логировать суммы/имена в info |

### 7.2 Решения владельца (зафиксированы 2026-11-21)

1. **Размещение:** отдельная страница `/bedolaga/revenue` (как в 5.3). Позже — связать/встроить с вкладкой «Финансы», но не смешивать итоги с `fin_transactions`.
2. **Источник цен:** использовать уже реализованное подтягивание из БД бота (`bot_db`); проверить и обеспечить динамичность (2.8). Транзакции — fallback/сверка. Ручной справочник не нужен в MVP.
3. **Тарифы:** учитывать **все** без исключения, включая бесплатные (`0 ₽`) и неактивные; `0` — валидная цена и может измениться в любую сторону, поэтому каталог пересчитывается при каждом обновлении, без «зашитых» нулей.

Осталось подтвердить (не блокирует старт, взять дефолты):

- Таймзона отчётности — по умолчанию `Europe/Moscow`.
- «Уже оплачено» — по умолчанию всё время, с разрезом за 12 месяцев.
- Кассовый прогноз — валовый (по списаниям), баланс не вычитается; в UI предупреждение.

---

## 8. Порядок выполнения и Definition of Done

### 8.1 Порядок

1. **Решения владельца получены (7.2)** — старт с E1.
2. **E1** — ядро + юнит-тесты.
3. **E2** — API + тесты; smoke на проде read-only.
4. **E3** — типы + список клиентов.
5. **E4** — карточка клиента.
6. **E5** — страница дохода.
7. **E6** — индекс, проверки, ручной прогон.
8. Только после этого — обсуждение Этапа 2.

### 8.2 Команды проверки

```powershell
cd web/backend
python -m pytest -q

cd ..\frontend
npm run typecheck
npm run build
```

Если в проекте принят `npm run build:check` — использовать его.

### 8.3 Definition of Done

- [ ] Код реализован, старые контракты не сломаны.
- [ ] `docs/CODEBASE_INDEX.md` обновлён по T6.1: новые эндпоинты, параметры, типы, методы, маршрут, core-модуль.
- [ ] `python -m pytest -q` в `web/backend` — зелёный.
- [ ] `npm run typecheck` и `npm run build` в `web/frontend` — зелёные.
- [ ] Ручная проверка на проде (read-only): 277 users, 133 paid, 3 trial, 996 transactions.
- [ ] В «Клиентах» есть колонка «Тариф», фильтр, сортировка, CSV, мобильная строка.
- [ ] В карточке клиента тариф есть в блоке «Информация»; финансы клиента отображаются.
- [ ] На `/bedolaga/revenue` есть KPI, таблица, график, прогноз, переключатель, покрытие и предупреждения.
- [ ] Неизвестная цена не показана как 0; есть `price_known`, `price_source`, `mrr_lower_bound`.
- [ ] Нет записи в БД бота и нет изменений бота/Remnawave.
- [ ] Секреты не попали в код/логи/документацию.
- [ ] Коммит — только по явной команде владельца.

---

## 9. Чек-лист приёмки (краткий)

- [ ] В списке клиентов у платного клиента виден тариф и цена/мес.
- [ ] Фильтр «Тариф» и «Без тарифа» работают; сортировка не ломает пагинацию.
- [ ] CSV содержит тариф и цену.
- [ ] В карточке клиента тариф есть в «Информации».
- [ ] В карточке видны: цена/период, оплачено до, дней осталось, всего оплатил, оплачено вперёд, следующая оплата.
- [ ] `/bedolaga/revenue` показывает MRR, прогноз на следующий месяц, оплачено вперёд, начисление, факт, активных платных.
- [ ] Таблица по тарифам сходится с итогами.
- [ ] Покрытие цен и unknown-тарифы видны.
- [ ] Переключатель «Кассовый/Начислительный» меняет данные и подписи.
- [ ] Данные обновляются автоматически; ручного ввода нет.
- [ ] Все предупреждения отображаются, а не скрываются.
- [ ] Индекс и тесты обновлены; сборка проходит.
