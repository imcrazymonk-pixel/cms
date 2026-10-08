import { api } from './client'

export interface Post {
  id: number
  title: string
  slug: string
  content: string
  excerpt?: string
  status: 'draft' | 'published' | 'archived'
  category_id?: number
  category_name?: string
  image?: string
  user_id?: number
  author_name?: string
  views?: number
  seo_title?: string | null
  seo_description?: string | null
  canonical?: string | null
  featured?: boolean
  comments_enabled?: boolean
  tags?: string[]
  created_at: string
  updated_at: string
}

export const postsApi = {
  list: (params?: { page?: number; per_page?: number; sort?: string; dir?: string; search?: string }) =>
    api.get('/posts', { params }).then(r => r.data),
  get: (id: number) =>
    api.get(`/posts/${id}`).then(r => r.data),
  create: (data: Partial<Post>) =>
    api.post('/posts', data).then(r => r.data),
  update: (id: number, data: Partial<Post>) =>
    api.post(`/posts/${id}`, data).then(r => r.data),
  delete: (id: number) =>
    api.delete(`/posts/${id}`).then(r => r.data),
}