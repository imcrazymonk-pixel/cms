import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, AlertTriangle, RefreshCw } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import {
  supportApi,
  getSupportErrorCode,
  getSupportErrorMessage,
  type ConversationPriority,
  type ConversationStatus,
  type PollerStatus,
  type SupportConfigStatus,
  type SupportMessage,
  type SupportSuggestionDecisionPayload,
} from '@/api/support'
import { useSupportSocket } from '@/lib/supportSocket'
import { toast } from 'sonner'
import { toastMutationError } from '@/lib/mutationToast'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { ConversationList } from './components/ConversationList'
import { MessageThread } from './components/MessageThread'
import { CustomerCard } from './components/CustomerCard'
import type { SuggestionDecision } from './components/AiDraftCard'

const PAGE_SIZE = 20
const LIST_REFETCH_DEBOUNCE = 400

function formatPollTime(value?: string | null): string {
  if (!value) return 'ещё не было'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function channelLabel(channel: string): string {
  if (!channel) return '—'
  if (channel === 'telegram') return 'Telegram'
  if (channel === 'bedolaga') return 'Bedolaga'
  return channel.charAt(0).toUpperCase() + channel.slice(1).replace(/_/g, ' ')
}

/** Время самого свежего сообщения в диалоге — для seen_at. */
function lastMessageTime(messages: SupportMessage[]): string | undefined {
  let latest: SupportMessage | undefined
  for (const message of messages) {
    if (!latest || new Date(message.created_at).getTime() > new Date(latest.created_at).getTime()) {
      latest = message
    }
  }
  return latest?.created_at
}

function PollerRow({ channel, status }: { channel: string; status?: PollerStatus }) {
  const label = channelLabel(channel)

  if (!status) {
    return (
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-medium text-dark-100">{label}</span>
        <Badge variant="secondary">не запущен</Badge>
        <span className="text-dark-300">нет данных от поллера</span>
      </div>
    )
  }

  const conflict = status.last_error === 'conflict'
  const badge = conflict ? (
    <Badge variant="destructive">конфликт</Badge>
  ) : status.running ? (
    <Badge variant="success">работает</Badge>
  ) : status.enabled ? (
    <Badge variant="warning">ожидание</Badge>
  ) : (
    <Badge variant="secondary">выключен</Badge>
  )

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-medium text-dark-100">{label}</span>
        {badge}
        <span className="text-dark-300">последний опрос: {formatPollTime(status.last_poll)}</span>
        {typeof status.ingested === 'number' && (
          <span className="text-dark-300">· обработано: {status.ingested}</span>
        )}
      </div>
      {conflict && (
        <p className="flex items-start gap-1.5 text-xs text-red-400">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-px" />
          Тот же токен опрашивает другой бот/webhook: остановите второй поллер или используйте
          отдельный токен
        </p>
      )}
      {!conflict && status.last_error && (
        <p className="text-xs text-yellow-400 break-all">Ошибка: {status.last_error}</p>
      )}
    </div>
  )
}

function PollerStatusPanel({
  pollers,
  config,
  isLoading,
  isError,
}: {
  pollers?: Record<string, PollerStatus>
  config?: SupportConfigStatus
  isLoading: boolean
  isError: boolean
}) {
  // Объединяем каналы из конфига и из ответа поллеров — без хардкода.
  const channels = useMemo(() => {
    const set = new Set<string>()
    for (const channel of config?.channels ?? []) set.add(channel)
    for (const channel of Object.keys(pollers ?? {})) set.add(channel)
    return Array.from(set).sort()
  }, [config, pollers])

  return (
    <Card className="p-4 md:p-5">
      <div className="mb-3 flex items-center gap-2">
        <Activity className="w-4 h-4 text-dark-300" />
        <h2 className="text-sm font-semibold text-white">Каналы поддержки</h2>
        {isLoading && <span className="text-xs text-dark-300">обновление…</span>}
        {isError && <Badge variant="warning">статус недоступен</Badge>}
      </div>

      {config && (
        <p className="mb-3 text-[11px] text-dark-300">
          Интервал опроса: {config.poll_interval_seconds} с · Окно ответа: {config.reply_window_hours} ч
          {channels.length > 0 && <> · Включены: {channels.map(channelLabel).join(', ')}</>}
        </p>
      )}

      {!pollers && isLoading ? (
        <p className="text-xs text-dark-300">Проверка статуса поллеров…</p>
      ) : !pollers && isError ? (
        <p className="text-xs text-yellow-400">Не удалось получить статус поллеров</p>
      ) : channels.length === 0 ? (
        <p className="text-xs text-dark-300">Каналы поддержки не настроены.</p>
      ) : (
        <div className="space-y-3">
          {channels.map((channel) => (
            <PollerRow key={channel} channel={channel} status={pollers?.[channel]} />
          ))}
        </div>
      )}
    </Card>
  )
}

