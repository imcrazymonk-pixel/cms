import { useEffect, useState, useCallback } from 'react'
import { dashboardApi, DashboardStats } from '../api/dashboard'
import {
  RotateCcw, LayoutGrid, FileText, MessageCircle, Users, Grid3x3,
} from 'lucide-react'
import { useWidgetVisibility } from '@/lib/useWidgetVisibility'
import { useOrderPreference } from '@/lib/useOrderPreference'
import { SortableSection } from '@/components/SortableSection'
import { FinanceWidget, LogsWidget } from '@/components/dashboard/ExtraWidgets'
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
  verticalListSortingStrategy,
  arrayMove,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

const DASHBOARD_WIDGETS = ['stats', 'activity', 'finance', 'logs'] as const

type WidgetId = (typeof DASHBOARD_WIDGETS)[number]

const WIDGET_LABELS: Record<WidgetId, string> = {
  stats: 'Статистика',
  activity: 'Активность',
  finance: 'Финансы',
  logs: 'Логи',
}

// ── StatCard colors (Remnawave palette) ──────────────────────────

const STAT_COLORS = {
  cyan:   { rgb: '6, 182, 212',   text: 'text-cyan-400' },
  green:  { rgb: '34, 197, 94',   text: 'text-emerald-400' },
  yellow: { rgb: '234, 179, 8',   text: 'text-amber-400' },
  violet: { rgb: '139, 92, 246',  text: 'text-violet-400' },
} as const

type StatColor = keyof typeof STAT_COLORS

interface StatCardDef {
  label: string
  value: number
  icon: React.ElementType
  color: StatColor
}

// ── Remnawave-style StatCard ─────────────────────────────────────

function StatCard({
  title, value, icon: Icon, color, loading, index = 0,
}: {
  title: string
  value: number
  icon: React.ElementType
  color: StatColor
  loading: boolean
  index?: number
}) {
  const cfg = STAT_COLORS[color]

  return (
    <div
      className="animate-fade-in-up group relative overflow-hidden rounded-xl transition-all duration-300"
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
                {value}
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
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const order = useOrderPreference('cms-dashboard-widget-order')
  const visibility = useWidgetVisibility('cms-dashboard-hidden-v1', [])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await dashboardApi.getStats()
      if (res.success) setStats(res.stats)
      else setError('Не удалось загрузить статистику')
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

  const statCards: StatCardDef[] = [
    { label: 'Постов', value: stats?.posts ?? 0, icon: FileText, color: 'cyan' },
    { label: 'Комментариев', value: stats?.comments ?? 0, icon: MessageCircle, color: 'green' },
    { label: 'Пользователей', value: stats?.users ?? 0, icon: Users, color: 'violet' },
    { label: 'Категорий', value: stats?.categories ?? 0, icon: Grid3x3, color: 'yellow' },
  ]

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
              {(visibility.isCustomized || order.isCustomized) && (
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
            {(visibility.isCustomized || order.isCustomized) && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => { order.reset(); visibility.reset() }}>
                  <RotateCcw className="w-3.5 h-3.5 mr-2" />
                  Сбросить настройки
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* ── Sortable widgets ────────────────────────────────────── */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleWidgetDragEnd}>
        <SortableContext items={widgetIds} strategy={verticalListSortingStrategy}>
          <div className="space-y-6">
            {widgetIds.map((wid) => {
              switch (wid) {
                case 'stats':
                  return (
                    <SortableSection key="stats" id="stats">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {statCards.map((card, i) => (
                          <StatCard
                            key={card.label}
                            title={card.label}
                            value={card.value}
                            icon={card.icon}
                            color={card.color}
                            loading={loading}
                            index={i}
                          />
                        ))}
                      </div>
                    </SortableSection>
                  )

                case 'activity':
                  return (
                    <SortableSection key="activity" id="activity">
                      <Card className="animate-fade-in-up">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base md:text-lg">Последние действия</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-muted-foreground">
                            Здесь будет отображаться активность на сайте.
                          </p>
                        </CardContent>
                      </Card>
                    </SortableSection>
                  )

                case 'finance':
                  return (
                    <SortableSection key="finance" id="finance">
                      <FinanceWidget />
                    </SortableSection>
                  )

                case 'logs':
                  return (
                    <SortableSection key="logs" id="logs">
                      <LogsWidget />
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