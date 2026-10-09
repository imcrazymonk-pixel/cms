import { api } from './client'

export interface ThemeListItem {
  value: string
  label: string
}

export interface ThemeOption {
  label: string
  type: string
  default: string
  value: string
  hint?: string
  rows?: number
  options?: Record<string, string>
}

export interface ThemeGroup {
  name: string
  options: Record<string, ThemeOption>
}

export interface ThemeSettingsResponse {
  success: boolean
  data: {
    theme: string
    label: string
    options: Record<string, ThemeOption>
    groups: ThemeGroup[]
  }
}

export const themesApi = {
  list: () =>
    api.get<{ success: boolean; data: ThemeListItem[] }>('/themes').then(r => r.data),
  getSettings: () =>
    api.get<ThemeSettingsResponse>('/themes/settings').then(r => r.data),
  updateSettings: (data: Record<string, string>) =>
    api.post('/themes/settings', data).then(r => r.data),
}