import { FileText, Search } from 'lucide-react'
import type { KbDocStatus, SupportKbListItem } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'
import { cn } from '@/lib/utils'

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

function relativeTime(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const diffMin = Math.floor((Date.now() - date.getTime()) / 60_000)
  if (diffMin < 1) return 'сейчас'
  if (diffMin < 60) return `${diffMin}м назад`
  const hours = Math.floor(diffMin / 60)
  if (hours < 24) return `${hours}ч назад`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}д назад`
  return date.toLocaleDateString('ru-RU')
}

export interface KbListProps {
  items: SupportKbListItem[]
  total: number
  activeId: number | null
  isLoading: boolean
  emptyTitle?: string
  emptyDescription?: string
  onSelect: (id: number) => void
}

/** Левая колонка базы знаний: статьи выбранного статуса с бейджем и версией. */
export function KbList({
  items,
  total,
  activeId,
  isLoading,
  emptyTitle = 'Статей нет',
  emptyDescription = 'Создайте статью или измените поисковый запрос',
  onSelect,
}: KbListProps) {
  return (
    <div className="glass-card flex min-h-0 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-[var(--glass-border)] px-3 py-2 text-xs text-dark-300">
        <span className="inline-flex items-center gap-1.5">
          <Search className="h-3.5 w-3.5" />
          Найдено
        </span>
        <span className="font-medium text-dark-100">{total}</span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto xl:max-h-[calc(100vh-340px)]">
        {isLoading && items.length === 0 ? (
          <div className="space-y-2 p-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-1.5 rounded-lg p-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            icon={FileText}
            size="sm"
            title={emptyTitle}
            description={emptyDescription}
            className="py-12"
          />
        ) : (
          <ul className="divide-y divide-[var(--glass-border)]">
            {items.map((item) => {
              const active = item.id === activeId
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(item.id)}
                    aria-current={active ? 'true' : undefined}
                    className={cn(
                      'w-full px-3 py-2.5 text-left transition-colors hover:bg-[var(--glass-bg-hover)]',
                      active && 'bg-[var(--glass-bg-hover)]',
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="line-clamp-2 text-sm font-medium text-dark-50">{item.title}</span>
                      <Badge variant={STATUS_VARIANT[item.status] ?? 'secondary'} className="shrink-0">
                        {STATUS_LABEL[item.status] ?? item.status}
                      </Badge>
                    </div>
                    {item.excerpt && (
                      <p className="mt-1 line-clamp-2 text-xs text-dark-300">{item.excerpt}</p>
                    )}
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-dark-400">
                      <span>v{item.version}</span>
                      <span>·</span>
                      <span>{relativeTime(item.updated_at)}</span>
                      {item.source && item.source !== 'manual' && (
                        <>
                          <span>·</span>
                          <span>{item.source}</span>
                        </>
                      )}
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
