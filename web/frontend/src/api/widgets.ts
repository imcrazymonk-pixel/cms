import { api } from './client'

export interface Widget {
  id: number
  area: string
  title: string
  content: string
  sort_order: number
  created_at: string
}

export const widgetsApi = {
  list: () =>
    api.get('/widgets').then(r => r.data),
  get: (id: number) =>
    api.get(`/widgets/${id}`).then(r => r.data),
  create: (data: Partial<Widget>) =>
    api.post('/widgets', data).then(r => r.data),
  update: (id: number, data: Partial<Widget>) =>
    api.post(`/widgets/${id}`, data).then(r => r.data),
  delete: (id: number) =>
    api.delete(`/widgets/${id}`).then(r => r.data),
}