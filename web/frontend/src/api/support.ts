import { api } from './client'

// ── Types ───────────────────────────────────────────────────────────────────

export type ConversationStatus = 'open' | 'pending' | 'resolved' | 'closed'
export type ConversationPriority = 'low' | 'normal' | 'high' | 'urgent'

export interface SupportConversation {
  id: number
  channel: string
  external_id: string
  tg_user_id: number | null
  source_id: string | null
  status: ConversationStatus
  priority: ConversationPriority
  subject: string | null
  assignee_id: number | null
  claimed_at: string | null
  first_inbound_at: string | null
  last_inbound_at: string | null
  first_response_at: string | null
  last_message_at: string | null
  unread: number
  suspicious: boolean
  sub_link: string | null
  customer_profile_id: number | null
  created_at: string
  updated_at: string
}

export interface SupportMessage {
  id: number
  conversation_id: number
  direction: 'in' | 'out'
  author: 'client' | 'agent' | 'system' | 'bot'
  text: string | null
  media_type: string | null
  media_file_id: string | null
  external_msg_id: string | null
  reply_to_external_id: string | null
  reply_excerpt: string | null
  is_backfill: boolean
  created_at: string
  /** Вложение сообщения (LEFT JOIN по message_id) — null, если файла нет. */
  attachment?: {
    id: number
    mime_type?: string | null
    original_name?: string | null
    size?: number | null
    media_type?: string | null
  } | null
}

export interface SupportCustomerProfileBrief {
  id: number
  identity_key: string
  tg_user_id: number | null
  username: string | null
  display_name: string | null
  email: string | null
  phone: string | null
}

export interface SupportCustomerCard {
  provider: string
  id: number | null
  telegram_id: number | null
  username: string
  display_name: string
  balance_kopeks: number | null
  balance_rub: number | null
  subscription: {
    status?: string
    end_date?: string
    is_trial?: boolean
    traffic?: { used_bytes?: number | null; limit_bytes?: number | null }
    subscription_url?: string | null
    tariff_name?: string | null
    device_limit?: number | null
    device_count?: number | null
    traffic_used_gb?: number | null
    traffic_limit_gb?: number | null
  }
  tickets_total: number
  last_activity: string | null
  recent_transactions: number
  remnawave: { available?: boolean; note?: string }
  fetched_at: string
}

export interface SupportListResult {
  items: SupportConversation[]
  total: number
  page: number
  per_page: number
}

export interface SupportConversationDetail {
  conversation: SupportConversation
  messages: SupportMessage[]
  customer: SupportCustomerProfileBrief | null
  /** Последняя ожидающая ИИ-предложка (B3b) — null, если её нет. */
  suggestion?: SupportAiSuggestion | null
}

export interface PollerStatus {
  enabled?: boolean
  running?: boolean
  last_poll?: string | null
  last_offset?: number
  last_error?: string | null
  ingested?: number
}

export interface SupportPollersResult {
  pollers: Record<string, PollerStatus>
}

export interface SupportConfigStatus {
  channels: string[]
  poll_interval_seconds: number
  reply_window_hours: number
}

export interface ListConversationParams {
  status?: string
  channel?: string
  priority?: string
  assignee_id?: number
  customer_id?: number
  unread_only?: boolean
  q?: string
  page?: number
  per_page?: number
}

// ── Ответ / статус: идемпотентность, lease, seen ──────────────────────────

export interface ReplyPayload {
  text: string
  attachment_ids?: string[]
  /** Идемпотентный ключ попытки (crypto.randomUUID). Повтор с тем же id не дублирует отправку. */
  client_msg_id?: string
  /** Перехватить диалог у другого оператора (обход 409 LOCKED_BY_OTHER). */
  force?: boolean
}

export interface ReplyResult {
  conversation_id: number
  message_id?: number
  external_msg_id?: string | null
  message_ids?: number[]
  count?: number
  /** Повтор с тем же client_msg_id: сообщение уже было отправлено. */
  repeated?: boolean
}

