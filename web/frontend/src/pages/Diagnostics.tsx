import { useState, useEffect } from 'react'
import { diagnosticsApi, Node, DiagnosticsData, PingEntry, NodeLoad, NodeRAM, NodeDisk, NodeTCP, NodeNetworkErrors, NodeNginx, NodeData } from '../api/diagnostics'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import {
  Monitor, Check, AlertTriangle,
  RefreshCw, Download, Loader2, X, Server,
  BarChart3,
} from 'lucide-react'

const PING_LABELS: Record<string, string> = {
  '77.88.8.8': 'Яндекс DNS',
  '8.8.8.8': 'Google DNS',
  'ya.ru': 'Яндекс (Москва)',
  'vk.com': 'VK (СПб)',
  '144.31.96.78': 'DE (files)',
  '144.31.156.172': 'Панель',
  '31.77.128.251': 'FI (audio)',
  '150.241.94.61': 'NL (photo)',
  '159.194.221.84': 'RU (video)',
  '162.217.248.186': 'US (data)',
  '155.212.131.4': 'Yandex',
}

const LOAD_CLS = (v: number): string =>
  v < 0.5 ? 'text-green-400' : v < 0.8 ? 'text-amber-400' : 'text-red-400'

const SPEED_CLS = (v: number): string =>
  v > 100 ? 'text-green-400' : v > 5 ? 'text-amber-400' : 'text-red-400'

const RETRANS_CLS = (v: number | null): string =>
  v === null ? '' : v < 0.5 ? 'text-green-400' : v < 2 ? 'text-amber-400' : 'text-red-400'

const TIMEOUT_CLS = (v: number): string =>
  v < 1_000_000 ? 'text-green-400' : v < 10_000_000 ? 'text-amber-400' : 'text-red-400'

const DISK_CLS = (v: number): string =>
  v < 50 ? 'text-green-400' : v < 80 ? 'text-amber-400' : 'text-red-400'

const PING_CLS = (ms: number | null): string =>
  ms === null ? '' : ms < 30 ? 'text-green-400' : ms < 80 ? 'text-amber-400' : 'text-red-400'

function formatCount(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K'
  return String(n)
}

