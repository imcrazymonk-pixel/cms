# ADR-007: Саппорт — ИИ-ворота, FTS и нумерация миграции

## Status

Accepted

## Date

2026-11-28

## Context

Этап B добавляет в CMS ИИ-ассистента и базу знаний. Апстрим `ai-support` v3.0.0
написан на Node/SQLite: полнотекст через FTS5 и `bm25`, режимы `off/shadow/suggest/auto`
и порядок «ворот» перед автоответом, а также отдельная нумерация миграций. CMS работает
на PostgreSQL и едином миграционном проходе из lifespan (`ensure_support_schema`), поэтому
прямой перенос невозможен. Нужно зафиксировать четыре решения, от которых зависит вся
последующая нарезка B2–B4.

## Decision

1. **Полнотекст — PostgreSQL `tsvector` + GIN, не FTS5/bm25.**
   Основной индекс статей:
   `GIN (to_tsvector('russian', coalesce(title, '') || ' ' || coalesce(body, '')))`.
   Используется именно **двухаргументная** форма `to_tsvector(regconfig, text)` — она
   `IMMUTABLE` и допустима в индексе; одноаргументная `STABLE` — нет. Поисковый предикат
   (в B2) — `to_tsvector(...) @@ websearch_to_tsquery('russian', :q)`, сортировка —
   `ts_rank_cd(...) DESC, updated_at DESC`. `websearch_to_tsquery` выбран вместо
   `plainto_tsquery`, потому что не падает на кавычках и `|` из пользовательского ввода.
   `CREATE INDEX CONCURRENTLY`, FTS5, `bm25` и `PRAGMA` не используются: миграция
   идёт одним транзакционным проходом через сплиттер `core/support/schema.py`.

2. **Порядок ИИ-ворот и трактовка `require_kb` × профиль.**
   Гейт (`gate.decide()`, порт `ai-support/src/ai/gate.ts`) проверяет условия строго по
   порядку: режим (`off` → `skip`) → наличие ключа (нет → эффективный `off`) → пауза →
   handoff/`needs_human` → пустой ответ → `require_kb` × профиль клиента → уверенность
   (`min_confidence`) → чувствительные темы («верните деньги» и т.п.) → тон → окно ответа →
   лимит `ai_auto_per_hour` → повторяющийся clarifying-вопрос. Первое сработавшее условие
   определяет `gate_action` (`auto` | `suggest` | `shadow` | `skip`) и `gate_reason`;
   `require_kb=true` при отсутствии опубликованной опоры понижает действие до `suggest`,
   но не блокирует генерацию полностью. `support_ai_api_key` пустой ⇒ эффективный режим
   всегда `off`, `has_key=false`, автоответы невозможны.

3. **`shadow` — обязательный этап включения.**
   Режим `shadow` генерирует предложку и пишет её в `support_ai_suggestion`, но не
   показывает в треде и не отправляет клиенту: результат виден только в `/support/ai`
   (активность и статистика). Это позволяет проверить качество и ворота на живом потоке
   до `suggest`/`auto`. `shadow` не меняет видимость для клиента и не расходует лимит
   автоответов (`gate_action='auto'` не выставляется).

4. **Миграция 006 занята саппортом, docs-history сдвигается на 007.**
   `docs/plans/2026-11-15-changelog-history-editable.md` резервировал `006` под
   `docs-history`, но файла `006-docs-history.sql` в репозитории нет, а саппорт-схема
   накатывается автоматически на старте. Нумерация кода, который реально едет, идёт
   первой: `db/postgres/migrations/006-support-ai-kb.sql` — саппорт, docs-history —
   `007-docs-history.sql`. Все три упоминания `006` в плане docs-history обновлены на
   `007` в том же изменении.

## Consequences

- В B2 поиск и ранжирование реализуются на `tsvector`/`ts_rank_cd`; сниппеты — через
  `ts_headline` при необходимости. Никакого SQLite-кода в CMS.
- `support_ai_suggestion.status` расширен до `pending|sent|edited|rejected|superseded`;
  частичный уникальный индекс `uq_support_ai_suggestion_pending` держит один `pending`
  на диалог после предварительной нормализации старых строк.
- `support_job` переведён на `status IN ('queued','running','done','error')` и
  `progress INTEGER`; `result` конвертируется в `JSONB` с защитой: при невалидном JSON
  в существующих данных колонка остаётся `TEXT` (идемпотентно перепроверяется).
- `support_kb_candidate.decided_by` остаётся `TEXT`, как в 004: тип не меняем, потому что
  это не требуется в B1, а `ALTER ... TYPE` по живых данным рискован. При необходимости
  ID-ссылка добавляется отдельной миграцией.
- Миграция 006 идемпотентна: `ADD COLUMN IF NOT EXISTS`, `CREATE ... IF NOT EXISTS`,
  `DO $$`-расширения CHECK и предварительная нормализация перед частичными индексами.
