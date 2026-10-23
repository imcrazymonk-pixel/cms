import { useMemo } from 'react'
import { Inbox, Search, X, RefreshCw, ChevronDown } from 'lucide-react'
import type { SupportConversation } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'
import { cn } from '@/lib/utils'
import { formatDateShortUtil as formatDateShort } from '@/lib/useFormatters'

const STATUS_OPTIONS = [
  { value: '', label: 'Все' },
  { value: 'open', label: 'Открытые' },
  { value: 'pending', label: 'Ожидают' },
  { value: 'resolved', label: 'Решённые' },
]

const statusBadge: Record<string, string> = {
  open: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  pending: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  resolved: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  closed: 'bg-dark-500/20 text-dark-300 border-dark-500/30',
}

function relativeTime(d?: string | null): string {
  if (!d) return '—'
  const diffMin = Math.floor((Date.now() - new Date(d).getTime()) / 60_000)
  if (diffMin < 1) return 'сейчас'
  if (diffMin < 60) return `${diffMin}м`
  const hours = Math.floor(diffMin / 60)
  if (hours < 24) return `${hours}ч`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}д`
  return formatDateShort(d)
}

function getInitialColor(id: number): string {
  const colors = [
    'bg-blue-500/20 text-blue-400',
    'bg-emerald-500/20 text-emerald-400',
    'bg-amber-500/20 text-amber-400',
    'bg-violet-500/20 text-violet-400',
    'bg-pink-500/20 text-pink-400',
    'bg-cyan-500/20 text-cyan-400',
  ]
  return colors[id % colors.length]
}

interface ConversationListProps {
  items: SupportConversation[]
  activeId: number | null
  isLoading: boolean
  hasNextPage: boolean
  isFetchingNextPage: boolean
  statusFilter: string
  search: string
  onStatusFilter: (value: string) => void
  onSearch: (value: string) => void
  onSelect: (id: number) => void
  onLoadMore: () => void
  onRefresh: () => void
}

export function ConversationList({
  items,
  activeId,
  isLoading,
  hasNextPage,
  isFetchingNextPage,
  statusFilter,
  search,
  onStatusFilter,
  onSearch,
  onSelect,
  onLoadMore,
  onRefresh,
}: ConversationListProps) {
  const unreadTotal = useMemo(() => items.reduce((acc, c) => acc + c.unread, 0), [items])

  return (
    <div className="glass-card flex min-h-0 flex-col overflow-hidden">
      {/* Filters */}
      <div className="space-y-2 border-b border-[var(--glass-border)] p-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dark-300" />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            placeholder="Поиск по тексту…"
            className="h-10 w-full rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] pl-10 pr-8 text-sm text-white placeholder:text-dark-300 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
          />
          {search && (
            <button
              onClick={() => onSearch('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-dark-400 hover:text-white"
              aria-label="Очистить"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <select
              value={statusFilter}
              onChange={(e) => onStatusFilter(e.target.value)}
              className="h-9 w-full appearance-none rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] px-3 pr-8 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-dark-400" />
          </div>
          <Button variant="secondary" size="icon" className="h-9 w-9 shrink-0" onClick={onRefresh} disabled={isLoading} aria-label="Обновить список">
            <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* List */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading && items.length === 0 ? (
          <div className="space-y-2 p-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-2.5 rounded-lg p-2">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1"><Skeleton className="h-4 w-3/4" /><Skeleton className="mt-1.5 h-3 w-1/2" /></div>
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState icon={Inbox} size="sm" title="Очередь пуста" description="Обращений по выбранным фильтрам нет" className="py-12" />
        ) : (
          <ul className="divide-y divide-[var(--glass-border)]">
            {items.map((conv) => {
              const active = conv.id === activeId
              return (
                <li key={conv.id}>
                  <button
                    onClick={() => onSelect(conv.id)}
                    className={cn(
                      'flex w-full items-start gap-2.5 p-3 text-left transition-colors hover:bg-[var(--glass-bg-hover)]',
                      active && 'bg-[var(--glass-bg-hover)] ring-1 ring-inset ring-primary-500/40',
                    )}
                  >
                    <div className={cn('mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold', getInitialColor(conv.id))}>
                      {(conv.subject || conv.external_id).charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-medium text-white">
                          {conv.subject || `Тикет #${conv.external_id}`}
                        </span>
                        <span className="shrink-0 text-[10px] text-dark-400">{relativeTime(conv.last_message_at)}</span>
                      </div>
                      <div className="mt-1 flex items-center gap-1.5">
                        <Badge className={cn('text-[10px]', statusBadge[conv.status] || statusBadge.closed)}>
                          {conv.status}
                        </Badge>
                        <span className={cn('text-[10px] capitalize', conv.priority === 'urgent' ? 'text-red-400' : conv.priority === 'high' ? 'text-amber-400' : 'text-dark-400')}>
                          {conv.priority}
                        </span>
                        {conv.unread > 0 && (
                          <span className="ml-auto flex h-4.5 min-w-[18px] items-center justify-center rounded-full bg-primary-500 px-1 text-[10px] font-bold text-white">
                            {conv.unread}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-[var(--glass-border)] p-2">
        {hasNextPage ? (
          <Button
            variant="ghost"
            className="w-full"
            onClick={onLoadMore}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? 'Загрузка…' : 'Загрузить ещё'}
          </Button>
        ) : (
          <p className="py-1 text-center text-[11px] text-dark-400">
            {items.length > 0 ? `${items.length} из ${items.length}${unreadTotal > 0 ? ` · ${unreadTotal} непрочитанных` : ''}` : ' '}
          </p>
        )}
      </div>
    </div>
  )
}
