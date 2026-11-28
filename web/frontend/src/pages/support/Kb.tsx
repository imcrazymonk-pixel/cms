import { useCallback, useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Lightbulb, Plus, RefreshCw, Search, Upload, X } from 'lucide-react'
import { toast } from 'sonner'
import {
  getSupportErrorCode,
  getSupportErrorMessage,
  supportApi,
  type SupportKbCandidate,
  type SupportKbDoc,
  type SupportKbListResult,
} from '@/api/support'
import { toastMutationError } from '@/lib/mutationToast'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState } from '@/components/EmptyState'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { KbList } from '@/components/kb/KbList'
import { KbEditor, type KbEditorValues } from '@/components/kb/KbEditor'
import { CandidateList } from '@/components/kb/CandidateList'
import { ImportPanel } from '@/components/kb/ImportPanel'

type Tab = 'published' | 'drafts' | 'ideas'

const SEARCH_DEBOUNCE_MS = 300

/**
 * База знаний саппорта (`/support/kb`).
 *
 * Две колонки: слева табы/поиск/список (статьи, черновики, идеи), справа —
 * редактор выбранной статьи. Правка идёт с `expected_version`; конфликт
 * версий поднимает диалог перезагрузки, удаление опубликованной статьи
 * подсказывает сначала отправить её в архив.
 */
