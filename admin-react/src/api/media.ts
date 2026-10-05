import { api } from './client'

export interface MediaItem {
  id: number
  filename: string
  path: string
  alt?: string
  size?: number
  mime_type?: string
  uploaded_by?: number
  created_at: string
}

export const mediaApi = {
  list: () =>
    api.get('/media').then(r => r.data),
  upload: (formData: FormData) =>
    api.post('/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data),
  delete: (id: number) =>
    api.post('/media/delete', { id }).then(r => r.data),
}