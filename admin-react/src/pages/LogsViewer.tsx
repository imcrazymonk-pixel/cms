import { useState, useEffect } from 'react'
import { logsApi, LogEntry } from '../api/logs'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import {
  Terminal, Info, AlertTriangle, AlertCircle,
  Search, X, Trash2, ChevronRight, RefreshCw,
  Settings, Globe, Package2, Server, Container, BarChart3, Wallet, Users,
  CreditCard, Shield, BarChart2,
} from 'lucide-react'

const CATEGORIES: Record<string, string> = {
  all: 'Все',
  system: 'Система',
  site: 'Сайт',
  modules: 'Модули',
  infrastructure: 'Инфраструктура',
  docker: 'Docker',
  loki: 'Loki',
  finance: 'Финансы',
  users: 'Пользователи',
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  all: <Terminal className="w-4 h-4" />,
  system: <Settings className="w-4 h-4" />,
  site: <Globe className="w-4 h-4" />,
  modules: <Package2 className="w-4 h-4" />,
  infrastructure: <Server className="w-4 h-4" />,
  docker: <Container className="w-4 h-4" />,
  loki: <BarChart3 className="w-4 h-4" />,
  finance: <Wallet className="w-4 h-4" />,
  users: <Users className="w-4 h-4" />,
}

const LEVELS: Record<string, string> = {
  '': 'Все уровни',
  info: 'Info',
  warning: 'Warning',
  error: 'Error',
}

const CHANNEL_LABELS: Record<string, string> = {
  system: 'Система',
  platega: 'Platega',
  yookassa: 'ЮKassa',
  auth: 'Авторизация',
  finance: 'Финансы',
  user: 'Пользователи',
}

const CHANNEL_ICONS: Record<string, React.ReactNode> = {
  system: <Settings className="w-3.5 h-3.5" />,
  platega: <CreditCard className="w-3.5 h-3.5" />,
  yookassa: <Wallet className="w-3.5 h-3.5" />,
  auth: <Shield className="w-3.5 h-3.5" />,
  finance: <BarChart2 className="w-3.5 h-3.5" />,
  user: <Users className="w-3.5 h-3.5" />,
}

const LEVEL_ICONS: Record<string, React.ReactNode> = {
  info: <Info className="w-4 h-4" />,
  warning: <AlertTriangle className="w-4 h-4" />,
  error: <AlertCircle className="w-4 h-4" />,
  '': <Terminal className="w-4 h-4" />,
}

const PER_PAGE_OPTIONS = [25, 50, 100, 200]

const EXTERNAL_CATEGORIES = ['docker', 'loki']

interface LogListResponse {
  success: boolean
  data: LogEntry[]
  total: number
  page: number
  per_page: number
}

