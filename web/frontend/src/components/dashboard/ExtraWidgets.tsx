/**
 * Дополнительные виджеты дашборда — данные из других модулей админки
 * (финансы, логи). Компактные, переиспользуют существующие API.
 * Видимость/порядок — на стороне Dashboard.
 */
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { financeApi, type ChartPoint } from '@/api/finance'
import { logsApi } from '@/api/logs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Wallet, Terminal, AlertCircle, AlertTriangle, Info, BarChart3, Maximize2,
} from 'lucide-react'
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

/** Компактный KPI-блок: подпись сверху, значение + единица снизу. */
function Kpi({
  label, value, unit, tone,
}: {
  label: string
  value: string
  unit?: string
  tone?: 'green' | 'red' | 'amber' | 'white'
}) {
  return (
    <div className="min-w-0 bg-[var(--glass-bg)] rounded-lg px-3 py-2.5 border border-[var(--glass-border)]">
      <p className="text-xs text-muted-foreground truncate" title={label}>{label}</p>
      <p
        className={cn(
          'flex items-baseline gap-1 whitespace-nowrap font-bold tabular-nums leading-tight',
          tone === 'green' ? 'text-green-400'
            : tone === 'red' ? 'text-red-400'
              : tone === 'amber' ? 'text-amber-400'
                : 'text-white',
        )}
      >
        <span className="min-w-0 text-lg truncate">{value}</span>
        {unit && <span className="shrink-0 text-[11px] font-medium text-muted-foreground">{unit}</span>}
      </p>
    </div>
  )
}

// ── Логи: количество записей по уровням ──────────────────────────
function useLogCount(level: string) {
  return useQuery({
    queryKey: ['logs-widget-count', level],
    queryFn: () => logsApi.list({ level, per_page: 1 }),
    staleTime: 60_000,
  })
}

export function LogsWidget() {
  const errors = useLogCount('error')
  const warnings = useLogCount('warning')
  const info = useLogCount('info')
  const loading = errors.isLoading || warnings.isLoading || info.isLoading

  const errCount = errors.data?.total ?? 0
  const warnCount = warnings.data?.total ?? 0
  const infoCount = info.data?.total ?? 0
  const tone: ShellTone = errCount > 0 ? 'danger' : warnCount > 0 ? 'warning' : 'default'

  return (
    <WidgetShell
      title="Логи"
      subtitle="Записи"
      to="/logs"
      icon={<Terminal className="w-5 h-5 text-primary-400" />}
      tone={tone}
    >
      {loading ? (
        <Skeleton className="h-20 w-full" />
      ) : (
        <>
          <div className="grid grid-cols-3 gap-2">
            <Kpi label="Ошибки" value={String(errCount)} tone="red" />
            <Kpi label="Предупреждения" value={String(warnCount)} tone="amber" />
            <Kpi label="Инфо" value={String(infoCount)} tone="white" />
          </div>
          <div className="mt-2 flex items-center gap-3 text-xs">
            {errCount > 0 ? (
              <span className="inline-flex items-center gap-1 text-red-400">
                <AlertCircle className="w-3.5 h-3.5" /> Есть ошибки
              </span>
            ) : warnCount > 0 ? (
              <span className="inline-flex items-center gap-1 text-amber-400">
                <AlertTriangle className="w-3.5 h-3.5" /> Есть предупреждения
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-green-400">
                <Info className="w-3.5 h-3.5" /> Проблем не найдено
              </span>
            )}
          </div>
        </>
      )}
    </WidgetShell>
  )
}

// ── Финансы: график доходов/расходов/баланса ─────────────────────
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
                <CartesianGrid stroke="rgba(148,163,184,0.08)" strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke="rgba(148,163,184,0.3)" fontSize={11} />
                <YAxis stroke="rgba(148,163,184,0.3)" fontSize={10} tick={{ fill: 'rgba(148,163,184,0.5)' }} />
                <RechartsTooltip contentStyle={tooltipStyle} formatter={(value) => finMoney(Number(value))} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="income" name="Доход" fill="#22c55e" radius={[4, 4, 0, 0]} maxBarSize={28} />
                <Bar dataKey="expense" name="Расход" fill="#ef4444" radius={[4, 4, 0, 0]} maxBarSize={28} />
                <Line type="monotone" dataKey="balance" name="Баланс" stroke="#2dd4bf" strokeWidth={2} dot={false} />
              </ComposedChart>
            ) : (
              <LineChart data={rows}>
                <CartesianGrid stroke="rgba(148,163,184,0.08)" strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke="rgba(148,163,184,0.3)" fontSize={11} />
                <YAxis stroke="rgba(148,163,184,0.3)" fontSize={10} tick={{ fill: 'rgba(148,163,184,0.5)' }} />
                <RechartsTooltip contentStyle={tooltipStyle} formatter={(value) => finMoney(Number(value))} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="income" name="Доход" stroke="#22c55e" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="expense" name="Расход" stroke="#ef4444" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="balance" name="Баланс" stroke="#2dd4bf" strokeWidth={2} dot={false} />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
    </WidgetShell>
  )
}
