import api from './client'

export interface User {
  id: number
  login: string
  email: string
  role: string
}

export interface LoginResponse {
  success: boolean
  token: string
  user: User
}

export async function login(login: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', { login, password })
  return data
}

export async function getMe(): Promise<{ success: boolean; user: User }> {
  const { data } = await api.get('/auth/me')
  return data
}