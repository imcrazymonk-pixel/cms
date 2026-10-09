import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Plus, Trash2, Pencil, RefreshCw, BarChart3, History, Download, Settings as SettingsIcon,
} from 'lucide-react'
import {
  Bar, Line, ComposedChart, LineChart, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { financeApi, Transaction, ChartPoint } from '../api/finance'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { EmptyState } from '@/components/EmptyState'
import { QueryError } from '@/components/QueryError'
import PaymentSync from '@/components/PaymentSync'

const PAGE_SIZE = 25
const PAGE_SIZES = [25, 50, 100, 200]
const ALL = '__all__'

const PERIODS: { value: 'daily' | 'weekly' | 'monthly' | 'yearly'; label: string }[] = [
  { value: 'daily', label: 'Дни' },
  { value: 'weekly', label: 'Недели' },
  { value: 'monthly', label: 'Месяцы' },
  { value: 'yearly', label: 'Годы' },
]

type BulkAction = 'type' | 'category' | 'participant' | 'description' | null

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export default function Finance() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Tab state
  const [activeTab, setActiveTab] = useState('table')

  // Filters
  const [filterMonth, setFilterMonth] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterParticipant, setFilterParticipant] = useState('')
  const [filterQ, setFilterQ] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(PAGE_SIZE)
  const [sort, setSort] = useState('date')
  const [dir, setDir] = useState('desc')

  // Chart state
  const [chartPeriod, setChartPeriod] = useState<'daily' | 'weekly' | 'monthly' | 'yearly'>('monthly')
  const [chartType, setChartType] = useState<'bar' | 'line'>('bar')
  const [showAnomalies, setShowAnomalies] = useState(false)

  // Selection
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // CRUD state
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingTxn, setEditingTxn] = useState<Transaction | null>(null)
  const [formData, setFormData] = useState({ date: '', type: 'income', category: '', participant: '', amount: 0, description: '' })
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false)
  const [bulkAction, setBulkAction] = useState<BulkAction>(null)
  const [bulkValue, setBulkValue] = useState('')
  const [exporting, setExporting] = useState(false)

  // Load data
  const { data, isPending, error } = useQuery({
    queryKey: ['finance-data', filterMonth, filterType, filterCategory, filterParticipant, filterQ, page, perPage, sort, dir],
    queryFn: async () => {
      const params: Record<string, unknown> = { page, per_page: perPage, sort, dir }
      if (filterMonth) params.month = filterMonth
      if (filterType) params.type = filterType
      if (filterCategory) params.category = filterCategory
      if (filterParticipant) params.participant = filterParticipant
      if (filterQ) params.q = filterQ
      return financeApi.getData(params)
    },
    staleTime: 5_000,
    refetchOnMount: 'always',
    retry: 2,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['finance-data'] })

  // ── CRUD Mutations ──
  const addMutation = useMutation({
    mutationFn: (d: typeof formData) => financeApi.add(d),
    onSuccess: () => { invalidate(); setEditDialogOpen(false); toast.success('Добавлено') },
    onError: (e) => toast.error(String(e)),
  })

  const editMutation = useMutation({
    mutationFn: (d: typeof formData & { id: number }) => financeApi.edit(d),
    onSuccess: () => { invalidate(); setEditDialogOpen(false); toast.success('Сохранено') },
    onError: (e) => toast.error(String(e)),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => financeApi.delete(id),
    onSuccess: () => { invalidate(); toast.success('Удалено') },
    onError: (e) => toast.error(String(e)),
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: number[]) => financeApi.deleteBulk(ids),
    onSuccess: () => { invalidate(); toast.success('Записи удалены'); setSelectedIds(new Set()) },
    onError: (e) => toast.error(String(e)),
  })

  const bulkEditMutation = useMutation({
    mutationFn: (p: { action: Exclude<BulkAction, null>; ids: number[]; value: string }) => {
      if (p.action === 'type') return financeApi.bulkType(p.ids, p.value)
      if (p.action === 'category') return financeApi.bulkCategory(p.ids, p.value)
      if (p.action === 'participant') return financeApi.bulkParticipant(p.ids, p.value)
      return financeApi.bulkDescription(p.ids, p.value)
    },
    onSuccess: () => { invalidate(); setBulkAction(null); setBulkValue(''); toast.success('Обновлено') },
    onError: (e) => toast.error(String(e)),
  })

  // ── Helpers ──
  const openAddDialog = () => {
    setEditingTxn(null)
    setFormData({ date: new Date().toISOString().slice(0, 10), type: 'income', category: '', participant: '', amount: 0, description: '' })
    setEditDialogOpen(true)
  }

  const openEditDialog = (txn: Transaction) => {
    setEditingTxn(txn)
    setFormData({ date: txn.date, type: txn.type, category: txn.category, participant: txn.participant, amount: txn.amount, description: txn.description })
    setEditDialogOpen(true)
  }

  const saveForm = () => {
    if (editingTxn) editMutation.mutate({ ...formData, id: editingTxn.id })
    else addMutation.mutate(formData)
  }

  const toggleSort = (field: string) => {
    if (sort === field) setDir(dir === 'asc' ? 'desc' : 'asc')
    else { setSort(field); setDir('desc') }
  }

  const resetFilters = () => {
    setFilterMonth(''); setFilterType(''); setFilterCategory(''); setFilterParticipant(''); setFilterQ(''); setPage(1)
  }

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '—'
    const cur = data?.settings?.currency != null ? String(data.settings.currency) : '₽'
    const dec = typeof data?.settings?.decimals === 'number' ? (data.settings.decimals as number) : 2
    return `${amount.toFixed(dec)} ${cur}`
  }

  const anomalySet = useMemo(() => new Set<number>(data?.anomalies ?? []), [data])

  // KPI averages (same wording as PHP admin/js/finance/finance.js)
  const PERIOD_LABELS: Record<string, string> = { day: 'в день', week: 'в неделю', month: 'в месяц', year: 'в год' }
  const avgPeriod = (data?.settings?.avg_period != null ? String(data.settings.avg_period) : 'day')
  const incomeAvg = data?.averages?.avg_income?.[avgPeriod as 'day'] ?? 0
  const expenseAvg = data?.averages?.avg_expense?.[avgPeriod as 'day'] ?? 0
  const allSelected = !!data && data.transactions.length > 0 && data.transactions.every(t => selectedIds.has(t.id))

  const toggleAll = () => {
    if (!data) return
    if (allSelected) setSelectedIds(new Set())
    else setSelectedIds(new Set(data.transactions.map(t => t.id)))
  }

  const toggleOne = (id: number) => {
    const next = new Set(selectedIds)
    next.has(id) ? next.delete(id) : next.add(id)
    setSelectedIds(next)
  }

  const chartRows = useMemo<{ name: string; income: number; expense: number; balance: number; anomaly: boolean }[]>(() => {
    const src: ChartPoint[] = (data?.chart?.[chartPeriod] ?? []) as ChartPoint[]
    return src.map((row) => ({
      name: row.label ?? row.key,
      income: row.income ?? 0,
      expense: row.expense ?? 0,
      balance: row.balance ?? 0,
      anomaly: false,
    }))
  }, [data, chartPeriod])

  const doExport = async () => {
    setExporting(true)
    try {
      const params: Record<string, unknown> = {}
      if (filterMonth) params.month = filterMonth
      if (filterType) params.type = filterType
      if (filterCategory) params.category = filterCategory
      if (filterParticipant) params.participant = filterParticipant
      if (filterQ) params.q = filterQ
      const blob = await financeApi.exportCsv(params)
      downloadBlob(blob instanceof Blob ? blob : new Blob([blob]), `finance_${new Date().toISOString().slice(0, 10)}.csv`)
    } catch {
      toast.error('Не удалось выгрузить CSV')
    } finally {
      setExporting(false)
    }
  }

  const doExportSelected = async () => {
    try {
      const blob = await financeApi.exportSelected(Array.from(selectedIds))
      downloadBlob(blob instanceof Blob ? blob : new Blob([blob]), `finance_selected_${Date.now()}.csv`)
    } catch {
      toast.error('Не удалось выгрузить CSV')
    }
  }

  // ── Render ──
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-display font-bold text-white tracking-tight">Финансы</h1>
          <p className="text-sm text-dark-200 mt-1">Учёт доходов и расходов</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={invalidate}>
            <RefreshCw className="w-4 h-4" /> Обновить
          </Button>
          <Button variant="ghost" size="sm" onClick={doExport} disabled={exporting}>
            <Download className="w-4 h-4" /> Экспорт
          </Button>
          <Button variant="ghost" size="sm" onClick={() => navigate('/settings?tab=finance')}>
            <SettingsIcon className="w-4 h-4" /> Настройки
          </Button>
          <Button variant="default" size="sm" onClick={openAddDialog}>
            <Plus className="w-4 h-4" /> Добавить
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      {data && (
        <div className="grid grid-cols-4 gap-4">
          <Card className="rounded-xl"><CardContent className="p-5">
            <p className="text-xs text-dark-300 uppercase tracking-wider">Доходы</p>
            <p className="text-lg font-bold text-green-400">{formatCurrency(data.summary.income)}</p>
            <p className="text-xs text-dark-400 mt-1">Средний {formatCurrency(incomeAvg)} {PERIOD_LABELS[avgPeriod] || ''}</p>
          </CardContent></Card>
          <Card className="rounded-xl"><CardContent className="p-5">
            <p className="text-xs text-dark-300 uppercase tracking-wider">Расходы</p>
            <p className="text-lg font-bold text-red-400">{formatCurrency(data.summary.expense)}</p>
            <p className="text-xs text-dark-400 mt-1">Средний {formatCurrency(expenseAvg)} {PERIOD_LABELS[avgPeriod] || ''}</p>
          </CardContent></Card>
          <Card className="rounded-xl"><CardContent className="p-5">
            <p className="text-xs text-dark-300 uppercase tracking-wider">Баланс</p>
            <p className={`text-lg font-bold ${data.summary.balance >= 0 ? 'text-teal-400' : 'text-red-400'}`}>{formatCurrency(data.summary.balance)}</p>
            <p className="text-xs text-dark-400 mt-1">Доходы − расходы</p>
          </CardContent></Card>
          <Card className="rounded-xl"><CardContent className="p-5">
            <p className="text-xs text-dark-300 uppercase tracking-wider">Операций</p>
            <p className="text-lg font-bold text-white">{data.summary.count}</p>
            <p className="text-xs text-dark-400 mt-1">Всего операций</p>
          </CardContent></Card>
        </div>
      )}

      {isPending && (
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
      )}

      {error && <QueryError message={error instanceof Error ? error.message : String(error)} />}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="table"><History className="w-4 h-4" /> Таблица</TabsTrigger>
          <TabsTrigger value="charts"><BarChart3 className="w-4 h-4" /> Графики</TabsTrigger>
          <TabsTrigger value="sync"><RefreshCw className="w-4 h-4" /> Синхронизация</TabsTrigger>
        </TabsList>

        {/* ── Table Tab ── */}
        <TabsContent value="table" className="space-y-4">
          {/* Filters */}
          {data && (
            <div className="flex items-center gap-3 flex-wrap">
              <Select value={filterMonth || ALL} onValueChange={(v) => { setFilterMonth(v === ALL ? '' : v); setPage(1) }}>
                <SelectTrigger className="w-36"><SelectValue placeholder="Месяц" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>Все месяцы</SelectItem>
                  {data.all_months.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                </SelectContent>
              </Select>

              <Select value={filterType || ALL} onValueChange={(v) => { setFilterType(v === ALL ? '' : v); setPage(1) }}>
                <SelectTrigger className="w-32"><SelectValue placeholder="Тип" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>Все типы</SelectItem>
                  <SelectItem value="income">Доход</SelectItem>
                  <SelectItem value="expense">Расход</SelectItem>
                </SelectContent>
              </Select>

              <Select value={filterCategory || ALL} onValueChange={(v) => { setFilterCategory(v === ALL ? '' : v); setPage(1) }}>
                <SelectTrigger className="w-40"><SelectValue placeholder="Категория" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>Все категории</SelectItem>
                  {data.all_categories.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>

              <Select value={filterParticipant || ALL} onValueChange={(v) => { setFilterParticipant(v === ALL ? '' : v); setPage(1) }}>
                <SelectTrigger className="w-44"><SelectValue placeholder="Участник" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>Все участники</SelectItem>
                  {data.all_participants.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                </SelectContent>
              </Select>

              <div className="flex items-center gap-2">
                <span className="text-xs text-dark-300">На странице:</span>
                <Select value={String(perPage)} onValueChange={(v) => { setPerPage(Number(v)); setPage(1) }}>
                  <SelectTrigger className="w-20"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {PAGE_SIZES.map(s => <SelectItem key={s} value={String(s)}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>

              <Input
                placeholder="Поиск по описанию…"
                value={filterQ}
                onChange={(e) => setFilterQ(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') setPage(1) }}
                className="w-56"
              />

              <Button variant="ghost" size="sm" onClick={resetFilters}>Сброс</Button>

              {showAnomalies && (
                <Badge className="bg-amber-500/20 text-amber-400">
                  Аномалий на странице: {data.transactions.filter(t => anomalySet.has(t.id)).length}
                </Badge>
              )}
            </div>
          )}

          {/* Bulk actions bar */}
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2 p-3 rounded-xl border border-[var(--glass-border)] bg-[var(--glass-bg)]">
              <span className="text-sm text-dark-200 mr-2">Выбрано: <strong className="text-white">{selectedIds.size}</strong></span>
              <Button variant="ghost" size="sm" onClick={() => { setBulkAction('type'); setBulkValue('') }}>Тип</Button>
              <Button variant="ghost" size="sm" onClick={() => { setBulkAction('category'); setBulkValue('') }}>Категория</Button>
              <Button variant="ghost" size="sm" onClick={() => { setBulkAction('participant'); setBulkValue('') }}>Участник</Button>
              <Button variant="ghost" size="sm" onClick={() => { setBulkAction('description'); setBulkValue('') }}>Описание</Button>
              <Button variant="ghost" size="sm" onClick={doExportSelected}><Download className="w-4 h-4" /> Экспорт</Button>
              <Button variant="ghost" size="sm" className="text-red-400" onClick={() => setBulkDeleteConfirm(true)}>
                <Trash2 className="w-4 h-4" /> Удалить
              </Button>
            </div>
          )}

          {/* Table */}
          {!isPending && !error && data && (
            data.transactions.length === 0 ? (
              <EmptyState title="Нет записей" description="Нет транзакций по заданным фильтрам" />
            ) : (
              <Card className="rounded-xl">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8">
                        <input type="checkbox" checked={allSelected} onChange={toggleAll} />
                      </TableHead>
                      <TableHead className="cursor-pointer" onClick={() => toggleSort('date')}>Дата {sort === 'date' ? (dir === 'asc' ? '▲' : '▼') : ''}</TableHead>
                      <TableHead>Тип</TableHead>
                      <TableHead className="cursor-pointer" onClick={() => toggleSort('category')}>Категория {sort === 'category' ? (dir === 'asc' ? '▲' : '▼') : ''}</TableHead>
                      <TableHead className="cursor-pointer" onClick={() => toggleSort('participant')}>Участник {sort === 'participant' ? (dir === 'asc' ? '▲' : '▼') : ''}</TableHead>
                      <TableHead>Описание</TableHead>
                      <TableHead className="cursor-pointer text-right" onClick={() => toggleSort('amount')}>Сумма {sort === 'amount' ? (dir === 'asc' ? '▲' : '▼') : ''}</TableHead>
                      <TableHead className="w-24">Действия</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.transactions.map(txn => {
                      const isAnomaly = showAnomalies && anomalySet.has(txn.id)
                      return (
                        <TableRow key={txn.id} className={isAnomaly ? 'bg-amber-500/10' : undefined}>
                          <TableCell>
                            <input type="checkbox" checked={selectedIds.has(txn.id)} onChange={() => toggleOne(txn.id)} />
                          </TableCell>
                          <TableCell className="text-sm text-dark-200 whitespace-nowrap">
                            {isAnomaly && <span title="Аномалия" className="text-amber-400 mr-1">●</span>}
                            {txn.date_display}
                          </TableCell>
                          <TableCell>
                            <Badge className={txn.type === 'income' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
                              {txn.type === 'income' ? 'Доход' : 'Расход'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-dark-200">{txn.category}</TableCell>
                          <TableCell className="text-sm text-dark-200">{txn.participant}</TableCell>
                          <TableCell className="text-sm text-dark-300 max-w-[280px] truncate" title={txn.description}>{txn.description}</TableCell>
                          <TableCell className={`text-right font-semibold tabular-nums ${txn.type === 'income' ? 'text-green-400' : 'text-red-400'}`}>
                            {txn.type === 'income' ? '+' : '−'}{formatCurrency(txn.amount)}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEditDialog(txn)}>
                                <Pencil className="w-3.5 h-3.5" />
                              </Button>
                              <Button variant="ghost" size="icon" className="h-7 w-7 text-red-400" onClick={() => setDeleteConfirmId(txn.id)}>
                                <Trash2 className="w-3.5 h-3.5" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>

                {/* Pagination */}
                {data.pagination.pages > 1 && (
                  <div className="flex items-center justify-center gap-2 py-3">
                    <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => { setPage(page - 1); setSelectedIds(new Set()) }}>← Назад</Button>
                    <span className="text-sm text-dark-300">{data.pagination.page} / {data.pagination.pages}</span>
                    <Button variant="ghost" size="sm" disabled={page >= data.pagination.pages} onClick={() => { setPage(page + 1); setSelectedIds(new Set()) }}>Вперёд →</Button>
                  </div>
                )}
              </Card>
            )
          )}

          {!isPending && data && (
            <div className="text-sm text-dark-300">Всего: <strong className="text-white">{data.pagination.total}</strong></div>
          )}
        </TabsContent>

        {/* ── Charts Tab ── */}
        <TabsContent value="charts" className="space-y-4">
          <div className="flex items-center gap-3 flex-wrap">
            <Select value={chartPeriod} onValueChange={(v) => setChartPeriod(v as typeof chartPeriod)}>
              <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
              <SelectContent>
                {PERIODS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
              </SelectContent>
            </Select>

            <div className="flex items-center gap-1">
              <Button variant={chartType === 'bar' ? 'default' : 'ghost'} size="sm" onClick={() => setChartType('bar')}>Столбцы</Button>
              <Button variant={chartType === 'line' ? 'default' : 'ghost'} size="sm" onClick={() => setChartType('line')}>Линия</Button>
            </div>

            <label className="flex items-center gap-2 text-sm text-dark-200 cursor-pointer">
              <input type="checkbox" checked={showAnomalies} onChange={(e) => setShowAnomalies(e.target.checked)} />
              Аномалии
            </label>
          </div>

          {chartRows.length > 0 ? (
            <Card className="rounded-xl">
              <CardHeader><CardTitle>Доходы и расходы — {PERIODS.find(p => p.value === chartPeriod)?.label}</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={320}>
                  {chartType === 'bar' ? (
                    <ComposedChart data={chartRows}>
                      <CartesianGrid stroke="rgba(148,163,184,0.08)" strokeDasharray="3 3" />
                      <XAxis dataKey="name" stroke="rgba(148,163,184,0.3)" fontSize={11} />
                      <YAxis stroke="rgba(148,163,184,0.3)" fontSize={10} tick={{ fill: 'rgba(148,163,184,0.5)' }} />
                      <RechartsTooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} />
                      <Legend />
                      <Bar dataKey="income" name="Доход" fill="#22c55e" radius={[4, 4, 0, 0]} maxBarSize={40} />
                      <Bar dataKey="expense" name="Расход" fill="#ef4444" radius={[4, 4, 0, 0]} maxBarSize={40} />
                      <Line type="monotone" dataKey="balance" name="Баланс" stroke="#2dd4bf" strokeWidth={2} dot={false} />
                    </ComposedChart>
                  ) : (
                    <LineChart data={chartRows}>
                      <CartesianGrid stroke="rgba(148,163,184,0.08)" strokeDasharray="3 3" />
                      <XAxis dataKey="name" stroke="rgba(148,163,184,0.3)" fontSize={11} />
                      <YAxis stroke="rgba(148,163,184,0.3)" fontSize={10} tick={{ fill: 'rgba(148,163,184,0.5)' }} />
                      <RechartsTooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} />
                      <Legend />
                      <Line type="monotone" dataKey="income" name="Доход" stroke="#22c55e" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="expense" name="Расход" stroke="#ef4444" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="balance" name="Баланс" stroke="#2dd4bf" strokeWidth={2} dot={false} />
                    </LineChart>
                  )}
                </ResponsiveContainer>
              </CardContent>
            </Card>
          ) : (
            <Card className="rounded-xl">
              <CardContent>
                <EmptyState title="Нет данных" description="Недостаточно данных для построения графика" />
              </CardContent>
            </Card>
          )}

          {chartRows.length > 0 && (
            <Card className="rounded-xl">
              <CardHeader><CardTitle>Детальные данные</CardTitle></CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Период</TableHead>
                      <TableHead className="text-right">Доход</TableHead>
                      <TableHead className="text-right">Расход</TableHead>
                      <TableHead className="text-right">Баланс</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {[...chartRows].reverse().map(row => (
                      <TableRow key={row.name}>
                        <TableCell>{row.name}</TableCell>
                        <TableCell className="text-right text-green-400">{formatCurrency(row.income)}</TableCell>
                        <TableCell className="text-right text-red-400">{formatCurrency(row.expense)}</TableCell>
                        <TableCell className={`text-right ${row.balance >= 0 ? 'text-teal-400' : 'text-red-400'}`}>{formatCurrency(row.balance)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ── Sync Tab ── */}
        <TabsContent value="sync" className="space-y-4">
          <PaymentSync />
        </TabsContent>
      </Tabs>

      {/* ── Add/Edit Dialog ── */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingTxn ? 'Редактировать' : 'Добавить'} транзакцию</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Дата</Label>
                <Input type="date" value={formData.date} onChange={(e) => setFormData({ ...formData, date: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Тип</Label>
                <Select value={formData.type} onValueChange={(v) => setFormData({ ...formData, type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="income">Доход</SelectItem>
                    <SelectItem value="expense">Расход</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Категория</Label>
                <Input value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })} placeholder="категория" list="fin-cat-list" />
                <datalist id="fin-cat-list">
                  {data?.all_categories.map(c => <option key={c} value={c} />)}
                </datalist>
              </div>
              <div className="space-y-2">
                <Label>Контрагент</Label>
                <Input value={formData.participant} onChange={(e) => setFormData({ ...formData, participant: e.target.value })} placeholder="контрагент" list="fin-part-list" />
                <datalist id="fin-part-list">
                  {data?.all_participants.map(p => <option key={p} value={p} />)}
                </datalist>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Сумма</Label>
              <Input type="number" step="0.01" value={String(formData.amount)} onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })} />
            </div>
            <div className="space-y-2">
              <Label>Описание</Label>
              <Input value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} placeholder="описание" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditDialogOpen(false)}>Отмена</Button>
            <Button variant="default" onClick={saveForm} disabled={!formData.date || !formData.category || formData.amount === 0}>
              {editingTxn ? 'Сохранить' : 'Добавить'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Bulk edit Dialog ── */}
      <Dialog open={bulkAction !== null} onOpenChange={(o) => { if (!o) setBulkAction(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {bulkAction === 'type' && 'Изменить тип'}
              {bulkAction === 'category' && 'Изменить категорию'}
              {bulkAction === 'participant' && 'Изменить участника'}
              {bulkAction === 'description' && 'Изменить описание'}
            </DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-2">
            <Label>Значение для {selectedIds.size} записей</Label>
            {bulkAction === 'type' ? (
              <Select value={bulkValue} onValueChange={setBulkValue}>
                <SelectTrigger><SelectValue placeholder="Выберите тип" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="income">Доход</SelectItem>
                  <SelectItem value="expense">Расход</SelectItem>
                </SelectContent>
              </Select>
            ) : (
              <Input value={bulkValue} onChange={(e) => setBulkValue(e.target.value)} placeholder="значение" />
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setBulkAction(null)}>Отмена</Button>
            <Button
              variant="default"
              disabled={!bulkValue}
              onClick={() => { if (bulkAction) bulkEditMutation.mutate({ action: bulkAction, ids: Array.from(selectedIds), value: bulkValue }) }}
            >
              Применить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete Confirm ── */}
      <ConfirmDialog
        open={deleteConfirmId !== null}
        onOpenChange={(v) => { if (!v) setDeleteConfirmId(null) }}
        title="Удалить запись?"
        description="Это действие нельзя отменить."
        confirmLabel="Удалить"
        variant="destructive"
        onConfirm={() => {
          if (deleteConfirmId) deleteMutation.mutate(deleteConfirmId)
          setDeleteConfirmId(null)
        }}
      />

      {/* ── Bulk Delete Confirm ── */}
      <ConfirmDialog
        open={bulkDeleteConfirm}
        onOpenChange={setBulkDeleteConfirm}
        title={`Удалить ${selectedIds.size} записей?`}
        description="Это действие нельзя отменить."
        confirmLabel="Удалить всё"
        variant="destructive"
        onConfirm={() => {
          bulkDeleteMutation.mutate(Array.from(selectedIds))
          setBulkDeleteConfirm(false)
        }}
      />
    </div>
  )
}
