import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Play, Plus, Trash2 } from 'lucide-react'

import backupsApi, { type BackupPolicy, type BackupTier } from '../../api/backups'
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

const scopeLabel: Record<string, string> = {
  full: 'Полный',
  database: 'Только БД',
  files: 'Только файлы',
  env: 'Только .env',
  custom: 'Выборочно',
}

function TierRow({ tier, onChange }: { tier: BackupTier; onChange: () => void }) {
  return (
    <div className="rounded-lg border border-white/10 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-medium">{tier.name}</span>
          <Badge variant="outline">{scopeLabel[tier.scope] ?? tier.scope}</Badge>
          <Badge variant="secondary">
            {tier.schedule_kind === 'interval' ? `каждые ${tier.interval_minutes} мин` : tier.cron}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {tier.retention_mode === 'auto'
              ? `хранить ${tier.retention_copies ?? tier.retention_days} копий`
              : `хранить ${tier.retention_days} дней`}
            {' · '}следующий: {formatDate(tier.next_run_at)}
          </span>
          <Button size="sm" variant="secondary" onClick={() => backupsApi.runTier(tier.id).then(onChange)}>
            <Play className="mr-1 h-3.5 w-3.5" /> Запустить
          </Button>
          <Button size="sm" variant="ghost" onClick={() => backupsApi.deleteTier(tier.id).then(onChange)}>
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
      <div className="mt-1 text-xs text-muted-foreground">
        шифрование: {tier.encrypt ? 'да' : 'нет'} · логи: {tier.include_logs ? 'да' : 'нет'} · хранилищ: {tier.storage_ids.length}
      </div>
    </div>
  )
}

