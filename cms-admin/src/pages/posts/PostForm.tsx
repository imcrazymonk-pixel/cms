import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Input, Card } from '../../components/ui'
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
      getPost(Number(id))
        .then((post) => {
          setTitle(post.title)
          setSlug(post.slug)
          setContent(post.content)
          setExcerpt(post.excerpt ?? '')
          setStatus(post.status)
          setCategoryId(post.category_id ?? '')
        })
        .finally(() => setLoading(false))
    }
  }, [id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const data = { title, slug, content, excerpt, status, category_id: categoryId || null }
      if (isEdit && id) {
        await updatePost(Number(id), data)
      } else {
        const result = await createPost(data)
        navigate(`/admin/posts/${result.id}`)
        return
      }
      navigate('/admin/posts')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="text-[var(--text-secondary)] py-12 text-center">Загрузка...</div>

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">
            {isEdit ? 'Редактировать пост' : 'Создать пост'}
          </h2>
          <p className="text-sm text-[var(--text-secondary)]">
            {isEdit ? `ID: ${id}` : 'Новая запись в блоге'}
          </p>
        </div>
        <Button variant="ghost" onClick={() => navigate('/admin/posts')}>← Назад</Button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <Card>
          <div className="space-y-4">
            <Input
              label="Заголовок"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Введите заголовок"
              required
            />
            <Input
              label="Slug (URL)"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="my-post-slug"
            />
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-[var(--text-secondary)]">Содержание</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={14}
                className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-[var(--text-primary)] text-sm placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/30 font-mono resize-y"
                placeholder="Текст поста (HTML)"
              />
            </div>
            <Input
              label="Краткое описание (excerpt)"
              value={excerpt}
              onChange={(e) => setExcerpt(e.target.value)}
              placeholder="Краткое описание для превью"
            />
          </div>
        </Card>

        <Card>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-[var(--text-secondary)]">Категория</label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : '')}
                className="w-full h-11 px-4 rounded-lg bg-white/5 border border-white/10 text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--accent)]"
              >
                <option value="">Без категории</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-[var(--text-secondary)]">Статус</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full h-11 px-4 rounded-lg bg-white/5 border border-white/10 text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--accent)]"
              >
                <option value="draft">Черновик</option>
                <option value="published">Опубликован</option>
                <option value="archived">Архив</option>
              </select>
            </div>
          </div>
        </Card>

        <div className="flex gap-3">
          <Button type="submit" loading={saving}>
            {isEdit ? 'Сохранить' : 'Создать'}
          </Button>
          <Button variant="ghost" onClick={() => navigate('/admin/posts')}>Отмена</Button>
        </div>
      </form>
    </div>
  )
}