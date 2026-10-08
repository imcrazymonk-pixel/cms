import { api } from './client'

// Matches GET /api/media response shape (core/routes.php)
export interface MediaItem {
  path: string
  url: string
  name: string
  size: number
  modified: number
}

export const mediaApi = {
  list: () =>
    api.get('/media').then(r => r.data),
  upload: (formData: FormData) =>
    api.post('/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data),
  delete: (path: string) =>
    api.post('/media/delete', { path }).then(r => r.data),
}
