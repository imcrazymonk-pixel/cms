import client from './client'

// ── types ────────────────────────────────────────────────────────────────────

export interface BackupHost {
  id: string
  name: string
  role: 'server' | 'node' | 'self'
  address: string
  transport: 'agent' | 'inline' | 'ssh'
  ssh_port: number
  ssh_user?: string | null
  has_ssh_key?: boolean
  status: string
  tags: string[]
  agent_id?: string | null
  agent_version?: string | null
  agent_status?: string | null
  last_heartbeat?: string | null
  last_success_at?: string | null
  components_count?: number
  policies_count?: number
}

export interface BackupComponent {
  id: string
  host_id: string
  recipe_id: string
  name: string
  container_name?: string | null
  image?: string | null
  version?: string | null
  confidence: 'high' | 'medium' | 'low'
  enabled: boolean
  updated_at?: string | null
}

export interface BackupStorage {
  id: string
  name: string
  kind: 'local' | 's3' | 'sftp' | 'ssh' | 'webdav' | 'ftp' | 'rclone'
  config: Record<string, unknown>
  advanced: Record<string, unknown>
  has_secret: boolean
  enabled: boolean
  is_default: boolean
  quota_bytes?: number | null
  used_bytes: number
  last_check_at?: string | null
  last_check_ok?: boolean | null
}

export interface BackupTier {
  id: string
  policy_id: string
  name: string
  position: number
  scope: 'full' | 'database' | 'files' | 'env' | 'custom'
  component_ids: string[]
  schedule_kind: 'cron' | 'interval'
  cron?: string | null
  interval_minutes?: number | null
  retention_mode: 'auto' | 'days'
  retention_copies?: number | null
  retention_days: number
  min_copies: number
  storage_ids: string[]
  encrypt: boolean
  include_logs: boolean
  consistency: 'online' | 'quiesce'
  enabled: boolean
  next_run_at?: string | null
}

export interface BackupPolicy {
  id: string
  name: string
  host_id: string
  timezone: string
  enabled: boolean
  tiers?: BackupTier[]
}

export interface BackupRunStep {
  id: string
  title: string
  status: string
  detail?: string | null
}

export interface BackupRun {
  id: string
  policy_id?: string | null
  tier_id?: string | null
  host_id?: string | null
  kind: string
  trigger: string
  status: 'queued' | 'running' | 'success' | 'failed' | 'cancelled'
  progress: number
  steps: BackupRunStep[]
  log?: string
  error?: string | null
  size_bytes?: number | null
  artifact_scope?: string | null
  consistency_group?: string | null
  started_at?: string | null
  finished_at?: string | null
  created_at?: string | null
}

export interface BackupArtifact {
  id: string
  run_id: string
  artifact_type: string
  object_key: string
  size_bytes?: number | null
  sha256?: string | null
  encrypted: boolean
  orphaned: boolean
  expires_at?: string | null
  created_at?: string | null
}

export interface BackupOverview {
  hosts_total: number
  hosts_unreachable: number
  agents_online: number
  agents_offline: number
  storages_total: number
  storages_error: number
  policies_total: number
  total_bytes: number
  last_success_at?: string | null
  last_db_backup_at?: string | null
  last_full_backup_at?: string | null
  overdue: Array<{ id: string; name: string; last_success_at?: string | null }>
  attention: Array<{ type: string; message: string; host_id?: string; run_id?: string }>
}

export interface BackupRecipe {
  id: string
  title: string
  version: number
  transport: string
  description?: string | null
  has_database: boolean
  files: string[]
  logs_supported: boolean
}

export interface NotificationChannel {
  id: string
  name: string
  kind: 'telegram' | 'smtp' | 'webhook' | 'discord' | 'slack'
  config: Record<string, unknown>
  has_secret: boolean
  enabled: boolean
  last_check_ok?: boolean | null
}

export interface NotificationRule {
  id: string
  name: string
  event: string
  host_id?: string | null
  channel_ids: string[]
  threshold: Record<string, unknown>
  quiet_hours?: string | null
  repeat_every_min?: number | null
  severity: 'info' | 'warning' | 'critical'
  enabled: boolean
}

export interface NotificationEvent {
  event: string
  title: string
  description: string
  severity: string
}

const unwrap = <T>(response: { data: { data: T } }): T => response.data.data

// ── api ──────────────────────────────────────────────────────────────────────

