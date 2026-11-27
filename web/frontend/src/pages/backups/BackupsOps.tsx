import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Clock, Play, Plus, RotateCcw, Trash2, XCircle } from 'lucide-react'

import backupsApi, { type BackupRun } from '../../api/backups'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Skeleton } from '../../components/ui/skeleton'

const formatDate = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const statusVariant = (status: BackupRun['status']) => {
  if (status === 'success') return 'default' as const
  if (status === 'failed') return 'destructive' as const
  if (status === 'running') return 'secondary' as const
  return 'outline' as const
}

function RunsView() {
  const queryClient = useQueryClient()
  const hosts = useQuery({ queryKey: ['backups', 'hosts'], queryFn: backupsApi.hosts })
  const [hostId, setHostId] = useState('')
  const [selected, setSelected] = useState<BackupRun | null>(null)

  const runs = useQuery({
    queryKey: ['backups', 'runs', hostId],
    queryFn: () => backupsApi.runs({ host_id: hostId || undefined, limit: 50 }),
    refetchInterval: 5000,
  })

  const detail = useQuery({
    queryKey: ['backups', 'run', selected?.id],
    queryFn: () => backupsApi.run(selected!.id),
    enabled: Boolean(selected?.id),
    refetchInterval: selected && ['queued', 'running'].includes(selected.status) ? 3000 : false,
  })

  useEffect(() => {
    if (detail.data) setSelected((prev) => (prev ? { ...prev, ...detail.data } : prev))
  }, [detail.data])

  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['backups', 'runs'] })

  if (runs.isLoading) return <Skeleton className="h-64 w-full" />

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select
          className="rounded-md border border-white/10 bg-transparent p-2 text-sm"
          value={hostId}
          onChange={(e) => setHostId(e.target.value)}
        >
          <option value="">Все хосты</option>
          {(hosts.data ?? []).map((host) => (
            <option key={host.id} value={host.id}>
              {host.name}
            </option>
          ))}
        </select>
        <Button variant="secondary" onClick={refresh}>
          <RotateCcw className="mr-2 h-4 w-4" /> Обновить
        </Button>
      </div>

      <div className="grid gap-3 lg:grid-cols-[1fr_360px]">
        <Card className="glass-card">
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs text-muted-foreground">
                  <th className="p-3">Начало</th>
                  <th className="p-3">Хост</th>
                  <th className="p-3">Scope</th>
                  <th className="p-3">Статус</th>
                  <th className="p-3">Прогресс</th>
                </tr>
              </thead>
              <tbody>
                {(runs.data ?? []).map((run) => (
                  <tr
                    key={run.id}
                    className="cursor-pointer border-b border-white/5 last:border-0 hover:bg-white/5"
                    onClick={() => setSelected(run)}
                  >
                    <td className="p-3 text-muted-foreground">{formatDate(run.created_at)}</td>
                    <td className="p-3">
                      {hosts.data?.find((host) => host.id === run.host_id)?.name ?? run.host_id?.slice(0, 8)}
                    </td>
                    <td className="p-3 text-muted-foreground">{run.artifact_scope ?? 'full'}</td>
                    <td className="p-3">
                      <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
                    </td>
                    <td className="p-3 text-muted-foreground">{run.progress}%</td>
                  </tr>
                ))}
                {!runs.data?.length ? (
                  <tr>
                    <td className="p-6 text-center text-muted-foreground" colSpan={5}>
                      Запусков пока нет
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Clock className="h-4 w-4" /> Детали запуска
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {selected ? (
              <>
                <div className="flex items-center justify-between">
                  <Badge variant={statusVariant(selected.status)}>{selected.status}</Badge>
                  {selected.status === 'running' || selected.status === 'queued' ? (
                    <Button size="sm" variant="destructive" onClick={() => backupsApi.cancelRun(selected.id).then(refresh)}>
                      <XCircle className="mr-1 h-3.5 w-3.5" /> Отменить
                    </Button>
                  ) : null}
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white/10">
                  <div className="h-full bg-primary transition-all" style={{ width: `${selected.progress}%` }} />
                </div>
                <div className="space-y-1">
                  {(selected.steps ?? []).map((step) => (
                    <div key={step.id} className="flex items-center justify-between text-xs">
                      <span>{step.title}</span>
                      <span className="text-muted-foreground">{step.status}</span>
                    </div>
                  ))}
                </div>
                {selected.error ? <div className="text-xs text-red-400">{selected.error}</div> : null}
                <pre className="max-h-48 overflow-auto rounded-lg bg-black/40 p-2 text-[11px] whitespace-pre-wrap">
                  {selected.log || 'Лог пуст'}
                </pre>
              </>
            ) : (
              <div className="text-muted-foreground">Выберите запуск слева</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function RestoreView() {
  const hosts = useQuery({ queryKey: ['backups', 'hosts'], queryFn: backupsApi.hosts })
  const [groupKey, setGroupKey] = useState('')
  const [targetHost, setTargetHost] = useState('')
  const [plan, setPlan] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  const buildPlan = async () => {
    setError('')
    try {
      const result = await backupsApi.restorePlan({
        group_key: groupKey.trim(),
        target_host_id: targetHost || undefined,
        target_kind: targetHost ? 'new' : 'same',
      })
      setPlan(result)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Не удалось построить план')
    }
  }

  const execute = async () => {
    if (!plan) return
    await backupsApi.restore(String(plan.plan_token))
    setPlan(null)
    setGroupKey('')
  }

  return (
    <div className="space-y-4">
      <Card className="glass-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Восстановление из бэкапа</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <Label>Группа консистентности (consistency_group)</Label>
              <Input value={groupKey} onChange={(e) => setGroupKey(e.target.value)} placeholder="grp_20261121T180000Z_abc" />
            </div>
            <div className="space-y-1">
              <Label>Целевой хост (пусто — тот же)</Label>
              <select
                className="w-full rounded-md border border-white/10 bg-transparent p-2 text-sm"
                value={targetHost}
                onChange={(e) => setTargetHost(e.target.value)}
              >
                <option value="">Тот же хост</option>
                {(hosts.data ?? []).map((host) => (
                  <option key={host.id} value={host.id}>
                    {host.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <Button onClick={buildPlan} disabled={!groupKey.trim()}>
            Построить план
          </Button>
          {error ? <div className="text-xs text-red-400">{error}</div> : null}
        </CardContent>
      </Card>

      {plan ? (
        <Card className="glass-card border-amber-500/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">План восстановления</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <ol className="list-decimal space-y-1 pl-5">
              {((plan.steps as Array<{ title: string }>) ?? []).map((step, index) => (
                <li key={index}>{step.title}</li>
              ))}
            </ol>
            {((plan.warnings as string[]) ?? []).map((warning) => (
              <div key={warning} className="text-xs text-amber-400">
                ⚠ {warning}
              </div>
            ))}
            <Button variant="destructive" onClick={execute}>
              <Play className="mr-2 h-4 w-4" /> Начать восстановление
            </Button>
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}

function NotificationsView() {
  const queryClient = useQueryClient()
  const channels = useQuery({ queryKey: ['backups', 'channels'], queryFn: backupsApi.channels })
  const rules = useQuery({ queryKey: ['backups', 'rules'], queryFn: backupsApi.rules })
  const events = useQuery({ queryKey: ['backups', 'events'], queryFn: backupsApi.events })
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: '', kind: 'telegram', bot_token: '', chat_id: '', topic_id: '', url: '' })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['backups', 'channels'] })
    void queryClient.invalidateQueries({ queryKey: ['backups', 'rules'] })
  }

  const create = async () => {
    const config: Record<string, unknown> = {}
    const secret: Record<string, unknown> = {}
    if (form.kind === 'telegram') {
      config.chat_id = form.chat_id
      config.topic_id = form.topic_id || undefined
      secret.bot_token = form.bot_token
    } else {
      config.url = form.url
    }
    await backupsApi.createChannel({
      name: form.name,
      kind: form.kind,
      config,
      secret,
      enabled: true,
    })
    setOpen(false)
    setForm({ name: '', kind: 'telegram', bot_token: '', chat_id: '', topic_id: '', url: '' })
    refresh()
  }

  const addRule = async (channelId: string) => {
    await backupsApi.createRule({
      name: `Правило ${channelId.slice(0, 4)}`,
      event: 'run_failed',
      channel_ids: [channelId],
      severity: 'critical',
      enabled: true,
    })
    refresh()
  }

  if (channels.isLoading) return <Skeleton className="h-64 w-full" />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">Каналы и правила уведомлений о бэкапах.</p>
        <Button onClick={() => setOpen(true)}>
          <Plus className="mr-2 h-4 w-4" /> Канал
        </Button>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        {(channels.data ?? []).map((channel) => (
          <Card key={channel.id} className="glass-card">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4" />
                  <span className="font-medium">{channel.name}</span>
                  <Badge variant="outline">{channel.kind}</Badge>
                  {channel.has_secret ? <Badge variant="secondary">секрет ✓</Badge> : null}
                </div>
                <div className="flex gap-1">
                  <Button size="sm" variant="secondary" onClick={() => backupsApi.testChannel(channel.id).then(refresh)}>
                    Проверить
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => addRule(channel.id)}>
                    + правило
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => backupsApi.deleteChannel(channel.id).then(refresh)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {!channels.data?.length ? (
          <Card className="glass-card lg:col-span-2">
            <CardContent className="p-8 text-center text-muted-foreground">
              Каналов нет — алерты никуда не приходят.
            </CardContent>
          </Card>
        ) : null}
      </div>

      <Card className="glass-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Правила</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(rules.data ?? []).map((rule) => (
            <div key={rule.id} className="flex items-center justify-between rounded-lg border border-white/10 p-2 text-sm">
              <div>
                <span className="font-medium">{rule.event}</span>
                <span className="ml-2 text-xs text-muted-foreground">
                  {rule.severity} · каналов: {rule.channel_ids.length}
                  {rule.quiet_hours ? ` · тишина ${rule.quiet_hours}` : ''}
                </span>
              </div>
              <Button size="sm" variant="ghost" onClick={() => backupsApi.deleteRule(rule.id).then(refresh)}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
          {!rules.data?.length ? (
            <div className="text-sm text-muted-foreground">
              Правил нет. Доступные события: {(events.data ?? []).map((event) => event.event).join(', ')}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Новый канал</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Название</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="space-y-1">
                <Label>Тип</Label>
                <select
                  className="w-full rounded-md border border-white/10 bg-transparent p-2 text-sm"
                  value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value })}
                >
                  <option value="telegram">Telegram</option>
                  <option value="webhook">Webhook</option>
                </select>
              </div>
            </div>
            {form.kind === 'telegram' ? (
              <>
                <div className="space-y-1">
                  <Label>Bot token</Label>
                  <Input type="password" value={form.bot_token} onChange={(e) => setForm({ ...form, bot_token: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label>Chat ID</Label>
                    <Input value={form.chat_id} onChange={(e) => setForm({ ...form, chat_id: e.target.value })} placeholder="-100..." />
                  </div>
                  <div className="space-y-1">
                    <Label>Topic ID</Label>
                    <Input value={form.topic_id} onChange={(e) => setForm({ ...form, topic_id: e.target.value })} />
                  </div>
                </div>
              </>
            ) : (
              <div className="space-y-1">
                <Label>URL</Label>
                <Input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://..." />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Отмена
            </Button>
            <Button onClick={create} disabled={!form.name}>
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default function OpsTab({ mode = 'runs' }: { mode?: 'runs' | 'restore' | 'notifications' }) {
  if (mode === 'restore') return <RestoreView />
  if (mode === 'notifications') return <NotificationsView />
  return <RunsView />
}
