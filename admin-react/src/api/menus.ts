import { api } from './client'

export interface MenuItem {
  id: number
  name: string
  url: string
  location: string
}

export const menusApi = {
  list: () =>
    api.get('/menus').then(r => r.data),
  get: (id: number) =>
    api.get(`/menus/${id}`).then(r => r.data),
  create: (data: Partial<MenuItem>) =>
    api.post('/menus', data).then(r => r.data),
  update: (id: number, data: Partial<MenuItem>) =>
    api.post(`/menus/${id}`, data).then(r => r.data),
  delete: (id: number) =>
    api.delete(`/menus/${id}`).then(r => r.data),
}