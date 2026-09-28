import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { Button, Input, Card, Label } from '../../components/ui'
import { getUser, createUser, updateUser } from '../../api/users'

export default function UserFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = !!id
  const [login, setLogin] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('author')
  const [displayName, setDisplayName] = useState('')
  const [status, setStatus] = useState('active')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEdit && id) {
      setLoading(true)
      getUser(Number(id)).then((u) => {
        setLogin(u.login); setEmail(u.email); setRole(u.role)
        setDisplayName(u.display_name ?? ''); setStatus(u.status)
      }).finally(() => setLoading(false))
    }
  }, [id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const data: Record<string, unknown> = { login, email, role, display_name: displayName, status }
      if (password) data.password = password
      if (isEdit && id) { await updateUser(Number(id), data); navigate('/admin/users') }
      else { await createUser(data as Parameters<typeof createUser>[0]); navigate('/admin/users') }
    } finally { setSaving(false) }
  }

  if (loading) return <div className="text-center py-12 text-muted-foreground">Загрузка...</div>

  return (
    <div className="max-w-xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl md:text-2xl font-bold" style={{ color: 'var(--text-body)' }}>
          {isEdit ? 'Редактировать пользователя' : 'Создать пользователя'}
        </h2>
        <Button variant="ghost" onClick={() => navigate('/admin/users')}>← Назад</Button>
      </div>
      <form onSubmit={handleSubmit}>
        <Card>
          <div className="space-y-4 p-4 md:p-6">
            <div className="space-y-2"><Label>Логин</Label><Input value={login} onChange={(e) => setLogin(e.target.value)} required /></div>
            <div className="space-y-2"><Label>Email</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
            <div className="space-y-2"><Label>{isEdit ? 'Новый пароль' : 'Пароль'}</Label><Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required={!isEdit} /></div>
            <div className="space-y-2"><Label>Отображаемое имя</Label><Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} /></div>
            <div className="space-y-2">
              <Label>Роль</Label>
              <select value={role} onChange={(e) => setRole(e.target.value)} className="flex h-10 w-full rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-sm px-3 py-2 text-sm text-dark-50">
                <option value="admin">Администратор</option>
                <option value="editor">Редактор</option>
                <option value="author">Автор</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Статус</Label>
              <select value={status} onChange={(e) => setStatus(e.target.value)} className="flex h-10 w-full rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-sm px-3 py-2 text-sm text-dark-50">
                <option value="active">Активен</option>
                <option value="suspended">Заблокирован</option>
              </select>
            </div>
          </div>
        </Card>
        <div className="flex gap-3 mt-5">
          <Button type="submit" disabled={saving}>{saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}{isEdit ? 'Сохранить' : 'Создать'}</Button>
          <Button variant="ghost" onClick={() => navigate('/admin/users')}>Отмена</Button>
        </div>
      </form>
    </div>
  )
}