import api from './client'

export interface User {
  id: number
  login: string
  email: string
  role: string
  display_name: string
  status: string
  posts_count: number
  comments_count: number
  created_at: string
  [key: string]: unknown
}

export async function getUsers(): Promise<User[]> {
  const { data } = await api.get('/users')
  return data.data
}

export async function getUser(id: number): Promise<User> {
  const { data } = await api.get(`/users/${id}`)
  return data.data
}

export async function createUser(u: Partial<User> & { password: string }): Promise<{ id: number }> {
  const { data } = await api.post('/users', u)
  return data.data
}

export async function updateUser(id: number, u: Partial<User> & { password?: string }): Promise<void> {
  await api.post(`/users/${id}`, u)
}

export async function deleteUser(id: number): Promise<void> {
  await api.delete(`/users/${id}`)
}