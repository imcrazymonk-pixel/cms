-- Support reply idempotency — Этап A (апстрим v3.0.0): один client_msg_id = один ответ.
-- Идемпотентный DDL: CREATE TABLE/INDEX IF NOT EXISTS, повторный запуск безопасен.
-- Применяется из lifespan через ensure_support_schema() после 004-support-foundation.sql.

-- ============================================
-- Ключи идемпотентности ответов оператора
-- ============================================
CREATE TABLE IF NOT EXISTS support_reply_key (
    actor_id        BIGINT      NOT NULL,
    conversation_id BIGINT      NOT NULL REFERENCES support_conversation(id) ON DELETE CASCADE,
    client_msg_id   TEXT        NOT NULL,
    message_id      BIGINT      NOT NULL REFERENCES support_message(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (actor_id, conversation_id, client_msg_id)
);

CREATE INDEX IF NOT EXISTS idx_support_reply_key_message
    ON support_reply_key (message_id);
