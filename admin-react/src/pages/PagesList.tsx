import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { pagesApi, Page } from '../api/pages'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import {
  File, Plus, Pencil, Trash2, RefreshCw,
} from 'lucide-react'

function formatDate(raw: string): string {
  if (!raw) return '—'
  try {
    const d = new Date(raw)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`
  } catch { return raw }
}

export default function PagesList() {
  const navigate = useNavigate()
  const [data, setData] = useState<{ success: boolean; data: Page[] } | null>(null)
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)

  const load = async () => {
    setIsPending(true)
    setError(null)
    try {
      const res = await pagesApi.list() as { success: boolean; data: Page[] }
      if (res.success) setData(res)
      else setError('Не удалось загрузить страницы')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка подключения')
    } finally { setIsPending(false) }
  }

  useEffect(() => { load() }, [])

  const doDelete = async (id: number) => {
    try { await pagesApi.delete(id); setDeleteConfirmId(null); load() }
    catch { /* ignore */ }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Страницы</h1>
          <p className="text-sm text-dark-200 mt-1">Управление статическими страницами сайта</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw className="w-4 h-4" /> Обновить</Button>
          <Button variant="default" size="sm" onClick={() => navigate('/pages/create')}><Plus className="w-4 h-4" /> Добавить</Button>
        </div>
      </div>

      {isPending && <div className="space-y-2">{ [1,2,3].map(i => <Skeleton key={i} className="h-10 rounded-lg" />) }</div>}
      {error && <QueryError message={error} />}

      {!isPending && !error && data && (
        <>
          {data.data.length === 0 ? (
            <Card className="rounded-xl"><CardContent className="p-10 text-center">
              <File className="w-10 h-10 text-dark-300 mx-auto mb-3" />
              <p className="text-base font-semibold mb-2">Страниц пока нет</p>
              <Button variant="default" onClick={() => navigate('/pages/create')}><Plus className="w-4 h-4" /> Создать страницу</Button>
            </CardContent></Card>
          ) : (
            <Card className="rounded-xl"><div className="overflow-x-auto">
              <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr className="border-b border-white/5 text-dark-300 text-xs uppercase tracking-wider">
                    <th className="text-left py-2 px-2.5">Заголовок</th>
                    <th className="text-left py-2 px-2.5">Slug</th>
                    <th className="text-left py-2 px-2.5">Статус</th>
                    <th className="text-left py-2 px-2.5">Шаблон</th>
                    <th className="text-center py-2 px-2.5">Главная</th>
                    <th className="text-left py-2 px-2.5">Создан</th>
                    <th className="w-24 py-2 px-2.5">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.map((page: Page) => (
                    <tr key={page.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-2 px-2.5 font-medium">
                        <button onClick={() => navigate(`/pages/${page.id}`)} className="text-white hover:text-primary transition-colors bg-transparent border-0 p-0 cursor-pointer">{page.title}</button>
                      </td>
                      <td className="py-2 px-2.5 text-dark-300 text-xs">/{page.slug}</td>
                      <td className="py-2 px-2.5">
                        <Badge className={page.status === 'published' ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'}>
                          {page.status === 'published' ? 'Опубликована' : 'Черновик'}
                        </Badge>
                      </td>
                      <td className="py-2 px-2.5 text-dark-300 text-xs">{page.template || 'default'}</td>
                      <td className="py-2 px-2.5 text-center">{page.is_home ? <Badge className="bg-primary/20 text-primary">Да</Badge> : '—'}</td>
                      <td className="py-2 px-2.5 text-dark-300 text-xs whitespace-nowrap">{formatDate(page.created_at)}</td>
                      <td className="py-2 px-2.5">
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => navigate(`/pages/${page.id}`)} className="h-7 w-7"><Pencil className="w-3.5 h-3.5" /></Button>
                          <Button variant="ghost" size="icon" onClick={() => setDeleteConfirmId(page.id)} className="h-7 w-7 text-red-400"><Trash2 className="w-3.5 h-3.5" /></Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div></Card>
          )}

          <div className="text-sm text-dark-300">Всего: <strong className="text-white">{data.data.length}</strong></div>
        </>
      )}

      <ConfirmDialog
        open={deleteConfirmId !== null}
        onOpenChange={(v) => { if (!v) setDeleteConfirmId(null) }}
        title="Удалить страницу?"
        description="Страница будет удалена без возможности восстановления."
        confirmLabel="Удалить" variant="destructive"
        onConfirm={() => { if (deleteConfirmId) doDelete(deleteConfirmId) }}
      />
    </div>
  )
}
