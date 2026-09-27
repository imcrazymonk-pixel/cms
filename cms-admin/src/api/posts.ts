import api from './client'

export interface Post {
  [key: string]: unknown
  id: number
  title: string
  slug: string
  content: string
  excerpt: string
  status: string
  category_id: number | null
  category_name: string | null
  image: string
  user_id: number
  author_name: string
  created_at: string
  updated_at: string
}

export interface PostsResponse {
  success: boolean
  data: Post[]
  total: number
  page: number
  per_page: number
}

export async function getPosts(params: {
  page?: number
  per_page?: number
  sort?: string
  dir?: string
  search?: string
} = {}): Promise<PostsResponse> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.per_page) query.set('per_page', String(params.per_page))
  if (params.sort) query.set('sort', params.sort)
  if (params.dir) query.set('dir', params.dir)
  if (params.search) query.set('search', params.search)
  const { data } = await api.get<PostsResponse>(`/posts?${query}`)
  return data
}

export async function getPost(id: number): Promise<Post> {
  const { data } = await api.get(`/posts/${id}`)
  return data.data
}

export async function createPost(post: Partial<Post>): Promise<{ id: number }> {
  const { data } = await api.post('/posts', post)
  return data.data
}

export async function updatePost(id: number, post: Partial<Post>): Promise<void> {
  await api.post(`/posts/${id}`, post)
}

export async function deletePost(id: number): Promise<void> {
  await api.delete(`/posts/${id}`)
}