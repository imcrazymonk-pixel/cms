import { useState } from 'react'
import navigation from '@/config/navigation'
import { Link, useLocation } from 'react-router-dom'
import {
  ChevronDown,
  ChevronsLeft,
  ChevronsRight,
  LogOut,
  X,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useAppearanceStore } from '../../store/useAppearanceStore'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { ConfirmDialog } from '@/components/ConfirmDialog'

interface NavItem {
  type?: 'item'
  name: string
  href: string
  icon: typeof ChevronDown
  permission: null
}

interface NavGroup {
  type: 'group'
  name: string
  icon: typeof ChevronDown
  items: NavItem[]
}

interface NavSection {
  type: 'section'
  name: string
}

type NavigationEntry = NavItem | NavGroup | NavSection

function isNavGroup(entry: NavigationEntry): entry is NavGroup {
  return entry.type === 'group'
}

function isNavSection(entry: NavigationEntry): entry is NavSection {
  return entry.type === 'section'
}

interface SidebarProps {
  mobileOpen?: boolean
  onClose?: () => void
}

export default function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  const location = useLocation()
  const { clearAuth } = useAuthStore()
  const collapsed = useAppearanceStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useAppearanceStore((s) => s.toggleSidebar)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false)

  const handleNavClick = () => {
    if (onClose) onClose()
  }

  const toggleGroup = (name: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const isGroupActive = (group: NavGroup) =>
    group.items.some((item) => location.pathname === item.href)

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className={cn(
        "sidebar-logo-area flex items-center justify-between h-16 px-6 relative",
        "[&::after]:content-[''] [&::after]:absolute [&::after]:bottom-0 [&::after]:inset-x-4 [&::after]:h-px [&::after]:bg-gradient-to-r [&::after]:from-transparent [&::after]:via-[rgba(var(--glow-rgb),0.15)] [&::after]:to-transparent",
        collapsed && "px-0 justify-center"
      )}>
        <Link to="/" onClick={handleNavClick} className={cn(
          "flex items-center gap-2.5 hover:opacity-90 transition-opacity duration-200",
          collapsed && "gap-0"
        )}>
          <div className="w-8 h-8 flex items-center justify-center rounded-lg bg-gradient-to-br from-teal-600 to-cyan-600 text-white text-sm font-bold flex-shrink-0">
            H
          </div>
          {!collapsed && (
            <span className="text-sm font-semibold text-white truncate max-w-[140px]">
              HexaVeil CMS
            </span>
          )}
        </Link>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="md:hidden h-8 w-8"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </Button>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 py-4">
        <nav className={cn("px-3 space-y-0.5", collapsed && "px-2")}>
          {(navigation as NavigationEntry[]).map((entry, idx) => {
            if (isNavSection(entry)) {
              if (collapsed) {
                return <div key={`s-${idx}`} className="my-2 mx-1 border-t border-[var(--glass-border)]" />
              }
              return (
                <div
                  key={`s-${idx}`}
                  className="sidebar-section-title px-3 pt-4 pb-1.5 text-[10px] font-bold uppercase tracking-widest text-dark-400 select-none"
                >
                  {entry.name}
                </div>
              )
            }

            if (isNavGroup(entry)) {
              const groupActive = isGroupActive(entry)
              const isExpanded = expandedGroups.has(entry.name) || groupActive

              if (collapsed) {
                return (
                  <div key={`g-${idx}`} className="space-y-0.5">
                    {entry.items.map((item) => {
                      const isActive = location.pathname === item.href
                      return (
                        <Tooltip key={item.name} delayDuration={0}>
                          <TooltipTrigger asChild>
                            <Link
                              to={item.href}
                              onClick={handleNavClick}
                              className={cn(
                                "sidebar-nav-item group flex items-center justify-center px-0 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 relative",
                                isActive
                                  ? "text-white bg-[var(--glass-bg-hover)] border border-[var(--glass-border-hover)] shadow-[0_0_15px_-4px_rgba(var(--glow-rgb),0.3)]"
                                  : "text-dark-200 hover:text-white hover:bg-[var(--glass-bg)]"
                              )}
                            >
                              {isActive && (
                                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full"
                                  style={{ background: 'linear-gradient(180deg, var(--accent-from), var(--accent-to))' }}
                                />
                              )}
                              <item.icon className={cn("w-5 h-5 flex-shrink-0", isActive ? "text-primary-400" : "")} />
                            </Link>
                          </TooltipTrigger>
                          <TooltipContent side="right">
                            {item.name}
                          </TooltipContent>
                        </Tooltip>
                      )
                    })}
                  </div>
                )
              }

              return (
                <div key={`g-${idx}`} className="space-y-0.5">
                  <button
                    onClick={() => toggleGroup(entry.name)}
                    className={cn(
                      "sidebar-nav-item group flex items-center w-full px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200",
                      groupActive
                        ? "text-white bg-[var(--glass-bg-hover)] border border-[var(--glass-border)]"
                        : "text-dark-200 hover:text-white hover:bg-[var(--glass-bg)]"
                    )}
                  >
                    <entry.icon className={cn("w-5 h-5 mr-3 flex-shrink-0", groupActive ? "text-primary-400" : "")} />
                    <span className="sidebar-nav-text flex-1 text-left">{entry.name}</span>
                    <ChevronDown className={cn("sidebar-group-chevron w-4 h-4 text-dark-300 transition-transform duration-200", isExpanded && "rotate-180")} />
                  </button>

                  <div className={cn("overflow-hidden transition-all duration-200", isExpanded ? "max-h-96 opacity-100" : "max-h-0 opacity-0")}>
                    <div className="sidebar-group-items ml-3 pl-3 border-l border-[var(--glass-border)] space-y-0.5">
                      {entry.items.map((item) => {
                        const isActive = location.pathname === item.href
                        return (
                          <Tooltip key={item.name} delayDuration={0}>
                            <TooltipTrigger asChild>
                              <Link
                                to={item.href}
                                onClick={handleNavClick}
                                className={cn(
                                  "group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 relative overflow-hidden",
                                  isActive
                                    ? "text-white bg-[var(--glass-bg-hover)] border border-[var(--glass-border-hover)] shadow-[0_0_10px_-4px_rgba(var(--glow-rgb),0.2)]"
                                    : "text-dark-200 hover:text-white hover:bg-[var(--glass-bg)] hover:translate-x-0.5"
                                )}
                              >
                                {isActive && (
                                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-3.5 rounded-r-full"
                                    style={{ background: 'linear-gradient(180deg, var(--accent-from), var(--accent-to))' }}
                                  />
                                )}
                                <item.icon className={cn("w-4 h-4 mr-2.5 flex-shrink-0", isActive ? "text-primary-400" : "")} />
                                <span className="sidebar-nav-text">{item.name}</span>
                              </Link>
                            </TooltipTrigger>
                            <TooltipContent side="right">{item.name}</TooltipContent>
                          </Tooltip>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )
            }

            const item = entry as NavItem
            const isActive = location.pathname === item.href
            return (
              <Tooltip key={item.name} delayDuration={0}>
                <TooltipTrigger asChild>
                  <Link
                    to={item.href}
                    onClick={handleNavClick}
                    className={cn(
                      "sidebar-nav-item group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 relative overflow-hidden",
                      isActive
                        ? "text-white bg-[var(--glass-bg-hover)] border border-[var(--glass-border-hover)] shadow-[0_0_15px_-4px_rgba(var(--glow-rgb),0.3)]"
                        : "text-dark-200 hover:text-white hover:bg-[var(--glass-bg)] hover:translate-x-0.5",
                      collapsed && "justify-center px-0"
                    )}
                  >
                    {isActive && !collapsed && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full transition-all duration-300"
                        style={{ background: 'linear-gradient(180deg, var(--accent-from), var(--accent-to))' }}
                      />
                    )}
                    <item.icon className={cn("w-5 h-5 flex-shrink-0", !collapsed && "mr-3", isActive ? "text-primary-400" : "")} />
                    {!collapsed && <span className="sidebar-nav-text">{item.name}</span>}
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" className={cn(!collapsed && "md:hidden")}>
                  {item.name}
                </TooltipContent>
              </Tooltip>
            )
          })}
        </nav>
      </ScrollArea>

      {/* Collapse toggle */}
      <div className="hidden md:flex justify-center py-2">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              className="h-8 w-8 text-dark-300 hover:text-white"
              aria-label="Toggle sidebar"
            >
              {collapsed ? <ChevronsRight className="w-4 h-4" /> : <ChevronsLeft className="w-4 h-4" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {collapsed ? 'Expand' : 'Collapse'}
          </TooltipContent>
        </Tooltip>
      </div>

      {/* User info */}
      <div className="mx-4 h-px bg-gradient-to-r from-transparent via-[rgba(var(--glow-rgb),0.12)] to-transparent" />
      <div className={cn("p-4", collapsed && "p-2")}>
        <div className={cn("sidebar-user-section flex items-center", collapsed && "justify-center")}>
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <div className="w-9 h-9 rounded-full flex items-center justify-center bg-[var(--glass-bg-hover)] border border-[var(--glass-border)] shadow-[0_0_15px_-4px_rgba(var(--glow-rgb),0.25)] flex-shrink-0">
                <span className="text-sm font-medium text-primary-400">A</span>
              </div>
            </TooltipTrigger>
            {collapsed && (
              <TooltipContent side="right">Admin</TooltipContent>
            )}
          </Tooltip>
          {!collapsed && (
            <>
              <div className="sidebar-user-info ml-3 flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">Admin</p>
                <p className="text-xs text-muted-foreground capitalize">Administrator</p>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setLogoutConfirmOpen(true)}
                    className="h-9 w-9 text-dark-200 hover:text-red-400"
                    aria-label="Log out"
                  >
                    <LogOut className="w-5 h-5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Log out</TooltipContent>
              </Tooltip>
            </>
          )}
          {collapsed && (
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setLogoutConfirmOpen(true)}
                  className="h-8 w-8 text-dark-200 hover:text-red-400 mt-2"
                  aria-label="Log out"
                >
                  <LogOut className="w-4 h-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Log out</TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>
    </div>
  )

  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden" onClick={onClose} />
      )}
      <div className={cn(
        "fixed inset-y-0 left-0 z-50 flex flex-col",
        "glass-heavy animate-fade-in",
        "pt-safe pb-safe pl-[env(safe-area-inset-left)] md:pl-0",
        "[&::after]:content-[''] [&::after]:absolute [&::after]:right-0 [&::after]:inset-y-0 [&::after]:w-px [&::after]:bg-gradient-to-b [&::after]:from-transparent [&::after]:via-[rgba(var(--glow-rgb),0.2)] [&::after]:to-transparent",
        "transform transition-all duration-300 ease-in-out",
        "md:relative md:translate-x-0",
        collapsed ? "w-[4.5rem]" : "w-64",
        mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>
        {sidebarContent}
      </div>

      <ConfirmDialog
        open={logoutConfirmOpen}
        onOpenChange={setLogoutConfirmOpen}
        title="Выйти"
        description="Вы уверены, что хотите выйти?"
        confirmLabel="Выйти"
        variant="destructive"
        onConfirm={() => {
          setLogoutConfirmOpen(false)
          clearAuth()
          window.location.href = '/admin/logout'
        }}
      />
    </>
  )
}