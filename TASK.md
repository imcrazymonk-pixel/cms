# TASK — Саппорт: состояние и продолжение (хендофф)

**Обновлено:** 2026-11-28
**Состояние:** Этап A, **Этап B** (B1–B4) и **Этап C** (C1–C5) закрыты полностью. Этап D в работе: сделан deep-карточка на данных Bedolaga и редактор приветствия бота.
**Следующий шаг:** продолжить Этап D — медиа-лимиты из настроек, вкладка «Поддержка», активация CMS-бота/cutover, решение по истории.
**Планы:**
- `docs/plans/2026-11-28-support-stage-b.md` — Этап B (выполнен);
- `docs/plans/2026-11-28-support-stage-c.md` — Этап C (выполнен);
- `docs/plans/2026-11-28-support-bot-activation-and-history.md` — активация бота и история (в работе).
**Проверки на 2026-11-28:** `pytest` 726 passed; `tsc` 0 ошибок; `npm run build` успешно.

---

## 1. Что сделано

### Этап A (очередь + защиты)
- Фильтры/`total`/динамические поллеры, назначение диалога, цитаты.
- `seen_at` + 409 `CLIENT_WROTE`, идемпотентность `client_msg_id`, lease 15 мин + `LOCKED_BY_OTHER`/`force`.
- ACL и TTL вложений, `priority_synced`, health с реальной БД.
- Миграция `005-support-reply-idempotency.sql`.

### Этап B
- **B1a:** `006-support-ai-kb.sql` (KB-поля, `tsvector`+GIN, `support_qa_pair`, `support_operator_draft`, расширенные статусы/индексы), 18 ключей `support_ai_*`, `SupportSettings.ai_*` + generic-applier, ADR-007, docs-history → 007.
- **B1b:** пакет `core/support/ai/` (`config`, `provider`, `prompt`, `repair`, `chunks`, `links`, `scrub`, `outbound`, `gate`, `responder`, `worker`, `examples`, `public`); `store/ai.py`; API `suggestions.py` + `assistant.py`; `settings_values.py`; WS-кадр `ai_suggestion`; hot reload через `SUPPORT_TRIGGER_KEYS`.
- **B2:** `kb/fts.py`, `store/kb.py`, `api/v1/support/kb.py` (11 эндпоинтов), `store/qa.py`, `feedback.py`, `imports/` (text/result.json/cluster/runner), `store/jobs.py`, `imports.py`.
- **B3a:** `api/support.ts` (+24 метода и типы), страница `/support/kb`, `components/kb/{KbList,KbEditor,CandidateList,ImportPanel}.tsx`.
- **B3b:** страница `/support/ai` + `components/assistant/{ModeCard,PauseCard,ParamsCard,StatsCard,TryPanel}.tsx`; `components/AiDraftCard.tsx` в треде; WS `ai_suggestion` → инвалидация; «Править» переносит текст в композер через явный `suggestionEditText`; deep-link `?from=support_ai`.
- **B3b-0:** `GET /conversations/{id}` отдаёт `suggestion` в публичной форме (`core/support/ai/public.py`: `level`, `gate:{action,reason}`, `used` без `chunk`).
- **B4:** `CODEBASE_INDEX.md` (§1.26, §3.16, §3.16a, §5.1), `CHANGELOG_CMS.md`, `AI-SUPPORT.md` §1a, планы завершения и Этапа B.

### Проверки на момент фиксации
```
cd web/backend; python -m pytest tests -q   → 726 passed
cd web/frontend; npx tsc --noEmit           → 0 ошибок
cd web/frontend; npm run build              → успешно (dist обновлён)
```

---

## 2. Что осталось

### Этап C — Фаза 4 ✅ (выполнен 2026-11-28, C1–C5)
Полный план и статус: **`docs/plans/2026-11-28-support-stage-c.md`** (`pytest` 722, `tsc`/`build` зелёные).
- **C1** — миграция `008-support-stage-c.sql` (`support_message.author_id`), заметки о клиенте, присутствие, аудит действий.
- **C2** — SLA: политики по приоритетам редактируются, вотчер раз в минуту, одно уведомление на событие (≤5 за проход), кадр WS `sla_alert`, дубль в staff-группу форума; экран `/support/sla`.
- **C3** — шаблоны ответов: CRUD, `/shortcut`, счётчик `uses`, вставка в композер кнопкой и слэш-подсказкой; экран `/support/templates`.
- **C4** — присутствие `viewing|typing` (TTL 120 с, троттлинг 5 с, WS `presence`) в треде, аудит и экран `/support/team` (операторы + журнал).
- **C5** — аналитика `/support/analytics`: объёмы, медиана/P90 первого ответа только по людям, каналы/приоритеты, нагрузка операторов, метрики ИИ.

