import { api } from './client'

export interface Page {
  id: number
  title: string
  slug: string
  content: string
  meta_description?: string
  status: string
  template?: string
  is_home?: number
  created_at: string
  updated_at?: string
}

export const pagesApi = {
  list: () =>
    api.get('/pages').then(r => r.data),
  get: (id: number) =>
    api.get(`/pages/${id}`).then(r => r.data),
  create: (data: Partial<Page>) =>
    api.post('/pages', data).then(r => r.data),
  update: (id: number, data: Partial<Page>) =>
    api.post(`/pages/${id}`, data).then(r => r.data),
  delete: (id: number) =>
    api.delete(`/pages/${id}`).then(r => r.data),
}