import api from './client'

export interface Category {
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