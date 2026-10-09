import { api } from './client'

export interface User {
  id: number
  login: string
  email: string
  role: 'admin' | 'editor' | 'author'
  display_name?: string
  status: 'active' | 'inactive' | 'banned'
  created_at: string
  updated_at: string
}

export const usersApi = {
  list: () =>
    api.get('/users').then(r => r.data),
  get: (id: number) =>
    api.get(`/users/${id}`).then(r => r.data),
  create: (data: Partial<User> & { password: string }) =>
    api.post('/users', data).then(r => r.data),
  update: (id: number, data: Partial<User> & { password?: string }) =>
    api.post(`/users/${id}`, data).then(r => r.data),
  delete: (id: number) =>
    api.delete(`/users/${id}`).then(r => r.data),
}