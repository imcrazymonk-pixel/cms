import { useState, useEffect } from 'react'
import { docsApi, DocEntry, DocSection, DocumentPayload, UserName } from '@/api/docs'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import ChangelogEntryModal, { EntryFormData } from '@/components/changelog/ChangelogEntryModal'
import HistoryDocumentEditor from '@/components/changelog/HistoryDocumentEditor'
import { cn } from '@/lib/utils'
import {
  ScrollText,
  Search,
  X,
  Pencil,
  Trash2,
  Plus,
  RefreshCw,
  Clock,
  BookOpenText,
  ChevronDown,
  Upload,
  FileDown,
  Loader2,
} from 'lucide-react'
import { toast } from 'sonner'

/** Return the first N lines of a body as a preview. */
function bodyPreview(body: string, maxLines = 5): string {
  if (!body) return ''
  const lines = body.split('\n').filter(Boolean)
  const preview = lines.slice(0, maxLines).join('\n')
  if (lines.length > maxLines) {
    return preview + '\n…'
  }
  return preview
}

/** Strip tags so search matches visible text, not class names. */
function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, ' ')
}

/**
 * The backend renders each section *including* its own heading, while the
 * card already shows that heading. Drop the leading heading to avoid a
 * duplicated title.
 */
function stripLeadingHeading(html: string): string {
  return html.replace(/^\s*<h([1-4])[^>]*>[\s\S]*?<\/h\1>\s*/i, '')
}

/** Parse a date like "15.09.2026" into a readable format. */
function formatEntryDate(dateStr: string): string {
  if (!dateStr) return ''
  const parts = dateStr.split('.')
  if (parts.length !== 3) return dateStr
  const months = [
    'янв', 'фев', 'мар', 'апр', 'мая', 'июн',
    'июл', 'авг', 'сен', 'окт', 'ноя', 'дек',
  ]
  const monthIdx = parseInt(parts[1]) - 1
  const month = monthIdx >= 0 && monthIdx < 12 ? months[monthIdx] : parts[1]
  return `${parts[0]} ${month} ${parts[2]}`
}

