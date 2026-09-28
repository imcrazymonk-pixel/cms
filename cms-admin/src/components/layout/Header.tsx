import { Search, Menu } from 'lucide-react'
import { useAuth } from '../../store/authStore'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'

interface HeaderProps {
  onMenuToggle?: () => void
  onSearchClick?: () => void
}

export default function Header({ onMenuToggle, onSearchClick }: HeaderProps) {
  const { user, logout } = useAuth()

  return (
    <header className="h-16 flex items-center justify-between px-4 md:px-6 animate-fade-in relative z-30 backdrop-blur-sm">
      <div className="flex items-center gap-3 flex-1">
        <Button variant="ghost" size="icon" onClick={onMenuToggle} className="md:hidden h-11 w-11">
          <Menu className="w-6 h-6" />
        </Button>
        <button onClick={onSearchClick}
          className="flex-1 max-w-md hidden sm:flex items-center gap-2 h-10 rounded-xl border border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-sm px-3.5 text-sm text-muted-foreground hover:border-[var(--glass-border-hover)] hover:text-foreground transition-all duration-200 cursor-pointer">
          <Search className="w-4 h-4 flex-shrink-0" />
          <span className="flex-1 text-left">Поиск...</span>
          <span className="hidden lg:inline-flex items-center gap-1">
            <kbd className="h-5 select-none inline-flex items-center gap-1 rounded-md border border-[var(--glass-border)] bg-white/5 px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
              <span className="text-xs">⌘</span>K
            </kbd>
          </span>
        </button>
      </div>

      <div className="flex items-center gap-2 md:gap-4">
        {/* User avatar + logout */}
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <div className="text-sm font-medium text-white">{user?.login}</div>
            <div className="text-xs text-muted-foreground">{user?.role}</div>
          </div>
          <div className="w-9 h-9 rounded-full flex items-center justify-center bg-[var(--glass-bg-hover)] border border-[var(--glass-border)] flex-shrink-0">
            <span className="text-sm font-medium text-primary">{user?.login?.charAt(0).toUpperCase() || 'A'}</span>
          </div>
          <Button variant="ghost" size="icon" onClick={logout} className="h-9 w-9 text-dark-200 hover:text-red-400 hidden sm:flex">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </Button>
        </div>

        {/* Status */}
        <Badge variant="default" className="gap-2 px-3 py-1.5 rounded-xl">
          <span className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: 'var(--accent-from)', boxShadow: '0 0 8px rgba(var(--glow-rgb), 0.5)' }} />
          <span className="hidden sm:inline text-xs">Онлайн</span>
        </Badge>
      </div>
    </header>
  )
}