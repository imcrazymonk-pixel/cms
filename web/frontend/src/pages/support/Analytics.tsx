import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart3, RefreshCw } from 'lucide-react'
import {
  getSupportErrorMessage,
  supportApi,
  type SupportAnalyticsAi,
  type SupportAnalyticsChannel,
  type SupportAnalyticsDay,
  type SupportAnalyticsFirstResponse,
  type SupportAnalyticsOperator,
  type SupportAnalyticsPriority,
  type SupportAnalyticsTotals,
} from '@/api/support'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'
import { QueryError } from '@/components/QueryError'

type Days = 7 | 30 | 90

const DAY_OPTIONS: Days[] = [7, 30, 90]

const PRIORITY_LABEL: Record<string, string> = {
  low: 'Низкий',
  normal: 'Обычный',
  high: 'Высокий',
  urgent: 'Срочный',
}

const PRIORITY_ORDER: Record<string, number> = { low: 0, normal: 1, high: 2, urgent: 3 }

function formatNumber(value: number): string {
  return value.toLocaleString('ru-RU')
}

/** Минуты → короткая длительность; `null` — прочерк. */
function formatMinutes(minutes: number | null): string {
  if (minutes == null || !Number.isFinite(minutes)) return '—'
  if (minutes < 1) return '< 1 мин'
  if (minutes < 60) return `${Math.round(minutes)} мин`
  if (minutes < 1440) {
    const hours = minutes / 60
    return `${Number.isInteger(hours) ? hours : hours.toFixed(1)} ч`
  }
  const days = minutes / 1440
  return `${Number.isInteger(days) ? days : days.toFixed(1)} д`
}

function formatDateTime(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

interface MetricProps {
  label: string
  value: string
  hint?: string
  accent?: string
}

function Metric({ label, value, hint, accent }: MetricProps) {
  return (
    <div className="rounded-xl border border-[var(--glass-border)]/50 bg-[var(--glass-bg)] p-3">
      <p className="text-xs text-dark-300">{label}</p>
      <p className={cn('mt-1 text-2xl font-semibold tabular-nums', accent ?? 'text-white')}>
        {value}
      </p>
      {hint && <p className="mt-0.5 text-[11px] text-dark-400">{hint}</p>}
    </div>
  )
}

function TotalsGrid({ totals }: { totals: SupportAnalyticsTotals }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <Metric label="Новые диалоги" value={formatNumber(totals.conversations_created)} />
      <Metric
        label="Решено"
        value={formatNumber(totals.conversations_resolved)}
        accent="text-green-400"
      />
      <Metric label="Сообщений вх." value={formatNumber(totals.messages_in)} />
      <Metric label="Сообщений исх." value={formatNumber(totals.messages_out)} />
      <Metric
        label="Открыто сейчас"
        value={formatNumber(totals.open_now)}
        accent="text-primary-300"
      />
      <Metric
        label="Без исполнителя"
        value={formatNumber(totals.unassigned_now)}
        accent={totals.unassigned_now > 0 ? 'text-yellow-400' : undefined}
      />
    </div>
  )
}

