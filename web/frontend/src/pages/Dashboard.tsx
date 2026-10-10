import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { dashboardApi, DashboardStats } from '../api/dashboard'
import { financeApi } from '@/api/finance'
import { logsApi } from '@/api/logs'
import {
  RotateCcw, LayoutGrid, FileText, MessageCircle, Wallet, Terminal,
  ArrowUpRight, ArrowLeftRight,
} from 'lucide-react'
import { useWidgetVisibility } from '@/lib/useWidgetVisibility'
import { useOrderPreference } from '@/lib/useOrderPreference'
import { useWidgetSize, SIZE_SPAN } from '@/lib/useWidgetSize'
import { SortableSection } from '@/components/SortableSection'
import { FinanceChartWidget, LogsRecentWidget } from '@/components/dashboard/ExtraWidgets'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  TouchSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  rectSortingStrategy,
  arrayMove,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

const DASHBOARD_WIDGETS = ['stats', 'finance_chart', 'logs'] as const

type WidgetId = (typeof DASHBOARD_WIDGETS)[number]

const WIDGET_LABELS: Record<WidgetId, string> = {
  stats: 'Статистика',
  finance_chart: 'Финансы — график',
  logs: 'Последние логи',
}

// Виджеты с изменяемой шириной (полная / половина / треть) — по клику на Maximize2
const RESIZABLE = new Set<WidgetId>(['finance_chart', 'logs'])

// ── StatCard colors (Remnawave palette) ──────────────────────────

const STAT_COLORS = {
  cyan:   { rgb: '6, 182, 212',   text: 'text-cyan-400',    hoverText: 'group-hover:text-cyan-400' },
  green:  { rgb: '34, 197, 94',   text: 'text-emerald-400', hoverText: 'group-hover:text-emerald-400' },
  yellow: { rgb: '234, 179, 8',   text: 'text-amber-400',   hoverText: 'group-hover:text-amber-400' },
  violet: { rgb: '139, 92, 246',  text: 'text-violet-400',  hoverText: 'group-hover:text-violet-400' },
  red:    { rgb: '239, 68, 68',   text: 'text-red-400',     hoverText: 'group-hover:text-red-400' },
  blue:   { rgb: '59, 130, 246',  text: 'text-blue-400',    hoverText: 'group-hover:text-blue-400' },
} as const

type StatColor = keyof typeof STAT_COLORS

function money(v: number): string {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(Math.round(v)) + ' ₽'
}

/** Анимация значения 0 → target за ~800мс (как в каноне Remnawave). */
function useCountUp(target: string | number, loading?: boolean): string {
  const [display, setDisplay] = useState('0')
  const rafRef = useRef<number>(0)

  useEffect(() => {
    if (loading) return

    const str = String(target)
    // Убираем разделители (запятые, пробелы и неразрывные пробелы ru-RU)
    const cleaned = str.replace(/[,\s\u00A0]/g, '')
    const num = parseFloat(cleaned)
    if (!isFinite(num) || num === 0 || str === '-' || /[/]/.test(str)) {
      setDisplay(str)
      return
    }

    const isInt = Number.isInteger(num) && !cleaned.includes('.')
    const suffix = cleaned.length < str.length ? str.slice(cleaned.indexOf(String(num)) + String(num).length) : ''

    const duration = 800
    const start = performance.now()

    const tick = (now: number) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      const current = eased * num

      if (isInt) {
        setDisplay(new Intl.NumberFormat('ru-RU').format(Math.round(current)) + suffix)
      } else {
        setDisplay(current.toFixed(1) + suffix)
      }

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        setDisplay(str)
      }
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, loading])

  return display
}

// ── Remnawave-style StatCard (с «Подробнее» и кликом на раздел) ───

