import { useState, useEffect } from 'react'
import api from '../api/client'

interface Stats {
  posts: number
  comments: number
  users: number
  categories: number
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    api.get('/dashboard/stats').then((r) => setStats(r.data)).catch(() => {})
  }, [])

  const cards = [
    { label: 'Постов', value: stats?.posts ?? '—', color: 'hsl(239 84% 67%)' },
    { label: 'Комментариев (ожидает)', value: stats?.comments ?? '—', color: 'hsl(35 100% 60%)' },
    { label: 'Пользователей', value: stats?.users ?? '—', color: 'hsl(150 80% 45%)' },
    { label: 'Категорий', value: stats?.categories ?? '—', color: 'hsl(330 80% 55%)' },
  ]

  return (
    <div>
      <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">Дашборд</h2>
      <p className="text-sm text-[var(--text-secondary)] mb-6">Общая статистика сайта</p>

      <div className="grid grid-cols-4 gap-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-xl bg-[var(--glass-bg)] border border-[var(--glass-border)] p-5 backdrop-blur-sm">
            <div className="flex items-center gap-3 mb-3">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: `${card.color}15` }}
              >
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: card.color }} />
              </div>
              <span className="text-sm text-[var(--text-secondary)]">{card.label}</span>
            </div>
            <div className="text-3xl font-bold text-[var(--text-primary)] tabular-nums">
              {card.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}