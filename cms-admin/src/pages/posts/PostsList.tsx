import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { DataGrid, Button, Badge, Input } from '../../components/ui'
import type { Column } from '../../components/ui'
import { getPosts, deletePost, type Post } from '../../api/posts'

const statusColors: Record<string, 'default' | 'success' | 'warning' | 'destructive' | 'secondary'> = {
  published: 'success', draft: 'warning', archived: 'destructive',
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

  const fetchPosts = async () => {
    setLoading(true)
    try {
      const res = await getPosts({ page, per_page: 15, sort: sortKey, dir: sortDir, search })
      setPosts(res.data)
      setTotal(res.total)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchPosts() }, [page, sortKey, sortDir, search])

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить пост?')) return
    await deletePost(id)
    fetchPosts()
  }

  const columns: Column<Post>[] = [
    { key: 'title', label: 'Заголовок', sortable: true, width: '35%' },
    { key: 'category_name', label: 'Категория', render: (r: Post) => r.category_name ?? '—' },
    { key: 'status', label: 'Статус', sortable: true, render: (r: Post) => <Badge variant={statusColors[r.status] ?? 'default'}>{r.status}</Badge> },
    { key: 'author_name', label: 'Автор' },
    { key: 'created_at', label: 'Создан', sortable: true, render: (r: Post) => new Date(r.created_at).toLocaleDateString('ru-RU') },
  ]

  return (
    <div>
      <div className="page-header mb-6">
        <div>
          <h1 className="page-header-title">Посты</h1>
          <p className="text-sm text-muted-foreground">Управление записями блога</p>
        </div>
        <div className="page-header-actions">
          <Button onClick={() => navigate('/admin/posts/create')}>+ Создать пост</Button>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <Input value={search} onChange={(e: React.ChangeEvent<HTMLInputElement>) => { setSearch(e.target.value); setPage(1) }} placeholder="Поиск по заголовку..." className="w-72" />
        {selectedIds.length > 0 && <span className="text-sm text-muted-foreground">Выбрано: {selectedIds.length}</span>}
      </div>

      <DataGrid<Post>
        columns={columns} data={posts} keyField="id" total={total} page={page} perPage={15}
        onPageChange={setPage}
        onSort={(key: string, dir: 'asc' | 'desc') => { setSortKey(key); setSortDir(dir); setPage(1) }}
        sortKey={sortKey} sortDir={sortDir}
        loading={loading}
        selectable selectedIds={selectedIds} onSelectionChange={setSelectedIds}
        actions={(row: Post) => (
          <div className="flex flex-col">
            <button onClick={() => navigate(`/admin/posts/${row.id}`)} className="px-3 py-1.5 text-left text-sm text-dark-50 hover:bg-[var(--glass-bg-hover)]">Редактировать</button>
            <button onClick={() => handleDelete(row.id)} className="px-3 py-1.5 text-left text-sm text-red-400 hover:bg-[var(--glass-bg-hover)]">Удалить</button>
          </div>
        )}
        emptyMessage="Постов пока нет"
      />
    </div>
  )
}