function StatCard({
  title, value, icon: Icon, color, subtitle, to, loading, index = 0,
}: {
  title: string
  value: string | number
  icon: React.ElementType
  color: StatColor
  subtitle?: string
  to?: string
  loading: boolean
  index?: number
}) {
  const cfg = STAT_COLORS[color]
  const animatedValue = useCountUp(value, loading)
  const navigate = useNavigate()

  return (
    <div
      className={cn(
        'animate-fade-in-up group relative overflow-hidden rounded-xl transition-all duration-300',
        to && 'cursor-pointer hover:-translate-y-1 hover:shadow-lg',
      )}
      role={to ? 'button' : undefined}
      tabIndex={to ? 0 : undefined}
      onClick={to ? () => navigate(to) : undefined}
      onKeyDown={to ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(to) } } : undefined}
      style={{
        animationDelay: `${index * 0.06}s`,
        background: `linear-gradient(135deg, rgba(${cfg.rgb}, 0.06) 0%, var(--glass-bg) 50%, rgba(${cfg.rgb}, 0.03) 100%)`,
        backdropFilter: 'blur(var(--glass-blur, 24px))',
        WebkitBackdropFilter: 'blur(var(--glass-blur, 24px))',
        border: '1px solid var(--glass-border)',
      }}
    >
      {/* Top accent line */}
      <div
        className="absolute inset-x-0 top-0 h-[2px] opacity-40 group-hover:opacity-80 transition-opacity duration-300"
        style={{ background: `linear-gradient(90deg, transparent 5%, rgba(${cfg.rgb}, 0.7) 50%, transparent 95%)` }}
      />
      {/* Hover glow */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-400 pointer-events-none rounded-xl"
        style={{ boxShadow: `inset 0 0 40px -15px rgba(${cfg.rgb}, 0.12), 0 0 25px -8px rgba(${cfg.rgb}, 0.2)` }}
      />
      <div className="px-4 py-3.5 relative">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">{title}</p>
            {loading ? (
              <Skeleton className="h-8 w-20 mt-1.5" />
            ) : (
              <p className="text-xl md:text-2xl font-bold text-foreground mt-1 tracking-tight tabular-nums">
                {animatedValue}
              </p>
            )}
            {subtitle && (
              <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed truncate" title={subtitle}>
                {subtitle}
              </p>
            )}
          </div>
          <div
            className="p-2.5 rounded-xl shrink-0 transition-all duration-300 group-hover:scale-110 group-hover:rotate-3"
            style={{
              background: `rgba(${cfg.rgb}, 0.1)`,
              border: `1px solid rgba(${cfg.rgb}, 0.2)`,
              boxShadow: `0 0 20px -8px rgba(${cfg.rgb}, 0.25)`,
            }}
          >
            <Icon className={cn('w-5 h-5 transition-colors duration-300', cfg.text)} />
          </div>
        </div>
        {to && (
          <span className={cn(
            'text-[11px] text-muted-foreground flex items-center gap-1 transition-all duration-200 mt-2.5 group-hover:gap-1.5',
            cfg.hoverText,
          )}>
            Подробнее
            <ArrowUpRight className="w-3 h-3 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </span>
        )}
      </div>
    </div>
  )
}

// ── Комбинированная карточка «Доход / Расход» (Вариант A) ────────

function FinanceFlowCard({
  income, expense, loading, index = 0, to,
}: {
  income: number
  expense: number
  loading: boolean
  index?: number
  to: string
}) {
  const inc = useCountUp(money(income), loading)
  const exp = useCountUp(money(expense), loading)
  const navigate = useNavigate()

  return (
    <div
      className="animate-fade-in-up group relative overflow-hidden rounded-xl transition-all duration-300 cursor-pointer hover:-translate-y-1 hover:shadow-lg"
      role="button"
      tabIndex={0}
      onClick={() => navigate(to)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(to) } }}
      style={{
        animationDelay: `${index * 0.06}s`,
        background: 'linear-gradient(135deg, rgba(34,197,94,0.07) 0%, var(--glass-bg) 50%, rgba(239,68,68,0.04) 100%)',
        backdropFilter: 'blur(var(--glass-blur, 24px))',
        WebkitBackdropFilter: 'blur(var(--glass-blur, 24px))',
        border: '1px solid var(--glass-border)',
      }}
    >
      {/* Top accent line */}
      <div
        className="absolute inset-x-0 top-0 h-[2px] opacity-40 group-hover:opacity-80 transition-opacity duration-300"
        style={{ background: 'linear-gradient(90deg, transparent 5%, rgba(34,197,94,0.7) 25%, rgba(239,68,68,0.7) 75%, transparent 95%)' }}
      />
      {/* Hover glow */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-400 pointer-events-none rounded-xl"
        style={{ boxShadow: 'inset 0 0 40px -15px rgba(34,197,94,0.12), 0 0 25px -8px rgba(34,197,94,0.2)' }}
      />
      <div className="px-4 py-3.5 relative">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">Доход / Расход</p>
            {loading ? (
              <Skeleton className="h-10 w-24 mt-1.5" />
            ) : (
              <div className="mt-1 space-y-0.5">
                <p className="text-base md:text-lg font-bold text-emerald-400 tracking-tight tabular-nums leading-tight">+{inc}</p>
                <p className="text-base md:text-lg font-bold text-red-400 tracking-tight tabular-nums leading-tight">−{exp}</p>
              </div>
            )}
          </div>
          <div
            className="p-2.5 rounded-xl shrink-0 transition-all duration-300 group-hover:scale-110 group-hover:rotate-3"
            style={{
              background: 'rgba(34,197,94,0.1)',
              border: '1px solid rgba(34,197,94,0.2)',
              boxShadow: '0 0 20px -8px rgba(34,197,94,0.25)',
            }}
          >
            <ArrowLeftRight className="w-5 h-5 text-emerald-400 transition-colors duration-300" />
          </div>
        </div>
        <span className="text-[11px] text-muted-foreground flex items-center gap-1 transition-all duration-200 mt-2.5 group-hover:gap-1.5 group-hover:text-emerald-400">
          Подробнее
          <ArrowUpRight className="w-3 h-3 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </span>
      </div>
    </div>
  )
}

