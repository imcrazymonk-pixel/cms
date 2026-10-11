// Preferences API — uses /admin URLs (not /api prefix) — separate instance
import axios from 'axios'

const adminApi = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
})

// Copy auth interceptor from main client
adminApi.interceptors.request.use((config) => {
  const raw = localStorage.getItem('auth-store')
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      if (parsed.state?.token) {
        config.headers.Authorization = `Bearer ${parsed.state.token}`
      }
    } catch { /* ignore */ }
  }
  return config
})

adminApi.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth-store')
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  }
)

export interface PreferencesResponse {
  ok: boolean
  data: Record<string, unknown>
}

export const preferencesApi = {
  /** Load panel_ui_state from server for current user */
  getPreferences: () =>
    adminApi.get<PreferencesResponse>('/admin/settings/preferences').then((r) => r.data),

  /** Save full panel_ui_state blob to server */
  savePreferences: (data: Record<string, unknown>) =>
    adminApi.post<{ ok: boolean }>('/admin/settings/save-all-preferences', data).then((r) => r.data),
}