function formatStamp(updatedAt: string | null): string {
  if (!updatedAt) return ''
  const d = new Date(updatedAt)
  if (Number.isNaN(d.getTime())) return updatedAt
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function ChangelogViewer() {
  const [activeTab, setActiveTab] = useState('changelog')
  const [entries, setEntries] = useState<DocEntry[]>([])
  const [editable, setEditable] = useState(false)
  const [historyDoc, setHistoryDoc] = useState<DocumentPayload | null>(null)
  const [historySections, setHistorySections] = useState<DocSection[]>([])
  const [searchQ, setSearchQ] = useState('')
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Users for author dropdown
  const [users, setUsers] = useState<UserName[]>([])

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [editingEntry, setEditingEntry] = useState<DocEntry | null>(null)
  const [showDocEditor, setShowDocEditor] = useState(false)

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<DocEntry | null>(null)

  const isHistory = activeTab === 'history'

  // ── Load entries ───────────────────────────────────────────
  const loadEntries = async () => {
    setIsPending(true)
    setError(null)
    try {
      const res = await docsApi.getEntries(activeTab)
      if (res.success) {
        setEntries(res.data.entries)
        setEditable(res.data.editable)
        setHistoryDoc(res.data.document ?? null)
        setHistorySections(res.data.sections ?? res.data.document?.sections ?? [])
      } else {
        setError('Не удалось загрузить записи')
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки')
    } finally {
      setIsPending(false)
    }
  }

  // ── Load users once ───────────────────────────────────────
  const loadUsers = async () => {
    try {
      const res = await docsApi.getUserNames()
      if (res.success) {
        setUsers(res.data)
      }
    } catch {
      // silently fail — user can type author manually
    }
  }

  useEffect(() => {
    loadEntries()
    if (users.length === 0) loadUsers()
  }, [activeTab])

  // ── Modal handlers ────────────────────────────────────────
  const openCreateModal = () => {
    setEditingEntry(null)
    setShowModal(true)
  }

  const openEditModal = (entry: DocEntry) => {
    setEditingEntry(entry)
    setShowModal(true)
  }

  const handleSave = async (data: EntryFormData) => {
    if (editingEntry) {
      // Update existing
      const res = await docsApi.updateEntry(activeTab, editingEntry.id, {
        date: data.date,
        time: data.time,
        author: data.author,
        title: data.title,
        body: data.body,
      })
      if (!res.success) throw new Error('Ошибка обновления')
      toast.success('Запись обновлена')
    } else {
      // Create new
      const res = await docsApi.createEntry(activeTab, {
        date: data.date,
        time: data.time,
        author: data.author,
        title: data.title,
        body: data.body,
        also_history: data.also_history,
      })
      if (!res.success) throw new Error('Ошибка создания')
      toast.success(isHistory ? 'Блок добавлен' : 'Запись добавлена')
    }
    await loadEntries()
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      const res = await docsApi.deleteEntry(activeTab, deleteTarget.id)
      if (!res.success) throw new Error('Ошибка удаления')
      toast.success('Запись удалена')
      setDeleteTarget(null)
      await loadEntries()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Ошибка удаления')
    }
  }

  // ── Entry list filtering ──────────────────────────────────
  const searchNeedle = searchQ.trim().toLowerCase()

  const filtered = entries.filter((e) => {
    if (!searchNeedle) return true
    return (
      e.title.toLowerCase().includes(searchNeedle) ||
      e.body.toLowerCase().includes(searchNeedle) ||
      (e.body_html ?? '').toLowerCase().includes(searchNeedle) ||
      e.author.toLowerCase().includes(searchNeedle) ||
      e.date.includes(searchNeedle)
    )
  })

  // ── History sections filtering ────────────────────────────
  const filteredSections = historySections.filter((section) => {
    if (!searchNeedle) return true
    return (
      section.title.toLowerCase().includes(searchNeedle) ||
      stripHtml(section.html).toLowerCase().includes(searchNeedle)
    )
  })

  // ── Import / Export ───────────────────────────────────────
  const [importing, setImporting] = useState(false)

  const handleExport = async () => {
    try {
      const token = localStorage.getItem('auth-store')
      let bearer = ''
      if (token) {
        try {
          const parsed = JSON.parse(token)
          bearer = parsed.state?.token || ''
        } catch { /* ignore */ }
      }
      const resp = await fetch(docsApi.getExportUrl(activeTab), {
        headers: bearer ? { Authorization: `Bearer ${bearer}` } : {},
      })
      if (!resp.ok) { toast.error('Ошибка экспорта'); return }
      const blob = await resp.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      const now = new Date()
      const base = isHistory ? 'HISTORY_TECHNICAL' : 'CHANGELOG_CMS'
      const stamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
      a.download = `${base}_${stamp}.md`
      a.click()
      URL.revokeObjectURL(a.href)
      toast.success('Файл экспортирован')
    } catch {
      toast.error('Ошибка экспорта')
    }
  }

  const handleChangelogImport = async (file: File) => {
    setImporting(true)
    try {
      const res = await docsApi.importFile(file)
      if (res.success) {
        toast.success(`Импортировано ${res.data.imported} записей`)
        await loadEntries()
      } else {
        toast.error('Ошибка импорта')
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Ошибка импорта')
    } finally {
      setImporting(false)
    }
  }

  const handleHistoryImport = async (file: File) => {
    const confirmed = window.confirm(
      'Импорт перезапишет текст документа технической истории. Блоки «Дополнения» останутся без изменений. Продолжить?',
    )
    if (!confirmed) return
    setImporting(true)
    try {
      const res = await docsApi.importDocument('history', file)
      if (res.success) {
        toast.success(`Документ импортирован (${res.data.chars.toLocaleString('ru-RU')} символов)`)
        await loadEntries()
      } else {
        toast.error('Ошибка импорта')
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Ошибка импорта')
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Ченжлог</h1>
          <p className="text-sm text-muted-foreground">
            {isHistory
              ? 'Техническая история проекта и дополнения из ленты изменений'
              : 'Просмотр и редактирование ленты изменений CMS'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={loadEntries} aria-label="Refresh">
            <RefreshCw className="w-5 h-5 text-dark-200" />
          </Button>

          {editable && !isHistory && (
            <>
              <label className="relative cursor-pointer">
                <Button variant="outline" size="sm" disabled={importing} onClick={() => {}}>
                  {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4 mr-1.5" />}
                  Импорт .md
                </Button>
                <input
                  type="file"
                  accept=".md,.txt"
                  className="absolute inset-0 opacity-0 w-full h-full cursor-pointer"
                  onChange={(e) => {
                    const input = e.target
                    const file = input.files?.[0]
                    if (!file) return
                    void handleChangelogImport(file).finally(() => { input.value = '' })
                  }}
                />
              </label>
              <Button variant="outline" size="sm" onClick={handleExport}>
                <FileDown className="w-4 h-4 mr-1.5" />
                Экспорт .md
              </Button>
              <Button variant="default" onClick={openCreateModal}>
                <Plus className="w-4 h-4 mr-1.5" />
                Новая запись
              </Button>
            </>
          )}

          {editable && isHistory && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDocEditor(true)}
                disabled={!historyDoc}
              >
                <Pencil className="w-4 h-4 mr-1.5" />
                Редактировать документ
              </Button>
              <label className="relative cursor-pointer">
                <Button variant="outline" size="sm" disabled={importing} onClick={() => {}}>
                  {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4 mr-1.5" />}
                  Импорт .md
                </Button>
                <input
                  type="file"
                  accept=".md"
                  className="absolute inset-0 opacity-0 w-full h-full cursor-pointer"
                  onChange={(e) => {
                    const input = e.target
                    const file = input.files?.[0]
                    if (!file) return
                    void handleHistoryImport(file).finally(() => { input.value = '' })
                  }}
                />
              </label>
              <Button variant="outline" size="sm" onClick={handleExport}>
                <FileDown className="w-4 h-4 mr-1.5" />
                Экспорт .md
              </Button>
              <Button variant="default" onClick={openCreateModal}>
                <Plus className="w-4 h-4 mr-1.5" />
                Новая запись
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between">
          <TabsList className="w-auto">
            <TabsTrigger value="changelog">
              <ScrollText className="w-4 h-4 mr-1.5" />
              Лента изменений
            </TabsTrigger>
            <TabsTrigger value="history">
              <BookOpenText className="w-4 h-4 mr-1.5" />
              Техническая история
            </TabsTrigger>
          </TabsList>

          {/* Search */}
          <div className="relative w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-300" />
            <Input
              type="text"
              placeholder={isHistory ? 'Поиск по дополнениям…' : 'Поиск по записям…'}
              className="pl-8"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
            />
            {searchQ && (
              <button
                onClick={() => setSearchQ('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-300 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Loading state */}
        {isPending && (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardContent>
                  <Skeleton className="h-5 w-3/4 mb-2" />
                  <Skeleton className="h-20 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Error state */}
        {!isPending && error && (
          <QueryError message={error} onRetry={loadEntries} />
        )}

        {/* Empty state (changelog only — history always has a document) */}
        {!isPending && !error && !isHistory && entries.length === 0 && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <ScrollText className="w-12 h-12 text-dark-300 mb-4" />
              <h3 className="text-lg font-semibold text-white">Нет записей</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Нажмите «Новая запись», чтобы добавить первую запись в ченжлог.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Tab: Changelog entries */}
        <TabsContent value="changelog">
          {!isPending && !error && renderEntries(filtered, openEditModal, setDeleteTarget, formatEntryDate, bodyPreview)}
        </TabsContent>

        {/* Tab: History document + append-blocks */}
        <TabsContent value="history">
          {!isPending && !error && renderHistoryView({
            document: historyDoc,
            sections: filteredSections,
            hasSections: historySections.length > 0,
            entries: filtered,
            searchQ,
            openEditModal,
            setDeleteTarget,
            formatEntryDate,
          })}
        </TabsContent>
      </Tabs>

      {/* Create/Edit Modal */}
      {showModal && (
        <ChangelogEntryModal
          mode={editingEntry ? 'edit' : 'create'}
          entry={editingEntry ?? undefined}
          users={users}
          docName={isHistory ? 'history' : 'changelog'}
          onSave={handleSave}
          onClose={() => {
            setShowModal(false)
            setEditingEntry(null)
          }}
        />
      )}

      {/* History document editor */}
      {showDocEditor && historyDoc && (
        <HistoryDocumentEditor
          open={showDocEditor}
          onOpenChange={setShowDocEditor}
          initialRaw={historyDoc.raw}
          updatedAt={historyDoc.updated_at}
          onSaved={() => loadEntries()}
        />
      )}

      {/* Delete confirmation */}
      {deleteTarget && (
        <ConfirmDialog
          open={!!deleteTarget}
          onOpenChange={(v) => { if (!v) setDeleteTarget(null) }}
          title="Удалить запись"
          description={`Вы уверены, что хотите удалить запись «${deleteTarget.title}»?`}
          confirmLabel="Удалить"
          variant="destructive"
          onConfirm={handleDelete}
        />
      )}
    </div>
  )
}

// ── Render helpers ───────────────────────────────────────────
function renderEntries(
  entries: DocEntry[],
  openEditModal: (entry: DocEntry) => void,
  setDeleteTarget: (entry: DocEntry | null) => void,
  formatEntryDate: (d: string) => string,
  bodyPreview: (b: string, m?: number) => string,
) {
  return (
    <div className="space-y-3">
      {entries.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <ScrollText className="w-12 h-12 text-dark-300 mb-4" />
            <h3 className="text-lg font-semibold text-white">Нет записей</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Нажмите «Новая запись», чтобы добавить первую запись в ченжлог.
            </p>
          </CardContent>
        </Card>
      ) : (
        entries.map((entry) => {
          const preview = bodyPreview(entry.body, 6)
          return (
            <Card
              key={entry.id}
              className="cursor-pointer hover:border-[var(--glass-border-hover)] transition-colors"
              onClick={() => openEditModal(entry)}
            >
              <CardContent>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    {/* Meta line */}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{formatEntryDate(entry.date)}</span>
                      <span className="opacity-40">·</span>
                      <span>{entry.time}</span>
                      <span className="opacity-40">·</span>
                      <span>{entry.author}</span>
                    </div>

                    {/* Title */}
                    <h3 className="text-base font-semibold text-white leading-snug">
                      {entry.title}
                    </h3>

                    {/* Preview */}
                    {preview && (
                      <div className="mt-1 text-sm text-dark-200 whitespace-pre-line line-clamp-5">
                        {preview}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-dark-200 hover:text-primary-400"
                      onClick={(e) => { e.stopPropagation(); openEditModal(entry) }}
                      aria-label="Edit"
                    >
                      <Pencil className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-dark-200 hover:text-red-400"
                      onClick={(e) => { e.stopPropagation(); setDeleteTarget(entry) }}
                      aria-label="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })
      )}
    </div>
  )
}

interface HistoryViewProps {
  document: DocumentPayload | null
  /** Sections after search filtering. */
  sections: DocSection[]
  /** Whether the document produced any sections at all (before filtering). */
  hasSections: boolean
  entries: DocEntry[]
  searchQ: string
  openEditModal: (entry: DocEntry) => void
  setDeleteTarget: (entry: DocEntry | null) => void
  formatEntryDate: (d: string) => string
}

function renderHistoryView({
  document,
  sections,
  hasSections,
  entries,
  searchQ,
  openEditModal,
  setDeleteTarget,
  formatEntryDate,
}: HistoryViewProps) {
  return (
    <ScrollArea className="h-[calc(100dvh-18rem)]">
      <div className="space-y-4 pr-3">
        {/* Meta line */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>
            Документ технической истории
            {hasSections && ` · секций: ${sections.length}`}
          </span>
          {document?.updated_at && (
            <span>обновлён {formatStamp(document.updated_at)}</span>
          )}
        </div>

        {searchQ && (
          <p className="text-xs text-muted-foreground">
            Найдено: секций — {sections.length}, блоков — {entries.length}
          </p>
        )}

        {/* Base document split into collapsible sections */}
        {hasSections ? (
          sections.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-sm text-muted-foreground">
                Ничего не найдено по запросу
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {sections.map((section, index) => (
                <HistorySectionCard
                  key={`${index}-${section.title}`}
                  section={section}
                  defaultOpen={index === 0}
                  forceOpen={!!searchQ}
                />
              ))}
            </div>
          )
        ) : document ? (
          // Fallback for old responses / documents without H2 sections.
          <Card>
            <CardContent>
              <div
                className={cn(!document.html.includes('prose') && 'prose')}
                dangerouslySetInnerHTML={{ __html: document.html }}
              />
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              Документ технической истории недоступен.
            </CardContent>
          </Card>
        )}

        {/* Append-blocks */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-white uppercase tracking-wide">Дополнения</h3>

          {entries.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-sm text-muted-foreground">
                {searchQ
                  ? 'Ничего не найдено по запросу'
                  : 'Дополнений пока нет. Нажмите «Новая запись», чтобы добавить блок.'}
              </CardContent>
            </Card>
          ) : (
            entries.map((entry) => (
              <HistoryEntryCard
                key={entry.id}
                entry={entry}
                defaultOpen
                forceOpen={!!searchQ}
                onEdit={() => openEditModal(entry)}
                onDelete={() => setDeleteTarget(entry)}
                formatEntryDate={formatEntryDate}
              />
            ))
          )}
        </div>
      </div>
    </ScrollArea>
  )
}

// ── History section card ─────────────────────────────────────
interface HistorySectionCardProps {
  section: DocSection
  defaultOpen: boolean
  /** Search hits stay expanded so matches are visible without extra clicks. */
  forceOpen: boolean
}

function HistorySectionCard({ section, defaultOpen, forceOpen }: HistorySectionCardProps) {
  const [open, setOpen] = useState(defaultOpen)
  const expanded = forceOpen || open

  return (
    <Card>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={expanded}
        className={cn(
          'flex w-full items-start gap-2 rounded-2xl px-4 py-3 text-left transition-colors md:px-6',
          'hover:bg-[var(--surface-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50',
        )}
      >
        <ChevronDown
          className={cn(
            'mt-0.5 w-4 h-4 shrink-0 text-dark-300 transition-transform',
            expanded && 'rotate-180',
          )}
        />
        <span className="flex-1 min-w-0 break-words text-sm font-semibold text-white">
          {section.title}
        </span>
        <span className="shrink-0 pt-0.5 text-[11px] uppercase tracking-wide text-dark-300">
          H{section.level}
        </span>
      </button>

      {expanded && (
        <CardContent className="pt-0">
          <div
            className="prose"
            dangerouslySetInnerHTML={{ __html: stripLeadingHeading(section.html) }}
          />
        </CardContent>
      )}
    </Card>
  )
}

// ── History append-block card ────────────────────────────────
interface HistoryEntryCardProps {
  entry: DocEntry
  defaultOpen: boolean
  forceOpen: boolean
  onEdit: () => void
  onDelete: () => void
  formatEntryDate: (d: string) => string
}

function HistoryEntryCard({
  entry,
  defaultOpen,
  forceOpen,
  onEdit,
  onDelete,
  formatEntryDate,
}: HistoryEntryCardProps) {
  const [open, setOpen] = useState(defaultOpen)
  const expanded = forceOpen || open
  const hasBody = Boolean(entry.body_html?.trim() || entry.body?.trim())

  return (
    <Card>
      <div className="flex items-start gap-2 px-4 py-3 md:px-6">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={expanded}
          className="flex flex-1 min-w-0 items-start gap-2 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg"
        >
          <ChevronDown
            className={cn(
              'mt-1 w-4 h-4 shrink-0 text-dark-300 transition-transform',
              expanded && 'rotate-180',
            )}
          />
          <span className="flex-1 min-w-0">
            <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Clock className="w-3.5 h-3.5" />
              <span>{formatEntryDate(entry.date)}</span>
              <span className="opacity-40">·</span>
              <span>{entry.time}</span>
              <span className="opacity-40">·</span>
              <span>{entry.author}</span>
              {entry.origin === 'changelog' && (
                <>
                  <span className="opacity-40">·</span>
                  <span className="text-primary-400/80">из ленты изменений</span>
                </>
              )}
            </span>
            <span className="mt-1 block text-base font-semibold leading-snug text-white break-words">
              {entry.title}
            </span>
          </span>
        </button>

        <div className="flex items-center gap-1.5 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-dark-200 hover:text-primary-400"
            onClick={onEdit}
            aria-label="Edit"
          >
            <Pencil className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-dark-200 hover:text-red-400"
            onClick={onDelete}
            aria-label="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {expanded && hasBody && (
        <CardContent className="pt-0">
          {entry.body_html ? (
            <div className="prose" dangerouslySetInnerHTML={{ __html: entry.body_html }} />
          ) : (
            <div className="prose">
              <p className="whitespace-pre-line">{entry.body}</p>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}

