import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { usersApi, User } from '../api/users'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import {
  Users, Plus, Pencil, Trash2, RefreshCw,
} from 'lucide-react'

export default function UsersList() {
  const navigate = useNavigate()
  const [data, setData] = useState<{ success: boolean; data: User[] } | null>(null)
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)

  const load = async () => {
    setIsPending(true); setError(null)
    try {
      const res = await usersApi.list() as { success: boolean; data: User[] }
      if (res.success) setData(res)
      else setError('Не удалось загрузить пользователей')
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Ошибка') }
    finally { setIsPending(false) }
  }

  useEffect(() => { load() }, [])

  const doDelete = async (id: number) => {
    try { await usersApi.delete(id); setDeleteConfirmId(null); load() }
    catch { /* ignore */ }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Пользователи</h1>
          <p className="text-sm text-dark-200 mt-1">Управление учётными записями</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw className="w-4 h-4" /> Обновить</Button>
          <Button variant="default" size="sm" onClick={() => navigate('/users/create')}><Plus className="w-4 h-4" /> Добавить</Button>
        </div>
      </div>

      {isPending && <>{ [1,2,3].map(i => <Skeleton key={i} className="h-10 rounded-lg" />) }</>}
      {error && <QueryError message={error} />}

      {!isPending && !error && data && (
        <>
          {data.data.length === 0 ? (
            <Card className="rounded-xl"><CardContent className="p-10 text-center">
              <Users className="w-10 h-10 text-dark-300 mx-auto mb-3" />
              <p className="text-base font-semibold mb-2">Пользователей пока нет</p>
              <Button variant="default" onClick={() => navigate('/users/create')}><Plus className="w-4 h-4" /> Создать</Button>
            </CardContent></Card>
          ) : (
            <Card className="rounded-xl"><div className="overflow-x-auto">
              <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr className="border-b border-white/5 text-dark-300 text-xs uppercase tracking-wider">
                    <th className="text-left py-2 px-2.5">ID</th>
                    <th className="text-left py-2 px-2.5">Логин</th>
                    <th className="text-left py-2 px-2.5">Email</th>
                    <th className="text-left py-2 px-2.5">Роль</th>
                    <th className="text-left py-2 px-2.5">Создан</th>
                    <th className="w-24 py-2 px-2.5">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.map((user: User) => (
                    <tr key={user.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-2 px-2.5 text-dark-300 text-xs">{user.id}</td>
                      <td className="py-2 px-2.5 font-medium">
                        <a href={`/admin/users/${user.id}`} className="text-white hover:text-primary transition-colors">{user.login}</a>
                      </td>
                      <td className="py-2 px-2.5 text-dark-300 text-xs">{user.email || '—'}</td>
                      <td className="py-2 px-2.5">
                        <Badge className={user.role === 'admin' ? 'bg-primary/20 text-primary' : 'bg-white/10 text-dark-200'}>
                          {user.role === 'admin' ? 'Администратор' : user.role === 'editor' ? 'Редактор' : user.role || '—'}
                        </Badge>
                      </td>
                      <td className="py-2 px-2.5 text-dark-300 text-xs">{user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}</td>
                      <td className="py-2 px-2.5">
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => navigate(`/users/${user.id}`)} className="h-7 w-7"><Pencil className="w-3.5 h-3.5" /></Button>
                          <Button variant="ghost" size="icon" onClick={() => setDeleteConfirmId(user.id)} className="h-7 w-7 text-red-400"><Trash2 className="w-3.5 h-3.5" /></Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div></Card>
          )}
          <div className="text-sm text-dark-300">Всего: <strong className="text-white">{data.data.length}</strong></div>
        </>
      )}

      <ConfirmDialog
        open={deleteConfirmId !== null}
        onOpenChange={(v) => { if (!v) setDeleteConfirmId(null) }}
        title="Удалить пользователя?" description="Пользователь будет удалён."
        confirmLabel="Удалить" variant="destructive"
        onConfirm={() => { if (deleteConfirmId) doDelete(deleteConfirmId) }}
      />
    </div>
  )
}
