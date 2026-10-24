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
  author: 'client' | 'agent' | 'system'
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
}

export interface SupportPollersResult {
  pollers: Record<string, { enabled?: boolean; running?: boolean; last_poll?: string | null; last_error?: string | null; ingested?: number }>
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

export interface SupportUploadResult {
  token: string
  media_type: string
  mime_type: string
  original_name: string
  bytes: number
  sha256: string
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

  replyConversation: (id: number, data: { text: string; attachment_ids?: string[] }) =>
    api.post(`/support/conversations/${id}/reply`, data).then((r) =>
      unwrap<{ conversation_id: number; message_id?: number; external_msg_id?: string | null; message_ids?: number[]; count?: number }>(r.data),
    ),

  readConversation: (id: number) =>
    api.post(`/support/conversations/${id}/read`, {}).then((r) => unwrap<{ conversation_id: number; unread: number }>(r.data)),

  setState: (id: number, data: { status: ConversationStatus; priority?: ConversationPriority }) =>
    api.post(`/support/conversations/${id}/state`, data).then((r) => unwrap<{ conversation_id: number; status: ConversationStatus; priority?: ConversationPriority | null; synced: string }>(r.data)),

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
}
