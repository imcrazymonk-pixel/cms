import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Input, Card } from '../../components/ui'
import { getPage, createPage, updatePage } from '../../api/pages'

export default function PageFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = !!id

  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [content, setContent] = useState('')
  const [metaDescription, setMetaDescription] = useState('')
  const [status, setStatus] = useState('draft')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEdit && id) {
      setLoading(true)
      getPage(Number(id)).then((p) => {
        setTitle(p.title); setSlug(p.slug); setContent(p.content)
        setMetaDescription(p.meta_description ?? ''); setStatus(p.status)
      }).finally(() => setLoading(false))
    }
  }, [id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const data = { title, slug, content, meta_description: metaDescription, status }
      if (isEdit && id) { await updatePage(Number(id), data); navigate('/admin/pages') }
      else { const r = await createPage(data); navigate(`/admin/pages/${r.id}`) }
    } finally { setSaving(false) }
  }

  if (loading) return <div className="text-[var(--text-secondary)] py-12 text-center">Загрузка...</div>

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">
            {isEdit ? 'Редактировать страницу' : 'Создать страницу'}
          </h2>
        </div>
        <Button variant="ghost" onClick={() => navigate('/admin/pages')}>← Назад</Button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-5">
        <Card>
          <div className="space-y-4">
            <Input label="Заголовок" value={title} onChange={(e) => setTitle(e.target.value)} required />
            <Input label="Slug" value={slug} onChange={(e) => setSlug(e.target.value)} />
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-[var(--text-secondary)]">Содержание</label>
              <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={14}
                className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--accent)] font-mono resize-y"
              />
            </div>
            <Input label="Meta description" value={metaDescription} onChange={(e) => setMetaDescription(e.target.value)} />
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-[var(--text-secondary)]">Статус</label>
              <select value={status} onChange={(e) => setStatus(e.target.value)}
                className="w-full h-11 px-4 rounded-lg bg-white/5 border border-white/10 text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--accent)]">
                <option value="draft">Черновик</option>
                <option value="published">Опубликована</option>
              </select>
            </div>
          </div>
        </Card>
        <div className="flex gap-3">
          <Button type="submit" loading={saving}>{isEdit ? 'Сохранить' : 'Создать'}</Button>
          <Button variant="ghost" onClick={() => navigate('/admin/pages')}>Отмена</Button>
        </div>
      </form>
    </div>
  )
}