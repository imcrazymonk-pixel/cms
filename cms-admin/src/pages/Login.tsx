import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, Lock, AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { login } from '../api/auth'
import { useAuth } from '../store/authStore'

export default function LoginPage() {
  const [loginField, setLoginField] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login(loginField, password)
      setAuth(res.token, res.user)
      navigate('/admin')
    } catch {
      setError('Неверный логин или пароль')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-bg min-h-screen flex items-center justify-center p-4">
      {/* Animated orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full opacity-10" style={{ background: 'radial-gradient(circle, var(--mesh-color-2) 0%, transparent 70%)', animation: 'login-orb-float 20s ease-in-out infinite' }} />
        <div className="absolute -bottom-40 -right-40 w-[500px] h-[500px] rounded-full opacity-10" style={{ background: 'radial-gradient(circle, var(--mesh-color-1) 0%, transparent 70%)', animation: 'login-orb-float 25s ease-in-out infinite reverse' }} />
      </div>

      <div className="login-card-enter w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-primary flex items-center justify-center text-white font-bold text-3xl login-logo-glow mb-4">
            H
          </div>
          <h1 className="text-2xl font-bold text-white">HexaVeil CMS</h1>
          <p className="text-sm text-dark-200 mt-1">Войдите в панель управления</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-[var(--glass-border)] glass-card overflow-hidden">
          <div className="p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium text-dark-100">Логин или Email</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-300" />
                  <Input
                    value={loginField}
                    onChange={(e) => setLoginField(e.target.value)}
                    className="pl-10"
                    placeholder="admn"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-dark-100">Пароль</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-300" />
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10"
                    placeholder="••••••••"
                    required
                  />
                </div>
              </div>

              <Button type="submit" disabled={loading} className="w-full h-11">
                {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Вход...</> : 'Войти'}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}