### Этап D — полировка (в работе; план — `docs/plans/2026-11-28-support-bot-activation-and-history.md`)

Сделано:
1. [x] Deep-карточка на **существующих данных Bedolaga**: `subscription_url`, `tariff_name`, `device_limit/count`, `traffic_*_gb` в `bedolaga_customer.py` и `CustomerCard`; мёртвый запрос `/api/users?search=` (это пользователи CMS, не Remnawave) удалён из `BedolagaCustomerDetail`.
2. [x] **Редактор приветствия бота**: `support_tg_greeting` (textarea, env `SUPPORT_TG_GREETING`), `TelegramPoller(greeting=...)`, hot reload через `SUPPORT_TRIGGER_KEYS`; тесты 726.
3. [x] План активации бота и истории — `docs/plans/2026-11-28-support-bot-activation-and-history.md`.

Осталось:
4. [ ] Медиа-лимиты из настроек (`SupportService.upload_max_size` всегда `None`).
5. [ ] Вкладка «Поддержка» в настройках.
6. [ ] Активация CMS-бота и cutover (D1): ключи `support_tg_*`, остановить `vpn_support_bot`, смоук.
7. [ ] История (D3): **решение по приватности** — mapping-only (24 пары `topics.json`) или тела через MTProto/Desktop export; добавить `is_backfill` в `record_outbound`.
8. [ ] Остановка/удаление старого Node-бота `vpn_support_bot` (это не `ai-support`; `ai-support` в проде не развёрнут) — после смоука, см. план.

### Этап E — публичный чат (решение владельца, не начат)
Виджет чата на `hexaveil.xyz` (канал `web`) или остаёмся на Telegram-ссылке.

### Не закрытый смоук Этапа B (нужен реальный ключ ИИ и живой канал)
`shadow` без карточки; `suggest` → «Отправить/Править/Отклонить»; пауза; песочница; автоответ в `auto`. См. `docs/plans/2026-11-28-support-stage-b.md` §8.

---

## 3. Известные долги и отклонения

| # | Долг | Где |
|---|------|-----|
| 1 | В `support_kb_doc` нет `created_at`; store отдаёт `updated_at` как прокси. Добавить в 006 идемпотентно или миграцией 007. | `db/postgres/migrations/006-support-ai-kb.sql`, `store/kb.py` |
| 2 | `dry_run` импорта не считает `would_skip` по существующим `external_key` (не ходит в БД). | `imports/runner.py` |
| 3 | Миграции 005/006 не применялись на живой БД: `psql` и Docker были недоступны. Нужен прогон дважды на тестовой БД. | `db/postgres/migrations/` |
| 4 | Импорт принимает только JSON-тело (`payload`), файл читает фронт. | `api/v1/support/imports.py` |
| 5 | `core/support/imports/` назван так, а не `import/` — `import` зарезервирован в Python. | — |
| 6 | Компоненты КБ лежат в `src/components/kb/`, а страницы ИИ — в `pages/support/components/assistant/`; расположение исторически неоднородно. | `web/frontend/src` |
| 7 | `user`-код `INTEGRATION_TEST_IDS` для «ИИ / Саппорт» не добавлен — тест-эндпоинта нет. | `pages/Settings.tsx` |
| 8 | Присутствие и аудит проверены на фейковой `AsyncSession`, без живой БД: SQL-heartbeat/TTL и запись `support_audit_log` на реальном PostgreSQL не прогонялись. | `tests/test_support_presence.py`, `tests/test_support_audit.py` |
| 9 | `conversations_resolved` считается по `updated_at` диалогов в статусе `resolved|closed` — отдельного `resolved_at` в `support_conversation` нет, поэтому повторное изменение «решённого» диалога сдвигает дату. | `store/analytics.py` |

Закрыто в B: shadow-предложки скрываются фронтом (`AiDraftCard`), `suggestion` в детали диалога приведён к публичной форме.

---

## 4. Инварианты, которые нельзя нарушать

1. Единственный выход клиенту — `Outbox.send` (+ `check_window`); автоответ ИИ пишется `author='bot'`, ответ оператора — `author='agent'`.
2. `api_key` не появляется в API-ответах, логах и текстах исключений.
3. Поиск ИИ и операторов видит только `status='published'`.
4. FTS — только PostgreSQL `tsvector`/`websearch_to_tsquery`/`ts_rank_cd`.
5. Права/роли не вводим: все админы CMS = операторы.
6. Прод-конфиги руками не правим; изменения только в репозитории.

---

## 5. Быстрые команды

```powershell
cd web/backend; python -m pytest tests -q
cd web/frontend; npx tsc --noEmit
cd web/frontend; npm run build
```

Апстрим-референс: `ai-support/` (v3.0.0, `ee05237`), сводка отличий — `docs/AI-SUPPORT.md` §1a.
