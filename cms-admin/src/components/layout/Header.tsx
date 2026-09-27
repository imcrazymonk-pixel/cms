import { useAuth } from '../../store/authStore'

export default function Header() {
  const { user, logout } = useAuth()

  return (
    <header className="h-16 border-b border-white/5 flex items-center justify-between px-6 bg-[var(--bg-base)]/80 backdrop-blur-md sticky top-0 z-20">
      <div>
        <h1 className="text-lg font-semibold text-[var(--text-primary)]">Панель управления</h1>
      </div>
      <div className="flex items-center gap-4">
        <button className="relative p-2 rounded-lg text-[var(--text-secondary)] hover:bg-white/5 hover:text-[var(--text-primary)] transition-colors">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        </button>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-sm font-medium text-[var(--text-primary)]">{user?.login}</div>
            <div className="text-xs text-[var(--text-muted)]">{user?.role}</div>
          </div>
          <div className="w-9 h-9 rounded-full bg-[var(--accent)]/20 flex items-center justify-center text-sm font-semibold text-[var(--accent)]">
            {user?.login?.charAt(0).toUpperCase()}
          </div>
          <button
            onClick={logout}
            className="text-xs text-[var(--text-secondary)] hover:text-red-400 transition-colors ml-2"
          >
            Выйти
          </button>
        </div>
      </div>
    </header>
  )
}