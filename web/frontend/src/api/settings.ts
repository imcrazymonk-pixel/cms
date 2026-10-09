import { api } from './client'

export interface RegistryItem {
  key: string
  label: string
  description: string
  category: string
  tab: string
  type: 'text' | 'textarea' | 'number' | 'bool' | 'select' | 'secret'
  default: string
  value: string
  source: 'db' | 'env' | 'default'
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

export const settingsApi = {
  getAll: () =>
    api.get<SettingsResponse>('/settings').then((r) => r.data),
  update: (data: Record<string, string>) =>
    api.post('/settings', data).then((r) => r.data),
  setKey: (key: string, value: string) =>
    api.put<RegistryItemResponse>(`/settings/${key}`, { value }).then((r) => r.data),
  resetKey: (key: string) =>
    api.delete<RegistryItemResponse>(`/settings/${key}`).then((r) => r.data),
}
