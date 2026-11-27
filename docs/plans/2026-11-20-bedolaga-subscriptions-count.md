# TASK — «Подписки» в разделе Bedolaga = 133 (как в кабинете бота)

> Статус: **к реализации (финальная схема)**
> Дата: 2026-11-20

## Установленные факты

- Требуемое число в кабинете бота: **133** = активные **платные** подписки (триалы исключены).
- Прямой доступ CMS к БД бота локально недоступен: из контейнера `hexacms_api`
  порты 5433/5434 на `144.31.156.172` дают timeout. Попытка подключения к БД
  на каждом запросе стоит ~20 с — так делать нельзя.
- Bot Web API уже отдаёт нужное число по HTTP: `GET /stats/full` →
  `subscriptions.paid_subscriptions`. Проверено из контейнера:
  ```
  total_subscriptions  = 256
  active_subscriptions = 136
  trial_subscriptions  = 3
  paid_subscriptions   = 133   ← то, что нужно
  ```
  Латентность `/stats/full` ≈ 0.3 с.

## Решение

Считать «Подписки» из **Bot Web API `/stats/full` → `subscriptions.paid_subscriptions`**,
с кэшем 60 с. От доступа к БД бота в этой задаче отказаться (медленный timeout,
лишняя зависимость от UFW-правил).

### 1. `web/backend/api/v1/bedolaga/dashboard.py`

- Убрать импорт/использование `bot_db` и `get_subscription_counts`.
- В `get_overview`:
  ```python
  data = await proxy_request(bedolaga_client.get_overview)
  paid = await _paid_subscriptions_cached()   # int | None, TTL 60 c
  if paid is not None:
      data = dict(data or {})
      subs = dict(data.get("subscriptions") or {})
      subs["active"] = paid
      data["subscriptions"] = subs
  return data
  ```
- `_paid_subscriptions_cached()`:
  - module-level кэш `{"ts": monotonic, "value": int|None}`;
  - вызывает `bedolaga_client.get_full_stats()`, берёт
    `(full.get("subscriptions") or {}).get("paid_subscriptions")`;
  - при любой ошибке (httpx/`HTTPException`) возвращает `None` **и не ломает `/overview`**
    (fallback → ответ бота с `active=136`);
  - ошибки логирует `logger.warning` без traceback на каждый запрос (кэш не заполняем,
    но и не спамим — достаточно warning).
- `subscriptions.expired` не трогать.

### 2. `web/backend/core/bot_db.py`

Удалить добавленную ранее `get_subscription_counts()` (она больше не используется;
файл вернуть к состоянию без неё, не затрагивая прочие существующие изменения).

### 3. Тест `web/backend/tests/test_bedolaga_overview_subscriptions.py`

- Кейс override: `get_overview` → `{"users": {"total": 277}, "subscriptions": {"active": 136, "expired": 119}}`,
  `get_full_stats` → `{"subscriptions": {"paid_subscriptions": 133}}`;
  ожидаем `active == 133`, `expired == 119`, `users.total == 277`.
- Кейс fallback: `get_full_stats` бросает исключение ⇒ `active == 136`, `expired == 119`.
- Сбросить кэш между тестами (фикстура/`monkeypatch` на кэш-переменную).

### 4. `docs/CODEBASE_INDEX.md`

- `/api/bedolaga/overview`: `subscriptions.active` = `paid_subscriptions` из `/stats/full`
  (кэш 60 с, fallback — значение бота).
- Убрать упоминание `bot_db.get_subscription_counts`.

## Проверки

- `python -m pytest -q` из `web/backend`.
- Ручная проверка из контейнера (после реализации):
  ```
  docker exec hexacms_api python -c "... get_full_stats()['subscriptions']['paid_subscriptions'] ..."
  ```
  → 133.
- Перезапуск контейнера обязателен (код смонтирован, нужен рестарт процесса).

## Ограничения

- Бот, Remnawave, фронтенд, `/stats/full` как контракт — не менять.
- Без команды владельца не коммитить.
