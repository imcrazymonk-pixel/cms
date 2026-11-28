import { Pause, Play, Clock } from 'lucide-react'
import type { SupportAiPauseRequest, SupportAiSettings } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { formatDateUtil as formatDate } from '@/lib/useFormatters'

/** 09:00 следующего локального дня, сериализованное в ISO для бэкенда. */
function nextMorningIso(): string {
  const date = new Date()
  date.setDate(date.getDate() + 1)
  date.setHours(9, 0, 0, 0)
  return date.toISOString()
}

export interface PauseCardProps {
  settings: SupportAiSettings
  pending: boolean
  onPause: (payload: SupportAiPauseRequest) => void
  onResume: () => void
}

/** Пауза помощника: до какого времени, кем, быстрые кнопки и «Снять». */
export function PauseCard({ settings, pending, onPause, onResume }: PauseCardProps) {
  const pause = settings.paused

  return (
    <Card className="space-y-3 p-4 md:p-5">
      <div className="flex flex-wrap items-center gap-2">
        <Pause className="h-4 w-4 text-primary-300" />
        <h2 className="text-sm font-semibold text-white">Пауза</h2>
        {pause ? <Badge variant="warning">на паузе</Badge> : <Badge variant="secondary">активен</Badge>}
      </div>

      {pause ? (
        <div className="space-y-1 rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] p-2.5 text-xs text-dark-200">
          <p className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-yellow-400" />
            До <span className="font-medium text-white">{formatDate(pause.until)}</span>
          </p>
          <p>Поставил: {pause.by || '—'}</p>
          {pause.note && <p className="text-dark-300">Заметка: {pause.note}</p>}
        </div>
      ) : (
        <p className="text-xs text-dark-300">
          Автоответы и предложки работают. Пауза не меняет режим — только глушит ИИ.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-1.5">
        <Button variant="secondary" size="sm" onClick={() => onPause({ hours: 1 })} disabled={pending}>
          1 ч
        </Button>
        <Button variant="secondary" size="sm" onClick={() => onPause({ hours: 4 })} disabled={pending}>
          4 ч
        </Button>
        <Button variant="secondary" size="sm" onClick={() => onPause({ hours: 24 })} disabled={pending}>
          24 ч
        </Button>
        <Button variant="outline" size="sm" onClick={() => onPause({ until: nextMorningIso() })} disabled={pending}>
          До утра
        </Button>
        <Button variant="ghost" size="sm" onClick={onResume} disabled={pending || !pause}>
          <Play className="mr-1.5 h-3.5 w-3.5" /> Снять
        </Button>
      </div>
    </Card>
  )
}
