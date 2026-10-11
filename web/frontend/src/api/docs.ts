import { api } from './client'

export interface DocInfo {
  name: string
  title: string
  editable: boolean
}

export interface DocContent {
  name: string
  title: string
  editable: boolean
  raw: string
  html: string
}

export interface DocEntry {
  id: number
  day_of_week: string
  date: string
  time: string
  author: string
  title: string
  body: string
}

export interface EntriesResponse {
  success: boolean
  data: {
    name: string
    title: string
    editable: boolean
    header: string
    entries: DocEntry[]
  }
}

export interface UserName {
  id: number
  username: string
  display_name: string
}

export const docsApi = {
  list: () =>
    api.get<{ success: boolean; data: DocInfo[] }>('/docs/list').then((r) => r.data),

  get: (name: string) =>
    api.get<{ success: boolean; data: DocContent }>(`/docs/${name}`).then((r) => r.data),

  getEntries: (name: string) =>
    api.get<EntriesResponse>(`/docs/${name}/entries`).then((r) => r.data),

  createEntry: (name: string, data: {
    date: string
    time: string
    author: string
    title: string
    body: string
    also_history?: boolean
  }) =>
    api.post<{ success: boolean; data: { id: number } }>(`/docs/${name}/entries`, data).then((r) => r.data),

  updateEntry: (name: string, id: number, data: {
    date: string
    time: string
    author: string
    title: string
    body: string
  }) =>
    api.put<{ success: boolean }>(`/docs/${name}/entries/${id}`, data).then((r) => r.data),

  deleteEntry: (name: string, id: number) =>
    api.delete<{ success: boolean }>(`/docs/${name}/entries/${id}`).then((r) => r.data),

  getUserNames: () =>
    api.get<{ success: boolean; data: UserName[] }>('/users/names').then((r) => r.data),

  importFile: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<{ success: boolean; data: { imported: number } }>('/docs/changelog/import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },

  getExportUrl: () => '/api/docs/changelog/export',
}