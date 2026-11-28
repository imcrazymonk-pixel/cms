import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, UserRound, CreditCard, Ticket, Activity, Trash2, StickyNote, Copy } from 'lucide-react'
import { toast } from 'sonner'
import { supportApi, type SupportCustomerCard } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { EmptyState } from '@/components/EmptyState'
import { toastMutationError } from '@/lib/mutationToast'
import { cn } from '@/lib/utils'
import { formatDateUtil as formatDate } from '@/lib/useFormatters'

const SUB_STATUS_STYLES: Record<string, string> = {
  active: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  expired: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  trial: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  blocked: 'bg-red-500/20 text-red-400 border-red-500/30',
}

function formatGb(gb?: number | null): string {
  if (gb == null) return '—'
  if (gb >= 100) return `${Math.round(gb)} ГБ`
  return `${gb.toFixed(2)} ГБ`
}

function copySubscriptionLink(url: string) {
  void navigator.clipboard.writeText(url)
  toast.success('Скопировано')
}

interface CustomerCardProps {
  card: SupportCustomerCard | undefined
  isLoading: boolean
  isRefreshing: boolean
  onRefresh: () => void
  /** id профиля клиента (`support_customer_profile`) — для внутренних заметок. */
  customerProfileId?: number | null
  /** Текущий оператор — чтобы пометить свою заметку. */
  currentUserId?: number | null
}

