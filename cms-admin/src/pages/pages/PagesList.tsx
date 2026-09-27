import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { DataGrid, Button, Badge } from '../../components/ui'
import type { Column } from '../../components/ui'
import { getPages, deletePage, type Page } from '../../api/pages'

export default function PagesListPage() {
  const navigate = useNavigate()
  const [pages, setPages] = useState<Page[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getPages().then(setPages).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить страницу?')) return
    await deletePage(id)
    setPages(await getPages())
  }

  const columns: Column<Page>[] = [
    { key: 'title', label: 'Заголовок' },
    { key: 'slug', label: 'Slug' },
    {
      key: 'status', label: 'Статус',
      render: (r) => <Badge variant={r.status === 'published' ? 'success' : 'warning'}>{r.status}</Badge>,
    },
    { key: 'author_name', label: 'Автор' },
    {
      key: 'created_at', label: 'Создана',
      render: (r) => new Date(r.created_at).toLocaleDateString('ru-RU'),
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">Страницы</h2>
          <p className="text-sm text-[var(--text-secondary)]">Управление статическими страницами</p>
        </div>
        <Button onClick={() => navigate('/admin/pages/create')}>+ Создать страницу</Button>
      </div>
      <DataGrid<Page>
        columns={columns}
        data={pages}
        keyField="id"
        total={pages.length}
        page={1}
        perPage={50}
        onPageChange={() => {}}
        loading={loading}
        actions={(row) => (
          <div className="flex flex-col">
            <button onClick={() => navigate(`/admin/pages/${row.id}`)} className="px-3 py-1.5 text-left text-sm text-[var(--text-primary)] hover:bg-white/5">Редактировать</button>
            <button onClick={() => handleDelete(row.id)} className="px-3 py-1.5 text-left text-sm text-red-400 hover:bg-white/5">Удалить</button>
          </div>
        )}
        emptyMessage="Страниц пока нет"
      />
    </div>
  )
}