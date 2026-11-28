import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { History, Send, CheckCheck, UserCheck, UserMinus, MessagesSquare, Paperclip, FileText, X, Loader2, Download } from 'lucide-react'
import type {
  ConversationPriority,
  ConversationStatus,
  SupportAiSuggestion,
  SupportConversation,
  SupportMessage,
  SupportTemplate,
} from '@/api/support'
import { supportApi } from '@/api/support'
import { AiDraftCard, type SuggestionDecision } from './AiDraftCard'
import { TemplatePicker, useSupportTemplates } from './TemplatePicker'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'
import { toast } from 'sonner'
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
/** Не чаще одного heartbeat `typing` в 5 с на диалог (совпадает с бэкендом). */
const TYPING_THROTTLE_MS = 5000
const SLASH_RE = /^\/[a-z0-9_-]*$/

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
        {message.reply_excerpt && (
          <div
            className={cn(
              'mb-1.5 rounded-md border-l-2 px-2 py-1 text-[11px] leading-snug',
              incoming
                ? 'border-primary-500/60 bg-black/20 text-dark-200'
                : 'border-white/60 bg-white/10 text-white/80',
            )}
          >
            <span className="line-clamp-3 whitespace-pre-wrap break-words">{message.reply_excerpt}</span>
          </div>
        )}
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
  /** Текущий оператор — для логики «Взять / Освободить / Перехватить». */
  currentUserId: number | null
  assigneePending: boolean
  statePending: boolean
  sending: boolean
  onMarkRead: (id: number) => void
  onState: (patch: { status?: ConversationStatus; priority?: ConversationPriority }) => void
  /** null — освободить диалог, число — назначить на себя. */
  onAssign: (assigneeId: number | null) => void
  onResolve: () => void
  onReply: (text: string, attachmentIds: string[]) => void
  /** Ожидающая ИИ-предложка из `GET /conversations/{id}` (null — нет). */
  suggestion?: SupportAiSuggestion | null
  suggestionPending?: boolean
  onSuggestionDecision?: (
    decision: SuggestionDecision,
    opts?: { final_text?: string; reason?: string },
  ) => void
  onEditSuggestionText?: (text: string) => void
  onSuggestionWrong?: (payload: { verdict: 'wrong'; corrected_text?: string }) => void
  /** Тик из родителя: перенести текст предложки в композер и сфокусировать его. */
  suggestionEditSignal?: number
  /** Явный текст для переноса (родитель фиксирует его до инвалидации предложки). */
  suggestionEditText?: string
  /** Лимит размера файла из настроек (МБ); 8 — безопасный дефолт. */
  mediaMaxMb?: number
}

