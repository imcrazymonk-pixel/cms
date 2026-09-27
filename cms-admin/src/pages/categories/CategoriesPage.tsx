import { useState, useEffect } from 'react'
import { DataGrid, Button, Input, Card } from '../../components/ui'
import type { Column } from '../../components/ui'
import { getCategories, createCategory, updateCategory, deleteCategory, type Category } from '../../api/categories'

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [description, setDescription] = useState('')

  const fetch = async () => {
    setLoading(true)
    const data = await getCategories()
    setCategories(data)
    setLoading(false)
  }
  useEffect(() => { fetch() }, [])

  const resetForm = () => { setEditingId(null); setName(''); setSlug(''); setDescription('') }

  const handleSave = async () => {
    if (!name.trim()) return
    if (editingId) {
      await updateCategory(editingId, { name, slug, description } as Category)
    } else {
      await createCategory({ name, slug, description } as Category)
    }
    resetForm()
    fetch()
  }

  const handleEdit = (c: Category) => {
    setEditingId(c.id); setName(c.name); setSlug(c.slug); setDescription(c.description)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить категорию?')) return
    await deleteCategory(id)
    fetch()
  }

  const columns: Column<Category>[] = [
    { key: 'name', label: 'Название' },
    { key: 'slug', label: 'Slug' },
    { key: 'posts_count', label: 'Постов' },
    { key: 'description', label: 'Описание' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">Категории</h2>
          <p className="text-sm text-[var(--text-secondary)]">Управление категориями постов</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div>
          <Card>
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-4">
              {editingId ? 'Редактировать' : 'Создать категорию'}
            </h3>
            <div className="space-y-3">
              <Input label="Название" value={name} onChange={(e) => setName(e.target.value)} placeholder="Название" />
              <Input label="Slug" value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="category-slug" />
              <Input label="Описание" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Описание" />
              <div className="flex gap-2">
                <Button onClick={handleSave} disabled={!name.trim()}>{editingId ? 'Сохранить' : 'Создать'}</Button>
                {editingId && <Button variant="ghost" onClick={resetForm}>Отмена</Button>}
              </div>
            </div>
          </Card>
        </div>
        <div className="col-span-2">
          <DataGrid<Category>
            columns={columns}
            data={categories}
            keyField="id"
            total={categories.length}
            page={1}
            perPage={100}
            onPageChange={() => {}}
            loading={loading}
            actions={(row) => (
              <div className="flex flex-col">
                <button onClick={() => handleEdit(row)} className="px-3 py-1.5 text-left text-sm text-[var(--text-primary)] hover:bg-white/5">Редактировать</button>
                <button onClick={() => handleDelete(row.id)} className="px-3 py-1.5 text-left text-sm text-red-400 hover:bg-white/5">Удалить</button>
              </div>
            )}
          />
        </div>
      </div>
    </div>
  )
}