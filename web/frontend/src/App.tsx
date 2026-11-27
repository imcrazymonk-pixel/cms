import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { usePermissionStore } from './store/permissionStore'
import { useSidebarLinksStore } from './store/useSidebarLinksStore'
import { useAppearanceStore } from './store/useAppearanceStore'
import { AppearanceProvider } from './components/AppearanceProvider'
import { BrandingProvider } from './components/BrandingProvider'
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
const Finance = lazy(() => import('./pages/Finance'))
const UsersList = lazy(() => import('./pages/UsersList'))
const Settings = lazy(() => import('./pages/Settings'))
const LogsViewer = lazy(() => import('./pages/LogsViewer'))
const Diagnostics = lazy(() => import('./pages/Diagnostics'))

// Bedolaga pages
const BedolagaDashboard = lazy(() => import('./pages/bedolaga/BedolagaDashboard'))
const BedolagaCustomers = lazy(() => import('./pages/bedolaga/BedolagaCustomers'))
const BedolagaCustomerDetail = lazy(() => import('./pages/bedolaga/BedolagaCustomerDetail'))
const BedolagaPromo = lazy(() => import('./pages/bedolaga/BedolagaPromo'))
const BedolagaMarketing = lazy(() => import('./pages/bedolaga/BedolagaMarketing'))
const BedolagaReferrals = lazy(() => import('./pages/bedolaga/BedolagaReferrals'))
const BedolagaTariffs = lazy(() => import('./pages/bedolaga/BedolagaTariffs'))
const BedolagaRevenue = lazy(() => import('./pages/bedolaga/BedolagaRevenue'))

const ChangelogViewer = lazy(() => import('./pages/ChangelogViewer'))

// Infrastructure pages
const BackupsPage = lazy(() => import('./pages/backups/BackupsPage'))
const InfrastructureNodes = lazy(() => import('./pages/infrastructure/Nodes'))
const InfrastructurePanel = lazy(() => import('./pages/infrastructure/Panel'))

// Support pages
const SupportQueue = lazy(() => import('./pages/support/Queue'))
const SupportPlaceholder = lazy(() => import('./pages/support/Placeholder'))

const NotFound = lazy(() => import('./pages/NotFound'))

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()
  const { isLoaded, loadPermissions, clearPermissions } = usePermissionStore()
  const loadSidebarLinks = useSidebarLinksStore((s) => s.loadFromServer)
  const loadAppearance = useAppearanceStore((s) => s.loadFromServer)

  useEffect(() => {
    if (token && !isLoaded) loadPermissions()
  }, [token, isLoaded, loadPermissions])

  useEffect(() => {
    if (!token) clearPermissions()
  }, [token, clearPermissions])

  // Load user preferences from server on EVERY mount when authenticated.
  // The store deduplicates concurrent calls via _fetchPromise internally.
  useEffect(() => {
    if (token) loadSidebarLinks()
  }, [token, loadSidebarLinks])

  useEffect(() => {
    if (token) loadAppearance()
  }, [token, loadAppearance])

  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <AppearanceProvider>
      <BrandingProvider>
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

              {/* Media, menus, widgets */}
              <Route path="/media" element={<RequireAuth><Layout><MediaList /></Layout></RequireAuth>} />
              <Route path="/menus" element={<RequireAuth><Layout><MenusList /></Layout></RequireAuth>} />
              <Route path="/menus/create" element={<RequireAuth><Layout><MenuEdit /></Layout></RequireAuth>} />
              <Route path="/menus/:id" element={<RequireAuth><Layout><MenuEdit /></Layout></RequireAuth>} />
              <Route path="/widgets" element={<RequireAuth><Layout><WidgetsList /></Layout></RequireAuth>} />

              {/* Finance */}
              <Route path="/finance" element={<RequireAuth><Layout><Finance /></Layout></RequireAuth>} />

              {/* System */}
              <Route path="/users" element={<RequireAuth><Layout><UsersList /></Layout></RequireAuth>} />
              <Route path="/settings" element={<RequireAuth><Layout><Settings /></Layout></RequireAuth>} />
              <Route path="/logs" element={<RequireAuth><Layout><LogsViewer /></Layout></RequireAuth>} />
              <Route path="/diagnostics" element={<RequireAuth><Layout><Diagnostics /></Layout></RequireAuth>} />

              {/* Bedolaga Bot Integration */}
              <Route path="/bedolaga" element={<RequireAuth><Layout><BedolagaDashboard /></Layout></RequireAuth>} />
              <Route path="/bedolaga/customers" element={<RequireAuth><Layout><BedolagaCustomers /></Layout></RequireAuth>} />
              <Route path="/bedolaga/customers/:id" element={<RequireAuth><Layout><BedolagaCustomerDetail /></Layout></RequireAuth>} />
              <Route path="/bedolaga/promo" element={<RequireAuth><Layout><BedolagaPromo /></Layout></RequireAuth>} />
              <Route path="/bedolaga/marketing" element={<RequireAuth><Layout><BedolagaMarketing /></Layout></RequireAuth>} />
              <Route path="/bedolaga/referrals" element={<RequireAuth><Layout><BedolagaReferrals /></Layout></RequireAuth>} />
              <Route path="/bedolaga/tariffs" element={<RequireAuth><Layout><BedolagaTariffs /></Layout></RequireAuth>} />
              <Route path="/bedolaga/revenue" element={<RequireAuth><Layout><BedolagaRevenue /></Layout></RequireAuth>} />

              {/* Support */}
              <Route path="/support" element={<RequireAuth><Layout><SupportQueue /></Layout></RequireAuth>} />
              <Route path="/support/sla" element={<RequireAuth><Layout><SupportPlaceholder title="Контроль SLA" description="Политики SLA, просрочки первого ответа и времени решения появятся в фазе 4" /></Layout></RequireAuth>} />
              <Route path="/support/kb" element={<RequireAuth><Layout><SupportPlaceholder title="База знаний" description="Статьи КБ, полнотекстовый поиск и дообучение из диалогов — фаза 3" /></Layout></RequireAuth>} />
              <Route path="/support/ai" element={<RequireAuth><Layout><SupportPlaceholder title="ИИ-ассистент" description="Черновики ответов, ворота и настройки модели — фаза 3" /></Layout></RequireAuth>} />
              <Route path="/support/templates" element={<RequireAuth><Layout><SupportPlaceholder title="Шаблоны ответов" description="Быстрые заготовки ответов операторов — фаза 4" /></Layout></RequireAuth>} />
              <Route path="/support/analytics" element={<RequireAuth><Layout><SupportPlaceholder title="Аналитика" description="Метрики очереди, SLA и операторов — фаза 4" /></Layout></RequireAuth>} />
              <Route path="/support/team" element={<RequireAuth><Layout><SupportPlaceholder title="Команда" description="Присутствие операторов и аудит действий — фаза 4" /></Layout></RequireAuth>} />

              {/* 404 */}
              {/* Infrastructure */}
              <Route path="/backups" element={<RequireAuth><Layout><BackupsPage /></Layout></RequireAuth>} />
              <Route path="/infrastructure/nodes" element={<RequireAuth><Layout><InfrastructureNodes /></Layout></RequireAuth>} />
              <Route path="/infrastructure/panel" element={<RequireAuth><Layout><InfrastructurePanel /></Layout></RequireAuth>} />

              {/* Docs / Changelog */}
              <Route path="/changelog" element={<RequireAuth><Layout><ChangelogViewer /></Layout></RequireAuth>} />

              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
        </ErrorBoundary>
      </BrandingProvider>
    </AppearanceProvider>
  )
}