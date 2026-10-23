import { useEffect, useRef, useState } from 'react'
import { History, Send, CheckCheck, UserCheck, MessagesSquare } from 'lucide-react'
import type {
  ConversationPriority,
  ConversationStatus,
  SupportConversation,
  SupportMessage,
} from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'
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

function initials(conversation: SupportConversation): string {
  return (conversation.subject || conversation.external_id).charAt(0).toUpperCase()
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
        <div className="whitespace-pre-wrap break-words">{message.text || ''}</div>
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
  onReply: (text: string) => void
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
  const scrollRef = useRef<HTMLDivElement>(null)

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

  const handleSubmit = () => {
    const value = text.trim()
    if (!value || sending || !conversation) return
    onReply(value)
    setText('')
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
          <span className="text-[11px] text-dark-400">Enter — отправить · Shift+Enter — новая строка</span>
          <Button size="sm" onClick={handleSubmit} disabled={sending || !text.trim()}>
            <Send className="mr-1.5 h-4 w-4" /> {sending ? 'Отправка…' : 'Отправить'}
          </Button>
        </div>
      </div>
    </div>
  )
}
