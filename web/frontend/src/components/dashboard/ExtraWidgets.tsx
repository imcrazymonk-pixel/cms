/**
 * Дополнительные виджеты дашборда — данные из других модулей админки
 * (финансы, логи). Компактные, переиспользуют существующие API.
 * Видимость/порядок/ширина — на стороне Dashboard.
 */
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { financeApi, type ChartPoint } from '@/api/finance'
import { logsApi, type LogEntry } from '@/api/logs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Terminal, BarChart3, Maximize2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Bar, Line, ComposedChart, LineChart, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend,
} from 'recharts'

/** Окраска плитки: тонирует рамку/свечение через переменную glass-card. */
type ShellTone = 'default' | 'warning' | 'danger'
const SHELL_TONE: Record<ShellTone, string> = {
  default: '',
  warning: 'border-amber-400/35 hover:border-amber-400/50 [--card-accent-rgb:245,158,11]',
  danger: 'border-red-500/45 hover:border-red-500/60 [--card-accent-rgb:239,68,68]',
}

/** Пропсы виджета: onResize — кнопка изменения ширины (цикл sm/md/lg). */
export interface WidgetSizeProps { onResize?: () => void }

/** Общий каркас виджета: карточка с иконкой, заголовком и ссылкой на раздел. */
function WidgetShell({
  title, subtitle, icon, to, onResize, tone = 'default', children,
}: {
  title: string
  subtitle?: string
  icon: React.ReactNode
  to?: string
  onResize?: () => void
  tone?: ShellTone
  children: React.ReactNode
}) {
  const head = (
    <div className="flex items-center gap-2 min-w-0">
      {icon}
      <CardTitle className="text-base truncate">{title}</CardTitle>
      {subtitle && <span className="text-xs text-muted-foreground truncate">{subtitle}</span>}
    </div>
  )
  return (
    <Card className={cn('h-full', SHELL_TONE[tone])}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          {to ? (
            <Link to={to} className="hover:opacity-80 transition-opacity min-w-0">{head}</Link>
          ) : head}
          {onResize && (
            <button
              type="button"
              onClick={onResize}
              className="shrink-0 p-1 rounded-md text-muted-foreground hover:text-white hover:bg-white/5 transition-colors"
              title="Изменить размер"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

// ── Финансы: график доходов/расходов/баланса (яркий, как в каноне) ──
const FIN_PERIODS: { value: 'daily' | 'weekly' | 'monthly' | 'yearly'; label: string }[] = [
  { value: 'daily', label: 'День' },
  { value: 'weekly', label: 'Неделя' },
  { value: 'monthly', label: 'Месяц' },
  { value: 'yearly', label: 'Год' },
]

function finMoney(v: number): string {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(Math.round(v)) + ' ₽'
}

export function FinanceChartWidget({ onResize }: WidgetSizeProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['finance-widget-chart'],
    queryFn: () => financeApi.getData({ page: 1, per_page: 1 }),
    staleTime: 60_000,
  })

  const [period, setPeriod] = useState<'daily' | 'weekly' | 'monthly' | 'yearly'>('monthly')
  const [type, setType] = useState<'bar' | 'line'>('bar')

  const rows = useMemo(() => {
    const src: ChartPoint[] = (data?.chart?.[period] ?? []) as ChartPoint[]
    return src.map((r) => ({
      name: r.label ?? r.key,
      income: r.income ?? 0,
      expense: r.expense ?? 0,
      balance: r.balance ?? 0,
    }))
  }, [data, period])

  const periodLabel = FIN_PERIODS.find((p) => p.value === period)?.label ?? period

  const tooltipStyle: React.CSSProperties = {
    background: 'rgba(0,0,0,0.85)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '8px',
    color: '#fff',
    fontSize: '12px',
    padding: '6px 10px',
  }

  return (
    <WidgetShell
      title="Финансы — график"
      subtitle={periodLabel}
      to="/finance"
      onResize={onResize}
      icon={<BarChart3 className="w-5 h-5 text-primary-400" />}
    >
      {isLoading ? (
        <Skeleton className="h-44 w-full" />
      ) : rows.length === 0 ? (
        <p className="text-sm text-muted-foreground py-6 text-center">
          Недостаточно данных для графика
        </p>
      ) : (
        <div className="space-y-3">
          {/* Period + type controls */}
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-0.5">
              {FIN_PERIODS.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => setPeriod(p.value)}
                  className={cn(
                    'px-2 py-1 rounded-md text-xs font-medium transition-colors',
                    period === p.value
                      ? 'bg-primary/15 text-primary-400'
                      : 'text-muted-foreground hover:text-white hover:bg-[var(--glass-bg)]',
                  )}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-0.5">
              {(['bar', 'line'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setType(t)}
                  className={cn(
                    'px-2 py-1 rounded-md text-xs font-medium transition-colors',
                    type === t
                      ? 'bg-primary/15 text-primary-400'
                      : 'text-muted-foreground hover:text-white hover:bg-[var(--glass-bg)]',
                  )}
                >
                  {t === 'bar' ? 'Столбцы' : 'Линия'}
                </button>
              ))}
            </div>
          </div>

          {/* Chart */}
          <ResponsiveContainer width="100%" height={220}>
            {type === 'bar' ? (
              <ComposedChart data={rows}>
                <defs>
                  <linearGradient id="finIncome" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4ade80" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="#16a34a" stopOpacity={0.45} />
                  </linearGradient>
                  <linearGradient id="finExpense" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f87171" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="#dc2626" stopOpacity={0.45} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(148,163,184,0.1)" strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke="rgba(148,163,184,0.4)" fontSize={11} />
                <YAxis stroke="rgba(148,163,184,0.4)" fontSize={10} tick={{ fill: 'rgba(148,163,184,0.6)' }} />
                <RechartsTooltip contentStyle={tooltipStyle} formatter={(value) => finMoney(Number(value))} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="income" name="Доход" fill="url(#finIncome)" radius={[4, 4, 0, 0]} maxBarSize={28} />
                <Bar dataKey="expense" name="Расход" fill="url(#finExpense)" radius={[4, 4, 0, 0]} maxBarSize={28} />
                <Line
                  type="monotone" dataKey="balance" name="Баланс"
                  stroke="#2dd4bf" strokeWidth={2.5} dot={{ r: 3, fill: '#2dd4bf', strokeWidth: 0 }}
                />
              </ComposedChart>
            ) : (
              <LineChart data={rows}>
                <CartesianGrid stroke="rgba(148,163,184,0.1)" strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke="rgba(148,163,184,0.4)" fontSize={11} />
                <YAxis stroke="rgba(148,163,184,0.4)" fontSize={10} tick={{ fill: 'rgba(148,163,184,0.6)' }} />
                <RechartsTooltip contentStyle={tooltipStyle} formatter={(value) => finMoney(Number(value))} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="income" name="Доход" stroke="#4ade80" strokeWidth={2.5} dot={{ r: 2.5, fill: '#4ade80', strokeWidth: 0 }} />
                <Line type="monotone" dataKey="expense" name="Расход" stroke="#f87171" strokeWidth={2.5} dot={{ r: 2.5, fill: '#f87171', strokeWidth: 0 }} />
                <Line type="monotone" dataKey="balance" name="Баланс" stroke="#2dd4bf" strokeWidth={2.5} dot={{ r: 2.5, fill: '#2dd4bf', strokeWidth: 0 }} />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
    </WidgetShell>
  )
}

// ── Последние логи: список записей ───────────────────────────────
function formatLogTime(raw: string): string {
  if (!raw) return '—'
  try {
    const d = new Date(raw)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch {
    return '—'
  }
}

function levelBadgeClass(lvl: string): string {
  return cn(
    'px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase shrink-0',
    lvl === 'error' ? 'bg-red-500/20 text-red-400'
      : lvl === 'warning' ? 'bg-amber-500/20 text-amber-400'
        : 'bg-blue-500/20 text-blue-400',
  )
}

export function LogsRecentWidget({ onResize }: WidgetSizeProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['logs-widget-recent'],
    queryFn: () => logsApi.list({ per_page: 8 }),
    staleTime: 30_000,
  })

  const entries = (data as { data?: LogEntry[] } | null)?.data ?? []
  const hasErrors = entries.some((l) => l.level === 'error')
  const hasWarnings = entries.some((l) => l.level === 'warning')
  const tone: ShellTone = hasErrors ? 'danger' : hasWarnings ? 'warning' : 'default'

  return (
    <WidgetShell
      title="Последние логи"
      subtitle={entries.length ? `Показано: ${entries.length}` : undefined}
      to="/logs"
      onResize={onResize}
      tone={tone}
      icon={<Terminal className="w-5 h-5 text-primary-400" />}
    >
      {isLoading ? (
        <Skeleton className="h-44 w-full" />
      ) : entries.length === 0 ? (
        <p className="text-sm text-muted-foreground py-6 text-center">Записей пока нет</p>
      ) : (
        <div className="space-y-0.5">
          {entries.map((l) => (
            <div
              key={l.id}
              className="flex items-center gap-2 py-1.5 border-b border-[var(--glass-border)] last:border-0 min-w-0"
            >
              <Badge variant="secondary" className={levelBadgeClass(l.level)}>
                {l.level}
              </Badge>
              <span className="shrink-0 font-mono text-[10px] text-muted-foreground tabular-nums">
                {formatLogTime(l.created_at)}
              </span>
              <span className="min-w-0 flex-1 truncate text-xs text-white/85" title={l.message}>
                {l.message}
              </span>
            </div>
          ))}
        </div>
      )}
    </WidgetShell>
  )
}
