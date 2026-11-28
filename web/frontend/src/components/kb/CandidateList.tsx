import { Check, Lightbulb, X } from 'lucide-react'
import type { SupportKbCandidate } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'

export interface CandidateListProps {
  items: SupportKbCandidate[]
  total: number
  isLoading: boolean
  pendingId: number | null
  onAccept: (candidate: SupportKbCandidate) => void
  onReject: (candidate: SupportKbCandidate) => void
}

function formatDate(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

/** Идеи статей из фидбека и импорта: принять (создаст черновик) или отклонить. */
export function CandidateList({
  items,
  total,
  isLoading,
  pendingId,
  onAccept,
  onReject,
}: CandidateListProps) {
  return (
    <div className="glass-card flex min-h-0 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-[var(--glass-border)] px-3 py-2 text-xs text-dark-300">
        <span className="inline-flex items-center gap-1.5">
          <Lightbulb className="h-3.5 w-3.5" />
          Новые идеи
        </span>
        <span className="font-medium text-dark-100">{total}</span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto xl:max-h-[calc(100vh-340px)]">
        {isLoading && items.length === 0 ? (
          <div className="space-y-2 p-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-1.5 rounded-lg p-2">
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            icon={Lightbulb}
            size="sm"
            title="Идей нет"
            description="Идеи появляются из отметок «это неверно» и импорта истории"
            className="py-12"
          />
        ) : (
          <ul className="divide-y divide-[var(--glass-border)]">
            {items.map((candidate) => {
              const pending = pendingId === candidate.id
              return (
                <li key={candidate.id} className="space-y-2 px-3 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-dark-50">
                      {candidate.topic || candidate.question || `Идея #${candidate.id}`}
                    </p>
                    <Badge variant="warning" className="shrink-0">
                      ×{candidate.occurrences}
                    </Badge>
                  </div>

                  {candidate.question && (
                    <p className="line-clamp-3 text-xs text-dark-200">{candidate.question}</p>
                  )}
                  {candidate.answer && (
                    <p className="line-clamp-3 text-xs text-dark-400">Ответ: {candidate.answer}</p>
                  )}

                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] text-dark-400">
                      {candidate.source} · {formatDate(candidate.created_at)}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <Button
                        variant="secondary"
                        size="sm"
                        className="h-7 px-2 text-xs"
                        onClick={() => onReject(candidate)}
                        disabled={pending}
                      >
                        <X className="mr-1 h-3.5 w-3.5" />
                        Отклонить
                      </Button>
                      <Button
                        size="sm"
                        className="h-7 px-2 text-xs"
                        onClick={() => onAccept(candidate)}
                        disabled={pending}
                      >
                        <Check className="mr-1 h-3.5 w-3.5" />
                        {pending ? '…' : 'Принять'}
                      </Button>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
