import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { RefreshCw, Download, Search, AlertTriangle, CheckCircle2, History, Zap } from 'lucide-react'
import { financeApi, type PaymentPreviewRow, type PaymentSettings, type SyncHistoryEntry, type SyncProviderStatus } from '../api/finance'
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

  const reloadSyncMeta = () => {
    qc.invalidateQueries({ queryKey: ['payments', provider, 'status'] })
    qc.invalidateQueries({ queryKey: ['payments', provider, 'history'] })
  }

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
      reloadSyncMeta()
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
      reloadSyncMeta()
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

      <LiveSyncStatus provider={provider} />

      <SyncHistory provider={provider} />

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

/** Живой статус автосинка (Вариант D): включён ли, интервал, next_run, lock. */
function LiveSyncStatus({ provider }: { provider: Provider }) {
  const api = financeApi.payments[provider]
  const { data, isFetching, refetch } = useQuery<SyncProviderStatus | null>({
    queryKey: ['payments', provider, 'status'],
    queryFn: async () => {
      const res = await api.status()
      return res.providers?.find(p => p.provider === provider) ?? null
    },
  })

  const nextRun = data?.next_run ? fmtDate(data.next_run) : null

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-dark-200" data-sync-status>
      <span className="inline-flex items-center gap-1.5">
        <Zap className="w-3.5 h-3.5 text-dark-300" />
        Автосинк:
        {data?.auto_sync ? (
          <Badge variant="secondary" className="text-[10px] bg-green-500/20 text-green-400">вкл</Badge>
        ) : (
          <Badge variant="outline" className="text-[10px]">выкл</Badge>
        )}
      </span>
      {data?.auto_sync ? (
        <span>Интервал: <span className="text-dark-100">{data.interval} с</span></span>
      ) : null}
      {data?.auto_sync && nextRun ? (
        <span>Следующий запуск: <span className="text-dark-100">{nextRun}</span></span>
      ) : null}
      {data?.lock_active ? (
        <span className="inline-flex items-center gap-1 text-amber-400">
          <AlertTriangle className="w-3.5 h-3.5" /> идёт синхронизация…
        </span>
      ) : null}
      {data && !data.configured ? (
        <span className="inline-flex items-center gap-1 text-amber-400">
          <AlertTriangle className="w-3.5 h-3.5" /> не настроен (нет ключей)
        </span>
      ) : null}
      <Button variant="ghost" size="sm" className="h-6" onClick={() => refetch()} disabled={isFetching}>
        <RefreshCw className={`w-3 h-3 mr-1 ${isFetching ? 'animate-spin' : ''}`} /> Обновить статус
      </Button>
    </div>
  )
}

/** История синхронизаций (Вариант C): последние события из app_logs. */
function SyncHistory({ provider }: { provider: Provider }) {
  const api = financeApi.payments[provider]
  const { data, isLoading, refetch, isFetching } = useQuery<SyncHistoryEntry[]>({
    queryKey: ['payments', provider, 'history'],
    queryFn: async () => {
      const res = await api.history(10)
      return res.data || []
    },
  })

  const entries = data || []

  return (
    <div className="space-y-2" data-sync-history>
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-medium text-dark-300 uppercase tracking-wider inline-flex items-center gap-1.5">
          <History className="w-3.5 h-3.5" /> История синхронизаций
        </h4>
        <Button variant="ghost" size="sm" className="h-6" onClick={() => refetch()} disabled={isLoading || isFetching}>
          <RefreshCw className={`w-3 h-3 mr-1 ${isFetching ? 'animate-spin' : ''}`} /> Обновить
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-16 w-full" />
      ) : entries.length === 0 ? (
        <p className="text-xs text-dark-400">Логов синхронизации пока нет — они появятся после первого запуска.</p>
      ) : (
        <div className="rounded-lg border border-[var(--glass-border)]/50 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-32">Время</TableHead>
                <TableHead className="w-16">Уровень</TableHead>
                <TableHead>Результат</TableHead>
                <TableHead className="w-28">Источник</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map(e => {
                const ok = e.context?.ok
                const sourceLabel =
                  e.context?.source === 'auto' ? 'авто' :
                  e.context?.source === 'manual' ? 'ручной' :
                  e.context?.source === 'cron' ? 'cron' :
                  (e.source === 'autosync' ? 'авто' : (e.source || '—'))
                return (
                  <TableRow key={e.id}>
                    <TableCell className="text-xs whitespace-nowrap text-dark-300">{fmtDate(e.created_at)}</TableCell>
                    <TableCell>
                      <Badge className={
                        e.level === 'error' ? 'bg-red-500/20 text-red-400' :
                        e.level === 'warning' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-blue-500/20 text-blue-400'
                      }>{e.level}</Badge>
                    </TableCell>
                    <TableCell className="text-xs max-w-[380px]">
                      {ok === false ? (
                        <span className="text-red-400 inline-flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          {(e.context?.error as string) || e.message}
                        </span>
                      ) : (
                        <span className="text-dark-200">
                          Добавлено{' '}
                          <strong className="text-green-400">{e.context?.added ?? 0}</strong>, пропущено{' '}
                          <strong className="text-dark-100">{e.context?.skipped ?? 0}</strong>
                          {typeof e.context?.new === 'number' ? <> (новых: {e.context.new})</> : null}
                          {typeof e.context?.duration_ms === 'number' ? <> · {e.context.duration_ms} мс</> : null}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-dark-300">{sourceLabel}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
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
