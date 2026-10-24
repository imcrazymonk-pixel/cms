import { useEffect, useRef, useState } from 'react'
import { History, Send, CheckCheck, UserCheck, MessagesSquare, Paperclip, FileText, X, Loader2, Download } from 'lucide-react'
import type {
  ConversationPriority,
  ConversationStatus,
  SupportConversation,
  SupportMessage,
} from '@/api/support'
import { supportApi } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'
import { toastMutationError } from '@/lib/mutationToast'
import { cn } from '@/lib/utils'
import { formatDateUtil as formatDate } from '@/lib/useFormatters'

const STATUS_OPTIONS: Array<{ value: ConversationStatus; label: string }> = [
  { value: 'open', label: 'Открыт' },
  { value: 'pending', label: 'Ожидает' },
  { value: 'resolved', label: 'Решён' },
  { value: 'closed', label: 'Закрыт' },
]

const PRIORITY_OPTIONS: Array<{ value: ConversationPriority; label: string }> = [
  { value: 'low', label: 'Низкий' },
  { value: 'normal', label: 'Обычный' },
  { value: 'high', label: 'Высокий' },
  { value: 'urgent', label: 'Срочный' },
]

const MAX_ATTACHMENTS = 10

function initials(conversation: SupportConversation): string {
  return (conversation.subject || conversation.external_id).charAt(0).toUpperCase()
}

// ── Вложения ────────────────────────────────────────────────────────────────

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function BlobImage({ attachmentId, alt }: { attachmentId: number; alt: string }) {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    supportApi
      .getAttachmentBlob(attachmentId)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [attachmentId])

  if (failed) {
    return <span className="text-[11px] text-red-400">Не удалось загрузить вложение</span>
  }
  if (!url) return <Skeleton className="h-28 w-44 rounded-xl" />
  return <img src={url} alt={alt} loading="lazy" className="max-h-56 max-w-[260px] rounded-xl object-cover" />
}

type MessageAttachment = NonNullable<SupportMessage['attachment']>

function AttachmentContent({ attachment }: { attachment: MessageAttachment }) {
  const [downloading, setDownloading] = useState(false)
  const isImage = (attachment.mime_type || '').startsWith('image/')
  const name = attachment.original_name || 'вложение'
  const sizeKb = attachment.size != null ? Math.round(attachment.size / 1024) : null

  if (isImage) {
    return <BlobImage attachmentId={attachment.id} alt={name} />
  }

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const blob = await supportApi.getAttachmentBlob(attachment.id, true)
      downloadBlob(blob, name)
    } catch (e) {
      toastMutationError(e, 'Не удалось скачать вложение')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <button
      onClick={handleDownload}
      disabled={downloading}
      className="mt-1 flex max-w-[260px] items-center gap-2 rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg-hover)] px-2.5 py-1.5 text-xs hover:border-primary-500/40 disabled:opacity-60"
      title={`Скачать ${name}`}
    >
      <FileText className="h-4 w-4 shrink-0 text-primary-300" />
      <span className="min-w-0 truncate">{name}</span>
      <span className="text-[10px] text-dark-400">{sizeKb != null && sizeKb > 0 ? `${sizeKb} КБ` : ''}</span>
      {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5 text-dark-300" />}
    </button>
  )
}

function MessageBubble({ message }: { message: SupportMessage }) {
  // Системные заметки — по центру бейджем
  if (message.author === 'system') {
    return (
      <div className="my-1 flex justify-center">
        <Badge className="bg-dark-500/20 text-dark-300 border-dark-500/30 text-[10px] max-w-[80%] truncate">
          {message.text || 'Системное сообщение'}
        </Badge>
      </div>
    )
  }

  const incoming = message.direction === 'in'
  return (
    <div className={cn('flex w-full', incoming ? 'justify-start' : 'justify-end')}>
      <div
        className={cn(
          'max-w-[78%] rounded-2xl px-3.5 py-2 text-sm shadow-sm',
          incoming
            ? 'rounded-tl-md bg-[var(--glass-bg-hover)] border border-[var(--glass-border)] text-white'
            : 'rounded-tr-md bg-primary-500/90 text-white',
        )}
      >
        {message.attachment && <AttachmentContent attachment={message.attachment} />}
        {message.text && <div className="whitespace-pre-wrap break-words">{message.text}</div>}
        <div className={cn('mt-1 flex items-center gap-1.5 text-[10px]', incoming ? 'text-dark-400' : 'text-white/70')}>
          <span>{formatDate(message.created_at)}</span>
          {message.is_backfill && (
            <span className="inline-flex items-center gap-0.5 rounded bg-dark-500/40 px-1">
              <History className="h-2.5 w-2.5" /> история
            </span>
          )}
          {!incoming && <CheckCheck className="h-3 w-3" />}
        </div>
      </div>
    </div>
  )
}

interface UploadedToken {
  token: string
  name: string
}

interface MessageThreadProps {
  conversation: SupportConversation | undefined
  messages: SupportMessage[]
  isLoading: boolean
  assigneePending: boolean
  statePending: boolean
  sending: boolean
  onMarkRead: (id: number) => void
  onState: (patch: { status?: ConversationStatus; priority?: ConversationPriority }) => void
  onAssign: () => void
  onResolve: () => void
  onReply: (text: string, attachmentIds: string[]) => void
}

