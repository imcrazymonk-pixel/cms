import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { authApi } from '../api/auth'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Card, CardHeader, CardContent } from '../components/ui/card'
import { cn } from '../lib/utils'
import { User, Lock, AlertCircle, KeyRound, Loader2, X } from 'lucide-react'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) return
    setError('')
    setLoading(true)

    try {
      const res = await authApi.login(username.trim(), password)
      if (res.success) {
        setAuth(res.token, res.user)
        window.location.href = '/admin/'
      } else {
        setError(res.error ?? 'Неверный логин или пароль')
      }
    } catch (err: any) {
      setError(err?.response?.data?.error ?? 'Ошибка подключения к серверу')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-bg min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Mesh gradient background */}
      <div className="mesh-bg">
        <div className="mesh-layer mesh-layer--1" />
        <div className="mesh-layer mesh-layer--2" />
        <div className="mesh-layer mesh-layer--3" />
        <div className="mesh-layer mesh-layer--4" />
      </div>

      {/* Main card */}
      <div className="w-full max-w-[420px] relative z-10">
        <Card
          className="rounded-2xl overflow-hidden glass-heavy"
          style={{
            boxShadow:
              '0 0 0 1px var(--glass-highlight), ' +
              '0 20px 60px -10px rgba(0, 0, 0, 0.5), ' +
              '0 0 80px -20px rgba(var(--glow-rgb), 0.12)',
          }}
        >
          {/* Top accent line */}
          <div
            className="h-[2px] w-full"
            style={{
              background:
                'linear-gradient(90deg, transparent 0%, var(--accent-from) 30%, var(--accent-to) 70%, transparent 100%)',
            }}
          />

          <CardHeader className="items-center pt-6 sm:pt-8 pb-2 px-4 sm:px-8">
            <div className="flex flex-col items-center gap-4 mb-2">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center relative login-logo-glow">
                <div
                  className="w-full h-full rounded-2xl flex items-center justify-center"
                  style={{
                    background:
                      'linear-gradient(135deg, var(--accent-from) 0%, var(--accent-to) 100%)',
                  }}
                >
                  <KeyRound className="w-8 h-8 text-white" strokeWidth={1.8} />
                </div>
              </div>
              <div className="text-center">
                <h1 className="text-2xl font-display font-bold text-white tracking-tight">
                  HexaVeil CMS
                </h1>
                <p className="text-sm text-dark-200 mt-1">
                  Вход в панель управления
                </p>
              </div>
            </div>
          </CardHeader>

          <CardContent className="px-4 sm:px-8 pb-6 sm:pb-8 pt-4">
            {/* Separator */}
            <div className="flex items-center gap-3 mb-6">
              <div className="flex-1 h-px bg-[var(--glass-border)]" />
              <span className="text-xs text-dark-300 font-medium uppercase tracking-wider">
                Авторизация
              </span>
              <div className="flex-1 h-px bg-[var(--glass-border)]" />
            </div>

            {/* Error */}
            {error && (
              <div
                className="mb-5 p-3.5 rounded-xl border animate-fade-in"
                style={{
                  background:
                    'linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(239, 68, 68, 0.04) 100%)',
                  borderColor: 'rgba(239, 68, 68, 0.2)',
                }}
              >
                <div className="flex items-start gap-2.5">
                  <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-sm text-red-400 leading-relaxed flex-1">{error}</p>
                  <button
                    onClick={() => setError('')}
                    className="text-red-400/60 hover:text-red-400 transition-colors shrink-0"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}

            {/* Loading */}
            {loading && (
              <div className="flex flex-col items-center py-6 animate-fade-in">
                <div className="relative">
                  <div
                    className="absolute inset-0 rounded-full"
                    style={{
                      background:
                        'radial-gradient(circle, rgba(13, 148, 136, 0.2) 0%, transparent 70%)',
                      transform: 'scale(2)',
                    }}
                  />
                  <Loader2 className="h-8 w-8 animate-spin text-teal-500 relative" />
                </div>
                <p className="mt-3 text-sm text-dark-200">Вход...</p>
              </div>
            )}

            {!loading && (
              <form onSubmit={handlePasswordLogin} className="space-y-4 mb-5">
                {/* Username */}
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-dark-100 text-sm font-medium">
                    Логин
                  </Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-dark-300" />
                    <Input
                      id="username"
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="admin"
                      autoComplete="username"
                      autoFocus
                      className="pl-10"
                    />
                  </div>
                </div>

                {/* Password */}
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-dark-100 text-sm font-medium">
                    Пароль
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-dark-300" />
                    <Input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="current-password"
                      className="pl-10"
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  className={cn(
                    'w-full h-11 font-medium text-sm',
                    'bg-gradient-to-r from-teal-600 to-cyan-600',
                    'hover:from-teal-500 hover:to-cyan-500',
                    'shadow-lg shadow-teal-900/20',
                    'transition-all duration-200'
                  )}
                  disabled={!username.trim() || !password.trim()}
                >
                  <KeyRound className="w-4 h-4 mr-2" />
                  Войти
                </Button>
              </form>
            )}

            {/* Footer */}
            <div className="mt-8 pt-5 border-t border-[var(--glass-border)]">
              <p className="text-center text-[11px] text-dark-300/80 leading-relaxed">
                Только для администраторов
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}