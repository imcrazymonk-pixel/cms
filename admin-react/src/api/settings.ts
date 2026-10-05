import { api } from './client'

export const settingsApi = {
  getAll: () =>
    api.get('/settings').then(r => r.data),
  update: (data: Record<string, string>) =>
    api.post('/settings', data).then(r => r.data),
}