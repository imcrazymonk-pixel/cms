import { useState, useEffect } from 'react'
import { widgetsApi, Widget } from '../api/widgets'
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
  Puzzle, Plus, Pencil, Trash2, RefreshCw,
} from 'lucide-react'

export default function WidgetsList() {
  const [data, setData] = useState<Widget[]>([])
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Widget | null>(null)
  const [formArea, setFormArea] = useState('')
  const [formTitle, setFormTitle] = useState('')
  const [formContent, setFormContent] = useState('')
  const [formSort, setFormSort] = useState('0')
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)

  const load = async () => {
    setIsPending(true); setError(null)
    try {
      const res = await widgetsApi.list() as { success: boolean; data: Widget[] }
      if (res.success) setData(res.data)
      else setError('Не удалось загрузить виджеты')
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Ошибка') }
    finally { setIsPending(false) }
  }

  useEffect(() => { load() }, [])

  const openAdd = () => {
    setEditing(null); setFormArea('sidebar'); setFormTitle(''); setFormContent(''); setFormSort('0')
    setDialogOpen(true)
  }
  const openEdit = (w: Widget) => {
    setEditing(w); setFormArea(w.area); setFormTitle(w.title); setFormContent(w.content); setFormSort(String(w.sort_order))
    setDialogOpen(true)
  }

  const save = async () => {
    if (!formTitle.trim()) return
    try {
      const payload: Record<string, unknown> = {
        area: formArea, title: formTitle.trim(), content: formContent,
        sort_order: parseInt(formSort) || 0,
      }
      if (editing) await widgetsApi.update(editing.id, payload)
      else await widgetsApi.create(payload)
      setDialogOpen(false); load()
    } catch { /* ignore */ }
  }

  const doDelete = async (id: number) => {
    try { await widgetsApi.delete(id); setDeleteConfirmId(null); load() }
    catch { /* ignore */ }
  }

  const AREA_LABEL: Record<string, string> = { sidebar: 'Сайдбар', footer: 'Подвал', header: 'Шапка' }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Виджеты</h1>
          <p className="text-sm text-dark-200 mt-1">Управление боковыми блоками сайта</p>
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
              <Puzzle className="w-10 h-10 text-dark-300 mx-auto mb-3" />
              <p className="text-base font-semibold mb-2">Виджетов пока нет</p>
              <Button variant="default" onClick={openAdd}><Plus className="w-4 h-4" /> Создать виджет</Button>
            </CardContent></Card>
          ) : (
            <Card className="rounded-xl"><div className="overflow-x-auto">
              <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr className="border-b border-white/5 text-dark-300 text-xs uppercase tracking-wider">
                    <th className="text-left py-2 px-2.5">Название</th>
                    <th className="text-left py-2 px-2.5">Область</th>
                    <th className="text-left py-2 px-2.5">Содержимое</th>
                    <th className="text-right py-2 px-2.5">Порядок</th>
                    <th className="w-24 py-2 px-2.5">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((w: Widget) => (
                    <tr key={w.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-2 px-2.5 font-medium">{w.title}</td>
                      <td className="py-2 px-2.5"><Badge className="bg-white/10 text-dark-200">{AREA_LABEL[w.area] || w.area}</Badge></td>
                      <td className="py-2 px-2.5 text-dark-300 text-xs max-w-[300px] truncate">{w.content.replace(/<[^>]*>/g, '').substring(0, 80)}</td>
                      <td className="py-2 px-2.5 text-right text-dark-300 text-xs">{w.sort_order}</td>
                      <td className="py-2 px-2.5">
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => openEdit(w)} className="h-7 w-7"><Pencil className="w-3.5 h-3.5" /></Button>
                          <Button variant="ghost" size="icon" onClick={() => setDeleteConfirmId(w.id)} className="h-7 w-7 text-red-400"><Trash2 className="w-3.5 h-3.5" /></Button>
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
          <DialogHeader><DialogTitle>{editing ? 'Редактировать' : 'Добавить'} виджет</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Название *</Label>
              <Input value={formTitle} onChange={(e) => setFormTitle(e.target.value)} placeholder="Заголовок виджета" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Область</Label>
                <select value={formArea} onChange={(e) => setFormArea(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl text-sm"
                  style={{ background: 'var(--surface-card)', border: '1px solid var(--glass-border)', color: 'var(--text-primary)' }}>
                  {Object.entries(AREA_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Порядок</Label>
                <Input type="number" value={formSort} onChange={(e) => setFormSort(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Содержимое (HTML)</Label>
              <textarea value={formContent} onChange={(e) => setFormContent(e.target.value)}
                className="w-full min-h-[150px] px-3 py-2.5 rounded-xl text-sm font-mono"
                style={{ background: 'var(--surface-card)', border: '1px solid var(--glass-border)', color: '#d1d5db' }}
                placeholder="HTML-содержимое виджета..." />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>Отмена</Button>
            <Button variant="default" onClick={save} disabled={!formTitle.trim()}>{editing ? 'Сохранить' : 'Добавить'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteConfirmId !== null}
        onOpenChange={(v) => { if (!v) setDeleteConfirmId(null) }}
        title="Удалить виджет?" description="Виджет будет удалён."
        confirmLabel="Удалить" variant="destructive"
        onConfirm={() => { if (deleteConfirmId) doDelete(deleteConfirmId) }}
      />
    </div>
  )
}