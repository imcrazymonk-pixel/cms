import { useState, useEffect } from 'react'
import { themesApi, ThemeSettingsResponse } from '../api/themes'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { Palette, RefreshCw, Save } from 'lucide-react'

export default function ThemeManager() {
  const [data, setData] = useState<ThemeSettingsResponse | null>(null)
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [formValues, setFormValues] = useState<Record<string, string>>({})

  const load = async () => {
    setIsPending(true); setError(null)
    try {
      const res = await themesApi.getSettings()
      if (res.success) {
        setData(res)
        // Initialize form values from current settings
        const vals: Record<string, string> = {}
        for (const [key, opt] of Object.entries(res.data.options)) {
          vals[key] = opt.value
        }
        setFormValues(vals)
      } else setError('Не удалось загрузить настройки темы')
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Ошибка') }
    finally { setIsPending(false) }
  }

  useEffect(() => { load() }, [])

  const save = async () => {
    setSaving(true)
    try {
      await themesApi.updateSettings(formValues)
      load()
    } catch { /* ignore */ }
    finally { setSaving(false) }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Темы</h1>
          <p className="text-sm text-dark-200 mt-1">Настройки активной темы оформления</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw className="w-4 h-4" /> Обновить</Button>
          <Button variant="default" size="sm" onClick={save} disabled={saving}>
            <Save className="w-4 h-4" /> {saving ? 'Сохранение...' : 'Сохранить'}
          </Button>
        </div>
      </div>

      {isPending && <><Skeleton className="h-32 rounded-lg" /><Skeleton className="h-48 rounded-lg" /></>}
      {error && <QueryError message={error} />}

      {!isPending && !error && data && (
        <>
          <Card className="rounded-xl">
            <CardHeader>
              <CardTitle>
                <Palette className="w-4 h-4" />
                {' ' + data.data.theme}
                <Badge className="bg-primary/20 text-primary ml-2">{data.data.label}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(data.data.options).map(([key, opt]) => (
                  <div key={key} className="space-y-2">
                    <Label>{opt.label}</Label>

                    {opt.type === 'select' && opt.options ? (
                      <Select value={formValues[key] || opt.default} onValueChange={(v) => setFormValues({ ...formValues, [key]: v })}>
                        <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {Object.entries(opt.options).map(([val, label]) => (
                            <SelectItem key={val} value={val}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : opt.type === 'textarea' || (opt.rows && opt.rows > 1) ? (
                      <textarea value={formValues[key] || opt.default}
                        onChange={(e) => setFormValues({ ...formValues, [key]: e.target.value })}
                        className="w-full px-3 py-2.5 rounded-xl text-sm"
                        style={{ background: 'var(--surface-card)', border: '1px solid var(--glass-border)', color: '#d1d5db' }}
                        rows={opt.rows || 3} placeholder={opt.hint || ''} />
                    ) : (
                      <Input value={formValues[key] || opt.default}
                        onChange={(e) => setFormValues({ ...formValues, [key]: e.target.value })}
                        placeholder={opt.hint || ''} />
                    )}

                    {opt.hint && <p className="text-xs text-dark-300">{opt.hint}</p>}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
