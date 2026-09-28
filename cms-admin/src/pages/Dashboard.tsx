import { useState, useEffect } from 'react'
import { Card, CardContent } from '../components/ui'
import { FileText, MessageSquare, Users, FolderTree } from 'lucide-react'

interface Stats {
  posts: number; comments: number; users: number; categories: number
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  useEffect(() => {
    fetch('/api/dashboard/stats', { headers: { Authorization: `Bearer ${localStorage.getItem('jwt_token')}` } })
      .then((r) => r.json()).then((d) => setStats(d.stats)).catch(() => {})
  }, [])

  const cards = [
    { label: 'Постов', value: stats?.posts ?? '—', icon: FileText },
    { label: 'Комментариев', value: stats?.comments ?? '—', icon: MessageSquare },
    { label: 'Пользователей', value: stats?.users ?? '—', icon: Users },
    { label: 'Категорий', value: stats?.categories ?? '—', icon: FolderTree },
  ]

  return (
    <div>
      <div className="page-header mb-6">
        <div>
          <h1 className="page-header-title">Дашборд</h1>
          <p className="text-sm text-muted-foreground">Общая статистика сайта</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card, i) => (
          <Card key={card.label}>
            <CardContent className="p-4 md:p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-[var(--glass-bg)] border border-[var(--glass-border)]">
                  <card.icon className="w-5 h-5 text-primary" />
                </div>
                <span className="text-sm text-muted-foreground">{card.label}</span>
              </div>
              <div className="text-3xl font-bold text-white tabular-nums">{card.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}