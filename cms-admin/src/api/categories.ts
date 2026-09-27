import api from './client'

export interface Category {
  [key: string]: unknown
  id: number
  name: string
  slug: string
  description: string
  posts_count: number
}

export async function getCategories(): Promise<Category[]> {
  const { data } = await api.get('/categories')
  return data.data
}

export async function createCategory(c: Partial<Category>): Promise<{ id: number }> {
  const { data } = await api.post('/categories', c)
  return data.data
}

export async function updateCategory(id: number, c: Partial<Category>): Promise<void> {
  await api.post(`/categories/${id}`, c)
}

export async function deleteCategory(id: number): Promise<void> {
  await api.delete(`/categories/${id}`)
}