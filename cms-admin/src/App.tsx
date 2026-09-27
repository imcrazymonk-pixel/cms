import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './store/authStore'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/layout/Layout'
import LoginPage from './pages/Login'
import DashboardPage from './pages/Dashboard'
import PostsListPage from './pages/posts/PostsList'
import PostFormPage from './pages/posts/PostForm'
import CategoriesPage from './pages/categories/CategoriesPage'
import PagesListPage from './pages/pages/PagesList'
import PageFormPage from './pages/pages/PageForm'
import UsersListPage from './pages/users/UsersList'
import UserFormPage from './pages/users/UserForm'
import PlaceholderPage from './pages/Placeholder'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/admin/login" element={<LoginPage />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="posts" element={<PostsListPage />} />
            <Route path="posts/create" element={<PostFormPage />} />
            <Route path="posts/:id" element={<PostFormPage />} />
            <Route path="posts/categories" element={<CategoriesPage />} />
            <Route path="pages" element={<PagesListPage />} />
            <Route path="pages/create" element={<PageFormPage />} />
            <Route path="pages/:id" element={<PageFormPage />} />
            <Route path="users" element={<UsersListPage />} />
            <Route path="users/create" element={<UserFormPage />} />
            <Route path="users/:id" element={<UserFormPage />} />
            <Route path="media" element={<PlaceholderPage />} />
            <Route path="settings" element={<PlaceholderPage />} />
            <Route path="theme" element={<PlaceholderPage />} />
            <Route path="widgets" element={<PlaceholderPage />} />
            <Route path="menus" element={<PlaceholderPage />} />
            <Route path="logs" element={<PlaceholderPage />} />
            <Route path="finance" element={<PlaceholderPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}