export interface StatePayload {
  status: ConversationStatus
  priority?: ConversationPriority
  /** Время последнего увиденного сообщения (ISO-8601) — для проверки CLIENT_WROTE. */
  seen_at?: string
}

export type PrioritySyncResult = 'synced' | 'unchanged' | 'skipped' | 'error'

export interface StateResult {
  conversation_id: number
  status: ConversationStatus
  priority?: ConversationPriority | null
  synced?: string
  /** Результат синхронизации приоритета в Bedolaga. */
  priority_synced?: PrioritySyncResult | string
}

/** Коды прикладных ошибок саппорта (лежат в detail.code). */
export type SupportErrorCode =
  | 'CLIENT_WROTE'
  | 'LOCKED_BY_OTHER'
  | 'REPLY_WINDOW_CLOSED'
  | 'KB_VERSION_CONFLICT'
  | 'KB_DOC_PUBLISHED'
  | 'IMPORT_TOO_LARGE'
  | 'IMPORT_PARSE_FAILED'
  | 'JOB_BUSY'
  | 'AI_DISABLED'
  | 'AI_PAUSED'
  | 'AI_KEY_MISSING'
  | 'PROVIDER_ERROR'
  | 'CONFLICT'
  | 'TEMPLATE_EXISTS'
  | 'SLA_POLICY_NOT_FOUND'

export interface SupportErrorDetail {
  code: SupportErrorCode | string
  error?: string
  message?: string
}

/**
 * Достаёт прикладной код ошибки из ответа бэкенда.
 * Поддерживает `{detail:{code}}`, `{detail:"CODE"}` и `{error:{code}}`.
 */
export function getSupportErrorCode(err: unknown): SupportErrorCode | string | undefined {
  const data = (err as { response?: { data?: unknown } } | null)?.response?.data as
    | { detail?: unknown; error?: unknown }
    | undefined
  if (!data || typeof data !== 'object') return undefined

  const detail = data.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'code' in detail) {
    const code = (detail as { code?: unknown }).code
    if (typeof code === 'string') return code
  }

  const error = data.error
  if (typeof error === 'string') return error
  if (error && typeof error === 'object' && 'code' in error) {
    const code = (error as { code?: unknown }).code
    if (typeof code === 'string') return code
  }

  return undefined
}

/** Понятные пользователю тексты для прикладных кодов (иначе — текст бэкенда). */
const SUPPORT_FRIENDLY_ERRORS: Record<string, string> = {
  TEMPLATE_EXISTS: 'Шаблон с таким ярлыком уже существует',
  SLA_POLICY_NOT_FOUND: 'Политика SLA не найдена',
}

/** Человекочитаемый текст ошибки для тела ответа (detail.error / error.message). */
export function getSupportErrorMessage(err: unknown): string | undefined {
  const data = (err as { response?: { data?: unknown } } | null)?.response?.data as
    | { detail?: unknown; error?: unknown }
    | undefined
  if (!data || typeof data !== 'object') return undefined

  const friendly = SUPPORT_FRIENDLY_ERRORS[getSupportErrorCode(err) ?? '']
  if (friendly) return friendly

  const detail = data.detail
  if (detail && typeof detail === 'object' && 'error' in detail) {
    const text = (detail as { error?: unknown }).error
    if (typeof text === 'string') return text
  }
  const error = data.error
  if (error && typeof error === 'object' && 'message' in error) {
    const text = (error as { message?: unknown }).message
    if (typeof text === 'string') return text
  }
  if (typeof error === 'string') return error
  return undefined
}

export interface SupportUploadResult {
  token: string
  media_type: string
  mime_type: string
  original_name: string
  bytes: number
  sha256: string
}

// ── База знаний (B3a) ──────────────────────────────────────────────────────

export type KbDocStatus = 'draft' | 'published' | 'archived'
export type KbDocSource = 'manual' | 'import' | 'candidate' | 'faq'

