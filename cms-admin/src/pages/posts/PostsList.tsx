import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { DataGrid, Button, Badge } from '../../components/ui'
import type { Column } from '../../components/ui'
import { getPosts, deletePost, type Post } from '../../api/posts'

const statusColors: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  published: 'success',
  draft: 'warning',
  archived: 'danger',
}

export default function PostsListPage() {
  const navigate = useNavigate()
  const [posts, setPosts] = useState<Post[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [sortKey, setSortKey] = useState('created_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [loading, setLoading] = useState(true)
  const [selectedIds, setSelectedIds] = useState<(string | number)[]>([])
  const [search, setSearch] = useState('')

  const fetchPosts = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getPosts({ page, per_page: 15, sort: sortKey, dir: sortDir, search })
      setPosts(res.data)
      setTotal(res.total)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [page, sortKey, sortDir, search])

  useEffect(() => { fetchPosts() }, [fetchPosts])

  const handleSort = (key: string, dir: 'asc' | 'desc') => {
    setSortKey(key)
    setSortDir(dir)
    setPage(1)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить пост?')) return
    await deletePost(id)
    fetchPosts()
  }

  const columns: Column<Post>[] = [
    { key: 'title', label: 'Заголовок', sortable: true, width: '35%' },
    { key: 'category_name', label: 'Категория', render: (r) => r.category_name ?? '—' },
    {
      key: 'status', label: 'Статус', sortable: true,
      render: (r) => <Badge variant={statusColors[r.status] ?? 'default'}>{r.status}</Badge>,
    },
    { key: 'author_name', label: 'Автор' },
    {
      key: 'created_at', label: 'Создан', sortable: true,
      render: (r) => new Date(r.created_at).toLocaleDateString('ru-RU'),
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">Посты</h2>
          <p className="text-sm text-[var(--text-secondary)]">Управление записями блога</p>
        </div>
        <Button onClick={() => navigate('/admin/posts/create')}>+ Создать пост</Button>
      </div>

      {/* Search + mass actions */}
      <div className="flex items-center gap-3 mb-4">
        <input
          type="text"
          placeholder="Поиск по заголовку..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          className="h-10 px-4 rounded-lg bg-white/5 border border-white/10 text-[var(--text-primary)] text-sm placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] w-72"
        />
        {selectedIds.length > 0 && (
          <span className="text-sm text-[var(--text-secondary)]">
            Выбрано: {selectedIds.length}
          </span>
        )}
      </div>

      <DataGrid<Post>
        columns={columns}
        data={posts}
        keyField="id"
        total={total}
        page={page}
        perPage={15}
        onPageChange={setPage}
        onSort={handleSort}
        sortKey={sortKey}
        sortDir={sortDir}
        loading={loading}
        selectable
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        actions={(row) => (
          <div className="flex flex-col">
            <button
              onClick={() => navigate(`/admin/posts/${row.id}`)}
              className="px-3 py-1.5 text-left text-sm text-[var(--text-primary)] hover:bg-white/5 transition-colors"
            >
              Редактировать
            </button>
            <button
              onClick={() => handleDelete(row.id)}
              className="px-3 py-1.5 text-left text-sm text-red-400 hover:bg-white/5 transition-colors"
            >
              Удалить
            </button>
          </div>
        )}
        emptyMessage="Постов пока нет"
      />
    </div>
  )
}