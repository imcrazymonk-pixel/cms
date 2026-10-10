import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  RefreshCw,
  Server,
  Smartphone,
  HardDrive,
  Ticket,
  Gift,
  BadgeCheck,
  Clock,
  Search,
} from 'lucide-react'
import client from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface Tariff {
  id: number
  name: string
  description?: string | null
  is_active: boolean
  is_trial_available: boolean
  is_highlighted: boolean
  display_order: number
  traffic_limit_gb: number
  device_limit: number
  device_price_kopeks?: number | null
  max_device_limit?: number | null
  tier_level: number
  period_prices_list?: Array<{ days: number; price_kopeks: number; price_rubles: number }>
  is_daily: boolean
  daily_price_kopeks: number
  custom_days_enabled: boolean
  price_per_day_kopeks: number
  min_days: number
  max_days: number
  custom_traffic_enabled: boolean
  traffic_price_per_gb_kopeks: number
  min_traffic_gb: number
  max_traffic_gb: number
  allow_traffic_topup: boolean
  show_in_gift: boolean
  trial_duration_days?: number | null
  panel_tag?: string | null
  external_squad_uuid?: string | null
  lava_product_id?: string | null
  subscriptions_count?: number
  servers_count?: number
}

function rubles(kopeks?: number): string {
  if (kopeks == null) return '—'
  return `${(kopeks / 100).toLocaleString('ru-RU')} ₽`
}

function formatTraffic(gb: number): string {
  return gb === 0 ? '∞' : `${gb} GB`
}

