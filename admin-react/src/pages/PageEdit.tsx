import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { pagesApi, Page } from '../api/pages'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { Loader2 } from 'lucide-react'

function transliterate(word: string): string {
  const map: Record<string, string> = {
    а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'yo',
    ж: 'zh', з: 'z', и: 'i', й: 'y', к: 'k', л: 'l', м: 'm',
    н: 'n', о: 'o', п: 'p', р: 'r', с: 's', т: 't', у: 'u',
    ф: 'f', х: 'h', ц: 'c', ч: 'ch', ш: 'sh', щ: 'sch', ъ: '',
    ы: 'y', ь: '', э: 'e', ю: 'yu', я: 'ya',
    А: 'A', Б: 'B', В: 'V', Г: 'G', Д: 'D', Е: 'E', Ё: 'Yo',
    Ж: 'Zh', З: 'Z', И: 'I', Й: 'Y', К: 'K', Л: 'L', М: 'M',
    Н: 'N', О: 'O', П: 'P', Р: 'R', С: 'S', Т: 'T', У: 'U',
    Ф: 'F', Х: 'H', Ц: 'C', Ч: 'Ch', Ш: 'Sh', Щ: 'Sch', '№': '',
  }
  let r = ''
  for (const ch of word) r += map[ch] || ch
  return r
}

function slugify(title: string): string {
  return transliterate(title).toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').replace(/-+/g, '-').replace(/^-+|-+$/g, '')
}

const PAGE_TEMPLATES = ['default', 'fullwidth', 'landing']

export default function PageEdit() {
  const navigate = useNavigate()
  const params = useParams()
  const isEdit = !!params.id
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [content, setContent] = useState('')
  const [metaDescription, setMetaDescription] = useState('')
  const [template, setTemplate] = useState('default')
  const [status, setStatus] = useState('draft')
  let userEditedSlug = false

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        if (isEdit && params.id) {
          const res = await pagesApi.get(parseInt(params.id)) as { success: boolean; data: Page }
          if (!cancelled && res.success) {
            const p = res.data
            setTitle(p.title || '')
            setSlug(p.slug || '')
            setContent(p.content || '')
            setMetaDescription(p.meta_description || '')
            setTemplate(p.template || 'default')
            setStatus(p.status || 'draft')
            if (p.slug) userEditedSlug = true
          } else if (!cancelled) setError('Страница не найдена')
        }
      } catch (err: unknown) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Ошибка загрузки')
      } finally { if (!cancelled) setIsPending(false) }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const save = async () => {
    if (!title.trim()) return
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        title: title.trim(), slug: slug.trim() || undefined, content,
        meta_description: metaDescription, template, status,
      }
      if (isEdit && params.id) await pagesApi.update(parseInt(params.id), payload)
      else {
        const res = await pagesApi.create(payload) as { success: boolean; data?: { id: number } }
        if (res.success && res.data?.id) { navigate(`/pages/${res.data.id}`); setSaving(false); return }
      }
      navigate('/pages')
    } catch { /* ignore */ }
    finally { setSaving(false) }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <button onClick={() => navigate('/pages')} className="text-sm text-dark-300 hover:text-dark-100 transition-colors mb-1 block bg-transparent border-0 p-0 cursor-pointer">← Назад к списку</button>
          <h1 className="text-2xl font-bold text-white tracking-tight">{isEdit ? 'Редактировать страницу' : 'Создать страницу'}</h1>
          <p className="text-sm text-dark-200 mt-1">{isEdit ? 'Редактирование статической страницы' : 'Новая статическая страница'}</p>
        </div>
      </div>

      {isPending && <><Skeleton className="h-12 rounded-lg" /><Skeleton className="h-64 rounded-lg" /></>}
      {error && <QueryError message={error} />}

      {!isPending && !error && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
          <div className="space-y-5">
            <Card className="rounded-xl">
              <CardHeader><CardTitle>Содержимое</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Заголовок *</Label>
                  <Input id="title" value={title} onChange={(e) => {
                    const v = e.target.value; setTitle(v)
                    if (!userEditedSlug) setSlug(slugify(v))
                  }} placeholder="Заголовок страницы" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="slug">Slug (URL)</Label>
                  <Input id="slug" value={slug} onChange={(e) => { setSlug(e.target.value); userEditedSlug = true }} placeholder="page-url" />
                  <p className="text-xs text-dark-300">Оставьте пустым для автогенерации</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="content">Содержимое *</Label>
                  <textarea id="content" className="w-full min-h-[400px] px-3 py-2.5 rounded-xl text-sm font-mono"
                    style={{ background: 'var(--surface-card, rgba(24,30,40,0.8))', border: '1px solid var(--glass-border, rgba(255,255,255,0.08))', color: '#d1d5db' }}
                    value={content} onChange={(e) => setContent(e.target.value)} placeholder="HTML-содержимое страницы..." />
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="rounded-xl">
              <CardHeader><CardTitle>Настройки</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-2">
                  <Label>Статус</Label>
                  <Select value={status} onValueChange={setStatus}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="draft">Черновик</SelectItem>
                      <SelectItem value="published">Опубликована</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Шаблон</Label>
                  <Select value={template} onValueChange={setTemplate}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {PAGE_TEMPLATES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Meta Description</Label>
                  <textarea className="w-full px-3 py-2 rounded-xl text-sm"
                    style={{ background: 'var(--surface-card, rgba(24,30,40,0.8))', border: '1px solid var(--glass-border, rgba(255,255,255,0.08))', color: '#d1d5db' }}
                    value={metaDescription} onChange={(e) => setMetaDescription(e.target.value)} placeholder="SEO-описание" rows={2} />
                </div>
              </CardContent>
            </Card>

            <div className="space-y-3">
              <Button variant="default" className="w-full" onClick={save} disabled={saving || !title.trim()}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null} {isEdit ? 'Сохранить' : 'Создать'}
              </Button>
              <Button variant="ghost" className="w-full" onClick={() => navigate('/pages')}>Отмена</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
