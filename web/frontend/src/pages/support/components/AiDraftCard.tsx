import { useState } from 'react'
import { ChevronDown, Send, PenLine, Ban, StickyNote, BookOpen, AlertTriangle, Loader2 } from 'lucide-react'
import type { SupportAiSuggestion } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

/** Подписи уровней уверенности (порог считается на бэкенде от настроек). */
const LEVEL_LABEL: Record<string, { label: string; variant: 'success' | 'warning' | 'destructive' }> = {
  sure: { label: 'Уверен', variant: 'success' },
  check: { label: 'Проверьте', variant: 'warning' },
  unsure: { label: 'Не уверен', variant: 'destructive' },
}

const GATE_LABEL: Record<string, string> = {
  auto: 'Автоответ',
  suggest: 'Предложка',
  shadow: 'Тень',
  skip: 'Пропуск',
}

/** Фиксированный набор причин отказа — бэкенд принимает только эти значения. */
const REJECT_REASONS: Array<{ value: string; label: string }> = [
  { value: 'wrong_facts', label: 'Неверные факты' },
  { value: 'unclear', label: 'Непонятно' },
  { value: 'off_topic', label: 'Не по теме' },
  { value: 'too_formal', label: 'Слишком формально' },
  { value: 'sensitive', label: 'Чувствительная тема' },
  { value: 'other', label: 'Другое' },
]

export type SuggestionDecision = 'send' | 'edit' | 'reject'

export interface AiDraftCardProps {
  suggestion: SupportAiSuggestion
  pending: boolean
  onDecide: (decision: SuggestionDecision, opts?: { final_text?: string; reason?: string }) => void
  onEdit: (text: string) => void
  onWrong: (payload: { verdict: 'wrong'; corrected_text?: string }) => void
}

/**
 * Карточка ИИ-черновика в треде (план §6.3).
 *
 * Показывается над композером, только для `suggest`-предложек: в `shadow`
 * клиенту ничего не уходит и оператору карточка не нужна — компонент
 * возвращает `null`. «Заметка для оператора» рендерится отдельным блоком и
 * никогда не попадает в текст ответа.
 */