export default function SupportKbPage() {
  const queryClient = useQueryClient()

  const [tab, setTab] = useState<Tab>('published')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [conflictOpen, setConflictOpen] = useState(false)

  // Поиск с debounce 300 мс.
  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput.trim()), SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  const listStatus: 'published' | 'draft' = tab === 'drafts' ? 'draft' : 'published'

  const docsQuery = useQuery({
    queryKey: ['support', 'kb', 'list', listStatus, search],
    queryFn: () =>
      supportApi.listKb({
        status: listStatus,
        q: search || undefined,
        page: 1,
        per_page: 100,
      }),
    enabled: tab !== 'ideas',
  })

  const candidatesQuery = useQuery({
    queryKey: ['support', 'kb', 'candidates', 'new'],
    queryFn: () => supportApi.listCandidates({ status: 'new', page: 1, per_page: 100 }),
    enabled: tab === 'ideas',
  })

  const docQuery = useQuery({
    queryKey: ['support', 'kb', 'doc', selectedId],
    queryFn: () => supportApi.getKb(selectedId as number),
    enabled: selectedId != null && tab !== 'ideas',
  })

  const doc: SupportKbDoc | undefined = docQuery.data?.doc

  // Автовыбор первой статьи, когда ничего не выбрано. Выбранную статью не
  // сбрасываем, если она выпала из списка (например, после архивации) — так
  // остаётся доступной кнопка «Восстановить».
  useEffect(() => {
    if (tab === 'ideas') return
    const items = docsQuery.data?.items
    if (!items || items.length === 0) return
    if (selectedId === null) setSelectedId(items[0].id)
  }, [tab, docsQuery.data, selectedId])

  const invalidateKb = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['support', 'kb'] })
  }, [queryClient])

  const handleKbError = useCallback((err: unknown, fallback: string) => {
    const code = getSupportErrorCode(err)
    if (code === 'KB_VERSION_CONFLICT') {
      setConflictOpen(true)
      return
    }
    if (code === 'KB_DOC_PUBLISHED') {
      toast.error('Статья опубликована — сначала переведите её в архив')
      return
    }
    const message = getSupportErrorMessage(err)
    if (message) {
      toast.error(message, { duration: 8000 })
      return
    }
    toastMutationError(err, fallback)
  }, [])

  // ── Мутации статьи ──────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: () =>
      supportApi.createKb({ title: 'Новая статья', body: '# Новая статья\n\n' }),
    onSuccess: (data) => {
      toast.success('Черновик создан')
      invalidateKb()
      setTab('drafts')
      setSelectedId(data.id)
    },
    onError: (err) => handleKbError(err, 'Не удалось создать статью'),
  })

  const saveMutation = useMutation({
    mutationFn: (values: KbEditorValues) => {
      if (selectedId == null || !doc) {
        throw new Error('Статья ещё не загружена')
      }
      return supportApi.updateKb(selectedId, {
        title: values.title,
        body: values.body,
        tags: values.tags,
        expected_version: doc.version,
      })
    },
    onSuccess: (data) => {
      toast.success('Статья сохранена')
      queryClient.setQueryData<{ doc: SupportKbDoc }>(
        ['support', 'kb', 'doc', data.id],
        (prev) => (prev ? { doc: { ...prev.doc, ...data } } : prev),
      )
      invalidateKb()
    },
    onError: (err) => handleKbError(err, 'Не удалось сохранить статью'),
  })

  const publishMutation = useMutation({
    mutationFn: () => {
      if (selectedId == null || !doc) throw new Error('Статья ещё не загружена')
      return supportApi.publishKb(selectedId, doc.version)
    },
    onSuccess: () => {
      toast.success('Статья опубликована')
      invalidateKb()
    },
    onError: (err) => handleKbError(err, 'Не удалось опубликовать статью'),
  })

  const archiveMutation = useMutation({
    mutationFn: () => {
      if (selectedId == null) throw new Error('Статья ещё не выбрана')
      return supportApi.archiveKb(selectedId)
    },
    onSuccess: () => {
      toast.success('Статья отправлена в архив')
      invalidateKb()
    },
    onError: (err) => handleKbError(err, 'Не удалось отправить статью в архив'),
  })

  const restoreMutation = useMutation({
    mutationFn: () => {
      if (selectedId == null) throw new Error('Статья ещё не выбрана')
      return supportApi.restoreKb(selectedId)
    },
    onSuccess: () => {
      toast.success('Статья восстановлена как черновик')
      invalidateKb()
      setTab('drafts')
    },
    onError: (err) => handleKbError(err, 'Не удалось восстановить статью'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => supportApi.deleteKb(id),
    onSuccess: (_data, id) => {
      toast.success('Статья удалена')
      setDeleteOpen(false)
      // Убираем статью из кэша списка сразу, чтобы автовыбор не вернул её.
      queryClient.setQueriesData<SupportKbListResult>(
        { queryKey: ['support', 'kb', 'list'] },
        (prev) =>
          prev
            ? {
                ...prev,
                items: prev.items.filter((item) => item.id !== id),
                total: Math.max(0, prev.total - 1),
              }
            : prev,
      )
      setSelectedId(null)
      invalidateKb()
    },
    onError: (err) => {
      setDeleteOpen(false)
      handleKbError(err, 'Не удалось удалить статью')
    },
  })

  // ── Мутации идей ────────────────────────────────────────────────────

  const acceptMutation = useMutation({
    mutationFn: (id: number) => supportApi.decideCandidate(id, { decision: 'accept' }),
    onSuccess: (data) => {
      toast.success('Черновик создан из идеи')
      invalidateKb()
      if (data.doc_id != null) {
        setTab('drafts')
        setSelectedId(data.doc_id)
      }
    },
    onError: (err) => handleKbError(err, 'Не удалось принять идею'),
  })

  const rejectMutation = useMutation({
    mutationFn: (id: number) => supportApi.decideCandidate(id, { decision: 'reject' }),
    onSuccess: () => {
      toast.success('Идея отклонена')
      invalidateKb()
    },
    onError: (err) => handleKbError(err, 'Не удалось отклонить идею'),
  })

  const pendingCandidateId =
    acceptMutation.isPending
      ? acceptMutation.variables ?? null
      : rejectMutation.isPending
        ? rejectMutation.variables ?? null
        : null

  // ── Обработчики ─────────────────────────────────────────────────────

  const handleRefresh = () => {
    if (tab === 'ideas') {
      void candidatesQuery.refetch()
      return
    }
    void docsQuery.refetch()
    if (selectedId != null) void docQuery.refetch()
  }

  const handleTabChange = (value: string) => {
    setTab(value as Tab)
    setSelectedId(null)
  }

  const handleAcceptCandidate = (candidate: SupportKbCandidate) => acceptMutation.mutate(candidate.id)
  const handleRejectCandidate = (candidate: SupportKbCandidate) => rejectMutation.mutate(candidate.id)

  const handleReloadAfterConflict = () => {
    setConflictOpen(false)
    invalidateKb()
    if (selectedId != null) void docQuery.refetch()
  }

  const listLoading = tab === 'ideas' ? candidatesQuery.isLoading : docsQuery.isLoading

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">База знаний</h1>
          <p className="mt-1 text-sm text-dark-200">
            Статьи для операторов и ИИ ·{' '}
            {tab === 'ideas'
              ? candidatesQuery.isLoading
                ? '…'
                : `${candidatesQuery.data?.total ?? 0} идей`
              : docsQuery.isLoading
                ? '…'
                : `${docsQuery.data?.total ?? 0} статей`}
          </p>
        </div>
        <div className="page-header-actions flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            size="icon"
            onClick={handleRefresh}
            disabled={listLoading}
            aria-label="Обновить"
          >
            <RefreshCw className={cn('h-5 w-5', listLoading && 'animate-spin')} />
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setImportOpen(true)}>
            <Upload className="mr-1.5 h-4 w-4" />
            Импорт
          </Button>
          <Button
            size="sm"
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
          >
            <Plus className="mr-1.5 h-4 w-4" />
            Новая статья
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        {/* Левая колонка */}
        <div className="space-y-3">
          <div className="glass-card space-y-3 p-3">
            <Tabs value={tab} onValueChange={handleTabChange}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="published">Статьи</TabsTrigger>
                <TabsTrigger value="drafts">Черновики</TabsTrigger>
                <TabsTrigger value="ideas">Идеи</TabsTrigger>
              </TabsList>
            </Tabs>

            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dark-300" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder={tab === 'ideas' ? 'Поиск недоступен для идей' : 'Поиск по статьям…'}
                disabled={tab === 'ideas'}
                className="h-10 w-full rounded-lg border border-[var(--glass-border)] bg-[var(--glass-bg)] pl-10 pr-8 text-sm text-white placeholder:text-dark-300 focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:cursor-not-allowed disabled:opacity-50"
              />
              {searchInput && tab !== 'ideas' && (
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
          </div>

          {tab === 'ideas' ? (
            <CandidateList
              items={candidatesQuery.data?.items ?? []}
              total={candidatesQuery.data?.total ?? 0}
              isLoading={candidatesQuery.isLoading}
              pendingId={pendingCandidateId}
              onAccept={handleAcceptCandidate}
              onReject={handleRejectCandidate}
            />
          ) : (
            <KbList
              items={docsQuery.data?.items ?? []}
              total={docsQuery.data?.total ?? 0}
              activeId={selectedId}
              isLoading={docsQuery.isLoading}
              emptyTitle={tab === 'drafts' ? 'Черновиков нет' : 'Статей нет'}
              emptyDescription={
                tab === 'drafts'
                  ? 'Черновики появляются после создания статьи или принятия идеи'
                  : 'Опубликуйте статью, чтобы она стала доступна поиску и ИИ'
              }
              onSelect={setSelectedId}
            />
          )}
        </div>

        {/* Правая колонка */}
        <div className="min-w-0">
          {tab === 'ideas' ? (
            <div className="glass-card">
              <EmptyState
                icon={Lightbulb}
                size="lg"
                title="Идеи статей"
                description="Примите идею — она превратится в черновик, который откроется в редакторе"
              />
            </div>
          ) : docQuery.isLoading ? (
            <div className="glass-card space-y-4 p-4 md:p-5">
              <Skeleton className="h-8 w-1/3" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-80 w-full" />
            </div>
          ) : (
            <KbEditor
              doc={doc}
              isLoading={false}
              saving={saveMutation.isPending}
              publishing={publishMutation.isPending}
              archiving={archiveMutation.isPending}
              restoring={restoreMutation.isPending}
              deleting={deleteMutation.isPending}
              onSave={(values) => saveMutation.mutate(values)}
              onPublish={() => publishMutation.mutate()}
              onArchive={() => archiveMutation.mutate()}
              onRestore={() => restoreMutation.mutate()}
              onDelete={() => setDeleteOpen(true)}
            />
          )}
        </div>
      </div>

      <ImportPanel open={importOpen} onOpenChange={setImportOpen} onFinished={invalidateKb} />

      <ConfirmDialog
        open={conflictOpen}
        onOpenChange={setConflictOpen}
        title="Статья изменена, перезагрузить?"
        description={
          doc
            ? `Кто-то сохранил версию ${doc.version} раньше вас. Перезагрузите статью, чтобы не потерять чужие правки.`
            : 'Кто-то сохранил статью раньше вас. Перезагрузите её, чтобы не потерять чужие правки.'
        }
        confirmLabel="Перезагрузить"
        cancelLabel="Остаться"
        onConfirm={handleReloadAfterConflict}
      />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Удалить статью?"
        description={
          doc ? `«${doc.title}» будет удалена без возможности восстановления.` : undefined
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