export const backupsApi = {
  overview: () => client.get('/backups/overview').then((r) => unwrap<BackupOverview>(r)),
  recipes: () => client.get('/backups/recipes').then((r) => unwrap<BackupRecipe[]>(r)),

  hosts: () => client.get('/backups/hosts').then((r) => unwrap<BackupHost[]>(r)),
  createHost: (payload: Partial<BackupHost>) =>
    client.post('/backups/hosts', payload).then((r) => unwrap<BackupHost>(r)),
  updateHost: (id: string, payload: Partial<BackupHost>) =>
    client.patch(`/backups/hosts/${id}`, payload).then((r) => unwrap<BackupHost>(r)),
  deleteHost: (id: string) => client.delete(`/backups/hosts/${id}`),
  testHost: (id: string) => client.post(`/backups/hosts/${id}/test`).then((r) => unwrap<Record<string, unknown>>(r)),
  scanHost: (id: string) => client.post(`/backups/hosts/${id}/scan`),
  installAgent: (id: string, via: 'command' | 'ssh' = 'command') =>
    client
      .post(`/backups/hosts/${id}/agent-install`, null, { params: { via } })
      .then((r) =>
        unwrap<{
          install_command: string
          token: string
          install_result?: { ok: boolean; message?: string; output?: string }
        }>(r),
      ),
  components: (hostId?: string) =>
    client
      .get('/backups/components', { params: hostId ? { host_id: hostId } : {} })
      .then((r) => unwrap<BackupComponent[]>(r)),
  updateComponent: (id: string, payload: Partial<BackupComponent>) =>
    client.patch(`/backups/components/${id}`, payload).then((r) => unwrap<BackupComponent>(r)),

  storages: () => client.get('/backups/storages').then((r) => unwrap<BackupStorage[]>(r)),
  createStorage: (payload: Partial<BackupStorage> & { secret?: Record<string, unknown> }) =>
    client.post('/backups/storages', payload).then((r) => unwrap<BackupStorage>(r)),
  updateStorage: (id: string, payload: Partial<BackupStorage> & { secret?: Record<string, unknown> }) =>
    client.patch(`/backups/storages/${id}`, payload).then((r) => unwrap<BackupStorage>(r)),
  deleteStorage: (id: string) => client.delete(`/backups/storages/${id}`),
  testStorage: (id: string) =>
    client.post(`/backups/storages/${id}/test`).then((r) => unwrap<{ ok: boolean; message: string; latency_ms?: number }>(r)),

  policies: (hostId?: string) =>
    client
      .get('/backups/policies', { params: hostId ? { host_id: hostId } : {} })
      .then((r) => unwrap<BackupPolicy[]>(r)),
  createPolicy: (payload: Partial<BackupPolicy>) =>
    client.post('/backups/policies', payload).then((r) => unwrap<BackupPolicy>(r)),
  deletePolicy: (id: string) => client.delete(`/backups/policies/${id}`),
  tiers: (policyId: string) =>
    client.get(`/backups/policies/${policyId}/tiers`).then((r) => unwrap<BackupTier[]>(r)),
  createTier: (policyId: string, payload: Partial<BackupTier>) =>
    client.post(`/backups/policies/${policyId}/tiers`, payload).then((r) => unwrap<BackupTier>(r)),
  updateTier: (id: string, payload: Partial<BackupTier>) =>
    client.patch(`/backups/tiers/${id}`, payload).then((r) => unwrap<BackupTier>(r)),
  deleteTier: (id: string) => client.delete(`/backups/tiers/${id}`),
  runTier: (id: string) => client.post(`/backups/tiers/${id}/run`),

  runs: (params?: { host_id?: string; status?: string; limit?: number }) =>
    client.get('/backups/runs', { params }).then((r) => unwrap<BackupRun[]>(r)),
  run: (id: string) => client.get(`/backups/runs/${id}`).then((r) => unwrap<BackupRun>(r)),
  runLog: (id: string, offset = 0) =>
    client.get(`/backups/runs/${id}/log`, { params: { offset } }).then((r) => unwrap<{ log: string; next_offset: number }>(r)),
  cancelRun: (id: string) => client.post(`/backups/runs/${id}/cancel`),

  artifacts: (params?: { host_id?: string; run_id?: string }) =>
    client.get('/backups/artifacts', { params }).then((r) => unwrap<BackupArtifact[]>(r)),
  verifyArtifact: (id: string) =>
    client.post(`/backups/artifacts/${id}/verify`).then((r) => unwrap<{ sha256_ok: boolean; message: string }>(r)),
  deleteArtifact: (id: string) => client.delete(`/backups/artifacts/${id}`),
  artifactUrl: (id: string) => `/api/backups/artifacts/${id}/download`,

  restorePlan: (payload: { group_key: string; target_host_id?: string; target_kind?: string }) =>
    client.post('/backups/restore/plan', payload).then((r) => unwrap<Record<string, unknown>>(r)),
  restore: (planToken: string) =>
    client.post('/backups/restore', { plan_token: planToken, confirm: true }).then((r) => unwrap<Record<string, unknown>>(r)),
  restores: () => client.get('/backups/restore').then((r) => unwrap<Record<string, unknown>[]>(r)),

  channels: () => client.get('/backups/notifications/channels').then((r) => unwrap<NotificationChannel[]>(r)),
  createChannel: (payload: Record<string, unknown>) =>
    client.post('/backups/notifications/channels', payload).then((r) => unwrap<NotificationChannel>(r)),
  deleteChannel: (id: string) => client.delete(`/backups/notifications/channels/${id}`),
  testChannel: (id: string) =>
    client.post(`/backups/notifications/channels/${id}/test`).then((r) => unwrap<{ ok: boolean; message: string }>(r)),
  events: () => client.get('/backups/notifications/events').then((r) => unwrap<NotificationEvent[]>(r)),
  rules: () => client.get('/backups/notifications/rules').then((r) => unwrap<NotificationRule[]>(r)),
  createRule: (payload: Record<string, unknown>) =>
    client.post('/backups/notifications/rules', payload).then((r) => unwrap<NotificationRule>(r)),
  deleteRule: (id: string) => client.delete(`/backups/notifications/rules/${id}`),

  settings: () => client.get('/backups/settings').then((r) => unwrap<{ values: Record<string, unknown> }>(r)),
  saveSettings: (values: Record<string, unknown>) =>
    client.put('/backups/settings', { values }).then((r) => unwrap<{ values: Record<string, unknown> }>(r)),
}

export default backupsApi
