import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { menusApi, MenuItem } from '../api/menus'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import {
  Menu, Plus, Pencil, Trash2, RefreshCw,
} from 'lucide-react'

const LOCATION_LABEL: Record<string, string> = { main: 'Главное меню', footer: 'Подвал' }

export default function MenusList() {
  const navigate = useNavigate()
  const [data, setData] = useState<MenuItem[]>([])
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)

  const load = async () => {
    setIsPending(true); setError(null)
    try {
      const res = await menusApi.list() as { success: boolean; data: MenuItem[] }
      if (res.success) setData(res.data)
      else setError('Не удалось загрузить меню')
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Ошибка') }
    finally { setIsPending(false) }
  }

  useEffect(() => { load() }, [])

  const doDelete = async (id: number) => {
    try { await menusApi.delete(id); setDeleteConfirmId(null); load() }
    catch { /* ignore */ }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Меню</h1>
          <p className="text-sm text-dark-200 mt-1">Управление пунктами навигации сайта</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw className="w-4 h-4" /> Обновить</Button>
          <Button variant="default" size="sm" onClick={() => navigate('/menus/create')}><Plus className="w-4 h-4" /> Добавить</Button>
        </div>
      </div>

      {isPending && <>{ [1,2,3].map(i => <Skeleton key={i} className="h-10 rounded-lg" />) }</>}
      {error && <QueryError message={error} />}

      {!isPending && !error && (
        <>
          {data.length === 0 ? (
            <Card className="rounded-xl"><CardContent className="p-10 text-center">
              <Menu className="w-10 h-10 text-dark-300 mx-auto mb-3" />
              <p className="text-base font-semibold mb-2">Пунктов меню пока нет</p>
              <Button variant="default" onClick={() => navigate('/menus/create')}><Plus className="w-4 h-4" /> Добавить пункт</Button>
            </CardContent></Card>
          ) : (
            <Card className="rounded-xl"><div className="overflow-x-auto">
              <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr className="border-b border-white/5 text-dark-300 text-xs uppercase tracking-wider">
                    <th className="text-left py-2 px-2.5">Название</th>
                    <th className="text-left py-2 px-2.5">URL</th>
                    <th className="text-left py-2 px-2.5">Расположение</th>
                    <th className="w-24 py-2 px-2.5">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((m: MenuItem) => (
                    <tr key={m.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-2 px-2.5 font-medium">
                        <button onClick={() => navigate(`/menus/${m.id}`)} className="text-white hover:text-primary transition-colors bg-transparent border-0 p-0 cursor-pointer">{m.name}</button>
                      </td>
                      <td className="py-2 px-2.5 text-dark-300 text-xs font-mono">/{m.url}</td>
                      <td className="py-2 px-2.5"><Badge className="bg-white/10 text-dark-200">{LOCATION_LABEL[m.location] || m.location}</Badge></td>
                      <td className="py-2 px-2.5">
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => navigate(`/menus/${m.id}`)} className="h-7 w-7"><Pencil className="w-3.5 h-3.5" /></Button>
                          <Button variant="ghost" size="icon" onClick={() => setDeleteConfirmId(m.id)} className="h-7 w-7 text-red-400"><Trash2 className="w-3.5 h-3.5" /></Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div></Card>
          )}
          <div className="text-sm text-dark-300">Всего: <strong className="text-white">{data.length}</strong></div>
        </>
      )}

      <ConfirmDialog
        open={deleteConfirmId !== null}
        onOpenChange={(v) => { if (!v) setDeleteConfirmId(null) }}
        title="Удалить пункт меню?" description="Пункт меню будет удалён."
        confirmLabel="Удалить" variant="destructive"
        onConfirm={() => { if (deleteConfirmId) doDelete(deleteConfirmId) }}
      />
    </div>
  )
}
