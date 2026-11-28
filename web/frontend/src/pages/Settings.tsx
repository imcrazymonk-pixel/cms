import { useEffect, useId, useMemo, useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { settingsApi, type RegistryItem } from '../api/settings'
import { themesApi, type ThemeListItem, type ThemeGroup } from '../api/themes'
import { authApi } from '../api/auth'
import { useBrandingStore } from '../store/useBrandingStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { QueryError } from '@/components/QueryError'
import { EmptyState } from '@/components/EmptyState'
import { toast } from 'sonner'
import { ChevronDown, ChevronRight, Save, RefreshCw, Database, Zap, Check, X, Search, HardDrive } from 'lucide-react'

type Values = Record<string, string>

const CATEGORY_DESC: Record<string, string> = {
  'Общие': 'Название, адрес и контакты проекта',
  'Контент': 'Публикация и комментарии',
  'SEO': 'Мета-теги по умолчанию',
  'Внешний вид': 'Оформление публичной части',
  'Финансы': 'Валюта, точность и расчёт средних',
  'Platega': 'Синхронизация платежей Platega',
  'YooKassa': 'Синхронизация платежей YooKassa',
  'Сайт': 'Название, адрес и оформление публичного сайта',
  'Bedolaga Bot': 'Bot Web API: токен, таймаут и прокси',
  'Telegram / Саппорт': 'Бот поддержки, поллер и прокси',
  'ИИ / Саппорт': 'Режим ответов, порог уверенности, пауза помощника',
  'Bedolaga БД': 'Read-only PostgreSQL с тарифами (TCP, прокси не применим)',
  'Бэкапы': 'Хранилища и уровни резервного копирования',
  'Прокси по умолчанию': 'Общий прокси для интеграций и исключения',
}

/** Collapsible settings block — Remnawave-style accordion card. */
function Section({
  id,
  title,
  description,
  defaultOpen = false,
  action,
  children,
}: {
  id?: string
  title: string
  description?: string
  defaultOpen?: boolean
  action?: ReactNode
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  const generatedId = useId()
  const sectionId = id ?? generatedId
  const headerId = `${sectionId}-header`
  const panelId = `${sectionId}-panel`
  const count = Array.isArray(children) ? children.filter(Boolean).length : 1

  useEffect(() => {
    if (defaultOpen) setOpen(true)
  }, [defaultOpen])

  return (
    <Card id={sectionId} className="p-0 overflow-hidden animate-fade-in-up">
      <div className="w-full flex items-center gap-3 p-4 md:p-5 hover:bg-[var(--glass-bg)] transition-colors text-left">
        <button
          type="button"
          id={headerId}
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-3 min-w-0 flex-1 text-left"
        >
          {open ? (
            <ChevronDown className="w-5 h-5 text-dark-200 shrink-0 transition-transform duration-200" />
          ) : (
            <ChevronRight className="w-5 h-5 text-dark-200 shrink-0 transition-transform duration-200" />
          )}
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-white truncate">{title}</h2>
            {description && <p className="text-xs text-dark-300 mt-0.5">{description}</p>}
          </div>
        </button>
        {action && <div className="shrink-0">{action}</div>}
        <span className="text-xs text-dark-300 shrink-0">{count}</span>
      </div>
      {open && (
        <div
          id={panelId}
          role="region"
          aria-labelledby={headerId}
          className="px-4 md:px-5 pb-4 md:pb-5 border-t border-[var(--glass-border)]/50 animate-fade-in-down"
        >
          <div className="divide-y divide-dark-700/50">{children}</div>
        </div>
      )}
    </Card>
  )
}

function SearchBar({ value, onChange, count }: { value: string; onChange: (v: string) => void; count: number }) {
  return (
    <div className="animate-fade-in-up">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-300 pointer-events-none" />
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Поиск настроек..."
          className="pl-10 pr-10"
          autoComplete="off"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-dark-300 hover:text-dark-100"
            aria-label="Очистить"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      {value && <p className="text-xs text-dark-200 mt-1 ml-1">Найдено: {count}</p>}
    </div>
  )
}

function Legend() {
  return (
    <Card className="animate-fade-in-up">
      <div className="p-4 md:p-5">
        <h3 className="text-xs font-medium text-dark-300 uppercase tracking-wider mb-2">Обозначения</h3>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-dark-200">
          <span className="inline-flex items-center gap-1.5"><SourceBadge source="db" /> значение из базы</span>
          <span className="inline-flex items-center gap-1.5"><SourceBadge source="env" /> переопределено в .env</span>
          <span className="inline-flex items-center gap-1.5"><SourceBadge source="default" /> значение по умолчанию</span>
          <span className="inline-flex items-center gap-1.5"><X className="w-3.5 h-3.5" /> сбросить к значению по умолчанию</span>
        </div>
      </div>
    </Card>
  )
}

function SourceBadge({ source }: { source: RegistryItem['source'] }) {
  if (source === 'db') {
    return (
      <Badge variant="default" className="gap-1 text-[10px] px-1.5 py-0.5">
        <Database className="w-2.5 h-2.5" /> БД
      </Badge>
    )
  }
  if (source === 'env') {
    return (
      <Badge variant="warning" className="gap-1 text-[10px] px-1.5 py-0.5">
        <Zap className="w-2.5 h-2.5" /> .env
      </Badge>
    )
  }
  return <Badge variant="secondary" className="text-[10px] px-1.5 py-0.5">по умолч.</Badge>
}

function MetaBadges({ item, isSaving, wasSaved, onReset }: {
  item: RegistryItem
  isSaving: boolean
  wasSaved: boolean
  onReset: (key: string) => void
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <SourceBadge source={item.source} />
      {item.is_secret && item.is_set && (
        <span className="text-[10px] text-green-400" title="Секрет задан">●</span>
      )}
      {isSaving && <RefreshCw className="w-3.5 h-3.5 text-cyan-400 animate-spin" />}
      {wasSaved && !isSaving && <Check className="w-3.5 h-3.5 text-green-400" />}
      {item.source === 'db' && (
        <button
          type="button"
          onClick={() => onReset(item.key)}
          title="Сбросить к значению по умолчанию"
          className="text-dark-300 hover:text-red-400 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </span>
  )
}

const SELECT_LABELS: Record<string, string> = {
  inherit: 'Как по умолчанию',
  direct: 'Напрямую',
  custom: 'Свой прокси',
  auto: 'Авто',
  on: 'Включено',
  off: 'Выключено',
}

/** Категории вкладки «Интеграции» → id эндпоинта проверки. */
const INTEGRATION_TEST_IDS: Record<string, string> = {
  'Bedolaga Bot': 'bedolaga',
  'Telegram / Саппорт': 'support',
  'Bedolaga БД': 'bot_db',
  Platega: 'platega',
  YooKassa: 'yookassa',
  'Прокси по умолчанию': 'global',
}

/** Deep-link `from` (Sidebar) → категория вкладки «Интеграции»/«Поддержка». */
const FROM_TO_CATEGORY: Record<string, string> = {
  bedolaga: 'Bedolaga Bot',
  support: 'Telegram / Саппорт',
  support_ai: 'ИИ / Саппорт',
  bot_db: 'Bedolaga БД',
  platega: 'Platega',
  yookassa: 'YooKassa',
  proxy: 'Прокси по умолчанию',
}

/** Deep-link `from` → вкладка настроек: саппорт-категории живут во вкладке «Поддержка». */
const tabForFrom = (from: string): string => {
  if (!from) return 'basic'
  return from === 'support' || from === 'support_ai' ? 'support' : 'integrations'
}

/** Категория → ASCII-якорь DOM (без кириллицы и пробелов). */
const CATEGORY_ANCHOR: Record<string, string> = {
  'Bedolaga Bot': 'settings-cat-bedolaga',
  'Telegram / Саппорт': 'settings-cat-support',
  'ИИ / Саппорт': 'support-ai',
  'Bedolaga БД': 'settings-cat-bot-db',
  Platega: 'settings-cat-platega',
  YooKassa: 'settings-cat-yookassa',
  'Прокси по умолчанию': 'settings-cat-proxy',
}

/** Ключи интеграций, после изменения которых кэш Bedolaga / support устаревает. */
const isIntegrationKey = (key: string) =>
  key.startsWith('bedolaga_') ||
  key.startsWith('bot_db_') ||
  key.startsWith('support_') ||
  key.startsWith('outbound_proxy_')

/** Префиксы react-query, которые зависят от живой конфигурации интеграций. */
const BEDOLAGA_QUERY_KEYS: string[][] = [
  ['bedolaga-status'],
  ['bedolaga-overview'],
  ['bedolaga-full'],
  ['bedolaga-health'],
  ['bedolaga-tariffs'],
  ['bedolaga-capabilities'],
  ['bedolaga-maintenance'],
  ['bedolaga-customers'],
  ['bedolaga-analytics-overview'],
  ['bedolaga-analytics-forecast'],
  ['bedolaga-analytics-tariffs'],
  ['support-pollers'],
  ['support-config-status'],
]

/** После теста этих интеграций кэши инвалидируются и при ошибке тоже. */
const TEST_INVALIDATES: ReadonlySet<string> = new Set(['bedolaga', 'bot_db', 'support', 'global'])

function SettingItem({
  item, value, isSaving, wasSaved, themes, onSave, onReset, onChange,
}: {
  item: RegistryItem
  value: string
  isSaving: boolean
  wasSaved: boolean
  themes: ThemeListItem[]
  onSave: (key: string, value: string) => void
  onReset: (key: string) => void
  onChange: (key: string, value: string) => void
}) {
  const meta = <MetaBadges item={item} isSaving={isSaving} wasSaved={wasSaved} onReset={onReset} />

  if (item.type === 'bool') {
    return (
      <div className="flex items-center justify-between gap-4 py-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm text-white">{item.label}</p>
            {meta}
          </div>
          {item.description && <p className="text-xs text-dark-200 mt-0.5">{item.description}</p>}
        </div>
        <Switch
          checked={value === '1' || value === 'true'}
          onCheckedChange={(v) => onSave(item.key, v ? '1' : '0')}
          disabled={isSaving || item.is_readonly}
        />
      </div>
    )
  }

  if (item.type === 'select') {
    const opts = item.options
      ? item.options.map((o) => ({ value: o, label: SELECT_LABELS[o] ?? o }))
      : item.options_source === 'themes'
        ? themes.map((t) => ({ value: t.value, label: t.label }))
        : []
    return (
      <div className="py-3">
        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
          <Label className="text-sm text-dark-200">{item.label}</Label>
          {meta}
        </div>
        <Select value={value} onValueChange={(v) => onSave(item.key, v)} disabled={isSaving || item.is_readonly}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {opts.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
          </SelectContent>
        </Select>
        {item.description && <p className="text-xs text-dark-200 mt-1">{item.description}</p>}
      </div>
    )
  }

  const changed = value !== (item.value || '')
  return (
    <div className="py-3">
      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
        <Label className="text-sm text-dark-200">{item.label}</Label>
        {meta}
      </div>
      <div className="flex gap-2">
        {item.type === 'textarea' || item.type === 'json' ? (
          <Textarea
            value={value}
            onChange={(e) => onChange(item.key, e.target.value)}
            rows={item.type === 'json' ? 4 : 3}
            className={item.type === 'json' ? 'flex-1 font-mono text-xs' : 'flex-1'}
            disabled={isSaving || item.is_readonly}
          />
        ) : (
          <Input
            type={item.type === 'secret' ? 'password' : item.type === 'number' ? 'number' : 'text'}
            value={value}
            onChange={(e) => onChange(item.key, e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && value !== (item.value || '')) {
                e.preventDefault()
                onSave(item.key, value)
              }
            }}
            className="flex-1"
            disabled={isSaving || item.is_readonly}
            placeholder={
              item.is_secret ? (item.is_set ? '•••••••• (задано)' : '••••••••') : (item.default || '')
            }
          />
        )}
        {changed && (
          <Button size="sm" onClick={() => onSave(item.key, value)} disabled={isSaving} className="shrink-0">
            Сохранить
          </Button>
        )}
      </div>
      {item.description && <p className="text-xs text-dark-200 mt-1">{item.description}</p>}
    </div>
  )
}

export default function Settings() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fromParam = searchParams.get('from') || ''
  const initialTab = searchParams.get('tab') || tabForFrom(fromParam)
  const [tab, setTab] = useState(initialTab)
  const focusCategory = tab === 'integrations' || tab === 'support'
    ? (FROM_TO_CATEGORY[fromParam] || '')
    : ''
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [items, setItems] = useState<RegistryItem[]>([])
  const [pending, setPending] = useState<Values>({})
  const [savingKeys, setSavingKeys] = useState<Set<string>>(new Set())
  const [savedKeys, setSavedKeys] = useState<Set<string>>(new Set())
  const [savingTab, setSavingTab] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [testing, setTesting] = useState<string | null>(null)

  const [docker, setDocker] = useState<Values>({})
  const [loki, setLoki] = useState<Values>({})
  const [themes, setThemes] = useState<ThemeListItem[]>([])
  const [themeGroups, setThemeGroups] = useState<ThemeGroup[]>([])
  const [themeValues, setThemeValues] = useState<Values>({})
  const [savingTheme, setSavingTheme] = useState(false)

  // Change password
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [savingPassword, setSavingPassword] = useState(false)

  const effective = (it: RegistryItem) => pending[it.key] ?? it.value

  const load = async () => {
    setIsPending(true)
    setError(null)
    try {
      const res = await settingsApi.getAll()
      if (!res.success) { setError('Не удалось загрузить настройки'); return }
      setItems(res.items || [])
      setPending({})
      const d = res.data || {}
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
        const tr = await themesApi.list()
        setThemes(tr.success ? tr.data : [])
      } catch { /* themes optional */ }
      await loadThemeOptions()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    } finally {
      setIsPending(false)
    }
  }

  const loadThemeOptions = async () => {
    try {
      const ts = await themesApi.getSettings()
      const groups = ts.data?.groups || []
      setThemeGroups(groups)
      const vals: Values = {}
      for (const g of groups) {
        for (const [k, o] of Object.entries(g.options)) vals[k] = o.value
      }
      setThemeValues(vals)
    } catch { /* theme options optional */ }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    setTab(searchParams.get('tab') || tabForFrom(searchParams.get('from') || ''))
  }, [searchParams])

  // Deep-link из другого раздела не должен наследовать старый поиск:
  // иначе `from` фокусирует категорию, а прежний запрос скрывает все блоки.
  useEffect(() => {
    setSearch('')
  }, [fromParam])

  useEffect(() => {
    if (!focusCategory || isPending) return
    const anchor = CATEGORY_ANCHOR[focusCategory]
    if (!anchor) return
    const frame = requestAnimationFrame(() => {
      document.getElementById(anchor)?.scrollIntoView({ block: 'start', behavior: 'smooth' })
    })
    return () => cancelAnimationFrame(frame)
  }, [focusCategory, isPending, items.length])

  const byTab = useMemo(() => {
    const res: Record<string, Record<string, RegistryItem[]>> = {}
    for (const it of items) {
      res[it.tab] = res[it.tab] || {}
      res[it.tab][it.category] = res[it.tab][it.category] || []
      res[it.tab][it.category].push(it)
    }
    return res
  }, [items])

  const applySaved = (saved?: RegistryItem) => {
    if (!saved) return
    setItems((prev) => prev.map((it) => (it.key === saved.key ? saved : it)))
    setPending((prev) => { const n = { ...prev }; delete n[saved.key]; return n })
  }

  const flashSaved = (key: string) => {
    setSavedKeys((prev) => new Set(prev).add(key))
    setTimeout(() => setSavedKeys((prev) => { const n = new Set(prev); n.delete(key); return n }), 2000)
  }

  const invalidateBedolagaRuntime = () => {
    for (const queryKey of BEDOLAGA_QUERY_KEYS) {
      queryClient.invalidateQueries({ queryKey })
    }
  }

  const onSave = async (key: string, value: string) => {
    setSavingKeys((prev) => new Set(prev).add(key))
    try {
      const res = await settingsApi.setKey(key, value)
      if (res.success === false) { toast.error((res as { error?: string }).error || 'Не удалось сохранить'); return }
      applySaved(res.data)
      flashSaved(key)
      // branding depends on admin_title/browser_title — refresh it silently
      if (key === 'admin_title' || key === 'browser_title' || key === 'title_separator' || key === 'favicon_url') {
        useBrandingStore.getState().load()
      }
      // switching the active theme changes the available theme options
      if (key === 'active_theme') {
        await loadThemeOptions()
      }
      if (isIntegrationKey(key)) invalidateBedolagaRuntime()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } } }
      toast.error(e?.response?.data?.error || 'Ошибка сохранения')
    } finally {
      setSavingKeys((prev) => { const n = new Set(prev); n.delete(key); return n })
    }
  }

  const onReset = async (key: string) => {
    setSavingKeys((prev) => new Set(prev).add(key))
    try {
      const res = await settingsApi.resetKey(key)
      if (res.success === false) { toast.error('Не удалось сбросить'); return }
      applySaved(res.data)
      flashSaved(key)
      if (key === 'admin_title' || key === 'browser_title' || key === 'title_separator' || key === 'favicon_url') {
        useBrandingStore.getState().load()
      }
      if (isIntegrationKey(key)) invalidateBedolagaRuntime()
    } catch {
      toast.error('Ошибка сброса')
    } finally {
      setSavingKeys((prev) => { const n = new Set(prev); n.delete(key); return n })
    }
  }

  const onChange = (key: string, value: string) => {
    setPending((prev) => ({ ...prev, [key]: value }))
  }

  const saveLogs = async () => {
    setSavingTab('logs')
    try {
      const res = await settingsApi.update({
        docker_config: JSON.stringify(docker),
        loki_config: JSON.stringify(loki),
      }) as { success?: boolean }
      if (res.success !== false) { toast.success('Настройки сохранены'); load() }
      else toast.error('Не удалось сохранить')
    } catch { toast.error('Ошибка сохранения') }
    finally { setSavingTab(null) }
  }

  const saveTheme = async () => {
    setSavingTheme(true)
    try {
      const res = await themesApi.updateSettings(themeValues) as { success?: boolean }
      if (res.success !== false) { toast.success('Настройки темы сохранены'); await loadThemeOptions() }
      else toast.error('Не удалось сохранить')
    } catch { toast.error('Ошибка сохранения') }
    finally { setSavingTheme(false) }
  }

  const saveThemeKey = async (key: string, value: string) => {
    try {
      await themesApi.updateSettings({ [key]: value })
    } catch { toast.error('Ошибка сохранения') }
  }

  const saveAll = async () => {
    setSavingTab('all')
    try {
      const flat: Record<string, string> = {}
      for (const it of items) {
        const value = effective(it)
        // Skip masked secrets on bulk save (empty = keep existing).
        if (it.is_secret && value === '') continue
        // Send only changed values: avoids needless client/support reloads.
        if (value === (it.value ?? '')) continue
        flat[it.key] = value
      }
      flat.docker_config = JSON.stringify(docker)
      flat.loki_config = JSON.stringify(loki)
      const integrationChanged = Object.keys(flat).some(isIntegrationKey)
      const res = await settingsApi.update(flat) as { success?: boolean; error?: string }
      if (res.success === false) { toast.error(res.error || 'Не удалось сохранить'); return }
      if (integrationChanged) invalidateBedolagaRuntime()
      toast.success('Настройки сохранены')
      await load()
      useBrandingStore.getState().load()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } } }
      toast.error(e?.response?.data?.error || 'Ошибка сохранения')
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

  const q = search.trim().toLowerCase()
  const match = (it: RegistryItem) =>
    !q ||
    it.label.toLowerCase().includes(q) ||
    it.key.toLowerCase().includes(q) ||
    (it.description || '').toLowerCase().includes(q)

  const countMatches = (cats: [string, RegistryItem[]][]) =>
    cats.reduce((n, [, ci]) => n + ci.filter(match).length, 0)

  const renderCategory = (category: string, catItems: RegistryItem[]) => {
    const filtered = catItems.filter(match)
    if (q && filtered.length === 0) return null
    return (
      <Section key={category} title={category} description={CATEGORY_DESC[category]}>
        {filtered.map((it) => (
          <SettingItem
            key={it.key}
            item={it}
            value={effective(it)}
            isSaving={savingKeys.has(it.key)}
            wasSaved={savedKeys.has(it.key)}
            themes={themes}
            onSave={onSave}
            onReset={onReset}
            onChange={onChange}
          />
        ))}
      </Section>
    )
  }

  const runTest = async (id: string) => {
    setTesting(id)
    try {
      const res = id === 'global'
        ? await settingsApi.testProxy()
        : await settingsApi.testIntegration(id)
      const data = res.data
      const extra = data.egress_ip ? ` · внешний IP ${data.egress_ip}` : ''
      if (data.ok) {
        toast.success(data.message + extra)
      } else toast.error(data.message)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Не удалось проверить подключение')
    } finally {
      // Статусы могли измениться и при неудачной проверке — кэш всё равно устарел.
      if (TEST_INVALIDATES.has(id)) invalidateBedolagaRuntime()
      setTesting(null)
    }
  }

  const renderIntegrationCategory = (category: string, catItems: RegistryItem[]) => {
    const filtered = catItems.filter(match)
    if (q && filtered.length === 0) return null
    const id = INTEGRATION_TEST_IDS[category]
    return (
      <Section
        key={category}
        id={CATEGORY_ANCHOR[category]}
        title={category}
        description={CATEGORY_DESC[category]}
        defaultOpen={!!q || !focusCategory || focusCategory === category || !fromParam}
        action={id ? (
          <Button
            size="sm"
            variant="outline"
            onClick={() => runTest(id)}
            disabled={testing !== null}
          >
            <Zap className={`w-4 h-4 mr-1.5 ${testing === id ? 'animate-pulse' : ''}`} />
            {testing === id ? 'Проверка…' : 'Проверить'}
          </Button>
        ) : undefined}
      >
        {filtered.map((it) => (
          <SettingItem
            key={it.key}
            item={it}
            value={effective(it)}
            isSaving={savingKeys.has(it.key)}
            wasSaved={savedKeys.has(it.key)}
            themes={themes}
            onSave={onSave}
            onReset={onReset}
            onChange={onChange}
          />
        ))}
      </Section>
    )
  }

  const renderThemeGroup = (group: ThemeGroup) => (
    <Section key={group.name} title={group.name} description={`Опций: ${Object.keys(group.options).length}`}>
      {Object.entries(group.options).map(([key, opt]) => {
        const val = themeValues[key] ?? ''
        const saveNow = () => saveThemeKey(key, val)
        return (
          <div key={key} className="py-3">
            <Label className="block text-sm text-dark-200 mb-1.5">{opt.label}</Label>
            {opt.type === 'textarea' ? (
              <Textarea
                rows={opt.rows || 3}
                value={val}
                onChange={(e) => setThemeValues({ ...themeValues, [key]: e.target.value })}
                onBlur={saveNow}
              />
            ) : opt.type === 'select' ? (
              <Select
                value={val}
                onValueChange={(v) => {
                  setThemeValues({ ...themeValues, [key]: v })
                  saveThemeKey(key, v)
                }}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(opt.options || {}).map(([v, label]) => (
                    <SelectItem key={v} value={v}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input
                type={opt.type === 'number' ? 'number' : 'text'}
                value={val}
                onChange={(e) => setThemeValues({ ...themeValues, [key]: e.target.value })}
                onBlur={saveNow}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveNow() } }}
              />
            )}
            {opt.hint && <p className="text-xs text-dark-200 mt-1">{opt.hint}</p>}
          </div>
        )
      })}
    </Section>
  )

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
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Настройки</h1>
          <p className="text-dark-200 mt-1 text-sm md:text-base">
            Управление сайтом, темой, интеграциями, финансами и логами
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
        <Tabs
          value={tab}
          onValueChange={(v) => {
            setTab(v)
            setSearch('')
            setSearchParams({ tab: v }, { replace: true })
          }}
        >
          <TabsList>
            <TabsTrigger value="basic">Основные</TabsTrigger>
            <TabsTrigger value="seo">SEO</TabsTrigger>
            <TabsTrigger value="theme">Сайт</TabsTrigger>
            <TabsTrigger value="security">Безопасность</TabsTrigger>
            <TabsTrigger value="finance">Финансы</TabsTrigger>
            <TabsTrigger value="support">Поддержка</TabsTrigger>
            <TabsTrigger value="integrations">Интеграции</TabsTrigger>
            <TabsTrigger value="logs">Логи</TabsTrigger>
          </TabsList>

          {/* ── Основные (registry-driven) ── */}
          <TabsContent value="basic" className="space-y-2 mt-4">
            <SearchBar value={search} onChange={setSearch} count={countMatches(Object.entries(byTab.basic || {}))} />
            {Object.entries(byTab.basic || {}).map(([cat, catItems]) =>
              renderCategory(cat, catItems)
            )}
            {!search && <Legend />}
          </TabsContent>

          {/* ── SEO (registry-driven) ── */}
          <TabsContent value="seo" className="space-y-2 mt-4">
            <SearchBar value={search} onChange={setSearch} count={countMatches(Object.entries(byTab.seo || {}))} />
            {Object.entries(byTab.seo || {}).map(([cat, catItems]) =>
              renderCategory(cat, catItems)
            )}
          </TabsContent>

          {/* ── Тема ── */}
          <TabsContent value="theme" className="space-y-2 mt-4">
            {Object.entries(byTab.theme || {}).map(([cat, catItems]) =>
              renderCategory(cat, catItems)
            )}
            {themeGroups.map((g) => renderThemeGroup(g))}
            <div className="flex justify-end pt-2">
              <Button variant="default" onClick={saveTheme} disabled={savingTheme}>
                <Save className="w-4 h-4 mr-1.5" /> {savingTheme ? 'Сохранение…' : 'Сохранить тему'}
              </Button>
            </div>
          </TabsContent>

          {/* ── Безопасность ── */}
          <TabsContent value="security" className="space-y-2 mt-4">
            <Section title="Смена пароля" description="Пароль текущей учётной записи">
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">Текущий пароль</Label>
                <Input type="password" autoComplete="current-password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} placeholder="••••••••" />
              </div>
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">Новый пароль</Label>
                <Input type="password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="••••••••" />
                <p className="text-xs text-dark-200 mt-1">Минимум 8 символов</p>
              </div>
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">Повторите новый пароль</Label>
                <Input type="password" autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="••••••••" />
                {confirmPassword.length > 0 && newPassword !== confirmPassword && (
                  <p className="text-xs text-red-400 mt-1">Пароли не совпадают</p>
                )}
                {confirmPassword.length > 0 && newPassword === confirmPassword && newPassword.length >= 8 && (
                  <p className="text-xs text-green-400 mt-1">Пароли совпадают</p>
                )}
              </div>
              <div className="pt-3">
                <Button variant="default" onClick={changePassword} disabled={savingPassword} className="w-full">
                  <Save className="w-4 h-4 mr-1.5" /> {savingPassword ? 'Сохранение…' : 'Сменить пароль'}
                </Button>
              </div>
            </Section>
          </TabsContent>

          {/* ── Финансы (registry-driven) ── */}
          <TabsContent value="finance" className="space-y-2 mt-4">
            <SearchBar value={search} onChange={setSearch} count={countMatches(Object.entries(byTab.finance || {}))} />
            {Object.entries(byTab.finance || {}).map(([cat, catItems]) =>
              renderCategory(cat, catItems)
            )}
          </TabsContent>

          {/* ── Поддержка ── */}
          <TabsContent value="support" className="space-y-2 mt-4">
            <SearchBar
              value={search}
              onChange={setSearch}
              count={countMatches(Object.entries(byTab.support || {}))}
            />
            {Object.entries(byTab.support || {}).map(([cat, catItems]) =>
              renderIntegrationCategory(cat, catItems)
            )}
          </TabsContent>

          {/* ── Интеграции ── */}
          <TabsContent value="integrations" className="space-y-2 mt-4">
            {!isPending && !error && Object.keys(byTab.integrations || {}).length === 0 ? (
              <Card className="animate-fade-in-up">
                <EmptyState
                  icon={Database}
                  size="lg"
                  title="Настройки интеграций недоступны"
                  description={'Backend не вернул ни одной категории интеграций. Проверьте, что API перезапущен с актуальным реестром настроек и что GET /api/settings отвечает items с tab="integrations".'}
                  action={
                    <Button variant="secondary" onClick={() => { void load() }}>
                      <RefreshCw className="w-4 h-4 mr-1.5" /> Повторить
                    </Button>
                  }
                />
              </Card>
            ) : (
              <>
                <SearchBar
                  value={search}
                  onChange={setSearch}
                  count={countMatches(Object.entries(byTab.integrations || {}))}
                />
                <Section
                  title="Бэкапы"
                  description="Хранилища, уровни, восстановление и уведомления — в разделе «Инфраструктура → Бэкапы»"
                  action={
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => runTest('backups')} disabled={testing !== null}>
                        <Zap className={`w-4 h-4 mr-1.5 ${testing === 'backups' ? 'animate-pulse' : ''}`} />
                        {testing === 'backups' ? 'Проверка…' : 'Проверить'}
                      </Button>
                      <Button size="sm" onClick={() => navigate('/backups?tab=storages')}>
                        <HardDrive className="w-4 h-4 mr-1.5" />
                        Управлять
                      </Button>
                    </div>
                  }
                >
                  <div className="py-3 text-sm text-dark-200">
                    Хранилища (CMS, S3, SFTP, rclone) добавляются на странице бэкапов. Здесь — только
                    быстрый переход и проверка доступности всех хранилищ.
                  </div>
                </Section>
                {Object.entries(byTab.integrations || {}).map(([cat, catItems]) =>
                  renderIntegrationCategory(cat, catItems)
                )}
              </>
            )}
          </TabsContent>

          {/* ── Логи ── */}
          <TabsContent value="logs" className="space-y-2 mt-4">
            <Section title="Docker" description="Просмотр логов контейнеров по SSH">
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">SSH хост</Label>
                <Input value={docker.docker_ssh_host || ''} onChange={(e) => setDocker({ ...docker, docker_ssh_host: e.target.value })} />
              </div>
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">SSH порт</Label>
                <Input value={docker.docker_ssh_port || '22'} onChange={(e) => setDocker({ ...docker, docker_ssh_port: e.target.value })} />
              </div>
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">SSH пользователь</Label>
                <Input value={docker.docker_ssh_user || ''} onChange={(e) => setDocker({ ...docker, docker_ssh_user: e.target.value })} />
              </div>
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">Строк на контейнер</Label>
                <Input type="number" value={docker.docker_lines || '100'} onChange={(e) => setDocker({ ...docker, docker_lines: e.target.value })} />
              </div>
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">Контейнеры</Label>
                <Input value={docker.docker_containers || ''} onChange={(e) => setDocker({ ...docker, docker_containers: e.target.value })} />
                <p className="text-xs text-dark-200 mt-1">Список через запятую</p>
              </div>
            </Section>

            <Section title="Loki" description="Источник логов Loki">
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">Loki URL</Label>
                <Input value={loki.loki_url || ''} onChange={(e) => setLoki({ ...loki, loki_url: e.target.value })} />
              </div>
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">Query</Label>
                <Input value={loki.loki_query || ''} onChange={(e) => setLoki({ ...loki, loki_query: e.target.value })} />
              </div>
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">Пользователь</Label>
                <Input value={loki.loki_user || ''} onChange={(e) => setLoki({ ...loki, loki_user: e.target.value })} />
              </div>
              <div className="py-3">
                <Label className="block text-sm text-dark-200 mb-1.5">Лимит записей</Label>
                <Input type="number" value={loki.loki_limit || '100'} onChange={(e) => setLoki({ ...loki, loki_limit: e.target.value })} />
              </div>
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
