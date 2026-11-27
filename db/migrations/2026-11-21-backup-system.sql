-- Backup system foundation (idempotent).
-- Mirrors docs/plans/2026-11-21-backup-system.md §7.2, §8, §8.1, §11.
-- Applied by deploy.sh (db/migrations) and by core/backup/schema.py at startup.

CREATE TABLE IF NOT EXISTS backup_storages (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL UNIQUE,
  kind          text NOT NULL CHECK (kind IN ('local','s3','sftp','ssh','webdav','ftp','rclone')),
  config        jsonb NOT NULL DEFAULT '{}',
  advanced      jsonb NOT NULL DEFAULT '{}',
  secrets       text,
  enabled       boolean NOT NULL DEFAULT true,
  is_default    boolean NOT NULL DEFAULT false,
  quota_bytes   bigint,
  used_bytes    bigint NOT NULL DEFAULT 0,
  last_check_at timestamptz,
  last_check_ok boolean,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backup_hosts (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name           text NOT NULL UNIQUE,
  role           text NOT NULL DEFAULT 'server' CHECK (role IN ('server','node','self')),
  address        text NOT NULL,
  transport      text NOT NULL DEFAULT 'agent' CHECK (transport IN ('agent','inline','ssh')),
  ssh_port       int  NOT NULL DEFAULT 22,
  ssh_user       text,
  credential_ref text,
  tags           jsonb NOT NULL DEFAULT '[]',
  status         text NOT NULL DEFAULT 'unknown' CHECK (status IN ('unknown','reachable','unreachable')),
  last_seen_at   timestamptz,
  last_scan_at   timestamptz,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backup_agents (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  host_id          uuid NOT NULL UNIQUE REFERENCES backup_hosts(id) ON DELETE CASCADE,
  token_enc        text NOT NULL,
  agent_version    text,
  desired_version  text,
  protocol_version int NOT NULL DEFAULT 1,
  status           text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','online','offline','update_failed')),
  spool_bytes      bigint NOT NULL DEFAULT 0,
  disk_free        bigint,
  last_heartbeat   timestamptz,
  installed_at     timestamptz
);
CREATE INDEX IF NOT EXISTS idx_backup_agents_heartbeat ON backup_agents(last_heartbeat);

CREATE TABLE IF NOT EXISTS backup_components (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  host_id        uuid NOT NULL REFERENCES backup_hosts(id) ON DELETE CASCADE,
  recipe_id      text NOT NULL,
  name           text NOT NULL,
  container_name text,
  image          text,
  image_digest   text,
  version        text,
  confidence     text NOT NULL DEFAULT 'high' CHECK (confidence IN ('high','medium','low')),
  enabled        boolean NOT NULL DEFAULT true,
  detect_meta    jsonb NOT NULL DEFAULT '{}',
  updated_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (host_id, recipe_id, name)
);
CREATE INDEX IF NOT EXISTS idx_backup_components_host ON backup_components(host_id);

CREATE TABLE IF NOT EXISTS backup_policies (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name       text NOT NULL,
  host_id    uuid NOT NULL REFERENCES backup_hosts(id) ON DELETE CASCADE,
  timezone   text NOT NULL DEFAULT 'Europe/Moscow',
  enabled    boolean NOT NULL DEFAULT true,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_backup_policies_host ON backup_policies(host_id);

CREATE TABLE IF NOT EXISTS backup_tiers (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_id        uuid NOT NULL REFERENCES backup_policies(id) ON DELETE CASCADE,
  name             text NOT NULL,
  position         int  NOT NULL DEFAULT 0,
  scope            text NOT NULL CHECK (scope IN ('full','database','files','env','custom')),
  component_ids    jsonb NOT NULL DEFAULT '[]',
  schedule_kind    text NOT NULL CHECK (schedule_kind IN ('cron','interval')),
  cron             text,
  interval_minutes int,
  retention_mode   text NOT NULL DEFAULT 'auto' CHECK (retention_mode IN ('auto','days')),
  retention_copies int,
  retention_days   int NOT NULL DEFAULT 14,
  min_copies       int NOT NULL DEFAULT 3,
  storage_ids      jsonb NOT NULL DEFAULT '[]',
  encrypt          boolean NOT NULL DEFAULT true,
  include_logs     boolean NOT NULL DEFAULT false,
  consistency      text NOT NULL DEFAULT 'online' CHECK (consistency IN ('online','quiesce')),
  enabled          boolean NOT NULL DEFAULT true,
  next_run_at      timestamptz
);
CREATE INDEX IF NOT EXISTS idx_backup_tiers_due ON backup_tiers(enabled, next_run_at);

CREATE TABLE IF NOT EXISTS backup_runs (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_id         uuid REFERENCES backup_policies(id) ON DELETE SET NULL,
  tier_id           uuid REFERENCES backup_tiers(id) ON DELETE SET NULL,
  host_id           uuid REFERENCES backup_hosts(id) ON DELETE SET NULL,
  agent_id          uuid REFERENCES backup_agents(id) ON DELETE SET NULL,
  kind              text NOT NULL DEFAULT 'backup' CHECK (kind IN ('backup','restore','verify','scan')),
  trigger           text NOT NULL DEFAULT 'manual' CHECK (trigger IN ('manual','schedule','api')),
  client_run_id     uuid UNIQUE,
  status            text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','success','failed','cancelled')),
  progress          int  NOT NULL DEFAULT 0,
  steps             jsonb NOT NULL DEFAULT '[]',
  log               text NOT NULL DEFAULT '',
  error             text,
  cancel_requested  boolean NOT NULL DEFAULT false,
  size_bytes        bigint,
  artifact_scope    text,
  consistency_group text,
  started_at        timestamptz,
  finished_at       timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_backup_runs_status ON backup_runs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backup_runs_host ON backup_runs(host_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backup_runs_group ON backup_runs(consistency_group);

CREATE TABLE IF NOT EXISTS backup_artifacts (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id        uuid NOT NULL REFERENCES backup_runs(id) ON DELETE CASCADE,
  component_id  uuid REFERENCES backup_components(id) ON DELETE SET NULL,
  storage_id    uuid REFERENCES backup_storages(id) ON DELETE SET NULL,
  artifact_type text NOT NULL,
  object_key    text NOT NULL,
  size_bytes    bigint,
  sha256        text,
  encrypted     boolean NOT NULL DEFAULT true,
  manifest      jsonb NOT NULL DEFAULT '{}',
  orphaned      boolean NOT NULL DEFAULT false,
  expires_at    timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_backup_artifacts_run ON backup_artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_backup_artifacts_expires ON backup_artifacts(expires_at);

CREATE TABLE IF NOT EXISTS backup_restores (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_key            text,
  target_host_id       uuid REFERENCES backup_hosts(id) ON DELETE SET NULL,
  target_kind          text NOT NULL DEFAULT 'same' CHECK (target_kind IN ('same','new','dry_run')),
  plan                 jsonb NOT NULL DEFAULT '{}',
  plan_token           text,
  status               text NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','running','success','failed','cancelled')),
  pre_snapshot_run_id  uuid REFERENCES backup_runs(id) ON DELETE SET NULL,
  started_at           timestamptz,
  finished_at          timestamptz,
  error                text,
  created_by           text,
  created_at           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_backup_restores_status ON backup_restores(status, created_at DESC);

CREATE TABLE IF NOT EXISTS backup_commands (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  host_id    uuid NOT NULL REFERENCES backup_hosts(id) ON DELETE CASCADE,
  type       text NOT NULL CHECK (type IN ('scan','backup_now','restore','cancel','update')),
  payload    jsonb NOT NULL DEFAULT '{}',
  status     text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','taken','done','failed','expired')),
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL DEFAULT now() + interval '24 hours'
);
CREATE INDEX IF NOT EXISTS idx_backup_commands_host ON backup_commands(host_id, status);

CREATE TABLE IF NOT EXISTS backup_notification_channels (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL UNIQUE,
  kind          text NOT NULL CHECK (kind IN ('telegram','smtp','webhook','discord','slack')),
  config        jsonb NOT NULL DEFAULT '{}',
  secrets       text,
  enabled       boolean NOT NULL DEFAULT true,
  last_check_at timestamptz,
  last_check_ok boolean,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backup_notification_rules (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name             text NOT NULL,
  event            text NOT NULL,
  host_id          uuid REFERENCES backup_hosts(id) ON DELETE CASCADE,
  policy_id        uuid REFERENCES backup_policies(id) ON DELETE CASCADE,
  channel_ids      jsonb NOT NULL DEFAULT '[]',
  threshold        jsonb NOT NULL DEFAULT '{}',
  quiet_hours      text,
  repeat_every_min int,
  severity         text NOT NULL DEFAULT 'warning' CHECK (severity IN ('info','warning','critical')),
  enabled          boolean NOT NULL DEFAULT true,
  created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_backup_notification_rules_event ON backup_notification_rules(event, enabled);

CREATE TABLE IF NOT EXISTS backup_settings (
  setting_key   text PRIMARY KEY,
  setting_value text,
  is_secret     boolean NOT NULL DEFAULT false,
  updated_at    timestamptz NOT NULL DEFAULT now()
);

-- Private SSH key for one-click agent installation (encrypted with APP_ENCRYPTION_KEY).
ALTER TABLE backup_hosts ADD COLUMN IF NOT EXISTS ssh_key_enc text;
