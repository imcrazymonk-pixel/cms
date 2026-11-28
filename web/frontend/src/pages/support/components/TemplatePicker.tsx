import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, Loader2, Search } from 'lucide-react'
import { supportApi, type SupportTemplate } from '@/api/support'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'

const SEARCH_DEBOUNCE_MS = 250
const PREVIEW_CHARS = 60

/**
 * Общий запрос шаблонов для подбора в композере: попап «Шаблоны» и
 * слэш-подсказка используют один hook, поэтому одинаковый `q` не дублируется.
 */
export function useSupportTemplates(q: string, enabled = true) {
  return useQuery({
    queryKey: ['support', 'templates', 'picker', q],
    queryFn: () => supportApi.listTemplates({ q: q || undefined, per_page: 50 }),
    staleTime: 30_000,
    placeholderData: (previous) => previous,
    enabled,
  })
}

function preview(body: string): string {
  const flat = body.replace(/\s+/g, ' ').trim()
  return flat.length > PREVIEW_CHARS ? `${flat.slice(0, PREVIEW_CHARS)}…` : flat
}

export interface TemplatePickerProps {
  /** Вставляет тело выбранного шаблона в композер. */
  onPick: (body: string) => void
}

/** Кнопка «Шаблоны» над композером: поиск и выбор шаблона ответа. */
export function TemplatePicker({ onPick }: TemplatePickerProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(search.trim()), SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [search])

  const templatesQuery = useSupportTemplates(debounced)
  const items = templatesQuery.data?.items ?? []

  const handlePick = (template: SupportTemplate) => {
    onPick(template.body)
    // Статистика использований некритична — ошибку не показываем.
    supportApi.useTemplate(template.id).catch(() => {})
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" title="Вставить шаблон ответа">
          <FileText className="mr-1.5 h-4 w-4" /> Шаблоны
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80 p-0">
        <div className="border-b border-[var(--glass-border)] p-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-dark-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск шаблона…"
              className="h-8 pl-8 text-xs"
              autoFocus
            />
          </div>
        </div>

        <div className="max-h-72 overflow-y-auto p-1">
          {templatesQuery.isLoading ? (
            <div className="flex items-center justify-center gap-2 p-6 text-xs text-dark-300">
              <Loader2 className="h-4 w-4 animate-spin" /> Загрузка…
            </div>
          ) : items.length === 0 ? (
            <div className="p-4 text-center text-xs text-dark-300">
              Нет шаблонов — создайте на{' '}
              <Link
                to="/support/templates"
                className="text-primary-300 underline-offset-4 hover:underline"
                onClick={() => setOpen(false)}
              >
                /support/templates
              </Link>
            </div>
          ) : (
            <ul className="space-y-0.5">
              {items.map((template) => (
                <li key={template.id}>
                  <button
                    type="button"
                    onClick={() => handlePick(template)}
                    className={cn(
                      'w-full rounded-md px-2 py-1.5 text-left transition-colors',
                      'hover:bg-[var(--glass-bg-hover)]',
                    )}
                  >
                    <div className="flex items-baseline gap-2">
                      <span className="shrink-0 font-mono text-[11px] text-primary-300">/{template.shortcut}</span>
                      <span className="truncate text-xs font-medium text-dark-50">{template.title}</span>
                    </div>
                    <p className="mt-0.5 line-clamp-2 text-[11px] text-dark-300">{preview(template.body)}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}
