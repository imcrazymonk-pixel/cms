-- 008-support-stage-c.sql — Этап C, C1: автор исходящих, шаблоны, SLA-события,
-- присутствие, аудит и заметки. Идемпотентно (IF NOT EXISTS).

ALTER TABLE support_message
    ADD COLUMN IF NOT EXISTS author_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_support_message_author
    ON support_message (author_id, created_at) WHERE direction='out';

ALTER TABLE support_template ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE support_template ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE support_template ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
CREATE INDEX IF NOT EXISTS idx_support_template_category ON support_template (category, title);

CREATE TABLE IF NOT EXISTS support_sla_event (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES support_conversation(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN ('first_response','resolution')),
    due_at          TIMESTAMPTZ NOT NULL,
    breached_at     TIMESTAMPTZ,
    notified_at     TIMESTAMPTZ,
    closed_at       TIMESTAMPTZ,
    UNIQUE (conversation_id, kind)
);
CREATE INDEX IF NOT EXISTS idx_support_sla_event_due
    ON support_sla_event (due_at) WHERE notified_at IS NULL AND closed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_support_presence_seen
    ON support_operator_presence (conversation_id, seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_audit_created
    ON support_audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_audit_action
    ON support_audit_log (action, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_customer_note_customer
    ON support_customer_note (customer_id, created_at DESC);
