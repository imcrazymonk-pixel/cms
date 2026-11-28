import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FlaskConical, Loader2, Play, BookOpen } from 'lucide-react'
import { getSupportErrorMessage, supportApi, type SupportAiTryResult } from '@/api/support'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

const TEXT_MAX = 2000

const GATE_LABEL: Record<string, string> = {
  auto: 'Автоответ',
  suggest: 'Предложка',
  shadow: 'Тень',
  skip: 'Пропуск',
}

const LEVEL_LABEL: Record<string, string> = {
  sure: 'Уверен',
  check: 'Проверьте',
  unsure: 'Не уверен',
}

/** Песочница: прогнать вопрос через модель и ворота, ничего не записывая в БД. */
export function TryPanel() {
  const [text, setText] = useState('')
  const [assumeAuto, setAssumeAuto] = useState(false)

  const mutation = useMutation<SupportAiTryResult, unknown, { text: string; assume_auto: boolean }>({
    mutationFn: (vars) => supportApi.tryAssistant(vars),
  })

  const trimmed = text.trim()
  const canRun = trimmed.length >= 1 && trimmed.length <= TEXT_MAX && !mutation.isPending
  const result = mutation.data
  const errorText = mutation.error ? getSupportErrorMessage(mutation.error) || 'Не удалось проверить' : null

  return (
    <Card className="space-y-3 p-4 md:p-5">
      <div className="flex flex-wrap items-center gap-2">
        <FlaskConical className="h-4 w-4 text-primary-300" />
        <h2 className="text-sm font-semibold text-white">Песочница</h2>
        <span className="text-[11px] text-dark-400">Главный инструмент настройки порога · ничего не пишет в БД</span>
      </div>

      <div className="space-y-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, TEXT_MAX))}
          rows={4}
          placeholder="Вопрос клиента, например: «Не подключается Германия, что делать?»"
          className="w-full resize-y rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] p-3 text-sm text-white placeholder:text-dark-300 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
        />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <label className="inline-flex cursor-pointer items-center gap-2 text-xs text-dark-200">
              <input
                type="checkbox"
                checked={assumeAuto}
                onChange={(e) => setAssumeAuto(e.target.checked)}
                className="h-3.5 w-3.5 accent-primary-500"
              />
              Считать как auto
            </label>
            <span className="text-[11px] text-dark-400">
              {text.length}/{TEXT_MAX}
            </span>
          </div>
          <Button
            size="sm"
            onClick={() => mutation.mutate({ text: trimmed, assume_auto: assumeAuto })}
            disabled={!canRun}
          >
            {mutation.isPending ? (
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-1.5 h-4 w-4" />
            )}
            Проверить
          </Button>
        </div>
      </div>

      {errorText && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 p-2.5 text-xs text-red-300">
          {errorText}
        </p>
      )}

      {result && (
        <div className="space-y-2.5 rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] p-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant={result.gate.action === 'auto' ? 'success' : result.gate.action === 'skip' ? 'secondary' : 'warning'}>
              {GATE_LABEL[result.gate.action] ?? result.gate.action}
            </Badge>
            {result.gate.level && (
              <Badge variant="secondary">{LEVEL_LABEL[result.gate.level] ?? result.gate.level}</Badge>
            )}
            {typeof result.draft.confidence === 'number' && (
              <span className="text-[11px] text-dark-300">
                уверенность {Math.round(result.draft.confidence * 100)}%
              </span>
            )}
            {result.draft.needs_human && <Badge variant="destructive">нужен человек</Badge>}
            {result.draft.clarify && <Badge variant="warning">уточняющий вопрос</Badge>}
          </div>

          {result.gate.reason && (
            <p className="text-[11px] text-dark-300">
              <span className="text-dark-400">Причина ворот: </span>
              {result.gate.reason}
            </p>
          )}

          <div>
            <p className="mb-1 text-[10px] uppercase tracking-wide text-dark-400">Черновик ответа</p>
            <p className="whitespace-pre-wrap break-words text-sm text-white">
              {result.draft.reply || <span className="text-dark-400">Модель не предложила текст</span>}
            </p>
          </div>

          {result.draft.operator_note && (
            <div className="rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg-hover)] p-2">
              <p className="text-[10px] uppercase tracking-wide text-dark-300">Заметка для оператора</p>
              <p className="mt-1 whitespace-pre-wrap break-words text-xs text-dark-100">
                {result.draft.operator_note}
              </p>
              <p className="mt-1 text-[10px] text-dark-400">Клиенту не отправляется</p>
            </div>
          )}

          {result.draft.used.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <BookOpen className="h-3.5 w-3.5 text-dark-400" />
              {result.draft.used.map((doc, index) => (
                <span
                  key={`${doc.doc_id ?? 'doc'}-${index}`}
                  title={doc.title}
                  className="max-w-[240px] truncate rounded-md border border-[var(--glass-border)] bg-[var(--glass-bg-hover)] px-2 py-0.5 text-[11px] text-dark-200"
                >
                  {doc.title || `Статья ${doc.doc_id ?? ''}`}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
