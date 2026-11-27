import axios from 'axios'
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
  updated_at?: string | null
}

/** One H1/H2 slice of the technical-history document, already rendered. */
export interface DocSection {
  title: string
  level: 1 | 2
  html: string
}

/** Base document (raw markdown + rendered html) with its last-updated stamp. */
export interface DocumentPayload {
  raw: string
  html: string
  updated_at: string | null
  /** Present on `GET /docs/history`; may be absent on older responses. */
  sections?: DocSection[]
}

export interface DocEntry {
  id: number
  day_of_week?: string
  date: string
  time: string
  author: string
  title: string
  body: string
  /** Rendered markdown of `body` (history blocks only). */
  body_html?: string
  origin?: 'manual' | 'changelog'
  source_changelog_id?: number | null
}

export interface EntriesResponse {
  success: boolean
  data: {
    name: string
    title: string
    editable: boolean
    header: string
    document?: DocumentPayload
    /** Present on `GET /docs/history/entries`. */
    sections?: DocSection[]
    entries: DocEntry[]
  }
}

export interface UserName {
  id: number
  username: string
  display_name: string
}

/**
 * Normalised error for docs endpoints. Carries the HTTP status and the
 * backend `code` (e.g. `CONFLICT`) so callers can react to optimistic-lock
 * failures instead of parsing axios internals.
 */
export class DocsApiError extends Error {
  readonly status?: number
  readonly code?: string

  constructor(message: string, status?: number, code?: string) {
    super(message)
    this.name = 'DocsApiError'
    this.status = status
    this.code = code
  }
}

interface ApiErrorBody {
  error?: unknown
  code?: unknown
}

function normalizeDocsError(err: unknown): DocsApiError {
  if (axios.isAxiosError(err)) {
    let message = err.message
    let code: string | undefined
    const payload: unknown = err.response?.data
    if (payload && typeof payload === 'object') {
      const body = payload as ApiErrorBody
      if (typeof body.error === 'string' && body.error.length > 0) {
        message = body.error
      }
      if (typeof body.code === 'string') {
        code = body.code
      }
    }
    return new DocsApiError(message, err.response?.status, code)
  }
  if (err instanceof Error) {
    return new DocsApiError(err.message)
  }
  return new DocsApiError('Неизвестная ошибка')
}

export const docsApi = {
  list: () =>
    api.get<{ success: boolean; data: DocInfo[] }>('/docs/list').then((r) => r.data),

  get: (name: string) =>
    api.get<{ success: boolean; data: DocContent }>(`/docs/${name}`).then((r) => r.data),

  getEntries: (name: string) =>
    api.get<EntriesResponse>(`/docs/${name}/entries`).then((r) => r.data),

  /**
   * Render markdown with the backend engine — the single renderer shared by
   * every preview and the history page, so they never diverge.
   */
  renderMarkdown: (markdown: string) =>
    api
      .post<{ success: boolean; data: { html: string } }>('/docs/render', { markdown })
      .then((r) => r.data.data.html)
      .catch((err: unknown) => {
        throw normalizeDocsError(err)
      }),

  /** Replace a document body (history only). 409 when `expectedUpdatedAt` is stale. */
  putDocument: (name: string, content: string, expectedUpdatedAt?: string | null) =>
    api
      .put<{ success: boolean; data: { updated_at: string | null } }>(`/docs/${name}`, {
        content,
        expected_updated_at: expectedUpdatedAt ?? null,
      })
      .then((r) => r.data)
      .catch((err: unknown) => {
        throw normalizeDocsError(err)
      }),

  /** Upload a .md file to replace a document body (history only). */
  importDocument: (name: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api
      .post<{ success: boolean; data: { updated_at: string | null; chars: number } }>(
        `/docs/${name}/import`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      .then((r) => r.data)
      .catch((err: unknown) => {
        throw normalizeDocsError(err)
      })
  },

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

  getExportUrl: (name: string = 'changelog') => `/api/docs/${name}/export`,
}
