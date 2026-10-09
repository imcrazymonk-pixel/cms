import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { RefreshCw, Download, Search, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { financeApi, type PaymentPreviewRow, type PaymentSettings } from '../api/finance'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table'

type Provider = 'platega' | 'yookassa'

const META: Record<Provider, { title: string; description: string }> = {
  platega: { title: 'Platega', description: 'Импорт пополнений из Platega' },
  yookassa: { title: 'YooKassa', description: 'Импорт платежей из YooKassa' },
}

function fmtDate(dt: string): string {
  if (!dt) return '—'
  const d = new Date(dt)
  return isNaN(d.getTime()) ? dt : d.toLocaleString('ru-RU')
}

function money(v: number | undefined | null): string {
  if (v === undefined || v === null) return ''
  return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function statusBadge(status: PaymentPreviewRow['status']) {
  if (status === 'new') return <Badge variant="default" className="text-[10px]">новый</Badge>
  if (status === 'duplicate') return <Badge variant="secondary" className="text-[10px]">дубликат</Badge>
  return <Badge variant="outline" className="text-[10px]">пропуск</Badge>
}

function ProviderPanel({ provider }: { provider: Provider }) {
  const qc = useQueryClient()
  const api = financeApi.payments[provider]
  const meta = META[provider]

  const [rows, setRows] = useState<PaymentPreviewRow[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState<null | 'preview' | 'sync' | 'import'>(null)

  const { data: settings, isLoading } = useQuery<PaymentSettings>({
    queryKey: ['payments', provider, 'settings'],
    queryFn: () => api.settings(),
  })

  const reloadSettings = () => qc.invalidateQueries({ queryKey: ['payments', provider, 'settings'] })

  const doPreview = async () => {
    setBusy('preview')
    try {
      const res = await api.preview({})
      if (res.success === false) { toast.error(res.error || 'Ошибка предпросмотра'); return }
      const list = res.transactions || []
      setRows(list)
      setSelected(new Set(list.filter(r => r.status === 'new').map(r => r.record_id)))
      if (list.length === 0) toast('Нет транзакций за период')
    } catch (e) {
      toast.error((e as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Ошибка предпросмотра')
    } finally { setBusy(null) }
  }

  const doSync = async () => {
    setBusy('sync')
    try {
      const res = await api.sync()
      if (res.success === false) { toast.error(res.error || 'Ошибка синхронизации'); return }
      toast.success(`Синхронизация: добавлено ${res.added ?? 0}, пропущено ${res.skipped ?? 0}`)
      qc.invalidateQueries({ queryKey: ['finance'] })
      reloadSettings()
    } catch (e) {
      toast.error((e as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Ошибка синхронизации')
    } finally { setBusy(null) }
  }

  const doImport = async () => {
    const chosen = rows.filter(r => selected.has(r.record_id)).map(r => ({ ...r, include: true }))
    if (chosen.length === 0) { toast.error('Ничего не выбрано'); return }
    setBusy('import')
    try {
      const res = await api.import(chosen)
      if (res.success === false) { toast.error(res.error || 'Ошибка импорта'); return }
      toast.success(`Добавлено: ${res.added ?? 0}, пропущено: ${res.skipped ?? 0}`)
      setRows([]); setSelected(new Set())
      qc.invalidateQueries({ queryKey: ['finance'] })
      reloadSettings()
    } catch (e) {
      toast.error((e as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Ошибка импорта')
    } finally { setBusy(null) }
  }

  const toggle = (id: string) => setSelected(prev => {
    const n = new Set(prev)
    if (n.has(id)) n.delete(id); else n.add(id)
    return n
  })

  const newCount = rows.filter(r => r.status === 'new').length

  return (
    <Card className="rounded-xl p-5 space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h3 className="text-base font-semibold text-white">{meta.title}</h3>
          <p className="text-xs text-dark-300 mt-0.5">{meta.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={doPreview} disabled={busy !== null}>
            <Search className="w-4 h-4 mr-1.5" /> {busy === 'preview' ? 'Загрузка…' : 'Предпросмотр'}
          </Button>
          <Button variant="default" size="sm" onClick={doSync} disabled={busy !== null}>
            <RefreshCw className={`w-4 h-4 mr-1.5 ${busy === 'sync' ? 'animate-spin' : ''}`} />
            {busy === 'sync' ? 'Синхронизация…' : 'Синхронизировать'}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <Skeleton className="h-5 w-72" />
      ) : (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-dark-200">
          <span>Последняя синхронизация: <span className="text-dark-100">{fmtDate(settings?.last_sync || '')}</span></span>
          {settings?.auto_sync ? <Badge variant="secondary" className="text-[10px]">авто</Badge> : null}
          {settings?.last_error ? (
            <span className="inline-flex items-center gap-1 text-red-400">
              <AlertTriangle className="w-3.5 h-3.5" /> {settings.last_error}
            </span>
          ) : settings?.last_sync_ok ? (
            <span className="inline-flex items-center gap-1 text-green-400">
              <CheckCircle2 className="w-3.5 h-3.5" /> OK
            </span>
          ) : null}
        </div>
      )}

      {rows.length > 0 && (
        <div className="space-y-3">
          <div className="rounded-lg border border-[var(--glass-border)]/50 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8" />
                  <TableHead>Дата</TableHead>
                  <TableHead>Описание</TableHead>
                  <TableHead className="text-right">Сумма</TableHead>
                  <TableHead className="text-right">К зачислению</TableHead>
                  <TableHead>Статус</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r, i) => (
                  <TableRow key={r.record_id || `${r.date}-${r.gross}-${i}`} className={r.status !== 'new' ? 'opacity-60' : undefined}>
                    <TableCell>
                      <input
                        type="checkbox"
                        disabled={r.status !== 'new' || !r.record_id}
                        checked={selected.has(r.record_id)}
                        onChange={() => toggle(r.record_id)}
                      />
                    </TableCell>
                    <TableCell className="text-xs whitespace-nowrap">{r.date}</TableCell>
                    <TableCell className="text-xs max-w-[360px] truncate" title={r.description}>{r.description}</TableCell>
                    <TableCell className="text-xs text-right whitespace-nowrap">{money(r.gross)}</TableCell>
                    <TableCell className="text-xs text-right whitespace-nowrap">{r.status === 'new' ? money(r.amount) : ''}</TableCell>
                    <TableCell>{statusBadge(r.status)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <p className="text-xs text-dark-200">Выбрано: {selected.size} из {newCount} новых</p>
            <Button variant="default" size="sm" onClick={doImport} disabled={busy !== null || selected.size === 0}>
              <Download className="w-4 h-4 mr-1.5" /> {busy === 'import' ? 'Импорт…' : 'Импортировать выбранные'}
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}

/** Platega + YooKassa sync panel (preview → import, or one-click sync). */
export default function PaymentSync() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-dark-200">
        «Предпросмотр» покажет транзакции за период — отметьте нужные и импортируйте.
        «Синхронизировать» сразу импортирует все новые автоматически.
      </p>
      <ProviderPanel provider="platega" />
      <ProviderPanel provider="yookassa" />
    </div>
  )
}
