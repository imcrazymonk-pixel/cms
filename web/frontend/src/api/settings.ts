import { api } from './client'

export interface RegistryItem {
  key: string
  label: string
  description: string
  category: string
  tab: string
  type: 'text' | 'textarea' | 'number' | 'bool' | 'select' | 'secret' | 'json'
  default: string
  value: string
  source: 'db' | 'env' | 'default'
  is_set: boolean
  store: string
  options: string[] | null
  options_source: string | null
  is_secret: boolean
  is_readonly: boolean
  is_env_override: boolean
  env_var_name: string | null
  sort_order: number
}

export interface SettingsResponse {
  success: boolean
  data: Record<string, string>
  items: RegistryItem[]
  categories: Record<string, RegistryItem[]>
}

export interface RegistryItemResponse {
  success: boolean
  data?: RegistryItem
}

export interface ProxyInfo {
  mode: string
  effective: string
  url: string
  applied: boolean
  no_proxy?: string
}

export interface IntegrationTestResult {
  id: string
  ok: boolean
  status: 'ok' | 'error'
  message: string
  elapsed_ms: number
  egress_ip?: string | null
  bot_username?: string | null
  proxy: ProxyInfo
  details?: Record<string, unknown>
}

export interface ProxyTestResult {
  ok: boolean
  status: 'ok' | 'error'
  message: string
  egress_ip?: string | null
  http_status?: number
  elapsed_ms: number
  test_url?: string
  proxy: { mode: string; url: string; applied: boolean }
}

export interface TestEnvelope<T> {
  success: boolean
  data: T
}

export const settingsApi = {
  getAll: () =>
    api.get<SettingsResponse>('/settings').then((r) => r.data),
  update: (data: Record<string, string>) =>
    api.post('/settings', data).then((r) => r.data),
  setKey: (key: string, value: string) =>
    api.put<RegistryItemResponse>(`/settings/${key}`, { value }).then((r) => r.data),
  resetKey: (key: string) =>
    api.delete<RegistryItemResponse>(`/settings/${key}`).then((r) => r.data),
  testIntegration: (id: string, body: Record<string, string> = {}) =>
    api.post<TestEnvelope<IntegrationTestResult>>(
      `/settings/integrations/${id}/test`, body,
    ).then((r) => r.data),
  testProxy: (body: Record<string, string> = {}) =>
    api.post<TestEnvelope<ProxyTestResult>>(
      '/settings/integrations/proxy/test', body,
    ).then((r) => r.data),
}
