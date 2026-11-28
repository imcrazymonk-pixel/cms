import { Link } from 'react-router-dom'
import { AlertTriangle, KeyRound, Sparkles } from 'lucide-react'
import type { SupportAiMode, SupportAiSettings } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

const MODE_ORDER: SupportAiMode[] = ['off', 'shadow', 'suggest', 'auto']

const MODE_LABEL: Record<SupportAiMode, string> = {
  off: 'Выключен',
  shadow: 'Тень',
  suggest: 'Предложка',
  auto: 'Автоответ',
}

const MODE_HINT: Record<SupportAiMode, string> = {
  off: 'ИИ не вмешивается',
  shadow: 'Генерирует, но не показывает и не отправляет',
  suggest: 'Черновик оператору в тред',
  auto: 'Отправляет сам, если ворота пропустили',
}

export interface ModeCardProps {
  settings: SupportAiSettings
  pending: boolean
  onChange: (mode: SupportAiMode) => void
}

/** Режим ИИ-помощника: 4 сегмента + фактический режим и баннер про ключ. */
export function ModeCard({ settings, pending, onChange }: ModeCardProps) {
  const noKey = !settings.has_key
  const actualMismatch = settings.effective_mode !== settings.mode

  return (
    <Card className="space-y-3 p-4 md:p-5">
      <div className="flex flex-wrap items-center gap-2">
        <Sparkles className="h-4 w-4 text-primary-300" />
        <h2 className="text-sm font-semibold text-white">Режим</h2>
        <Badge variant={settings.effective_mode === 'off' ? 'secondary' : 'success'}>
          фактически: {MODE_LABEL[settings.effective_mode]}
        </Badge>
      </div>

      {noKey && (
        <div className="flex items-start gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-2.5 text-xs text-yellow-200">
          <AlertTriangle className="mt-px h-4 w-4 shrink-0" />
          <div className="min-w-0 space-y-1">
            <p className="flex items-center gap-1.5 font-medium text-yellow-300">
              <KeyRound className="h-3.5 w-3.5" /> Ключ API не задан
            </p>
            <p>
              Без ключа ИИ не работает. Укажите ключ в{' '}
              <Link to="/settings?from=support_ai" className="text-primary-300 underline underline-offset-2 hover:text-primary-200">
                настройках → «ИИ / Саппорт»
              </Link>
              .
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {MODE_ORDER.map((mode) => {
          const active = settings.mode === mode
          const blocked = noKey && (mode === 'suggest' || mode === 'auto')
          return (
            <Button
              key={mode}
              variant={active ? 'default' : 'secondary'}
              size="sm"
              onClick={() => onChange(mode)}
              disabled={pending || blocked}
              title={blocked ? 'Сначала задайте ключ API' : MODE_HINT[mode]}
              aria-pressed={active}
              className={cn('h-auto py-2', active && 'ring-1 ring-primary-400/40')}
            >
              <span className="flex flex-col items-start gap-0.5 text-left">
                <span className="text-xs font-semibold">{MODE_LABEL[mode]}</span>
                <span className="whitespace-normal text-[10px] font-normal text-dark-300">
                  {MODE_HINT[mode]}
                </span>
              </span>
            </Button>
          )
        })}
      </div>

      {actualMismatch && (
        <p className="text-[11px] text-yellow-300">
          Задан режим «{MODE_LABEL[settings.mode]}», но фактически выключен
          {noKey ? ': нет ключа API' : ''}.
        </p>
      )}

      <p className="text-[11px] text-dark-400">
        Модель: {settings.model}
        {settings.fallback_model ? ` · фолбэк: ${settings.fallback_model}` : ''}
      </p>
    </Card>
  )
}
