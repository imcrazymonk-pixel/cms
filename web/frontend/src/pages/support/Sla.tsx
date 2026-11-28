import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AlertTriangle, RefreshCw, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import {
  getSupportErrorMessage,
  supportApi,
  type SupportSlaEvent,
  type SupportSlaPolicy,
} from '@/api/support'
import { toastMutationError } from '@/lib/mutationToast'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/EmptyState'
import { QueryError } from '@/components/QueryError'

const POLICY_ORDER: Record<string, number> = { low: 0, normal: 1, high: 2, urgent: 3 }

const POLICY_LABEL: Record<string, string> = {
  low: 'Низкий',
  normal: 'Обычный',
  high: 'Высокий',
  urgent: 'Срочный',
}

const KIND_LABEL: Record<SupportSlaEvent['kind'], string> = {
  first_response: 'Первый ответ',
  resolution: 'Решение',
}

type BadgeVariant = 'default' | 'warning' | 'destructive' | 'secondary'

const PRIORITY_LABEL: Record<string, string> = {
  low: 'Низкий',
  normal: 'Обычный',
  high: 'Высокий',
  urgent: 'Срочный',
}

const PRIORITY_VARIANT: Record<string, BadgeVariant> = {
  low: 'secondary',
  normal: 'default',
  high: 'warning',
  urgent: 'destructive',
}

const MIN_MINUTES = 1
const MAX_MINUTES = 100_000

function isPositiveInt(value: number): boolean {
  return Number.isInteger(value) && value >= MIN_MINUTES && value <= MAX_MINUTES
}

