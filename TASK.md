# TASK — Саппорт: состояние и продолжение (хендофф)

**Обновлено:** 2026-11-28
**Состояние:** Этап A закрыт. Этап B выполнен до B3a включительно (backend полностью, фронт KB).
**Продолжать с:** B3b (фронт ИИ) → B4 (доки/приёмка).
**Главный документ:** `docs/plans/2026-11-28-support-stage-b.md` — план Этапа B целиком (решения, контракты, нарезка, смоук). Читать его перед работой.

---

## 1. Что уже сделано

### Этап A (очередь + защиты)
- Фильтры/`total`/динамические поллеры, назначение диалога, цитаты.
- `seen_at` + 409 `CLIENT_WROTE`, идемпотентность `client_msg_id`, lease 15 мин + `LOCKED_BY_OTHER`/`force`.
- ACL и TTL вложений, `priority_synced`, health с реальной БД.
- Миграция `005-support-reply-idempotency.sql`.

### Этап B
- **B1a:** `006-support-ai-kb.sql` (KB-поля, `tsvector`+GIN, `support_qa_pair`, `support_operator_draft`, расширенные статусы/индексы), 18 ключей `support_ai_*`, `SupportSettings.ai_*` + generic-applier, ADR-007, docs-history → 007.
- **B1b:** пакет `core/support/ai/` — `config`, `provider`, `prompt`, `repair`, `chunks`, `links`, `scrub`, `outbound`, `gate`, `responder`, `worker`, `examples`; `store/ai.py` (suggestions, пауза `aiPause`, operator draft, stats); API `suggestions.py` + `assistant.py`; `settings_values.py`; WS-кадр `ai_suggestion`; hot reload через `SUPPORT_TRIGGER_KEYS`.
- **B2:** `kb/fts.py`, `store/kb.py`, `api/v1/support/kb.py` (11 эндпоинтов), `store/qa.py`, `feedback.py`, `imports/` (text/result.json/cluster/runner), `store/jobs.py`, `imports.py` API.
- **B3a:** `api/support.ts` (+24 метода и типы), страница `/support/kb`, компоненты `components/kb/{KbList,KbEditor,CandidateList,ImportPanel}.tsx`, билд `dist/`.

### Проверки на момент фиксации
```
cd web/backend; python -m pytest tests -q   → 661 passed
cd web/frontend; npx tsc --noEmit           → 0 ошибок
cd web/frontend; npm run build              → успешно (dist обновлён)
```

---

## 2. Что осталось

### B3b — фронт ИИ
1. `pages/support/Assistant.tsx` + `components/assistant/{ModeCard,PauseCard,ParamsCard,StatsCard,TryPanel}.tsx` по `docs/plans/2026-11-28-support-stage-b.md` §6.2.
2. `components/AiDraftCard.tsx` — в `MessageThread.tsx` над композером; данные из `GET /conversations/{id}` → `suggestion`; кнопки «Отправить/Править/Отклонить», `used[]`, «Почему так?», `operator_note`.
3. `lib/supportSocket.ts` — кадр `ai_suggestion` → инвалидация треда/списка.
4. `App.tsx` — заменить `SupportPlaceholder` для `/support/ai`.
5. `pages/Settings.tsx` — убедиться, что группа «ИИ / Саппорт» рендерится (включая `type="secret"`).
6. Проверка: `npx tsc --noEmit`, `npm run build`.

### B4 — приёмка и доки
1. Финальный прогон: `pytest tests -q`, `tsc --noEmit`, `npm run build`.
2. `docs/CODEBASE_INDEX.md`: фронтовые методы/типы `api/support.ts`, `AiDraftCard`, страницы `Kb`/`Assistant`, сокет-кадр.
3. `docs/CHANGELOG_CMS.md`: запись «Саппорт: Этап B — ИИ-помощник и база знаний».
4. `docs/AI-SUPPORT.md` §1a: пометка «портировано в CMS: gate/scrub/links/repair/chunks/examples; FTS→tsvector; interface-kb не переносим».
5. `docs/plans/2026-11-28-support-completion.md`: Этап B — выполнен.
6. Смоук-лист из плана §8 (нужны реальный ключ ИИ и живой канал).

---

## 3. Известные долги и отклонения

| # | Долг | Где |
|---|------|-----|
| 1 | В `support_kb_doc` нет `created_at`; store отдаёт `updated_at` как прокси. Добавить в 006 идемпотентно или миграцией 007. | `db/postgres/migrations/006-support-ai-kb.sql`, `store/kb.py` |
| 2 | `dry_run` импорта не считает `would_skip` по существующим `external_key` (не ходит в БД). | `imports/runner.py` |
| 3 | Миграции 005/006 не применялись на живой БД: `psql` и Docker были недоступны. Проверены статически и сплиттером. Нужен прогон дважды на тестовой БД. | `db/postgres/migrations/` |
| 4 | `shadow`-предложки отдаются в `GET /conversations/{id}`; фронт обязан их скрывать (не реализовано до B3b). | `AiDraftCard` |
| 5 | Импорт принимает только JSON-тело (`payload`), файл читает фронт. | `api/v1/support/imports.py` |
| 6 | `core/support/imports/` назван так, а не `import/` — `import` зарезервирован в Python. | — |

---

## 4. Инварианты, которые нельзя нарушать

1. Единственный выход клиенту — `Outbox.send` (+ `check_window`); автоответ ИИ пишется `author='bot'`, ответ оператора — `author='agent'`.
2. `api_key` не появляется в API-ответах, логах и текстах исключений.
3. Поиск ИИ и операторов видит только `status='published'`.
4. FTS — только PostgreSQL `tsvector`/`websearch_to_tsquery`/`ts_rank_cd`, никакого FTS5/`bm25`.
5. Права/роли не вводим: все админы CMS = операторы (решение владельца).
6. Прод-конфиги руками не правим; изменения только в репозитории.

---

## 5. Быстрые команды

```powershell
cd web/backend; python -m pytest tests -q
cd web/frontend; npx tsc --noEmit
cd web/frontend; npm run build
```

Апстрим-референс: `ai-support/` (v3.0.0, `ee05237`), сводка отличий — `docs/AI-SUPPORT.md` §1a.
