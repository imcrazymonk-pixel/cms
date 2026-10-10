import { api } from './client'

export interface DashboardStats {
  posts: number
  comments: number
  users: number
  categories: number
  posts_published: number
  posts_draft: number
  comments_total: number
  comments_approved: number
  users_active: number
}

export const dashboardApi = {
  getStats: () =>
    api.get<{ success: boolean; stats: DashboardStats }>('/dashboard/stats').then(r => r.data),
}