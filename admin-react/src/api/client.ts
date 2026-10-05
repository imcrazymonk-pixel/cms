import axios from 'axios'

const API_BASE = typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL
  ? (import.meta.env.VITE_API_URL as string)
  : '/api'

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const raw = localStorage.getItem('auth-store')
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      if (parsed.state?.token) {
        config.headers.Authorization = `Bearer ${parsed.state.token}`
      }
    } catch { /* ignore corrupted state */ }
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth-store')
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  }
)

export default api