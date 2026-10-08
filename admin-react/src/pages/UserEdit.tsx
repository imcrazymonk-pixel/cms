import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { usersApi, User } from '../api/users'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { Loader2 } from 'lucide-react'

export default function UserEdit() {
  const params = useParams()
  const navigate = useNavigate()
  const isEdit = !!params.id
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [login, setLogin] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('author')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        if (isEdit && params.id) {
          const res = await usersApi.get(parseInt(params.id)) as { success: boolean; data: User }
          if (!cancelled && res.success) {
            const u = res.data
            setLogin(u.login || '')
            setEmail(u.email || '')
            setRole(u.role || 'author')
          } else if (!cancelled) setError('Пользователь не найден')
        }
      } catch (err: unknown) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Ошибка')
      } finally { if (!cancelled) setIsPending(false) }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const save = async () => {
    if (!login.trim()) return
    setSaving(true)
    try {
      const payload: Partial<User> & { password?: string } = {
        login: login.trim(),
        email: email.trim(),
        role: role as User['role'],
      }
      if (password) payload.password = password
      if (isEdit && params.id) await usersApi.update(parseInt(params.id), payload)
      else {
        const res = await usersApi.create({ ...payload, password }) as { success: boolean; data?: { id: number } }
        if (res.success && res.data?.id) { navigate(`/users/${res.data.id}`); setSaving(false); return }
      }
      navigate('/users')
    } catch { /* ignore */ }
    finally { setSaving(false) }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <a href="/admin/users" className="text-sm text-dark-300 hover:text-dark-100 transition-colors mb-1 block">← Назад к списку</a>
          <h1 className="text-2xl font-bold text-white tracking-tight">{isEdit ? 'Редактировать пользователя' : 'Создать пользователя'}</h1>
          <p className="text-sm text-dark-200 mt-1">{isEdit ? 'Редактирование учётной записи' : 'Новая учётная запись'}</p>
        </div>
      </div>

      {isPending && <><Skeleton className="h-12 rounded-lg" /><Skeleton className="h-32 rounded-lg" /></>}
      {error && <QueryError message={error} />}

      {!isPending && !error && (
        <Card className="rounded-xl max-w-2xl mx-auto">
          <CardHeader><CardTitle>{isEdit ? 'Информация о пользователе' : 'Новый пользователь'}</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="login">Логин *</Label>
              <Input id="login" value={login} onChange={(e) => setLogin(e.target.value)} placeholder="username" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="user@example.com" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{isEdit ? 'Новый пароль (оставьте пустым, чтобы не менять)' : 'Пароль'}</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </div>
            <div className="space-y-2">
              <Label>Роль</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Администратор</SelectItem>
                  <SelectItem value="editor">Редактор</SelectItem>
                  <SelectItem value="author">Автор</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-3 pt-4">
              <Button variant="default" onClick={save} disabled={saving || !login.trim()}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null} {isEdit ? 'Сохранить' : 'Создать'}
              </Button>
              <Button variant="ghost" onClick={() => navigate('/users')}>Отмена</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