export default function BedolagaTariffs() {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(false)

  const { data, isLoading, refetch } = useQuery<{ items?: Tariff[]; total?: number }>({
    queryKey: ['bedolaga-tariffs', showInactive],
    queryFn: () => client.get('/bedolaga/tariffs').then((r) => r.data),
    staleTime: 60_000,
  })

  const tariffs: Tariff[] = Array.isArray(data?.items) ? data.items : []
  const filtered = tariffs.filter((tariff) => {
    if (!showInactive && !tariff.is_active) return false
    if (search) {
      const q = search.toLowerCase()
      const haystack = `${tariff.name} ${tariff.description || ''} ${tariff.panel_tag || ''}`.toLowerCase()
      return haystack.includes(q)
    }
    return true
  })

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-header-title">{t('bedolaga.tariffs.title')}</h1>
          <p className="text-dark-200 mt-1 text-sm">
            {t('bedolaga.tariffs.subtitle')}
            <span className="text-dark-300 ml-1">({tariffs.length})</span>
          </p>
        </div>
        <div className="page-header-actions">
          <Button
            variant={showInactive ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setShowInactive(!showInactive)}
            className="gap-1.5"
          >
            <BadgeCheck className="w-4 h-4" />
            {t('bedolaga.tariffs.showInactive')}
          </Button>
          <Button variant="secondary" size="icon" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={cn('w-5 h-5', isLoading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-300" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('bedolaga.tariffs.searchPlaceholder')}
          className="w-full h-10 pl-10 pr-4 rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] text-sm placeholder:text-dark-300 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
        />
      </div>

      {/* Tariff cards */}
      {isLoading && !tariffs.length ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-64 rounded-xl" />)}
        </div>
      ) : filtered.length === 0 ? (
        <Card className="glass-card">
          <CardContent className="p-8 text-center text-dark-300">
            <Ticket className="w-8 h-8 mx-auto mb-2 opacity-40" />
            {t('bedolaga.tariffs.noResults')}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((tariff) => (
            <Card key={tariff.id} className={cn('glass-card transition-all hover:border-[var(--glass-border-hover)]', tariff.is_highlighted && 'ring-2 ring-primary-500/30')}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-base font-semibold truncate">{tariff.name}</span>
                    {tariff.panel_tag && <code className="text-[10px] text-primary-400 font-mono">{tariff.panel_tag}</code>}
                  </div>
                  <Badge className={cn('text-[10px] flex-shrink-0',
                    tariff.is_highlighted ? 'bg-primary-500/20 text-primary-400 border-primary-500/30' :
                    tariff.is_active ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
                    'bg-dark-500/20 text-dark-300 border-dark-500/30'
                  )}>
                    {tariff.is_highlighted ? '★' : tariff.is_active ? t('bedolaga.tariffs.active') : t('bedolaga.tariffs.inactive')}
                  </Badge>
                </CardTitle>
                {tariff.description && (
                  <p className="text-xs text-dark-300 mt-1 line-clamp-2">{tariff.description}</p>
                )}
              </CardHeader>
              <CardContent className="pt-0 space-y-2.5">
                {/* Period prices */}
                <div className="flex flex-wrap gap-1.5">
                  {(tariff.period_prices_list || []).map((pp) => (
                    <span key={pp.days} className={cn(
                      'px-2 py-1 rounded-md text-[11px] font-semibold border',
                      tariff.is_highlighted && pp.days === 30 ? 'border-primary-500/40 bg-primary-500/15 text-primary-300' :
                      'border-[var(--glass-border)] bg-[var(--glass-bg)] text-dark-200'
                    )}>
                      {pp.days}д · {rubles(pp.price_kopeks)}
                    </span>
                  ))}
                  {tariff.custom_days_enabled && (
                    <span className="px-2 py-1 rounded-md text-[11px] border border-[var(--glass-border)] bg-[var(--glass-bg)] text-dark-200">
                      {tariff.min_days}-{tariff.max_days}д · {rubles(tariff.price_per_day_kopeks)}/день
                    </span>
                  )}
                  {tariff.is_daily && (
                    <span className="px-2 py-1 rounded-md text-[11px] border border-amber-500/30 bg-amber-500/10 text-amber-300">
                      День · {rubles(tariff.daily_price_kopeks)}
                    </span>
                  )}
                  {!tariff.period_prices_list?.length && !tariff.custom_days_enabled && !tariff.is_daily && (
                    <span className="text-[11px] text-dark-400">—</span>
                  )}
                </div>

                {/* Stats row */}
                <div className="flex items-center gap-3 text-xs text-dark-200">
                  <span className="flex items-center gap-1">
                    <HardDrive className="w-3.5 h-3.5" />{formatTraffic(tariff.traffic_limit_gb)}
                  </span>
                  <span className="flex items-center gap-1">
                    <Smartphone className="w-3.5 h-3.5" />{tariff.device_limit} {t('bedolaga.tariffs.devices')}
                  </span>
                  <span className="flex items-center gap-1">
                    <Server className="w-3.5 h-3.5" />T{tariff.tier_level}
                  </span>
                </div>

                {/* Trial / gift / topup flags */}
                <div className="flex flex-wrap gap-1.5">
                  {tariff.is_trial_available && (
                    <Badge className="text-[10px] bg-blue-500/20 text-blue-400 border-blue-500/30">
                      {t('bedolaga.tariffs.trial')}{tariff.trial_duration_days ? ` ${tariff.trial_duration_days}д` : ''}
                    </Badge>
                  )}
                  {tariff.show_in_gift && (
                    <Badge className="text-[10px] bg-pink-500/20 text-pink-400 border-pink-500/30">
                      <Gift className="w-3 h-3" /> {t('bedolaga.tariffs.gift')}
                    </Badge>
                  )}
                  {tariff.allow_traffic_topup && (
                    <Badge className="text-[10px] bg-[var(--glass-bg-hover)] text-dark-200">
                      {t('bedolaga.tariffs.topup')}
                    </Badge>
                  )}
                  {tariff.lava_product_id && (
                    <Badge className="text-[10px] bg-[var(--glass-bg-hover)] text-dark-200 font-mono">
                      Lava:{tariff.lava_product_id}
                    </Badge>
                  )}
                </div>

                {tariff.external_squad_uuid && (
                  <p className="text-[10px] text-dark-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {t('bedolaga.tariffs.externalSquad')}: <code className="font-mono truncate">{tariff.external_squad_uuid.slice(0, 8)}…</code>
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}