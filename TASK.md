# TASK — Саппорт: состояние и продолжение (хендофф)

**Обновлено:** 2026-11-28
**Состояние:** Этап A, **Этап B** (B1–B4) и **Этап C** (C1–C5) закрыты полностью. Этап D: закрыты deep-карточка, редактор приветствия, медиа-лимиты, вкладка «Поддержка», mapping, `is_backfill` и импорт тел/медиа (1171 сообщение, 87 вложений). Остались прод-действия D-3/D-5 и решение по retention тел.
**Следующий шаг:** D-3 — активация CMS-бота и cutover по `docs/plans/2026-11-28-support-stage-d-remainder.md` §3, только после подтверждения владельца; затем D-5 (остановка старого бота) и, при отдельном решении, D-4c (тела истории).
**Планы:**
- `docs/plans/2026-11-28-support-stage-b.md` — Этап B (выполнен);
- `docs/plans/2026-11-28-support-stage-c.md` — Этап C (выполнен);
- `docs/plans/2026-11-28-support-bot-activation-and-history.md` — активация бота и история (D-3/D-5 ждут владельца);
- `docs/plans/2026-11-28-support-stage-d-remainder.md` — остаток D (D-1/D-2/D-4a/D-4b выполнены).
**Проверки на 2026-11-28:** `pytest` 776 passed; `tsc` 0 ошибок; `npm run build` успешно.

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
cd web/backend; python -m pytest tests -q   → 754 passed
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

### Этап D — полировка (D-1/D-2/D-4 закрыты; D-3/D-5 ждут владельца)

Сделано:
1. [x] Deep-карточка на **существующих данных Bedolaga**: `subscription_url`, `tariff_name`, `device_limit/count`, `traffic_*_gb` в `bedolaga_customer.py` и `CustomerCard`; мёртвый запрос `/api/users?search=` (это пользователи CMS, не Remnawave) удалён из `BedolagaCustomerDetail`.
2. [x] **Редактор приветствия бота**: `support_tg_greeting` (textarea, env `SUPPORT_TG_GREETING`), `TelegramPoller(greeting=...)`, hot reload через `SUPPORT_TRIGGER_KEYS`.
3. [x] План активации бота и истории — `docs/plans/2026-11-28-support-bot-activation-and-history.md`.
4. [x] План остатка Этапа D — `docs/plans/2026-11-28-support-stage-d-remainder.md` (D-1 … D-5).
5. [x] **D-1. Медиа-лимиты**: `support_media_max_mb` (1–50, дефолт 8, env `SUPPORT_MEDIA_MAX_MB`) → `SupportSettings.media_max_mb` → `init_support` выставляет `SupportService.upload_max_size`; `config-status.media_max_mb/upload_max_bytes`; подсказка и клиентская проверка в композере; hot reload.
6. [x] **D-2. Вкладка «Поддержка»**: `tab="support"` для всех `support_*`/`support_ai_*`, `TabsTrigger`/`TabsContent` в `Settings.tsx`, deep-link `support|support_ai`; миграция не нужна. Долг №7 закрыт как «by design».
7. [x] **D-4a. История mapping-only**: `tools/support_import_history.py` (`--dry-run` по умолчанию, `--apply`), 24 пары `topics.json` → `support_conversation` (`closed`), `fill_conversation_mapping` только NULL, тела не пишутся, Outbox не используется.
8. [x] **D-4b. `is_backfill`**: `record_outbound(..., is_backfill=False)` — INSERT колонки, при `True` не пишет `first_response_at`, `last_message_at=GREATEST`.

Осталось (прод/решение владельца):
9. [ ] **D-3. Активация CMS-бота (D1)** — в процессе: панельный `vpn_support_bot` остановлен (не удалён, бэкап `/home/kilo/support-bot-backup-20261128-174238/`), CMS настроен на тот же токен + staff `-1003994836554` + forum + SOCKS5 `hexaveil-socks`, mapping 24 пар импортирован. Починены `sql_text`, `CAST(:meta AS jsonb)` и nullable-`CAST` в `record_inbound`; API пересобран. Проверено: диалог `id=38` (`/start`), приветствие клиенту, тема `2285`, карточка клиента 200. Остался реальный смоук: сообщение→тема, ответ веба→клиент, ответ темы→веб.
10. [ ] **D-5. Остановка старого `vpn_support_bot`** (не `ai-support`) — только после смоука и недели наблюдения, с бэкапом `topics.json`/`.env`.
11. [x] **D-4c. Тела истории импортированы** из HTML-экспорта: 1171 сообщение (528 in / 643 out) и 87 вложений по 26 темам, `is_backfill=True`, без Outbox/повторной отправки. Имена диалогов обновлены из экспорта (`ФИО (@ник)`), `_private_subject` исправлен. Осталось: решение по retention (тела хранятся) и обновление текста приватности/ADR.

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
| 7 | ✅ Закрыто в D-2: у «ИИ / Саппорт» нет тест-эндпоинта, кнопка «Проверить» не рендерится (by design). | `pages/Settings.tsx` |
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
