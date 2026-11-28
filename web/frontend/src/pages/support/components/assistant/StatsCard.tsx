import { BarChart3 } from 'lucide-react'
import type { SupportAiStats } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export interface StatsCardProps {
  stats?: SupportAiStats
  days: 7 | 30
  loading: boolean
  onDaysChange: (days: 7 | 30) => void
}

interface MetricProps {
  label: string
  value: string
  accent?: string
}

function Metric({ label, value, accent }: MetricProps) {
  return (
    <div className="rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] px-2.5 py-2">
      <p className="text-[10px] uppercase tracking-wide text-dark-400">{label}</p>
      <p className={cn('mt-0.5 text-sm font-semibold', accent ?? 'text-white')}>{value}</p>
    </div>
  )
}

/** Статистика ИИ за 7/30 дней + CSS-бары по дням (без chart-библиотек). */
export function StatsCard({ stats, days, loading, onDaysChange }: StatsCardProps) {
  const byDay = stats?.by_day ?? []
  const max = Math.max(1, ...byDay.map((d) => Math.max(d.generated, d.sent)))

  return (
    <Card className="space-y-3 p-4 md:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-primary-300" />
          <h2 className="text-sm font-semibold text-white">Статистика</h2>
        </div>
        <div className="flex items-center gap-1">
          {([7, 30] as const).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={days === value ? 'default' : 'secondary'}
              onClick={() => onDaysChange(value)}
            >
              {value} дн.
            </Button>
          ))}
        </div>
      </div>

      {loading && !stats ? (
        <div className="space-y-2">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : !stats ? (
        <p className="text-xs text-dark-400">Нет данных.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Metric label="Сгенерировано" value={String(stats.generated)} />
            <Metric label="Отправлено" value={String(stats.sent)} accent="text-green-400" />
            <Metric label="Правок" value={String(stats.edited)} accent="text-yellow-400" />
            <Metric label="Отклонено" value={String(stats.rejected)} accent="text-red-400" />
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-dark-300">
            <span>
              Доля отправки:{' '}
              <span className="font-medium text-white">{Math.round(stats.sent_rate * 100)}%</span>
            </span>
            <span>
              Средняя уверенность:{' '}
              <span className="font-medium text-white">{Math.round(stats.avg_confidence * 100)}%</span>
            </span>
            <span>
              Токены: <span className="font-medium text-white">{(stats.tokens_in + stats.tokens_out).toLocaleString('ru-RU')}</span>
            </span>
          </div>

          {byDay.length > 0 && (
            <div>
              <div className="flex h-24 items-end gap-[2px]">
                {byDay.map((day) => {
                  const generatedHeight = Math.max(2, Math.round((day.generated / max) * 100))
                  const sentHeight = Math.max(2, Math.round((day.sent / max) * 100))
                  return (
                    <div
                      key={day.date}
                      className="flex h-full flex-1 flex-col justify-end gap-[1px]"
                      title={`${day.date}: сгенерировано ${day.generated}, отправлено ${day.sent}`}
                    >
                      <div
                        className="w-full rounded-sm bg-primary-500/40"
                        style={{ height: `${generatedHeight}%` }}
                      />
                      <div
                        className="w-full rounded-sm bg-green-500/60"
                        style={{ height: `${sentHeight}%` }}
                      />
                    </div>
                  )
                })}
              </div>
              <div className="mt-1.5 flex items-center gap-3 text-[10px] text-dark-400">
                <span className="inline-flex items-center gap-1">
                  <span className="h-2 w-2 rounded-sm bg-primary-500/40" /> сгенерировано
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="h-2 w-2 rounded-sm bg-green-500/60" /> отправлено
                </span>
                <span className="ml-auto">{byDay[0]?.date} — {byDay[byDay.length - 1]?.date}</span>
              </div>
            </div>
          )}

          {stats.shadow > 0 && (
            <Badge variant="secondary">в тени: {stats.shadow} · авто: {stats.auto_sent} · предложек: {stats.suggest_sent}</Badge>
          )}
        </>
      )}
    </Card>
  )
}