function FirstResponseCard({ data }: { data: SupportAnalyticsFirstResponse }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>Первый ответ</CardTitle>
      </CardHeader>
      <CardContent>
        {data.count === 0 ? (
          <p className="py-4 text-sm text-dark-300">Нет данных за период</p>
        ) : (
          <div className="grid grid-cols-3 gap-3">
            <Metric label="Медиана" value={formatMinutes(data.median_minutes)} />
            <Metric label="P90" value={formatMinutes(data.p90_minutes)} />
            <Metric label="Ответов" value={formatNumber(data.count)} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/** Два столбика на день (входящие/исходящие), высота — % от максимума. */
function DayBars({ days }: { days: SupportAnalyticsDay[] }) {
  if (days.length === 0) {
    return <p className="py-6 text-sm text-dark-300">Нет данных за период</p>
  }

  const max = Math.max(1, ...days.map((day) => Math.max(day.incoming, day.outgoing)))
  const labelStep = Math.max(1, Math.ceil(days.length / 12))

  return (
    <div>
      <div className="flex h-40 items-end gap-[2px]">
        {days.map((day) => {
          const incomingHeight =
            day.incoming > 0 ? Math.max(2, Math.round((day.incoming / max) * 100)) : 0
          const outgoingHeight =
            day.outgoing > 0 ? Math.max(2, Math.round((day.outgoing / max) * 100)) : 0
          return (
            <div
              key={day.date}
              className="flex h-full flex-1 items-end gap-[1px]"
              title={`${day.date}: входящих ${day.incoming}, исходящих ${day.outgoing}`}
            >
              <div
                className="w-1/2 rounded-sm bg-primary-500/50"
                style={{ height: `${incomingHeight}%` }}
              />
              <div
                className="w-1/2 rounded-sm bg-green-500/60"
                style={{ height: `${outgoingHeight}%` }}
              />
            </div>
          )
        })}
      </div>

      <div className="mt-1 flex gap-[2px]">
        {days.map((day, index) => (
          <div
            key={day.date}
            className="min-w-0 flex-1 whitespace-nowrap text-center text-[9px] tabular-nums text-dark-400"
          >
            {index % labelStep === 0 ? day.date.slice(5) : '\u00a0'}
          </div>
        ))}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-dark-300">
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-primary-500/50" /> входящие
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-green-500/60" /> исходящие
        </span>
        <span className="ml-auto">
          {days[0]?.date} — {days[days.length - 1]?.date}
        </span>
      </div>
    </div>
  )
}

function ChannelsTable({ items }: { items: SupportAnalyticsChannel[] }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>Каналы</CardTitle>
      </CardHeader>
      <CardContent className="p-0 md:p-0">
        {items.length === 0 ? (
          <p className="p-4 text-sm text-dark-300 md:p-6">Нет данных за период</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--glass-border)]/40 text-left text-xs uppercase tracking-wide text-dark-400">
                <th className="px-4 py-2 font-medium md:px-6">Канал</th>
                <th className="px-4 py-2 text-right font-medium md:px-6">Диалоги</th>
                <th className="px-4 py-2 text-right font-medium md:px-6">Сообщения</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr
                  key={row.channel}
                  className="border-b border-[var(--glass-border)]/30 last:border-b-0"
                >
                  <td className="px-4 py-2 text-dark-100 md:px-6">{row.channel}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-white md:px-6">
                    {formatNumber(row.conversations)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-dark-100 md:px-6">
                    {formatNumber(row.messages)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  )
}

function PrioritiesTable({ items }: { items: SupportAnalyticsPriority[] }) {
  const sorted = [...items].sort(
    (a, b) =>
      (PRIORITY_ORDER[a.priority] ?? 99) - (PRIORITY_ORDER[b.priority] ?? 99) ||
      a.priority.localeCompare(b.priority),
  )

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>Приоритеты</CardTitle>
      </CardHeader>
      <CardContent className="p-0 md:p-0">
        {sorted.length === 0 ? (
          <p className="p-4 text-sm text-dark-300 md:p-6">Нет данных за период</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--glass-border)]/40 text-left text-xs uppercase tracking-wide text-dark-400">
                <th className="px-4 py-2 font-medium md:px-6">Приоритет</th>
                <th className="px-4 py-2 text-right font-medium md:px-6">Диалоги</th>
                <th className="px-4 py-2 text-right font-medium md:px-6">Просрочки</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr
                  key={row.priority}
                  className="border-b border-[var(--glass-border)]/30 last:border-b-0"
                >
                  <td className="px-4 py-2 text-dark-100 md:px-6">
                    {PRIORITY_LABEL[row.priority] ?? row.priority}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-white md:px-6">
                    {formatNumber(row.conversations)}
                  </td>
                  <td
                    className={cn(
                      'px-4 py-2 text-right tabular-nums md:px-6',
                      row.breached_first_response > 0 ? 'text-red-400' : 'text-dark-100',
                    )}
                  >
                    {formatNumber(row.breached_first_response)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  )
}

function OperatorsTable({ items }: { items: SupportAnalyticsOperator[] }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>Операторы</CardTitle>
      </CardHeader>
      <CardContent className="p-0 md:p-0">
        {items.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            size="sm"
            title="Ответов операторов нет"
            description="За выбранный период операторы не отвечали в диалогах."
          />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--glass-border)]/40 text-left text-xs uppercase tracking-wide text-dark-400">
                <th className="px-4 py-2 font-medium md:px-6">Оператор</th>
                <th className="px-4 py-2 text-right font-medium md:px-6">Ответов</th>
                <th className="px-4 py-2 text-right font-medium md:px-6">Диалогов</th>
                <th className="px-4 py-2 text-right font-medium md:px-6">Последний ответ</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr
                  key={row.actor_id}
                  className="border-b border-[var(--glass-border)]/30 last:border-b-0"
                >
                  <td className="px-4 py-2 md:px-6">
                    <p className="text-dark-100">{row.display_name || row.login}</p>
                    <p className="text-[11px] text-dark-400">@{row.login}</p>
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-white md:px-6">
                    {formatNumber(row.replies)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-dark-100 md:px-6">
                    {formatNumber(row.conversations)}
                  </td>
                  <td className="px-4 py-2 text-right text-dark-200 md:px-6">
                    {formatDateTime(row.last_reply_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  )
}

function AiCard({ ai }: { ai: SupportAnalyticsAi }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>ИИ-ассистент</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric label="Сгенерировано" value={formatNumber(ai.generated)} />
          <Metric label="Отправлено" value={formatNumber(ai.sent)} accent="text-green-400" />
          <Metric label="Правок" value={formatNumber(ai.edited)} accent="text-yellow-400" />
          <Metric label="Отклонено" value={formatNumber(ai.rejected)} accent="text-red-400" />
          <Metric label="Авто" value={formatNumber(ai.auto_sent)} />
          <Metric label="Предложка" value={formatNumber(ai.suggest_sent)} />
          <Metric label="Тень" value={formatNumber(ai.shadow)} />
        </div>
        {ai.auto_sent + ai.suggest_sent + ai.shadow > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge variant="success">авто: {ai.auto_sent}</Badge>
            <Badge variant="default">предложек: {ai.suggest_sent}</Badge>
            <Badge variant="secondary">в тени: {ai.shadow}</Badge>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-4 md:space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-24 w-full" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-56 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  )
}

/**
 * Аналитика саппорта (`/support/analytics`).
 *
 * Один снимок за окно `days` (7/30/90): сводка, первый ответ, дневные бары,
 * каналы, приоритеты, нагрузка операторов и использование ИИ. Всё только
 * читается — экран не пишет в бэкенд.
 */
export default function SupportAnalyticsPage() {
  const [days, setDays] = useState<Days>(30)

  const analyticsQuery = useQuery({
    queryKey: ['support', 'analytics', days],
    queryFn: () => supportApi.getAnalytics(days),
    refetchOnWindowFocus: true,
  })

  const data = analyticsQuery.data

  const handleRefresh = () => {
    void analyticsQuery.refetch()
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Аналитика</h1>
          <p className="mt-1 text-sm text-dark-200">
            Метрики очереди, SLA и операторов · {days} дней
          </p>
        </div>
        <div className="page-header-actions flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1">
            {DAY_OPTIONS.map((value) => (
              <Button
                key={value}
                size="sm"
                variant={days === value ? 'default' : 'secondary'}
                onClick={() => setDays(value)}
              >
                {value} дн.
              </Button>
            ))}
          </div>
          <Button
            variant="secondary"
            size="icon"
            onClick={handleRefresh}
            disabled={analyticsQuery.isFetching}
            aria-label="Обновить"
          >
            <RefreshCw className={cn('h-5 w-5', analyticsQuery.isFetching && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {analyticsQuery.isError && (
        <QueryError
          onRetry={handleRefresh}
          message={
            getSupportErrorMessage(analyticsQuery.error) || 'Не удалось загрузить аналитику'
          }
        />
      )}

      {analyticsQuery.isLoading ? (
        <AnalyticsSkeleton />
      ) : data ? (
        <>
          <TotalsGrid totals={data.totals} />

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle>Динамика по дням</CardTitle>
              </CardHeader>
              <CardContent>
                <DayBars days={data.by_day} />
              </CardContent>
            </Card>
            <FirstResponseCard data={data.first_response} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2 lg:items-start">
            <ChannelsTable items={data.by_channel} />
            <PrioritiesTable items={data.by_priority} />
          </div>

          <OperatorsTable items={data.by_operator} />

          <AiCard ai={data.ai} />
        </>
      ) : null}
    </div>
  )
}
