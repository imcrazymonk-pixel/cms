/**
 * Дополнительные виджеты дашборда — данные из других модулей админки
 * (финансы, логи). Компактные, переиспользуют существующие API.
 * Видимость/порядок — на стороне Dashboard.
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { financeApi } from '@/api/finance'
import { logsApi } from '@/api/logs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Wallet, Terminal, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

function money(v: number, cur = 'RUB'): string {
  return (
    new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(Math.round(v)) +
    (cur ? ` ${cur}` : '')
  )
}

/** Окраска плитки: тонирует рамку/свечение через переменную glass-card. */
type ShellTone = 'default' | 'warning' | 'danger'
const SHELL_TONE: Record<ShellTone, string> = {
  default: '',
  warning: 'border-amber-400/35 hover:border-amber-400/50 [--card-accent-rgb:245,158,11]',
  danger: 'border-red-500/45 hover:border-red-500/60 [--card-accent-rgb:239,68,68]',
}

/** Общий каркас виджета: карточка с иконкой, заголовком и ссылкой на раздел. */
function WidgetShell({
  title, subtitle, icon, to, tone = 'default', children,
}: {
  title: string
  subtitle?: string
  icon: React.ReactNode
  to?: string
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

// ── Финансы: итоги (доходы / расходы / баланс) ───────────────────
export function FinanceWidget() {
  const { data, isLoading } = useQuery({
    queryKey: ['finance-widget-summary'],
    queryFn: () => financeApi.getData({ page: 1, per_page: 1 }),
    staleTime: 60_000,
  })
  const s = data?.summary
  const net = s?.balance ?? 0

  return (
    <WidgetShell
      title="Финансы"
      subtitle="Итоги"
      to="/finance"
      icon={<Wallet className="w-5 h-5 text-primary-400" />}
      tone={net >= 0 ? 'default' : 'danger'}
    >
      {isLoading ? (
        <Skeleton className="h-20 w-full" />
      ) : (
        <div className="grid grid-cols-3 gap-2">
          <Kpi label="Доходы" value={money(s?.income ?? 0, '')} unit="₽" tone="green" />
          <Kpi label="Расходы" value={money(s?.expense ?? 0, '')} unit="₽" tone="red" />
          <Kpi label="Баланс" value={money(net, '')} unit="₽" tone={net >= 0 ? 'green' : 'red'} />
        </div>
      )}
    </WidgetShell>
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
