import { useEffect, useState } from 'react'
import { SlidersHorizontal, Save } from 'lucide-react'
import type { SupportAiSettings, SupportAiSettingsUpdate } from '@/api/support'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

export interface ParamsCardProps {
  settings: SupportAiSettings
  pending: boolean
  onSave: (update: SupportAiSettingsUpdate) => void
}

/** Порог уверенности, опора на КБ, лимит автоответов и склейка сообщений. */
export function ParamsCard({ settings, pending, onSave }: ParamsCardProps) {
  const [minConfidence, setMinConfidence] = useState<number>(settings.min_confidence)
  const [requireKb, setRequireKb] = useState<boolean>(settings.require_kb)
  const [autoPerHour, setAutoPerHour] = useState<string>(String(settings.auto_per_hour))
  const [debounce, setDebounce] = useState<string>(String(settings.debounce_seconds))

  // Сервер — источник истины: после сохранения/перезагрузки подтягиваем значения.
  useEffect(() => {
    setMinConfidence(settings.min_confidence)
    setRequireKb(settings.require_kb)
    setAutoPerHour(String(settings.auto_per_hour))
    setDebounce(String(settings.debounce_seconds))
  }, [settings])

  const handleSave = () => {
    const auto = Math.max(0, Number.parseInt(autoPerHour, 10) || 0)
    const debounceValue = Math.min(60, Math.max(3, Number.parseInt(debounce, 10) || 3))
    onSave({
      min_confidence: Math.min(1, Math.max(0.5, Number(minConfidence.toFixed(2)))),
      require_kb: requireKb,
      auto_per_hour: auto,
      debounce_seconds: debounceValue,
    })
  }

  return (
    <Card className="space-y-3 p-4 md:p-5">
      <div className="flex items-center gap-2">
        <SlidersHorizontal className="h-4 w-4 text-primary-300" />
        <h2 className="text-sm font-semibold text-white">Параметры</h2>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <Label className="text-xs text-dark-200">Минимальная уверенность</Label>
          <span className="text-xs font-medium text-white">{minConfidence.toFixed(2)}</span>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="range"
            min={0.5}
            max={1}
            step={0.05}
            value={minConfidence}
            onChange={(e) => setMinConfidence(Number(e.target.value))}
            className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-[var(--glass-bg-hover)] accent-primary-500"
            aria-label="Минимальная уверенность"
          />
          <Input
            type="number"
            min={0.5}
            max={1}
            step={0.05}
            value={minConfidence}
            onChange={(e) => setMinConfidence(Number(e.target.value))}
            className="w-20"
          />
        </div>
        <p className="text-[11px] text-dark-400">
          Ниже порога ИИ не отвечает автоматически, а оставляет предложку оператору.
        </p>
      </div>

      <div className="flex items-center justify-between gap-4 py-1">
        <div className="min-w-0">
          <p className="text-xs text-dark-100">Требовать опору на базу знаний</p>
          <p className="text-[11px] text-dark-400">Ответ без использованных статей уйдёт оператору</p>
        </div>
        <Switch checked={requireKb} onCheckedChange={setRequireKb} disabled={pending} />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label className="text-xs text-dark-200" htmlFor="ai-auto-per-hour">
            Автоответов в час
          </Label>
          <Input
            id="ai-auto-per-hour"
            type="number"
            min={0}
            value={autoPerHour}
            onChange={(e) => setAutoPerHour(e.target.value)}
          />
          <p className="text-[11px] text-dark-400">0 — без лимита</p>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs text-dark-200" htmlFor="ai-debounce">
            Склейка сообщений, сек
          </Label>
          <Input
            id="ai-debounce"
            type="number"
            min={3}
            max={60}
            value={debounce}
            onChange={(e) => setDebounce(e.target.value)}
          />
          <p className="text-[11px] text-dark-400">3–60 секунд</p>
        </div>
      </div>

      <div className="flex justify-end">
        <Button size="sm" onClick={handleSave} disabled={pending}>
          <Save className="mr-1.5 h-3.5 w-3.5" /> Сохранить
        </Button>
      </div>
    </Card>
  )
}
