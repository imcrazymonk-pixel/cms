import { NavLink } from 'react-router-dom'
import { navigation, type NavItem } from '../../config/navigation'

function SidebarNavItem({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.path}
      end={item.path === '/admin'}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
          isActive
            ? 'bg-[var(--accent)]/10 text-[var(--accent)]'
            : 'text-[var(--text-secondary)] hover:bg-white/5 hover:text-[var(--text-primary)]'
        }`
      }
    >
      <span className="w-5 h-5 flex items-center justify-center">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <use href={`#icon-${item.icon}`} />
        </svg>
      </span>
      {item.label}
    </NavLink>
  )
}

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-64 bg-[var(--bg-surface)] border-r border-white/5 z-30 overflow-y-auto">
      <div className="flex items-center gap-3 px-6 h-16 border-b border-white/5">
        <div className="w-8 h-8 rounded-lg bg-[var(--accent)] flex items-center justify-center text-white font-bold text-sm">
          H
        </div>
        <span className="font-semibold text-sm text-[var(--text-primary)]">HexaVeil CMS</span>
      </div>
      <nav className="p-3 space-y-1">
        {navigation.map((item) => (
          <SidebarNavItem key={item.path} item={item} />
        ))}
      </nav>
    </aside>
  )
}