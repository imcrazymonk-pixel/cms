import { useEffect, useMemo, useState } from 'react'
import { Archive, FileText, Save, Send, Trash2, Undo2 } from 'lucide-react'
import type { KbDocStatus, SupportKbDoc } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'

const STATUS_LABEL: Record<KbDocStatus, string> = {
  published: 'Опубликована',
  draft: 'Черновик',
  archived: 'В архиве',
}

const STATUS_VARIANT: Record<KbDocStatus, 'success' | 'warning' | 'secondary'> = {
  published: 'success',
  draft: 'warning',
  archived: 'secondary',
}

export interface KbEditorValues {
  title: string
  tags: string[]
  body: string
}

export interface KbEditorProps {
  doc: SupportKbDoc | undefined
  isLoading: boolean
  saving: boolean
  publishing: boolean
  archiving: boolean
  restoring: boolean
  deleting: boolean
  onSave: (values: KbEditorValues) => void
  onPublish: () => void
  onArchive: () => void
  onRestore: () => void
  onDelete: () => void
}

function tagsToText(tags: string[]): string {
  return tags.join(', ')
}

function textToTags(value: string): string[] {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
}

/** Правая колонка: редактор статьи с optimistic-lock через `expected_version`. */
export function KbEditor({
  doc,
  isLoading,
  saving,
  publishing,
  archiving,
  restoring,
  deleting,
  onSave,
  onPublish,
  onArchive,
  onRestore,
  onDelete,
}: KbEditorProps) {
  const [title, setTitle] = useState('')
  const [tags, setTags] = useState('')
  const [body, setBody] = useState('')

  useEffect(() => {
    if (!doc) {
      setTitle('')
      setTags('')
      setBody('')
      return
    }
    setTitle(doc.title)
    setTags(tagsToText(doc.tags ?? []))
    setBody(doc.body)
    // Пересбрасываем локальное состояние при смене статьи/версии с сервера.
  }, [doc?.id, doc?.version])

  const dirty = useMemo(() => {
    if (!doc) return false
    return (
      title !== doc.title ||
      body !== doc.body ||
      tagsToText(textToTags(tags)) !== tagsToText(doc.tags ?? [])
    )
  }, [doc, title, body, tags])

  if (isLoading) {
    return (
      <div className="glass-card space-y-4 p-4 md:p-5">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-80 w-full" />
      </div>
    )
  }

  if (!doc) {
    return (
      <div className="glass-card">
        <EmptyState
          icon={FileText}
          size="lg"
          title="Статья не выбрана"
          description="Выберите статью слева или создайте новую"
        />
      </div>
    )
  }

  const published = doc.status === 'published'
  const archived = doc.status === 'archived'
  const busy = saving || publishing || archiving || restoring || deleting
  const canSave = title.trim().length > 0 && body.trim().length > 0

  return (
    <div className="glass-card space-y-4 p-4 md:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-dark-50">Редактор статьи</h2>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-dark-300">
            <Badge variant={STATUS_VARIANT[doc.status] ?? 'secondary'}>
              {STATUS_LABEL[doc.status] ?? doc.status}
            </Badge>
            <span>v{doc.version}</span>
            {doc.slug && <span className="text-dark-400">/{doc.slug}</span>}
            {dirty && <span className="text-amber-400">есть несохранённые изменения</span>}
          </div>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="kb-title">Заголовок</Label>
        <Input
          id="kb-title"
          value={title}
          maxLength={200}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="О чём статья"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="kb-tags">Теги</Label>
        <Input
          id="kb-tags"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="Через запятую: vpn, оплата, подключение"
        />
        <p className="text-xs text-dark-400">До 20 тегов, каждый до 64 символов</p>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor="kb-body">Текст статьи</Label>
          <span className="text-xs text-dark-400">{body.length.toLocaleString('ru-RU')} символов</span>
        </div>
        <Textarea
          id="kb-body"
          value={body}
          rows={20}
          maxLength={200_000}
          onChange={(e) => setBody(e.target.value)}
          className="min-h-[20rem] resize-y font-mono text-[13px] leading-relaxed"
          placeholder="Markdown или обычный текст — так, как статью увидит оператор"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-[var(--glass-border)] pt-3">
        <Button
          variant="default"
          size="sm"
          onClick={() => onSave({ title: title.trim(), tags: textToTags(tags), body })}
          disabled={busy || !canSave || !dirty}
        >
          <Save className="mr-1.5 h-4 w-4" />
          {saving ? 'Сохранение…' : 'Сохранить'}
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={onPublish}
          disabled={busy || published || archived}
          title={published ? 'Статья уже опубликована' : undefined}
        >
          <Send className="mr-1.5 h-4 w-4" />
          {published ? 'Опубликована' : 'Опубликовать'}
        </Button>

        {archived ? (
          <Button variant="secondary" size="sm" onClick={onRestore} disabled={busy}>
            <Undo2 className="mr-1.5 h-4 w-4" />
            {restoring ? 'Восстановление…' : 'Восстановить'}
          </Button>
        ) : (
          <Button variant="secondary" size="sm" onClick={onArchive} disabled={busy}>
            <Archive className="mr-1.5 h-4 w-4" />
            {archiving ? 'Архивация…' : 'В архив'}
          </Button>
        )}

        {!published && (
          <Button
            variant="destructive"
            size="sm"
            className="ml-auto"
            onClick={onDelete}
            disabled={busy}
          >
            <Trash2 className="mr-1.5 h-4 w-4" />
            {deleting ? 'Удаление…' : 'Удалить'}
          </Button>
        )}
      </div>
    </div>
  )
}
