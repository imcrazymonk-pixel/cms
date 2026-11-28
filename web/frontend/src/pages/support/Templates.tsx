import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, Plus, RefreshCw, Search, Trash2, Wand2, X } from 'lucide-react'
import { toast } from 'sonner'
import {
  getSupportErrorCode,
  getSupportErrorMessage,
  supportApi,
  type SupportTemplateInput,
  type SupportTemplateListResult,
} from '@/api/support'
import { toastMutationError } from '@/lib/mutationToast'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { EmptyState } from '@/components/EmptyState'
import { QueryError } from '@/components/QueryError'

const SEARCH_DEBOUNCE_MS = 300
const SHORTCUT_RE = /^[a-z0-9][a-z0-9_-]{0,31}$/
const SHORTCUT_HINT =
  'Только строчные латинские буквы, цифры, «_» и «-»; начинается с буквы или цифры; до 32 символов'
const MAX_BODY = 4000
const MAX_TITLE = 120

/**
 * Шаблоны ответов оператора (`/support/templates`).
 *
 * Слева — поиск (debounce 300 мс) и список; справа — редактор выбранного
 * шаблона или режим создания. Ярлык проверяется на клиенте тем же regexp,
 * что и на бэкенде; дубль (`409 TEMPLATE_EXISTS`) показывается тостом.
 */
