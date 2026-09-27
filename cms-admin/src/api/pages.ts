import api from './client'
import type { Category } from './categories'

export interface Page {
  id: number
  title: string
  slug: string
  content: string
  meta_description: string
  status: string
  author_name: string
  is_home: number
  created_at: string
  updated_at: string
  [key: string]: unknown
}

export async function getPages(): Promise<Page[]> {
  const { data } = await api.get('/pages')
  return data.data
}

export async function getPage(id: number): Promise<Page> {
  const { data } = await api.get(`/pages/${id}`)
  return data.data
}

export async function createPage(p: Partial<Page>): Promise<{ id: number }> {
  const { data } = await api.post('/pages', p)
  return data.data
}

export async function updatePage(id: number, p: Partial<Page>): Promise<void> {
  await api.post(`/pages/${id}`, p)
}

export async function deletePage(id: number): Promise<void> {
  await api.delete(`/pages/${id}`)
}