import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import {
  getSupportErrorMessage,
  supportApi,
  type SupportAiMode,
  type SupportAiPauseRequest,
  type SupportAiSettingsUpdate,
} from '@/api/support'
import { toastMutationError } from '@/lib/mutationToast'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { ModeCard } from './components/assistant/ModeCard'
import { PauseCard } from './components/assistant/PauseCard'
import { ParamsCard } from './components/assistant/ParamsCard'
import { StatsCard } from './components/assistant/StatsCard'
import { TryPanel } from './components/assistant/TryPanel'
import { cn } from '@/lib/utils'

/**
 * ИИ-ассистент саппорта (`/support/ai`).
 *
 * Настройки и статистика — разными запросами; любая запись настроек/паузы
 * инвалидирует `support-assistant-settings`, чтобы экран не расходился с
 * бэкендом. Песочница живёт отдельно и ничего не пишет.
 */
export default function SupportAssistantPage() {
  const queryClient = useQueryClient()
  const [days, setDays] = useState<7 | 30>(30)

  const settingsQuery = useQuery({
    queryKey: ['support-assistant-settings'],
    queryFn: supportApi.getAssistantSettings,
    refetchOnWindowFocus: true,
  })

  const statsQuery = useQuery({
    queryKey: ['support-assistant-stats', days],
    queryFn: () => supportApi.assistantStats(days),
    refetchOnWindowFocus: true,
  })

  const handleError = (err: unknown, fallback: string) => {
    const message = getSupportErrorMessage(err)
    if (message) {
      toast.error(message, { duration: 8000 })
      return
    }
    toastMutationError(err, fallback)
  }

  const invalidateSettings = () => {
    queryClient.invalidateQueries({ queryKey: ['support-assistant-settings'] })
    // Настройки ИИ влияют на живой статус саппорта в очереди.
    queryClient.invalidateQueries({ queryKey: ['support-config-status'] })
  }

  const settingsMutation = useMutation({
    mutationFn: (update: SupportAiSettingsUpdate) => supportApi.updateAssistantSettings(update),
    onSuccess: (data) => {
      queryClient.setQueryData(['support-assistant-settings'], data)
      invalidateSettings()
      toast.success('Настройки сохранены')
    },
    onError: (err) => handleError(err, 'Не удалось сохранить настройки ИИ'),
  })

  const pauseMutation = useMutation({
    mutationFn: (payload: SupportAiPauseRequest) => supportApi.pauseAssistant(payload),
    onSuccess: () => {
      invalidateSettings()
      toast.success('Помощник поставлен на паузу')
    },
    onError: (err) => handleError(err, 'Не удалось поставить на паузу'),
  })

  const resumeMutation = useMutation({
    mutationFn: () => supportApi.resumeAssistant(),
    onSuccess: () => {
      invalidateSettings()
      toast.success('Пауза снята')
    },
    onError: (err) => handleError(err, 'Не удалось снять паузу'),
  })

  const handleModeChange = (mode: SupportAiMode) => {
    if (settingsQuery.data?.mode === mode) return
    settingsMutation.mutate({ mode })
  }

  const handleRefresh = () => {
    void settingsQuery.refetch()
    void statsQuery.refetch()
  }

  const settings = settingsQuery.data
  const fetching = settingsQuery.isFetching || statsQuery.isFetching

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">ИИ-ассистент</h1>
          <p className="mt-1 text-sm text-dark-200">
            Режим ответов, порог уверенности и песочница ·{' '}
            {settings ? `модель ${settings.model}` : 'загрузка…'}
          </p>
        </div>
        <div className="page-header-actions">
          <Button variant="secondary" size="icon" onClick={handleRefresh} disabled={fetching} aria-label="Обновить">
            <RefreshCw className={cn('h-5 w-5', fetching && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {settingsQuery.isError && (
        <QueryError
          message={getSupportErrorMessage(settingsQuery.error) || 'Не удалось загрузить настройки ИИ'}
          onRetry={() => { void settingsQuery.refetch() }}
        />
      )}

      {settingsQuery.isLoading && !settings ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="space-y-3 p-4 md:p-5">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-2/3" />
            </Card>
          ))}
        </div>
      ) : settings ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <ModeCard
            settings={settings}
            pending={settingsMutation.isPending}
            onChange={handleModeChange}
          />
          <PauseCard
            settings={settings}
            pending={pauseMutation.isPending || resumeMutation.isPending}
            onPause={(payload) => pauseMutation.mutate(payload)}
            onResume={() => resumeMutation.mutate()}
          />
          <ParamsCard
            settings={settings}
            pending={settingsMutation.isPending}
            onSave={(update) => settingsMutation.mutate(update)}
          />
          <StatsCard
            stats={statsQuery.data}
            days={days}
            loading={statsQuery.isLoading}
            onDaysChange={setDays}
          />
          <div className="lg:col-span-2">
            <TryPanel />
          </div>
        </div>
      ) : null}
    </div>
  )
}