export default function PoliciesTab() {
  const queryClient = useQueryClient()
  const hosts = useQuery({ queryKey: ['backups', 'hosts'], queryFn: backupsApi.hosts })
  const [hostId, setHostId] = useState<string>('')
  const [policyDialog, setPolicyDialog] = useState(false)
  const [tierDialog, setTierDialog] = useState<BackupPolicy | null>(null)
  const [policyName, setPolicyName] = useState('')
  const [policy, setPolicy] = useState<BackupPolicy | null>(null)
  const [tiers, setTiers] = useState<BackupTier[]>([])
  const [tierForm, setTierForm] = useState({
    name: 'БД каждый час',
    scope: 'database',
    schedule_kind: 'interval',
    interval_minutes: 60,
    cron: '0 3 * * *',
    retention_mode: 'auto',
    retention_copies: 48,
    retention_days: 14,
    encrypt: true,
    include_logs: false,
  })

  useEffect(() => {
    if (!hostId && hosts.data?.length) setHostId(hosts.data[0].id)
  }, [hosts.data, hostId])

  const policies = useQuery({
    queryKey: ['backups', 'policies', hostId],
    queryFn: () => backupsApi.policies(hostId || undefined),
    enabled: Boolean(hostId),
  })

  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['backups', 'policies'] })

  const selectPolicy = async (item: BackupPolicy) => {
    setPolicy(item)
    setTiers(await backupsApi.tiers(item.id))
  }

  const createPolicy = async () => {
    if (!hostId) return
    const created = await backupsApi.createPolicy({ name: policyName || 'Политика', host_id: hostId })
    setPolicyDialog(false)
    setPolicyName('')
    refresh()
    await selectPolicy(created)
  }

  const createTier = async () => {
    if (!tierDialog) return
    await backupsApi.createTier(tierDialog.id, tierForm as unknown as Partial<BackupTier>)
    setTierDialog(null)
    setTiers(await backupsApi.tiers(tierDialog.id))
    refresh()
  }

  if (hosts.isLoading) return <Skeleton className="h-64 w-full" />

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label>Хост</Label>
          <select
            className="rounded-md border border-white/10 bg-transparent p-2 text-sm"
            value={hostId}
            onChange={(e) => {
              setHostId(e.target.value)
              setPolicy(null)
              setTiers([])
            }}
          >
            {(hosts.data ?? []).map((host) => (
              <option key={host.id} value={host.id}>
                {host.name} ({host.role})
              </option>
            ))}
          </select>
        </div>
        <Button onClick={() => setPolicyDialog(true)} disabled={!hostId}>
          <Plus className="mr-2 h-4 w-4" /> Политика
        </Button>
      </div>

      <div className="grid gap-3 lg:grid-cols-[260px_1fr]">
        <div className="space-y-2">
          {(policies.data ?? []).map((item) => (
            <button
              key={item.id}
              onClick={() => selectPolicy(item)}
              className={`w-full rounded-lg border p-3 text-left text-sm transition ${
                policy?.id === item.id ? 'border-primary/60 bg-primary/10' : 'border-white/10 hover:bg-white/5'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{item.name}</span>
                {!item.enabled ? <Badge variant="secondary">выкл</Badge> : null}
              </div>
              <div className="text-xs text-muted-foreground">{item.timezone}</div>
            </button>
          ))}
          {!policies.data?.length ? (
            <div className="rounded-lg border border-white/10 p-4 text-sm text-muted-foreground">
              Политик нет. Создайте первую кнопкой «Политика».
            </div>
          ) : null}
        </div>

        <Card className="glass-card">
          <CardHeader className="flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm">{policy ? `Уровни · ${policy.name}` : 'Выберите политику'}</CardTitle>
            {policy ? (
              <Button size="sm" onClick={() => setTierDialog(policy)}>
                <Plus className="mr-1 h-3.5 w-3.5" /> Уровень
              </Button>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-2">
            {policy ? (
              tiers.length ? (
                tiers.map((tier) => (
                  <TierRow key={tier.id} tier={tier} onChange={() => selectPolicy(policy)} />
                ))
              ) : (
                <div className="text-sm text-muted-foreground">
                  Уровней нет. Добавьте «БД каждый час» и «Полный ночью».
                </div>
              )
            ) : (
              <div className="text-sm text-muted-foreground">Слева выберите политику, чтобы настроить уровни.</div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={policyDialog} onOpenChange={setPolicyDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Новая политика</DialogTitle>
          </DialogHeader>
          <div className="space-y-1">
            <Label>Название</Label>
            <Input value={policyName} onChange={(e) => setPolicyName(e.target.value)} placeholder="control-plane" />
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setPolicyDialog(false)}>
              Отмена
            </Button>
            <Button onClick={createPolicy}>Создать</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(tierDialog)} onOpenChange={() => setTierDialog(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Новый уровень</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label>Название</Label>
              <Input value={tierForm.name} onChange={(e) => setTierForm({ ...tierForm, name: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Что бэкапить</Label>
                <select
                  className="w-full rounded-md border border-white/10 bg-transparent p-2 text-sm"
                  value={tierForm.scope}
                  onChange={(e) => setTierForm({ ...tierForm, scope: e.target.value })}
                >
                  <option value="full">Полный</option>
                  <option value="database">Только БД</option>
                  <option value="files">Только файлы</option>
                  <option value="env">Только .env</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label>Расписание</Label>
                <select
                  className="w-full rounded-md border border-white/10 bg-transparent p-2 text-sm"
                  value={tierForm.schedule_kind}
                  onChange={(e) => setTierForm({ ...tierForm, schedule_kind: e.target.value })}
                >
                  <option value="interval">Каждые N минут</option>
                  <option value="cron">Cron</option>
                </select>
              </div>
            </div>
            {tierForm.schedule_kind === 'interval' ? (
              <div className="space-y-1">
                <Label>Интервал, минут</Label>
                <Input
                  type="number"
                  value={tierForm.interval_minutes}
                  onChange={(e) => setTierForm({ ...tierForm, interval_minutes: Number(e.target.value) })}
                />
              </div>
            ) : (
              <div className="space-y-1">
                <Label>Cron</Label>
                <Input value={tierForm.cron} onChange={(e) => setTierForm({ ...tierForm, cron: e.target.value })} placeholder="0 3 * * *" />
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Режим retention</Label>
                <select
                  className="w-full rounded-md border border-white/10 bg-transparent p-2 text-sm"
                  value={tierForm.retention_mode}
                  onChange={(e) => setTierForm({ ...tierForm, retention_mode: e.target.value })}
                >
                  <option value="auto">По числу копий</option>
                  <option value="days">По дням</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label>{tierForm.retention_mode === 'auto' ? 'Копий' : 'Дней'}</Label>
                <Input
                  type="number"
                  value={tierForm.retention_mode === 'auto' ? tierForm.retention_copies : tierForm.retention_days}
                  onChange={(e) =>
                    setTierForm(
                      tierForm.retention_mode === 'auto'
                        ? { ...tierForm, retention_copies: Number(e.target.value) }
                        : { ...tierForm, retention_days: Number(e.target.value) },
                    )
                  }
                />
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={tierForm.encrypt}
                  onChange={(e) => setTierForm({ ...tierForm, encrypt: e.target.checked })}
                />
                Шифровать
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={tierForm.include_logs}
                  onChange={(e) => setTierForm({ ...tierForm, include_logs: e.target.checked })}
                />
                Включать логи
              </label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setTierDialog(null)}>
              Отмена
            </Button>
            <Button onClick={createTier}>Создать</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
