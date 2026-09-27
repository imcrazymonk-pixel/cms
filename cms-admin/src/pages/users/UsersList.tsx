import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { DataGrid, Button, Badge } from '../../components/ui'
import type { Column } from '../../components/ui'
import { getUsers, deleteUser, type User } from '../../api/users'

export default function UsersListPage() {
  const navigate = useNavigate()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getUsers().then(setUsers).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить пользователя?')) return
    await deleteUser(id)
    setUsers(await getUsers())
  }

  const roleColors: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
    admin: 'danger', editor: 'info', author: 'warning',
  }

  const columns: Column<User>[] = [
    { key: 'login', label: 'Логин' },
    { key: 'email', label: 'Email' },
    { key: 'display_name', label: 'Имя' },
    { key: 'role', label: 'Роль', render: (r) => <Badge variant={roleColors[r.role] ?? 'default'}>{r.role}</Badge> },
    { key: 'status', label: 'Статус', render: (r) => <Badge variant={r.status === 'active' ? 'success' : 'danger'}>{r.status}</Badge> },
    { key: 'posts_count', label: 'Постов' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">Пользователи</h2>
          <p className="text-sm text-[var(--text-secondary)]">Управление пользователями системы</p>
        </div>
        <Button onClick={() => navigate('/admin/users/create')}>+ Создать</Button>
      </div>
      <DataGrid<User>
        columns={columns}
        data={users}
        keyField="id"
        total={users.length}
        page={1}
        perPage={50}
        onPageChange={() => {}}
        loading={loading}
        actions={(row) => (
          <div className="flex flex-col">
            <button onClick={() => navigate(`/admin/users/${row.id}`)} className="px-3 py-1.5 text-left text-sm text-[var(--text-primary)] hover:bg-white/5">Редактировать</button>
            <button onClick={() => handleDelete(row.id)} className="px-3 py-1.5 text-left text-sm text-red-400 hover:bg-white/5">Удалить</button>
          </div>
        )}
        emptyMessage="Пользователей нет"
      />
    </div>
  )
}