import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Input, Card } from '../../components/ui'
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

  if (loading) return <div className="text-[var(--text-secondary)] py-12 text-center">Загрузка...</div>

  return (
    <div className="max-w-xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">
            {isEdit ? 'Редактировать пользователя' : 'Создать пользователя'}
          </h2>
        </div>
        <Button variant="ghost" onClick={() => navigate('/admin/users')}>← Назад</Button>
      </div>
      <form onSubmit={handleSubmit}>
        <Card>
          <div className="space-y-4">
            <Input label="Логин" value={login} onChange={(e) => setLogin(e.target.value)} required />
            <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Input label={isEdit ? 'Новый пароль (оставьте пустым, чтобы не менять)' : 'Пароль'} type="password" value={password} onChange={(e) => setPassword(e.target.value)} required={!isEdit} />
            <Input label="Отображаемое имя" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-[var(--text-secondary)]">Роль</label>
              <select value={role} onChange={(e) => setRole(e.target.value)}
                className="w-full h-11 px-4 rounded-lg bg-white/5 border border-white/10 text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--accent)]">
                <option value="admin">Администратор</option>
                <option value="editor">Редактор</option>
                <option value="author">Автор</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-[var(--text-secondary)]">Статус</label>
              <select value={status} onChange={(e) => setStatus(e.target.value)}
                className="w-full h-11 px-4 rounded-lg bg-white/5 border border-white/10 text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--accent)]">
                <option value="active">Активен</option>
                <option value="suspended">Заблокирован</option>
              </select>
            </div>
          </div>
        </Card>
        <div className="flex gap-3 mt-5">
          <Button type="submit" loading={saving}>{isEdit ? 'Сохранить' : 'Создать'}</Button>
          <Button variant="ghost" onClick={() => navigate('/admin/users')}>Отмена</Button>
        </div>
      </form>
    </div>
  )
}