export function MessageThread({
  conversation,
  messages,
  isLoading,
  currentUserId,
  assigneePending,
  statePending,
  sending,
  onMarkRead,
  onState,
  onAssign,
  onResolve,
  onReply,
  suggestion = null,
  suggestionPending = false,
  onSuggestionDecision,
  onEditSuggestionText,
  onSuggestionWrong,
  suggestionEditSignal = 0,
  suggestionEditText,
  mediaMaxMb = 8,
}: MessageThreadProps) {
  const [text, setText] = useState('')
  const [tokens, setTokens] = useState<UploadedToken[]>([])
  const [uploading, setUploading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const lastTypingPingRef = useRef(0)

  // Слэш-подсказка: текст целиком `/...` → до 5 шаблонов из общего запроса подбора.
  const slashQuery = SLASH_RE.test(text) ? text.slice(1) : null
  const slashTemplatesQuery = useSupportTemplates(slashQuery ?? '', slashQuery !== null)
  const slashItems = slashQuery !== null ? (slashTemplatesQuery.data?.items ?? []).slice(0, 5) : []

  // Присутствие операторов в диалоге (сервер отдаёт только свежие, TTL 120 с).
  const presenceQuery = useQuery({
    queryKey: ['support', 'presence', conversation?.id],
    queryFn: () => supportApi.getPresence(conversation?.id as number),
    enabled: conversation != null,
    refetchInterval: 15_000,
  })

  // Отмечаем прочитанным при открытии диалога с непрочитанными
  useEffect(() => {
    if (conversation && conversation.unread > 0) onMarkRead(conversation.id)
  }, [conversation, onMarkRead])

  // Heartbeat «смотрю» при открытии/смене диалога; при смене сбрасываем троттлинг печати.
  useEffect(() => {
    const id = conversation?.id
    if (id == null) return
    supportApi.pingPresence({ conversation_id: id, state: 'viewing' }).catch(() => {})
    return () => {
      lastTypingPingRef.current = 0
    }
  }, [conversation?.id])

  // Автопрокрутка к свежему
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages.length, conversation?.id])

  // «Править» в ИИ-черновике: родитель поднимает сигнал, текст переезжает в композер.
  // Сигнал 0 — начальное состояние, на монтировании ничего не переносим.
  // Текст берём из явного пропса: suggestion к этому моменту может быть уже null.
  useEffect(() => {
    if (!suggestionEditSignal) return
    const draft =
      suggestionEditText !== undefined
        ? suggestionEditText
        : suggestion?.final_text || suggestion?.text || ''
    setText(draft)
    textareaRef.current?.focus()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [suggestionEditSignal])

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

  // ── Шаблоны и присутствие ─────────────────────────────────────
  /** Вставка шаблона в позицию курсора (или в конец) без потери вложений. */
  const insertTemplate = (body: string) => {
    const el = textareaRef.current
    const start = el?.selectionStart ?? text.length
    const end = el?.selectionEnd ?? start
    setText((prev) => prev.slice(0, start) + body + prev.slice(end))
    requestAnimationFrame(() => {
      const node = textareaRef.current
      if (!node) return
      node.focus()
      const pos = start + body.length
      node.setSelectionRange(pos, pos)
    })
  }

  /** Слэш-подсказка заменяет весь текст телом выбранного шаблона. */
  const applySlashTemplate = (template: SupportTemplate) => {
    setText(template.body)
    textareaRef.current?.focus()
  }

  /** Heartbeat «печатает» — не чаще 1 раза в 5 с. */
  const pingTyping = () => {
    const now = Date.now()
    if (now - lastTypingPingRef.current < TYPING_THROTTLE_MS) return
    lastTypingPingRef.current = now
    supportApi
      .pingPresence({ conversation_id: conversation.id, state: 'typing' })
      .catch(() => {})
  }

  const presenceItems = (presenceQuery.data?.items ?? []).filter(
    (item) => !(currentUserId != null && item.actor_id === currentUserId),
  )
  const viewers = presenceItems.filter((item) => item.state === 'viewing').map((item) => item.actor_name)
  const typers = presenceItems.filter((item) => item.state === 'typing').map((item) => item.actor_name)

  const handlePickFiles = async (files: FileList | null) => {
    if (!files || !files.length) return
    const freeSlots = MAX_ATTACHMENTS - tokens.length
    const accepted = Array.from(files).slice(0, Math.max(0, freeSlots))
    if (!accepted.length) {
      toastMutationError(new Error('Слишком много файлов за раз (максимум 10)'), 'Максимум 10 вложений')
      return
    }
    const tooLarge = accepted.find((file) => file.size > mediaMaxMb * 1024 * 1024)
    if (tooLarge) {
      toast.error(`Файл «${tooLarge.name}» больше ${mediaMaxMb} МБ — уменьшите размер`)
      if (fileInputRef.current) fileInputRef.current.value = ''
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

  // ── Назначение ────────────────────────────────────────────────
  const assignedToMe = currentUserId != null && conversation.assignee_id === currentUserId
  const assignedToOther = conversation.assignee_id != null && !assignedToMe

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
              {conversation.assignee_id && (
                <span className="ml-2 text-primary-300">
                  {assignedToMe ? '· ваш диалог' : '· ведёт другой'}
                </span>
              )}
            </p>
            {(viewers.length > 0 || typers.length > 0) && (
              <p className="mt-0.5 text-[11px] text-dark-300">
                {viewers.length > 0 && <>Смотрит: {viewers.join(', ')}</>}
                {viewers.length > 0 && typers.length > 0 && ' · '}
                {typers.length > 0 && <>печатает: {typers.join(', ')}</>}
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {assignedToOther && (
              <>
                <Badge variant="warning" className="text-[10px]">Ведёт другой</Badge>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => currentUserId != null && onAssign(currentUserId)}
                  disabled={assigneePending || statePending || currentUserId == null}
                  title="Перехватить диалог у другого оператора"
                >
                  <UserCheck className="mr-1.5 h-3.5 w-3.5" /> Перехватить
                </Button>
              </>
            )}
            {assignedToMe && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onAssign(null)}
                disabled={assigneePending || statePending}
                title="Снять назначение с себя"
              >
                <UserMinus className="mr-1.5 h-3.5 w-3.5" /> Освободить
              </Button>
            )}
            {conversation.assignee_id == null && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => currentUserId != null && onAssign(currentUserId)}
                disabled={assigneePending || statePending || currentUserId == null}
              >
                <UserCheck className="mr-1.5 h-3.5 w-3.5" /> Взять диалог
              </Button>
            )}
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

      {/* ИИ-черновик — над композером, только когда есть предложка */}
      {suggestion && onSuggestionDecision && onEditSuggestionText && onSuggestionWrong && (
        <AiDraftCard
          suggestion={suggestion}
          pending={suggestionPending}
          onDecide={onSuggestionDecision}
          onEdit={onEditSuggestionText}
          onWrong={onSuggestionWrong}
        />
      )}

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
          ref={textareaRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            pingTyping()
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              // Пока открыта слэш-подсказка, Enter не отправляет ответ.
              if (slashItems.length > 0) return
              e.preventDefault()
              handleSubmit()
            }
          }}
          placeholder="Сообщение… (Enter — отправить, Shift+Enter — новая строка)"
          rows={2}
          className="w-full resize-none rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] p-3 text-sm text-white placeholder:text-dark-300 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
        />
        {slashItems.length > 0 && (
          <div className="mt-1 overflow-hidden rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg-solid)]">
            {slashItems.map((template) => (
              <button
                key={template.id}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => applySlashTemplate(template)}
                className="flex w-full items-baseline gap-2 px-2.5 py-1.5 text-left hover:bg-[var(--glass-bg-hover)]"
              >
                <span className="shrink-0 font-mono text-[11px] text-primary-300">/{template.shortcut}</span>
                <span className="truncate text-xs text-dark-100">{template.title}</span>
              </button>
            ))}
          </div>
        )}
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
            <span className="text-[11px] text-dark-400">до {mediaMaxMb} МБ</span>
            <TemplatePicker onPick={insertTemplate} />
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