export function MessageThread({
  conversation,
  messages,
  isLoading,
  assigneePending,
  statePending,
  sending,
  onMarkRead,
  onState,
  onAssign,
  onResolve,
  onReply,
}: MessageThreadProps) {
  const [text, setText] = useState('')
  const [tokens, setTokens] = useState<UploadedToken[]>([])
  const [uploading, setUploading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Отмечаем прочитанным при открытии диалога с непрочитанными
  useEffect(() => {
    if (conversation && conversation.unread > 0) onMarkRead(conversation.id)
  }, [conversation, onMarkRead])

  // Автопрокрутка к свежему
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages.length, conversation?.id])

  if (isLoading) {
    return (
      <div className="glass-card flex h-full flex-col p-4">
        <Skeleton className="h-10 w-64" />
        <div className="mt-4 space-y-3">
          <Skeleton className="ml-auto h-16 w-1/2 rounded-2xl" />
          <Skeleton className="h-16 w-1/2 rounded-2xl" />
          <Skeleton className="ml-auto h-16 w-1/2 rounded-2xl" />
        </div>
      </div>
    )
  }

  if (!conversation) {
    return (
      <div className="glass-card flex h-full flex-col">
        <EmptyState icon={MessagesSquare} title="Диалог не выбран" description="Выберите обращение в очереди слева" />
      </div>
    )
  }

  const handlePickFiles = async (files: FileList | null) => {
    if (!files || !files.length) return
    const freeSlots = MAX_ATTACHMENTS - tokens.length
    const accepted = Array.from(files).slice(0, Math.max(0, freeSlots))
    if (!accepted.length) {
      toastMutationError(new Error('Слишком много файлов за раз (максимум 10)'), 'Максимум 10 вложений')
      return
    }
    setUploading(true)
    try {
      const results = await Promise.all(accepted.map((file) => supportApi.uploadAttachment(file)))
      setTokens((prev) => [
        ...prev,
        ...results.map((r, index) => ({ token: r.token, name: r.original_name || accepted[index].name })),
      ])
    } catch (e) {
      toastMutationError(e, 'Не удалось загрузить файл')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleSubmit = () => {
    const value = text.trim()
    if ((!value && !tokens.length) || uploading || sending || !conversation) return
    onReply(value, tokens.map((t) => t.token))
    setText('')
    setTokens([])
  }

  const removeToken = (index: number) => {
    setTokens((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="glass-card flex min-h-0 flex-col">
      {/* Header */}
      <div className="border-b border-[var(--glass-border)] p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500/20 text-xs font-bold text-primary-300">
                {initials(conversation)}
              </div>
              <h2 className="truncate text-sm font-semibold text-white">
                {conversation.subject || `Тикет #${conversation.external_id}`}
              </h2>
            </div>
            <p className="mt-0.5 text-[11px] text-dark-400">
              {conversation.channel} · {conversation.external_id}
              {conversation.assignee_id && <span className="ml-2 text-primary-300">· в работе</span>}
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            <Button variant="secondary" size="sm" onClick={onAssign} disabled={assigneePending || statePending}>
              <UserCheck className="mr-1.5 h-3.5 w-3.5" /> Взять диалог
            </Button>
            <Button variant="secondary" size="sm" onClick={onResolve} disabled={statePending || assigneePending}>
              <CheckCheck className="mr-1.5 h-3.5 w-3.5" /> Решено
            </Button>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <select
            value={conversation.status}
            onChange={(e) => onState({ status: e.target.value as ConversationStatus })}
            disabled={statePending}
            className="h-8 w-auto appearance-none rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] px-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-primary-500/50"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            value={conversation.priority}
            onChange={(e) => onState({ status: conversation.status, priority: e.target.value as ConversationPriority })}
            disabled={statePending}
            className="h-8 w-auto appearance-none rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] px-2 text-xs capitalize text-white focus:outline-none focus:ring-2 focus:ring-primary-500/50"
          >
            {PRIORITY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-2 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <EmptyState size="sm" title="Сообщений пока нет" className="py-10" />
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-[var(--glass-border)] p-3">
        {tokens.length > 0 && (
          <div className="mb-2 flex flex-wrap items-center gap-1.5">
            {tokens.map((t, index) => (
              <span
                key={t.token}
                className="inline-flex items-center gap-1 rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg-hover)] px-2 py-1 text-xs"
              >
                <Paperclip className="h-3 w-3 text-primary-300" />
                <span className="max-w-[140px] truncate">{t.name}</span>
                <button
                  onClick={() => removeToken(index)}
                  disabled={uploading}
                  className="text-dark-400 hover:text-white"
                  aria-label="Убрать файл"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault()
              handleSubmit()
            }
          }}
          placeholder="Сообщение… (Enter — отправить, Shift+Enter — новая строка)"
          rows={2}
          className="w-full resize-none rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] p-3 text-sm text-white placeholder:text-dark-300 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
        />
        <div className="mt-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => handlePickFiles(e.target.files)}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || tokens.length >= MAX_ATTACHMENTS}
              title="Прикрепить файл"
            >
              {uploading ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Paperclip className="mr-1.5 h-4 w-4" />}
              {uploading ? 'Загрузка…' : 'Файл'}
            </Button>
            <span className="text-[11px] text-dark-400">Enter — отправить · Shift+Enter — новая строка</span>
          </div>
          <Button size="sm" onClick={handleSubmit} disabled={sending || uploading || (!text.trim() && !tokens.length)}>
            <Send className="mr-1.5 h-4 w-4" /> {sending ? 'Отправка…' : 'Отправить'}
          </Button>
        </div>
      </div>
    </div>
  )
}