/** Элемент списка статей (`GET /support/kb`). */
export interface SupportKbListItem {
  id: number
  slug: string | null
  title: string
  source: string
  status: KbDocStatus
  version: number
  updated_at: string
  updated_by: number | null
  excerpt: string
}

export interface SupportKbListResult {
  items: SupportKbListItem[]
  total: number
  page: number
  per_page: number
}

/** Полная статья (`GET /support/kb/{id}`). */
export interface SupportKbDoc {
  id: number
  slug: string | null
  title: string
  body: string
  status: KbDocStatus
  version: number
  tags: string[]
  source: string
  updated_by: number | null
  published_at: string | null
  archived_at: string | null
  updated_at: string
  /** Прокси `updated_at` (в таблице 004 нет отдельного created_at). */
  created_at?: string | null
}

export interface SupportKbDocInput {
  title: string
  body: string
  slug?: string | null
  tags?: string[]
  source?: KbDocSource
}

export interface SupportKbDocCreateResult {
  id: number
  slug: string | null
  version: number
  status: KbDocStatus
}

export interface SupportKbDocUpdateResult {
  id: number
  slug: string | null
  version: number
  status: KbDocStatus
  updated_at: string
}

export interface SupportKbPublishResult {
  id: number
  status: 'published'
  published_at: string | null
}

export interface SupportKbArchiveResult {
  id: number
  status: 'archived'
  archived_at: string | null
}

export interface SupportKbRestoreResult {
  id: number
  status: 'draft'
}

export interface SupportKbSearchItem {
  id: number
  slug: string | null
  title: string
  rank: number
  snippet: string
}

export type KbCandidateStatus = 'new' | 'accepted' | 'rejected'

export interface SupportKbCandidate {
  id: number
  topic: string | null
  question: string | null
  answer: string | null
  occurrences: number
  source: string
  status: KbCandidateStatus
  created_at: string
  doc_id: number | null
}

export interface SupportKbCandidateListResult {
  items: SupportKbCandidate[]
  total: number
  page: number
  per_page: number
}

export interface SupportKbCandidateDecision {
  decision: 'accept' | 'reject'
  reason?: string
  title?: string
  body?: string
}

export interface SupportKbCandidateDecisionResult {
  id: number
  status: KbCandidateStatus
  doc_id?: number
}

// ── Импорт базы знаний ─────────────────────────────────────────────────────

export type SupportImportKind = 'text' | 'result_json'
export type SupportImportJobStatus = 'queued' | 'running' | 'done' | 'error'

export interface SupportImportRequest {
  kind: SupportImportKind
  text?: string
  /** Объект `result.json` либо его текст (файл читается на фронте). */
  payload?: Record<string, unknown> | string
  operator_names?: string[]
  dry_run?: boolean
}

export interface SupportImportStartResult {
  job_id: number
}

export interface SupportImportResult {
  questions: number
  pairs_created: number
  skipped_duplicates: number
  candidates_created: number
  errors: string[]
  dry_run?: boolean
  would_create?: number
  would_skip?: number
  would_create_candidates?: number
}

export interface SupportImportJob {
  id: number
  kind: SupportImportKind
  status: SupportImportJobStatus
  progress: number
  total: number | null
  result: SupportImportResult | null
  error: string | null
  started_at: string | null
  finished_at: string | null
}

export interface SupportImportCancelResult {
  status: SupportImportJobStatus | null
  error: string | null
}

// ── ИИ: предложки, настройки, статистика, песочница ──────────────────────

export type SupportAiMode = 'off' | 'shadow' | 'suggest' | 'auto'
export type SupportAiLevel = 'sure' | 'check' | 'unsure'
export type SupportSuggestionStatus =
  | 'pending'
  | 'sent'
  | 'edited'
  | 'rejected'
  | 'superseded'

export interface SupportAiGate {
  action: string | null
  reason: string | null
}

