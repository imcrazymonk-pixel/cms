import { api } from './client'

export interface LogEntry {
  id: number
  level: string
  category?: string
  channel: string
  source?: string
  message: string
  context?: string
  created_at: string
}

export const logsApi = {
  list: (params?: { level?: string; category?: string; channel?: string; source?: string; q?: string; days?: number; page?: number; per_page?: number }) =>
    api.get('/logs', { params }).then(r => r.data),
  clear: (data?: { category?: string; channel?: string }) =>
    api.post('/logs/clear', data ?? {}).then(r => r.data),
}