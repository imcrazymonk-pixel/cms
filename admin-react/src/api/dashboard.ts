import { api } from './client'

export interface DashboardStats {
  posts: number
  comments: number
  users: number
  categories: number
}

export const dashboardApi = {
  getStats: () =>
    api.get<{ success: boolean; stats: DashboardStats }>('/dashboard/stats').then(r => r.data),
}