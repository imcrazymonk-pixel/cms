import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { postsApi, Post } from '../api/posts'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import {
  FileText, Plus, Search, X, Pencil, Trash2, RefreshCw,
} from 'lucide-react'

interface PostListResponse {
  success: boolean
  data: Post[]
  total: number
  page: number
  per_page: number
}

const STATUS_BADGE: Record<string, string> = {
  published: 'bg-green-500/20 text-green-400',
  draft: 'bg-amber-500/20 text-amber-400',
  archived: 'bg-white/10 text-dark-300',
}

const STATUS_LABEL: Record<string, string> = {
  published: 'Опубликован',
  draft: 'Черновик',
  archived: 'Архив',
}

function formatDate(raw: string): string {
  if (!raw) return '—'
  try {
    const d = new Date(raw)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return raw
  }
}

export default function PostsList() {
  const navigate = useNavigate()
  const [data, setData] = useState<PostListResponse | null>(null)
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [searchQ, setSearchQ] = useState('')
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState('created_at')
  const [dir, setDir] = useState('DESC')

  // Selection & actions
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)

  const loadPosts = async () => {
    setIsPending(true)
    setError(null)
    try {
      const params: Record<string, unknown> = { page, per_page: 20, sort, dir }
      if (searchQ) params.search = searchQ
      const res = await postsApi.list(params) as PostListResponse
      if (res.success) {
        setData(res)
      } else {
        setError('Не удалось загрузить посты')
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка подключения')
    } finally {
      setIsPending(false)
    }
  }

  useEffect(() => {
    loadPosts()
  }, [page, sort, dir])

  const doSearch = () => {
    setPage(1)
    loadPosts()
  }

  const toggleSort = (field: string) => {
    if (sort === field) {
      setDir(dir === 'ASC' ? 'DESC' : 'ASC')
    } else {
      setSort(field)
      setDir('DESC')
    }
  }

  const sortIndicator = (field: string): string =>
    sort === field ? (dir === 'ASC' ? ' ▲' : ' ▼') : ''

  const doDelete = async (id: number) => {
    try {
      await postsApi.delete(id)
      setDeleteConfirmId(null)
      loadPosts()
    } catch { /* ignore */ }
  }

  // ── Render ──
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Посты</h1>
          <p className="text-sm text-dark-200 mt-1">Управление записями блога</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={loadPosts}>
            <RefreshCw className="w-4 h-4" /> Обновить
          </Button>
          <Button variant="default" size="sm" onClick={() => navigate('/posts/create')}>
            <Plus className="w-4 h-4" /> Добавить
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-2">
        <Input
          placeholder="Поиск по заголовку или slug…"
          value={searchQ}
          onChange={(e) => setSearchQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') doSearch() }}
          className="flex-1 max-w-sm"
        />
        <Button variant="secondary" size="sm" onClick={doSearch}>
          <Search className="w-4 h-4" /> Найти
        </Button>
        {searchQ && (
          <Button variant="ghost" size="sm" onClick={() => { setSearchQ(''); setPage(1); loadPosts() }}>
            <X className="w-4 h-4" /> Сброс
          </Button>
        )}
      </div>

      {/* Loading */}
      {isPending && (
        <div className="space-y-2">
          {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10 rounded-lg" />)}
        </div>
      )}

      {/* Error */}
      {error && <QueryError message={error} />}

      {/* Table */}
      {!isPending && !error && data && (
        <>
          {data.data.length === 0 ? (
            <Card className="rounded-xl">
              <CardContent className="p-10 text-center">
                <FileText className="w-10 h-10 text-dark-300 mx-auto mb-3" />
                <p className="text-base font-semibold mb-2">
                  {searchQ ? 'Ничего не найдено' : 'Постов пока нет'}
                </p>
                <p className="text-sm text-dark-300 mb-3">
                  {searchQ ? 'Попробуйте изменить поисковый запрос' : 'Создайте первый пост'}
                </p>
                {!searchQ && (
                  <Button variant="default" onClick={() => navigate('/posts/create')}>
                    <Plus className="w-4 h-4" /> Создать пост
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="rounded-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                  <thead>
                    <tr className="border-b border-white/5 text-dark-300 text-xs uppercase tracking-wider">
                      <th className="w-8 py-2 px-2"><input type="checkbox" onChange={(e) => {
                        if (e.target.checked) setSelectedIds(new Set(data.data.map(p => p.id)))
                        else setSelectedIds(new Set())
                      }} /></th>
                      <th className="text-left py-2 px-2.5 cursor-pointer hover:text-dark-100" onClick={() => toggleSort('title')}>
                        Заголовок{sortIndicator('title')}
                      </th>
                      <th className="text-left py-2 px-2.5">Slug</th>
                      <th className="text-left py-2 px-2.5 cursor-pointer hover:text-dark-100" onClick={() => toggleSort('status')}>
                        Статус{sortIndicator('status')}
                      </th>
                      <th className="text-left py-2 px-2.5">Категория</th>
                      <th className="text-left py-2 px-2.5">Автор</th>
                      <th className="text-right py-2 px-2.5">Просмотры</th>
                      <th className="text-left py-2 px-2.5 cursor-pointer hover:text-dark-100" onClick={() => toggleSort('created_at')}>
                        Создан{sortIndicator('created_at')}
                      </th>
                      <th className="w-24 py-2 px-2.5">Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.data.map((post: Post) => (
                      <tr key={post.id} className="border-b border-white/5 hover:bg-white/5">
                        <td className="py-2 px-2">
                          <input type="checkbox" checked={selectedIds.has(post.id)} onChange={(e) => {
                            const next = new Set(selectedIds)
                            e.target.checked ? next.add(post.id) : next.delete(post.id)
                            setSelectedIds(next)
                          }} />
                        </td>
                        <td className="py-2 px-2.5 font-medium">
                          <button onClick={() => navigate(`/posts/${post.id}`)} className="text-white hover:text-primary transition-colors bg-transparent border-0 p-0 cursor-pointer">
                            {post.title}
                          </button>
                        </td>
                        <td className="py-2 px-2.5 text-dark-300 text-xs">{post.slug}</td>
                        <td className="py-2 px-2.5">
                          <Badge className={STATUS_BADGE[post.status] || 'bg-white/10 text-dark-300'}>
                            {STATUS_LABEL[post.status] || post.status}
                          </Badge>
                        </td>
                        <td className="py-2 px-2.5 text-dark-300 text-xs">{post.category_name || '—'}</td>
                        <td className="py-2 px-2.5 text-dark-300 text-xs">{post.author_name || '—'}</td>
                        <td className="py-2 px-2.5 text-right text-dark-300 text-xs font-semibold">
                          {post.views !== undefined ? String(post.views) : '—'}
                        </td>
                        <td className="py-2 px-2.5 text-dark-300 text-xs whitespace-nowrap">{formatDate(post.created_at)}</td>
                        <td className="py-2 px-2.5">
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="icon" onClick={() => navigate(`/posts/${post.id}`)} className="h-7 w-7">
                              <Pencil className="w-3.5 h-3.5" />
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => setDeleteConfirmId(post.id)} className="h-7 w-7 text-red-400">
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {(() => {
                const pages = Math.ceil(data.total / data.per_page)
                if (pages <= 1) return null
                return (
                  <div className="flex items-center justify-center gap-2 py-3">
                    <Button variant="ghost" size="sm" disabled={page <= 1}
                      onClick={() => { setPage(page - 1); setSelectedIds(new Set()) }}>
                      ← Назад
                    </Button>
                    <span className="text-sm text-dark-300">
                      {page} / {pages}
                    </span>
                    <Button variant="ghost" size="sm" disabled={page >= pages}
                      onClick={() => { setPage(page + 1); setSelectedIds(new Set()) }}>
                      Вперёд →
                    </Button>
                  </div>
                )
              })()}
            </Card>
          )}

          {/* Total count */}
          <div className="text-sm text-dark-300">
            Всего: <strong className="text-white">{data.total}</strong>
          </div>
        </>
      )}

      {/* Delete Confirm */}
      <ConfirmDialog
        open={deleteConfirmId !== null}
        onOpenChange={(v) => { if (!v) setDeleteConfirmId(null) }}
        title="Удалить пост?"
        description="Пост будет удалён без возможности восстановления."
        confirmLabel="Удалить"
        variant="destructive"
        onConfirm={() => { if (deleteConfirmId) doDelete(deleteConfirmId) }}
      />
    </div>
  )
}