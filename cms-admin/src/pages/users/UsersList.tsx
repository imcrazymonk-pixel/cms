import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { DataGrid, Button, Badge } from '../../components/ui'
import type { Column } from '../../components/ui'
import { getUsers, deleteUser, type User } from '../../api/users'

export default function UsersListPage() {
  const navigate = useNavigate()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => { getUsers().then(setUsers).catch(() => {}).finally(() => setLoading(false)) }, [])

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить пользователя?')) return
    await deleteUser(id); setUsers(await getUsers())
  }

  const roleColors: Record<string, 'default' | 'success' | 'warning' | 'destructive' | 'secondary'> = {
    admin: 'destructive', editor: 'secondary', author: 'warning',
  }

  const columns: Column<User>[] = [
    { key: 'login', label: 'Логин' }, { key: 'email', label: 'Email' }, { key: 'display_name', label: 'Имя' },
    { key: 'role', label: 'Роль', render: (r) => <Badge variant={roleColors[r.role] ?? 'default'}>{r.role}</Badge> },
    { key: 'status', label: 'Статус', render: (r) => <Badge variant={r.status === 'active' ? 'success' : 'destructive'}>{r.status}</Badge> },
    { key: 'posts_count', label: 'Постов' },
  ]

  return (
    <div>
      <div className="page-header mb-6">
        <div>
          <h1 className="page-header-title">Пользователи</h1>
          <p className="text-sm text-muted-foreground">Управление пользователями системы</p>
        </div>
        <div className="page-header-actions">
          <Button onClick={() => navigate('/admin/users/create')}>+ Создать</Button>
        </div>
      </div>
      <DataGrid<User>
        columns={columns} data={users} keyField="id" total={users.length}
        page={1} perPage={50} onPageChange={() => {}} loading={loading}
        actions={(row) => (
          <div className="flex flex-col">
            <button onClick={() => navigate(`/admin/users/${row.id}`)} className="px-3 py-1.5 text-left text-sm text-dark-50 hover:bg-[var(--glass-bg-hover)]">Редактировать</button>
            <button onClick={() => handleDelete(row.id)} className="px-3 py-1.5 text-left text-sm text-red-400 hover:bg-[var(--glass-bg-hover)]">Удалить</button>
          </div>
        )}
        emptyMessage="Пользователей нет"
      />
    </div>
  )
}