function formatDate(raw: string): string {
  if (!raw) return '—'
  try {
    const d = new Date(raw)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch {
    return raw
  }
}

function levelBadgeColor(lvl: string): string {
  switch (lvl) {
    case 'error': return 'bg-red-500/20 text-red-400'
    case 'warning': return 'bg-amber-500/20 text-amber-400'
    case 'info': return 'bg-blue-500/20 text-blue-400'
    default: return 'bg-white/10 text-dark-200'
  }
}

export default function LogsViewer() {
  const [data, setData] = useState<LogListResponse | null>(null)
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [activeCategory, setActiveCategory] = useState('all')
  const [activeLevel, setActiveLevel] = useState('')
  const [searchQ, setSearchQ] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(50)

  // Expanded context rows
  const [expandedContexts, setExpandedContexts] = useState<Set<number>>(new Set())

  const loadLogs = async () => {
    setIsPending(true)
    setError(null)
    try {
      const params: Record<string, unknown> = { page, per_page: perPage }
      if (activeCategory !== 'all') params.category = activeCategory
      if (activeLevel !== '') params.level = activeLevel
      if (searchQ) params.q = searchQ

      const res = await logsApi.list(params)
      if ((res as Record<string, unknown>).success === true || Array.isArray(res.data)) {
        setData(res as LogListResponse)
      } else {
        setError('Не удалось загрузить логи')
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка подключения')
    } finally {
      setIsPending(false)
    }
  }

  useEffect(() => {
    loadLogs()
  }, [activeCategory, activeLevel, page, perPage])

  const clearLogs = async () => {
    const category = activeCategory !== 'all' ? activeCategory : ''
    const msg = category
      ? `Очистить все логи категории "${CATEGORIES[category] || category}"? Это действие необратимо.`
      : 'Очистить все логи? Это действие необратимо.'
    if (!confirm(msg)) return

    try {
      const res = await logsApi.clear(category ? { category } : {})
      if ((res as Record<string, unknown>).success) {
        loadLogs()
      }
    } catch { /* ignore */ }
  }

  const toggleContext = (id: number) => {
    const next = new Set(expandedContexts)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setExpandedContexts(next)
  }

  const hasContext = (entry: LogEntry): boolean => {
    const ctx = entry.context
    if (!ctx) return false
    if (ctx === 'null' || ctx === '[]' || ctx === '{}') return false
    return true
  }

  const formatContext = (ctx: string): string => {
    try {
      const parsed = JSON.parse(ctx)
      return JSON.stringify(parsed, null, 2)
    } catch {
      return ctx
    }
  }

  const isExternal = EXTERNAL_CATEGORIES.includes(activeCategory)

  const setCategory = (cat: string) => {
    setActiveCategory(cat)
    setPage(1)
    setExpandedContexts(new Set())
  }

  const setLevel = (lvl: string) => {
    setActiveLevel(lvl)
    setPage(1)
    setExpandedContexts(new Set())
  }

  const doSearch = () => {
    setPage(1)
    setExpandedContexts(new Set())
    loadLogs()
  }

  const doPerPage = (pp: number) => {
    setPerPage(pp)
    setPage(1)
  }

  // ── Render ──
  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <Terminal className="w-5 h-5 text-primary" />
        <h1 className="text-xl font-bold text-white tracking-tight">Логи</h1>
      </div>

      {/* Row 1: Category Tabs */}
      <div className="flex items-center gap-1 flex-wrap" role="tablist">
        {Object.entries(CATEGORIES).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setCategory(key)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              activeCategory === key
                ? 'bg-primary/20 text-primary shadow-sm'
                : 'text-dark-300 hover:text-dark-100 hover:bg-white/5'
            }`}
            role="tab"
          >
            <span className="flex items-center gap-1.5">
              {CATEGORY_ICONS[key]}
              {label}
            </span>
          </button>
        ))}
      </div>

      {/* Row 2: Level Tabs */}
      <div className="flex items-center gap-1 flex-wrap" role="tablist">
        {Object.entries(LEVELS).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setLevel(key)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              (key === '' && activeLevel === '') || key === activeLevel
                ? 'bg-primary/20 text-primary shadow-sm'
                : 'text-dark-300 hover:text-dark-100 hover:bg-white/5'
            }`}
            role="tab"
          >
            <span className="flex items-center gap-1.5">
              {key ? (LEVEL_ICONS[key] || LEVEL_ICONS['']) : LEVEL_ICONS['']}
              {label}
            </span>
          </button>
        ))}
      </div>

      {/* Actions: Search + Clear */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <div className="flex items-center gap-2">
            <Input
              placeholder="Текст сообщения…"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') doSearch() }}
              className="flex-1"
            />
            <Button variant="secondary" size="sm" onClick={doSearch}>
              <Search className="w-4 h-4" /> Фильтр
            </Button>
            <Button variant="ghost" size="sm" onClick={() => { setSearchQ(''); setPage(1); loadLogs() }}>
              <X className="w-4 h-4" /> Сброс
            </Button>
          </div>
        </div>

        {!isExternal && (
          <Button variant="destructive" size="sm" onClick={clearLogs}>
            <Trash2 className="w-4 h-4" /> Очистить{activeCategory !== 'all' ? ` ${CATEGORIES[activeCategory]}` : ' все'}
          </Button>
        )}

        <Button variant="ghost" size="sm" onClick={loadLogs}>
          <RefreshCw className="w-4 h-4" /> Обновить
        </Button>
      </div>

      {/* Loading */}
      {isPending && (
        <div className="space-y-2">
          {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10 rounded-lg" />)}
        </div>
      )}

      {/* Error */}
      {error && <QueryError message={error} />}

      {/* External source not configured */}
      {isExternal && data && data.data && data.data.length === 0 && (
        <Card className="rounded-xl">
          <CardContent className="p-10 text-center">
            <BarChart3 className="w-10 h-10 text-dark-300 mx-auto mb-3" />
            <p className="text-base font-semibold mb-2">Внешний источник логов не настроен</p>
            <p className="text-sm text-dark-300">
              Настройте параметры в <a href="/admin/settings?tab=logs" className="text-primary underline">Настройках</a>
            </p>
          </CardContent>
        </Card>
      )}

      {/* Logs Table */}
      {!isPending && !error && data && (
        <>
          {data.data.length === 0 ? (
            <Card className="rounded-xl">
              <CardContent className="p-10 text-center">
                <Terminal className="w-10 h-10 text-dark-300 mx-auto mb-3" />
                <p className="text-base font-semibold mb-2">Логов пока нет</p>
                <p className="text-sm text-dark-300">Логи появляются здесь по мере работы системы</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="rounded-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                  <colgroup>
                    <col style={{ width: '150px' }} />
                    <col style={{ width: '80px' }} />
                    <col style={{ width: '105px' }} />
                    <col style={{ width: '120px' }} />
                    <col />
                    <col style={{ width: '40px' }} />
                  </colgroup>
                  <thead>
                    <tr className="border-b border-white/5 text-dark-300 text-xs uppercase tracking-wider">
                      <th className="text-left py-2 px-2.5">Дата</th>
                      <th className="text-left py-2 px-2.5">Уровень</th>
                      <th className="text-left py-2 px-2.5">Категория</th>
                      <th className="text-left py-2 px-2.5">Канал</th>
                      <th className="text-left py-2 px-2.5">Сообщение</th>
                      <th className="text-center py-2 px-2.5" title="Контекст">Ctx</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.data.map((entry: LogEntry) => {
                      const cat = entry.category || 'system'
                      const catLabel = CATEGORIES[cat] || cat
                      const ch = entry.channel || ''
                      const chLabel = CHANNEL_LABELS[ch] || ch
                      const hasCtx = hasContext(entry)
                      const ctxExpanded = expandedContexts.has(entry.id)

                      return (
                        <tr key={entry.id} className="border-b border-white/5 hover:bg-white/5">
                          <td className="py-1.5 px-2.5 text-dark-300 text-xs whitespace-nowrap" title={entry.created_at}>
                            {formatDate(entry.created_at)}
                          </td>
                          <td className="py-1.5 px-2.5">
                            <Badge className={levelBadgeColor(entry.level)}>
                              {entry.level}
                            </Badge>
                          </td>
                          <td className="py-1.5 px-2.5">
                            <span className="flex items-center gap-1 text-xs text-dark-200">
                              {CATEGORY_ICONS[cat] || <Terminal className="w-3.5 h-3.5" />}
                              {catLabel}
                            </span>
                          </td>
                          <td className="py-1.5 px-2.5">
                            <span className="flex items-center gap-1 text-xs text-dark-300">
                              {CHANNEL_ICONS[ch]}
                              {chLabel}
                            </span>
                          </td>
                          <td className="py-1.5 px-2.5 max-w-[500px]">
                            <code className="text-xs text-dark-100">{entry.message}</code>
                            {hasCtx && (
                              <button
                                onClick={() => toggleContext(entry.id)}
                                className="ml-1 text-dark-400 hover:text-dark-200 transition-colors"
                                title="Показать контекст"
                              >
                                <ChevronRight className={`w-3 h-3 transition-transform ${ctxExpanded ? 'rotate-90' : ''}`} />
                              </button>
                            )}
                            {hasCtx && ctxExpanded && (
                              <pre
                                className="mt-1.5 p-2 rounded-lg text-xs overflow-x-auto max-w-[600px] whitespace-pre-wrap"
                                style={{ background: 'var(--surface-card, rgba(24,30,40,0.8))' }}
                              >
                                {formatContext(entry.context!)}
                              </pre>
                            )}
                          </td>
                          <td className="py-1.5 px-2.5 text-center">
                            {hasCtx && (
                              <Badge className="bg-white/10 text-dark-300" title="Есть контекст">+</Badge>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Pagination (only for non-external) */}
          {!isExternal && data.total > 0 && (
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <span className="text-sm text-dark-300">
                Всего: <strong className="text-white">{data.total}</strong>
              </span>

              <div className="flex items-center gap-1">
                {(() => {
                  const pages = Math.ceil(data.total / data.per_page)
                  const start = Math.max(1, page - 2)
                  const end = Math.min(pages, page + 2)
                  const links: React.ReactNode[] = []

                  if (page > 1) {
                    links.push(
                      <Button key="prev" variant="ghost" size="icon" onClick={() => { setPage(page - 1); setExpandedContexts(new Set()) }}
                        className="h-7 w-7"><span className="text-sm">‹</span></Button>
                    )
                  }

                  for (let i = start; i <= end; i++) {
                    links.push(
                      <Button
                        key={i}
                        variant={i === page ? 'default' : 'ghost'}
                        size="icon"
                        onClick={() => { setPage(i); setExpandedContexts(new Set()) }}
                        className={`h-7 w-7 text-xs ${i === page ? '' : ''}`}
                      >
                        {String(i)}
                      </Button>
                    )
                  }

                  if (page < pages) {
                    links.push(
                      <Button key="next" variant="ghost" size="icon" onClick={() => { setPage(page + 1); setExpandedContexts(new Set()) }}
                        className="h-7 w-7"><span className="text-sm">›</span></Button>
                    )
                  }

                  return links
                })()}
              </div>

              <div className="flex items-center gap-2 text-sm text-dark-300">
                <label>Показывать:</label>
                <select
                  onChange={(e) => doPerPage(parseInt(e.target.value))}
                  className="text-xs px-2 py-1 rounded-lg"
                  style={{
                    background: 'var(--surface-card, rgba(24,30,40,0.8))',
                    border: '1px solid var(--glass-border, rgba(255,255,255,0.08))',
                    color: 'var(--text-primary)',
                  }}
                >
                  {PER_PAGE_OPTIONS.map(pp => (
                    <option key={pp} value={pp} selected={perPage === pp}>{pp}</option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}