export interface SupportAiUsedDoc {
  doc_id: number | null
  title: string
}

/** Предложка/автоответ (`GET /support/suggestions/{id}`). */
export interface SupportAiSuggestion {
  id: number
  conversation_id: number | null
  message_id: number | null
  text: string | null
  final_text: string | null
  operator_note: string | null
  confidence: number | null
  level: SupportAiLevel
  used: SupportAiUsedDoc[]
  reason: string | null
  gate: SupportAiGate
  model: string | null
  status: SupportSuggestionStatus | null
  created_at: string | null
}

export interface SupportAiSuggestionListResult {
  items: SupportAiSuggestion[]
  total: number
  page: number
  per_page: number
}

export type SupportSuggestionDecision = 'send' | 'edit' | 'reject'

export interface SupportSuggestionDecisionPayload {
  decision: SupportSuggestionDecision
  final_text?: string
  /** Одна из причин отказа (REJECT_REASONS бэкенда). */
  reason?: string
}

export type SupportSuggestionDecisionResult =
  | { status: 'sent'; message_id: number }
  | { status: 'edited'; text: string }
  | { status: 'rejected' }

export interface SupportAiPause {
  until: string
  by: string
  note: string
}

export interface SupportAiSettings {
  mode: SupportAiMode
  effective_mode: SupportAiMode
  has_key: boolean
  paused: SupportAiPause | null
  model: string
  fallback_model: string
  base_url: string
  min_confidence: number
  require_kb: boolean
  auto_per_hour: number
  human_hold_minutes: number
  debounce_seconds: number
  kb_budget_chars: number
  language: string
  brand: string
  allowed_domains: string[]
}

export interface SupportAiSettingsUpdate {
  mode?: SupportAiMode
  min_confidence?: number
  require_kb?: boolean
  auto_per_hour?: number
  debounce_seconds?: number
}

export interface SupportAiPauseRequest {
  hours?: number
  until?: string
  note?: string
}

export interface SupportAiActivityParams {
  since?: string
  before?: number
  limit?: number
}

export interface SupportAiActivityItem {
  id: number
  conversation_id: number | null
  action: string | null
  gate_reason: string | null
  confidence: number | null
  model: string | null
  tokens_in: number | null
  tokens_out: number | null
  status: string | null
  created_at: string
  gate_action: string | null
}

export interface SupportAiStatsDay {
  date: string
  generated: number
  sent: number
}

export interface SupportAiStats {
  generated: number
  sent: number
  edited: number
  rejected: number
  superseded: number
  auto_sent: number
  suggest_sent: number
  shadow: number
  sent_rate: number
  avg_confidence: number
  tokens_in: number
  tokens_out: number
  by_day: SupportAiStatsDay[]
}

export interface SupportAiTryRequest {
  text: string
  assume_auto?: boolean
}

export interface SupportAiTryResult {
  draft: {
    reply: string
    operator_note: string
    used: SupportAiUsedDoc[]
    confidence: number | null
    clarify: boolean
    needs_human: boolean
  }
  gate: {
    action: string
    reason: string
    level?: SupportAiLevel
  }
}

// ── Фидбек по ответу ──────────────────────────────────────────────────────

export type SupportFeedbackVerdict = 'correct' | 'partial' | 'wrong'

export interface SupportFeedbackPayload {
  verdict: SupportFeedbackVerdict
  note?: string
  correct_answer?: string
}

export interface SupportFeedbackResult {
  qa_pair_id: number | null
}

// ── SLA (Этап C, C2) ───────────────────────────────────────────────────────

export type SupportSlaKind = 'first_response' | 'resolution'

/** Политика SLA по приоритету (`GET /support/sla/policies`). */
export interface SupportSlaPolicy {
  name: string
  first_response_minutes: number
  resolution_minutes: number
}

