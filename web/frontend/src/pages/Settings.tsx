import { useEffect, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { settingsApi } from '../api/settings'
import { financeApi } from '../api/finance'
import { themesApi, type ThemeListItem } from '../api/themes'
import { authApi } from '../api/auth'
import { useBrandingStore } from '../store/useBrandingStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { QueryError } from '@/components/QueryError'
import { toast } from 'sonner'
import { ChevronDown, ChevronRight, Save, RefreshCw } from 'lucide-react'

type BasicValues = Record<string, string>

const FALLBACK_THEMES: ThemeListItem[] = [
  { value: 'hexaveil', label: 'HexaVeil (лендинг + блог)' },
  { value: 'default', label: 'Default (блог)' },
]

const EMAIL_RE = /^[^@\s]+@[^@\s]+$/

/** Collapsible settings block — Remnawave-style accordion card. */
function Section({
  title,
  description,
  defaultOpen = false,
  children,
}: {
  title: string
  description?: string
  defaultOpen?: boolean
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  const count = Array.isArray(children) ? children.filter(Boolean).length : 1

  return (
    <Card className="p-0 overflow-hidden animate-fade-in-up">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-4 p-4 md:p-5 hover:bg-[var(--glass-bg)] transition-colors text-left"
      >
        <div className="flex items-center gap-3 min-w-0">
          {open ? (
            <ChevronDown className="w-5 h-5 text-dark-200 shrink-0 transition-transform duration-200" />
          ) : (
            <ChevronRight className="w-5 h-5 text-dark-200 shrink-0 transition-transform duration-200" />
          )}
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-white truncate">{title}</h2>
            {description && <p className="text-xs text-dark-300 mt-0.5">{description}</p>}
          </div>
        </div>
        <span className="text-xs text-dark-300 shrink-0">{count}</span>
      </button>

      {open && (
        <div className="px-4 md:px-5 pb-4 md:pb-5 border-t border-[var(--glass-border)]/50 animate-fade-in-down">
          <div className="divide-y divide-dark-700/50">{children}</div>
        </div>
      )}
    </Card>
  )
}

/** Stacked field row: label + description above the control. */
function FieldRow({
  label,
  description,
  children,
}: {
  label: string
  description?: string
  children: ReactNode
}) {
  return (
    <div className="py-3">
      <Label className="block text-sm text-dark-200 mb-1.5">{label}</Label>
      {children}
      {description && <p className="text-xs text-dark-200 mt-1">{description}</p>}
    </div>
  )
}

/** Inline row: label left, toggle right. */
function SwitchRow({
  label,
  description,
  checked,
  onCheckedChange,
}: {
  label: string
  description?: string
  checked: boolean
  onCheckedChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white">{label}</p>
        {description && <p className="text-xs text-dark-200 mt-0.5">{description}</p>}
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
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
  const [themes, setThemes] = useState<ThemeListItem[]>(FALLBACK_THEMES)

  // Change password
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [savingPassword, setSavingPassword] = useState(false)

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
        site_url: d.site_url || '',
        admin_email: d.admin_email || '',
        admin_title: d.admin_title || '',
        browser_title: d.browser_title || '',
        title_separator: d.title_separator ?? '—',
        favicon_url: d.favicon_url || '',
        timezone: d.timezone || 'Europe/Moscow',
        locale: d.locale || 'ru',
        meta_description: d.meta_description || '',
        meta_keywords: d.meta_keywords || '',
        posts_per_page: d.posts_per_page || '10',
        comments_auto_approve: d.comments_auto_approve || '0',
        maintenance_mode: d.maintenance_mode || '0',
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

      try {
        const tr = await themesApi.list()
        if (tr.success && tr.data?.length) setThemes(tr.data)
      } catch { /* themes optional — keep fallback */ }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    } finally {
      setIsPending(false)
    }
  }

  useEffect(() => { load() }, [])

  const validateBasic = (): string | null => {
    const pp = (basic.posts_per_page || '').trim()
    if (!/^\d+$/.test(pp) || parseInt(pp, 10) <= 0) {
      return '«Постов на страницу» должно быть положительным целым числом'
    }
    const email = (basic.admin_email || '').trim()
    if (email && !EMAIL_RE.test(email)) return 'Некорректный email администратора'
    const urls: Array<[string, string]> = [
      ['URL сайта', basic.site_url || ''],
      ['URL favicon', basic.favicon_url || ''],
    ]
    for (const [label, value] of urls) {
      const val = value.trim()
      if (val && !/^(https?:\/\/|\/)/.test(val)) {
        return `${label}: должен начинаться с http://, https:// или /`
      }
    }
    return null
  }

  const saveBasic = async (tab: string, extra: Record<string, string> = {}) => {
    const validationError = validateBasic()
    if (validationError) { toast.error(validationError); return }
    setSavingTab(tab)
    try {
      const res = await settingsApi.update({ ...basic, ...extra }) as { success: boolean }
      if (res.success !== false) {
        toast.success('Настройки сохранены')
        await load()
        useBrandingStore.getState().load()
      } else {
        toast.error('Не удалось сохранить')
      }
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
      const res = await financeApi.saveSettings(fin) as { success?: boolean }
      if (res.success !== false) { toast.success('Настройки финансов сохранены'); load() }
      else toast.error('Не удалось сохранить')
    } catch { toast.error('Ошибка сохранения') }
    finally { setSavingTab(null) }
  }

  const saveAll = async () => {
    const validationError = validateBasic()
    if (validationError) { toast.error(validationError); return }
    setSavingTab('all')
    try {
      await settingsApi.update({
        ...basic,
        active_theme: basic.active_theme || 'hexaveil',
        docker_config: JSON.stringify(docker),
        loki_config: JSON.stringify(loki),
      })
      try { await financeApi.saveSettings(fin) } catch { /* finance optional */ }
      toast.success('Настройки сохранены')
      await load()
      useBrandingStore.getState().load()
    } catch {
      toast.error('Ошибка сохранения')
    } finally {
      setSavingTab(null)
    }
  }

  const changePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error('Заполните все поля'); return
    }
    if (newPassword.length < 8) {
      toast.error('Новый пароль должен содержать минимум 8 символов'); return
    }
    if (newPassword !== confirmPassword) {
      toast.error('Пароли не совпадают'); return
    }
    setSavingPassword(true)
    try {
      const res = await authApi.changePassword(currentPassword, newPassword) as { success?: boolean; error?: string }
      if (res.success === false) { toast.error(res.error || 'Не удалось сменить пароль'); return }
      toast.success('Пароль изменён')
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } } }
      toast.error(e?.response?.data?.error || 'Ошибка смены пароля')
    } finally {
      setSavingPassword(false)
    }
  }

  if (isPending) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64 rounded-lg" />
        <Skeleton className="h-16 rounded-2xl" />
        <Skeleton className="h-16 rounded-2xl" />
        <Skeleton className="h-16 rounded-2xl" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Настройки</h1>
          <p className="text-dark-200 mt-1 text-sm md:text-base">
            Управление сайтом, темой, финансами и логами
          </p>
        </div>
        <div className="page-header-actions">
          <Button variant="secondary" onClick={load} disabled={savingTab !== null}>
            <RefreshCw className="w-4 h-4 mr-1.5" /> Обновить
          </Button>
          <Button variant="default" onClick={saveAll} disabled={savingTab !== null}>
            <Save className="w-4 h-4 mr-1.5" /> {savingTab === 'all' ? 'Сохранение…' : 'Сохранить всё'}
          </Button>
        </div>
      </div>

      {error && <QueryError message={error} />}

      {!error && (
        <Tabs defaultValue={initialTab}>
          <TabsList>
            <TabsTrigger value="basic">Основные</TabsTrigger>
            <TabsTrigger value="appearance">Внешний вид</TabsTrigger>
            <TabsTrigger value="security">Безопасность</TabsTrigger>
            <TabsTrigger value="finance">Финансы</TabsTrigger>
            <TabsTrigger value="logs">Логи</TabsTrigger>
          </TabsList>

          {/* ── Основные ── */}
          <TabsContent value="basic" className="space-y-2 mt-4">
            <Section title="Брендинг панели" description="Название CMS, заголовок вкладки и favicon" defaultOpen>
              <FieldRow label="Название CMS" description="Отображается в сайдбаре и на странице входа">
                <Input value={basic.admin_title || ''} onChange={(e) => setBasic({ ...basic, admin_title: e.target.value })} placeholder="HexaVeil CMS" />
              </FieldRow>
              <FieldRow label="Заголовок вкладки браузера" description="Если пусто — используется название CMS">
                <Input value={basic.browser_title || ''} onChange={(e) => setBasic({ ...basic, browser_title: e.target.value })} placeholder={basic.admin_title || 'HexaVeil CMS'} />
              </FieldRow>
              <FieldRow label="Разделитель заголовков" description="Например: — или |">
                <Input value={basic.title_separator || ''} onChange={(e) => setBasic({ ...basic, title_separator: e.target.value })} placeholder="—" />
              </FieldRow>
              <FieldRow label="URL favicon" description="Пусто — встроенная иконка">
                <Input value={basic.favicon_url || ''} onChange={(e) => setBasic({ ...basic, favicon_url: e.target.value })} placeholder="/favicon.svg" />
              </FieldRow>
            </Section>

            <Section title="Сайт" description="Название, адрес и контакты проекта">
              <FieldRow label="Название сайта" description="Заголовок публичной части">
                <Input value={basic.site_name || ''} onChange={(e) => setBasic({ ...basic, site_name: e.target.value })} />
              </FieldRow>
              <FieldRow label="Описание сайта">
                <Input value={basic.site_description || ''} onChange={(e) => setBasic({ ...basic, site_description: e.target.value })} />
              </FieldRow>
              <FieldRow label="URL сайта">
                <Input value={basic.site_url || ''} onChange={(e) => setBasic({ ...basic, site_url: e.target.value })} placeholder="https://hexaveil.xyz" />
              </FieldRow>
              <FieldRow label="Email администратора">
                <Input value={basic.admin_email || ''} onChange={(e) => setBasic({ ...basic, admin_email: e.target.value })} placeholder="admin@example.com" />
              </FieldRow>
              <FieldRow label="Часовой пояс">
                <Input value={basic.timezone || ''} onChange={(e) => setBasic({ ...basic, timezone: e.target.value })} placeholder="Europe/Moscow" />
              </FieldRow>
              <FieldRow label="Язык (locale)">
                <Input value={basic.locale || ''} onChange={(e) => setBasic({ ...basic, locale: e.target.value })} placeholder="ru" />
              </FieldRow>
            </Section>

            <Section title="Контент" description="Публикация и комментарии">
              <FieldRow label="Постов на страницу">
                <Input type="number" min={1} value={basic.posts_per_page || '10'} onChange={(e) => setBasic({ ...basic, posts_per_page: e.target.value })} />
              </FieldRow>
              <SwitchRow
                label="Автоодобрение комментариев"
                description="Новые комментарии публикуются без модерации"
                checked={basic.comments_auto_approve === '1'}
                onCheckedChange={(v) => setBasic({ ...basic, comments_auto_approve: v ? '1' : '0' })}
              />
              <SwitchRow
                label="Режим обслуживания"
                description="Публичная часть показывает заглушку"
                checked={basic.maintenance_mode === '1'}
                onCheckedChange={(v) => setBasic({ ...basic, maintenance_mode: v ? '1' : '0' })}
              />
            </Section>

            <Section title="SEO" description="Мета-теги по умолчанию для поисковых систем">
              <FieldRow label="Meta Description" description="SEO-описание по умолчанию">
                <Input value={basic.meta_description || ''} onChange={(e) => setBasic({ ...basic, meta_description: e.target.value })} />
              </FieldRow>
              <FieldRow label="Meta Keywords" description="Ключевые слова через запятую">
                <Input value={basic.meta_keywords || ''} onChange={(e) => setBasic({ ...basic, meta_keywords: e.target.value })} />
              </FieldRow>
            </Section>

            <div className="flex justify-end pt-2">
              <Button variant="default" onClick={() => saveBasic('basic')} disabled={savingTab === 'basic'}>
                <Save className="w-4 h-4 mr-1.5" /> {savingTab === 'basic' ? 'Сохранение…' : 'Сохранить'}
              </Button>
            </div>
          </TabsContent>

          {/* ── Внешний вид ── */}
          <TabsContent value="appearance" className="space-y-2 mt-4">
            <Section title="Тема оформления" description="Оформление публичной части сайта" defaultOpen>
              <FieldRow label="Активная тема" description="Тема, применяемая к лендингу и блогу">
                <Select value={basic.active_theme || 'hexaveil'} onValueChange={(v) => setBasic({ ...basic, active_theme: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {themes.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </FieldRow>
            </Section>
            <div className="flex justify-end pt-2">
              <Button variant="default" onClick={() => saveBasic('appearance', { active_theme: basic.active_theme || 'hexaveil' })} disabled={savingTab === 'appearance'}>
                <Save className="w-4 h-4 mr-1.5" /> {savingTab === 'appearance' ? 'Сохранение…' : 'Сохранить'}
              </Button>
            </div>
          </TabsContent>

          {/* ── Безопасность ── */}
          <TabsContent value="security" className="space-y-2 mt-4">
            <Section title="Смена пароля" description="Пароль текущей учётной записи" defaultOpen>
              <FieldRow label="Текущий пароль">
                <Input type="password" autoComplete="current-password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} placeholder="••••••••" />
              </FieldRow>
              <FieldRow label="Новый пароль" description="Минимум 8 символов">
                <Input type="password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="••••••••" />
              </FieldRow>
              <FieldRow
                label="Повторите новый пароль"
                description={
                  confirmPassword.length === 0
                    ? undefined
                    : newPassword !== confirmPassword
                      ? 'Пароли не совпадают'
                      : newPassword.length >= 8
                        ? 'Пароли совпадают'
                        : undefined
                }
              >
                <Input type="password" autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="••••••••" />
              </FieldRow>
              <div className="pt-3">
                <Button variant="default" onClick={changePassword} disabled={savingPassword} className="w-full">
                  <Save className="w-4 h-4 mr-1.5" /> {savingPassword ? 'Сохранение…' : 'Сменить пароль'}
                </Button>
              </div>
            </Section>
          </TabsContent>

          {/* ── Финансы ── */}
          <TabsContent value="finance" className="space-y-2 mt-4">
            <Section title="Основные настройки" description="Валюта, точность и автообновление" defaultOpen>
              <FieldRow label="Валюта">
                <Input value={fin.currency || ''} onChange={(e) => setFin({ ...fin, currency: e.target.value })} />
              </FieldRow>
              <FieldRow label="Знаков после запятой">
                <Input type="number" value={fin.decimals || '2'} onChange={(e) => setFin({ ...fin, decimals: e.target.value })} />
              </FieldRow>
              <FieldRow label="Автообновление, сек" description="0 — выключено">
                <Input type="number" value={fin.auto_refresh || '0'} onChange={(e) => setFin({ ...fin, auto_refresh: e.target.value })} />
              </FieldRow>
              <FieldRow label="Период средних">
                <Select value={fin.avg_period || 'day'} onValueChange={(v) => setFin({ ...fin, avg_period: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="day">День</SelectItem>
                    <SelectItem value="week">Неделя</SelectItem>
                    <SelectItem value="month">Месяц</SelectItem>
                    <SelectItem value="year">Год</SelectItem>
                  </SelectContent>
                </Select>
              </FieldRow>
            </Section>

            <Section title="Platega" description="Синхронизация платежей Platega">
              <FieldRow label="Merchant ID">
                <Input value={fin.platega_merchant_id || ''} onChange={(e) => setFin({ ...fin, platega_merchant_id: e.target.value })} />
              </FieldRow>
              <FieldRow label="Секрет" description="Оставьте пустым, чтобы не менять сохранённый ключ">
                <Input type="password" value={fin.platega_secret || ''} onChange={(e) => setFin({ ...fin, platega_secret: e.target.value })} placeholder="••••••" />
              </FieldRow>
              <FieldRow label="Дней назад">
                <Input type="number" value={fin.platega_days_back || '5'} onChange={(e) => setFin({ ...fin, platega_days_back: e.target.value })} />
              </FieldRow>
              <FieldRow label="Автоимпорт">
                <Select value={String(fin.platega_auto_sync || '0')} onValueChange={(v) => setFin({ ...fin, platega_auto_sync: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">Выключен</SelectItem>
                    <SelectItem value="1">Включён</SelectItem>
                  </SelectContent>
                </Select>
              </FieldRow>
            </Section>

            <Section title="YooKassa" description="Синхронизация платежей YooKassa">
              <FieldRow label="Shop ID">
                <Input value={fin.yookassa_shop_id || ''} onChange={(e) => setFin({ ...fin, yookassa_shop_id: e.target.value })} />
              </FieldRow>
              <FieldRow label="Секретный ключ" description="Оставьте пустым, чтобы не менять сохранённый ключ">
                <Input type="password" value={fin.yookassa_secret_key || ''} onChange={(e) => setFin({ ...fin, yookassa_secret_key: e.target.value })} placeholder="••••••" />
              </FieldRow>
              <FieldRow label="Дней назад">
                <Input type="number" value={fin.yookassa_days_back || '5'} onChange={(e) => setFin({ ...fin, yookassa_days_back: e.target.value })} />
              </FieldRow>
              <FieldRow label="Автоимпорт">
                <Select value={String(fin.yookassa_auto_sync || '0')} onValueChange={(v) => setFin({ ...fin, yookassa_auto_sync: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">Выключен</SelectItem>
                    <SelectItem value="1">Включён</SelectItem>
                  </SelectContent>
                </Select>
              </FieldRow>
            </Section>

            <div className="flex justify-end pt-2">
              <Button variant="default" onClick={saveFinance} disabled={savingTab === 'finance'}>
                <Save className="w-4 h-4 mr-1.5" /> {savingTab === 'finance' ? 'Сохранение…' : 'Сохранить финансы'}
              </Button>
            </div>
          </TabsContent>

          {/* ── Логи ── */}
          <TabsContent value="logs" className="space-y-2 mt-4">
            <Section title="Docker" description="Просмотр логов контейнеров по SSH" defaultOpen>
              <FieldRow label="SSH хост">
                <Input value={docker.docker_ssh_host || ''} onChange={(e) => setDocker({ ...docker, docker_ssh_host: e.target.value })} />
              </FieldRow>
              <FieldRow label="SSH порт">
                <Input value={docker.docker_ssh_port || '22'} onChange={(e) => setDocker({ ...docker, docker_ssh_port: e.target.value })} />
              </FieldRow>
              <FieldRow label="SSH пользователь">
                <Input value={docker.docker_ssh_user || ''} onChange={(e) => setDocker({ ...docker, docker_ssh_user: e.target.value })} />
              </FieldRow>
              <FieldRow label="Строк на контейнер">
                <Input type="number" value={docker.docker_lines || '100'} onChange={(e) => setDocker({ ...docker, docker_lines: e.target.value })} />
              </FieldRow>
              <FieldRow label="Контейнеры" description="Список через запятую">
                <Input value={docker.docker_containers || ''} onChange={(e) => setDocker({ ...docker, docker_containers: e.target.value })} />
              </FieldRow>
            </Section>

            <Section title="Loki" description="Источник логов Loki">
              <FieldRow label="Loki URL">
                <Input value={loki.loki_url || ''} onChange={(e) => setLoki({ ...loki, loki_url: e.target.value })} />
              </FieldRow>
              <FieldRow label="Query">
                <Input value={loki.loki_query || ''} onChange={(e) => setLoki({ ...loki, loki_query: e.target.value })} />
              </FieldRow>
              <FieldRow label="Пользователь">
                <Input value={loki.loki_user || ''} onChange={(e) => setLoki({ ...loki, loki_user: e.target.value })} />
              </FieldRow>
              <FieldRow label="Лимит записей">
                <Input type="number" value={loki.loki_limit || '100'} onChange={(e) => setLoki({ ...loki, loki_limit: e.target.value })} />
              </FieldRow>
            </Section>

            <div className="flex justify-end pt-2">
              <Button variant="default" onClick={saveLogs} disabled={savingTab === 'logs'}>
                <Save className="w-4 h-4 mr-1.5" /> {savingTab === 'logs' ? 'Сохранение…' : 'Сохранить'}
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
