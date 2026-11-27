import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Save } from 'lucide-react'

import backupsApi from '../../api/backups'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Skeleton } from '../../components/ui/skeleton'

const FIELDS: Array<{ key: string; label: string; hint?: string; type?: 'number' | 'text' | 'bool' }> = [
  { key: 'timezone', label: 'Часовой пояс', hint: 'Europe/Moscow' },
  { key: 'sla_db_hours', label: 'SLA: БД не старше, ч', type: 'number' },
  { key: 'sla_full_hours', label: 'SLA: полный не старше, ч', type: 'number' },
  { key: 'retention_db_copies', label: 'Хранить копий БД по умолчанию', type: 'number' },
  { key: 'retention_full_days', label: 'Хранить полный, дней', type: 'number' },
  { key: 'min_copies', label: 'Минимум копий (защита retention)', type: 'number' },
  { key: 'default_timeout_sec', label: 'Таймаут операции, сек', type: 'number' },
  { key: 'spool_limit_mb', label: 'Лимит spool агента, МБ', type: 'number' },
  { key: 'encrypt_always', label: 'Шифровать всегда', type: 'bool' },
  { key: 'notify_digest', label: 'Дайджест вместо потока сообщений', type: 'bool' },
]

export default function SettingsTab() {
  const queryClient = useQueryClient()
  const settings = useQuery({ queryKey: ['backups', 'settings'], queryFn: backupsApi.settings })
  const [values, setValues] = useState<Record<string, unknown>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (settings.data?.values) setValues(settings.data.values)
  }, [settings.data])

  if (settings.isLoading) return <Skeleton className="h-64 w-full" />

  const save = async () => {
    setSaving(true)
    try {
      await backupsApi.saveSettings(values)
      void queryClient.invalidateQueries({ queryKey: ['backups', 'settings'] })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="glass-card max-w-2xl">
      <CardHeader>
        <CardTitle className="text-sm">Значения по умолчанию</CardTitle>
        <CardDescription>
          Наследуются хранилищами и уровнями, если там параметр не задан.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          {FIELDS.map((field) => (
            <div key={field.key} className="space-y-1">
              <Label>{field.label}</Label>
              {field.type === 'bool' ? (
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={Boolean(values[field.key])}
                    onChange={(e) => setValues({ ...values, [field.key]: e.target.checked })}
                  />
                  включено
                </label>
              ) : (
                <Input
                  type={field.type === 'number' ? 'number' : 'text'}
                  value={String(values[field.key] ?? '')}
                  placeholder={field.hint}
                  onChange={(e) =>
                    setValues({
                      ...values,
                      [field.key]: field.type === 'number' ? Number(e.target.value) : e.target.value,
                    })
                  }
                />
              )}
            </div>
          ))}
        </div>
        <Button onClick={save} disabled={saving}>
          <Save className="mr-2 h-4 w-4" /> Сохранить
        </Button>
      </CardContent>
    </Card>
  )
}