/** Активное SLA-событие; `overdue_minutes` отрицательный до дедлайна. */
export interface SupportSlaEvent {
  id: number
  conversation_id: number
  kind: SupportSlaKind
  due_at: string
  notified_at: string | null
  breached_at: string | null
  subject: string | null
  priority: ConversationPriority
  status: ConversationStatus
  assignee_id: number | null
  overdue_minutes: number | null
}

export interface SupportSlaBreaches {
  first_response: number
  resolution: number
}

export interface SupportSlaOverview {
  policies: SupportSlaPolicy[]
  breaches: SupportSlaBreaches
  events: SupportSlaEvent[]
}

// ── Шаблоны ответов (Этап C, C1) ───────────────────────────────────────────

/** Шаблон ответа оператора (`GET /support/templates`). */
export interface SupportTemplate {
  id: number
  shortcut: string
  title: string
  body: string
  category: string | null
  uses: number
  created_by: number | null
  created_at: string
  updated_at: string
}

export interface SupportTemplateInput {
  shortcut: string
  title: string
  body: string
  category?: string | null
}

export interface SupportTemplateListResult {
  items: SupportTemplate[]
  total: number
  page: number
  per_page: number
}

export interface ListTemplatesParams {
  q?: string
  category?: string
  page?: number
  per_page?: number
}

// ── Заметки о клиенте и присутствие (Этап C, C4) ──────────────────────────

/** Внутренняя заметка оператора о клиенте (`GET /support/customers/{id}/notes`). */
export interface SupportNote {
  id: number
  text: string
  actor_id: number | null
  actor_name: string
  created_at: string | null
}

export type SupportPresenceState = 'viewing' | 'typing'

/** Свежая отметка присутствия оператора в диалоге (TTL 120 с). */
export interface SupportPresenceItem {
  actor_id: number | null
  actor_name: string
  state: SupportPresenceState
  seen_at: string
}

export interface SupportPresencePing {
  conversation_id: number
  state: SupportPresenceState
}

export interface SupportPresencePingResult {
  ok: boolean
  throttled: boolean
}

export interface ListKbParams {
  status?: 'draft' | 'published' | 'archived' | 'all'
  q?: string
  page?: number
  per_page?: number
}

export interface ListKbCandidatesParams {
  status?: KbCandidateStatus | 'all'
  page?: number
  per_page?: number
}

// ── Аналитика и команда (Этап C, C3) ──────────────────────────────────────

/** Сводные счётчики за окно (`totals` в `GET /support/analytics`). */
export interface SupportAnalyticsTotals {
  conversations_created: number
  conversations_resolved: number
  messages_in: number
  messages_out: number
  open_now: number
  unassigned_now: number
}

/** Один день непрерывного ряда; пропущенные дни приходят нулями. */
export interface SupportAnalyticsDay {
  date: string
  created: number
  resolved: number
  incoming: number
  outgoing: number
}

export interface SupportAnalyticsChannel {
  channel: string
  conversations: number
  messages: number
}

export interface SupportAnalyticsPriority {
  priority: string
  conversations: number
  breached_first_response: number
}

/** Медиана и P90 первого ответа в минутах; `null` при отсутствии данных. */
export interface SupportAnalyticsFirstResponse {
  median_minutes: number | null
  p90_minutes: number | null
  count: number
}

export interface SupportAnalyticsOperator {
  actor_id: number
  login: string
  display_name: string
  replies: number
  conversations: number
  last_reply_at: string | null
}

export interface SupportAnalyticsAi {
  generated: number
  sent: number
  edited: number
  rejected: number
  auto_sent: number
  suggest_sent: number
  shadow: number
}

/** Полный снимок аналитики (`GET /support/analytics?days=`). */
export interface SupportAnalytics {
  range_days: number
  totals: SupportAnalyticsTotals
  by_day: SupportAnalyticsDay[]
  by_channel: SupportAnalyticsChannel[]
  by_priority: SupportAnalyticsPriority[]
  first_response: SupportAnalyticsFirstResponse
  by_operator: SupportAnalyticsOperator[]
  ai: SupportAnalyticsAi
}