export function AiDraftCard({ suggestion, pending, onDecide, onEdit, onWrong }: AiDraftCardProps) {
  const [whyOpen, setWhyOpen] = useState(false)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [wrongOpen, setWrongOpen] = useState(false)
  const [wrongText, setWrongText] = useState('')

  // shadow-предложки оператору не показываем (см. TASK.md, долг #4).
  if (suggestion.gate?.action === 'shadow') return null

  const draftText = suggestion.final_text || suggestion.text || ''
  const level = LEVEL_LABEL[suggestion.level] ?? { label: suggestion.level, variant: 'secondary' as const }
  const gateAction = suggestion.gate?.action ?? ''
  const gateLabel = GATE_LABEL[gateAction] ?? gateAction

  const handleReject = () => {
    if (!reason) return
    onDecide('reject', { reason })
    setRejectOpen(false)
    setReason('')
  }

  const handleWrong = () => {
    onWrong({ verdict: 'wrong', corrected_text: wrongText.trim() || undefined })
    setWrongOpen(false)
    setWrongText('')
  }

  return (
    <div className="glass-card m-3 space-y-2.5 p-3">
      {/* Заголовок: уровень + режим */}
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge variant={level.variant}>ИИ · {level.label}</Badge>
        {gateLabel && <Badge variant="secondary">{gateLabel}</Badge>}
        {typeof suggestion.confidence === 'number' && (
          <span className="text-[11px] text-dark-400">
            уверенность {Math.round(suggestion.confidence * 100)}%
          </span>
        )}
      </div>

      {/* Текст черновика */}
      <div className="rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] p-2.5">
        <p className="whitespace-pre-wrap break-words text-sm text-white">
          {draftText || <span className="text-dark-400">Модель не предложила текст</span>}
        </p>
      </div>

      {/* Источники */}
      {suggestion.used.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <BookOpen className="h-3.5 w-3.5 text-dark-400" />
          {suggestion.used.map((doc, index) => (
            <span
              key={`${doc.doc_id ?? 'doc'}-${index}`}
              title={doc.title}
              className="max-w-[220px] truncate rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg-hover)] px-2 py-0.5 text-[11px] text-dark-200"
            >
              {doc.title || `Статья ${doc.doc_id ?? ''}`}
            </span>
          ))}
        </div>
      )}

      {/* Почему так? */}
      <div>
        <button
          type="button"
          onClick={() => setWhyOpen((v) => !v)}
          aria-expanded={whyOpen}
          className="inline-flex items-center gap-1 text-[11px] text-dark-300 transition-colors hover:text-white"
        >
          <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', whyOpen && 'rotate-180')} />
          Почему так?
        </button>
        {whyOpen && (
          <div className="mt-2 space-y-2 rounded-lg border border-[var(--glass-border)] bg-black/15 p-2.5 text-xs">
            {suggestion.reason && (
              <p className="text-dark-200">
                <span className="text-dark-400">Модель: </span>
                {suggestion.reason}
              </p>
            )}
            {suggestion.gate?.reason && (
              <p className="text-dark-200">
                <span className="text-dark-400">Ворота: </span>
                {suggestion.gate.reason}
              </p>
            )}
            {suggestion.operator_note && (
              <div className="rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg-hover)] p-2">
                <p className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-dark-300">
                  <StickyNote className="h-3 w-3" />
                  Заметка для оператора
                </p>
                <p className="mt-1 whitespace-pre-wrap break-words text-dark-100">
                  {suggestion.operator_note}
                </p>
                <p className="mt-1 text-[10px] text-dark-400">Клиенту не отправляется</p>
              </div>
            )}
            {!suggestion.reason && !suggestion.gate?.reason && !suggestion.operator_note && (
              <p className="text-dark-400">Пояснений нет.</p>
            )}
          </div>
        )}
      </div>

      {/* Действия */}
      <div className="flex flex-wrap items-center gap-1.5">
        <Button size="sm" onClick={() => onDecide('send')} disabled={pending || !draftText}>
          {pending ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Send className="mr-1.5 h-3.5 w-3.5" />}
          Отправить
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onEdit(draftText)}
          disabled={pending || !draftText}
          title="Перенести черновик в поле ответа и отправить обычным способом"
        >
          <PenLine className="mr-1.5 h-3.5 w-3.5" /> Править
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setRejectOpen(true)}
          disabled={pending}
        >
          <Ban className="mr-1.5 h-3.5 w-3.5" /> Отклонить
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setWrongOpen((v) => !v)}
          disabled={pending}
          className="text-dark-300 hover:text-white"
        >
          <AlertTriangle className="mr-1.5 h-3.5 w-3.5" /> Это неверно
        </Button>
      </div>

      {/* Фидбек «Это неверно» */}
      {wrongOpen && (
        <div className="space-y-2 rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] p-2.5">
          <label className="block text-[11px] text-dark-200" htmlFor={`wrong-${suggestion.id}`}>
            Как правильно?
          </label>
          <textarea
            id={`wrong-${suggestion.id}`}
            value={wrongText}
            onChange={(e) => setWrongText(e.target.value)}
            rows={2}
            placeholder="Необязательно: правильный ответ для обучения"
            className="w-full resize-none rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] p-2 text-xs text-white placeholder:text-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
          />
          <div className="flex justify-end gap-1.5">
            <Button variant="ghost" size="sm" onClick={() => setWrongOpen(false)} disabled={pending}>
              Отмена
            </Button>
            <Button variant="secondary" size="sm" onClick={handleWrong} disabled={pending}>
              Сохранить
            </Button>
          </div>
        </div>
      )}

      {/* Отклонение: причина обязательна */}
      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Почему отклоняем?</DialogTitle>
            <DialogDescription>
              Причина уходит в обучение и статистику. Выберите один вариант.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            {REJECT_REASONS.map((item) => (
              <label
                key={item.value}
                className={cn(
                  'flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors',
                  reason === item.value
                    ? 'border-primary-500/50 bg-[var(--glass-bg-hover)] text-white'
                    : 'border-[var(--glass-border)] text-dark-200 hover:bg-[var(--glass-bg-hover)]',
                )}
              >
                <input
                  type="radio"
                  name={`reject-reason-${suggestion.id}`}
                  value={item.value}
                  checked={reason === item.value}
                  onChange={() => setReason(item.value)}
                  className="h-3.5 w-3.5 accent-primary-500"
                />
                {item.label}
              </label>
            ))}
          </div>
          <DialogFooter className="gap-2">
            <Button variant="ghost" size="sm" onClick={() => setRejectOpen(false)} disabled={pending}>
              Отмена
            </Button>
            <Button variant="destructive" size="sm" onClick={handleReject} disabled={pending || !reason}>
              Отклонить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
