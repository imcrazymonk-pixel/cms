import { useEffect, useRef } from 'react'
import { useAuthStore } from '@/store/authStore'
import { toast } from 'sonner'

/**
 * Live support WebSocket — connects to /api/support/ws, authenticates with the
 * JWT from the auth store and relays server events into callbacks.
 *
 * Protocol:
 *   1. client → { "type": "auth", "token": "<JWT>" }  (first frame, within 5s)
 *   2. server → { "type": "message"|"message_updated"|"conversation"|"poller"|"ai_suggestion"|"presence"|"sla_alert", "data": {...} }
 *      plus a {"type":"ping"} heartbeat every 30s.
 *   close 4401 → token invalid/expired (we stop and redirect to /admin/login).
 *
 * Reconnect backoff: 2s → 5s → 10s → 30s (cap), reset on a successful open.
 */

const BACKOFF = [2000, 5000, 10000, 30000] as const
const AUTH_EXPIRED_CODE = 4401

export interface SupportEventPayload {
  type:
    | 'message'
    | 'message_updated'
    | 'conversation'
    | 'poller'
    | 'ai_suggestion'
    | 'presence'
    | 'sla_alert'
    | 'ping'
  data?: Record<string, unknown>
}

export interface SupportSocketHandlers {
  onMessage?: (data: Record<string, unknown>) => void
  onMessageUpdated?: (data: Record<string, unknown>) => void
  onConversation?: (data: Record<string, unknown>) => void
  onPoller?: (data: Record<string, unknown>) => void
  /** Новая/изменённая ИИ-предложка: `{conversation_id, suggestion_id, status}`. */
  onAiSuggestion?: (data: Record<string, unknown>) => void
  /** Отметка присутствия оператора: `{conversation_id, actor_id, state}`. */
  onPresence?: (data: Record<string, unknown>) => void
  /** Просрочка SLA: `{conversation_id, kind, due_at, overdue_minutes}`. */
  onSlaAlert?: (data: Record<string, unknown>) => void
  onAuthExpired?: () => void
  onStatusChange?: (connected: boolean) => void
}

/** Токен читаем из localStorage в том же формате, что api/client.ts. */
function readToken(): string | null {
  return useAuthStore.getState().token
}

function socketUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss://' : 'ws://'
  return `${proto}${window.location.host}/api/support/ws`
}

function redirectToLogin() {
  // client.ts редиректит на /admin/login (basename приложения — /admin).
  window.location.href = '/admin/login'
}

class SupportSocketClient {
  private ws: WebSocket | null = null
  private stopped = false
  private retry = 0
  private reconnectTimer: number | null = null

  constructor(private readonly handlers: SupportSocketHandlers) {}

  connect() {
    this.stopped = false
    this.open()
  }

  dispose() {
    this.stopped = true
    if (this.reconnectTimer !== null) window.clearTimeout(this.reconnectTimer)
    if (this.ws) {
      this.ws.onclose = null
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.close()
      this.ws = null
    }
  }

  private open() {
    if (this.stopped) return
    const token = readToken()
    if (!token) {
      // Нет сессии — не переподключаемся, ждём следующего монтирования страницы.
      return
    }

    const ws = new WebSocket(socketUrl())
    this.ws = ws

    ws.onopen = () => {
      this.retry = 0
      this.handlers.onStatusChange?.(true)
      ws.send(JSON.stringify({ type: 'auth', token }))
    }

    ws.onmessage = (event) => this.dispatch(event.data)

    ws.onclose = (event) => {
      this.ws = null
      this.handlers.onStatusChange?.(false)
      if (this.stopped) return
      if (event.code === AUTH_EXPIRED_CODE) {
        this.stopped = true
        toast.error('Сессия истекла — войдите заново')
        this.handlers.onAuthExpired?.()
        redirectToLogin()
        return
      }
      this.scheduleReconnect()
    }

    ws.onerror = () => {
      // onclose сработает следом — реконнект обрабатывается там.
    }
  }

  private scheduleReconnect() {
    if (this.stopped || this.reconnectTimer !== null) return
    const delay = BACKOFF[Math.min(this.retry, BACKOFF.length - 1)]
    this.retry += 1
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.open()
    }, delay)
  }

  private dispatch(raw: unknown) {
    let frame: SupportEventPayload
    try {
      frame = JSON.parse(String(raw)) as SupportEventPayload
    } catch {
      return
    }
    if (!frame || frame.type === 'ping') return
    const data = frame.data || {}
    switch (frame.type) {
      case 'message':
        this.handlers.onMessage?.(data)
        break
      case 'message_updated':
        this.handlers.onMessageUpdated?.(data)
        break
      case 'conversation':
        this.handlers.onConversation?.(data)
        break
      case 'poller':
        this.handlers.onPoller?.(data)
        break
      case 'ai_suggestion':
        this.handlers.onAiSuggestion?.(frame.data ?? {})
        break
      case 'presence':
        this.handlers.onPresence?.(data)
        break
      case 'sla_alert':
        this.handlers.onSlaAlert?.(data)
        break
      default:
        break
    }
  }
}

/**
 * React hook — subscribes to live support events while mounted.
 * Handlers are read from a ref, so changing them never reconnects.
 */
export function useSupportSocket(handlers: SupportSocketHandlers) {
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  useEffect(() => {
    const client = new SupportSocketClient(handlersRef.current)
    client.connect()
    return () => client.dispose()
  }, [])
}
