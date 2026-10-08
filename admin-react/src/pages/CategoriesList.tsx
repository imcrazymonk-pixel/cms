import { useState, useEffect } from 'react'
import { categoriesApi, Category } from '../api/categories'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import {
  Folder, Plus, Pencil, Trash2, RefreshCw,
} from 'lucide-react'

export default function CategoriesList() {
  const [data, setData] = useState<Category[]>([])
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Add/Edit dialog
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingCat, setEditingCat] = useState<Category | null>(null)
  const [formName, setFormName] = useState('')
  const [formSlug, setFormSlug] = useState('')
  const [formDesc, setFormDesc] = useState('')

  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)

  const load = async () => {
    setIsPending(true); setError(null)
    try {
      const res = await categoriesApi.list() as { success: boolean; data: Category[] }
      if (res.success) setData(res.data)
      else setError('Не удалось загрузить категории')
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Ошибка') }
    finally { setIsPending(false) }
  }

  useEffect(() => { load() }, [])

  const openAdd = () => {
    setEditingCat(null)
    setFormName(''); setFormSlug(''); setFormDesc('')
    setDialogOpen(true)
  }

  const openEdit = (cat: Category) => {
    setEditingCat(cat)
    setFormName(cat.name); setFormSlug(cat.slug); setFormDesc(cat.description || '')
    setDialogOpen(true)
  }

  const save = async () => {
    if (!formName.trim()) return
    try {
      const payload: Record<string, unknown> = {
        name: formName.trim(),
        slug: formSlug.trim() || undefined,
        description: formDesc.trim(),
      }
      if (editingCat) {
        await categoriesApi.update(editingCat.id, payload)
      } else {
        await categoriesApi.create(payload)
      }
      setDialogOpen(false)
      load()
    } catch { /* ignore */ }
  }

  const doDelete = async (id: number) => {
    try { await categoriesApi.delete(id); setDeleteConfirmId(null); load() }
    catch { /* ignore */ }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Категории</h1>
          <p className="text-sm text-dark-200 mt-1">Управление категориями постов</p>
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
              <Folder className="w-10 h-10 text-dark-300 mx-auto mb-3" />
              <p className="text-base font-semibold mb-2">Категорий пока нет</p>
              <p className="text-sm text-dark-300 mb-3">Создайте первую категорию, чтобы упорядочить контент</p>
              <Button variant="default" onClick={openAdd}><Plus className="w-4 h-4" /> Создать категорию</Button>
            </CardContent></Card>
          ) : (
            <Card className="rounded-xl"><div className="overflow-x-auto">
              <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr className="border-b border-white/5 text-dark-300 text-xs uppercase tracking-wider">
                    <th className="text-left py-2 px-2.5">ID</th>
                    <th className="text-left py-2 px-2.5">Название</th>
                    <th className="text-left py-2 px-2.5">Slug</th>
                    <th className="text-left py-2 px-2.5">Описание</th>
                    <th className="w-24 py-2 px-2.5">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((cat: Category) => (
                    <tr key={cat.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-2 px-2.5 text-dark-300 text-xs">{cat.id}</td>
                      <td className="py-2 px-2.5 font-medium">{cat.name}</td>
                      <td className="py-2 px-2.5 text-dark-300 text-xs">{cat.slug}</td>
                      <td className="py-2 px-2.5 text-dark-300 text-xs max-w-[200px] truncate">{cat.description || '—'}</td>
                      <td className="py-2 px-2.5">
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => openEdit(cat)} className="h-7 w-7"><Pencil className="w-3.5 h-3.5" /></Button>
                          <Button variant="ghost" size="icon" onClick={() => setDeleteConfirmId(cat.id)} className="h-7 w-7 text-red-400"><Trash2 className="w-3.5 h-3.5" /></Button>
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

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={(v) => { if (!v) setDialogOpen(false) }}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editingCat ? 'Редактировать' : 'Добавить'} категорию</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Название *</Label>
              <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="Название категории" />
            </div>
            <div className="space-y-2">
              <Label>Slug (URL)</Label>
              <Input value={formSlug} onChange={(e) => setFormSlug(e.target.value)} placeholder="category-slug" />
            </div>
            <div className="space-y-2">
              <Label>Описание</Label>
              <Input value={formDesc} onChange={(e) => setFormDesc(e.target.value)} placeholder="Описание категории" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>Отмена</Button>
            <Button variant="default" onClick={save} disabled={!formName.trim()}>
              {editingCat ? 'Сохранить' : 'Добавить'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteConfirmId !== null}
        onOpenChange={(v) => { if (!v) setDeleteConfirmId(null) }}
        title="Удалить категорию?" description="Категория будет удалена."
        confirmLabel="Удалить" variant="destructive"
        onConfirm={() => { if (deleteConfirmId) doDelete(deleteConfirmId) }}
      />
    </div>
  )
}
