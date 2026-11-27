import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, RefreshCw, Server, Terminal } from 'lucide-react'
import { Link } from 'react-router-dom'

import backupsApi, { type BackupHost } from '../../api/backups'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog'
import { Skeleton } from '../../components/ui/skeleton'

const formatDate = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const agentBadge = (host: BackupHost) => {
  if (host.agent_status === 'online') return <Badge className="bg-emerald-500/15 text-emerald-400">online</Badge>
  if (host.agent_status === 'offline') return <Badge variant="destructive">offline</Badge>
  return <Badge variant="outline">нет агента</Badge>
}

export default function InfrastructureNodes() {
  const hosts = useQuery({ queryKey: ['backups', 'hosts'], queryFn: backupsApi.hosts, refetchInterval: 30000 })
  const [command, setCommand] = useState<string | null>(null)

  const nodes = (hosts.data ?? []).filter((host) => host.role === 'node')
  const stats = [
    { title: 'Всего нод', value: nodes.length },
    { title: 'Агент online', value: nodes.filter((host) => host.agent_status === 'online').length },
    { title: 'Агент offline', value: nodes.filter((host) => host.agent_status === 'offline').length },
    { title: 'Без агента', value: nodes.filter((host) => !host.agent_status).length },
    { title: 'Доступно', value: nodes.filter((host) => host.status === 'reachable').length },
    { title: 'Недоступно', value: nodes.filter((host) => host.status === 'unreachable').length },
  ]

  const install = async (host: BackupHost) => {
    const result = await backupsApi.installAgent(host.id)
    setCommand(result.install_command)
  }

  if (hosts.isLoading) return <Skeleton className="h-64 w-full" />

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Ноды</h1>
          <p className="mt-1 text-sm text-muted-foreground">Управление нодами Remnawave и их агентами бэкапа</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => hosts.refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" /> Обновить
          </Button>
          <Link to="/backups?tab=hosts">
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Добавить ноду
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {stats.map((stat) => (
          <Card key={stat.title} className="glass-card">
            <CardContent className="p-4 text-center">
              <div className="text-xs text-muted-foreground">{stat.title}</div>
              <div className="mt-1 text-2xl font-semibold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="glass-card">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Server className="h-4 w-4" /> Список нод
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-left text-xs text-muted-foreground">
                <th className="p-3">Нода</th>
                <th className="p-3">Адрес</th>
                <th className="p-3">Агент</th>
                <th className="p-3">Heartbeat</th>
                <th className="p-3">Последний бэкап</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody>
              {nodes.map((host) => (
                <tr key={host.id} className="border-b border-white/5 last:border-0">
                  <td className="p-3 font-medium">{host.name}</td>
                  <td className="p-3 text-muted-foreground">{host.address}</td>
                  <td className="p-3">{agentBadge(host)}</td>
                  <td className="p-3 text-muted-foreground">{formatDate(host.last_heartbeat)}</td>
                  <td className="p-3 text-muted-foreground">{formatDate(host.last_success_at)}</td>
                  <td className="p-3">
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="secondary" onClick={() => backupsApi.scanHost(host.id).then(() => hosts.refetch())}>
                        Сканировать
                      </Button>
                      <Button size="sm" onClick={() => install(host)}>
                        <Terminal className="mr-1 h-3.5 w-3.5" /> Агент
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
              {!nodes.length ? (
                <tr>
                  <td className="p-8 text-center text-muted-foreground" colSpan={6}>
                    Нод нет. Добавьте хост с ролью «node» на странице «Бэкапы → Хосты и агенты».
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Dialog open={Boolean(command)} onOpenChange={() => setCommand(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Установка агента на ноду</DialogTitle>
          </DialogHeader>
          <pre className="max-h-40 overflow-auto rounded-lg bg-black/40 p-3 text-xs">{command}</pre>
          <DialogFooter>
            <Button onClick={() => command && navigator.clipboard.writeText(command)}>Скопировать</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
