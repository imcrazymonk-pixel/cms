import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Plus, Trash2, Pencil, RefreshCw, BarChart3, History,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import { financeApi, Transaction } from '../api/finance'
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

const PAGE_SIZE = 25

export default function Finance() {
  const queryClient = useQueryClient()

  // Tab state
  const [activeTab, setActiveTab] = useState('table')

  // Filters
  const [filterMonth, setFilterMonth] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterQ, setFilterQ] = useState('')
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState('date')
  const [dir, setDir] = useState('desc')

  // Selection
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // CRUD state
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingTxn, setEditingTxn] = useState<Transaction | null>(null)
  const [formData, setFormData] = useState({ date: '', type: 'income', category: '', participant: '', amount: 0, description: '' })
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false)

  // Load data
  const { data, isPending, error } = useQuery({
    queryKey: ['finance-data', filterMonth, filterType, filterCategory, filterQ, page, sort, dir],
    queryFn: async () => {
      const params: Record<string, unknown> = { page, per_page: PAGE_SIZE, sort, dir }
      if (filterMonth) params.month = filterMonth
      if (filterType) params.type = filterType
      if (filterCategory) params.category = filterCategory
      if (filterQ) params.q = filterQ
      return financeApi.getData(params)
    },
    staleTime: 5_000,
    retry: 2,
  })

  // Build filter params for mutations
  const filterParams = useCallback(() => {
    const p: Record<string, unknown> = {}
    if (filterMonth) p.month = filterMonth
    if (filterType) p.type = filterType
    if (filterCategory) p.category = filterCategory
    if (filterQ) p.q = filterQ
    return p
  }, [filterMonth, filterType, filterCategory, filterQ])

  // ── CRUD Mutations ──
  const addMutation = useMutation({
    mutationFn: (d: typeof formData) => financeApi.add(d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['finance-data'] }); setEditDialogOpen(false); toast.success('Добавлено') },
    onError: (e) => toast.error(String(e)),
  })

  const editMutation = useMutation({
    mutationFn: (d: typeof formData & { id: number }) => financeApi.edit(d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['finance-data'] }); setEditDialogOpen(false); toast.success('Сохранено') },
    onError: (e) => toast.error(String(e)),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => financeApi.delete(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['finance-data'] }); toast.success('Удалено') },
    onError: (e) => toast.error(String(e)),
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: number[]) => financeApi.deleteBulk(ids),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['finance-data'] }); setSelectedIds(new Set()); toast.success(`Удалено ${selectedIds.size} записей`) },
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
    if (editingTxn) {
      editMutation.mutate({ ...formData, id: editingTxn.id })
    } else {
      addMutation.mutate(formData)
    }
  }

  const toggleSort = (field: string) => {
    if (sort === field) {
      setDir(dir === 'asc' ? 'desc' : 'asc')
    } else {
      setSort(field)
      setDir('desc')
    }
  }

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '—'
    const cur = data?.settings?.currency ?? '₽'
    const dec = typeof data?.settings?.decimals === 'number' ? data.settings.decimals : 2
    return `${amount.toFixed(dec)} ${cur}`
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
          <Button variant="ghost" size="sm" onClick={() => queryClient.invalidateQueries({ queryKey: ['finance-data'] })}>
            <RefreshCw className="w-4 h-4" /> Обновить
          </Button>
          <Button variant="primary" size="sm" onClick={openAddDialog}>
            <Plus className="w-4 h-4" /> Добавить
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      {data && (
        <div className="grid grid-cols-4 gap-4">
          <Card className="rounded-xl"><CardContent className="p-5">
            <p className="text-xs text-dark-300 uppercase tracking-wider">Доход</p>
            <p className="text-lg font-bold text-green-400">{formatCurrency(data.summary.income)}</p>
          </CardContent></Card>
          <Card className="rounded-xl"><CardContent className="p-5">
            <p className="text-xs text-dark-300 uppercase tracking-wider">Расход</p>
            <p className="text-lg font-bold text-red-400">{formatCurrency(data.summary.expense)}</p>
          </CardContent></Card>
          <Card className="rounded-xl"><CardContent className="p-5">
            <p className="text-xs text-dark-300 uppercase tracking-wider">Баланс</p>
            <p className={`text-lg font-bold ${data.summary.balance >= 0 ? 'text-teal-400' : 'text-red-400'}`}>{formatCurrency(data.summary.balance)}</p>
          </CardContent></Card>
          <Card className="rounded-xl"><CardContent className="p-5">
            <p className="text-xs text-dark-300 uppercase tracking-wider">Записей</p>
            <p className="text-lg font-bold text-white">{data.summary.count}</p>
          </CardContent></Card>
        </div>
      )}

      {isPending && (
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
      )}

      {error && <QueryError error={error} />}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="table"><History className="w-4 h-4" /> Таблица</TabsTrigger>
          <TabsTrigger value="charts"><BarChart3 className="w-4 h-4" /> Графики</TabsTrigger>
        </TabsList>

        {/* ── Table Tab ── */}
        <TabsContent value="table" className="space-y-4">
          {/* Filters */}
          {data && (
            <div className="flex items-center gap-3 flex-wrap">
              <Select value={filterMonth} onValueChange={(v) => { setFilterMonth(v); setPage(1); setSelectedIds(new Set()) }}>
                <SelectTrigger className="w-32"><SelectValue placeholder="Месяц" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все месяцы</SelectItem>
                  {data.all_months.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                </SelectContent>
              </Select>

              <Select value={filterType} onValueChange={(v) => { setFilterType(v); setPage(1) }}>
                <SelectTrigger className="w-28"><SelectValue placeholder="Тип" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все типы</SelectItem>
                  <SelectItem value="income">Доход</SelectItem>
                  <SelectItem value="expense">Расход</SelectItem>
                </SelectContent>
              </Select>

              <Select value={filterCategory} onValueChange={(v) => { setFilterCategory(v); setPage(1) }}>
                <SelectTrigger className="w-36"><SelectValue placeholder="Категория" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все категории</SelectItem>
                  {data.all_categories.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>

              <Input placeholder="Поиск..." value={filterQ} onChange={(e) => { setFilterQ(e.target.value); setPage(1) }} className="w-40" />

              {selectedIds.size > 0 && (
                <Button variant="destructive" size="sm" onClick={() => setBulkDeleteConfirm(true)}>
                  <Trash2 className="w-4 h-4" /> Удалить ({selectedIds.size})
                </Button>
              )}
            </div>
          )}

          {/* Table */}
          {data && (
            <Card className="rounded-xl">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8"><input type="checkbox" onChange={(e) => {
                        if (e.target.checked) setSelectedIds(new Set(data.transactions.map(t => t.id)))
                        else setSelectedIds(new Set())
                      }} /></TableHead>
                      <TableHead sortable="true" onClick={() => toggleSort('date')}>Дата {sort === 'date' ? (dir === 'asc' ? '▲' : '▼') : ''}</TableHead>
                      <TableHead>Тип</TableHead>
                      <TableHead sortable="true" onClick={() => toggleSort('category')}>Категория {sort === 'category' ? (dir === 'asc' ? '▲' : '▼') : ''}</TableHead>
                      <TableHead>Контрагент</TableHead>
                      <TableHead>Описание</TableHead>
                      <TableHead sortable="true" onClick={() => toggleSort('amount')}>Сумма {sort === 'amount' ? (dir === 'asc' ? '▲' : '▼') : ''}</TableHead>
                      <TableHead className="w-24">Действия</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.transactions.length === 0 ? (
                      <TableRow><TableCell colSpan={8}><EmptyState title="Нет записей" description="Нет транзакций по заданным фильтрам" /></TableCell></TableRow>
                    ) : data.transactions.map(txn => (
                      <TableRow key={txn.id}>
                        <TableCell><input type="checkbox" checked={selectedIds.has(txn.id)} onChange={(e) => {
                          const next = new Set(selectedIds)
                          e.target.checked ? next.add(txn.id) : next.delete(txn.id)
                          setSelectedIds(next)
                        }} /></TableCell>
                        <TableCell className="text-sm text-dark-200">{txn.date_display}</TableCell>
                        <TableCell>
                          <Badge className={txn.type === 'income' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
                            {txn.type === 'income' ? 'Доход' : 'Расход'}
                          </Badge>
                        </TableCell>
                        <TableCell>{txn.category}</TableCell>
                        <TableCell className="text-sm text-dark-300">{txn.participant}</TableCell>
                        <TableCell className="text-sm text-dark-300 max-w-[200px] truncate">{txn.description}</TableCell>
                        <TableCell className={`font-medium ${txn.type === 'income' ? 'text-green-400' : 'text-red-400'}`}>
                          {txn.type === 'income' ? '+' : '-'}{formatCurrency(Math.abs(txn.amount))}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="icon" onClick={() => openEditDialog(txn)} className="h-7 w-7"><Pencil className="w-3.5 h-3.5" /></Button>
                            <Button variant="ghost" size="icon" onClick={() => setDeleteConfirmId(txn.id)} className="h-7 w-7 text-red-400"><Trash2 className="w-3.5 h-3.5" /></Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {data.pagination.pages > 1 && (
                <div className="flex items-center justify-center gap-2 py-3">
                  <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => { setPage(page - 1); setSelectedIds(new Set()) }}>
                    ← Назад
                  </Button>
                  <span className="text-sm text-dark-300">
                    {data.pagination.page} / {data.pagination.pages}
                  </span>
                  <Button variant="ghost" size="sm" disabled={page >= data.pagination.pages} onClick={() => { setPage(page + 1); setSelectedIds(new Set()) }}>
                    Вперёд →
                  </Button>
                </div>
              )}
            </Card>
          )}
        </TabsContent>

        {/* ── Charts Tab ── */}
        <TabsContent value="charts">
          {data && data.chart.monthly.length > 0 && (
            <>
              {/* Bar chart with recharts */}
              <Card className="rounded-xl">
                <CardHeader><CardTitle>Доходы и расходы по месяцам</CardTitle></CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={[...data.chart.monthly].reverse().filter(r => r?.date).map(row => ({
                        month: row.date.slice(5),
                        income: row.income ?? 0,
                        expense: -(row.expense ?? 0),
                        balance: row.balance ?? 0,
                      }))}
                    >
                      <CartesianGrid stroke="rgba(148,163,184,0.08)" strokeDasharray="3 3" />
                      <XAxis dataKey="month" type="category" stroke="rgba(148,163,184,0.3)" fontSize={11} />
                      <YAxis type="number" stroke="rgba(148,163,184,0.3)" fontSize={10} tick={{ fill: 'rgba(148,163,184,0.5)' }} />
                      <RechartsTooltip contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} />
                      <Bar dataKey="income" name="Доход" radius={4} maxBarSize={40}>
                        <Cell fill="#22c55e" />
                      </Bar>
                      <Bar dataKey="expense" name="Расход" radius={4} maxBarSize={40}>
                        <Cell fill="#ef4444" />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Data table */}
              <Card className="rounded-xl">
                <CardHeader><CardTitle>Детальные данные</CardTitle></CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Месяц</TableHead>
                        <TableHead>Доход</TableHead>
                        <TableHead>Расход</TableHead>
                        <TableHead>Баланс</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {[...data.chart.monthly].reverse().map(row => (
                        <TableRow key={row.date}>
                          <TableCell>{row.date}</TableCell>
                          <TableCell className="text-green-400">{formatCurrency(row.income)}</TableCell>
                          <TableCell className="text-red-400">{formatCurrency(row.expense)}</TableCell>
                          <TableCell className={row.balance >= 0 ? 'text-teal-400' : 'text-red-400'}>{formatCurrency(row.balance)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}
          {data && data.chart.monthly.length === 0 && (
            <Card className="rounded-xl">
              <CardContent>
                <EmptyState title="Нет данных" description="Недостаточно данных для построения графика" />
              </CardContent>
            </Card>
          )}
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
                <Input value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })} placeholder="категория" />
              </div>
              <div className="space-y-2">
                <Label>Контрагент</Label>
                <Input value={formData.participant} onChange={(e) => setFormData({ ...formData, participant: e.target.value })} placeholder="контрагент" />
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
            <Button variant="primary" onClick={saveForm} disabled={!formData.date || !formData.category || formData.amount === 0}>
              {editingTxn ? 'Сохранить' : 'Добавить'}
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