import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Plus, RefreshCw, Trash2, XCircle } from 'lucide-react'

import backupsApi, { type BackupStorage } from '../../api/backups'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Card, CardContent } from '../../components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Skeleton } from '../../components/ui/skeleton'

const KIND_LABELS: Record<string, string> = {
  local: 'Папка в CMS',
  s3: 'S3-совместимое',
  sftp: 'SFTP-сервер',
  ssh: 'SSH (SFTP)',
  webdav: 'WebDAV (rclone)',
  ftp: 'FTP (rclone)',
  rclone: 'rclone (облако)',
}

const formatBytes = (value: number) => {
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

export default function StoragesTab() {
  const queryClient = useQueryClient()
  const storages = useQuery({ queryKey: ['backups', 'storages'], queryFn: backupsApi.storages })
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ id: string; ok: boolean; message: string } | null>(null)
  const [form, setForm] = useState({
    name: '',
    kind: 's3',
    path: '',
    endpoint: '',
    bucket: '',
    prefix: '',
    access_key: '',
    secret_key: '',
    host: '',
    port: 22,
    user: '',
    password: '',
    remote: '',
  })

  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['backups', 'storages'] })

  const buildPayload = (): Partial<BackupStorage> & { secret?: Record<string, unknown> } => {
    const config: Record<string, unknown> = {}
    const secret: Record<string, unknown> = {}
    if (form.kind === 'local') config.path = form.path
    if (form.kind === 's3') {
      config.endpoint = form.endpoint
      config.bucket = form.bucket
      config.prefix = form.prefix
      secret.access_key = form.access_key
      secret.secret_key = form.secret_key
    }
    if (form.kind === 'sftp' || form.kind === 'ssh') {
      config.host = form.host
      config.port = Number(form.port)
      config.user = form.user
      config.path = form.path
      secret.password = form.password
    }
    if (form.kind === 'rclone' || form.kind === 'webdav' || form.kind === 'ftp') {
      config.remote = form.remote
      config.path = form.path
    }
    return { name: form.name, kind: form.kind as BackupStorage['kind'], config, secret, enabled: true }
  }

  const create = async () => {
    await backupsApi.createStorage(buildPayload())
    setOpen(false)
    setForm({ ...form, name: '', path: '', endpoint: '', bucket: '', prefix: '', access_key: '', secret_key: '', host: '', user: '', password: '', remote: '' })
    refresh()
  }

  const test = async (storage: BackupStorage) => {
    setBusy(storage.id)
    try {
      const result = await backupsApi.testStorage(storage.id)
      setTestResult({ id: storage.id, ...result })
      refresh()
    } finally {
      setBusy(null)
    }
  }

  if (storages.isLoading) return <Skeleton className="h-64 w-full" />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Хранилищ может быть сколько угодно. Правило 3-2-1: минимум одно — вне этого сервера.
        </p>
        <Button onClick={() => setOpen(true)}>
          <Plus className="mr-2 h-4 w-4" /> Добавить хранилище
        </Button>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        {(storages.data ?? []).map((storage) => (
          <Card key={storage.id} className="glass-card">
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{storage.name}</span>
                    <Badge variant="outline">{KIND_LABELS[storage.kind] ?? storage.kind}</Badge>
                    {storage.is_default ? <Badge>default</Badge> : null}
                    {!storage.enabled ? <Badge variant="secondary">выкл</Badge> : null}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground break-all">
                    {String(storage.config.path ?? storage.config.bucket ?? storage.config.remote ?? '')}
                  </div>
                  <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                    <span>занято: {formatBytes(storage.used_bytes)}</span>
                    {storage.last_check_ok === true ? (
                      <span className="flex items-center gap-1 text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" /> проверено
                      </span>
                    ) : null}
                    {storage.last_check_ok === false ? (
                      <span className="flex items-center gap-1 text-red-400">
                        <XCircle className="h-3 w-3" /> ошибка
                      </span>
                    ) : null}
                  </div>
                  {testResult?.id === storage.id ? (
                    <div className={`mt-2 text-xs ${testResult.ok ? 'text-emerald-400' : 'text-red-400'}`}>
                      {testResult.ok ? 'OK' : testResult.message}
                      {testResult.ok && testResult.message ? ` · ${testResult.message}` : ''}
                    </div>
                  ) : null}
                </div>
                <div className="flex flex-col gap-2">
                  <Button size="sm" variant="secondary" disabled={busy === storage.id} onClick={() => test(storage)}>
                    <RefreshCw className="mr-1 h-3.5 w-3.5" /> Проверить
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => backupsApi.deleteStorage(storage.id).then(refresh)}
                  >
                    <Trash2 className="mr-1 h-3.5 w-3.5" /> Удалить
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {!storages.data?.length ? (
          <Card className="glass-card lg:col-span-2">
            <CardContent className="p-8 text-center text-muted-foreground">
              Хранилищ нет. Пока не добавлено хотя бы одно, бэкапы некуда складывать.
            </CardContent>
          </Card>
        ) : null}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Добавить хранилище</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Название</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="s3-main" />
              </div>
              <div className="space-y-1">
                <Label>Тип</Label>
                <select
                  className="w-full rounded-md border border-white/10 bg-transparent p-2 text-sm"
                  value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value })}
                >
                  {Object.entries(KIND_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {form.kind === 'local' ? (
              <div className="space-y-1">
                <Label>Путь</Label>
                <Input value={form.path} onChange={(e) => setForm({ ...form, path: e.target.value })} placeholder="/var/lib/hexaveil/backups" />
              </div>
            ) : null}

            {form.kind === 's3' ? (
              <>
                <div className="space-y-1">
                  <Label>Endpoint</Label>
                  <Input value={form.endpoint} onChange={(e) => setForm({ ...form, endpoint: e.target.value })} placeholder="https://s3.ru1.storage.beget.com" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label>Bucket</Label>
                    <Input value={form.bucket} onChange={(e) => setForm({ ...form, bucket: e.target.value })} />
                  </div>
                  <div className="space-y-1">
                    <Label>Prefix</Label>
                    <Input value={form.prefix} onChange={(e) => setForm({ ...form, prefix: e.target.value })} placeholder="prod/" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label>Access key</Label>
                    <Input value={form.access_key} onChange={(e) => setForm({ ...form, access_key: e.target.value })} />
                  </div>
                  <div className="space-y-1">
                    <Label>Secret key</Label>
                    <Input type="password" value={form.secret_key} onChange={(e) => setForm({ ...form, secret_key: e.target.value })} />
                  </div>
                </div>
              </>
            ) : null}

            {form.kind === 'sftp' || form.kind === 'ssh' ? (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2 space-y-1">
                    <Label>Хост</Label>
                    <Input value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} />
                  </div>
                  <div className="space-y-1">
                    <Label>Порт</Label>
                    <Input type="number" value={form.port} onChange={(e) => setForm({ ...form, port: Number(e.target.value) })} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label>Пользователь</Label>
                    <Input value={form.user} onChange={(e) => setForm({ ...form, user: e.target.value })} />
                  </div>
                  <div className="space-y-1">
                    <Label>Пароль</Label>
                    <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label>Абсолютный путь</Label>
                  <Input value={form.path} onChange={(e) => setForm({ ...form, path: e.target.value })} placeholder="/backups/hexaveil" />
                </div>
              </>
            ) : null}

            {form.kind === 'rclone' || form.kind === 'webdav' || form.kind === 'ftp' ? (
              <>
                <div className="space-y-1">
                  <Label>rclone remote</Label>
                  <Input value={form.remote} onChange={(e) => setForm({ ...form, remote: e.target.value })} placeholder="gdrive" />
                </div>
                <div className="space-y-1">
                  <Label>Путь внутри remote</Label>
                  <Input value={form.path} onChange={(e) => setForm({ ...form, path: e.target.value })} placeholder="hexaveil/backups" />
                </div>
                <p className="text-xs text-muted-foreground">
                  Remote настраивается через `rclone config` на машине, где работает CMS/агент.
                </p>
              </>
            ) : null}
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