/** Админ как оператор: нагрузка и присутствие (`GET /support/operators`). */
export interface SupportOperator {
  id: number
  login: string
  display_name: string
  status: string
  active_dialogs: number
  replies_30d: number
  present: boolean
}

/** Запись журнала аудита (`GET /support/audit`). */
export interface SupportAuditItem {
  id: number
  actor_id: number | null
  actor_name: string | null
  action: string
  resource: string
  resource_id: string | null
  payload: Record<string, unknown>
  ip: string | null
  created_at: string
}

export interface SupportAuditListResult {
  items: SupportAuditItem[]
  total: number
  page: number
  per_page: number
}

export interface SupportAuditActionCount {
  action: string
  count: number
}

export interface ListAuditParams {
  action?: string
  actor_id?: number
  page?: number
  per_page?: number
}

// ── Helpers ────────────────────────────────────────────────────────────────

/** Backend answers {success, data} — strip the envelope. */
function unwrap<T>(body: { success: boolean; data: T }): T {
  return body.data
}

function toParams(params: Record<string, string | number | boolean | null | undefined>): URLSearchParams {
  const out = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue
    out.set(key, String(value))
  }
  return out
}

// ── API ────────────────────────────────────────────────────────────────────

export const supportApi = {
  listConversations: (params: ListConversationParams = {}) =>
    api.get(`/support/conversations?${toParams({ ...params })}`).then((r) => unwrap<SupportListResult>(r.data)),

  getConversation: (id: number) =>
    api.get(`/support/conversations/${id}`).then((r) => unwrap<SupportConversationDetail>(r.data)),

  replyConversation: (id: number, data: ReplyPayload) =>
    api.post(`/support/conversations/${id}/reply`, data).then((r) => unwrap<ReplyResult>(r.data)),

  readConversation: (id: number) =>
    api.post(`/support/conversations/${id}/read`, {}).then((r) => unwrap<{ conversation_id: number; unread: number }>(r.data)),

  setState: (id: number, data: StatePayload) =>
    api.post(`/support/conversations/${id}/state`, data).then((r) => unwrap<StateResult>(r.data)),

  setAssignee: (id: number, data: { assignee_id: number | null }) =>
    api.post(`/support/conversations/${id}/assignee`, data).then((r) => unwrap<{ conversation_id: number; assignee_id: number | null }>(r.data)),

  getCustomer: (id: number) =>
    api.get(`/support/conversations/${id}/customer`).then((r) => unwrap<SupportCustomerCard>(r.data)),

  refreshCustomer: (id: number) =>
    api.post(`/support/conversations/${id}/customer/refresh`, {}).then((r) => unwrap<SupportCustomerCard>(r.data)),

  // ── Вложения (фаза 2b) ────────────────────────────────────────────

  /** Загрузить файл оператора → токен для attachment_ids в reply. */
  uploadAttachment: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/support/attachments', form).then((r) => unwrap<SupportUploadResult>(r.data))
  },

  /** Скачать содержимое вложения (blob через axios — Authorization из клиента). */
  getAttachmentBlob: (id: number, download = false) =>
    api
      .get(`/support/attachments/${id}${download ? '?download=1' : ''}`, { responseType: 'blob' })
      .then((r) => r.data as Blob),

  getPollers: () =>
    api.get('/support/pollers').then((r) => unwrap<SupportPollersResult>(r.data)),

  getConfigStatus: () =>
    api.get('/support/config-status').then((r) => unwrap<SupportConfigStatus>(r.data)),

  // ── База знаний ───────────────────────────────────────────────────

  listKb: (params: ListKbParams = {}) =>
    api.get(`/support/kb?${toParams({ ...params })}`).then((r) => unwrap<SupportKbListResult>(r.data)),

  getKb: (id: number) =>
    api.get(`/support/kb/${id}`).then((r) => unwrap<{ doc: SupportKbDoc }>(r.data)),

  createKb: (data: SupportKbDocInput) =>
    api.post('/support/kb', data).then((r) => unwrap<SupportKbDocCreateResult>(r.data)),

  updateKb: (id: number, data: SupportKbDocInput & { expected_version: number }) =>
    api.put(`/support/kb/${id}`, data).then((r) => unwrap<SupportKbDocUpdateResult>(r.data)),

  publishKb: (id: number, expected_version: number) =>
    api
      .post(`/support/kb/${id}/publish`, { expected_version })
      .then((r) => unwrap<SupportKbPublishResult>(r.data)),

  archiveKb: (id: number) =>
    api.post(`/support/kb/${id}/archive`, {}).then((r) => unwrap<SupportKbArchiveResult>(r.data)),

  restoreKb: (id: number) =>
    api.post(`/support/kb/${id}/restore`, {}).then((r) => unwrap<SupportKbRestoreResult>(r.data)),

  deleteKb: (id: number) =>
    api.delete(`/support/kb/${id}`).then((r) => unwrap<{ deleted: boolean }>(r.data)),

  searchKb: (q: string, limit = 10) =>
    api
      .get(`/support/kb/search?${toParams({ q, limit })}`)
      .then((r) => unwrap<{ items: SupportKbSearchItem[] }>(r.data)),

  listCandidates: (params: ListKbCandidatesParams = {}) =>
    api
      .get(`/support/kb/candidates?${toParams({ ...params })}`)
      .then((r) => unwrap<SupportKbCandidateListResult>(r.data)),

  decideCandidate: (id: number, data: SupportKbCandidateDecision) =>
    api
      .post(`/support/kb/candidates/${id}`, data)
      .then((r) => unwrap<SupportKbCandidateDecisionResult>(r.data)),

  // ── Импорт ────────────────────────────────────────────────────────

  importKb: (data: SupportImportRequest) =>
    api.post('/support/kb/import', data).then((r) => unwrap<SupportImportStartResult>(r.data)),

  getImportJob: (jobId: number) =>
    api.get(`/support/kb/import/${jobId}`).then((r) => unwrap<SupportImportJob>(r.data)),

  cancelImport: (jobId: number) =>
    api
      .post(`/support/kb/import/${jobId}/cancel`, {})
      .then((r) => unwrap<SupportImportCancelResult>(r.data)),

  // ── ИИ: предложки ─────────────────────────────────────────────────

  getSuggestion: (id: number) =>
    api.get(`/support/suggestions/${id}`).then((r) => unwrap<SupportAiSuggestion>(r.data)),

  decideSuggestion: (id: number, data: SupportSuggestionDecisionPayload) =>
    api
      .post(`/support/suggestions/${id}/decide`, data)
      .then((r) => unwrap<SupportSuggestionDecisionResult>(r.data)),

  // ── ИИ: настройки, пауза, активность, статистика, песочница ────────

  getAssistantSettings: () =>
    api.get('/support/assistant/settings').then((r) => unwrap<SupportAiSettings>(r.data)),

  updateAssistantSettings: (data: SupportAiSettingsUpdate) =>
    api.put('/support/assistant/settings', data).then((r) => unwrap<SupportAiSettings>(r.data)),

  pauseAssistant: (data: SupportAiPauseRequest) =>
    api.post('/support/assistant/pause', data).then((r) => unwrap<SupportAiPause>(r.data)),

  resumeAssistant: () =>
    api.delete('/support/assistant/pause').then((r) => unwrap<{ paused: false }>(r.data)),

  assistantActivity: (params: SupportAiActivityParams = {}) =>
    api
      .get(`/support/assistant/activity?${toParams({ ...params })}`)
      .then((r) => unwrap<{ items: SupportAiActivityItem[] }>(r.data)),

  assistantStats: (days = 30) =>
    api
      .get(`/support/assistant/stats?${toParams({ days })}`)
      .then((r) => unwrap<SupportAiStats>(r.data)),

  tryAssistant: (data: SupportAiTryRequest) =>
    api.post('/support/assistant/try', data).then((r) => unwrap<SupportAiTryResult>(r.data)),

  // ── Фидбек по ответу ──────────────────────────────────────────────

  messageFeedback: (messageId: number, data: SupportFeedbackPayload) =>
    api
      .post(`/support/messages/${messageId}/feedback`, data)
      .then((r) => unwrap<SupportFeedbackResult>(r.data)),

  // ── SLA ───────────────────────────────────────────────────────────

  listSlaPolicies: () =>
    api
      .get('/support/sla/policies')
      .then((r) => unwrap<{ items: SupportSlaPolicy[] }>(r.data)),

  updateSlaPolicy: (name: string, data: { first_response_minutes: number; resolution_minutes: number }) =>
    api
      .put(`/support/sla/policies/${encodeURIComponent(name)}`, data)
      .then((r) => unwrap<SupportSlaPolicy>(r.data)),

  getSlaOverview: (days = 7) =>
    api
      .get(`/support/sla/overview?${toParams({ days })}`)
      .then((r) => unwrap<SupportSlaOverview>(r.data)),

  // ── Шаблоны ответов ───────────────────────────────────────────────

  listTemplates: (params: ListTemplatesParams = {}) =>
    api
      .get(`/support/templates?${toParams({ ...params })}`)
      .then((r) => unwrap<SupportTemplateListResult>(r.data)),

  createTemplate: (data: SupportTemplateInput) =>
    api.post('/support/templates', data).then((r) => unwrap<SupportTemplate>(r.data)),

  updateTemplate: (id: number, data: SupportTemplateInput) =>
    api.put(`/support/templates/${id}`, data).then((r) => unwrap<SupportTemplate>(r.data)),

  deleteTemplate: (id: number) =>
    api.delete(`/support/templates/${id}`).then((r) => unwrap<{ deleted: boolean }>(r.data)),

  useTemplate: (id: number) =>
    api
      .post(`/support/templates/${id}/use`, {})
      .then((r) => unwrap<{ id: number; uses: number }>(r.data)),

  // ── Заметки о клиенте и присутствие ─────────────────────────────────

  listNotes: (customerId: number) =>
    api
      .get(`/support/customers/${customerId}/notes`)
      .then((r) => unwrap<{ items: SupportNote[] }>(r.data)),

  createNote: (customerId: number, data: { text: string }) =>
    api
      .post(`/support/customers/${customerId}/notes`, data)
      .then((r) => unwrap<SupportNote>(r.data)),

  deleteNote: (noteId: number) =>
    api.delete(`/support/notes/${noteId}`).then((r) => unwrap<{ deleted: boolean }>(r.data)),

  pingPresence: (data: SupportPresencePing) =>
    api.post('/support/presence', data).then((r) => unwrap<SupportPresencePingResult>(r.data)),

  getPresence: (conversationId: number) =>
    api
      .get(`/support/presence/${conversationId}`)
      .then((r) => unwrap<{ items: SupportPresenceItem[] }>(r.data)),

  // ── Аналитика и команда ───────────────────────────────────────────

  getAnalytics: (days = 30) =>
    api
      .get(`/support/analytics?${toParams({ days })}`)
      .then((r) => unwrap<SupportAnalytics>(r.data)),

  listOperators: () =>
    api
      .get('/support/operators')
      .then((r) => unwrap<{ items: SupportOperator[] }>(r.data)),

  listAudit: (params: ListAuditParams = {}) =>
    api
      .get(`/support/audit?${toParams({ ...params })}`)
      .then((r) => unwrap<SupportAuditListResult>(r.data)),

  listAuditActions: () =>
    api
      .get('/support/audit/actions')
      .then((r) => unwrap<{ items: SupportAuditActionCount[] }>(r.data)),
}
