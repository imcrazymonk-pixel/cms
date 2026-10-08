import { useState, useEffect } from 'react'
import { menusApi, MenuItem } from '../api/menus'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import {
  Menu, Plus, Pencil, Trash2, RefreshCw,
} from 'lucide-react'

const LOCATION_LABEL: Record<string, string> = { main: 'Главное меню', footer: 'Подвал' }

export default function MenusList() {
  const [data, setData] = useState<MenuItem[]>([])
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<MenuItem | null>(null)
  const [formName, setFormName] = useState('')
  const [formUrl, setFormUrl] = useState('')
  const [formLocation, setFormLocation] = useState('main')
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

  const openAdd = () => {
    setEditing(null); setFormName(''); setFormUrl(''); setFormLocation('main')
    setDialogOpen(true)
  }
  const openEdit = (m: MenuItem) => {
    setEditing(m); setFormName(m.name); setFormUrl(m.url); setFormLocation(m.location)
    setDialogOpen(true)
  }

  const save = async () => {
    if (!formName.trim() || !formUrl.trim()) return
    try {
      const payload: Record<string, unknown> = { name: formName.trim(), url: formUrl.trim(), location: formLocation }
      if (editing) await menusApi.update(editing.id, payload)
      else await menusApi.create(payload)
      setDialogOpen(false); load()
    } catch { /* ignore */ }
  }

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
          <Button variant="default" size="sm" onClick={openAdd}><Plus className="w-4 h-4" /> Добавить</Button>
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
              <Button variant="default" onClick={openAdd}><Plus className="w-4 h-4" /> Добавить пункт</Button>
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
                      <td className="py-2 px-2.5 font-medium">{m.name}</td>
                      <td className="py-2 px-2.5 text-dark-300 text-xs font-mono">/{m.url}</td>
                      <td className="py-2 px-2.5"><Badge className="bg-white/10 text-dark-200">{LOCATION_LABEL[m.location] || m.location}</Badge></td>
                      <td className="py-2 px-2.5">
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => openEdit(m)} className="h-7 w-7"><Pencil className="w-3.5 h-3.5" /></Button>
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

      <Dialog open={dialogOpen} onOpenChange={(v) => { if (!v) setDialogOpen(false) }}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? 'Редактировать' : 'Добавить'} пункт меню</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Название *</Label>
              <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="Главная" />
            </div>
            <div className="space-y-2">
              <Label>URL *</Label>
              <Input value={formUrl} onChange={(e) => setFormUrl(e.target.value)} placeholder="/about" />
            </div>
            <div className="space-y-2">
              <Label>Расположение</Label>
              <select value={formLocation} onChange={(e) => setFormLocation(e.target.value)}
                className="w-full px-3 py-2 rounded-xl text-sm"
                style={{ background: 'var(--surface-card)', border: '1px solid var(--glass-border)', color: 'var(--text-primary)' }}>
                {Object.entries(LOCATION_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>Отмена</Button>
            <Button variant="default" onClick={save} disabled={!formName.trim() || !formUrl.trim()}>
              {editing ? 'Сохранить' : 'Добавить'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
