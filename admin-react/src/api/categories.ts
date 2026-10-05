import { api } from './client'

export interface Category {
  id: number
  name: string
  slug: string
  description?: string
  parent_id?: number
}

export const categoriesApi = {
  list: () =>
    api.get('/categories').then(r => r.data),
  get: (id: number) =>
    api.get(`/categories/${id}`).then(r => r.data),
  create: (data: Partial<Category>) =>
    api.post('/categories', data).then(r => r.data),
  update: (id: number, data: Partial<Category>) =>
    api.post(`/categories/${id}`, data).then(r => r.data),
  delete: (id: number) =>
    api.delete(`/categories/${id}`).then(r => r.data),
}