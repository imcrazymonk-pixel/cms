import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { Button, Input, Card, Label } from '../../components/ui'
import { getPost, createPost, updatePost } from '../../api/posts'
import { getCategories, type Category } from '../../api/categories'

export default function PostFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = !!id

  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [content, setContent] = useState('')
  const [excerpt, setExcerpt] = useState('')
  const [status, setStatus] = useState('draft')
  const [categoryId, setCategoryId] = useState<number | ''>('')
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {})
    if (isEdit && id) {
      setLoading(true)
      getPost(Number(id)).then((post) => {
        setTitle(post.title); setSlug(post.slug); setContent(post.content)
        setExcerpt(post.excerpt ?? ''); setStatus(post.status)
        setCategoryId(post.category_id ?? '')
      }).finally(() => setLoading(false))
    }
  }, [id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const data = { title, slug, content, excerpt, status, category_id: categoryId || null }
      if (isEdit && id) { await updatePost(Number(id), data); navigate('/admin/posts') }
      else { const r = await createPost(data); navigate(`/admin/posts/${r.id}`) }
    } finally { setSaving(false) }
  }

  if (loading) return <div className="text-center py-12 text-muted-foreground">Загрузка...</div>

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl md:text-2xl font-bold" style={{ color: 'var(--text-body)' }}>
            {isEdit ? 'Редактировать пост' : 'Создать пост'}
          </h2>
          <p className="text-sm text-muted-foreground">{isEdit ? `ID: ${id}` : 'Новая запись в блоге'}</p>
        </div>
        <Button variant="ghost" onClick={() => navigate('/admin/posts')}>← Назад</Button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <Card>
          <div className="space-y-4 p-4 md:p-6">
            <div className="space-y-2">
              <Label>Заголовок</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Введите заголовок" required />
            </div>
            <div className="space-y-2">
              <Label>Slug (URL)</Label>
              <Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="my-post-slug" />
            </div>
            <div className="space-y-2">
              <Label>Содержание</Label>
              <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={14}
                className="w-full px-4 py-3 rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-sm text-dark-50 text-sm font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 resize-y" />
            </div>
            <div className="space-y-2">
              <Label>Краткое описание</Label>
              <Input value={excerpt} onChange={(e) => setExcerpt(e.target.value)} placeholder="Краткое описание для превью" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="space-y-4 p-4 md:p-6">
            <div className="space-y-2">
              <Label>Категория</Label>
              <select value={categoryId} onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : '')}
                className="flex h-10 w-full rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-sm px-3 py-2 text-sm text-dark-50">
                <option value="">Без категории</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Статус</Label>
              <select value={status} onChange={(e) => setStatus(e.target.value)}
                className="flex h-10 w-full rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-sm px-3 py-2 text-sm text-dark-50">
                <option value="draft">Черновик</option>
                <option value="published">Опубликован</option>
                <option value="archived">Архив</option>
              </select>
            </div>
          </div>
        </Card>

        <div className="flex gap-3">
          <Button type="submit" disabled={saving}>
            {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {isEdit ? 'Сохранить' : 'Создать'}
          </Button>
          <Button variant="ghost" onClick={() => navigate('/admin/posts')}>Отмена</Button>
        </div>
      </form>
    </div>
  )
}