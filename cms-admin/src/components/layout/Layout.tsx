import { useState, useEffect, useCallback } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import { Outlet } from 'react-router-dom'

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [commandOpen, setCommandOpen] = useState(false)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      setCommandOpen((prev) => !prev)
    }
  }, [])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--glass-bg)] relative">
      {/* Mesh gradient background */}
      <div className="mesh-bg">
        <div className="mesh-layer mesh-layer--1" />
        <div className="mesh-layer mesh-layer--2" />
        <div className="mesh-layer mesh-layer--3" />
        <div className="mesh-layer mesh-layer--4" />
        <div className="mesh-layer mesh-layer--5" />
      </div>

      {/* Sidebar */}
      <Sidebar mobileOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Header onMenuToggle={() => setSidebarOpen(true)} onSearchClick={() => setCommandOpen(true)} />

        {/* Page content */}
        <main className="flex-1 overflow-y-auto" style={{ background: 'linear-gradient(135deg, var(--surface-body) 0%, var(--surface-card) 50%, var(--surface-body) 100%)' }}>
          <div className="p-4 md:p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}