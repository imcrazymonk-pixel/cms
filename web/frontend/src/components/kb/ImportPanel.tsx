import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { FileJson, FileUp, Loader2, MessageSquare, Upload, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import {
  getSupportErrorMessage,
  supportApi,
  type SupportImportJob,
  type SupportImportKind,
} from '@/api/support'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

const POLL_INTERVAL_MS = 1500

const STATUS_LABEL: Record<SupportImportJob['status'], string> = {
  queued: 'в очереди',
  running: 'выполняется',
  done: 'готово',
  error: 'ошибка',
}

export interface ImportPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Вызывается один раз, когда реальный (не dry-run) импорт завершился успешно. */
  onFinished: () => void
}

function progressPercent(job: SupportImportJob): number {
  if (!job.total) return job.status === 'queued' ? 0 : 35
  return Math.min(100, Math.round((job.progress / job.total) * 100))
}

/** Импорт истории: текст чата или `result.json` (файл читается в браузере). */
export function ImportPanel({ open, onOpenChange, onFinished }: ImportPanelProps) {
  const [kind, setKind] = useState<SupportImportKind>('text')
  const [text, setText] = useState('')
  const [payloadText, setPayloadText] = useState('')
  const [fileName, setFileName] = useState('')
  const [dryRun, setDryRun] = useState(true)
  const [starting, setStarting] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [job, setJob] = useState<SupportImportJob | null>(null)
  const notifiedRef = useRef(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const jobId = job?.id ?? null
  const jobStatus = job?.status ?? null
  const active = jobStatus === 'queued' || jobStatus === 'running'

  // Поллинг: 1.5 с, стоп на done/error.
  useEffect(() => {
    if (jobId == null || (jobStatus !== 'queued' && jobStatus !== 'running')) return
    let cancelled = false
    const timer = window.setInterval(async () => {
      try {
        const next = await supportApi.getImportJob(jobId)
        if (!cancelled) setJob(next)
      } catch (err) {
        if (!cancelled) {
          setError(getSupportErrorMessage(err) || 'Не удалось получить статус импорта')
        }
      }
    }, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [jobId, jobStatus])

  // После реального успешного импорта обновляем список статей (один раз).
  useEffect(() => {
    if (job?.status !== 'done' || job.result?.dry_run) return
    if (notifiedRef.current) return
    notifiedRef.current = true
    onFinished()
    toast.success('Импорт завершён')
  }, [job, onFinished])

  const reset = () => {
    setJob(null)
    setError(null)
    notifiedRef.current = false
  }

  const handleOpenChange = (next: boolean) => {
    if (!next && active) return // не закрываем во время работы задачи
    if (!next) reset()
    onOpenChange(next)
  }

  const handleFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      setPayloadText(String(reader.result ?? ''))
      setFileName(file.name)
      setError(null)
    }
    reader.onerror = () => toast.error('Не удалось прочитать файл')
    reader.readAsText(file)
    event.target.value = ''
  }

  const handleStart = async () => {
    setError(null)
    if (kind === 'text' && !text.trim()) {
      setError('Вставьте текст чата')
      return
    }
    if (kind === 'result_json' && !payloadText.trim()) {
      setError('Загрузите result.json')
      return
    }
    setStarting(true)
    notifiedRef.current = false
    try {
      const started = await supportApi.importKb({
        kind,
        text: kind === 'text' ? text : undefined,
        payload: kind === 'result_json' ? payloadText : undefined,
        dry_run: dryRun,
      })
      setJob({
        id: started.job_id,
        kind,
        status: 'queued',
        progress: 0,
        total: null,
        result: null,
        error: null,
        started_at: null,
        finished_at: null,
      })
    } catch (err) {
      setError(getSupportErrorMessage(err) || 'Не удалось запустить импорт')
    } finally {
      setStarting(false)
    }
  }

  const handleCancel = async () => {
    if (jobId == null) return
    setCancelling(true)
    try {
      const result = await supportApi.cancelImport(jobId)
      setJob((prev) =>
        prev
          ? { ...prev, status: result.status ?? 'error', error: result.error ?? 'cancelled' }
          : prev,
      )
    } catch (err) {
      setError(getSupportErrorMessage(err) || 'Не удалось отменить импорт')
    } finally {
      setCancelling(false)
    }
  }

  const percent = job ? progressPercent(job) : 0
  const result = job?.result

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Импорт базы знаний</DialogTitle>
          <DialogDescription>
            История чата превращается в пары «вопрос → ответ». Сначала прогоните dry-run:
            он ничего не записывает.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setKind('text')}
              disabled={active || starting}
              className={cn(
                'flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors',
                kind === 'text'
                  ? 'border-primary-500/50 bg-primary-500/15 text-primary-200'
                  : 'border-[var(--glass-border)] bg-[var(--glass-bg)] text-dark-200 hover:text-white',
              )}
            >
              <MessageSquare className="h-4 w-4" />
              Текст чата
            </button>
            <button
              type="button"
              onClick={() => setKind('result_json')}
              disabled={active || starting}
              className={cn(
                'flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors',
                kind === 'result_json'
                  ? 'border-primary-500/50 bg-primary-500/15 text-primary-200'
                  : 'border-[var(--glass-border)] bg-[var(--glass-bg)] text-dark-200 hover:text-white',
              )}
            >
              <FileJson className="h-4 w-4" />
              result.json
            </button>
          </div>

          {kind === 'text' ? (
            <div className="space-y-1.5">
              <Label htmlFor="import-text">Экспорт чата</Label>
              <Textarea
                id="import-text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={active || starting}
                rows={10}
                className="min-h-[12rem] font-mono text-[13px]"
                placeholder="Вставьте текст переписки в формате экспорта Telegram"
              />
            </div>
          ) : (
            <div className="space-y-1.5">
              <Label>Файл result.json</Label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                onChange={handleFile}
                className="hidden"
              />
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={active || starting}
                >
                  <FileUp className="mr-1.5 h-4 w-4" />
                  Выбрать файл
                </Button>
                <span className="text-xs text-dark-300">
                  {fileName || (payloadText ? 'файл загружен' : 'файл не выбран')}
                  {payloadText && ` · ${payloadText.length.toLocaleString('ru-RU')} символов`}
                </span>
              </div>
            </div>
          )}

          <label className="flex items-center gap-2 text-sm text-dark-200">
            <Checkbox
              checked={dryRun}
              onCheckedChange={(value) => setDryRun(value === true)}
              disabled={active || starting}
            />
            Проверка без записи (dry-run)
          </label>

          {error && <p className="text-sm text-red-400">{error}</p>}

          {job && (
            <div className="space-y-2 rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] p-3">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <span className="text-dark-200">
                  Задача #{job.id} · {STATUS_LABEL[job.status] ?? job.status}
                </span>
                <span className="text-dark-400">
                  {job.total ? `${job.progress} / ${job.total}` : ''}
                </span>
              </div>

              <div className="h-1.5 w-full overflow-hidden rounded-full bg-dark-700/60">
                <div
                  className={cn(
                    'h-full rounded-full bg-primary transition-all',
                    active && !job.total && 'w-1/3 animate-pulse',
                  )}
                  style={job.total ? { width: `${percent}%` } : undefined}
                />
              </div>

              {job.error && <p className="text-xs text-red-400">{job.error}</p>}

              {result && job.status === 'done' && (
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-dark-200 sm:grid-cols-3">
                  <span>Вопросов: {result.questions}</span>
                  <span>
                    {result.dry_run ? 'Будет создано' : 'Создано'}:{' '}
                    {result.dry_run ? result.would_create ?? 0 : result.pairs_created}
                  </span>
                  <span>
                    {result.dry_run ? 'Будет пропущено' : 'Пропущено'}:{' '}
                    {result.dry_run ? result.would_skip ?? 0 : result.skipped_duplicates}
                  </span>
                  <span>
                    Идей: {result.dry_run ? result.would_create_candidates ?? 0 : result.candidates_created}
                  </span>
                  {result.errors.length > 0 && (
                    <span className="text-amber-400">Ошибок: {result.errors.length}</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          {active ? (
            <Button variant="destructive" size="sm" onClick={handleCancel} disabled={cancelling}>
              <XCircle className="mr-1.5 h-4 w-4" />
              {cancelling ? 'Отмена…' : 'Отменить импорт'}
            </Button>
          ) : (
            <>
              {job && (
                <Button variant="ghost" size="sm" onClick={reset}>
                  Новый импорт
                </Button>
              )}
              <Button variant="secondary" size="sm" onClick={() => handleOpenChange(false)}>
                Закрыть
              </Button>
              <Button size="sm" onClick={handleStart} disabled={starting}>
                {starting ? (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-1.5 h-4 w-4" />
                )}
                Запустить
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
