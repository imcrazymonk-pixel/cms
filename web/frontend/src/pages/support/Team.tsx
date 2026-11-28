import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  ScrollText,
  Users,
} from 'lucide-react'
import {
  getSupportErrorMessage,
  supportApi,
  type SupportAuditItem,
  type SupportOperator,
} from '@/api/support'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'
import { QueryError } from '@/components/QueryError'

const PER_PAGE = 25
const ALL_ACTIONS = '__all__'

type BadgeVariant = 'default' | 'success' | 'warning' | 'destructive' | 'secondary'

function statusVariant(status: string): BadgeVariant {
  if (status === 'active') return 'success'
  if (status === 'banned') return 'destructive'
  return 'secondary'
}

function statusLabel(status: string): string {
  if (status === 'active') return 'Активен'
  if (status === 'banned') return 'Заблокирован'
  if (status === 'inactive') return 'Неактивен'
  return status
}

function actionVariant(action: string): BadgeVariant {
  if (action.includes('delete') || action.includes('reject')) return 'destructive'
  if (action.includes('create') || action.includes('accept')) return 'success'
  if (action.includes('update')) return 'warning'
  return 'secondary'
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatPayload(payload: Record<string, unknown> | null | undefined): string {
  if (!payload) return '—'
  try {
    const text = JSON.stringify(payload)
    if (!text || text === '{}') return '—'
    return text.length > 80 ? `${text.slice(0, 79)}…` : text
  } catch {
    return '—'
  }
}

function OperatorCard({ operator }: { operator: SupportOperator }) {
  return (
    <div className="rounded-xl border border-[var(--glass-border)]/50 bg-[var(--glass-bg)] p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-white">
            {operator.display_name || operator.login}
          </p>
          <p className="truncate text-xs text-dark-300">@{operator.login}</p>
        </div>
        <Badge variant={statusVariant(operator.status)}>{statusLabel(operator.status)}</Badge>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-dark-300">
        <span
          className={cn(
            'inline-flex items-center gap-1.5',
            operator.present ? 'text-green-400' : 'text-dark-400',
          )}
          title={operator.present ? 'Оператор открывал панель недавно' : 'Оператора давно не было'}
        >
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              operator.present ? 'bg-green-400' : 'bg-dark-500',
            )}
          />
          {operator.present ? 'в панели' : 'не в сети'}
        </span>
        <span>
          Диалогов:{' '}
          <span className="tabular-nums text-white">{operator.active_dialogs}</span>
        </span>
        <span>
          Ответов 30д:{' '}
          <span className="tabular-nums text-white">{operator.replies_30d}</span>
        </span>
      </div>
    </div>
  )
}

function AuditRow({ item }: { item: SupportAuditItem }) {
  return (
    <tr className="border-b border-[var(--glass-border)]/30 last:border-b-0 align-top">
      <td className="whitespace-nowrap px-4 py-2 text-xs text-dark-200 md:px-6">
        {formatDateTime(item.created_at)}
      </td>
      <td className="px-4 py-2 md:px-6">
        <p className="text-dark-100">{item.actor_name || '—'}</p>
        <p className="text-[11px] text-dark-400">
          {item.actor_id != null ? `id ${item.actor_id}` : 'без автора'}
        </p>
      </td>
      <td className="px-4 py-2 md:px-6">
        <Badge variant={actionVariant(item.action)} className="font-mono">
          {item.action}
        </Badge>
      </td>
      <td className="px-4 py-2 text-xs text-dark-200 md:px-6">
        <span className="font-mono">{item.resource}</span>
        {item.resource_id ? (
          <span className="text-dark-400">#{item.resource_id}</span>
        ) : null}
      </td>
      <td className="px-4 py-2 text-xs text-dark-300 md:px-6">
        <span className="font-mono" title={JSON.stringify(item.payload ?? {})}>
          {formatPayload(item.payload)}
        </span>
      </td>
    </tr>
  )
}

/**
 * Команда саппорта (`/support/team`).
 *
 * Слева-сверху — все админы как операторы: статус, присутствие в панели,
 * активные диалоги и ответы за 30 дней. Ниже — журнал аудита с фильтром по
 * действию и постраничной навигацией. Оба блока только читают данные.
 */