// ── Карточка «Логи за сутки» (строки: ошибки / предупреждения / инфо) ──

function LogsStatsCard({
  error, warning, info, loading, index = 0, to,
}: {
  error: number
  warning: number
  info: number
  loading: boolean
  index?: number
  to: string
}) {
  const e = useCountUp(String(error), loading)
  const w = useCountUp(String(warning), loading)
  const i = useCountUp(String(info), loading)
  const navigate = useNavigate()
  const hasErr = error > 0
  const accent = hasErr ? '239,68,68' : '59,130,246'

  return (
    <div
      className="animate-fade-in-up group relative overflow-hidden rounded-xl transition-all duration-300 cursor-pointer hover:-translate-y-1 hover:shadow-lg"
      role="button"
      tabIndex={0}
      onClick={() => navigate(to)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(to) } }}
      style={{
        animationDelay: `${index * 0.06}s`,
        background: `linear-gradient(135deg, rgba(${accent}, 0.06) 0%, var(--glass-bg) 50%, rgba(${accent}, 0.03) 100%)`,
        backdropFilter: 'blur(var(--glass-blur, 24px))',
        WebkitBackdropFilter: 'blur(var(--glass-blur, 24px))',
        border: '1px solid var(--glass-border)',
      }}
    >
      {/* Top accent line */}
      <div
        className="absolute inset-x-0 top-0 h-[2px] opacity-40 group-hover:opacity-80 transition-opacity duration-300"
        style={{ background: `linear-gradient(90deg, transparent 5%, rgba(${accent}, 0.7) 50%, transparent 95%)` }}
      />
      {/* Hover glow */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-400 pointer-events-none rounded-xl"
        style={{ boxShadow: `inset 0 0 40px -15px rgba(${accent}, 0.12), 0 0 25px -8px rgba(${accent}, 0.2)` }}
      />
      <div className="px-4 py-3.5 relative">
        <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium flex items-center gap-1.5">
          <Terminal className="w-3 h-3" />
          Логи за сутки
        </p>
        {loading ? (
          <Skeleton className="h-14 w-full mt-2" />
        ) : (
          <div className="mt-2 space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Ошибки</span>
              <span className="font-semibold tabular-nums text-red-400">{e}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Предупреждения</span>
              <span className="font-semibold tabular-nums text-amber-400">{w}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Инфо</span>
              <span className="font-semibold tabular-nums text-blue-400">{i}</span>
            </div>
          </div>
        )}
        <span className="text-[11px] text-muted-foreground flex items-center gap-1 transition-all duration-200 mt-2.5 group-hover:gap-1.5 group-hover:text-red-400">
          Подробнее
          <ArrowUpRight className="w-3 h-3 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </span>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [finance, setFinance] = useState<{ income: number; expense: number; balance: number } | null>(null)
  const [logCounts, setLogCounts] = useState<{ error: number; warning: number; info: number } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const order = useOrderPreference('cms-dashboard-widget-order')
  const visibility = useWidgetVisibility('cms-dashboard-hidden-v1', [])
  const widgetSize = useWidgetSize('cms-dashboard-widget-size-v1', 'md')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [res, fin, errs, warns, infos] = await Promise.all([
        dashboardApi.getStats(),
        financeApi.getData({ page: 1, per_page: 1 }).catch(() => null),
        logsApi.list({ level: 'error', per_page: 1, days: 1 }).catch(() => null),
        logsApi.list({ level: 'warning', per_page: 1, days: 1 }).catch(() => null),
        logsApi.list({ level: 'info', per_page: 1, days: 1 }).catch(() => null),
      ])
      if (res.success) setStats(res.stats)
      else setError('Не удалось загрузить статистику')
      setFinance(fin?.summary ?? null)
      setLogCounts({
        error: (errs as { total?: number } | null)?.total ?? 0,
        warning: (warns as { total?: number } | null)?.total ?? 0,
        info: (infos as { total?: number } | null)?.total ?? 0,
      })
    } catch {
      setError('Ошибка подключения к серверу')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const orderedWidgetIds = order.applyOrder([...DASHBOARD_WIDGETS]) as WidgetId[]
  // рендерим только видимые; drag работает в пределах видимых
  const widgetIds = orderedWidgetIds.filter((w) => visibility.isVisible(w))

  const handleWidgetDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = orderedWidgetIds.indexOf(String(active.id) as WidgetId)
    const newIndex = orderedWidgetIds.indexOf(String(over.id) as WidgetId)
    if (oldIndex < 0 || newIndex < 0) return
    order.setCustomOrder(arrayMove(orderedWidgetIds, oldIndex, newIndex))
  }

  // ширина виджета на сетке из 6 колонок (как в каноне Remnawave)
  const spanClass = (id: WidgetId) => (RESIZABLE.has(id) ? SIZE_SPAN[widgetSize.getSize(id)] : 'lg:col-span-6')

  return (
    <div className="space-y-6">
      {/* ── Page header ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground tracking-tight">Дашборд</h1>
          <p className="text-muted-foreground mt-1 text-sm">Общая статистика сайта</p>
        </div>
      </div>

      {/* ── Error banner ────────────────────────────────────────── */}
      {error && (
        <Card className="border-red-500/30 bg-red-500/10 animate-fade-in-down">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-red-400 text-sm">{error}</p>
              <Button variant="secondary" size="sm" onClick={load}>Повторить</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Настройка дашборда: показать/скрыть виджеты + сброс ──── */}
      <div className="flex justify-end">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-8 px-2 text-xs text-dark-200 hover:text-white gap-1.5">
              <LayoutGrid className="w-3.5 h-3.5" />
              Настроить
              {(visibility.isCustomized || order.isCustomized || widgetSize.isCustomized) && (
                <span className="w-1.5 h-1.5 rounded-full bg-primary-400" />
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Виджеты</DropdownMenuLabel>
            {DASHBOARD_WIDGETS.map((w) => (
              <DropdownMenuCheckboxItem
                key={w}
                checked={visibility.isVisible(w)}
                onCheckedChange={() => visibility.toggle(w)}
                onSelect={(e) => e.preventDefault()}
              >
                {WIDGET_LABELS[w]}
              </DropdownMenuCheckboxItem>
            ))}
            {(visibility.isCustomized || order.isCustomized || widgetSize.isCustomized) && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => { order.reset(); visibility.reset(); widgetSize.reset() }}>
                  <RotateCcw className="w-3.5 h-3.5 mr-2" />
                  Сбросить настройки
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* ── Sortable widgets (сетка как в каноне: 6 колонок) ─────── */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleWidgetDragEnd}>
        <SortableContext items={widgetIds} strategy={rectSortingStrategy}>
          <div className="grid grid-cols-1 lg:grid-cols-6 gap-6 items-start">
            {widgetIds.map((wid) => {
              switch (wid) {
                case 'stats':
                  return (
                    <SortableSection key="stats" id="stats" className={spanClass('stats')}>
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                        <StatCard
                          title="Постов"
                          value={stats?.posts ?? 0}
                          icon={FileText}
                          color="cyan"
                          subtitle={stats
                            ? `Опубликовано: ${stats.posts_published} · Черновиков: ${stats.posts_draft}`
                            : undefined}
                          to="/posts"
                          loading={loading}
                          index={0}
                        />
                        <StatCard
                          title="Комментариев"
                          value={stats?.comments ?? 0}
                          icon={MessageCircle}
                          color="green"
                          subtitle={stats
                            ? `Всего: ${stats.comments_total} · Одобрено: ${stats.comments_approved}`
                            : undefined}
                          to="/posts"
                          loading={loading}
                          index={1}
                        />
                        <FinanceFlowCard
                          income={finance?.income ?? 0}
                          expense={finance?.expense ?? 0}
                          loading={loading}
                          index={2}
                          to="/finance"
                        />
                        <StatCard
                          title="Баланс"
                          value={money(finance?.balance ?? 0)}
                          icon={Wallet}
                          color="violet"
                          subtitle="Доход − Расход"
                          to="/finance"
                          loading={loading}
                          index={3}
                        />
                        <LogsStatsCard
                          error={logCounts?.error ?? 0}
                          warning={logCounts?.warning ?? 0}
                          info={logCounts?.info ?? 0}
                          loading={loading}
                          index={4}
                          to="/logs"
                        />
                      </div>
                    </SortableSection>
                  )

                case 'finance_chart':
                  return (
                    <SortableSection key="finance_chart" id="finance_chart" className={spanClass('finance_chart')}>
                      <FinanceChartWidget onResize={() => widgetSize.cycle('finance_chart')} />
                    </SortableSection>
                  )

                case 'logs':
                  return (
                    <SortableSection key="logs" id="logs" className={spanClass('logs')}>
                      <LogsRecentWidget onResize={() => widgetSize.cycle('logs')} />
                    </SortableSection>
                  )

                default:
                  return null
              }
            })}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  )
}