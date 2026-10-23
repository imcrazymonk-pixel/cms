-- Support foundation — Phase 0 (живые таблицы фаз 0–1 + каркасы будущих фаз).
-- Идемпотентный DDL: CREATE TABLE/INDEX IF NOT EXISTS, повторный запуск безопасен.
-- Применяется из lifespan через ensure_support_schema()
-- (web/backend/core/support/schema.py). FTS-индексы КБ не создаём — фаза 3.

-- ============================================
-- Профили клиентов (создаётся первой — на неё ссылается support_conversation)
-- ============================================
CREATE TABLE IF NOT EXISTS support_customer_profile (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identity_key TEXT        NOT NULL UNIQUE,   -- например 'bedolaga:123'
    tg_user_id   BIGINT,
    username     TEXT,
    display_name TEXT,
    email        TEXT,
    phone        TEXT,
    meta         JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_support_customer_profile_tg      ON support_customer_profile (tg_user_id);
CREATE INDEX IF NOT EXISTS idx_support_customer_profile_username ON support_customer_profile (username);

-- ============================================
-- Диалоги
-- ============================================
CREATE TABLE IF NOT EXISTS support_conversation (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    channel               TEXT        NOT NULL,
    external_id           TEXT        NOT NULL,
    tg_user_id            BIGINT,
    source_id             TEXT,
    status                TEXT        NOT NULL DEFAULT 'open'
                              CHECK (status IN ('open', 'pending', 'resolved', 'closed')),
    priority              TEXT        NOT NULL DEFAULT 'normal'
                              CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    subject               TEXT,
    assignee_id           BIGINT REFERENCES users(id) ON DELETE SET NULL,
    claimed_at            TIMESTAMPTZ,
    first_inbound_at      TIMESTAMPTZ,
    last_inbound_at       TIMESTAMPTZ,
    first_response_at     TIMESTAMPTZ,
    last_message_at       TIMESTAMPTZ,
    unread                INTEGER     NOT NULL DEFAULT 0,
    suspicious            BOOLEAN     NOT NULL DEFAULT FALSE,
    sub_link              TEXT,
    customer_profile_id   BIGINT REFERENCES support_customer_profile(id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (channel, external_id)
);

CREATE INDEX IF NOT EXISTS idx_support_conversation_queue
    ON support_conversation (status, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_conversation_activity
    ON support_conversation (last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_conversation_customer
    ON support_conversation (customer_profile_id);
CREATE INDEX IF NOT EXISTS idx_support_conversation_assignee
    ON support_conversation (assignee_id);

-- ============================================
-- Сообщения
-- ============================================
CREATE TABLE IF NOT EXISTS support_message (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id      BIGINT      NOT NULL REFERENCES support_conversation(id) ON DELETE CASCADE,
    direction            TEXT        NOT NULL CHECK (direction IN ('in', 'out')),
    author               TEXT        NOT NULL CHECK (author IN ('client', 'agent', 'system')),
    text                 TEXT,
    media_type           TEXT,
    media_file_id        TEXT,
    external_msg_id      TEXT,
    reply_to_external_id TEXT,
    reply_excerpt        TEXT,
    is_backfill          BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Дедуп входящих: один внешний id не заводит дубликат в диалоге
CREATE UNIQUE INDEX IF NOT EXISTS uq_support_message_in_external
    ON support_message (conversation_id, external_msg_id)
    WHERE direction = 'in' AND external_msg_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_support_message_conversation
    ON support_message (conversation_id, id);
-- Живые входящие (без импортированной истории) — для SLA и статистики
CREATE INDEX IF NOT EXISTS idx_support_message_live_inbound
    ON support_message (created_at, conversation_id)
    WHERE direction = 'in' AND NOT is_backfill;

-- ============================================
-- Служебные таблицы (курсоры поллинга, рантайм-настройки)
-- ============================================
CREATE TABLE IF NOT EXISTS support_poll_state (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS support_setting (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================
-- Каркасы будущих фаз (создаём, но не используем)
-- ============================================

-- Фаза 3 — ИИ-подсказки
CREATE TABLE IF NOT EXISTS support_ai_suggestion (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT      NOT NULL REFERENCES support_conversation(id) ON DELETE CASCADE,
    message_id      BIGINT,
    text            TEXT        NOT NULL,
    confidence      REAL,
    needs_human     BOOLEAN     NOT NULL DEFAULT FALSE,
    reason          TEXT,
    model           TEXT,
    sources         TEXT,
    status          TEXT        NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending', 'accepted', 'rejected')),
    decided_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Фаза 3 — база знаний (полнотекстовые индексы появятся вместе с фазой 3)
CREATE TABLE IF NOT EXISTS support_kb_doc (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source     TEXT        NOT NULL,
    ext_id     TEXT        NOT NULL,
    title      TEXT        NOT NULL,
    body       TEXT        NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, ext_id)
);

CREATE TABLE IF NOT EXISTS support_kb_candidate (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title      TEXT        NOT NULL,
    file_name  TEXT        NOT NULL,
    source     TEXT        NOT NULL,
    confidence REAL,
    status     TEXT        NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending', 'approved', 'rejected')),
    version    INTEGER     NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ,
    decided_by TEXT,
    UNIQUE (file_name, version)
);

-- Журнал фоновых задач
CREATE TABLE IF NOT EXISTS support_job (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind       TEXT        NOT NULL,
    status     TEXT        NOT NULL DEFAULT 'running',
    progress   TEXT,
    result     TEXT,
    error      TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at   TIMESTAMPTZ
);

-- Вложения (фаза 2+): медиа CMS хранится отдельной вкладкой, тут только ссылки
CREATE TABLE IF NOT EXISTS support_attachment (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id      BIGINT      NOT NULL REFERENCES support_message(id) ON DELETE CASCADE,
    media_type      TEXT,
    file_ref        TEXT        NOT NULL,
    local_path      TEXT,
    bytes           BIGINT,
    downloaded_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    attempts        INTEGER     NOT NULL DEFAULT 0,
    width           INTEGER,
    height          INTEGER,
    original_name   TEXT,
    mime_type       TEXT,
    sha256          TEXT,
    next_attempt_at TIMESTAMPTZ,
    last_error      TEXT
);

-- Присутствие операторов (фаза 4)
CREATE TABLE IF NOT EXISTS support_operator_presence (
    actor_key       TEXT        NOT NULL,
    conversation_id BIGINT      NOT NULL REFERENCES support_conversation(id) ON DELETE CASCADE,
    state           TEXT        NOT NULL CHECK (state IN ('viewing', 'typing')),
    seen_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (actor_key, conversation_id)
);

-- Заметки по клиенту (фаза 4)
CREATE TABLE IF NOT EXISTS support_customer_note (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT      NOT NULL REFERENCES support_customer_profile(id) ON DELETE CASCADE,
    actor_key   TEXT        NOT NULL,
    text        TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Источники каналов (несколько Telegram-аккаунтов и т.п., фаза 2)
CREATE TABLE IF NOT EXISTS support_source_account (
    id         TEXT        PRIMARY KEY,
    kind       TEXT        NOT NULL,
    name       TEXT        NOT NULL,
    enabled    BOOLEAN     NOT NULL DEFAULT TRUE,
    metadata   JSONB       NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Шаблоны ответов (фаза 4)
CREATE TABLE IF NOT EXISTS support_template (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shortcut   TEXT        NOT NULL UNIQUE,
    title      TEXT        NOT NULL,
    body       TEXT        NOT NULL,
    uses       INTEGER     NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Политики SLA (фаза 4) — seed по приоритетам
CREATE TABLE IF NOT EXISTS support_sla_policy (
    name                   TEXT    PRIMARY KEY,
    first_response_minutes INTEGER NOT NULL,
    resolution_minutes     INTEGER NOT NULL
);

INSERT INTO support_sla_policy (name, first_response_minutes, resolution_minutes) VALUES
    ('low',    240, 2880),
    ('normal',  60, 1440),
    ('high',    20,  480),
    ('urgent',   5,  120)
ON CONFLICT (name) DO NOTHING;

-- Аудит действий операторов
CREATE TABLE IF NOT EXISTS support_audit_log (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT        NOT NULL,
    resource    TEXT        NOT NULL,
    resource_id TEXT,
    payload     JSONB       NOT NULL DEFAULT '{}',
    ip          TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================
-- updated_at триггеры (идемпотентно)
-- ============================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_support_conversation_updated_at') THEN
        CREATE TRIGGER update_support_conversation_updated_at
        BEFORE UPDATE ON support_conversation
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_support_customer_profile_updated_at') THEN
        CREATE TRIGGER update_support_customer_profile_updated_at
        BEFORE UPDATE ON support_customer_profile
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_support_setting_updated_at') THEN
        CREATE TRIGGER update_support_setting_updated_at
        BEFORE UPDATE ON support_setting
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_support_poll_state_updated_at') THEN
        CREATE TRIGGER update_support_poll_state_updated_at
        BEFORE UPDATE ON support_poll_state
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;