export default function SupportQueue() {
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const [activeId, setActiveId] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [channelFilter, setChannelFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  /** Тик для переноса ИИ-черновика в композер («Править»). */
  const [suggestionEditSignal, setSuggestionEditSignal] = useState(0)
  /**
   * Текст, который «Править» переносит в композер. Фиксируется в onSuccess,
   * потому что после invalidateQueries suggestion может стать null раньше эффекта.
   */
  const [suggestionEditText, setSuggestionEditText] = useState('')
  const listRefreshTimer = useRef<number | null>(null)
  /** Попытка отправки — нужна, чтобы повторить с тем же client_msg_id (идемпотентность). */
  const pendingReplyRef = useRef<{
    id: number
    text: string
    attachment_ids: string[]
    client_msg_id: string
  } | null>(null)

  // Дебаунс поиска
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 400)
    return () => window.clearTimeout(timer)
  }, [search])

  const scheduleListRefresh = useCallback(() => {
    if (listRefreshTimer.current !== null) window.clearTimeout(listRefreshTimer.current)
    listRefreshTimer.current = window.setTimeout(() => {
      listRefreshTimer.current = null
      queryClient.invalidateQueries({ queryKey: ['support-conversations'] })
      queryClient.invalidateQueries({ queryKey: ['support-pollers'] })
    }, LIST_REFETCH_DEBOUNCE)
  }, [queryClient])

  // ── Live-события ──────────────────────────────────────────────
  useSupportSocket({
    onMessage: (data) => {
      const cid = Number(data.conversation_id)
      if (activeId != null && cid === activeId) {
        queryClient.invalidateQueries({ queryKey: ['support-conversation', activeId] })
        queryClient.invalidateQueries({ queryKey: ['support-customer', activeId] })
      }
      scheduleListRefresh()
    },
    onMessageUpdated: (data) => {
      const cid = Number(data.conversation_id)
      if (activeId != null && cid === activeId) {
        queryClient.invalidateQueries({ queryKey: ['support-conversation', activeId] })
      }
    },
    onConversation: () => scheduleListRefresh(),
    onPoller: () => queryClient.invalidateQueries({ queryKey: ['support-pollers'] }),
    onAiSuggestion: (data) => {
      const cid = Number(data.conversation_id)
      if (activeId != null && cid === activeId) {
        queryClient.invalidateQueries({ queryKey: ['support-conversation', activeId] })
      }
      scheduleListRefresh()
    },
    onPresence: (data) => {
      const cid = Number(data.conversation_id)
      if (activeId != null && cid === activeId) {
        queryClient.invalidateQueries({ queryKey: ['support', 'presence', activeId] })
      }
    },
    onSlaAlert: () => {
      queryClient.invalidateQueries({ queryKey: ['support', 'sla'] })
    },
  })

  // ── Запросы ───────────────────────────────────────────────────
  const listQuery = useInfiniteQuery({
    queryKey: ['support-conversations', statusFilter, channelFilter, priorityFilter, unreadOnly, debouncedSearch],
    queryFn: ({ pageParam }) =>
      supportApi.listConversations({
        status: statusFilter || undefined,
        channel: channelFilter || undefined,
        priority: priorityFilter || undefined,
        unread_only: unreadOnly || undefined,
        q: debouncedSearch || undefined,
        page: pageParam,
        per_page: PAGE_SIZE,
      }),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page * last.per_page < last.total ? last.page + 1 : undefined),
  })

  const conversations = useMemo(() => listQuery.data?.pages.flatMap((p) => p.items) ?? [], [listQuery.data])

  const detailQuery = useQuery({
    queryKey: ['support-conversation', activeId],
    queryFn: () => supportApi.getConversation(activeId as number),
    enabled: activeId != null,
    staleTime: 10_000,
  })

  const customerQuery = useQuery({
    queryKey: ['support-customer', activeId],
    queryFn: () => supportApi.getCustomer(activeId as number),
    enabled: activeId != null,
    staleTime: 30_000,
  })

  const pollersQuery = useQuery({
    queryKey: ['support-pollers'],
    queryFn: supportApi.getPollers,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  })

  const configQuery = useQuery({
    queryKey: ['support-config-status'],
    queryFn: supportApi.getConfigStatus,
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  })

  // ── Мутации ──────────────────────────────────────────────────
  const readMutation = useMutation({
    mutationFn: (id: number) => supportApi.readConversation(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['support-conversation', data.conversation_id] })
      scheduleListRefresh()
    },
    onError: (err) => toastMutationError(err, 'Не удалось отметить прочитанным'),
  })

  const replyMutation = useMutation({
    mutationFn: (vars: {
      id: number
      text: string
      attachment_ids: string[]
      client_msg_id: string
      force?: boolean
    }) =>
      supportApi.replyConversation(vars.id, {
        text: vars.text,
        attachment_ids: vars.attachment_ids,
        client_msg_id: vars.client_msg_id,
        force: vars.force,
      }),
    onSuccess: (data) => {
      pendingReplyRef.current = null
      queryClient.invalidateQueries({ queryKey: ['support-conversation', data.conversation_id] })
      scheduleListRefresh()
      toast.success(data.repeated ? 'Сообщение уже было отправлено' : 'Ответ отправлен')
    },
    onError: (err) => {
      const code = getSupportErrorCode(err)
      if (code === 'CLIENT_WROTE') {
        // Клиент написал после seen_at — статус не закрыт, надо перечитать диалог.
        toast.error('Клиент написал после прочтения — проверьте новые сообщения')
        if (activeId != null) {
          queryClient.invalidateQueries({ queryKey: ['support-conversation', activeId] })
        }
        queryClient.invalidateQueries({ queryKey: ['support-conversations'] })
        return
      }
      if (code === 'LOCKED_BY_OTHER') {
        const pending = pendingReplyRef.current
        toast.error('Диалог ведёт другой оператор', {
          action: pending
            ? {
                label: 'Всё равно отправить',
                onClick: () => replyMutation.mutate({ ...pending, force: true }),
              }
            : undefined,
        })
        return
      }
      // REPLY_WINDOW_CLOSED и прочее — прежнее поведение.
      toastMutationError(err, 'Не удалось отправить ответ')
    },
  })

  const stateMutation = useMutation({
    mutationFn: ({
      id,
      status,
      priority,
      seen_at,
    }: {
      id: number
      status: ConversationStatus
      priority?: ConversationPriority
      seen_at?: string
    }) => supportApi.setState(id, { status, priority, seen_at }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['support-conversation', data.conversation_id] })
      scheduleListRefresh()
      toast.success('Статус обновлён')
    },
    onError: (err) => {
      if (getSupportErrorCode(err) === 'CLIENT_WROTE') {
        toast.error('Клиент написал после прочтения — диалог не закрыт')
        if (activeId != null) {
          queryClient.invalidateQueries({ queryKey: ['support-conversation', activeId] })
        }
        queryClient.invalidateQueries({ queryKey: ['support-conversations'] })
        return
      }
      toastMutationError(err, 'Не удалось обновить статус')
    },
  })

  const assignMutation = useMutation({
    mutationFn: ({ id, assignee_id }: { id: number; assignee_id: number | null }) =>
      supportApi.setAssignee(id, { assignee_id }),
    onSuccess: (_data, variables) => {
      scheduleListRefresh()
      queryClient.invalidateQueries({ queryKey: ['support-conversation', variables.id] })
      toast.success(variables.assignee_id == null ? 'Диалог освобождён' : 'Диалог взят в работу')
    },
    onError: (err) => toastMutationError(err, 'Не удалось назначить оператора'),
  })

  const refreshCustomerMutation = useMutation({
    mutationFn: (id: number) => supportApi.refreshCustomer(id),
    onSuccess: (card) => {
      if (activeId != null) queryClient.setQueryData(['support-customer', activeId], card)
      toast.success('Карточка обновлена')
    },
    onError: (err) => toastMutationError(err, 'Не удалось обновить карточку'),
  })

  // ── ИИ: решение по предложке ─────────────────────────────────
  const suggestionDecisionMutation = useMutation({
    mutationFn: (vars: { id: number; payload: SupportSuggestionDecisionPayload }) =>
      supportApi.decideSuggestion(vars.id, vars.payload),
    onSuccess: (data, vars) => {
      if (vars.payload.decision === 'edit') {
        // Даём MessageThread сигнал забрать текст в композер до инвалидации.
        // Текст передаём явно: suggestion после invalidateQueries может стать null.
        setSuggestionEditText(vars.payload.final_text || '')
        setSuggestionEditSignal((n) => n + 1)
        toast.success('Черновик перенесён в поле ответа')
      } else if (data.status === 'sent') {
        toast.success('Ответ отправлен')
      } else {
        toast.success('Предложка отклонена')
      }
      if (activeId != null) {
        queryClient.invalidateQueries({ queryKey: ['support-conversation', activeId] })
      }
      scheduleListRefresh()
    },
    onError: (err) => {
      const code = getSupportErrorCode(err)
      if (code === 'AI_PAUSED') {
        toast.error('ИИ-помощник на паузе — ответ отправлен не будет')
        return
      }
      if (code === 'AI_KEY_MISSING') {
        toast.error('Ключ API ИИ не задан — настройте его в «Настройки → ИИ / Саппорт»')
        return
      }
      if (code === 'REPLY_WINDOW_CLOSED') {
        toast.error('Клиент давно не писал — отправка ограничена')
        return
      }
      if (code === 'CLIENT_WROTE') {
        toast.error('Клиент написал после прочтения — проверьте новые сообщения')
        if (activeId != null) {
          queryClient.invalidateQueries({ queryKey: ['support-conversation', activeId] })
        }
        return
      }
      const message = getSupportErrorMessage(err)
      if (message) {
        toast.error(message, { duration: 8000 })
        return
      }
      toastMutationError(err, 'Не удалось обработать предложку')
    },
  })

  // ── ИИ: обратная связь по ответу («Это неверно») ──────────────
  const feedbackMutation = useMutation({
    mutationFn: (vars: { messageId: number; correctAnswer?: string }) =>
      supportApi.messageFeedback(vars.messageId, {
        verdict: 'wrong',
        correct_answer: vars.correctAnswer,
      }),
    onSuccess: () => toast.success('Спасибо! Учли, как надо отвечать'),
    onError: (err) => {
      const message = getSupportErrorMessage(err)
      if (message) {
        toast.error(message, { duration: 8000 })
        return
      }
      toastMutationError(err, 'Не удалось отправить оценку')
    },
  })

  // ── Обработчики ─────────────────────────────────────────────
  const handleSelect = (id: number) => {
    setActiveId(id)
  }

  const handleReply = (text: string, attachmentIds: string[]) => {
    if (activeId == null) return
    const pending = {
      id: activeId,
      text,
      attachment_ids: attachmentIds,
      // Один id на попытку: повтор (в т.ч. force) не создаст дубль.
      client_msg_id: crypto.randomUUID(),
    }
    pendingReplyRef.current = pending
    replyMutation.mutate(pending)
  }

  // ── ИИ-предложка: обработчики для MessageThread ───────────────
  const suggestion = detailQuery.data?.suggestion ?? null

  const handleSuggestionDecision = (
    decision: SuggestionDecision,
    opts?: { final_text?: string; reason?: string },
  ) => {
    if (!suggestion) return
    suggestionDecisionMutation.mutate({
      id: suggestion.id,
      payload: { decision, final_text: opts?.final_text, reason: opts?.reason },
    })
  }

  // «Править»: бэкенд помечает предложку edited и сохраняет черновик,
  // текст переезжает в композер через suggestionEditSignal.
  const handleEditSuggestionText = (value: string) => {
    if (!suggestion) return
    suggestionDecisionMutation.mutate({
      id: suggestion.id,
      payload: { decision: 'edit', final_text: value },
    })
  }

  const handleSuggestionWrong = (payload: { verdict: 'wrong'; corrected_text?: string }) => {
    const messageId = suggestion?.message_id
    if (!messageId) {
      toast.error('Не к чему привязать оценку: у предложки нет входящего сообщения')
      return
    }
    feedbackMutation.mutate({ messageId, correctAnswer: payload.corrected_text })
  }

  const handleState = (patch: { status?: ConversationStatus; priority?: ConversationPriority }) => {
    if (activeId == null) return
    const conversation = detailQuery.data?.conversation
    const status = patch.status ?? conversation?.status
    if (!status) return
    // seen_at нужен только при фактическом закрытии/решении.
    const closing =
      (status === 'resolved' || status === 'closed') && status !== conversation?.status
    const seen_at =
      closing && detailQuery.data ? lastMessageTime(detailQuery.data.messages) : undefined
    stateMutation.mutate({ id: activeId, status, priority: patch.priority, seen_at })
  }

  const handleAssign = (assigneeId: number | null) => {
    if (activeId == null) return
    assignMutation.mutate({ id: activeId, assignee_id: assigneeId })
  }

  const handleResolve = () => {
    if (activeId == null) return
    handleState({ status: 'resolved' })
  }

  const handleMarkRead = (id: number) => readMutation.mutate(id)

  // ── Рендер ──────────────────────────────────────────────────
  return (
    <div className="space-y-4 md:space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Очередь обращений</h1>
          <p className="mt-1 text-sm text-dark-200">
            Живая очередь саппорта · {listQuery.isLoading ? '…' : conversations.length} показано
            {listQuery.data && <span className="ml-1 text-dark-300">из {listQuery.data.pages[0]?.total ?? 0}</span>}
          </p>
        </div>
        <div className="page-header-actions">
          <Button variant="secondary" size="icon" onClick={() => listQuery.refetch()} disabled={listQuery.isFetching} aria-label="Обновить очередь">
            <RefreshCw className={listQuery.isFetching ? 'h-5 w-5 animate-spin' : 'h-5 w-5'} />
          </Button>
        </div>
      </div>

      <PollerStatusPanel
        pollers={pollersQuery.data?.pollers}
        config={configQuery.data}
        isLoading={pollersQuery.isLoading}
        isError={pollersQuery.isError}
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[340px_minmax(0,1fr)] 2xl:grid-cols-[340px_minmax(0,1fr)_340px] 2xl:items-start">
        {/* Список */}
        <div className="xl:h-[calc(100vh-190px)]">
          <ConversationList
            items={conversations}
            total={listQuery.data?.pages[0]?.total ?? conversations.length}
            activeId={activeId}
            isLoading={listQuery.isLoading}
            hasNextPage={listQuery.hasNextPage || false}
            isFetchingNextPage={listQuery.isFetchingNextPage}
            statusFilter={statusFilter}
            channelFilter={channelFilter}
            priorityFilter={priorityFilter}
            unreadOnly={unreadOnly}
            search={search}
            onStatusFilter={setStatusFilter}
            onChannelFilter={setChannelFilter}
            onPriorityFilter={setPriorityFilter}
            onUnreadOnly={setUnreadOnly}
            onSearch={setSearch}
            onSelect={handleSelect}
            onLoadMore={() => listQuery.fetchNextPage()}
            onRefresh={() => listQuery.refetch()}
          />
        </div>

        {/* Переписка */}
        <div className="xl:h-[calc(100vh-190px)]">
          <MessageThread
            conversation={activeId != null ? detailQuery.data?.conversation : undefined}
            messages={activeId != null ? detailQuery.data?.messages ?? [] : []}
            isLoading={activeId != null && detailQuery.isLoading}
            currentUserId={user?.id ?? null}
            assigneePending={assignMutation.isPending}
            statePending={stateMutation.isPending}
            sending={replyMutation.isPending}
            onMarkRead={handleMarkRead}
            onState={handleState}
            onAssign={handleAssign}
            onResolve={handleResolve}
            onReply={handleReply}
            suggestion={suggestion}
            suggestionPending={suggestionDecisionMutation.isPending || feedbackMutation.isPending}
            onSuggestionDecision={handleSuggestionDecision}
            onEditSuggestionText={handleEditSuggestionText}
            onSuggestionWrong={handleSuggestionWrong}
            suggestionEditSignal={suggestionEditSignal}
            suggestionEditText={suggestionEditText}
            mediaMaxMb={configQuery.data?.media_max_mb ?? 8}
          />
        </div>

        {/* Карточка клиента */}
        <div className="hidden 2xl:block 2xl:h-[calc(100vh-190px)] 2xl:overflow-y-auto">
          <CustomerCard
            card={activeId != null ? customerQuery.data : undefined}
            isLoading={activeId != null && customerQuery.isLoading}
            isRefreshing={refreshCustomerMutation.isPending}
            customerProfileId={detailQuery.data?.conversation.customer_profile_id ?? null}
            currentUserId={user?.id ?? null}
            onRefresh={() => {
              if (activeId != null) refreshCustomerMutation.mutate(activeId)
            }}
          />
        </div>
      </div>
    </div>
  )
}
