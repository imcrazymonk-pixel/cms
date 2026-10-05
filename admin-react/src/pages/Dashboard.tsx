import { useEffect, useState } from 'react'
import { dashboardApi, DashboardStats } from '../api/dashboard'
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card'
import { Loader } from 'lucide-react'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    dashboardApi.getStats()
      .then((res) => {
        if (res.success) setStats(res.stats)
        else setError('Не удалось загрузить статистику')
      })
      .catch(() => setError('Ошибка подключения к серверу'))
      .finally(() => setLoading(false))
  }, [])

  const statCards = [
    { label: 'Постов', value: stats?.posts ?? 0, color: 'teal' },
    { label: 'Комментариев (ожидают)', value: stats?.comments ?? 0, color: 'amber' },
    { label: 'Пользователей', value: stats?.users ?? 0, color: 'blue' },
    { label: 'Категорий', value: stats?.categories ?? 0, color: 'purple' },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-display font-bold text-white tracking-tight">
          Дашборд
        </h1>
        <p className="text-sm text-dark-200 mt-1">
          Общая статистика сайта
        </p>
      </div>

      {/* Error */}
      {error && (
        <div
          className="mb-5 p-3.5 rounded-xl border animate-fade-in"
          style={{
            background:
              'linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(239, 68, 68, 0.04) 100%)',
            borderColor: 'rgba(239, 68, 68, 0.2)',
          }}
        >
          <p className="text-sm text-red-400 leading-relaxed">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader className="h-8 w-8 animate-spin text-teal-500" />
        </div>
      )}

      {/* Stats grid */}
      {!loading && (
        <div className="grid grid-cols-4 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {statCards.map((card) => (
            <Card key={card.label} className="rounded-xl glass-heavy">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-dark-300 font-medium uppercase tracking-wider">
                      {card.label}
                    </p>
                    <p className={card.color === 'teal' ? 'text-teal-400' : card.color === 'amber' ? 'text-amber-400' : card.color === 'blue' ? 'text-blue-400' : 'text-purple-400'}>
                      {stats ? (
                        <span className="text-3xl font-bold font-variant-numeric tabular-nums">
                          {card.value}
                        </span>
                      ) : (
                        <Loader className="h-6 w-6 animate-spin" />
                      )}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Placeholder for future widgets */}
      <Card className="rounded-xl glass-heavy">
        <CardHeader>
          <CardTitle>Последние действия</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-dark-300">
            Здесь будет отображаться активность на сайте.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}