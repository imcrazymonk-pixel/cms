-- Support AI + knowledge base — Этап B (миграция 006).
-- Идемпотентный DDL поверх 004/005: ADD COLUMN IF NOT EXISTS, CREATE ... IF NOT EXISTS,
-- расширение CHECK через DO $$. Повторный запуск безопасен.
-- Применяется из lifespan через ensure_support_schema() (core/support/schema.py).
-- Полнотекст — PostgreSQL tsvector + GIN (НЕ FTS5/bm25); CREATE INDEX CONCURRENTLY запрещён.

-- ============================================
-- support_kb_doc — статьи базы знаний
-- 004 уже создала: id, source, ext_id, title, body, updated_at, UNIQUE(source, ext_id)
-- ============================================
ALTER TABLE support_kb_doc
    ADD COLUMN IF NOT EXISTS slug         TEXT,
    ADD COLUMN IF NOT EXISTS status       TEXT        NOT NULL DEFAULT 'draft',
    ADD COLUMN IF NOT EXISTS version      INTEGER     NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS tags         TEXT[]      NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS updated_by   BIGINT,
    ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS archived_at  TIMESTAMPTZ;

ALTER TABLE support_kb_doc ALTER COLUMN source SET DEFAULT 'manual';

-- Нормализация перед уникальным индексом: пустые слаги → NULL, дубли → суффикс id
UPDATE support_kb_doc
   SET slug = NULL
 WHERE slug IS NOT NULL AND btrim(slug) = '';

UPDATE support_kb_doc d
   SET slug = d.slug || '-' || d.id
 WHERE d.slug IS NOT NULL
   AND d.id <> (SELECT min(x.id) FROM support_kb_doc x WHERE x.slug = d.slug);

-- CHECK status IN ('draft','published','archived') — идемпотентно
DO $$
DECLARE
    con record;
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conrelid = 'support_kb_doc'::regclass
           AND contype = 'c'
           AND pg_get_constraintdef(oid) LIKE '%status%'
           AND pg_get_constraintdef(oid) LIKE '%archived%'
    ) THEN
        FOR con IN
            SELECT conname
              FROM pg_constraint
             WHERE conrelid = 'support_kb_doc'::regclass
               AND contype = 'c'
               AND pg_get_constraintdef(oid) LIKE '%status%'
        LOOP
            EXECUTE format('ALTER TABLE support_kb_doc DROP CONSTRAINT %I', con.conname);
        END LOOP;
        ALTER TABLE support_kb_doc
            ADD CONSTRAINT support_kb_doc_status_check
            CHECK (status IN ('draft', 'published', 'archived'));
    END IF;
END $$;

-- Полнотекстовый индекс: двухаргументная to_tsvector(regconfig, text) IMMUTABLE
CREATE INDEX IF NOT EXISTS idx_support_kb_doc_fts
    ON support_kb_doc
    USING GIN (to_tsvector('russian', coalesce(title, '') || ' ' || coalesce(body, '')));

