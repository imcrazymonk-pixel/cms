import { useEffect, useState, useCallback } from 'react'
import { dashboardApi, DashboardStats } from '../api/dashboard'
import { Loader, RotateCcw, Eye, EyeOff, Settings2, FileText, MessageCircle, Users, Grid3x3 } from 'lucide-react'
import { useDashboardWidgetsStore } from '../store/useDashboardWidgetsStore'
import { useOrderPreference } from '@/lib/useOrderPreference'
import { SortableSection } from '@/components/SortableSection'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

const DASHBOARD_WIDGETS = ['stats', 'activity'] as const

type WidgetId = (typeof DASHBOARD_WIDGETS)[number]

// ── Remnawave-style StatCard colors ──────────────────────────────

const STAT_COLORS = {
  teal:   { rgb: '6, 182, 212',  text: 'text-teal-400' },
  amber:  { rgb: '234, 179, 8',  text: 'text-amber-400' },
  blue:   { rgb: '59, 130, 246', text: 'text-blue-400' },
  purple: { rgb: '139, 92, 246', text: 'text-purple-400' },
} as const

type StatColor = keyof typeof STAT_COLORS

interface StatCardDef {
  label: string
  value: number
  icon: React.ElementType
  color: StatColor
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const { widgets, toggleWidget, resetToDefaults } = useDashboardWidgetsStore()
  const order = useOrderPreference('cms-dashboard-widget-order')

  useEffect(() => {
    dashboardApi.getStats()
      .then((res) => {
        if (res.success) setStats(res.stats)
        else setError('Не удалось загрузить статистику')
      })
      .catch(() => setError('Ошибка подключения к серверу'))
      .finally(() => setLoading(false))
  }, [])

  // Filter enabled + apply saved order
  const enabledWidgets = [...DASHBOARD_WIDGETS].filter((id) =>
    widgets.find((w) => w.id === id)?.enabled ?? true
  )
  const widgetIds: WidgetId[] = order.applyOrder(enabledWidgets)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event
      if (!over || active.id === over.id) return
      const oldIndex = widgetIds.indexOf(active.id as WidgetId)
      const newIndex = widgetIds.indexOf(over.id as WidgetId)
      if (oldIndex === -1 || newIndex === -1) return
      order.setOrder(arrayMove(widgetIds, oldIndex, newIndex))
    },
    [widgetIds, order]
  )

  const statCards: StatCardDef[] = [
    { label: 'Постов', value: stats?.posts ?? 0, icon: FileText, color: 'teal' },
    { label: 'Комментариев (ожидают)', value: stats?.comments ?? 0, icon: MessageCircle, color: 'amber' },
    { label: 'Пользователей', value: stats?.users ?? 0, icon: Users, color: 'blue' },
    { label: 'Категорий', value: stats?.categories ?? 0, icon: Grid3x3, color: 'purple' },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-bold text-white tracking-tight">
            Дашборд
          </h1>
          <p className="text-sm text-dark-200 mt-1">
            Общая статистика сайта
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Dashboard Widget Settings */}
          <Popover>
            <Tooltip>
              <TooltipTrigger asChild>
                <PopoverTrigger asChild>
                  <Button variant="ghost" size="icon" className="text-dark-300 hover:text-white">
                    <Settings2 className="w-4 h-4" />
                  </Button>
                </PopoverTrigger>
              </TooltipTrigger>
              <TooltipContent>Настройка виджетов</TooltipContent>
            </Tooltip>
            <PopoverContent align="end" className="w-72 p-0">
              <div className="px-4 py-3 border-b border-[var(--glass-border)]">
                <h4 className="text-sm font-semibold text-white">Виджеты дашборда</h4>
              </div>
              <ScrollArea className="max-h-[40vh]">
                <div className="p-3 space-y-1">
                  {widgets.map((w) => (
                    <div
                      key={w.id}
                      className="flex items-center justify-between py-2 px-2 rounded-lg hover:bg-[var(--glass-bg)] transition-colors"
                    >
                      <span className="text-xs text-dark-100">{w.defaultLabel}</span>
                      <button
                        onClick={() => toggleWidget(w.id)}
                        className={cn(
                          'flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-md transition-all font-medium',
                          w.enabled
                            ? 'bg-primary/15 text-primary-400'
                            : 'bg-dark-600/30 text-dark-300'
                        )}
                      >
                        {w.enabled ? (
                          <><Eye className="w-3 h-3" /> Показано</>
                        ) : (
                          <><EyeOff className="w-3 h-3" /> Скрыто</>
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              </ScrollArea>
              <div className="px-3 py-2 border-t border-[var(--glass-border)]">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full text-xs text-dark-300 hover:text-white"
                  onClick={resetToDefaults}
                >
                  <RotateCcw className="w-3 h-3 mr-1" />
                  Сбросить
                </Button>
              </div>
            </PopoverContent>
          </Popover>

          {/* Reset widget order */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="text-dark-300 hover:text-white"
                onClick={() => order.setOrder([])}
              >
                <RotateCcw className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Сбросить порядок виджетов</TooltipContent>
          </Tooltip>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          className="mb-5 p-3.5 rounded-xl border animate-fade-in"
          style={{
            background:
              'linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(239, 68, 68, 0.04) 100%)',
            borderColor: 'rgba(239, 68, 68, 0.2)',
          }}
        >
          <p className="text-sm text-red-400 leading-relaxed">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader className="h-8 w-8 animate-spin text-teal-500" />
        </div>
      )}

      {/* DnD Dashboard Widgets */}
      {!loading && (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={widgetIds} strategy={verticalListSortingStrategy}>
            <div className="space-y-6">
              {widgetIds.map((id) => (
                <SortableSection key={id} id={id}>
                  {id === 'stats' && (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {statCards.map((card, i) => {
                          const cfg = STAT_COLORS[card.color]
                          return (
                            <div
                              key={card.label}
                              className="animate-fade-in-up group relative overflow-hidden rounded-xl transition-all duration-300"
                              style={{
                                animationDelay: `${i * 0.06}s`,
                                background: `linear-gradient(135deg, rgba(${cfg.rgb}, 0.06) 0%, var(--glass-bg) 50%, rgba(${cfg.rgb}, 0.03) 100%)`,
                                backdropFilter: 'blur(20px)',
                                WebkitBackdropFilter: 'blur(20px)',
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
                                    <p className="text-[11px] uppercase tracking-wider text-dark-300 font-medium">{card.label}</p>
                                    <p className="text-xl md:text-2xl font-bold text-white mt-1 tracking-tight">
                                      {stats ? card.value : '-'}
                                    </p>
                                  </div>
                                  <div
                                    className="p-2.5 rounded-xl shrink-0 transition-all duration-300 group-hover:scale-110 group-hover:rotate-3"
                                    style={{
                                      background: `rgba(${cfg.rgb}, 0.1)`,
                                      border: `1px solid rgba(${cfg.rgb}, 0.2)`,
                                      boxShadow: `0 0 20px -8px rgba(${cfg.rgb}, 0.25)`,
                                    }}
                                  >
                                    <card.icon className={cn("w-5 h-5 transition-colors duration-300", cfg.text)} />
                                  </div>
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {id === 'activity' && (
                    <div className="pt-4">
                      <h3 className="text-sm font-semibold text-white mb-3">Последние действия</h3>
                      <p className="text-sm text-dark-300">
                        Здесь будет отображаться активность на сайте.
                      </p>
                    </div>
                  )}
                </SortableSection>
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}
    </div>
  )
}