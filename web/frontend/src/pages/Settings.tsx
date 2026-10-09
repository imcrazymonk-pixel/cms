import { useEffect, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { settingsApi } from '../api/settings'
import { financeApi } from '../api/finance'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { QueryError } from '@/components/QueryError'
import { toast } from 'sonner'
import { Settings as SettingsIcon, Save, RefreshCw, Palette, Wallet, Terminal } from 'lucide-react'

type BasicValues = Record<string, string>

const THEMES = [
  { value: 'hexaveil', label: 'HexaVeil (лендинг + блог)' },
  { value: 'modern', label: 'Modern (блог)' },
  { value: 'minimal', label: 'Minimal (блог)' },
  { value: 'default', label: 'Default (блог)' },
]

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
      {hint && <p className="text-xs text-dark-300">{hint}</p>}
    </div>
  )
}

export default function Settings() {
  const [searchParams] = useSearchParams()
  const initialTab = searchParams.get('tab') || 'basic'
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [savingTab, setSavingTab] = useState<string | null>(null)

  const [basic, setBasic] = useState<BasicValues>({})
  const [docker, setDocker] = useState<BasicValues>({})
  const [loki, setLoki] = useState<BasicValues>({})
  const [fin, setFin] = useState<BasicValues>({})
  const [useReactAdmin, setUseReactAdmin] = useState(true)

  const load = async () => {
    setIsPending(true)
    setError(null)
    try {
      const res = await settingsApi.getAll() as { success: boolean; data: Record<string, string> }
      if (!res.success) { setError('Не удалось загрузить настройки'); return }
      const d = res.data || {}
      setBasic({
        site_name: d.site_name || '',
        site_description: d.site_description || '',
        meta_description: d.meta_description || '',
        meta_keywords: d.meta_keywords || '',
        posts_per_page: d.posts_per_page || '10',
        active_theme: d.active_theme || 'hexaveil',
      })
      try {
        const dc = d.docker_config ? JSON.parse(d.docker_config) : {}
        setDocker({
          docker_ssh_host: dc.docker_ssh_host || '',
          docker_ssh_user: dc.docker_ssh_user || '',
          docker_ssh_port: dc.docker_ssh_port || '22',
          docker_lines: dc.docker_lines || '100',
          docker_containers: dc.docker_containers || '',
        })
      } catch { setDocker({ docker_ssh_host: '', docker_ssh_user: '', docker_ssh_port: '22', docker_lines: '100', docker_containers: '' }) }
      try {
        const lk = d.loki_config ? JSON.parse(d.loki_config) : {}
        setLoki({
          loki_url: lk.loki_url || '',
          loki_query: lk.loki_query || '{job="varlog"}',
          loki_user: lk.loki_user || '',
          loki_limit: lk.loki_limit || '100',
        })
      } catch { setLoki({ loki_url: '', loki_query: '{job="varlog"}', loki_user: '', loki_limit: '100' }) }

      try {
        const f = await financeApi.getSettings() as Record<string, string>
        setFin({
          currency: f.currency ?? '₽',
          decimals: f.decimals ?? '2',
          auto_refresh: f.auto_refresh ?? '0',
          avg_period: f.avg_period ?? 'day',
          platega_merchant_id: f.platega_merchant_id ?? '',
          platega_secret: '',
          platega_days_back: f.platega_days_back ?? '5',
          platega_auto_sync: f.platega_auto_sync ?? '0',
          yookassa_shop_id: f.yookassa_shop_id ?? '',
          yookassa_secret_key: '',
          yookassa_days_back: f.yookassa_days_back ?? '5',
          yookassa_auto_sync: f.yookassa_auto_sync ?? '0',
        })
      } catch { /* finance settings optional */ }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    } finally {
      setIsPending(false)
    }
  }

  useEffect(() => { load() }, [])

  const saveBasic = async (tab: string, extra: Record<string, string> = {}) => {
    setSavingTab(tab)
    try {
      const res = await settingsApi.update({ ...basic, ...extra }) as { success: boolean }
      if (res.success) { toast.success('Настройки сохранены'); load() }
      else toast.error('Не удалось сохранить')
    } catch { toast.error('Ошибка сохранения') }
    finally { setSavingTab(null) }
  }

  const saveLogs = () => saveBasic('logs', {
    docker_config: JSON.stringify(docker),
    loki_config: JSON.stringify(loki),
  })

  const saveFinance = async () => {
    setSavingTab('finance')
    try {
      const res = await financeApi.saveSettings(fin) as { success: boolean }
      if (res.success !== false) { toast.success('Настройки финансов сохранены'); load() }
      else toast.error('Не удалось сохранить')
    } catch { toast.error('Ошибка сохранения') }
    finally { setSavingTab(null) }
  }

  const toggleReactAdmin = async (enabled: boolean) => {
    setUseReactAdmin(enabled)
    try {
      await fetch('/admin/settings/save-preference', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: 'use_react_admin', value: enabled ? '1' : '0' }),
      })
    } catch { /* ignore */ }
  }

  const saveAll = async () => {
    setSavingTab('all')
    try {
      await settingsApi.update({
        ...basic,
        active_theme: basic.active_theme || 'hexaveil',
        docker_config: JSON.stringify(docker),
        loki_config: JSON.stringify(loki),
      })
      try { await financeApi.saveSettings(fin) } catch { /* finance optional */ }
      await toggleReactAdmin(useReactAdmin)
      toast.success('Настройки сохранены')
      load()
    } catch {
      toast.error('Ошибка сохранения')
    } finally {
      setSavingTab(null)
    }
  }

  if (isPending) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-10 w-64 rounded-lg" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Настройки</h1>
          <p className="text-sm text-dark-200 mt-1">Управление сайтом, темой, финансами и логами</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw className="w-4 h-4" /> Обновить</Button>
          <Button variant="default" size="sm" onClick={saveAll} disabled={savingTab !== null}>
            <Save className="w-4 h-4" /> {savingTab === 'all' ? 'Сохранение…' : 'Сохранить всё'}
          </Button>
        </div>
      </div>

      {error && <QueryError message={error} />}

      {!error && (
        <Tabs defaultValue={initialTab}>
          <TabsList>
            <TabsTrigger value="basic"><SettingsIcon className="w-4 h-4" /> Основные</TabsTrigger>
            <TabsTrigger value="appearance"><Palette className="w-4 h-4" /> Внешний вид</TabsTrigger>
            <TabsTrigger value="finance"><Wallet className="w-4 h-4" /> Финансы</TabsTrigger>
            <TabsTrigger value="logs"><Terminal className="w-4 h-4" /> Логи</TabsTrigger>
          </TabsList>

          {/* ── Основные ── */}
          <TabsContent value="basic" className="space-y-4">
            <Card className="rounded-xl max-w-3xl">
              <CardHeader><CardTitle><SettingsIcon className="w-4 h-4" /> Основные настройки</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <Field label="Название сайта" hint="Отображается в заголовке вкладки браузера">
                  <Input value={basic.site_name || ''} onChange={(e) => setBasic({ ...basic, site_name: e.target.value })} />
                </Field>
                <Field label="Описание сайта">
                  <Input value={basic.site_description || ''} onChange={(e) => setBasic({ ...basic, site_description: e.target.value })} />
                </Field>
                <Field label="Meta Description" hint="SEO-описание по умолчанию">
                  <Input value={basic.meta_description || ''} onChange={(e) => setBasic({ ...basic, meta_description: e.target.value })} />
                </Field>
                <Field label="Meta Keywords" hint="Ключевые слова через запятую">
                  <Input value={basic.meta_keywords || ''} onChange={(e) => setBasic({ ...basic, meta_keywords: e.target.value })} />
                </Field>
                <Field label="Постов на страницу">
                  <Input type="number" value={basic.posts_per_page || '10'} onChange={(e) => setBasic({ ...basic, posts_per_page: e.target.value })} />
                </Field>
                <div className="flex justify-end pt-2">
                  <Button variant="default" onClick={() => saveBasic('basic')} disabled={savingTab === 'basic'}>
                    <Save className="w-4 h-4" /> {savingTab === 'basic' ? 'Сохранение…' : 'Сохранить'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Внешний вид ── */}
          <TabsContent value="appearance" className="space-y-4">
            <Card className="rounded-xl max-w-3xl">
              <CardHeader><CardTitle><Palette className="w-4 h-4" /> Тема оформления</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <Field label="Активная тема" hint="Тема публичной части сайта">
                  <Select value={basic.active_theme || 'hexaveil'} onValueChange={(v) => setBasic({ ...basic, active_theme: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {THEMES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </Field>
                <div className="flex justify-end pt-2">
                  <Button variant="default" onClick={() => saveBasic('appearance', { active_theme: basic.active_theme || 'hexaveil' })} disabled={savingTab === 'appearance'}>
                    <Save className="w-4 h-4" /> {savingTab === 'appearance' ? 'Сохранение…' : 'Сохранить'}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-xl max-w-3xl">
              <CardHeader><CardTitle><SettingsIcon className="w-4 h-4" /> Панель управления</CardTitle></CardHeader>
              <CardContent>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input type="checkbox" className="mt-1 w-4 h-4" checked={useReactAdmin} onChange={(e) => toggleReactAdmin(e.target.checked)} />
                  <span>
                    <span className="text-sm text-white">Новая панель управления (React)</span>
                    <span className="block text-xs text-dark-300">Включено — админка в стиле Remnawave. Выключено — старая PHP-панель.</span>
                  </span>
                </label>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Финансы ── */}
          <TabsContent value="finance" className="space-y-4">
            <Card className="rounded-xl max-w-3xl">
              <CardHeader><CardTitle><Wallet className="w-4 h-4" /> Основные настройки финансов</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Валюта">
                    <Input value={fin.currency || ''} onChange={(e) => setFin({ ...fin, currency: e.target.value })} />
                  </Field>
                  <Field label="Знаков после запятой">
                    <Input type="number" value={fin.decimals || '2'} onChange={(e) => setFin({ ...fin, decimals: e.target.value })} />
                  </Field>
                  <Field label="Автообновление (сек)">
                    <Input type="number" value={fin.auto_refresh || '0'} onChange={(e) => setFin({ ...fin, auto_refresh: e.target.value })} />
                  </Field>
                  <Field label="Период средних">
                    <Select value={fin.avg_period || 'day'} onValueChange={(v) => setFin({ ...fin, avg_period: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="day">День</SelectItem>
                        <SelectItem value="week">Неделя</SelectItem>
                        <SelectItem value="month">Месяц</SelectItem>
                        <SelectItem value="year">Год</SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-xl max-w-3xl">
              <CardHeader><CardTitle>Platega</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <Field label="Merchant ID">
                  <Input value={fin.platega_merchant_id || ''} onChange={(e) => setFin({ ...fin, platega_merchant_id: e.target.value })} />
                </Field>
                <Field label="Секрет" hint="Оставьте пустым, чтобы не менять сохранённый ключ">
                  <Input type="password" value={fin.platega_secret || ''} onChange={(e) => setFin({ ...fin, platega_secret: e.target.value })} placeholder="••••••" />
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Дней назад">
                    <Input type="number" value={fin.platega_days_back || '5'} onChange={(e) => setFin({ ...fin, platega_days_back: e.target.value })} />
                  </Field>
                  <Field label="Автоимпорт">
                    <Select value={String(fin.platega_auto_sync || '0')} onValueChange={(v) => setFin({ ...fin, platega_auto_sync: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0">Выключен</SelectItem>
                        <SelectItem value="1">Включён</SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-xl max-w-3xl">
              <CardHeader><CardTitle>YooKassa</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <Field label="Shop ID">
                  <Input value={fin.yookassa_shop_id || ''} onChange={(e) => setFin({ ...fin, yookassa_shop_id: e.target.value })} />
                </Field>
                <Field label="Секретный ключ" hint="Оставьте пустым, чтобы не менять сохранённый ключ">
                  <Input type="password" value={fin.yookassa_secret_key || ''} onChange={(e) => setFin({ ...fin, yookassa_secret_key: e.target.value })} placeholder="••••••" />
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Дней назад">
                    <Input type="number" value={fin.yookassa_days_back || '5'} onChange={(e) => setFin({ ...fin, yookassa_days_back: e.target.value })} />
                  </Field>
                  <Field label="Автоимпорт">
                    <Select value={String(fin.yookassa_auto_sync || '0')} onValueChange={(v) => setFin({ ...fin, yookassa_auto_sync: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0">Выключен</SelectItem>
                        <SelectItem value="1">Включён</SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-end max-w-3xl">
              <Button variant="default" onClick={saveFinance} disabled={savingTab === 'finance'}>
                <Save className="w-4 h-4" /> {savingTab === 'finance' ? 'Сохранение…' : 'Сохранить финансы'}
              </Button>
            </div>
          </TabsContent>

          {/* ── Логи ── */}
          <TabsContent value="logs" className="space-y-4">
            <Card className="rounded-xl max-w-3xl">
              <CardHeader><CardTitle><Terminal className="w-4 h-4" /> Docker (просмотр логов)</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Field label="SSH хост">
                    <Input value={docker.docker_ssh_host || ''} onChange={(e) => setDocker({ ...docker, docker_ssh_host: e.target.value })} />
                  </Field>
                  <Field label="SSH порт">
                    <Input value={docker.docker_ssh_port || '22'} onChange={(e) => setDocker({ ...docker, docker_ssh_port: e.target.value })} />
                  </Field>
                  <Field label="SSH пользователь">
                    <Input value={docker.docker_ssh_user || ''} onChange={(e) => setDocker({ ...docker, docker_ssh_user: e.target.value })} />
                  </Field>
                  <Field label="Строк на контейнер">
                    <Input type="number" value={docker.docker_lines || '100'} onChange={(e) => setDocker({ ...docker, docker_lines: e.target.value })} />
                  </Field>
                </div>
                <Field label="Контейнеры" hint="Список через запятую">
                  <Input value={docker.docker_containers || ''} onChange={(e) => setDocker({ ...docker, docker_containers: e.target.value })} />
                </Field>
              </CardContent>
            </Card>

            <Card className="rounded-xl max-w-3xl">
              <CardHeader><CardTitle><Terminal className="w-4 h-4" /> Loki</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <Field label="Loki URL">
                  <Input value={loki.loki_url || ''} onChange={(e) => setLoki({ ...loki, loki_url: e.target.value })} />
                </Field>
                <Field label="Query">
                  <Input value={loki.loki_query || ''} onChange={(e) => setLoki({ ...loki, loki_query: e.target.value })} />
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Пользователь">
                    <Input value={loki.loki_user || ''} onChange={(e) => setLoki({ ...loki, loki_user: e.target.value })} />
                  </Field>
                  <Field label="Лимит записей">
                    <Input type="number" value={loki.loki_limit || '100'} onChange={(e) => setLoki({ ...loki, loki_limit: e.target.value })} />
                  </Field>
                </div>
                <div className="flex justify-end pt-2">
                  <Button variant="default" onClick={saveLogs} disabled={savingTab === 'logs'}>
                    <Save className="w-4 h-4" /> {savingTab === 'logs' ? 'Сохранение…' : 'Сохранить'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
