import { api } from './client'

export const financeApi = {
  getData: (params?: { page?: number; per_page?: number; sort?: string; dir?: string; type?: string; category?: string; date_from?: string; date_to?: string }) =>
    api.get('/finance/api/data', { params }).then(r => r.data),
  add: (data: Record<string, unknown>) =>
    api.post('/finance/api/add', data).then(r => r.data),
  edit: (data: Record<string, unknown>) =>
    api.post('/finance/api/edit', data).then(r => r.data),
  delete: (data: { id: number }) =>
    api.post('/finance/api/delete', data).then(r => r.data),
  deleteBulk: (data: { ids: number[] }) =>
    api.post('/finance/api/delete-bulk', data).then(r => r.data),
  getSettings: () =>
    api.get('/finance/api/settings').then(r => r.data),
  saveSettings: (data: Record<string, unknown>) =>
    api.post('/finance/api/settings', data).then(r => r.data),
}