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
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Loader2, RefreshCw, Save } from 'lucide-react'
import { toast } from 'sonner'
import { docsApi, DocsApiError } from '@/api/docs'

interface HistoryDocumentEditorProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Current raw markdown of the history document. */
  initialRaw: string
  /** Last-updated stamp used as the optimistic-lock token. */
  updatedAt: string | null
  /** Called after a successful save, before the dialog closes. */
  onSaved: (updatedAt: string | null) => void | Promise<void>
}

export default function HistoryDocumentEditor({
  open,
  onOpenChange,
  initialRaw,
  updatedAt,
  onSaved,
}: HistoryDocumentEditorProps) {
  const [content, setContent] = useState(initialRaw)
  const [savedAt, setSavedAt] = useState<string | null>(updatedAt)
  const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit')
  const [saving, setSaving] = useState(false)
  const [reloading, setReloading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conflict, setConflict] = useState(false)
  // Preview is produced by the backend renderer so it matches the page exactly.
  const [previewHtml, setPreviewHtml] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)

  // Sync with the parent's document every time the dialog is opened.
  useEffect(() => {
    if (!open) return
    setContent(initialRaw)
    setSavedAt(updatedAt)
    setActiveTab('edit')
    setError(null)
    setConflict(false)
    setPreviewHtml('')
    setPreviewError(null)
  }, [open, initialRaw, updatedAt])

  // Debounced preview rendering — only while the preview tab is visible.
  useEffect(() => {
    if (!open || activeTab !== 'preview') return
    let cancelled = false
    const timer = window.setTimeout(() => {
      setPreviewLoading(true)
      docsApi
        .renderMarkdown(content)
        .then((html) => {
          if (cancelled) return
          setPreviewHtml(html)
          setPreviewError(null)
        })
        .catch((e: unknown) => {
          // Keep the previous html so the pane never goes blank on a hiccup.
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
  }, [open, activeTab, content])

  const handleSave = async () => {
    setError(null)
    setConflict(false)

    if (!content.trim()) {
      setError('Документ не может быть пустым')
      return
    }

    setSaving(true)
    try {
      const res = await docsApi.putDocument('history', content, savedAt)
      const nextUpdatedAt = res.data.updated_at ?? null
      setSavedAt(nextUpdatedAt)
      toast.success('Документ сохранён')
      await onSaved(nextUpdatedAt)
      onOpenChange(false)
    } catch (e: unknown) {
      if (e instanceof DocsApiError && (e.status === 409 || e.code === 'CONFLICT')) {
        setConflict(true)
        setError('Документ изменён в другой вкладке. Перезагрузите его, чтобы не потерять чужие правки.')
      } else {
        setError(e instanceof Error ? e.message : 'Не удалось сохранить документ')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleReload = async () => {
    setReloading(true)
    setError(null)
    setConflict(false)
    try {
      const res = await docsApi.get('history')
      if (!res.success) throw new Error('Не удалось загрузить документ')
      setContent(res.data.raw)
      setSavedAt(res.data.updated_at ?? null)
      toast.success('Документ перезагружен')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Не удалось перезагрузить документ')
    } finally {
      setReloading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Редактирование технической истории</DialogTitle>
          <DialogDescription>
            Базовый документ технической истории. Блоки «Дополнения» редактируются отдельными записями.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <span>{error}</span>
              {conflict && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={reloading}
                  onClick={handleReload}
                  className="shrink-0"
                >
                  {reloading
                    ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                    : <RefreshCw className="w-4 h-4 mr-1.5" />}
                  Перезагрузить
                </Button>
              )}
            </div>
          </div>
        )}

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v === 'preview' ? 'preview' : 'edit')}>
          <TabsList>
            <TabsTrigger value="edit">✏️ Редактирование</TabsTrigger>
            <TabsTrigger value="preview">👁 Предпросмотр</TabsTrigger>
          </TabsList>

          <TabsContent value="edit">
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              spellCheck={false}
              aria-label="Markdown технической истории"
              className="h-[60vh] resize-none font-mono text-xs leading-relaxed"
            />
          </TabsContent>

          <TabsContent value="preview">
            <ScrollArea className="h-[60vh] rounded-md">
              <div className="relative">
                {(previewLoading || previewError) && (
                  <div className="sticky top-0 z-10 flex items-center gap-1.5 border-b border-[var(--glass-border)] bg-[var(--glass-bg-solid)]/90 px-3 py-1.5 text-xs text-muted-foreground backdrop-blur">
                    {previewError ? (
                      <span className="text-red-400">
                        {previewError} — показан предыдущий вариант
                      </span>
                    ) : (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        Рендеринг…
                      </>
                    )}
                  </div>
                )}
                <div className="prose p-4" dangerouslySetInnerHTML={{ __html: previewHtml }} />
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>

        <DialogFooter className="sm:items-center sm:justify-between">
          <span className="text-xs text-muted-foreground">
            {content.length.toLocaleString('ru-RU')} символов
          </span>
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
              Отмена
            </Button>
            <Button variant="default" onClick={handleSave} disabled={saving}>
              {saving
                ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                : <Save className="w-4 h-4 mr-1.5" />}
              Сохранить
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