export default function Diagnostics() {
  const [data, setData] = useState<DiagnosticsData | null>(null)
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCollecting, setIsCollecting] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [toast, setToast] = useState<{ msg: string; type: 'ok' | 'err' | 'warn' } | null>(null)
  let toastTimer: ReturnType<typeof setTimeout> | null = null

  const showToast = (msg: string, type: 'ok' | 'err' | 'warn' = 'ok') => {
    if (toastTimer) clearTimeout(toastTimer)
    setToast({ msg, type })
    toastTimer = setTimeout(() => { setToast(null); toastTimer = null }, 2500)
  }

  const loadData = async () => {
    try {
      const res = await diagnosticsApi.getData()
      if (res.success) {
        setData(res)
        setIsCollecting(res.is_collecting)
        setError(null)
      } else {
        setError('Не удалось загрузить данные')
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка подключения')
    } finally {
      setIsPending(false)
    }
  }

  const startCollect = async () => {
    setIsCollecting(true)
    showToast('⏳ Запуск сбора статистики...', 'warn')
    try {
      const res = await diagnosticsApi.collect()
      if (res.success) {
        showToast('⏳ Сбор запущен. Ожидайте ~30 сек...', 'warn')
        // Poll for completion
        let attempts = 0
        const maxAttempts = 20
        const poll = async () => {
          attempts++
          try {
            const pollRes = await diagnosticsApi.getData()
            if (!pollRes.is_collecting && pollRes.collected_at) {
              setIsCollecting(false)
              setData(pollRes)
              showToast('✅ Сбор завершён', 'ok')
              return
            }
          } catch { /* continue polling */ }
          if (attempts < maxAttempts) {
            setTimeout(poll, 5000)
          } else {
            setIsCollecting(false)
            showToast('⚠️ Сбор не завершился за 100с', 'warn')
          }
        }
        setTimeout(poll, 3000)
      } else {
        setIsCollecting(false)
        showToast('❌ ' + (res.error || 'Ошибка запуска'), 'err')
      }
    } catch (err: unknown) {
      setIsCollecting(false)
      showToast('❌ Ошибка: ' + (err instanceof Error ? err.message : String(err)), 'err')
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return
    const timer = setInterval(() => {
      diagnosticsApi.getData().then(res => {
        if (res.success) { setData(res); setIsCollecting(res.is_collecting) }
      }).catch(() => {})
    }, 30000)
    return () => clearInterval(timer)
  }, [autoRefresh])

  const refresh = () => {
    setIsPending(true)
    loadData()
    showToast('🔄 Обновлено', 'ok')
  }

  // ── Build problems list ──
  const buildProblems = (nodes: Node[]): { type: 'err' | 'warn'; text: string }[] => {
    const problems: { type: 'err' | 'warn'; text: string }[] = []
    for (const n of nodes) {
      if (!n.reachable) {
        problems.push({ type: 'err', text: `${n.name}: Недоступна (${n.error || 'таймаут'})` })
        continue
      }
      const d = n.data
      if (!d) continue
      const dSafe = d as NodeData
      const tcp: NodeTCP | undefined = dSafe.tcp
      if (tcp && tcp.retrans_pct != null && tcp.retrans_pct >= 2) {
        problems.push({ type: 'err', text: `${n.name}: ${tcp.retrans_pct}% ретрансмиссий, ${formatCount(tcp.timeouts || 0)} таймаутов` })
      }
      if (dSafe.nginx && dSafe.nginx.status === 'error') {
        problems.push({ type: 'warn', text: `${n.name}: nginx: ${dSafe.nginx.error || 'ошибка'}` })
      }
      if (dSafe.speed_download_mbps !== null && dSafe.speed_download_mbps !== undefined && dSafe.speed_download_mbps < 3) {
        problems.push({ type: 'warn', text: `${n.name}: скорость ${dSafe.speed_download_mbps} Мбит/с` })
      }
      if (dSafe.load && dSafe.load['1m'] !== undefined && dSafe.load['1m'] > 0.8) {
        problems.push({ type: 'warn', text: `${n.name}: Load ${dSafe.load['1m']}` })
      }
    }
    return problems
  }

  // ── Build comparison rows ──
  const buildComparison = (nodes: Node[]): { name: string; load: number; ram: string; diskPct: number; speed: number; retrans: number | null; timeouts: number; yaMs: number | null; deMs: number | null }[] => {
    return nodes
      .filter(n => n.reachable && n.data)
      .map(n => {
        const d = n.data!
        const tcp: NodeTCP = d.tcp || {}
        const pings: Record<string, PingEntry> = d.pings || {}
        const load: NodeLoad = d.load || {}
        const ram: NodeRAM = d.ram || {}
        const disk: NodeDisk = d.disk || {}
        const diskPct = typeof disk.pct === 'string' ? parseInt(disk.pct) : 0
        const ya: PingEntry = pings['ya.ru'] || { ms: null, loss: null }
        const de: PingEntry = pings['144.31.96.78'] || { ms: null, loss: null }
        return {
          name: n.name,
          load: load['1m'] || 0,
          ram: ram.used || '—',
          diskPct,
          speed: d.speed_download_mbps || 0,
          retrans: tcp.retrans_pct !== null && tcp.retrans_pct !== undefined ? tcp.retrans_pct : null,
          timeouts: tcp.timeouts || 0,
          yaMs: ya.ms ?? null,
          deMs: de.ms ?? null,
        }
      })
  }

  // ── Build node card HTML ──
  const buildCard = (n: Node): React.ReactNode => {
    const d = n.data
    const isOk = n.reachable

    if (!isOk) {
      return (
        <Card key={n.id} className="rounded-xl border-red-900/30" style={{ background: 'rgba(95,30,30,0.15)' }}>
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold">{n.name}</h3>
              <Badge className="bg-red-500/20 text-red-400"><X className="w-3.5 h-3.5" /> Недоступна</Badge>
            </div>
            <div className="flex justify-between text-sm py-1 border-b border-white/5">
              <span className="text-dark-300">Ошибка</span>
              <span className="text-red-400 font-semibold">{n.error || 'таймаут'}</span>
            </div>
          </CardContent>
        </Card>
      )
    }

    if (!d) return null

    const load: NodeLoad = d.load || {}
    const ram: NodeRAM = d.ram || {}
    const disk: NodeDisk = d.disk || {}
    const tcp: NodeTCP = d.tcp || {}
    const net: NodeNetworkErrors = d.network_errors || {}
    const pings: Record<string, PingEntry> = d.pings || {}
    const nginx: NodeNginx = d.nginx || {}
    const docker = d.docker || []
    const certs = d.certs || []

    const load1m = load['1m'] || 0
    const retransPct = tcp.retrans_pct
    const speed = d.speed_download_mbps
    const diskPct = disk.pct ? parseInt(disk.pct) : 0

    return (
      <Card key={n.id} className="rounded-xl">
        <CardContent className="p-5">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-base font-semibold flex items-center gap-2">
              <Server className="w-4 h-4 text-dark-300" />
              {n.name}
            </h3>
            <Badge className="bg-green-500/15 text-green-400"><Check className="w-3 h-3" /> Доступна</Badge>
          </div>

          {/* Hostname & Uptime */}
          <div className="grid grid-cols-2 gap-x-4 text-sm space-y-1">
            <span className="text-dark-300">Hostname</span>
            <span className="font-semibold text-right">{d.hostname || '—'}</span>
            <span className="text-dark-300">Uptime</span>
            <span className="font-semibold text-right">{d.uptime || '—'}</span>
          </div>

          <div className="h-px bg-white/5 my-2" />

          {/* CPU / RAM / Disk */}
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-dark-300">CPU / RAM</span>
              <span className="font-semibold">{(d.cpu_cores || '?') + ' ядра · ' + (ram.used || '—') + ' / ' + (ram.total || '—')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-dark-300">Диск</span>
              <span className={`font-semibold ${DISK_CLS(diskPct)}`}>{disk.used || '—'} / {disk.total || '—'} ({disk.pct || '—'})</span>
            </div>
            <div className="flex justify-between">
              <span className="text-dark-300">Load (1/5/15)</span>
              <span className={`font-semibold ${LOAD_CLS(load1m)}`}>
                {load['1m'] ?? '—'} / {load['5m'] ?? '—'} / {load['15m'] ?? '—'}
              </span>
            </div>
          </div>

          <div className="h-px bg-white/5 my-2" />

          {/* Docker & Nginx */}
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-dark-300">Docker</span>
              <span className="font-semibold">{docker.map(c => c.name).join(', ') || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-dark-300">nginx</span>
              <span className="font-semibold">
                {nginx.status === 'ok' ? <span className="text-green-400">✅ OK</span> :
                 nginx.status === 'error' ? <span className="text-red-400">🔴 {nginx.error || 'error'}</span> :
                 <span className="text-amber-400">⚠️ неизвестно</span>}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-dark-300">Download</span>
              <span className={`font-semibold ${speed !== undefined && speed !== null ? SPEED_CLS(speed) : ''}`}>
                {speed !== undefined && speed !== null ? speed + ' Мбит/с' : '—'}
              </span>
            </div>
          </div>

          <div className="h-px bg-white/5 my-2" />

          {/* TCP */}
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-dark-300">TCP ретрансмиссии</span>
              <span className={`font-semibold ${RETRANS_CLS(retransPct ?? null)}`}>
                {retransPct !== null ? retransPct + '%' : '—'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-dark-300">TCP таймауты</span>
              <span className={`font-semibold ${TIMEOUT_CLS(tcp.timeouts || 0)}`}>
                {(tcp.timeouts || 0) > 0 ? formatCount(tcp.timeouts || 0) : '0'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-dark-300">Traffic in/out</span>
              <span className="font-semibold">{formatCount(tcp.in_segs || 0)} / {formatCount(tcp.out_segs || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-dark-300">Ошибки сети (rx/tx)</span>
              <span className="font-semibold">{(net.rx_err || 0)} / {(net.tx_err || 0)}</span>
            </div>
          </div>

          {/* Certificates */}
          {certs.length > 0 && (
            <>
              <div className="h-px bg-white/5 my-2" />
              <div className="flex justify-between text-sm">
                <span className="text-dark-300">Сертификаты</span>
                <span className="font-semibold">{certs.length} шт</span>
              </div>
            </>
          )}

          {/* Pings */}
          {Object.keys(pings).length > 0 && (
            <div
              className="mt-2 p-1.5 rounded-lg"
              style={{ background: 'rgba(255,255,255,0.04)' }}
            >
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
                {Object.entries(pings).map(([ip, p]) => {
                  if (p.ms === null && p.loss === null) return null
                  const label = PING_LABELS[ip] || ip
                  const cls = PING_CLS(p.ms)
                  return (
                    <>
                      <span className="text-dark-300">{label}</span>
                      <span className={`font-semibold text-right ${cls}`}>
                        {p.ms !== null ? p.ms + 'ms' : '—'}
                      </span>
                    </>
                  )
                }).filter(Boolean)}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  // ── Render ──
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Monitor className="w-5 h-5 text-primary" />
          <h1 className="text-xl font-bold text-white tracking-tight">Диагностика нод</h1>
          <span className="text-sm text-dark-300">
            {data?.collected_at
              ? '· обновлено ' + data.collected_at.replace('T', ' ').replace('Z', '')
              : '· данные не загружены'}
          </span>
          {isCollecting && (
            <Badge className="bg-amber-500/15 text-amber-400">
              <Loader2 className="w-3 h-3 animate-spin" /> Идёт сбор...
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <label className="flex items-center gap-1.5 text-xs text-green-400 cursor-pointer">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            ♻️ Авто 30с
          </label>
          <Button variant="ghost" size="sm" onClick={refresh} disabled={isPending}>
            <RefreshCw className="w-4 h-4" /> Обновить
          </Button>
          <Button variant="default" size="sm" onClick={startCollect} disabled={isCollecting}>
            <Download className="w-4 h-4" /> {isCollecting ? 'Сбор...' : 'Собрать статистику'}
          </Button>
        </div>
      </div>

      {/* Loading */}
      {isPending && (
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
      )}

      {/* Error */}
      {error && <QueryError message={error} />}

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-4 gap-4">
          <Card className="rounded-xl"><CardContent className="p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(99,102,241,0.15)' }}>
                <Monitor className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <p className="text-xs text-dark-300 uppercase tracking-wider">Всего нод</p>
                <p className="text-xl font-bold text-white">{data.summary.total}</p>
              </div>
            </div>
          </CardContent></Card>
          <Card className="rounded-xl"><CardContent className="p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(34,197,94,0.15)' }}>
                <Check className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-xs text-dark-300 uppercase tracking-wider">Доступны</p>
                <p className="text-xl font-bold text-green-400">{data.summary.reachable}</p>
              </div>
            </div>
          </CardContent></Card>
          <Card className="rounded-xl"><CardContent className="p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(239,68,68,0.15)' }}>
                <X className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <p className="text-xs text-dark-300 uppercase tracking-wider">Недоступны</p>
                <p className="text-xl font-bold text-red-400">{data.summary.unreachable}</p>
              </div>
            </div>
          </CardContent></Card>
          <Card className="rounded-xl"><CardContent className="p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(245,158,11,0.15)' }}>
                <AlertTriangle className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <p className="text-xs text-dark-300 uppercase tracking-wider">Проблем</p>
                <p className="text-xl font-bold text-amber-400">{data.summary.problems}</p>
              </div>
            </div>
          </CardContent></Card>
        </div>
      )}

      {/* Data content */}
      {data && data.nodes.length === 0 && (
        <Card className="rounded-xl col-span-full">
          <CardContent className="p-10 text-center">
            <div className="mb-2 text-4xl opacity-40">
              <Monitor className="w-12 h-12" />
            </div>
            <h3 className="text-base font-semibold mb-2">Данные мониторинга не загружены</h3>
            <p className="text-sm text-dark-300 mb-2">Нажмите «Собрать статистику» — скрипт опросит все ноды (занимает ~30 сек).</p>
            <div className="flex gap-2.5 mt-3 justify-center">
              <Button variant="default" size="default" onClick={startCollect} disabled={isCollecting}>
                <Download className="w-4 h-4" /> Собрать статистику
              </Button>
              <Button variant="ghost" size="sm" onClick={refresh}>
                <RefreshCw className="w-4 h-4" /> Обновить
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Node Cards */}
      {data && data.nodes.length > 0 && (
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))' }}>
          {data.nodes.map(n => buildCard(n))}
        </div>
      )}

      {/* Problems Panel */}
      {data && data.nodes.length > 0 && (() => {
        const problems = buildProblems(data.nodes)
        if (problems.length === 0) return null
        return (
          <Card className="rounded-xl">
            <CardHeader>
              <CardTitle><AlertTriangle className="w-4 h-4" /> Выявленные проблемы</CardTitle>
            </CardHeader>
            <CardContent>
              {problems.map(p => (
                <div key={p.text} className={`py-1.5 text-sm ${p.type === 'err' ? 'text-red-400' : 'text-amber-400'}`}>
                  {p.type === 'err' ? '🔴' : '⚠️'} <b>{p.text.split(':')[0]}:</b>{p.text.substring(p.text.indexOf(':') + 1)}
                </div>
              ))}
            </CardContent>
          </Card>
        )
      })()}

      {/* Comparison Table */}
      {data && data.nodes.length > 0 && (() => {
        const rows = buildComparison(data.nodes)
        if (rows.length === 0) return null
        return (
          <Card className="rounded-xl">
            <CardHeader>
              <CardTitle><BarChart3 className="w-4 h-4" /> Сравнение нод</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr className="border-b border-white/5 text-dark-300 text-xs uppercase tracking-wider">
                    <th className="text-left py-2 px-2.5">Нода</th>
                    <th className="text-right py-2 px-2.5">Load</th>
                    <th className="text-right py-2 px-2.5">RAM</th>
                    <th className="text-right py-2 px-2.5">Disk</th>
                    <th className="text-right py-2 px-2.5">Speed</th>
                    <th className="text-right py-2 px-2.5">Retrans %</th>
                    <th className="text-right py-2 px-2.5">Timeouts</th>
                    <th className="text-right py-2 px-2.5">→ Москва</th>
                    <th className="text-right py-2 px-2.5">→ DE</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(r => (
                    <tr key={r.name} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-1.5 px-2.5 font-medium">{r.name}</td>
                      <td className={`py-1.5 px-2.5 text-right font-semibold ${LOAD_CLS(r.load)}`}>{r.load}</td>
                      <td className="py-1.5 px-2.5 text-right font-semibold">{r.ram}</td>
                      <td className={`py-1.5 px-2.5 text-right font-semibold ${DISK_CLS(r.diskPct)}`}>{r.diskPct}%</td>
                      <td className={`py-1.5 px-2.5 text-right font-semibold ${SPEED_CLS(r.speed)}`}>{r.speed ? r.speed + 'M' : '—'}</td>
                      <td className={`py-1.5 px-2.5 text-right font-semibold ${RETRANS_CLS(r.retrans)}`}>{r.retrans !== null ? r.retrans + '%' : '—'}</td>
                      <td className={`py-1.5 px-2.5 text-right font-semibold ${TIMEOUT_CLS(r.timeouts)}`}>{r.timeouts > 0 ? formatCount(r.timeouts) : '0'}</td>
                      <td className={`py-1.5 px-2.5 text-right font-semibold ${PING_CLS(r.yaMs)}`}>{r.yaMs !== null ? r.yaMs + 'ms' : '—'}</td>
                      <td className={`py-1.5 px-2.5 text-right font-semibold ${PING_CLS(r.deMs)}`}>{r.deMs !== null ? r.deMs + 'ms' : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )
      })()}

      {/* Toast */}
      {toast && (
        <div
          className="fixed bottom-8 right-8 px-4 py-3 rounded-xl backdrop-blur-md border border-white/10 z-50 text-sm animate-fade-in"
          style={{
            background: toast.type === 'ok' ? 'rgba(34,197,94,0.15)' :
                        toast.type === 'err' ? 'rgba(239,68,68,0.15)' :
                        'rgba(245,158,11,0.15)',
            color: toast.type === 'ok' ? '#22c55e' :
                   toast.type === 'err' ? '#ef4444' :
                   '#f59e0b',
          }}
        >
          {toast.msg}
        </div>
      )}
    </div>
  )
}