import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { usersApi, type User, type UserPayload } from '@/api/users'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Info, Loader2, Upload, UserRound, X } from 'lucide-react'

const AVATAR_MAX_BYTES = 2 * 1024 * 1024 // 2 МБ — как на бэкенде

/** Подпись поля с иконкой-подсказкой. */
function FieldLabel({
  htmlFor, label, hint, required,
}: {
  htmlFor?: string
  label: string
  hint: string
  required?: boolean
}) {
  return (
    <div className="flex items-center gap-1.5">
      <Label htmlFor={htmlFor}>
        {label}{required ? ' *' : ''}
      </Label>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            tabIndex={-1}
            className="text-dark-400 hover:text-dark-200 transition-colors"
            aria-label={`Подсказка: ${label}`}
          >
            <Info className="w-3.5 h-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-[260px] text-xs leading-relaxed">
          {hint}
        </TooltipContent>
      </Tooltip>
    </div>
  )
}

const EMPTY = {
  login: '',
  displayName: '',
  email: '',
  password: '',
  role: 'author',
  status: 'active',
  avatarUrl: '',
  bio: '',
  phone: '',
  telegram: '',
  website: '',
  location: '',
}

export function UserFormModal({
  open, onOpenChange, user, onSaved,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: User | null
  onSaved: () => void
}) {
  const isEdit = !!user
  const fileRef = useRef<HTMLInputElement>(null)
  const [form, setForm] = useState({ ...EMPTY })
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    if (!open) return
    if (user) {
      setForm({
        login: user.login || '',
        displayName: user.display_name || '',
        email: user.email || '',
        password: '',
        role: user.role || 'author',
        status: user.status || 'active',
        avatarUrl: user.avatar_url || '',
        bio: user.bio || '',
        phone: user.phone || '',
        telegram: user.telegram || '',
        website: user.website || '',
        location: user.location || '',
      })
    } else {
      setForm({ ...EMPTY })
    }
  }, [open, user])

  const set = (key: keyof typeof EMPTY, value: string) =>
    setForm((f) => ({ ...f, [key]: value }))

  const pickAvatar = async (file?: File) => {
    if (!file) return
    if (file.size > AVATAR_MAX_BYTES) {
      toast.error('Файл больше 2 МБ')
      return
    }
    setUploading(true)
    try {
      const res = await usersApi.uploadAvatar(file) as { success: boolean; data?: { url: string }; error?: string }
      if (res.success && res.data?.url) {
        set('avatarUrl', res.data.url)
        toast.success('Аватар загружен')
      } else {
        toast.error(res.error || 'Не удалось загрузить аватар')
      }
    } catch (e) {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Ошибка загрузки аватара'
      toast.error(msg)
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const save = async () => {
    if (!form.login.trim()) { toast.error('Укажите логин'); return }
    if (!isEdit && !form.password) { toast.error('Укажите пароль'); return }

    const payload: UserPayload = {
      login: form.login.trim(),
      email: form.email.trim(),
      display_name: form.displayName.trim(),
      role: form.role,
      status: form.status,
      avatar_url: form.avatarUrl,
      bio: form.bio.trim(),
      phone: form.phone.trim(),
      telegram: form.telegram.trim(),
      website: form.website.trim(),
      location: form.location.trim(),
    }
    if (form.password) payload.password = form.password

    setSaving(true)
    try {
      if (isEdit && user) await usersApi.update(user.id, payload)
      else await usersApi.create(payload)
      toast.success(isEdit ? 'Пользователь сохранён' : 'Пользователь создан')
      onSaved()
      onOpenChange(false)
    } catch (e) {
      const msg = (e as { response?: { data?: { error?: string; detail?: string } } })?.response?.data
      toast.error(msg?.error || msg?.detail || 'Не удалось сохранить пользователя')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Редактировать пользователя' : 'Новый пользователь'}</DialogTitle>
          <DialogDescription>
            {isEdit ? 'Изменение учётной записи' : 'Создание учётной записи'}
          </DialogDescription>
        </DialogHeader>

        <TooltipProvider delayDuration={150}>
          <div className="space-y-4">
            {/* Avatar */}
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 rounded-full overflow-hidden bg-white/5 border border-[var(--glass-border)] flex items-center justify-center shrink-0">
                {form.avatarUrl ? (
                  <img src={form.avatarUrl} alt="avatar" className="w-full h-full object-cover" />
                ) : (
                  <UserRound className="w-8 h-8 text-dark-400" />
                )}
              </div>
              <div className="space-y-1.5">
                <FieldLabel
                  label="Аватар"
                  hint="JPG, PNG, GIF или WEBP, размер до 2 МБ. GIF-анимация поддерживается."
                />
                <div className="flex items-center gap-2">
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/jpeg,image/png,image/gif,image/webp"
                    className="hidden"
                    onChange={(e) => pickAvatar(e.target.files?.[0])}
                  />
                  <Button type="button" variant="secondary" size="sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
                    {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />} Загрузить
                  </Button>
                  {form.avatarUrl && (
                    <Button type="button" variant="ghost" size="sm" onClick={() => set('avatarUrl', '')}>
                      <X className="w-4 h-4" /> Убрать
                    </Button>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <FieldLabel htmlFor="u-login" label="Логин" required hint="Уникальное имя для входа (латиница, цифры, без пробелов)." />
                <Input id="u-login" value={form.login} onChange={(e) => set('login', e.target.value)} placeholder="username" />
              </div>

              <div className="space-y-2">
                <FieldLabel htmlFor="u-display" label="Отображаемое имя" hint="Как имя показывается в админке и на сайте." />
                <Input id="u-display" value={form.displayName} onChange={(e) => set('displayName', e.target.value)} placeholder="Иван Иванов" />
              </div>

              <div className="space-y-2">
                <FieldLabel htmlFor="u-email" label="Email" hint="Используется для входа и системных уведомлений." />
                <Input id="u-email" type="email" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="user@example.com" />
              </div>

              <div className="space-y-2">
                <FieldLabel
                  htmlFor="u-pass"
                  label={isEdit ? 'Новый пароль' : 'Пароль'}
                  required={!isEdit}
                  hint={isEdit ? 'Оставьте пустым, чтобы не менять пароль.' : 'Пароль для входа. Рекомендуется 6+ символов.'}
                />
                <Input id="u-pass" type="password" value={form.password} onChange={(e) => set('password', e.target.value)} placeholder="••••••••" autoComplete="new-password" />
              </div>

              <div className="space-y-2">
                <FieldLabel label="Роль" hint="Права доступа: администратор — полный доступ, редактор — контент, автор — только свои материалы." />
                <Select value={form.role} onValueChange={(v) => set('role', v)}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Администратор</SelectItem>
                    <SelectItem value="editor">Редактор</SelectItem>
                    <SelectItem value="author">Автор</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <FieldLabel label="Статус" hint="Активен — может входить; Неактивен — вход отключён; Заблокирован — доступ запрещён." />
                <Select value={form.status} onValueChange={(v) => set('status', v)}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Активен</SelectItem>
                    <SelectItem value="inactive">Неактивен</SelectItem>
                    <SelectItem value="banned">Заблокирован</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <FieldLabel htmlFor="u-phone" label="Телефон" hint="Контактный номер (необязательно)." />
                <Input id="u-phone" value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="+7 900 000-00-00" />
              </div>

              <div className="space-y-2">
                <FieldLabel htmlFor="u-tg" label="Telegram" hint="Ник или ID в Telegram, например @username." />
                <Input id="u-tg" value={form.telegram} onChange={(e) => set('telegram', e.target.value)} placeholder="@username" />
              </div>

              <div className="space-y-2">
                <FieldLabel htmlFor="u-site" label="Сайт" hint="Личный сайт или страница (полный URL)." />
                <Input id="u-site" value={form.website} onChange={(e) => set('website', e.target.value)} placeholder="https://example.com" />
              </div>

              <div className="space-y-2">
                <FieldLabel htmlFor="u-loc" label="Локация" hint="Город или страна (необязательно)." />
                <Input id="u-loc" value={form.location} onChange={(e) => set('location', e.target.value)} placeholder="Москва" />
              </div>
            </div>

            <div className="space-y-2">
              <FieldLabel htmlFor="u-bio" label="О себе" hint="Короткая биография — отображается в профиле (необязательно)." />
              <Textarea id="u-bio" value={form.bio} onChange={(e) => set('bio', e.target.value)} rows={3} placeholder="Пара слов о пользователе…" />
            </div>
          </div>
        </TooltipProvider>

        <DialogFooter className="gap-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={saving}>Отмена</Button>
          <Button variant="default" onClick={save} disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {isEdit ? 'Сохранить' : 'Создать'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
