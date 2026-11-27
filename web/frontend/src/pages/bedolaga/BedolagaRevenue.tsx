import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import axios from 'axios'
import {
  AlertTriangle,
  CalendarDays,
  Download,
  Gift,
  Percent,
  Receipt,
  RefreshCw,
  TrendingUp,
  Users,
  Wallet,
  type LucideIcon,
} from 'lucide-react'
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  bedolagaApi,
  type BedolagaAnalyticsForecast,
  type BedolagaAnalyticsOverview,
  type BedolagaAnalyticsOverviewTariff,
  type BedolagaAnalyticsTariffs,
  type BedolagaAnalyticsWarning,
} from '@/api/bedolaga'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { EmptyState } from '@/components/EmptyState'
import { QueryError } from '@/components/QueryError'
import { useFormatters } from '@/lib/useFormatters'
import { cn } from '@/lib/utils'

const MONTHS_DEPTH = [6, 12] as const

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

function currentMonthKey(): string {
  const now = new Date()
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
}

function shiftMonthKey(month: string, delta: number): string {
  const [year, monthNumber] = month.split('-').map(Number)
  const date = new Date(year, monthNumber - 1 + delta, 1)
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`
}

function monthLabel(month: string, locale: string): string {
  const [year, monthNumber] = month.split('-').map(Number)
  if (!year || !monthNumber) return month
  return new Date(year, monthNumber - 1, 1).toLocaleDateString(locale, { month: 'long', year: 'numeric' })
}

function parseDay(value: string): Date {
  const [year, monthNumber, day] = value.split('-').map(Number)
  return new Date(year, (monthNumber || 1) - 1, day || 1)
}

function shortDay(value: string, locale: string): string {
  return parseDay(value).toLocaleDateString(locale, { day: '2-digit', month: '2-digit' })
}

function csvCell(value: string | number | null | undefined): string {
  const text = value == null ? '' : String(value)
  return `"${text.replace(/"/g, '""')}"`
}

