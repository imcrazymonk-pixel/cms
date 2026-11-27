import { useQuery } from '@tanstack/react-query'
import { ExternalLink, Gauge, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

import backupsApi from '../../api/backups'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Skeleton } from '../../components/ui/skeleton'

const formatDate = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const formatBytes = (value?: number | null) => {
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = value
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size.toFixed(1)} ${units[unit]}`
}

export default function InfrastructurePanel() {
  const overview = useQuery({ queryKey: ['backups', 'overview'], queryFn: backupsApi.overview, refetchInterval: 60000 })
  const hosts = useQuery({ queryKey: ['backups', 'hosts'], queryFn: backupsApi.hosts })

  if (overview.isLoading || hosts.isLoading) return <Skeleton className="h-64 w-full" />

  const panelHosts = (hosts.data ?? []).filter((host) => host.role === 'server')
  const data = overview.data

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Панель Remnawave</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            control-plane · Remnawave 3.4.3 · источник данных — агент бэкапа и инвентарь
          </p>
        </div>
        <a href="https://panel.fortf.ru" target="_blank" rel="noreferrer">
          <Button variant="secondary">
            <ExternalLink className="mr-2 h-4 w-4" /> Открыть панель
          </Button>
        </a>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card className="glass-card">
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Серверы панели</div>
            <div className="mt-1 text-2xl font-semibold">{panelHosts.length}</div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Агенты online</div>
            <div className="mt-1 text-2xl font-semibold">{data?.agents_online ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Последний бэкап</div>
            <div className="mt-1 text-lg font-semibold">{formatDate(data?.last_success_at)}</div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Объём копий</div>
            <div className="mt-1 text-2xl font-semibold">{formatBytes(data?.total_bytes)}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="glass-card">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Gauge className="h-4 w-4" /> Состояние
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span>Доступность агентов</span>
              <Badge variant={data?.agents_offline ? 'destructive' : 'default'}>
                {data?.agents_online ?? 0} online · {data?.agents_offline ?? 0} offline
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Хранилища</span>
              <Badge variant={data?.storages_error ? 'destructive' : 'secondary'}>
                {data?.storages_total ?? 0} · ошибок {data?.storages_error ?? 0}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Политики бэкапа</span>
              <span className="text-muted-foreground">{data?.policies_total ?? 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Недоступные хосты</span>
              <span className={data?.hosts_unreachable ? 'text-red-400' : 'text-muted-foreground'}>
                {data?.hosts_unreachable ?? 0}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <ShieldCheck className="h-4 w-4" /> Бэкап панели
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span>Последний полный</span>
              <span className="text-muted-foreground">{formatDate(data?.last_full_backup_at)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Последний БД</span>
              <span className="text-muted-foreground">{formatDate(data?.last_db_backup_at)}</span>
            </div>
            {data?.attention?.length ? (
              <div className="rounded-lg border border-amber-500/30 p-2 text-xs text-amber-400">
                {data.attention.length} проблем(ы) требуют внимания
              </div>
            ) : null}
            <Link to="/backups">
              <Button variant="secondary" className="mt-2 w-full">
                Перейти в бэкапы
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