export function CustomerCard({
  card,
  isLoading,
  isRefreshing,
  onRefresh,
  customerProfileId = null,
  currentUserId = null,
}: CustomerCardProps) {
  const queryClient = useQueryClient()
  const [noteText, setNoteText] = useState('')

  const notesQuery = useQuery({
    queryKey: ['support', 'notes', customerProfileId],
    queryFn: () => supportApi.listNotes(customerProfileId as number),
    enabled: customerProfileId != null,
  })

  const createNoteMutation = useMutation({
    mutationFn: (text: string) => supportApi.createNote(customerProfileId as number, { text }),
    onSuccess: () => {
      setNoteText('')
      queryClient.invalidateQueries({ queryKey: ['support', 'notes', customerProfileId] })
      toast.success('Заметка добавлена')
    },
    onError: (err) => toastMutationError(err, 'Не удалось добавить заметку'),
  })

  const deleteNoteMutation = useMutation({
    mutationFn: (noteId: number) => supportApi.deleteNote(noteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['support', 'notes', customerProfileId] })
      toast.success('Заметка удалена')
    },
    onError: (err) => toastMutationError(err, 'Не удалось удалить заметку'),
  })

  if (isLoading && !card) {
    return (
      <div className="glass-card space-y-3 p-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-20 w-full rounded-xl" />
      </div>
    )
  }

  if (!card) {
    return (
      <div className="glass-card">
        <EmptyState icon={UserRound} size="sm" title="Карточка клиента" description="Выберите диалог, чтобы увидеть данные клиента" className="py-10" />
      </div>
    )
  }

  const { subscription } = card
  const traffic = subscription?.traffic
  const usedGb =
    subscription?.traffic_used_gb ??
    (traffic?.used_bytes != null ? traffic.used_bytes / 1024 ** 3 : null)
  const limitGb =
    subscription?.traffic_limit_gb ??
    (traffic?.limit_bytes != null ? traffic.limit_bytes / 1024 ** 3 : null)
  const trafficPercent =
    usedGb != null && limitGb != null && limitGb > 0
      ? Math.min(100, (usedGb / limitGb) * 100)
      : null

  const rows: Array<{ label: string; value: string; valueClassName?: string }> = [
    { label: 'Telegram ID', value: card.telegram_id != null ? String(card.telegram_id) : '—' },
    { label: 'Username', value: card.username || '—' },
    {
      label: 'Баланс',
      value: card.balance_rub != null ? `${card.balance_rub.toLocaleString('ru-RU')} ₽` : '—',
      valueClassName: card.balance_rub != null && card.balance_rub < 0 ? 'text-red-400' : undefined,
    },
    { label: 'Тикеты', value: String(card.tickets_total ?? 0) },
    { label: 'Последняя активность', value: card.last_activity ? formatDate(card.last_activity) : '—' },
  ]

  return (
    <div className="glass-card p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Карточка клиента</h3>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onRefresh} disabled={isRefreshing} aria-label="Обновить карточку">
          <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
        </Button>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-primary-500/20 text-base font-bold text-primary-300">
          {(card.display_name || card.username || '?').charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-white">{card.display_name || card.username || 'Без имени'}</p>
          <p className="truncate text-xs text-dark-400">{card.provider} · обновлено {formatDate(card.fetched_at)}</p>
        </div>
      </div>

      {/* Подписка */}
      {subscription && subscription.status ? (
        <div className="mt-3 rounded-xl border border-[var(--glass-border)] bg-[var(--glass-bg)] p-3">
          <div className="flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-dark-300" />
            <Badge className={cn('text-[10px]', SUB_STATUS_STYLES[subscription.status] || SUB_STATUS_STYLES.expired)}>
              {subscription.is_trial ? 'Trial' : subscription.status}
            </Badge>
            {subscription.end_date && (
              <span className="text-xs text-dark-300">→ {formatDate(subscription.end_date)}</span>
            )}
            {subscription.subscription_url && (
              <Button
                variant="ghost"
                size="icon"
                className="ml-auto h-6 w-6 text-dark-400 hover:text-dark-100"
                onClick={() => copySubscriptionLink(subscription.subscription_url as string)}
                aria-label="Скопировать ссылку подписки"
                title="Скопировать ссылку подписки"
              >
                <Copy className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
          {subscription.tariff_name && (
            <div className="mt-1.5 flex items-center justify-between gap-2 text-xs">
              <span className="text-dark-400">Тариф</span>
              <span className="truncate font-medium text-dark-100">{subscription.tariff_name}</span>
            </div>
          )}
          {subscription.device_limit != null && (
            <div className="mt-1 flex items-center justify-between gap-2 text-xs">
              <span className="text-dark-400">Устройства</span>
              <span className="font-medium text-dark-100">
                {subscription.device_count ?? 0} / {subscription.device_limit}
              </span>
            </div>
          )}
          {(usedGb != null || limitGb != null) && (
            <div className="mt-1.5 space-y-1">
              <div className="flex items-center gap-1.5 text-xs text-dark-300">
                <Activity className="h-3.5 w-3.5" />
                {formatGb(usedGb)} / {formatGb(limitGb)}
                {trafficPercent != null && (
                  <span className="text-dark-400">· {Math.round(trafficPercent)}%</span>
                )}
              </div>
              {trafficPercent != null && (
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-dark-600">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      trafficPercent > 90
                        ? 'bg-red-500'
                        : trafficPercent > 70
                          ? 'bg-amber-500'
                          : 'bg-emerald-500',
                    )}
                    style={{ width: `${trafficPercent}%` }}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="mt-3 flex items-center gap-2 rounded-xl border border-[var(--glass-border)] bg-[var(--glass-bg)] p-3 text-xs text-dark-300">
          <CreditCard className="h-4 w-4" /> Подписка не найдена
        </div>
      )}

      {/* Данные */}
      <div className="mt-3 space-y-1.5">
        {rows
          .filter((r) => r.label !== 'Последняя активность')
          .map((row) => (
            <div key={row.label} className="flex items-center justify-between text-xs">
              <span className="text-dark-400">{row.label}</span>
              <span className={cn('font-medium text-dark-100', row.valueClassName)}>{row.value}</span>
            </div>
          ))}
        <div className="flex items-center justify-between text-xs">
          <span className="text-dark-400">Последняя активность</span>
          <span className="font-medium text-dark-100">{rows.find((r) => r.label === 'Последняя активность')?.value}</span>
        </div>
      </div>

      {/* Remnawave — фаза 5 */}
      <div className="mt-3 flex items-center gap-1.5 rounded-lg bg-dark-500/10 px-2.5 py-1.5 text-[11px] text-dark-400">
        <Ticket className="h-3.5 w-3.5" />
        {card.remnawave?.available
          ? 'Remnawave подключён'
          : 'Remnawave — deep-карточка появится в фазе 5'}
      </div>

      {/* Внутренние заметки о клиенте */}
      {customerProfileId != null && (
        <div className="mt-4 border-t border-[var(--glass-border)] pt-3">
          <div className="flex items-center gap-1.5">
            <StickyNote className="h-4 w-4 text-dark-300" />
            <h4 className="text-xs font-semibold text-white">Заметки</h4>
            <span className="text-[10px] text-dark-400">внутренние, клиент не видит</span>
          </div>

          <div className="mt-2 space-y-1.5">
            {notesQuery.isLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : (notesQuery.data?.items.length ?? 0) === 0 ? (
              <p className="text-[11px] text-dark-400">Заметок пока нет</p>
            ) : (
              notesQuery.data?.items.map((note) => (
                <div
                  key={note.id}
                  className="rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] p-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="whitespace-pre-wrap break-words text-xs text-dark-100">{note.text}</p>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 shrink-0 text-dark-400 hover:text-red-400"
                      onClick={() => deleteNoteMutation.mutate(note.id)}
                      disabled={deleteNoteMutation.isPending}
                      aria-label="Удалить заметку"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                  <p className="mt-1 text-[10px] text-dark-400">
                    {note.actor_name}
                    {currentUserId != null && note.actor_id === currentUserId && ' (вы)'}
                    {note.created_at && <> · {formatDate(note.created_at)}</>}
                  </p>
                </div>
              ))
            )}
          </div>

          <div className="mt-2 space-y-1.5">
            <Textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Новая заметка…"
              rows={2}
              maxLength={2000}
              className="min-h-[60px] text-xs"
            />
            <div className="flex justify-end">
              <Button
                size="sm"
                onClick={() => {
                  const value = noteText.trim()
                  if (value) createNoteMutation.mutate(value)
                }}
                disabled={createNoteMutation.isPending || !noteText.trim()}
              >
                {createNoteMutation.isPending ? 'Добавление…' : 'Добавить'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
