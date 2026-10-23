import { RefreshCw, UserRound, CreditCard, Ticket, Activity } from 'lucide-react'
import type { SupportCustomerCard } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'
import { cn } from '@/lib/utils'
import { formatDateUtil as formatDate } from '@/lib/useFormatters'

const SUB_STATUS_STYLES: Record<string, string> = {
  active: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  expired: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  trial: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  blocked: 'bg-red-500/20 text-red-400 border-red-500/30',
}

function formatTraffic(bytes?: number | null): string {
  if (bytes == null) return '—'
  const gb = bytes / 1024 ** 3
  if (gb >= 100) return `${Math.round(gb)} ГБ`
  return `${gb.toFixed(2)} ГБ`
}

interface CustomerCardProps {
  card: SupportCustomerCard | undefined
  isLoading: boolean
  isRefreshing: boolean
  onRefresh: () => void
}

export function CustomerCard({ card, isLoading, isRefreshing, onRefresh }: CustomerCardProps) {
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
          </div>
          {traffic && (traffic.used_bytes != null || traffic.limit_bytes != null) && (
            <div className="mt-1.5 flex items-center gap-1.5 text-xs text-dark-300">
              <Activity className="h-3.5 w-3.5" />
              {formatTraffic(traffic.used_bytes)} / {formatTraffic(traffic.limit_bytes)}
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
    </div>
  )
}
