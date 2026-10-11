import { api } from './client'

export interface User {
  id: number
  login: string
  email: string
  role: 'admin' | 'editor' | 'author'
  display_name?: string | null
  status: 'active' | 'inactive' | 'banned'
  avatar_url?: string | null
  bio?: string | null
  phone?: string | null
  telegram?: string | null
  website?: string | null
  location?: string | null
  posts_count?: number
  comments_count?: number
  created_at: string
  updated_at: string
}

export interface UserPayload {
  login: string
  email?: string
  role?: string
  display_name?: string
  status?: string
  avatar_url?: string
  bio?: string
  phone?: string
  telegram?: string
  website?: string
  location?: string
  password?: string
}

export const usersApi = {
  list: () =>
    api.get('/users').then(r => r.data),
  get: (id: number) =>
    api.get(`/users/${id}`).then(r => r.data),
  create: (data: UserPayload) =>
    api.post('/users', data).then(r => r.data),
  update: (id: number, data: UserPayload) =>
    api.post(`/users/${id}`, data).then(r => r.data),
  delete: (id: number) =>
    api.delete(`/users/${id}`).then(r => r.data),
  uploadAvatar: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/users/avatar', form).then(r => r.data)
  },
}
