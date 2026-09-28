import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, FileText, FolderTree, Files, Users, Image,
  Settings, Palette, LayoutGrid, Menu, ScrollText, Wallet,
  ChevronDown, ChevronsLeft, ChevronsRight, LogOut, X,
} from 'lucide-react'
import { useAuth } from '../../store/authStore'
import { Button } from '../ui/button'
import { ScrollArea } from '../ui/scroll-area'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '../ui/tooltip'
import { cn } from '../../lib/utils'
import { navigation } from '../../config/navigation'

interface SidebarProps {
  mobileOpen?: boolean
  onClose?: () => void
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  'layout-dashboard': LayoutDashboard,
  'file-text': FileText,
  'folder-tree': FolderTree,
  'files': Files,
  'users': Users,
  'image': Image,
  'settings': Settings,
  'palette': Palette,
  'layout-grid': LayoutGrid,
  'menu': Menu, 'scroll-text': ScrollText, 'wallet': Wallet,
}

export default function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  const location = useLocation()
  const { user, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())

  const toggleGroup = (name: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className={cn("flex items-center justify-between h-16 px-6 relative", collapsed && "px-0 justify-center")}>
        <Link to="/admin" onClick={onClose} className={cn("flex items-center gap-2.5 hover:opacity-90 transition-opacity", collapsed && "gap-0")}>
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white font-bold text-sm flex-shrink-0">H</div>
          {!collapsed && <span className="text-sm font-semibold text-white truncate max-w-[140px]">HexaVeil CMS</span>}
        </Link>
        <Button variant="ghost" size="icon" onClick={onClose} className="md:hidden h-8 w-8"><X className="w-5 h-5" /></Button>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 py-4">
        <nav className={cn("px-3 space-y-0.5", collapsed && "px-2")}>
          {navigation.map((item) => {
            // Section header
            if ('type' in item && item.type === 'section') {
              if (collapsed) return <div key={item.label} className="my-2 mx-1 border-t border-[var(--glass-border)]" />
              return (
                <div key={item.label} className="px-3 pt-4 pb-1.5 text-[10px] font-bold uppercase tracking-widest text-dark-400 select-none">
                  {item.label}
                </div>
              )
            }

            // Regular nav item
            const navItem = item as { label: string; path: string; icon: string; children?: { label: string; path: string; icon: string }[] }
            const Icon = iconMap[navItem.icon] || LayoutDashboard
            const isActive = location.pathname === navItem.path

            if (navItem.children) {
              const groupActive = navItem.children.some((c) => location.pathname === c.path)
              const isExpanded = expandedGroups.has(navItem.label) || groupActive

              if (collapsed) {
                return (
                  <div key={navItem.label} className="space-y-0.5">
                    {navItem.children.map((sub) => {
                      const subActive = location.pathname === sub.path
                      return (
                        <Tooltip key={sub.label} delayDuration={0}>
                          <TooltipTrigger asChild>
                            <Link to={sub.path} onClick={onClose}
                              className={cn("flex items-center justify-center px-0 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 relative",
                                subActive ? "text-white bg-[var(--glass-bg-hover)] border border-[var(--glass-border-hover)]" : "text-dark-200 hover:text-white hover:bg-[var(--glass-bg)]")}>
                              {subActive && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full" style={{ background: 'linear-gradient(180deg, var(--accent-from), var(--accent-to))' }} />}
                              <Icon className="w-5 h-5" />
                            </Link>
                          </TooltipTrigger>
                          <TooltipContent side="right">{sub.label}</TooltipContent>
                        </Tooltip>
                      )
                    })}
                  </div>
                )
              }

              return (
                <div key={navItem.label} className="space-y-0.5">
                  <button onClick={() => toggleGroup(navItem.label)}
                    className={cn("flex items-center w-full px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200",
                      groupActive ? "text-white bg-[var(--glass-bg-hover)] border border-[var(--glass-border)]" : "text-dark-200 hover:text-white hover:bg-[var(--glass-bg)]")}>
                    <Icon className={cn("w-5 h-5 mr-3 flex-shrink-0", groupActive ? "text-primary" : "")} />
                    <span className="flex-1 text-left">{navItem.label}</span>
                    <ChevronDown className={cn("w-4 h-4 text-dark-300 transition-transform duration-200", isExpanded && "rotate-180")} />
                  </button>
                  <div className={cn("overflow-hidden transition-all duration-200", isExpanded ? "max-h-96 opacity-100" : "max-h-0 opacity-0")}>
                    <div className="ml-3 pl-3 border-l border-[var(--glass-border)] space-y-0.5">
                      {navItem.children.map((sub) => {
                        const subActive = location.pathname === sub.path
                        return (
                          <Link key={sub.path} to={sub.path} onClick={onClose}
                            className={cn("flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 relative overflow-hidden",
                              subActive ? "text-white bg-[var(--glass-bg-hover)] border border-[var(--glass-border-hover)]" : "text-dark-200 hover:text-white hover:bg-[var(--glass-bg)]")}>
                            {subActive && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-3.5 rounded-r-full" style={{ background: 'linear-gradient(180deg, var(--accent-from), var(--accent-to))' }} />}
                            {Icon && <Icon className="w-4 h-4 mr-2.5 flex-shrink-0" />}
                            <span>{sub.label}</span>
                          </Link>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )
            }

            return (
              <Tooltip key={navItem.path} delayDuration={0}>
                <TooltipTrigger asChild>
                  <Link to={navItem.path} onClick={onClose}
                    className={cn("flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 relative overflow-hidden",
                      isActive ? "text-white bg-[var(--glass-bg-hover)] border border-[var(--glass-border-hover)]" : "text-dark-200 hover:text-white hover:bg-[var(--glass-bg)] hover:translate-x-0.5",
                      collapsed && "justify-center px-0")}>
                    {isActive && !collapsed && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full" style={{ background: 'linear-gradient(180deg, var(--accent-from), var(--accent-to))' }} />}
                    <Icon className={cn("w-5 h-5 flex-shrink-0", !collapsed && "mr-3", isActive ? "text-primary" : "")} />
                    {!collapsed && <span>{navItem.label}</span>}
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" className={cn(!collapsed && "md:hidden")}>{navItem.label}</TooltipContent>
              </Tooltip>
            )
          })}
        </nav>
      </ScrollArea>

      {/* Collapse toggle */}
      <div className="hidden md:flex justify-center py-2">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" onClick={() => setCollapsed(!collapsed)} className="h-8 w-8 text-dark-300 hover:text-white">
              {collapsed ? <ChevronsRight className="w-4 h-4" /> : <ChevronsLeft className="w-4 h-4" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">{collapsed ? 'Развернуть' : 'Свернуть'}</TooltipContent>
        </Tooltip>
      </div>

      {/* User info */}
      <div className="mx-4 h-px bg-gradient-to-r from-transparent via-[rgba(var(--glow-rgb),0.12)] to-transparent" />
      <div className={cn("p-4", collapsed && "p-2")}>
        <div className={cn("flex items-center", collapsed && "justify-center")}>
          <div className="w-9 h-9 rounded-full flex items-center justify-center bg-[var(--glass-bg-hover)] border border-[var(--glass-border)] flex-shrink-0">
            <span className="text-sm font-medium text-primary">{user?.login?.charAt(0).toUpperCase() || 'A'}</span>
          </div>
          {!collapsed && (
            <>
              <div className="ml-3 flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{user?.login || 'Admin'}</p>
                <p className="text-xs text-muted-foreground capitalize">{user?.role || 'admin'}</p>
              </div>
              <Button variant="ghost" size="icon" onClick={logout} className="h-9 w-9 text-dark-200 hover:text-red-400">
                <LogOut className="w-5 h-5" />
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )

  return (
    <TooltipProvider delayDuration={0}>
      {mobileOpen && <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden" onClick={onClose} />}
      <div className={cn("fixed inset-y-0 left-0 z-50 flex flex-col glass-heavy animate-fade-in transform transition-all duration-300 ease-in-out md:relative md:translate-x-0", collapsed ? "w-[4.5rem]" : "w-64", mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0")}>
        {sidebarContent}
      </div>
    </TooltipProvider>
  )
}
