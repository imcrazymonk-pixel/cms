import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { usePermissionStore } from './store/permissionStore'
import { AppearanceProvider } from './components/AppearanceProvider'
import { ErrorBoundary } from './components/ErrorBoundary'

// Layout
import Layout from './components/layout/Layout'

// Login loaded eagerly (critical path)
import Login from './pages/Login'

// Lazy-loaded pages
const Dashboard = lazy(() => import('./pages/Dashboard'))
const PostsList = lazy(() => import('./pages/PostsList'))
const PostEdit = lazy(() => import('./pages/PostEdit'))
const CategoriesList = lazy(() => import('./pages/CategoriesList'))
const PagesList = lazy(() => import('./pages/PagesList'))
const PageEdit = lazy(() => import('./pages/PageEdit'))
const MediaList = lazy(() => import('./pages/MediaList'))
const MenusList = lazy(() => import('./pages/MenusList'))
const MenuEdit = lazy(() => import('./pages/MenuEdit'))
const WidgetsList = lazy(() => import('./pages/WidgetsList'))
const ThemeManager = lazy(() => import('./pages/ThemeManager'))
const Finance = lazy(() => import('./pages/Finance'))
const UsersList = lazy(() => import('./pages/UsersList'))
const UserEdit = lazy(() => import('./pages/UserEdit'))
const Settings = lazy(() => import('./pages/Settings'))
const LogsViewer = lazy(() => import('./pages/LogsViewer'))
const Diagnostics = lazy(() => import('./pages/Diagnostics'))
const NotFound = lazy(() => import('./pages/NotFound'))

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()
  const { isLoaded, loadPermissions, clearPermissions } = usePermissionStore()

  useEffect(() => {
    if (token && !isLoaded) loadPermissions()
  }, [token, isLoaded, loadPermissions])

  useEffect(() => {
    if (!token) clearPermissions()
  }, [token, clearPermissions])

  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <AppearanceProvider>
      <ErrorBoundary>
        <BrowserRouter basename="/admin">
          <Suspense fallback={<div className="loading">Загрузка...</div>}>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />

              {/* Protected routes — wrapped in Layout */}
              <Route path="/" element={<RequireAuth><Layout><Dashboard /></Layout></RequireAuth>} />

              {/* Site */}
              <Route path="/posts" element={<RequireAuth><Layout><PostsList /></Layout></RequireAuth>} />
              <Route path="/posts/create" element={<RequireAuth><Layout><PostEdit /></Layout></RequireAuth>} />
              <Route path="/posts/:id" element={<RequireAuth><Layout><PostEdit /></Layout></RequireAuth>} />
              <Route path="/posts/categories" element={<RequireAuth><Layout><CategoriesList /></Layout></RequireAuth>} />
              <Route path="/pages" element={<RequireAuth><Layout><PagesList /></Layout></RequireAuth>} />
              <Route path="/pages/create" element={<RequireAuth><Layout><PageEdit /></Layout></RequireAuth>} />
              <Route path="/pages/:id" element={<RequireAuth><Layout><PageEdit /></Layout></RequireAuth>} />

              {/* Media, menus, widgets, themes */}
              <Route path="/media" element={<RequireAuth><Layout><MediaList /></Layout></RequireAuth>} />
              <Route path="/menus" element={<RequireAuth><Layout><MenusList /></Layout></RequireAuth>} />
              <Route path="/menus/create" element={<RequireAuth><Layout><MenuEdit /></Layout></RequireAuth>} />
              <Route path="/menus/:id" element={<RequireAuth><Layout><MenuEdit /></Layout></RequireAuth>} />
              <Route path="/widgets" element={<RequireAuth><Layout><WidgetsList /></Layout></RequireAuth>} />
              <Route path="/themes" element={<RequireAuth><Layout><ThemeManager /></Layout></RequireAuth>} />

              {/* Finance */}
              <Route path="/finance" element={<RequireAuth><Layout><Finance /></Layout></RequireAuth>} />

              {/* System */}
              <Route path="/users" element={<RequireAuth><Layout><UsersList /></Layout></RequireAuth>} />
              <Route path="/users/:id" element={<RequireAuth><Layout><UserEdit /></Layout></RequireAuth>} />
              <Route path="/settings" element={<RequireAuth><Layout><Settings /></Layout></RequireAuth>} />
              <Route path="/logs" element={<RequireAuth><Layout><LogsViewer /></Layout></RequireAuth>} />
              <Route path="/diagnostics" element={<RequireAuth><Layout><Diagnostics /></Layout></RequireAuth>} />

              {/* 404 */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ErrorBoundary>
    </AppearanceProvider>
  )
}