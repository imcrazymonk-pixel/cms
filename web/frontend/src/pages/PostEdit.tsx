import { useState, useEffect, type KeyboardEvent, type ChangeEvent, type DragEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { postsApi, Post } from '../api/posts'
import { categoriesApi, Category } from '../api/categories'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { CollapsibleCard } from '@/components/CollapsibleCard'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { mediaApi } from '../api/media'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Loader2, Save, Eye, X, Upload, Image as ImageIcon, Monitor, Smartphone, Trash2 } from 'lucide-react'

// TinyMCE is loaded from CDN at runtime (same editor as the PHP admin, admin/js/editor.js).
declare const tinymce: any

// ── Transliteration for auto-slug ──
const TRANS: Record<string, string> = {
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

function transliterate(word: string): string {
  let result = ''
  for (const ch of word) result += TRANS[ch] || ch
  return result
}

function slugify(title: string): string {
  return transliterate(title).toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-')
    .replace(/-+/g, '-').replace(/^-+|-+$/g, '')
}

export default function PostEdit() {
  const params = useParams()
  const navigate = useNavigate()
  const isEdit = !!params.id
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [tinyLoaded, setTinyLoaded] = useState(false)

  // Form data
  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [content, setContent] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [status, setStatus] = useState('draft')
  const [excerpt, setExcerpt] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [categories, setCategories] = useState<Category[]>([])

  // Metadata (parity with the PHP v2 editor)
  const [seoTitle, setSeoTitle] = useState('')
  const [seoDescription, setSeoDescription] = useState('')
  const [canonical, setCanonical] = useState('')
  const [featured, setFeatured] = useState(false)
  const [commentsEnabled, setCommentsEnabled] = useState(true)
  const [publishDate, setPublishDate] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')

  // Cover upload + preview
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'mobile'>('desktop')
  const [previewHtml, setPreviewHtml] = useState('')

  // Text metrics
  const [wordCount, setWordCount] = useState(0)
  const [charCount, setCharCount] = useState(0)

  let userEditedSlug = false
  let tinyInit = false

  const markSlugEdited = () => { userEditedSlug = true }

  const onTitleChange = (val: string) => {
    setTitle(val)
    if (!userEditedSlug) setSlug(slugify(val))
  }

  // Load TinyMCE from CDN
  const loadTinyMCE = () => {
    if (tinyInit || typeof tinymce !== 'undefined') {
      tinyInit = true
      setTinyLoaded(true)
      initTinyMCE()
      return
    }

    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/tinymce@7/tinymce.min.js'
    script.onload = () => {
      tinyInit = true
      setTinyLoaded(true)
      initTinyMCE()
    }
    document.head.appendChild(script)
  }

  const initTinyMCE = () => {
    const el = document.getElementById('editor-content')
    if (!el || typeof tinymce === 'undefined') return

    // Remove existing instance
    if (tinymce.get('editor-content')) tinymce.get('editor-content').remove()

    tinymce.init({
      selector: '#editor-content',
      height: 500,
      menubar: true,
      plugins: 'advlist autolink lists link image charmap preview anchor searchreplace visualblocks code fullscreen media table emoticons help wordcount',
      toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline strikethrough forecolor backcolor | align lineheight | numlist bullist indent outdent | link image media table | emoticons charmap | removeformat | code fullscreen | help',
      image_advtab: true,
      image_title: true,
      automatic_uploads: false,
      promotion: false,
      branding: false,
      setup: (editor: any) => {
        // Set initial content
        if (content) editor.setContent(content)

        editor.on('change', () => {
          const html = editor.getContent()
          setContent(html)
          // Count words
          const text = editor.getContent().replace(/<[^>]*>/g, '')
          const words = text.trim() ? text.split(/\s+/).length : 0
          setWordCount(words)
          setCharCount(text.length)
        })
      },
    })
  }

  const getEditorHtml = (): string => {
    if (typeof tinymce !== 'undefined' && tinymce.get('editor-content')) {
      return tinymce.get('editor-content').getContent()
    }
    return content
  }

  // Load data
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const catRes = await categoriesApi.list() as { success: boolean; data: Category[] }
        if (!cancelled && catRes.success) setCategories(catRes.data)

        if (isEdit && params.id) {
          const postRes = await postsApi.get(parseInt(params.id)) as { success: boolean; data: Post }
          if (!cancelled && postRes.success) {
            const p = postRes.data
            setTitle(p.title || '')
            setSlug(p.slug || '')
            setContent(p.content || '')
            setCategoryId(p.category_id ? String(p.category_id) : '')
            setStatus(p.status || 'draft')
            setExcerpt(p.excerpt || '')
            setImageUrl(p.image || '')
            setSeoTitle(p.seo_title || '')
            setSeoDescription(p.seo_description || '')
            setCanonical(p.canonical || '')
            setFeatured(!!p.featured)
            setCommentsEnabled(p.comments_enabled !== false)
            setTags(Array.isArray(p.tags) ? p.tags : [])
            if (p.created_at) setPublishDate(p.created_at.slice(0, 16).replace(' ', 'T'))
            if (p.slug) userEditedSlug = true
          } else if (!cancelled) setError('Пост не найден')
        }
      } catch (err: unknown) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Ошибка загрузки')
      } finally { if (!cancelled) setIsPending(false) }
    }
    load()
    return () => { cancelled = true }
  }, [])

  // Load TinyMCE after content is ready
  useEffect(() => {
    if (!isPending) loadTinyMCE()
  }, [isPending])

  const save = async () => {
    if (!title.trim()) return
    setSaving(true)
    try {
      const html = getEditorHtml()
      const payload: Record<string, unknown> = {
        title: title.trim(), slug: slug.trim() || undefined,
        content: html, excerpt, status,
        category_id: categoryId ? parseInt(categoryId) : null,
        image: imageUrl,
        seo_title: seoTitle, seo_description: seoDescription, canonical,
        featured, comments_enabled: commentsEnabled,
        publish_date: publishDate || undefined,
        tags,
      }
      if (isEdit && params.id) await postsApi.update(parseInt(params.id), payload)
      else {
        const res = await postsApi.create(payload) as { success: boolean; data?: { id: number } }
        if (res.success && res.data?.id) { navigate(`/posts/${res.data.id}`); setSaving(false); return }
      }
      navigate('/posts')
    } catch { /* ignore */ }
    finally { setSaving(false) }
  }

  // ── Tag helpers ──
  const addTag = () => {
    const v = tagInput.trim()
    if (v && !tags.includes(v)) setTags([...tags, v])
    setTagInput('')
  }
  const onTagKeydown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTag() }
    else if (e.key === 'Backspace' && !tagInput && tags.length) setTags(tags.slice(0, -1))
  }

  // ── Cover upload ──
  const uploadCover = async (file: File | undefined | null) => {
    if (!file) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await mediaApi.upload(fd) as { success: boolean; data?: { url: string } }
      if (res.success && res.data?.url) setImageUrl(res.data.url)
    } catch { /* ignore */ }
    finally { setUploading(false) }
  }

  const onCoverInput = (e: ChangeEvent<HTMLInputElement>) => {
    uploadCover(e.target.files?.[0])
    e.target.value = ''
  }

  const onCoverDrop = (e: DragEvent<HTMLElement>) => {
    e.preventDefault()
    setDragOver(false)
    uploadCover(e.dataTransfer.files?.[0])
  }

  const openPreview = () => {
    setPreviewHtml(getEditorHtml())
    setPreviewOpen(true)
  }

  const escapeHtml = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  // Preview document uses the real theme stylesheet so fonts/typography match the blog.
  const buildPreviewDoc = () => {
    const cat = categoryId ? (categories.find(c => String(c.id) === categoryId)?.name || '') : ''
    const dateStr = publishDate ? new Date(publishDate).toLocaleDateString('ru-RU') : 'Сегодня'
    const mins = Math.max(1, Math.round(wordCount / 200))
    return `<!doctype html><html lang="ru"><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/public/hexaveil/css/variables.css">
<link rel="stylesheet" href="/public/hexaveil/css/reset.css">
<link rel="stylesheet" href="/public/hexaveil/css/style.css">
<style>
html,body{margin:0;background:#0b0d12;}
body{font-family:"Inter",system-ui,sans-serif;color:#e2e8f0;padding:24px;}
.wrap{max-width:760px;margin:0 auto;}
.post-cat{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#818cf8;font-weight:600;}
.post-title{font-size:34px;line-height:1.15;font-weight:700;color:#fff;margin:6px 0 10px;}
.post-meta{font-size:13px;color:#94a3b8;margin-bottom:18px;}
.post-cover{width:100%;border-radius:16px;display:block;margin:0 0 18px;}
.post-lead{font-size:18px;color:#cbd5e1;font-style:italic;margin:0 0 18px;}
</style></head><body><div class="wrap">
${cat ? `<div class="post-cat">${escapeHtml(cat)}</div>` : ''}
<h1 class="post-title">${escapeHtml(title || 'Заголовок поста')}</h1>
<div class="post-meta">Редакция · ${dateStr} · ~${mins} мин чтения</div>
${imageUrl ? `<img class="post-cover" src="${escapeHtml(imageUrl)}" alt="">` : ''}
${excerpt ? `<p class="post-lead">${escapeHtml(excerpt)}</p>` : ''}
<div class="post-content">${previewHtml}</div>
</div></body></html>`
  }

  // ── Render ──
  return (
    <div className="p-6 space-y-6">
      {/* Back link + Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <a href="/admin/posts" className="text-sm text-dark-300 hover:text-dark-100 transition-colors mb-1 block">
            ← Назад к списку
          </a>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {isEdit ? 'Редактировать пост' : 'Создать пост'}
          </h1>
          <p className="text-sm text-dark-200 mt-1">
            {isEdit ? 'Редактирование записи блога' : 'Новая запись в блоге'}
          </p>
        </div>

        {/* Topbar actions */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-dark-300">
            {wordCount > 0 ? `${wordCount} слов · ${charCount} символов` : ''}
          </span>
          <Button variant="ghost" size="sm" onClick={openPreview}>
            <Eye className="w-4 h-4" /> Предпросмотр
          </Button>
          <Button variant="default" size="sm" onClick={save} disabled={saving || !title.trim()}>
            <Save className="w-4 h-4" /> {isEdit ? 'Сохранить' : 'Создать'}
          </Button>
        </div>
      </div>

      {isPending && <><Skeleton className="h-12 rounded-lg" /><Skeleton className="h-64 rounded-lg" /></>}
      {error && <QueryError message={error} />}

      {!isPending && !error && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
          {/* Main column — Editor */}
          <div className="space-y-4">
            {/* Title - large input like in PHP editor */}
            <textarea
              id="editor-title"
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              placeholder="Заголовок поста *"
              className="w-full text-xl font-bold px-4 py-3 rounded-xl"
              style={{
                background: 'var(--surface-card, rgba(24,30,40,0.8))',
                border: '1px solid var(--glass-border, rgba(255,255,255,0.08))',
                color: '#f3f4f6',
                minHeight: '56px',
              }}
              rows={1}
            />

            {/* Excerpt — lead paragraph */}
            <textarea
              id="editor-lead"
              value={excerpt}
              onChange={(e) => setExcerpt(e.target.value)}
              placeholder="Короткое введение (отображается в карточке блога)..."
              className="w-full px-4 py-3 rounded-xl text-sm"
              style={{
                background: 'var(--surface-card, rgba(24,30,40,0.8))',
                border: '1px solid var(--glass-border, rgba(255,255,255,0.08))',
                color: '#d1d5db',
              }}
              rows={2}
            />

            {/* TinyMCE Content Editor */}
            <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--glass-border, rgba(255,255,255,0.08))' }}>
              {!tinyLoaded && (
                <div className="flex items-center justify-center py-8 text-sm text-dark-300">
                  <Loader2 className="w-5 h-5 animate-spin mr-2" /> Загрузка редактора...
                </div>
              )}
              <textarea
                id="editor-content"
                className={tinyLoaded ? '' : 'hidden'}
                style={{ minHeight: '500px' }}
              >
                {content}
              </textarea>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Параметры */}
            <CollapsibleCard title="Параметры">
              <div className="space-y-3 pt-3">
                <div className="space-y-2">
                  <Label>URL (slug)</Label>
                  <div className="flex items-center gap-1 text-xs text-dark-300">
                    <span>/blog/</span>
                    <Input value={slug} onChange={(e) => { setSlug(e.target.value); markSlugEdited() }}
                      placeholder="url-post" className="flex-1" />
                  </div>
                  <p className="text-xs text-dark-300">Оставьте пустым для автогенерации</p>
                </div>

                <div className="h-px bg-white/5 my-2" />

                <div className="space-y-2">
                  <Label>Рубрика</Label>
                  <Select value={categoryId || '__none__'} onValueChange={(v) => setCategoryId(v === '__none__' ? '' : v)}>
                    <SelectTrigger className="w-full"><SelectValue placeholder="Без категории" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">Без категории</SelectItem>
                      {categories.map(c => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Статус</Label>
                  <Select value={status} onValueChange={setStatus}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="draft">Черновик</SelectItem>
                      <SelectItem value="published">Опубликован</SelectItem>
                      <SelectItem value="archived">Архив</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Дата публикации</Label>
                  <input
                    type="datetime-local"
                    value={publishDate}
                    onChange={(e) => setPublishDate(e.target.value)}
                    className="w-full h-10 px-3 rounded-md text-sm"
                    style={{ background: 'var(--surface-card, rgba(24,30,40,0.8))', border: '1px solid var(--glass-border, rgba(255,255,255,0.08))', color: '#e5e7eb' }}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Теги</Label>
                  {tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {tags.map(t => (
                        <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-white/10 text-dark-100">
                          {t}
                          <button type="button" onClick={() => setTags(tags.filter(x => x !== t))} className="hover:text-red-400"><X className="w-3 h-3" /></button>
                        </span>
                      ))}
                    </div>
                  )}
                  <Input
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={onTagKeydown}
                    onBlur={addTag}
                    placeholder="Добавить тег (Enter)..."
                  />
                </div>

                <label className="flex items-center gap-2 text-sm text-dark-100 cursor-pointer">
                  <input type="checkbox" className="w-4 h-4" checked={featured} onChange={(e) => setFeatured(e.target.checked)} />
                  Закрепить в топе блога
                </label>
                <label className="flex items-center gap-2 text-sm text-dark-100 cursor-pointer">
                  <input type="checkbox" className="w-4 h-4" checked={commentsEnabled} onChange={(e) => setCommentsEnabled(e.target.checked)} />
                  Разрешить комментарии
                </label>

                <div className="h-px bg-white/5 my-2" />

                <div className="space-y-2">
                  <Label>Обложка</Label>
                  {imageUrl ? (
                    <div className="space-y-2">
                      <img src={imageUrl} alt="Обложка" className="rounded-lg w-full max-h-40 object-cover" />
                      <div className="flex items-center gap-3">
                        <label className="text-xs inline-flex items-center gap-1 cursor-pointer text-dark-200 hover:text-white">
                          <Upload className="w-3.5 h-3.5" /> Заменить
                          <input type="file" accept="image/*" className="hidden" onChange={onCoverInput} />
                        </label>
                        <button type="button" onClick={() => setImageUrl('')} className="text-xs inline-flex items-center gap-1 text-red-400 hover:text-red-300">
                          <Trash2 className="w-3.5 h-3.5" /> Удалить
                        </button>
                      </div>
                    </div>
                  ) : (
                    <label
                      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                      onDragLeave={() => setDragOver(false)}
                      onDrop={onCoverDrop}
                      className="flex flex-col items-center justify-center gap-2 py-6 rounded-lg cursor-pointer text-center"
                      style={{ border: `1px dashed ${dragOver ? '#6366f1' : 'rgba(255,255,255,0.15)'}`, background: dragOver ? 'rgba(99,102,241,0.08)' : 'transparent' }}
                    >
                      {uploading ? <Loader2 className="w-5 h-5 animate-spin text-dark-300" /> : <ImageIcon className="w-6 h-6 text-dark-300" />}
                      <span className="text-xs text-dark-300">{uploading ? 'Загрузка…' : 'Перетащите изображение или нажмите'}</span>
                      <input type="file" accept="image/*" className="hidden" onChange={onCoverInput} />
                    </label>
                  )}
                  <Input value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} placeholder="…или вставьте URL" className="text-xs" />
                </div>

                <div className="h-px bg-white/5 my-2" />

                {/* Metrics */}
                <div className="space-y-2">
                  <Label className="text-dark-300">Метрики текста</Label>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <span className="text-dark-300">Слов</span>
                    <span className="font-semibold text-right text-dark-100">{wordCount}</span>
                    <span className="text-dark-300">Символов</span>
                    <span className="font-semibold text-right text-dark-100">{charCount}</span>
                    <span className="text-dark-300">Чтение</span>
                    <span className="font-semibold text-right text-dark-100">~{Math.max(1, Math.round(wordCount / 200))} мин</span>
                    <span className="text-dark-300">Абзацев</span>
                    <span className="font-semibold text-right text-dark-100">{content ? (content.match(/<p[\s>]/gi) || []).length || content.split(/\n\s*\n/).filter(Boolean).length : 0}</span>
                  </div>
                </div>
              </div>
            </CollapsibleCard>

            {/* SEO */}
            <CollapsibleCard title="SEO">
              <div className="space-y-3 pt-3">
                <div className="rounded-lg p-3" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--glass-border, rgba(255,255,255,0.08))' }}>
                  <div className="text-[11px] text-dark-400 truncate">hexaveil.xyz › blog › <span className="text-green-400">{slug || 'url-post'}</span></div>
                  <div className="text-sm text-blue-400 truncate">{seoTitle || title || 'Заголовок поста'}</div>
                  <div className="text-[11px] text-dark-300" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{seoDescription || excerpt || 'Описание поста…'}</div>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <Label>SEO Заголовок (Title)</Label>
                    <span className={`text-xs ${seoTitle.length > 70 ? 'text-red-400' : 'text-dark-400'}`}>{seoTitle.length} / 70</span>
                  </div>
                  <Input value={seoTitle} onChange={(e) => setSeoTitle(e.target.value)} placeholder="SEO-заголовок (до 70 символов)" />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <Label>Meta Description</Label>
                    <span className={`text-xs ${seoDescription.length > 160 ? 'text-red-400' : 'text-dark-400'}`}>{seoDescription.length} / 160</span>
                  </div>
                  <textarea
                    value={seoDescription}
                    onChange={(e) => setSeoDescription(e.target.value)}
                    rows={3}
                    placeholder="Краткое описание (до 160 символов)"
                    className="w-full px-3 py-2 rounded-md text-sm"
                    style={{ background: 'var(--surface-card, rgba(24,30,40,0.8))', border: '1px solid var(--glass-border, rgba(255,255,255,0.08))', color: '#d1d5db' }}
                  />
                </div>

                <div className="space-y-1">
                  <Label>Канонический URL</Label>
                  <Input value={canonical} onChange={(e) => setCanonical(e.target.value)} placeholder="(совпадает с URL поста)" />
                </div>
              </div>
            </CollapsibleCard>

            {/* Save button */}
            <Button variant="default" className="w-full" onClick={save} disabled={saving || !title.trim()}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {saving ? 'Сохранение...' : isEdit ? 'Сохранить' : 'Опубликовать'}
            </Button>
            <Button variant="ghost" className="w-full" onClick={() => navigate('/posts')}>Отмена</Button>
          </div>
        </div>
      )}

      {/* Preview modal */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              <span className="flex items-center justify-between gap-4">
                <span>Предпросмотр</span>
                <span className="flex items-center gap-1">
                  <Button type="button" size="sm" variant={previewDevice === 'desktop' ? 'default' : 'ghost'} onClick={() => setPreviewDevice('desktop')}>
                    <Monitor className="w-4 h-4" /> ПК
                  </Button>
                  <Button type="button" size="sm" variant={previewDevice === 'mobile' ? 'default' : 'ghost'} onClick={() => setPreviewDevice('mobile')}>
                    <Smartphone className="w-4 h-4" /> Смартфон
                  </Button>
                </span>
              </span>
            </DialogTitle>
          </DialogHeader>
          <div className="mx-auto w-full" style={{ maxWidth: previewDevice === 'mobile' ? 390 : '100%' }}>
            <iframe
              title="Предпросмотр поста"
              srcDoc={buildPreviewDoc()}
              className="w-full rounded-lg"
              style={{ height: 640, border: '1px solid var(--glass-border, rgba(255,255,255,0.08))', background: '#0b0d12' }}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}