CREATE INDEX IF NOT EXISTS idx_support_kb_doc_status
    ON support_kb_doc (status, updated_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_support_kb_doc_slug
    ON support_kb_doc (slug)
    WHERE slug IS NOT NULL;

-- ============================================
-- support_ai_suggestion — предложки и автоответы
-- 004 уже создала: id, conversation_id, message_id, text, confidence, needs_human,
--                  reason, model, sources, status, decided_at, created_at
-- ============================================
ALTER TABLE support_ai_suggestion
    ADD COLUMN IF NOT EXISTS final_text        TEXT,
    ADD COLUMN IF NOT EXISTS answer_message_id BIGINT
        REFERENCES support_message(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS operator_note     TEXT,
    ADD COLUMN IF NOT EXISTS gate_action       TEXT,
    ADD COLUMN IF NOT EXISTS gate_reason       TEXT,
    ADD COLUMN IF NOT EXISTS latency_ms        INTEGER,
    ADD COLUMN IF NOT EXISTS tokens_in         INTEGER,
    ADD COLUMN IF NOT EXISTS tokens_out        INTEGER,
    ADD COLUMN IF NOT EXISTS used              JSONB NOT NULL DEFAULT '[]';

-- Статусы: pending | sent | edited | rejected | superseded
DO $$
DECLARE
    con record;
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conrelid = 'support_ai_suggestion'::regclass
           AND contype = 'c'
           AND pg_get_constraintdef(oid) LIKE '%status%'
           AND pg_get_constraintdef(oid) LIKE '%superseded%'
    ) THEN
        FOR con IN
            SELECT conname
              FROM pg_constraint
             WHERE conrelid = 'support_ai_suggestion'::regclass
               AND contype = 'c'
               AND pg_get_constraintdef(oid) LIKE '%status%'
        LOOP
            EXECUTE format('ALTER TABLE support_ai_suggestion DROP CONSTRAINT %I', con.conname);
        END LOOP;
        ALTER TABLE support_ai_suggestion
            ADD CONSTRAINT support_ai_suggestion_status_check
            CHECK (status IN ('pending', 'sent', 'edited', 'rejected', 'superseded'));
    END IF;
END $$;

-- Нормализация перед частичным уникальным индексом: один pending на диалог
UPDATE support_ai_suggestion
   SET status = 'superseded'
 WHERE status = 'pending'
   AND id NOT IN (
        SELECT max(id) FROM support_ai_suggestion
         WHERE status = 'pending'
         GROUP BY conversation_id
   );

CREATE INDEX IF NOT EXISTS idx_support_ai_suggestion_conv
    ON support_ai_suggestion (conversation_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_support_ai_suggestion_status
    ON support_ai_suggestion (status, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_support_ai_suggestion_pending
    ON support_ai_suggestion (conversation_id)
    WHERE status = 'pending';

-- ============================================
-- support_qa_pair — обучение на ответах операторов
-- ============================================
CREATE TABLE IF NOT EXISTS support_qa_pair (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT REFERENCES support_conversation(id) ON DELETE SET NULL,
    source          TEXT        NOT NULL DEFAULT 'operator'
                        CHECK (source IN ('operator', 'import', 'feedback')),
    question        TEXT        NOT NULL,
    answer          TEXT        NOT NULL,
    external_key    TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_key)
);

CREATE INDEX IF NOT EXISTS idx_support_qa_pair_fts
    ON support_qa_pair
    USING GIN (to_tsvector('russian', coalesce(question, '') || ' ' || coalesce(answer, '')));

-- ============================================
-- support_operator_draft — серверный черновик ответа/заметки
-- ============================================
CREATE TABLE IF NOT EXISTS support_operator_draft (
    actor_id           BIGINT      NOT NULL,
    conversation_id    BIGINT      NOT NULL REFERENCES support_conversation(id) ON DELETE CASCADE,
    text               TEXT        NOT NULL DEFAULT '',
    mode               TEXT        NOT NULL DEFAULT 'reply'
                           CHECK (mode IN ('reply', 'note')),
    quote              TEXT,
    from_suggestion_id BIGINT,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (actor_id, conversation_id)
);

-- ============================================
-- support_kb_candidate — идеи статей
-- 004 уже создала: id, title, file_name, source, confidence, status, version,
--                  created_at, decided_at, decided_by (TEXT — см. ADR-007, тип не меняем)
-- ============================================
ALTER TABLE support_kb_candidate
    ADD COLUMN IF NOT EXISTS reason      TEXT,
    ADD COLUMN IF NOT EXISTS doc_id      BIGINT REFERENCES support_kb_doc(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS question    TEXT,
    ADD COLUMN IF NOT EXISTS answer      TEXT,
    ADD COLUMN IF NOT EXISTS topic       TEXT,
    ADD COLUMN IF NOT EXISTS occurrences INTEGER NOT NULL DEFAULT 1;

ALTER TABLE support_kb_candidate ALTER COLUMN status SET DEFAULT 'new';
ALTER TABLE support_kb_candidate ALTER COLUMN source SET DEFAULT 'mining';

-- Приведение старых статусов 004 к новым (pending→new, approved→accepted) до CHECK
UPDATE support_kb_candidate SET status = 'new'      WHERE status = 'pending';
UPDATE support_kb_candidate SET status = 'accepted' WHERE status = 'approved';

-- Одна идея на тему: дубли в статусе new → rejected
UPDATE support_kb_candidate c
   SET status = 'rejected'
 WHERE c.status = 'new'
   AND c.topic IS NOT NULL
   AND c.id <> (
        SELECT min(x.id) FROM support_kb_candidate x
         WHERE x.topic = c.topic AND x.status = 'new'
   );

-- Статусы: new | accepted | rejected
DO $$
DECLARE
    con record;
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conrelid = 'support_kb_candidate'::regclass
           AND contype = 'c'
           AND pg_get_constraintdef(oid) LIKE '%status%'
           AND pg_get_constraintdef(oid) LIKE '%accepted%'
           AND pg_get_constraintdef(oid) LIKE '%rejected%'
    ) THEN
        FOR con IN
            SELECT conname
              FROM pg_constraint
             WHERE conrelid = 'support_kb_candidate'::regclass
               AND contype = 'c'
               AND pg_get_constraintdef(oid) LIKE '%status%'
        LOOP
            EXECUTE format('ALTER TABLE support_kb_candidate DROP CONSTRAINT %I', con.conname);
        END LOOP;
        ALTER TABLE support_kb_candidate
            ADD CONSTRAINT support_kb_candidate_status_check
            CHECK (status IN ('new', 'accepted', 'rejected'));
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_support_kb_candidate_topic
    ON support_kb_candidate (topic)
    WHERE status = 'new';

-- ============================================
-- support_job — фоновые задачи (импорт и т.п.)
-- 004 уже создала: id, kind, status (default running), progress (TEXT),
--                  result (TEXT), error, started_at, ended_at
-- ============================================
ALTER TABLE support_job
    ADD COLUMN IF NOT EXISTS payload     JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS total       INTEGER,
    ADD COLUMN IF NOT EXISTS created_by  BIGINT,
    ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ;

ALTER TABLE support_job ALTER COLUMN status SET DEFAULT 'queued';

-- progress TEXT → INTEGER (безопасно: нечисловые значения становятся 0)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'support_job'
           AND column_name = 'progress'
           AND data_type <> 'integer'
    ) THEN
        ALTER TABLE support_job ALTER COLUMN progress DROP DEFAULT;
        ALTER TABLE support_job
            ALTER COLUMN progress TYPE INTEGER
            USING (CASE WHEN progress ~ '^[0-9]+$' THEN progress::integer ELSE 0 END);
        UPDATE support_job SET progress = 0 WHERE progress IS NULL;
        ALTER TABLE support_job ALTER COLUMN progress SET DEFAULT 0;
        ALTER TABLE support_job ALTER COLUMN progress SET NOT NULL;
    END IF;
END $$;

-- result TEXT → JSONB; при невалидном JSON в данных колонка остаётся TEXT
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'support_job'
           AND column_name = 'result'
           AND data_type <> 'jsonb'
    ) THEN
        BEGIN
            ALTER TABLE support_job
                ALTER COLUMN result TYPE JSONB
                USING (
                    CASE
                        WHEN result IS NULL OR btrim(result) = '' THEN NULL
                        WHEN btrim(result) ~ '^[\[{\"]' THEN btrim(result)::jsonb
                        ELSE to_jsonb(result)
                    END
                );
        EXCEPTION WHEN others THEN
            NULL;  -- оставляем TEXT, если данные не парсятся как JSON
        END;
    END IF;
END $$;

-- Нормализация статусов 004 к queued|running|done|error
UPDATE support_job SET status = 'error' WHERE status NOT IN ('queued', 'running', 'done', 'error');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conrelid = 'support_job'::regclass
           AND contype = 'c'
           AND pg_get_constraintdef(oid) LIKE '%status%'
           AND pg_get_constraintdef(oid) LIKE '%done%'
    ) THEN
        ALTER TABLE support_job
            ADD CONSTRAINT support_job_status_check
            CHECK (status IN ('queued', 'running', 'done', 'error'));
    END IF;
END $$;

-- Один активный джоб на kind: лишние активные → error
UPDATE support_job j
   SET status = 'error'
 WHERE j.status IN ('queued', 'running')
   AND j.id <> (
        SELECT max(x.id) FROM support_job x
         WHERE x.kind = j.kind AND x.status IN ('queued', 'running')
   );

CREATE UNIQUE INDEX IF NOT EXISTS uq_support_job_active
    ON support_job (kind)
    WHERE status IN ('queued', 'running');
