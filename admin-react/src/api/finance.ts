// Finance API uses /admin URLs (not /api prefix) — separate instance
import axios from 'axios'

const adminApi = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
})

// Copy auth interceptor from main client
adminApi.interceptors.request.use((config) => {
  const raw = localStorage.getItem('auth-store')
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      if (parsed.state?.token) {
        config.headers.Authorization = `Bearer ${parsed.state.token}`
      }
    } catch { /* ignore */ }
  }
  return config
})

adminApi.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth-store')
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  }
)

export interface Transaction {
  id: number
  date: string
  date_display: string
  month: string
  type: 'income' | 'expense'
  participant: string
  category: string
  amount: number
  description: string
}

export interface ChartPoint {
  key: string
  label: string
  income: number
  expense: number
  balance: number
}

export interface FinanceData {
  summary: { income: number; expense: number; balance: number; count: number }
  averages: {
    income: number
    expense: number
    balance: number
    total: number
    avg_days: number
    avg_weeks: number
    avg_months: number
    avg_years: number
    avg_income: { day: number; week: number; month: number; year: number }
    avg_expense: { day: number; week: number; month: number; year: number }
  }
  chart: {
    daily: ChartPoint[]
    weekly: ChartPoint[]
    monthly: ChartPoint[]
    yearly: ChartPoint[]
  }
  categories: { category: string; income: number; expense: number }[]
  transactions: Transaction[]
  pagination: { page: number; per_page: number; total: number; pages: number }
  settings: Record<string, unknown>
  all_months: string[]
  all_categories: string[]
  all_participants: string[]
  anomalies: number[]
}

export const financeApi = {
  getData: (params?: Record<string, unknown>) =>
    adminApi.get<FinanceData>('/admin/finance/api/data', { params }).then(r => r.data),

  add: (data: { date: string; type: string; category: string; participant: string; amount: number; description: string }) =>
    adminApi.post('/admin/finance/api/add', data).then(r => r.data),

  edit: (data: { id: number; date: string; type: string; category: string; participant: string; amount: number; description: string }) =>
    adminApi.post('/admin/finance/api/edit', data).then(r => r.data),

  delete: (id: number) =>
    adminApi.post('/admin/finance/api/delete', { id }).then(r => r.data),

  deleteBulk: (ids: number[]) =>
    adminApi.post('/admin/finance/api/delete-bulk', { ids }).then(r => r.data),

  bulkType: (ids: number[], value: string) =>
    adminApi.post('/admin/finance/api/bulk/type', { ids, type: value }).then(r => r.data),

  bulkCategory: (ids: number[], value: string) =>
    adminApi.post('/admin/finance/api/bulk/category', { ids, category: value }).then(r => r.data),

  bulkParticipant: (ids: number[], value: string) =>
    adminApi.post('/admin/finance/api/bulk/participant', { ids, participant: value }).then(r => r.data),

  bulkDescription: (ids: number[], value: string) =>
    adminApi.post('/admin/finance/api/bulk/description', { ids, description: value }).then(r => r.data),

  exportCsv: (params?: Record<string, unknown>) =>
    adminApi.get('/admin/finance/api/export/csv', { params, responseType: 'blob' }).then(r => r.data),

  exportSelected: (ids: number[]) =>
    adminApi.post('/admin/finance/api/export/selected', { ids }, { responseType: 'blob' }).then(r => r.data),

  getSettings: () =>
    adminApi.get('/admin/finance/api/settings').then(r => r.data),

  saveSettings: (data: Record<string, unknown>) =>
    adminApi.post('/admin/finance/api/settings', data).then(r => r.data),
}