export default function SupportTemplatesPage() {
  const queryClient = useQueryClient()

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [creating, setCreating] = useState(false)
  const [shortcut, setShortcut] = useState('')
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('')
  const [body, setBody] = useState('')
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [showErrors, setShowErrors] = useState(false)

  // Поиск с debounce 300 мс.
  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput.trim()), SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  // Новый запрос — сбрасываем выбор, чтобы не держать шаблон вне выдачи.
  useEffect(() => {
    setSelectedId(null)
  }, [search])

  const listQuery = useQuery({
    queryKey: ['support', 'templates', 'list', search],
    queryFn: () =>
      supportApi.listTemplates({
        q: search || undefined,
        page: 1,
        per_page: 100,
      }),
    refetchOnWindowFocus: true,
  })

  const items = listQuery.data?.items ?? []
  const total = listQuery.data?.total ?? 0
  const selected = useMemo(
    () => items.find((item) => item.id === selectedId) ?? null,
    [items, selectedId],
  )

  // Автовыбор первого шаблона, если ничего не выбрано.
  useEffect(() => {
    if (creating || selectedId !== null || items.length === 0) return
    setSelectedId(items[0].id)
  }, [creating, items, selectedId])

  // Подтягиваем данные выбранного шаблона в редактор.
  useEffect(() => {
    if (creating) return
    if (!selected) {
      setShortcut('')
      setTitle('')
      setCategory('')
      setBody('')
      return
    }
    setShortcut(selected.shortcut)
    setTitle(selected.title)
    setCategory(selected.category ?? '')
    setBody(selected.body)
  }, [creating, selected?.id, selected?.updated_at])

  const invalidateTemplates = () => {
    void queryClient.invalidateQueries({ queryKey: ['support', 'templates'] })
  }

  const handleError = (err: unknown, fallback: string) => {
    const code = getSupportErrorCode(err)
    if (code === 'TEMPLATE_EXISTS') {
      toast.error('Шаблон с таким ярлыком уже существует', { duration: 8000 })
      return
    }
    const message = getSupportErrorMessage(err)
    if (message) {
      toast.error(message, { duration: 8000 })
      return
    }
    toastMutationError(err, fallback)
  }

  const createMutation = useMutation({
    mutationFn: (data: SupportTemplateInput) => supportApi.createTemplate(data),
    onSuccess: (template) => {
      toast.success('Шаблон создан')
      setCreating(false)
      setSelectedId(template.id)
      queryClient.setQueriesData<SupportTemplateListResult>(
        { queryKey: ['support', 'templates', 'list'] },
        (prev) => {
          if (!prev || prev.items.some((item) => item.id === template.id)) return prev
          return { ...prev, items: [template, ...prev.items], total: prev.total + 1 }
        },
      )
      invalidateTemplates()
    },
    onError: (err) => handleError(err, 'Не удалось создать шаблон'),
  })

  const updateMutation = useMutation({
    mutationFn: (data: SupportTemplateInput) => {
      if (selectedId == null) throw new Error('Шаблон не выбран')
      return supportApi.updateTemplate(selectedId, data)
    },
    onSuccess: (template) => {
      toast.success('Шаблон сохранён')
      queryClient.setQueriesData<SupportTemplateListResult>(
        { queryKey: ['support', 'templates', 'list'] },
        (prev) =>
          prev
            ? {
                ...prev,
                items: prev.items.map((item) =>
                  item.id === template.id ? template : item,
                ),
              }
            : prev,
      )
      invalidateTemplates()
    },
    onError: (err) => handleError(err, 'Не удалось сохранить шаблон'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => supportApi.deleteTemplate(id),
    onSuccess: (_data, id) => {
      toast.success('Шаблон удалён')
      setDeleteOpen(false)
      setCreating(false)
      setSelectedId(null)
      queryClient.setQueriesData<SupportTemplateListResult>(
        { queryKey: ['support', 'templates', 'list'] },
        (prev) =>
          prev
            ? {
                ...prev,
                items: prev.items.filter((item) => item.id !== id),
                total: Math.max(0, prev.total - 1),
              }
            : prev,
      )
      invalidateTemplates()
    },
    onError: (err) => {
      setDeleteOpen(false)
      handleError(err, 'Не удалось удалить шаблон')
    },
  })

  const useTemplateMutation = useMutation({
    mutationFn: (id: number) => supportApi.useTemplate(id),
    onSuccess: (result) => {
      toast.success(`Шаблон использован (${result.uses})`)
      queryClient.setQueriesData<SupportTemplateListResult>(
        { queryKey: ['support', 'templates', 'list'] },
        (prev) =>
          prev
            ? {
                ...prev,
                items: prev.items.map((item) =>
                  item.id === result.id ? { ...item, uses: result.uses } : item,
                ),
              }
            : prev,
      )
      invalidateTemplates()
    },
    onError: (err) => handleError(err, 'Не удалось отметить использование шаблона'),
  })

  const shortcutValid = SHORTCUT_RE.test(shortcut)
  const shortcutLiveInvalid = shortcut.length > 0 && !shortcutValid
  const bodyTooLong = body.length > MAX_BODY
  const titleTooLong = title.length > MAX_TITLE
  const formValid =
    shortcutValid &&
    title.trim().length > 0 &&
    body.trim().length > 0 &&
    !bodyTooLong &&
    !titleTooLong
  const saving = createMutation.isPending || updateMutation.isPending

  const handleStartCreate = () => {
    setCreating(true)
    setSelectedId(null)
    setShortcut('')
    setTitle('')
    setCategory('')
    setBody('')
    setShowErrors(false)
  }

  const handleSelect = (id: number) => {
    setCreating(false)
    setShowErrors(false)
    setSelectedId(id)
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setShowErrors(true)
    if (!formValid) return
    const payload: SupportTemplateInput = {
      shortcut,
      title: title.trim(),
      body,
      category: category.trim() || null,
    }
    if (selectedId == null) {
      createMutation.mutate(payload)
      return
    }
    updateMutation.mutate(payload)
  }

  const handleRefresh = () => {
    void listQuery.refetch()
  }

  const showEditor = creating || selected != null
  const shortcutError =
    shortcutLiveInvalid || (showErrors && !shortcutValid)
      ? SHORTCUT_HINT
      : null

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">Шаблоны ответов</h1>
          <p className="mt-1 text-sm text-dark-200">
            Быстрые заготовки операторов ·{' '}
            {listQuery.isLoading ? '…' : `${total} шаблонов`}
          </p>
        </div>
        <div className="page-header-actions flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            size="icon"
            onClick={handleRefresh}
            disabled={listQuery.isFetching}
            aria-label="Обновить"
          >
            <RefreshCw
              className={cn('h-5 w-5', listQuery.isFetching && 'animate-spin')}
            />
          </Button>
          <Button size="sm" onClick={handleStartCreate}>
            <Plus className="mr-1.5 h-4 w-4" />
            Новый шаблон
          </Button>
        </div>
      </div>

      {listQuery.isError && (
        <QueryError onRetry={handleRefresh} message="Не удалось загрузить шаблоны" />
      )}

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        {/* Левая колонка */}
        <Card className="overflow-hidden">
          <div className="space-y-3 p-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dark-300" />
              <Input
                type="text"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Поиск по шаблонам…"
                className="pl-10 pr-8"
                autoComplete="off"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={() => setSearchInput('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-dark-400 hover:text-white"
                  aria-label="Очистить поиск"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            <p className="text-xs text-dark-300">
              {listQuery.isLoading ? 'Загрузка…' : `Найдено: ${total}`}
            </p>
          </div>

          <div className="max-h-[560px] overflow-y-auto border-t border-[var(--glass-border)]/50">
            {listQuery.isLoading ? (
              <div className="space-y-3 p-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : items.length === 0 ? (
              <div className="p-3">
                <EmptyState
                  icon={FileText}
                  size="sm"
                  title={search ? 'Ничего не найдено' : 'Шаблонов нет'}
                  description={
                    search
                      ? 'Попробуйте другой запрос'
                      : 'Создайте первый шаблон кнопкой «Новый шаблон»'
                  }
                />
              </div>
            ) : (
              items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleSelect(item.id)}
                  className={cn(
                    'w-full border-b border-[var(--glass-border)]/40 px-3 py-2.5 text-left transition-colors last:border-b-0 hover:bg-[var(--glass-bg-hover)]',
                    !creating &&
                      item.id === selectedId &&
                      'bg-[var(--glass-bg-hover)]',
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-sm text-primary-300">
                      /{item.shortcut}
                    </span>
                    <span className="text-xs text-dark-300">{item.uses} исп.</span>
                  </div>
                  <p className="truncate text-sm text-dark-100">{item.title}</p>
                  {item.category && (
                    <p className="truncate text-xs text-dark-300">{item.category}</p>
                  )}
                </button>
              ))
            )}
          </div>
        </Card>

        {/* Правая колонка */}
        <div className="min-w-0">
          {!showEditor ? (
            <Card>
              <EmptyState
                icon={FileText}
                size="lg"
                title="Шаблон не выбран"
                description="Выберите шаблон слева или создайте новый"
              />
            </Card>
          ) : (
            <Card>
              <CardHeader className="pb-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle>
                    {creating || selectedId == null ? 'Новый шаблон' : 'Редактор'}
                  </CardTitle>
                  {!creating && selected && (
                    <span className="text-xs text-dark-300">
                      использован {selected.uses} раз
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <form className="space-y-4" onSubmit={handleSubmit} noValidate>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-1.5">
                      <Label htmlFor="template-shortcut">Ярлык</Label>
                      <div className="relative">
                        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono text-sm text-dark-300">
                          /
                        </span>
                        <Input
                          id="template-shortcut"
                          value={shortcut}
                          onChange={(event) => setShortcut(event.target.value)}
                          placeholder="greeting"
                          maxLength={32}
                          autoComplete="off"
                          spellCheck={false}
                          aria-invalid={Boolean(shortcutError)}
                          className={cn(
                            'pl-7 font-mono',
                            shortcutError &&
                              'border-red-500/60 focus-visible:ring-red-500/40',
                          )}
                        />
                      </div>
                      {shortcutError ? (
                        <p className="text-xs text-red-400">{SHORTCUT_HINT}</p>
                      ) : (
                        <p className="text-xs text-dark-300">
                          Вызывается как /{shortcut || 'ярлык'}
                        </p>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="template-category">Категория</Label>
                      <Input
                        id="template-category"
                        value={category}
                        onChange={(event) => setCategory(event.target.value)}
                        placeholder="Например, оплата"
                        maxLength={64}
                        autoComplete="off"
                      />
                      <p className="text-xs text-dark-300">Необязательно</p>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="template-title">Название</Label>
                    <Input
                      id="template-title"
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                      placeholder="Приветствие"
                      maxLength={MAX_TITLE}
                      autoComplete="off"
                    />
                    {titleTooLong ? (
                      <p className="text-xs text-red-400">
                        Не больше {MAX_TITLE} символов
                      </p>
                    ) : (
                      <p className="text-xs text-dark-300">
                        {title.length} / {MAX_TITLE}
                      </p>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="template-body">Текст ответа</Label>
                    <Textarea
                      id="template-body"
                      value={body}
                      onChange={(event) => setBody(event.target.value)}
                      placeholder="Здравствуйте! Чем можем помочь?"
                      rows={14}
                      className="min-h-[320px]"
                    />
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className={bodyTooLong ? 'text-red-400' : 'text-dark-300'}>
                        {body.length} / {MAX_BODY}
                      </span>
                      {showErrors && body.trim().length === 0 && (
                        <span className="text-red-400">Текст не может быть пустым</span>
                      )}
                    </div>
                  </div>

                  {showErrors && title.trim().length === 0 && (
                    <p className="text-xs text-red-400">Название не может быть пустым</p>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--glass-border)]/50 pt-4">
                    <div className="flex flex-wrap items-center gap-2">
                      {selectedId != null && (
                        <>
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            onClick={() => useTemplateMutation.mutate(selectedId)}
                            disabled={useTemplateMutation.isPending}
                          >
                            <Wand2 className="mr-1.5 h-4 w-4" />
                            Вставить пример
                          </Button>
                          <Button
                            type="button"
                            variant="destructive"
                            size="sm"
                            onClick={() => setDeleteOpen(true)}
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 className="mr-1.5 h-4 w-4" />
                            Удалить
                          </Button>
                        </>
                      )}
                    </div>
                    <Button type="submit" disabled={saving}>
                      {saving ? 'Сохранение…' : 'Сохранить'}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Удалить шаблон?"
        description={
          selected
            ? `«/${selected.shortcut}» — ${selected.title} будет удалён без возможности восстановления.`
            : 'Шаблон будет удалён без возможности восстановления.'
        }
        confirmLabel="Удалить"
        variant="destructive"
        onConfirm={() => {
          if (selectedId != null) deleteMutation.mutate(selectedId)
        }}
      />
    </div>
  )
}
