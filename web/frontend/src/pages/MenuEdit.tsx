import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { menusApi, MenuItem } from '../api/menus'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { Loader2 } from 'lucide-react'

const LOCATION_LABEL: Record<string, string> = {
  main: 'Главное меню',
  footer: 'Подвал',
}

export default function MenuEdit() {
  const navigate = useNavigate()
  const params = useParams()
  const isEdit = !!params.id
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [location, setLocation] = useState('main')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        if (isEdit && params.id) {
          const res = await menusApi.get(parseInt(params.id)) as { success: boolean; data: MenuItem }
          if (!cancelled && res.success) {
            const m = res.data
            setName(m.name || '')
            setUrl(m.url || '')
            setLocation(m.location || 'main')
          } else if (!cancelled) setError('Пункт меню не найден')
        }
      } catch (err: unknown) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Ошибка загрузки')
      } finally { if (!cancelled) setIsPending(false) }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const save = async () => {
    if (!name.trim() || !url.trim()) return
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        name: name.trim(), url: url.trim(), location,
      }
      if (isEdit && params.id) await menusApi.update(parseInt(params.id), payload)
      else {
        const res = await menusApi.create(payload) as { success: boolean; data?: { id: number } }
        if (res.success && res.data?.id) { navigate(`/menus/${res.data.id}`); setSaving(false); return }
      }
      navigate('/menus')
    } catch { /* ignore */ }
    finally { setSaving(false) }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <button onClick={() => navigate('/menus')} className="text-sm text-dark-300 hover:text-dark-100 transition-colors mb-1 block bg-transparent border-0 p-0 cursor-pointer">← Назад к списку</button>
          <h1 className="text-2xl font-bold text-white tracking-tight">{isEdit ? 'Редактировать пункт меню' : 'Создать пункт меню'}</h1>
          <p className="text-sm text-dark-200 mt-1">{isEdit ? 'Редактирование пункта навигации сайта' : 'Новый пункт навигации сайта'}</p>
        </div>
      </div>

      {isPending && <><Skeleton className="h-12 rounded-lg" /><Skeleton className="h-40 rounded-lg" /></>}
      {error && <QueryError message={error} />}

      {!isPending && !error && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
          <div className="space-y-5">
            <Card className="rounded-xl">
              <CardHeader><CardTitle>Пункт меню</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Название *</Label>
                  <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Главная" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="url">URL *</Label>
                  <Input id="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="/about" />
                  <p className="text-xs text-dark-300">Относительный путь (например /blog) или полный URL</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="rounded-xl">
              <CardHeader><CardTitle>Расположение</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-2">
                  <Label>Меню</Label>
                  <Select value={location} onValueChange={setLocation}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(LOCATION_LABEL).map(([k, v]) => (
                        <SelectItem key={k} value={k}>{v}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            <div className="space-y-3">
              <Button variant="default" className="w-full" onClick={save} disabled={saving || !name.trim() || !url.trim()}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null} {isEdit ? 'Сохранить' : 'Создать'}
              </Button>
              <Button variant="ghost" className="w-full" onClick={() => navigate('/menus')}>Отмена</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
