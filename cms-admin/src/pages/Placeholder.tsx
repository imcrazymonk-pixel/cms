import { useLocation } from 'react-router-dom'

export default function PlaceholderPage() {
  const location = useLocation()
  return (
    <div>
      <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-1">{location.pathname}</h2>
      <p className="text-sm text-[var(--text-secondary)]">Страница в разработке</p>
    </div>
  )
}