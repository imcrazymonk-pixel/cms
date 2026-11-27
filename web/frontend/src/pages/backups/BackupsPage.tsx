import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  Boxes,
  HardDrive,
  Plus,
  RefreshCw,
  Server,
  ShieldCheck,
  Terminal,
} from 'lucide-react'

import backupsApi, { type BackupHost } from '../../api/backups'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Skeleton } from '../../components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import PoliciesTab from './BackupsPolicies'
import OpsTab from './BackupsOps'
import SettingsTab from './BackupsSettings'
import StoragesTab from './BackupsStorages'

const formatBytes = (value?: number | null) => {
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = value
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unit]}`
}

const formatDate = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const statusBadge = (host: BackupHost) => {
  if (host.role === 'self' || host.transport === 'inline') return <Badge variant="secondary">local</Badge>
  if (host.agent_status === 'online') return <Badge className="bg-emerald-500/15 text-emerald-400">online</Badge>
  if (host.agent_status === 'offline') return <Badge variant="destructive">offline</Badge>
  return <Badge variant="outline">нет агента</Badge>
}

// ── Overview ─────────────────────────────────────────────────────────────────

function OverviewTab() {
  const overview = useQuery({ queryKey: ['backups', 'overview'], queryFn: backupsApi.overview, refetchInterval: 30000 })
  const hosts = useQuery({ queryKey: ['backups', 'hosts'], queryFn: backupsApi.hosts, refetchInterval: 30000 })

  if (overview.isLoading || hosts.isLoading) {
    return <Skeleton className="h-64 w-full" />
  }
  const data = overview.data
  const cards = [
    { title: 'Последний успешный', value: formatDate(data?.last_success_at), icon: ShieldCheck },
    { title: 'БД', value: formatDate(data?.last_db_backup_at), icon: Boxes },
    { title: 'Полный', value: formatDate(data?.last_full_backup_at), icon: HardDrive },
    { title: 'Агенты', value: `${data?.agents_online ?? 0} / ${(data?.agents_online ?? 0) + (data?.agents_offline ?? 0)}`, icon: Server },
    { title: 'Хранилища', value: `${data?.storages_total ?? 0}${data?.storages_error ? ` · ${data?.storages_error} ошибка` : ''}`, icon: HardDrive },
    { title: 'Объём', value: formatBytes(data?.total_bytes), icon: Boxes },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {cards.map((card) => (
          <Card key={card.title} className="glass-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <card.icon className="h-3.5 w-3.5" />
                {card.title}
              </div>
              <div className="mt-1 text-lg font-semibold">{card.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {data?.attention?.length ? (
        <Card className="glass-card border-amber-500/30">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <AlertTriangle className="h-4 w-4 text-amber-400" /> Требует внимания
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {data.attention.map((item, index) => (
              <div key={`${item.type}-${index}`} className="flex items-start gap-2 text-muted-foreground">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-amber-400" />
                {item.message}
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <Card className="glass-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Хосты</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-left text-xs text-muted-foreground">
                <th className="p-3">Хост</th>
                <th className="p-3">Роль</th>
                <th className="p-3">Агент</th>
                <th className="p-3">Компоненты</th>
                <th className="p-3">Последний бэкап</th>
              </tr>
            </thead>
            <tbody>
              {(hosts.data ?? []).map((host) => (
                <tr key={host.id} className="border-b border-white/5 last:border-0">
                  <td className="p-3">
                    <div className="font-medium">{host.name}</div>
                    <div className="text-xs text-muted-foreground">{host.address}</div>
                  </td>
                  <td className="p-3 text-muted-foreground">{host.role}</td>
                  <td className="p-3">{statusBadge(host)}</td>
                  <td className="p-3 text-muted-foreground">{host.components_count ?? 0}</td>
                  <td className="p-3 text-muted-foreground">{formatDate(host.last_success_at)}</td>
                </tr>
              ))}
              {!hosts.data?.length ? (
                <tr>
                  <td className="p-6 text-center text-muted-foreground" colSpan={5}>
                    Хостов пока нет — добавьте первый на вкладке «Хосты и агенты»
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}

// ── Hosts ────────────────────────────────────────────────────────────────────

function HostsTab() {
  const queryClient = useQueryClient()
  const hosts = useQuery({ queryKey: ['backups', 'hosts'], queryFn: backupsApi.hosts, refetchInterval: 30000 })
  const recipes = useQuery({ queryKey: ['backups', 'recipes'], queryFn: backupsApi.recipes })
  const [dialogOpen, setDialogOpen] = useState(false)
  const [installCommand, setInstallCommand] = useState<string | null>(null)
  const [installResult, setInstallResult] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [form, setForm] = useState({
    name: '',
    address: '',
    role: 'server',
    transport: 'agent',
    ssh_port: 22,
    ssh_user: '',
    ssh_private_key: '',
  })

  const components = useQuery({
    queryKey: ['backups', 'components', expanded],
    queryFn: () => backupsApi.components(expanded ?? undefined),
    enabled: Boolean(expanded),
  })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['backups'] })
  }

  const createHost = async () => {
    await backupsApi.createHost({
      ...form,
      ssh_port: Number(form.ssh_port),
      role: form.role as BackupHost['role'],
      transport: form.transport as BackupHost['transport'],
      ...(form.ssh_private_key ? { ssh_private_key: form.ssh_private_key } : {}),
    } as Partial<BackupHost> & { ssh_private_key?: string })
    setDialogOpen(false)
    setForm({
      name: '',
      address: '',
      role: 'server',
      transport: 'agent',
      ssh_port: 22,
      ssh_user: '',
      ssh_private_key: '',
    })
    refresh()
  }

  const install = async (host: BackupHost, via: 'command' | 'ssh' = 'command') => {
    const result = await backupsApi.installAgent(host.id, via)
    setInstallCommand(result.install_command)
    if (result.install_result) {
      const status = result.install_result.ok ? 'Установлено' : 'Ошибка'
      setInstallResult(`${status}: ${result.install_result.message ?? ''}\n${result.install_result.output ?? ''}`)
    } else {
      setInstallResult(null)
    }
  }

  const recipeTitles = useMemo(() => {
    const map = new Map<string, string>()
    for (const recipe of recipes.data ?? []) map.set(recipe.id, recipe.title)
    return map
  }, [recipes.data])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Агент ставится на сервер и выполняет бэкапы локально, даже если CMS недоступна.
        </p>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={refresh}>
            <RefreshCw className="mr-2 h-4 w-4" /> Обновить
          </Button>
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" /> Добавить хост
          </Button>
        </div>
      </div>

      <div className="grid gap-3">
        {(hosts.data ?? []).map((host) => (
          <Card key={host.id} className="glass-card">
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{host.name}</span>
                    {statusBadge(host)}
                    <Badge variant="outline">{host.role}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {host.address}:{host.ssh_port}
                    {host.agent_version ? ` · агент ${host.agent_version}` : ''}
                    {host.last_heartbeat ? ` · heartbeat ${formatDate(host.last_heartbeat)}` : ''}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => setExpanded(expanded === host.id ? null : host.id)}>
                    Компоненты ({host.components_count ?? 0})
                  </Button>
                  {host.transport !== 'inline' ? (
                    <>
                      <Button size="sm" variant="secondary" onClick={() => backupsApi.scanHost(host.id).then(refresh)}>
                        Сканировать
                      </Button>
                      <Button size="sm" onClick={() => install(host, 'command')}>
                        <Terminal className="mr-2 h-4 w-4" /> Команда
                      </Button>
                      {host.has_ssh_key ? (
                        <Button size="sm" variant="secondary" onClick={() => install(host, 'ssh')}>
                          <Terminal className="mr-2 h-4 w-4" /> По SSH
                        </Button>
                      ) : null}
                    </>
                  ) : null}
                </div>
              </div>

              {expanded === host.id ? (
                <div className="mt-3 rounded-lg border border-white/10">
                  {components.isLoading ? (
                    <Skeleton className="h-20 w-full" />
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-white/10 text-left text-xs text-muted-foreground">
                          <th className="p-2">Компонент</th>
                          <th className="p-2">Рецепт</th>
                          <th className="p-2">Версия</th>
                          <th className="p-2">Confidence</th>
                          <th className="p-2">Вкл.</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(components.data ?? []).map((component) => (
                          <tr key={component.id} className="border-b border-white/5 last:border-0">
                            <td className="p-2">{component.name}</td>
                            <td className="p-2 text-muted-foreground">
                              {recipeTitles.get(component.recipe_id) ?? component.recipe_id}
                            </td>
                            <td className="p-2 text-muted-foreground">{component.version ?? '—'}</td>
                            <td className="p-2">
                              <Badge variant={component.confidence === 'high' ? 'secondary' : 'outline'}>
                                {component.confidence}
                              </Badge>
                            </td>
                            <td className="p-2">
                              <input
                                type="checkbox"
                                checked={component.enabled}
                                onChange={(event) =>
                                  backupsApi
                                    .updateComponent(component.id, { enabled: event.target.checked })
                                    .then(() => components.refetch())
                                }
                              />
                            </td>
                          </tr>
                        ))}
                        {!components.data?.length ? (
                          <tr>
                            <td className="p-4 text-center text-muted-foreground" colSpan={5}>
                              Компоненты не найдены — нажмите «Сканировать»
                            </td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  )}
                </div>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Добавить хост</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label>Название</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="control-plane" />
            </div>
            <div className="space-y-1">
              <Label>Адрес</Label>
              <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="144.31.156.172" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Роль</Label>
                <select
                  className="w-full rounded-md border border-white/10 bg-transparent p-2 text-sm"
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                >
                  <option value="server">server</option>
                  <option value="node">node</option>
                  <option value="self">self (CMS)</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label>SSH-порт</Label>
                <Input
                  type="number"
                  value={form.ssh_port}
                  onChange={(e) => setForm({ ...form, ssh_port: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label>SSH-пользователь</Label>
              <Input
                value={form.ssh_user}
                onChange={(e) => setForm({ ...form, ssh_user: e.target.value })}
                placeholder="root или kilo"
              />
            </div>
            <div className="space-y-1">
              <Label>Приватный SSH-ключ (необязательно)</Label>
              <textarea
                className="min-h-[90px] w-full rounded-md border border-white/10 bg-transparent p-2 font-mono text-xs"
                value={form.ssh_private_key}
                onChange={(e) => setForm({ ...form, ssh_private_key: e.target.value })}
                placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
              />
              <p className="text-xs text-muted-foreground">
                Нужен только для установки агента по кнопке. Хранится зашифрованным и никогда не отдаётся обратно.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setDialogOpen(false)}>
              Отмена
            </Button>
            <Button onClick={createHost} disabled={!form.name || !form.address}>
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(installCommand)} onOpenChange={() => setInstallCommand(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Установка агента</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Выполните команду на сервере под root. Токен показывается один раз.
          </p>
          <pre className="max-h-40 overflow-auto rounded-lg bg-black/40 p-3 text-xs">{installCommand}</pre>
          {installResult ? (
            <pre className="max-h-40 overflow-auto rounded-lg border border-white/10 p-3 text-xs whitespace-pre-wrap">
              {installResult}
            </pre>
          ) : null}
          <DialogFooter>
            <Button
              onClick={() => {
                if (installCommand) void navigator.clipboard.writeText(installCommand)
              }}
            >
              Скопировать
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ── shell ────────────────────────────────────────────────────────────────────

export default function BackupsPage() {
  const initial = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('tab') : null
  const [tab, setTab] = useState(initial || 'overview')

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Бэкапы</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Сохранность серверов, панели, бота и самой CMS
          </p>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="flex flex-wrap">
          <TabsTrigger value="overview">Обзор</TabsTrigger>
          <TabsTrigger value="hosts">Хосты и агенты</TabsTrigger>
          <TabsTrigger value="policies">Политики и уровни</TabsTrigger>
          <TabsTrigger value="runs">Запуски</TabsTrigger>
          <TabsTrigger value="storages">Хранилища</TabsTrigger>
          <TabsTrigger value="restore">Восстановление</TabsTrigger>
          <TabsTrigger value="notifications">Уведомления</TabsTrigger>
          <TabsTrigger value="settings">Настройки</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <OverviewTab />
        </TabsContent>
        <TabsContent value="hosts" className="mt-4">
          <HostsTab />
        </TabsContent>
        <TabsContent value="policies" className="mt-4">
          <PoliciesTab />
        </TabsContent>
        <TabsContent value="runs" className="mt-4">
          <OpsTab />
        </TabsContent>
        <TabsContent value="storages" className="mt-4">
          <StoragesTab />
        </TabsContent>
        <TabsContent value="restore" className="mt-4">
          <OpsTab mode="restore" />
        </TabsContent>
        <TabsContent value="notifications" className="mt-4">
          <OpsTab mode="notifications" />
        </TabsContent>
        <TabsContent value="settings" className="mt-4">
          <SettingsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