function downloadCsv(filename: string, rows: Array<Array<string | number | null | undefined>>): void {
  const csv = `\uFEFF${rows.map((row) => row.map(csvCell).join(';')).join('\n')}`
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

type SortKey = 'clients' | 'revenue'
type SortDirection = 'asc' | 'desc'
type CalendarMode = 'day' | 'week'
type Basis = 'cash' | 'accrual'

interface WeekBucket {
  key: string
  start: string
  end: string
  expectedKopeks: number
  paymentsCount: number
}

export default function BedolagaRevenue() {
  const { t } = useTranslation()
  const { formatDate, formatNumber, locale } = useFormatters()

  const [month, setMonth] = useState(currentMonthKey())
  const [basis, setBasis] = useState<Basis>('cash')
  const [monthsDepth, setMonthsDepth] = useState<number>(6)
  const [sortKey, setSortKey] = useState<SortKey>('revenue')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [tariffFilter, setTariffFilter] = useState<string | null>(null)
  const [calendarMode, setCalendarMode] = useState<CalendarMode>('day')

  const forecastMonth = shiftMonthKey(month, 1)

  const overviewQuery = useQuery<BedolagaAnalyticsOverview>({
    queryKey: ['bedolaga-analytics-overview', month, basis, monthsDepth],
    queryFn: () => bedolagaApi.getAnalyticsOverview(month, basis, monthsDepth),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    retry: 1,
  })

  const forecastQuery = useQuery<BedolagaAnalyticsForecast>({
    queryKey: ['bedolaga-analytics-forecast', forecastMonth],
    queryFn: () => bedolagaApi.getAnalyticsForecast(forecastMonth, 'cash'),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    retry: 1,
  })

  // Каталог нужен только для флага is_active: overview.by_tariff его не отдаёт.
  const tariffsQuery = useQuery<BedolagaAnalyticsTariffs>({
    queryKey: ['bedolaga-analytics-tariffs'],
    queryFn: () => bedolagaApi.getAnalyticsTariffs(),
    staleTime: 60_000,
    retry: 1,
  })

  const overview = overviewQuery.data
  const forecast = forecastQuery.data
  const isFetching = overviewQuery.isFetching || forecastQuery.isFetching || tariffsQuery.isFetching

  const kpis = overview?.kpis
  const coverage = overview?.coverage
  const sources = overview?.sources

  const tariffsById = useMemo(() => {
    const map = new Map<number, boolean>()
    for (const item of tariffsQuery.data?.items ?? []) {
      if (item.tariff_id != null) map.set(item.tariff_id, item.is_active)
    }
    return map
  }, [tariffsQuery.data])

  const monthOptions = useMemo(() => {
    const current = currentMonthKey()
    const list = Array.from({ length: 14 }, (_, index) => shiftMonthKey(current, 2 - index))
    if (!list.includes(month)) list.push(month)
    return Array.from(new Set(list)).sort()
  }, [month])

  const rubles = (kopeks: number | null | undefined): string => {
    if (kopeks == null) return '—'
    return `${(kopeks / 100).toLocaleString(locale, { maximumFractionDigits: 2 })} ₽`
  }

  const percent = (value: number | null | undefined): string => {
    if (value == null) return '—'
    return `${value.toLocaleString(locale, { maximumFractionDigits: 1 })}%`
  }

  const rows = overview?.by_tariff ?? []

  const sortedRows = useMemo(() => {
    const filtered = tariffFilter ? rows.filter((row) => row.tariff_name === tariffFilter) : rows
    const value = (row: BedolagaAnalyticsOverviewTariff) =>
      sortKey === 'clients' ? row.clients_paid : row.mrr_kopeks
    return [...filtered].sort((left, right) => {
      const diff = value(left) - value(right)
      return sortDirection === 'asc' ? diff : -diff
    })
  }, [rows, tariffFilter, sortKey, sortDirection])

  const knownRows = sortedRows.filter((row) => row.tariff_id != null)
  const unknownRows = sortedRows.filter((row) => row.tariff_id == null)

  const displayedTotals = useMemo(() => {
    return sortedRows.reduce(
      (acc, row) => ({
        clientsPaid: acc.clientsPaid + row.clients_paid,
        clientsTrial: acc.clientsTrial + row.clients_trial,
        mrr: acc.mrr + row.mrr_kopeks,
        forward: acc.forward + row.paid_forward_kopeks,
        expected: acc.expected + row.next_month_expected_kopeks,
        unknownClients: acc.unknownClients + row.unknown_price_clients,
      }),
      { clientsPaid: 0, clientsTrial: 0, mrr: 0, forward: 0, expected: 0, unknownClients: 0 },
    )
  }, [sortedRows])

  const unknownPriceTariffs = useMemo(
    () =>
      rows.filter(
        (row) =>
          !row.is_free &&
          row.monthly_price_kopeks == null &&
          row.clients_paid + row.clients_trial > 0,
      ),
    [rows],
  )

  const warnings = useMemo(() => {
    const map = new Map<string, BedolagaAnalyticsWarning>()
    for (const warning of [...(overview?.warnings ?? []), ...(forecast?.warnings ?? [])]) {
      const key = `${warning.code}:${warning.message}`
      if (!map.has(key)) map.set(key, warning)
    }
    return Array.from(map.values())
  }, [overview, forecast])

  const warningText = (warning: BedolagaAnalyticsWarning): string => {
    const key = `bedolaga.revenue.warnings.${warning.code}`
    const translated = t(key)
    return translated === key ? warning.message : translated
  }

  const chartRows = useMemo(
    () =>
      (overview?.monthly ?? []).map((point) => ({
        month: point.month,
        label: monthLabel(point.month, locale),
        fact: point.cash_received_kopeks / 100,
        accrual: point.accrual_revenue_kopeks == null ? null : point.accrual_revenue_kopeks / 100,
        payments: point.payments_count,
      })),
    [overview, locale],
  )

  const weeks = useMemo<WeekBucket[]>(() => {
    const buckets = new Map<string, WeekBucket>()
    for (const day of forecast?.by_day ?? []) {
      const date = parseDay(day.date)
      const monday = new Date(date)
      monday.setDate(date.getDate() - ((date.getDay() + 6) % 7))
      const start = `${monday.getFullYear()}-${pad(monday.getMonth() + 1)}-${pad(monday.getDate())}`
      const sunday = new Date(monday)
      sunday.setDate(monday.getDate() + 6)
      const end = `${sunday.getFullYear()}-${pad(sunday.getMonth() + 1)}-${pad(sunday.getDate())}`
      const bucket = buckets.get(start) ?? {
        key: start,
        start,
        end,
        expectedKopeks: 0,
        paymentsCount: 0,
      }
      bucket.expectedKopeks += day.expected_kopeks
      bucket.paymentsCount += day.payments_count
      buckets.set(start, bucket)
    }
    return Array.from(buckets.values()).sort((left, right) => left.start.localeCompare(right.start))
  }, [forecast])

  const selectedMonthPoint = overview?.monthly.find((point) => point.month === overview.month)
  const selectedMonthPayments = selectedMonthPoint?.payments_count ?? 0

  const coveragePct =
    coverage?.price_coverage_pct ??
    (coverage && coverage.active_paid_subscriptions > 0
      ? (coverage.price_known_subscriptions / coverage.active_paid_subscriptions) * 100
      : 0)

  const sourcesLabel = (() => {
    const botDbOk = sources?.bot_db?.status === 'ok'
    const transactionsStatus = sources?.transactions?.status
    if (botDbOk) return { botDb: true, transactionsOnly: false, unknown: false }
    if (transactionsStatus === 'ok' || transactionsStatus === 'partial') {
      return { botDb: false, transactionsOnly: true, unknown: false }
    }
    return { botDb: false, transactionsOnly: false, unknown: true }
  })()

  const refreshAll = () => {
    overviewQuery.refetch()
    forecastQuery.refetch()
    tariffsQuery.refetch()
  }

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDirection('desc')
  }

  const exportCsv = () => {
    if (!overview) return
    const sourceNote = sourcesLabel.botDb
      ? `${t('bedolaga.revenue.source.botApi')} ${t('bedolaga.revenue.source.withBotDb')}`
      : sourcesLabel.transactionsOnly
        ? t('bedolaga.revenue.source.transactionsOnly')
        : t('bedolaga.revenue.source.unknown')

    const csvRows: Array<Array<string | number | null | undefined>> = [
      [t('bedolaga.revenue.csv.indicator'), t('bedolaga.revenue.csv.value')],
      [t('bedolaga.revenue.month'), month],
      [t('bedolaga.revenue.basis.label'), basis === 'cash' ? t('bedolaga.revenue.basis.cash') : t('bedolaga.revenue.basis.accrual')],
      [t('bedolaga.revenue.csv.source'), sourceNote],
      [t('bedolaga.revenue.kpi.mrr'), kpis ? (kpis.mrr_kopeks / 100).toFixed(2) : ''],
      [t('bedolaga.revenue.kpi.nextMonthExpected', { month: forecastMonth }), kpis ? (kpis.cash_forecast_next_month_kopeks / 100).toFixed(2) : ''],
      [t('bedolaga.revenue.kpi.paidForward'), kpis ? (kpis.paid_forward_kopeks / 100).toFixed(2) : ''],
      [t('bedolaga.revenue.kpi.cashMonth', { month }), kpis ? (kpis.cash_received_month_kopeks / 100).toFixed(2) : ''],
      [t('bedolaga.revenue.kpi.accrualMonth', { month }), kpis?.accrual_revenue_month_kopeks != null ? (kpis.accrual_revenue_month_kopeks / 100).toFixed(2) : ''],
      [t('bedolaga.revenue.kpi.activePaid'), coverage?.clients_with_paid ?? ''],
      [t('bedolaga.revenue.kpi.trial'), coverage?.trial_subscriptions ?? ''],
      [t('bedolaga.revenue.kpi.coverage'), percent(coveragePct)],
      [],
      [
        t('bedolaga.revenue.table.tariff'),
        t('bedolaga.revenue.table.clients'),
        t('bedolaga.revenue.table.price'),
        t('bedolaga.revenue.table.mrr'),
        t('bedolaga.revenue.table.forward'),
        t('bedolaga.revenue.table.expected', { month: forecastMonth }),
        t('bedolaga.revenue.table.share'),
        t('bedolaga.revenue.table.source'),
        t('bedolaga.revenue.table.unknownClients'),
      ],
      ...sortedRows.map((row) => [
        row.tariff_id == null ? t('bedolaga.revenue.table.unknownTariff') : row.tariff_name,
        `${row.clients_paid}/${row.clients_trial}`,
        row.monthly_price_kopeks == null ? '' : (row.monthly_price_kopeks / 100).toFixed(2),
        (row.mrr_kopeks / 100).toFixed(2),
        (row.paid_forward_kopeks / 100).toFixed(2),
        (row.next_month_expected_kopeks / 100).toFixed(2),
        row.share_pct,
        row.price_source,
        row.unknown_price_clients,
      ]),
      [
        t('bedolaga.revenue.table.totals'),
        `${displayedTotals.clientsPaid}/${displayedTotals.clientsTrial}`,
        '',
        (displayedTotals.mrr / 100).toFixed(2),
        (displayedTotals.forward / 100).toFixed(2),
        (displayedTotals.expected / 100).toFixed(2),
        '',
        '',
        displayedTotals.unknownClients,
      ],
    ]

    downloadCsv(`bedolaga_revenue_${month}_${basis}.csv`, csvRows)
  }

  const isNotConfigured =
    overviewQuery.isError &&
    axios.isAxiosError(overviewQuery.error) &&
    overviewQuery.error.response?.status === 503

  const header = (
    <div className="page-header">
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="page-header-title">{t('bedolaga.revenue.title')}</h1>
          <Badge variant="outline" className="text-[10px]">{t('bedolaga.revenue.source.botApi')}</Badge>
          {overview && sourcesLabel.botDb && (
            <Badge variant="success" className="text-[10px]">{t('bedolaga.revenue.source.withBotDb')}</Badge>
          )}
          {overview && sourcesLabel.transactionsOnly && (
            <Badge variant="warning" className="text-[10px]">{t('bedolaga.revenue.source.transactionsOnly')}</Badge>
          )}
          {overview && sourcesLabel.unknown && (
            <Badge variant="secondary" className="text-[10px]">{t('bedolaga.revenue.source.unknown')}</Badge>
          )}
        </div>
        <p className="text-dark-200 mt-1 text-sm">
          {t('bedolaga.revenue.subtitle', { time: overview ? formatDate(overview.generated_at) : '—' })}
        </p>
      </div>
      <div className="page-header-actions">
        <Button variant="secondary" size="sm" onClick={exportCsv} disabled={!overview} className="gap-1.5">
          <Download className="w-4 h-4" />
          {t('bedolaga.revenue.exportCsv')}
        </Button>
        <Button
          variant="secondary"
          size="icon"
          onClick={refreshAll}
          disabled={isFetching}
          aria-label={t('bedolaga.revenue.refresh')}
        >
          <RefreshCw className={cn('w-5 h-5', isFetching && 'animate-spin')} />
        </Button>
      </div>
    </div>
  )

  if (isNotConfigured) {
    return (
      <div className="space-y-4 md:space-y-6">
        {header}
        <Card className="glass-card">
          <CardContent className="p-8 text-center">
            <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
            <h2 className="text-lg font-semibold mb-2">{t('bedolaga.revenue.empty.notConfigured')}</h2>
            <p className="text-dark-300 text-sm max-w-md mx-auto mb-4">
              {t('bedolaga.revenue.empty.notConfiguredDesc')}
            </p>
            <Link to="/settings?tab=integrations&from=bedolaga">
              <Button variant="secondary" size="sm">{t('bedolaga.revenue.empty.goSettings')}</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4 md:space-y-6">
      {header}

      {/* Controls */}
      <Card className="glass-card">
        <CardContent className="p-3 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-dark-300 uppercase tracking-wider">{t('bedolaga.revenue.month')}</span>
            <Select value={month} onValueChange={(value) => { setMonth(value); setTariffFilter(null) }}>
              <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
              <SelectContent>
                {monthOptions.map((option) => (
                  <SelectItem key={option} value={option}>{monthLabel(option, locale)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-dark-300 uppercase tracking-wider">{t('bedolaga.revenue.depth')}</span>
            <Select value={String(monthsDepth)} onValueChange={(value) => setMonthsDepth(Number(value))}>
              <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
              <SelectContent>
                {MONTHS_DEPTH.map((option) => (
                  <SelectItem key={option} value={String(option)}>
                    {t('bedolaga.revenue.months', { count: option })}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-dark-300 uppercase tracking-wider">{t('bedolaga.revenue.basis.label')}</span>
            <div className="flex items-center gap-1 rounded-lg border border-[var(--glass-border)] p-1">
              <Button
                size="sm"
                variant={basis === 'cash' ? 'default' : 'ghost'}
                className="h-7"
                onClick={() => setBasis('cash')}
              >
                {t('bedolaga.revenue.basis.cash')}
              </Button>
              <Button
                size="sm"
                variant={basis === 'accrual' ? 'default' : 'ghost'}
                className="h-7"
                onClick={() => setBasis('accrual')}
              >
                {t('bedolaga.revenue.basis.accrual')}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Warnings */}
      {(overview?.partial || forecast?.partial) && (
        <Banner tone="amber" icon={AlertTriangle} text={t('bedolaga.revenue.warnings.partial')} />
      )}
      {warnings.map((warning) => (
        <Banner
          key={`${warning.code}:${warning.message}`}
          tone="amber"
          icon={AlertTriangle}
          text={warningText(warning)}
        />
      ))}
      {coverage &&
        coverage.active_paid_subscriptions > 0 &&
        coverage.price_known_subscriptions === 0 && (
          <Banner
            tone="amber"
            icon={AlertTriangle}
            text={`${t('bedolaga.revenue.empty.noMoney')}. ${t('bedolaga.revenue.empty.noMoneyDesc')}`}
          />
        )}

      {overviewQuery.isError && !overview && (
        <QueryError
          message={overviewQuery.error instanceof Error ? overviewQuery.error.message : String(overviewQuery.error)}
          onRetry={() => overviewQuery.refetch()}
        />
      )}

      {overviewQuery.isPending && !overview ? (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, index) => (
              <Skeleton key={index} className="h-24 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-64 rounded-xl" />
        </>
      ) : overview ? (
        <>
          {/* KPI */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KpiCard
              icon={TrendingUp}
              label={t('bedolaga.revenue.kpi.mrr')}
              value={rubles(kpis?.mrr_kopeks)}
              hint={
                kpis?.mrr_is_lower_bound
                  ? t('bedolaga.revenue.kpi.mrrLowerBound')
                  : t('bedolaga.revenue.kpi.mrrBasis', {
                      basis: t(`bedolaga.revenue.kpi.mrrBasisValue.${kpis?.mrr_basis ?? 'unknown'}`, {
                        defaultValue: kpis?.mrr_basis ?? '—',
                      }),
                    })
              }
              tone="text-emerald-400"
            />
            <KpiCard
              icon={CalendarDays}
              label={t('bedolaga.revenue.kpi.nextMonthExpected', { month: monthLabel(forecastMonth, locale) })}
              value={rubles(kpis?.cash_forecast_next_month_kopeks)}
              hint={
                forecast
                  ? t('bedolaga.revenue.kpi.payments', { count: forecast.totals.payments_count })
                  : t('bedolaga.revenue.kpi.unknownPayments', { count: kpis?.cash_forecast_unknown_count ?? 0 })
              }
              tone="text-blue-400"
            />
            <KpiCard
              icon={Wallet}
              label={t('bedolaga.revenue.kpi.paidForward')}
              value={rubles(kpis?.paid_forward_kopeks)}
              hint={t('bedolaga.revenue.kpi.paidForwardHint')}
              tone="text-violet-400"
            />
            <KpiCard
              icon={Receipt}
              label={
                basis === 'accrual'
                  ? t('bedolaga.revenue.kpi.accrualMonth', { month: monthLabel(month, locale) })
                  : t('bedolaga.revenue.kpi.cashMonth', { month: monthLabel(month, locale) })
              }
              value={
                rubles(
                  basis === 'accrual'
                    ? kpis?.accrual_revenue_month_kopeks
                    : kpis?.cash_received_month_kopeks,
                )
              }
              hint={t('bedolaga.revenue.kpi.monthHint', { count: selectedMonthPayments })}
              tone="text-amber-400"
            />
            <KpiCard
              icon={Users}
              label={t('bedolaga.revenue.kpi.activePaid')}
              value={formatNumber(kpis?.active_paid_clients ?? 0)}
              hint={t('bedolaga.revenue.kpi.activePaidHint', {
                subscriptions: kpis?.active_paid_subscriptions ?? 0,
              })}
              tone="text-cyan-400"
            />
            <KpiCard
              icon={Gift}
              label={t('bedolaga.revenue.kpi.trial')}
              value={formatNumber(coverage?.trial_subscriptions ?? 0)}
              hint={t('bedolaga.revenue.kpi.trialHint')}
              tone="text-pink-400"
            />
            <KpiCard
              icon={Percent}
              label={t('bedolaga.revenue.kpi.coverage')}
              value={percent(coveragePct)}
              hint={t('bedolaga.revenue.kpi.coverageHint', {
                known: coverage?.price_known_subscriptions ?? 0,
                total: coverage?.active_paid_subscriptions ?? 0,
              })}
              tone="text-emerald-400"
            />
          </div>

          {/* Coverage */}
          <Card className="glass-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Percent className="w-4 h-4 text-emerald-400" />
                {t('bedolaga.revenue.coverage.title')}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0 space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 rounded-full bg-dark-600 overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 transition-all"
                    style={{ width: `${Math.max(0, Math.min(100, coveragePct))}%` }}
                  />
                </div>
                <span className="text-sm font-semibold tabular-nums">{percent(coveragePct)}</span>
              </div>
              <p className="text-xs text-dark-300">
                {t('bedolaga.revenue.coverage.knownOf', {
                  known: coverage?.price_known_subscriptions ?? 0,
                  total: coverage?.active_paid_subscriptions ?? 0,
                })}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                {unknownPriceTariffs.length === 0 ? (
                  <span className="text-xs text-dark-400">{t('bedolaga.revenue.coverage.allKnown')}</span>
                ) : (
                  <>
                    <span className="text-xs text-dark-400">{t('bedolaga.revenue.coverage.unknownTariffs')}:</span>
                    {unknownPriceTariffs.map((row) => (
                      <button
                        key={`${row.tariff_id ?? 'unknown'}-${row.tariff_name}`}
                        type="button"
                        onClick={() => setTariffFilter(row.tariff_name)}
                        className={cn(
                          'text-[11px] px-2 py-0.5 rounded-md border transition-colors',
                          tariffFilter === row.tariff_name
                            ? 'border-amber-500/40 bg-amber-500/15 text-amber-300'
                            : 'border-[var(--glass-border)] bg-[var(--glass-bg)] text-dark-200 hover:border-[var(--glass-border-hover)]',
                        )}
                      >
                        {row.tariff_name}
                      </button>
                    ))}
                  </>
                )}
                {tariffFilter && (
                  <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setTariffFilter(null)}>
                    {t('bedolaga.revenue.coverage.clearFilter')}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Tariff table */}
          <Card className="glass-card">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                  {t('bedolaga.revenue.table.title')}
                  {tariffFilter && (
                    <span className="text-xs font-normal text-dark-300">
                      {t('bedolaga.revenue.coverage.filtered', { name: tariffFilter })}
                    </span>
                  )}
                </CardTitle>
                <div className="flex items-center gap-1">
                  <Button
                    variant={sortKey === 'clients' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => toggleSort('clients')}
                  >
                    {t('bedolaga.revenue.table.sortClients')} {sortKey === 'clients' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                  </Button>
                  <Button
                    variant={sortKey === 'revenue' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => toggleSort('revenue')}
                  >
                    {t('bedolaga.revenue.table.sortRevenue')} {sortKey === 'revenue' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0 space-y-3">
              {selectedMonthPayments === 0 && (
                <div className="rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] px-4 py-3 text-sm text-dark-200">
                  <span className="font-medium">{t('bedolaga.revenue.empty.noPayments')}.</span>{' '}
                  <span className="text-dark-300">{t('bedolaga.revenue.empty.noPaymentsDesc')}</span>
                </div>
              )}

              {sortedRows.length === 0 ? (
                <EmptyState title={t('bedolaga.revenue.table.noRows')} />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('bedolaga.revenue.table.tariff')}</TableHead>
                      <TableHead title={t('bedolaga.revenue.table.clientsHint')}>{t('bedolaga.revenue.table.clients')}</TableHead>
                      <TableHead className="text-right">{t('bedolaga.revenue.table.price')}</TableHead>
                      <TableHead className="text-right">{t('bedolaga.revenue.table.mrr')}</TableHead>
                      <TableHead className="text-right">{t('bedolaga.revenue.table.forward')}</TableHead>
                      <TableHead className="text-right">
                        {t('bedolaga.revenue.table.expected', { month: monthLabel(forecastMonth, locale) })}
                      </TableHead>
                      <TableHead className="text-right">{t('bedolaga.revenue.table.share')}</TableHead>
                      <TableHead>{t('bedolaga.revenue.table.source')}</TableHead>
                      <TableHead className="text-right">{t('bedolaga.revenue.table.unknownClients')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {knownRows.map((row) => (
                      <TariffRow
                        key={`${row.tariff_id}-${row.tariff_name}`}
                        row={row}
                        active={tariffsById.get(row.tariff_id as number)}
                        rubles={rubles}
                        percent={percent}
                      />
                    ))}
                    {unknownRows.map((row) => (
                      <TariffRow
                        key={`unknown-${row.tariff_name}`}
                        row={row}
                        rubles={rubles}
                        percent={percent}
                        muted
                        unknown
                      />
                    ))}
                  </TableBody>
                  <TableFooter>
                    <TableRow>
                      <TableCell>{t('bedolaga.revenue.table.totals')}</TableCell>
                      <TableCell className="tabular-nums">
                        {displayedTotals.clientsPaid} / {displayedTotals.clientsTrial}
                      </TableCell>
                      <TableCell className="text-right text-dark-400">—</TableCell>
                      <TableCell className="text-right tabular-nums">{rubles(displayedTotals.mrr)}</TableCell>
                      <TableCell className="text-right tabular-nums">{rubles(displayedTotals.forward)}</TableCell>
                      <TableCell className="text-right tabular-nums">{rubles(displayedTotals.expected)}</TableCell>
                      <TableCell className="text-right text-dark-400">—</TableCell>
                      <TableCell className="text-dark-400">—</TableCell>
                      <TableCell className="text-right tabular-nums">{displayedTotals.unknownClients || '—'}</TableCell>
                    </TableRow>
                  </TableFooter>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Chart */}
          <Card className="glass-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-400" />
                {t('bedolaga.revenue.chart.title')}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0 space-y-4">
              {chartRows.length === 0 ? (
                <EmptyState title={t('bedolaga.revenue.chart.empty')} />
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={300}>
                    <ComposedChart data={chartRows}>
                      <CartesianGrid stroke="rgba(148,163,184,0.08)" strokeDasharray="3 3" />
                      <XAxis dataKey="label" stroke="rgba(148,163,184,0.3)" fontSize={11} />
                      <YAxis
                        stroke="rgba(148,163,184,0.3)"
                        fontSize={10}
                        tick={{ fill: 'rgba(148,163,184,0.5)' }}
                        tickFormatter={(value) => (Number(value) >= 1000 ? `${Math.round(Number(value) / 1000)}k` : String(value))}
                      />
                      <RechartsTooltip
                        contentStyle={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                        formatter={(value) => `${Number(value).toLocaleString(locale, { maximumFractionDigits: 2 })} ₽`}
                      />
                      <Legend />
                      <Bar dataKey="fact" name={t('bedolaga.revenue.chart.fact')} fill="#22c55e" radius={[4, 4, 0, 0]} maxBarSize={42} />
                      <Line
                        type="monotone"
                        dataKey="accrual"
                        name={t('bedolaga.revenue.chart.accrual')}
                        stroke="#38bdf8"
                        strokeWidth={2}
                        dot={{ r: 2 }}
                        connectNulls={false}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>

                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('bedolaga.revenue.chart.month')}</TableHead>
                        <TableHead className="text-right">{t('bedolaga.revenue.chart.cash')}</TableHead>
                        <TableHead className="text-right">{t('bedolaga.revenue.chart.count')}</TableHead>
                        <TableHead className="text-right">{t('bedolaga.revenue.chart.accrualShort')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {chartRows.map((row) => (
                        <TableRow key={row.month}>
                          <TableCell className="text-dark-200">{row.label}</TableCell>
                          <TableCell className="text-right tabular-nums">{rubles(row.fact * 100)}</TableCell>
                          <TableCell className="text-right tabular-nums">{row.payments}</TableCell>
                          <TableCell className="text-right tabular-nums">
                            {row.accrual == null ? '—' : rubles(row.accrual * 100)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </>
              )}
            </CardContent>
          </Card>

          {/* Forecast calendar */}
          <Card className="glass-card">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <CalendarDays className="w-4 h-4 text-amber-400" />
                  {t('bedolaga.revenue.forecast.title', { month: monthLabel(forecastMonth, locale) })}
                  <span className="text-xs font-normal text-dark-300">{t('bedolaga.revenue.forecast.basisCash')}</span>
                </CardTitle>
                <div className="flex items-center gap-1">
                  <Button
                    variant={calendarMode === 'day' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => setCalendarMode('day')}
                  >
                    {t('bedolaga.revenue.forecast.day')}
                  </Button>
                  <Button
                    variant={calendarMode === 'week' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => setCalendarMode('week')}
                  >
                    {t('bedolaga.revenue.forecast.week')}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0 space-y-4">
              {forecastQuery.isError && !forecast && (
                <QueryError
                  message={t('bedolaga.revenue.forecast.error')}
                  onRetry={() => forecastQuery.refetch()}
                />
              )}

              {forecastQuery.isPending && !forecast ? (
                <Skeleton className="h-40 rounded-xl" />
              ) : forecast ? (
                forecast.totals.payments_count === 0 ? (
                  <EmptyState
                    icon={CalendarDays}
                    title={t('bedolaga.revenue.forecast.empty')}
                    description={t('bedolaga.revenue.forecast.daysTotal', {
                      count: 0,
                      sum: rubles(forecast.totals.expected_kopeks),
                    })}
                  />
                ) : (
                  <>
                    <p className="text-xs text-dark-300">
                      {t('bedolaga.revenue.forecast.daysTotal', {
                        count: forecast.totals.payments_count,
                        sum: rubles(forecast.totals.expected_kopeks),
                      })}
                      {forecast.totals.unknown_count > 0 && (
                        <span className="text-amber-400 ml-2">
                          {t('bedolaga.revenue.kpi.unknownPayments', { count: forecast.totals.unknown_count })}
                        </span>
                      )}
                    </p>

                    {calendarMode === 'day' ? (
                      <div className="grid grid-cols-3 sm:grid-cols-7 gap-1.5">
                        {forecast.by_day.map((day) => (
                          <div
                            key={day.date}
                            className={cn(
                              'rounded-lg border p-2 min-h-[66px]',
                              day.payments_count > 0
                                ? 'border-[var(--glass-border-hover)] bg-[var(--glass-bg)]'
                                : 'border-[var(--glass-border)] bg-transparent',
                            )}
                          >
                            <div className="text-[10px] text-dark-400">{parseDay(day.date).getDate()}</div>
                            <div className={cn('text-xs font-medium tabular-nums', day.payments_count > 0 ? 'text-dark-100' : 'text-dark-500')}>
                              {day.payments_count > 0 ? rubles(day.expected_kopeks) : '—'}
                            </div>
                            {day.payments_count > 0 && (
                              <div className="text-[10px] text-dark-400">
                                {day.payments_count} {t('bedolaga.revenue.forecast.paymentsUnit')}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                        {weeks.map((week) => (
                          <div
                            key={week.key}
                            className={cn(
                              'rounded-lg border px-3 py-2',
                              week.paymentsCount > 0
                                ? 'border-[var(--glass-border-hover)] bg-[var(--glass-bg)]'
                                : 'border-[var(--glass-border)] bg-transparent',
                            )}
                          >
                            <div className="text-[10px] text-dark-400">
                              {shortDay(week.start, locale)} – {shortDay(week.end, locale)}
                            </div>
                            <div className="flex items-center justify-between gap-2">
                              <span className={cn('text-sm font-semibold tabular-nums', week.paymentsCount > 0 ? 'text-dark-100' : 'text-dark-500')}>
                                {week.paymentsCount > 0 ? rubles(week.expectedKopeks) : '—'}
                              </span>
                              <span className="text-[11px] text-dark-400">
                                {week.paymentsCount} {t('bedolaga.revenue.forecast.paymentsUnit')}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {forecast.items.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-[10px] text-dark-400 uppercase tracking-wider">
                          {t('bedolaga.revenue.forecast.top')}
                        </p>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>{t('bedolaga.revenue.forecast.date')}</TableHead>
                              <TableHead>{t('bedolaga.revenue.forecast.client')}</TableHead>
                              <TableHead>{t('bedolaga.revenue.forecast.tariff')}</TableHead>
                              <TableHead className="text-right">{t('bedolaga.revenue.forecast.amount')}</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {forecast.items.slice(0, 50).map((item, index) => (
                              <TableRow key={`${item.user_id}-${item.subscription_id}-${index}`}>
                                <TableCell className="text-dark-200 whitespace-nowrap">
                                  {item.expected_charge_date ? shortDay(item.expected_charge_date, locale) : '—'}
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    {item.user_id != null ? (
                                      <Link
                                        to={`/bedolaga/customers/${item.user_id}`}
                                        className="text-primary-400 hover:underline"
                                      >
                                        {item.username || `#${item.user_id}`}
                                      </Link>
                                    ) : (
                                      <span>{item.username || '—'}</span>
                                    )}
                                    {item.autopay_enabled && (
                                      <Badge variant="secondary" className="text-[10px]">
                                        {t('bedolaga.revenue.forecast.autopay')}
                                      </Badge>
                                    )}
                                  </div>
                                </TableCell>
                                <TableCell className="text-dark-300">{item.tariff_name}</TableCell>
                                <TableCell className="text-right tabular-nums">
                                  {item.price_known ? rubles(item.amount_kopeks) : '—'}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    )}
                  </>
                )
              ) : null}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  )
}

function KpiCard({
  icon: Icon,
  label,
  value,
  hint,
  tone,
}: {
  icon: LucideIcon
  label: string
  value: string
  hint?: string
  tone?: string
}) {
  return (
    <Card className="glass-card">
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[10px] sm:text-xs text-dark-300 uppercase tracking-wider truncate">{label}</p>
            <p className="text-lg sm:text-xl font-bold mt-0.5 truncate tabular-nums">{value}</p>
            {hint && <p className="text-[10px] text-dark-400 mt-0.5">{hint}</p>}
          </div>
          <div className={cn('p-2 rounded-lg bg-[var(--glass-bg)] flex-shrink-0', tone)}>
            <Icon className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function Banner({
  icon: Icon,
  text,
  tone,
}: {
  icon: LucideIcon
  text: string
  tone: 'amber' | 'red'
}) {
  return (
    <div
      className={cn(
        'rounded-lg border px-4 py-3 text-sm flex items-start gap-3',
        tone === 'amber'
          ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
          : 'border-red-500/30 bg-red-500/10 text-red-300',
      )}
    >
      <Icon className="w-4 h-4 shrink-0 mt-0.5" />
      <span>{text}</span>
    </div>
  )
}

function TariffRow({
  row,
  active,
  rubles,
  percent,
  muted,
  unknown,
}: {
  row: BedolagaAnalyticsOverviewTariff
  active?: boolean
  rubles: (kopeks: number | null | undefined) => string
  percent: (value: number | null | undefined) => string
  muted?: boolean
  unknown?: boolean
}) {
  const { t } = useTranslation()
  const priceSource = row.price_source || 'unknown'
  const sourceVariant =
    priceSource === 'bot_db'
      ? 'success'
      : priceSource === 'transactions'
        ? 'default'
        : priceSource === 'manual'
          ? 'warning'
          : 'secondary'

  return (
    <TableRow className={cn(muted && 'bg-[var(--glass-bg)]/40')}>
      <TableCell>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={cn('font-medium', muted ? 'text-dark-300' : 'text-dark-100')}>
            {unknown ? t('bedolaga.revenue.table.unknownTariff') : row.tariff_name}
          </span>
          {!unknown && row.is_free && (
            <Badge variant="secondary" className="text-[10px]">{t('bedolaga.revenue.table.free')}</Badge>
          )}
          {!unknown && active === false && (
            <Badge variant="secondary" className="text-[10px]">{t('bedolaga.revenue.table.inactive')}</Badge>
          )}
        </div>
      </TableCell>
      <TableCell className="tabular-nums whitespace-nowrap">
        <span className="text-dark-100">{row.clients_paid}</span>
        <span className="text-dark-500"> / {row.clients_trial}</span>
      </TableCell>
      <TableCell className="text-right tabular-nums whitespace-nowrap">
        {unknown ? (
          <span className="text-dark-400">—</span>
        ) : row.is_free ? (
          <span className="text-emerald-400">{t('bedolaga.revenue.table.free')} · 0 ₽</span>
        ) : row.monthly_price_kopeks == null ? (
          <span className="text-dark-400">—</span>
        ) : (
          rubles(row.monthly_price_kopeks)
        )}
      </TableCell>
      <TableCell className="text-right tabular-nums whitespace-nowrap">{rubles(row.mrr_kopeks)}</TableCell>
      <TableCell className="text-right tabular-nums whitespace-nowrap">{rubles(row.paid_forward_kopeks)}</TableCell>
      <TableCell className="text-right tabular-nums whitespace-nowrap">{rubles(row.next_month_expected_kopeks)}</TableCell>
      <TableCell className="text-right tabular-nums">{percent(row.share_pct)}</TableCell>
      <TableCell>
        <Badge variant={sourceVariant} className="text-[10px]">
          {t(`bedolaga.revenue.priceSource.${priceSource}`, { defaultValue: priceSource })}
        </Badge>
      </TableCell>
      <TableCell className="text-right tabular-nums">
        {row.unknown_price_clients > 0 ? (
          <span className="text-amber-400">{row.unknown_price_clients}</span>
        ) : (
          <span className="text-dark-500">—</span>
        )}
      </TableCell>
    </TableRow>
  )
}