export default function SupportTeamPage() {
  const [action, setAction] = useState<string>(ALL_ACTIONS)
  const [page, setPage] = useState(1)

  const operatorsQuery = useQuery({
    queryKey: ['support', 'team', 'operators'],
    queryFn: supportApi.listOperators,
    refetchOnWindowFocus: true,
  })

  const actionsQuery = useQuery({
    queryKey: ['support', 'team', 'audit-actions'],
    queryFn: supportApi.listAuditActions,
  })

  const auditQuery = useQuery({
    queryKey: ['support', 'team', 'audit', action, page],
    queryFn: () =>
      supportApi.listAudit({
        action: action === ALL_ACTIONS ? undefined : action,
        page,
        per_page: PER_PAGE,
      }),
    refetchOnWindowFocus: true,
  })

  const operators = operatorsQuery.data?.items ?? []
  const actions = actionsQuery.data?.items ?? []
  const audit = auditQuery.data
  const total = audit?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  const handleRefresh = () => {
    void operatorsQuery.refetch()
    void actionsQuery.refetch()
    void auditQuery.refetch()
  }

  const handleActionChange = (value: string) => {
    setAction(value)
    setPage(1)
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Команда</h1>
          <p className="mt-1 text-sm text-dark-200">
            Присутствие операторов и журнал действий ·{' '}
            {operatorsQuery.isLoading ? '…' : `${operators.length} операторов`}
          </p>
        </div>
        <div className="page-header-actions">
          <Button
            variant="secondary"
            size="icon"
            onClick={handleRefresh}
            disabled={
              operatorsQuery.isFetching || actionsQuery.isFetching || auditQuery.isFetching
            }
            aria-label="Обновить"
          >
            <RefreshCw
              className={cn(
                'h-5 w-5',
                (operatorsQuery.isFetching || auditQuery.isFetching) && 'animate-spin',
              )}
            />
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Операторы</CardTitle>
        </CardHeader>
        <CardContent>
          {operatorsQuery.isError ? (
            <QueryError
              onRetry={() => {
                void operatorsQuery.refetch()
              }}
              message={
                getSupportErrorMessage(operatorsQuery.error) ||
                'Не удалось загрузить операторов'
              }
            />
          ) : operatorsQuery.isLoading ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-24 w-full" />
              ))}
            </div>
          ) : operators.length === 0 ? (
            <EmptyState
              icon={Users}
              size="sm"
              title="Операторов нет"
              description="Список собирается из администраторов панели."
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {operators.map((operator) => (
                <OperatorCard key={operator.id} operator={operator} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-3 pb-2 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle>Журнал действий</CardTitle>
          <div className="w-full sm:w-72">
            <Select value={action} onValueChange={handleActionChange}>
              <SelectTrigger aria-label="Фильтр по действию">
                <SelectValue placeholder="Все действия" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_ACTIONS}>Все действия</SelectItem>
                {actions.map((item) => (
                  <SelectItem key={item.action} value={item.action}>
                    {item.action} ({item.count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0 md:p-0">
          {auditQuery.isError ? (
            <div className="p-4 md:p-6">
              <QueryError
                onRetry={() => {
                  void auditQuery.refetch()
                }}
                message={
                  getSupportErrorMessage(auditQuery.error) || 'Не удалось загрузить журнал'
                }
              />
            </div>
          ) : auditQuery.isLoading ? (
            <div className="space-y-3 p-4 md:p-6">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : !audit || audit.items.length === 0 ? (
            <EmptyState
              icon={ScrollText}
              size="lg"
              title="Журнал пуст"
              description={
                action === ALL_ACTIONS
                  ? 'Здесь появятся действия операторов: заметки, шаблоны, SLA и другие изменения.'
                  : 'По выбранному действию записей нет — попробуйте другой фильтр.'
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--glass-border)]/40 text-left text-xs uppercase tracking-wide text-dark-400">
                    <th className="px-4 py-2 font-medium md:px-6">Время</th>
                    <th className="px-4 py-2 font-medium md:px-6">Кто</th>
                    <th className="px-4 py-2 font-medium md:px-6">Действие</th>
                    <th className="px-4 py-2 font-medium md:px-6">Ресурс</th>
                    <th className="px-4 py-2 font-medium md:px-6">Payload</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.items.map((item) => (
                    <AuditRow key={item.id} item={item} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
        {!auditQuery.isLoading && !auditQuery.isError && total > 0 && (
          <div className="flex flex-col gap-2 border-t border-[var(--glass-border)]/40 px-4 py-3 text-sm text-dark-300 sm:flex-row sm:items-center sm:justify-between md:px-6">
            <p>
              Всего: <span className="tabular-nums text-white">{total}</span> · страница{' '}
              <span className="tabular-nums text-white">{page}</span> из{' '}
              <span className="tabular-nums text-white">{totalPages}</span>
            </p>
            <div className="flex items-center gap-1">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                disabled={page <= 1 || auditQuery.isFetching}
              >
                <ChevronLeft className="mr-1 h-4 w-4" />
                Назад
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                disabled={page >= totalPages || auditQuery.isFetching}
              >
                Вперёд
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
