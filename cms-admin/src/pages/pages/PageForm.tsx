import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { Button, Input, Card, Label } from '../../components/ui'
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

  if (loading) return <div className="text-center py-12 text-muted-foreground">Загрузка...</div>

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl md:text-2xl font-bold" style={{ color: 'var(--text-body)' }}>
          {isEdit ? 'Редактировать страницу' : 'Создать страницу'}
        </h2>
        <Button variant="ghost" onClick={() => navigate('/admin/pages')}>← Назад</Button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-5">
        <Card>
          <div className="space-y-4 p-4 md:p-6">
            <div className="space-y-2"><Label>Заголовок</Label><Input value={title} onChange={(e) => setTitle(e.target.value)} required /></div>
            <div className="space-y-2"><Label>Slug</Label><Input value={slug} onChange={(e) => setSlug(e.target.value)} /></div>
            <div className="space-y-2">
              <Label>Содержание</Label>
              <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={14}
                className="w-full px-4 py-3 rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-sm text-dark-50 text-sm font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 resize-y" />
            </div>
            <div className="space-y-2"><Label>Meta description</Label><Input value={metaDescription} onChange={(e) => setMetaDescription(e.target.value)} /></div>
            <div className="space-y-2">
              <Label>Статус</Label>
              <select value={status} onChange={(e) => setStatus(e.target.value)}
                className="flex h-10 w-full rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-sm px-3 py-2 text-sm text-dark-50">
                <option value="draft">Черновик</option>
                <option value="published">Опубликована</option>
              </select>
            </div>
          </div>
        </Card>
        <div className="flex gap-3">
          <Button type="submit" disabled={saving}>{saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}{isEdit ? 'Сохранить' : 'Создать'}</Button>
          <Button variant="ghost" onClick={() => navigate('/admin/pages')}>Отмена</Button>
        </div>
      </form>
    </div>
  )
}