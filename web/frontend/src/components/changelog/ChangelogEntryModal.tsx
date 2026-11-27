import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'
import { docsApi } from '@/api/docs'
import type { DocEntry, UserName } from '@/api/docs'

export interface EntryFormData {
  date: string
  time: string
  author: string
  title: string
  body: string
  also_history: boolean
}

interface ChangelogEntryModalProps {
  mode: 'create' | 'edit'
  entry?: DocEntry  // provided when editing
  users: UserName[]
  /** Which document the entry belongs to. Defaults to the changelog feed. */
  docName?: 'changelog' | 'history'
  onSave: (data: EntryFormData) => Promise<void>
  onClose: () => void
}

export default function ChangelogEntryModal({
  mode,
  entry,
  users,
  docName = 'changelog',
  onSave,
  onClose,
}: ChangelogEntryModalProps) {
  const isHistory = docName === 'history'
  const [open, setOpen] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('edit')

  // Default: today
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const defaultDate = `${pad(now.getDate())}.${pad(now.getMonth() + 1)}.${now.getFullYear()}`
  const defaultTime = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`

  const [date, setDate] = useState(entry?.date ?? defaultDate)
  const [time, setTime] = useState(entry?.time ?? defaultTime)
  const [author, setAuthor] = useState(entry?.author ?? (users.length > 0 ? users[0].display_name : ''))
  const [title, setTitle] = useState(entry?.title ?? '')
  const [body, setBody] = useState(entry?.body ?? '')
  const [alsoHistory, setAlsoHistory] = useState(false)
  // Backend-rendered preview, same engine as the history page.
  const [previewHtml, setPreviewHtml] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)

  // Debounced preview rendering — only while the preview tab is visible.
  useEffect(() => {
    if (activeTab !== 'preview') return
    let cancelled = false
    const timer = window.setTimeout(() => {
      setPreviewLoading(true)
      docsApi
        .renderMarkdown(body)
        .then((html) => {
          if (cancelled) return
          setPreviewHtml(html)
          setPreviewError(null)
        })
        .catch((e: unknown) => {
          if (cancelled) return
          setPreviewError(e instanceof Error ? e.message : 'Не удалось отрисовать предпросмотр')
        })
        .finally(() => {
          if (!cancelled) setPreviewLoading(false)
        })
    }, 300)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [activeTab, body])

  const handleClose = () => {
    setOpen(false)
    onClose()
  }

  const handleSave = async () => {
    setError(null)

    // Validate
    if (!date.trim()) { setError('Дата обязательна'); return }
    if (!time.trim()) { setError('Время обязательно'); return }
    if (!author.trim()) { setError('Автор обязателен'); return }
    if (!title.trim()) { setError('Заголовок обязателен'); return }

    setSaving(true)
    try {
      await onSave({
        date: date.trim(),
        time: time.trim(),
        author: author.trim(),
        title: title.trim(),
        body: body.trim(),
        also_history: isHistory ? false : alsoHistory,
      })
      handleClose()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const titleText = mode === 'create'
    ? (isHistory ? '✏️ Новая запись в тех.историю' : '✏️ Новая запись')
    : '✏️ Редактировать запись'

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose() }}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{titleText}</DialogTitle>
          <DialogDescription>
            {mode === 'create'
              ? (isHistory
                  ? 'Добавьте запись в техническую историю'
                  : 'Добавьте новую запись в ленту изменений')
              : (isHistory
                  ? 'Измените дату, автора или содержимое блока тех.истории'
                  : 'Измените дату, автора или содержимое записи')}
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-3">
          <TabsList>
            <TabsTrigger value="edit">✏️ Редактирование</TabsTrigger>
            <TabsTrigger value="preview">👁 Предпросмотр</TabsTrigger>
          </TabsList>

          <TabsContent value="edit">
            <div className="grid gap-4">
              {/* Date + Time row */}
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-1.5">
                  <Label htmlFor="entry-date">Дата</Label>
                  <Input
                    id="entry-date"
                    type="text"
                    placeholder="ДД.ММ.ГГГГ"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                  />
                </div>
                <div className="grid gap-1.5">
                  <Label htmlFor="entry-time">Время</Label>
                  <Input
                    id="entry-time"
                    type="text"
                    placeholder="ЧЧ:ММ:СС"
                    value={time}
                    onChange={(e) => setTime(e.target.value)}
                  />
                </div>
              </div>

              {/* Author */}
              <div className="grid gap-1.5">
                <Label htmlFor="entry-author">Автор</Label>
                {users.length > 0 ? (
                  <select
                    id="entry-author"
                    className={cn(
                      "flex h-10 w-full items-center justify-between rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] px-3 py-2 text-sm text-dark-50",
                      "focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                    )}
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                  >
                    {users.map((u) => (
                      <option key={u.id} value={u.display_name}>
                        {u.display_name} ({u.username})
                      </option>
                    ))}
                  </select>
                ) : (
                  <Input
                    id="entry-author"
                    type="text"
                    placeholder="Имя автора"
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                  />
                )}
              </div>

              {/* Title */}
              <div className="grid gap-1.5">
                <Label htmlFor="entry-title">Заголовок</Label>
                <Input
                  id="entry-title"
                  type="text"
                  placeholder="🎯 Краткое описание изменений"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>

              {/* Body */}
              <div className="grid gap-1.5">
                <Label htmlFor="entry-body">Описание изменений (Markdown)</Label>
                <Textarea
                  id="entry-body"
                  placeholder="- ✨ Новая фича&#10;- 🐛 Исправлен баг&#10;- 📄 Обновлена документация"
                  rows={8}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
              </div>

              {/* Also history (changelog only, create mode) */}
              {mode === 'create' && !isHistory && (
                <div className="flex items-center justify-between rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] px-3 py-2">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-white">Также в тех.историю</span>
                    <span className="text-xs text-muted-foreground">Добавить краткую запись в HISTORY_TECHNICAL.md</span>
                  </div>
                  <Switch checked={alsoHistory} onCheckedChange={setAlsoHistory} />
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="preview">
            <ScrollArea className="max-h-[30rem]">
              <div className="rounded-xl border border-[var(--glass-border)] bg-[var(--glass-bg)] p-4">
                {/* Preview header */}
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground mb-2">
                  <span>{date}</span>
                  <span className="opacity-40">·</span>
                  <span>{time}</span>
                  <span className="opacity-40">·</span>
                  <span>{author}</span>
                  {previewLoading && (
                    <>
                      <span className="opacity-40">·</span>
                      <span className="flex items-center gap-1">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        Рендеринг…
                      </span>
                    </>
                  )}
                </div>
                <h3 className="text-base font-semibold text-white mb-1">{title || 'Заголовок'}</h3>
                {previewError && (
                  <p className="mb-2 text-xs text-red-400">
                    {previewError} — показан предыдущий вариант
                  </p>
                )}
                {/* Rendered body — backend engine output */}
                <div className="prose" dangerouslySetInnerHTML={{ __html: previewHtml }} />
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Отмена
          </Button>
          <Button variant="default" disabled={saving} onClick={handleSave}>
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            {mode === 'create' ? '✏️ Добавить' : '💾 Сохранить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}