/** Минуты → человекочитаемая длительность рядом с числом. */
function formatDuration(minutes: number): string {
  if (!Number.isFinite(minutes) || minutes <= 0) return '—'
  if (minutes >= 1440) {
    const days = minutes / 1440
    return Number.isInteger(days) ? `${days} д` : `${days.toFixed(1)} д`
  }
  if (minutes >= 60) {
    const hours = minutes / 60
    return Number.isInteger(hours) ? `${hours} ч` : `${hours.toFixed(1)} ч`
  }
  return `${Math.max(1, Math.round(minutes))} мин`
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function sortPolicies(items: SupportSlaPolicy[]): SupportSlaPolicy[] {
  return [...items].sort(
    (a, b) =>
      (POLICY_ORDER[a.name] ?? 99) - (POLICY_ORDER[b.name] ?? 99) ||
      a.name.localeCompare(b.name),
  )
}

interface PolicyRowProps {
  policy: SupportSlaPolicy
  saving: boolean
  onSave: (name: string, firstResponse: number, resolution: number) => void
}

function PolicyRow({ policy, saving, onSave }: PolicyRowProps) {
  const [first, setFirst] = useState(String(policy.first_response_minutes))
  const [resolution, setResolution] = useState(String(policy.resolution_minutes))

  useEffect(() => {
    setFirst(String(policy.first_response_minutes))
    setResolution(String(policy.resolution_minutes))
  }, [policy.name, policy.first_response_minutes, policy.resolution_minutes])

  const firstValue = Number(first)
  const resolutionValue = Number(resolution)
  const valid = isPositiveInt(firstValue) && isPositiveInt(resolutionValue)
  const dirty =
    firstValue !== policy.first_response_minutes ||
    resolutionValue !== policy.resolution_minutes

  return (
    <form
      className="flex flex-col gap-3 border-b border-[var(--glass-border)]/40 py-4 first:pt-0 last:border-b-0 last:pb-0 lg:flex-row lg:items-end"
      onSubmit={(event) => {
        event.preventDefault()
        if (valid) onSave(policy.name, firstValue, resolutionValue)
      }}
    >
      <div className="shrink-0 lg:w-40">
        <p className="text-sm font-medium text-white">
          {POLICY_LABEL[policy.name] ?? policy.name}
        </p>
        <p className="mt-0.5 text-xs text-dark-300">приоритет «{policy.name}»</p>
      </div>

      <div className="grid flex-1 gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor={`sla-${policy.name}-first`}>Первый ответ, мин</Label>
          <Input
            id={`sla-${policy.name}-first`}
            type="number"
            min={MIN_MINUTES}
            max={MAX_MINUTES}
            step={1}
            inputMode="numeric"
            value={first}
            onChange={(event) => setFirst(event.target.value)}
          />
          <p className="text-xs text-dark-300">≈ {formatDuration(firstValue)}</p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor={`sla-${policy.name}-resolution`}>Решение, мин</Label>
          <Input
            id={`sla-${policy.name}-resolution`}
            type="number"
            min={MIN_MINUTES}
            max={MAX_MINUTES}
            step={1}
            inputMode="numeric"
            value={resolution}
            onChange={(event) => setResolution(event.target.value)}
          />
          <p className="text-xs text-dark-300">≈ {formatDuration(resolutionValue)}</p>
        </div>
      </div>

      <div className="flex flex-col gap-1 lg:w-32">
        <Button type="submit" size="sm" disabled={saving || !valid || !dirty}>
          {saving ? 'Сохранение…' : 'Сохранить'}
        </Button>
        {!valid && (
          <p className="text-xs text-red-400">От 1 до 100 000 минут</p>
        )}
      </div>
    </form>
  )
}

function BreachCounter({ label, value }: { label: string; value: number }) {
  const dangerous = value > 0
  return (
    <div className="rounded-xl border border-[var(--glass-border)]/50 bg-[var(--glass-bg)] p-3">
      <p className="text-xs text-dark-300">{label}</p>
      <p
        className={cn(
          'mt-1 text-3xl font-semibold tabular-nums',
          dangerous ? 'text-red-400' : 'text-green-400',
        )}
      >
        {value}
      </p>
      <p className="mt-0.5 text-xs text-dark-300">
        {dangerous ? 'требуют внимания' : 'нарушений нет'}
      </p>
    </div>
  )
}

/**
 * Контроль SLA (`/support/sla`).
 *
 * Политики правятся по строкам (PUT на приоритет), обзор — один запрос:
 * счётчики нарушений и активные события с дедлайном в ближайший час.
 * Отрицательный `overdue_minutes` означает «до дедлайна ещё есть время».
 */
export default function SupportSlaPage() {
  const queryClient = useQueryClient()

  const overviewQuery = useQuery({
    queryKey: ['support', 'sla', 'overview'],
    queryFn: () => supportApi.getSlaOverview(7),
    refetchOnWindowFocus: true,
  })

  const saveMutation = useMutation({
    mutationFn: (payload: {
      name: string
      first_response_minutes: number
      resolution_minutes: number
    }) =>
      supportApi.updateSlaPolicy(payload.name, {
        first_response_minutes: payload.first_response_minutes,
        resolution_minutes: payload.resolution_minutes,
      }),
    onSuccess: (policy) => {
      toast.success(`Политика «${POLICY_LABEL[policy.name] ?? policy.name}» сохранена`)
      void queryClient.invalidateQueries({ queryKey: ['support', 'sla'] })
    },
    onError: (err) => {
      const message = getSupportErrorMessage(err)
      if (message) {
        toast.error(message, { duration: 8000 })
        return
      }
      toastMutationError(err, 'Не удалось сохранить политику SLA')
    },
  })

  const policies = useMemo(
    () => sortPolicies(overviewQuery.data?.policies ?? []),
    [overviewQuery.data?.policies],
  )
  const events = overviewQuery.data?.events ?? []
  const breaches = overviewQuery.data?.breaches ?? { first_response: 0, resolution: 0 }

  const handleRefresh = () => {
    void overviewQuery.refetch()
  }

  const handleSave = (name: string, firstResponse: number, resolution: number) => {
    saveMutation.mutate({
      name,
      first_response_minutes: firstResponse,
      resolution_minutes: resolution,
    })
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Контроль SLA</h1>
          <p className="mt-1 text-sm text-dark-200">
            Политики первого ответа и решения ·{' '}
            {overviewQuery.isLoading ? '…' : `${events.length} событий в окне`}
          </p>
        </div>
        <div className="page-header-actions">
          <Button
            variant="secondary"
            size="icon"
            onClick={handleRefresh}
            disabled={overviewQuery.isFetching}
            aria-label="Обновить"
          >
            <RefreshCw
              className={cn('h-5 w-5', overviewQuery.isFetching && 'animate-spin')}
            />
          </Button>
        </div>
      </div>

      {overviewQuery.isError && (
        <QueryError onRetry={handleRefresh} message="Не удалось загрузить обзор SLA" />
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-start">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Политики</CardTitle>
          </CardHeader>
          <CardContent>
            {overviewQuery.isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : policies.length === 0 ? (
              <p className="py-6 text-sm text-dark-300">
                Политики не загружены. Проверьте, что миграция засеяла приоритеты.
              </p>
            ) : (
              policies.map((policy) => (
                <PolicyRow
                  key={policy.name}
                  policy={policy}
                  saving={
                    saveMutation.isPending && saveMutation.variables?.name === policy.name
                  }
                  onSave={handleSave}
                />
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Просрочки</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              <BreachCounter
                label="Первый ответ"
                value={breaches.first_response}
              />
              <BreachCounter label="Решение" value={breaches.resolution} />
            </div>
            <p className="mt-3 text-xs text-dark-300">
              Активные события, у которых уже истёк дедлайн.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>События</CardTitle>
        </CardHeader>
        <CardContent className="p-0 md:p-0">
          {overviewQuery.isLoading ? (
            <div className="space-y-3 p-4 md:p-6">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : events.length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              size="lg"
              title="Просрочек нет"
              description="Здесь появятся диалоги, у которых дедлайн первого ответа или решения наступит в ближайший час."
            />
          ) : (
            <div className="divide-y divide-[var(--glass-border)]/40">
              {events.map((event) => {
                const overdue = event.overdue_minutes
                const breached = overdue != null && overdue > 0
                const remaining = overdue != null && overdue < 0
                const overdueText = breached
                  ? `Просрочено на ${formatDuration(overdue)}`
                  : remaining
                    ? `Осталось ${formatDuration(-overdue)}`
                    : overdue === 0
                      ? 'Дедлайн наступил'
                      : '—'

                return (
                  <div
                    key={`${event.conversation_id}-${event.kind}`}
                    className="flex flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between md:px-6"
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          to="/support"
                          className="font-mono text-sm text-primary-300 hover:underline"
                          title="Открыть очередь поддержки"
                        >
                          #{event.conversation_id}
                        </Link>
                        <Badge variant={PRIORITY_VARIANT[event.priority] ?? 'secondary'}>
                          {PRIORITY_LABEL[event.priority] ?? event.priority}
                        </Badge>
                        <Badge
                          variant={event.kind === 'first_response' ? 'default' : 'warning'}
                        >
                          {KIND_LABEL[event.kind] ?? event.kind}
                        </Badge>
                      </div>
                      <p className="truncate text-sm text-dark-100">
                        {event.subject || 'Без темы'}
                      </p>
                      <p className="text-xs text-dark-300">
                        Дедлайн: {formatDateTime(event.due_at)}
                      </p>
                    </div>

                    <div
                      className={cn(
                        'shrink-0 text-sm font-medium',
                        breached
                          ? 'text-red-400'
                          : remaining
                            ? 'text-dark-200'
                            : 'text-yellow-400',
                      )}
                    >
                      {breached && (
                        <AlertTriangle className="mr-1 inline h-4 w-4 align-[-2px]" />
                      )}
                      {overdueText}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
