import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { supportApi, type ConversationPriority, type ConversationStatus } from '@/api/support'
import { useSupportSocket } from '@/lib/supportSocket'
import { toast } from 'sonner'
import { toastMutationError } from '@/lib/mutationToast'
import { Button } from '@/components/ui/button'
import { ConversationList } from './components/ConversationList'
import { MessageThread } from './components/MessageThread'
import { CustomerCard } from './components/CustomerCard'

const PAGE_SIZE = 20
const LIST_REFETCH_DEBOUNCE = 400

export default function SupportQueue() {
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const [activeId, setActiveId] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const listRefreshTimer = useRef<number | null>(null)

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
  })

  // ── Запросы ───────────────────────────────────────────────────
  const listQuery = useInfiniteQuery({
    queryKey: ['support-conversations', statusFilter, debouncedSearch],
    queryFn: ({ pageParam }) =>
      supportApi.listConversations({
        status: statusFilter || undefined,
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
    mutationFn: ({ id, text }: { id: number; text: string }) => supportApi.replyConversation(id, { text }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['support-conversation', data.conversation_id] })
      scheduleListRefresh()
      toast.success('Ответ отправлен')
    },
    onError: (err) => toastMutationError(err, 'Не удалось отправить ответ'),
  })

  const stateMutation = useMutation({
    mutationFn: ({
      id,
      patch,
    }: {
      id: number
      patch: { status?: ConversationStatus; priority?: ConversationPriority }
    }) => supportApi.setState(id, { status: patch.status as ConversationStatus, priority: patch.priority }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['support-conversation', data.conversation_id] })
      scheduleListRefresh()
      toast.success('Статус обновлён')
    },
    onError: (err) => toastMutationError(err, 'Не удалось обновить статус'),
  })

  const assignMutation = useMutation({
    mutationFn: ({ id, assignee_id }: { id: number; assignee_id: number }) =>
      supportApi.setAssignee(id, { assignee_id }),
    onSuccess: () => {
      scheduleListRefresh()
      queryClient.invalidateQueries({ queryKey: ['support-conversation', activeId] })
      toast.success('Диалог взят в работу')
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

  // ── Обработчики ─────────────────────────────────────────────
  const handleSelect = (id: number) => {
    setActiveId(id)
  }

  const handleReply = (text: string) => {
    if (activeId == null) return
    replyMutation.mutate({ id: activeId, text })
  }

  const handleState = (patch: { status?: ConversationStatus; priority?: ConversationPriority }) => {
    if (activeId == null) return
    stateMutation.mutate({ id: activeId, patch })
  }

  const handleAssign = () => {
    if (activeId == null || user?.id == null) return
    assignMutation.mutate({ id: activeId, assignee_id: user.id })
  }

  const handleResolve = () => {
    if (activeId == null) return
    stateMutation.mutate({ id: activeId, patch: { status: 'resolved' } })
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

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[340px_minmax(0,1fr)] 2xl:grid-cols-[340px_minmax(0,1fr)_340px] 2xl:items-start">
        {/* Список */}
        <div className="xl:h-[calc(100vh-190px)]">
          <ConversationList
            items={conversations}
            activeId={activeId}
            isLoading={listQuery.isLoading}
            hasNextPage={listQuery.hasNextPage || false}
            isFetchingNextPage={listQuery.isFetchingNextPage}
            statusFilter={statusFilter}
            search={search}
            onStatusFilter={setStatusFilter}
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
            assigneePending={assignMutation.isPending}
            statePending={stateMutation.isPending}
            sending={replyMutation.isPending}
            onMarkRead={handleMarkRead}
            onState={handleState}
            onAssign={handleAssign}
            onResolve={handleResolve}
            onReply={handleReply}
          />
        </div>

        {/* Карточка клиента */}
        <div className="hidden 2xl:block 2xl:h-[calc(100vh-190px)] 2xl:overflow-y-auto">
          <CustomerCard
            card={activeId != null ? customerQuery.data : undefined}
            isLoading={activeId != null && customerQuery.isLoading}
            isRefreshing={refreshCustomerMutation.isPending}
            onRefresh={() => {
              if (activeId != null) refreshCustomerMutation.mutate(activeId)
            }}
          />
        </div>
      </div>
    </div>
  )
}
