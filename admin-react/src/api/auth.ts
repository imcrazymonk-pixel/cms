import { api } from './client'

export interface LoginResponse {
  success: boolean
  token: string
  user: { id: number; login: string; email: string; role: string }
}

export const authApi = {
  login: (login: string, password: string) =>
    api.post<LoginResponse>('/auth/login', { login, password }).then(r => r.data),
  me: () =>
    api.get<{ success: boolean; user: LoginResponse['user'] }>('/auth/me').then(r => r.data),
}