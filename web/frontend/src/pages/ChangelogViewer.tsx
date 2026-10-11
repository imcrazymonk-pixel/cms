import { useState, useEffect } from 'react'
import { docsApi, DocEntry, UserName } from '@/api/docs'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { QueryError } from '@/components/QueryError'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import ChangelogEntryModal, { EntryFormData } from '@/components/changelog/ChangelogEntryModal'
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

export default function ChangelogViewer() {
  const [activeTab, setActiveTab] = useState('changelog')
  const [entries, setEntries] = useState<DocEntry[]>([])
  const [searchQ, setSearchQ] = useState('')
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Users for author dropdown
  const [users, setUsers] = useState<UserName[]>([])

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [editingEntry, setEditingEntry] = useState<DocEntry | null>(null)

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<DocEntry | null>(null)

  // ── Load entries ───────────────────────────────────────────
  const loadEntries = async () => {
    setIsPending(true)
    setError(null)
    try {
      const res = await docsApi.getEntries(activeTab)
      if (res.success) {
        setEntries(res.data.entries)
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
      toast.success('Запись добавлена')
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
  const filtered = entries.filter((e) => {
    if (!searchQ) return true
    const q = searchQ.toLowerCase()
    return (
      e.title.toLowerCase().includes(q) ||
      e.body.toLowerCase().includes(q) ||
      e.author.toLowerCase().includes(q) ||
      e.date.includes(q)
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
      const resp = await fetch(docsApi.getExportUrl(), {
        headers: bearer ? { Authorization: `Bearer ${bearer}` } : {},
      })
      if (!resp.ok) { toast.error('Ошибка экспорта'); return }
      const blob = await resp.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      const now = new Date()
      a.download = `CHANGELOG_CMS_${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}.md`
      a.click()
      URL.revokeObjectURL(a.href)
      toast.success('Файл экспортирован')
    } catch {
      toast.error('Ошибка экспорта')
    }
  }

  const isEditable = activeTab === 'changelog'

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Ченжлог</h1>
          <p className="text-sm text-muted-foreground">
            Просмотр и редактирование ленты изменений CMS
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={loadEntries} aria-label="Refresh">
            <RefreshCw className="w-5 h-5 text-dark-200" />
          </Button>
          {isEditable && (
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
                    const file = (e.target as HTMLInputElement).files?.[0]
                    if (!file) return
                    ;(async () => {
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
                        setImporting(false);
                        (e.target as HTMLInputElement).value = ''
                      }
                    })()
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
              placeholder="Поиск по записям…"
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

        {/* Empty state */}
        {!isPending && !error && entries.length === 0 && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <ScrollText className="w-12 h-12 text-dark-300 mb-4" />
              <h3 className="text-lg font-semibold text-white">Нет записей</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {isEditable
                  ? 'Нажмите «Новая запись», чтобы добавить первую запись в ченжлог.'
                  : 'Техническая история пока пуста.'}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Tab: Changelog entries */}
        <TabsContent value="changelog">
          {!isPending && !error && renderEntries(filtered, openEditModal, setDeleteTarget, formatEntryDate, bodyPreview)}
        </TabsContent>

        {/* Tab: History (read-only, rendered as HTML) */}
        <TabsContent value="history">
          {!isPending && !error && renderHistoryView(filtered, searchQ)}
        </TabsContent>
      </Tabs>

      {/* Create/Edit Modal */}
      {showModal && (
        <ChangelogEntryModal
          mode={editingEntry ? 'edit' : 'create'}
          entry={editingEntry ?? undefined}
          users={users}
          onSave={handleSave}
          onClose={() => {
            setShowModal(false)
            setEditingEntry(null)
          }}
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

function renderHistoryView(
  filtered: DocEntry[],
  searchQ: string,
) {
  return (
    <div className="space-y-3">
      {filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <ScrollText className="w-12 h-12 text-dark-300 mb-4" />
            <h3 className="text-lg font-semibold text-white">
              {searchQ ? 'Ничего не найдено' : 'Нет записей'}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              {searchQ ? 'Попробуйте другой запрос' : 'Техническая история пока пуста.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <ScrollArea className="h-[calc(100dvh-16rem)]">
          <div className="prose max-w-none text-sm text-dark-200 leading-relaxed space-y-2">
            {filtered.map((entry) => (
              <div
                key={entry.id}
                className="glass-card rounded-lg border border-[var(--glass-border)] px-4 py-3"
              >
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{entry.date}</span>
                  <span className="opacity-40">·</span>
                  <span>{entry.time}</span>
                  <span className="opacity-40">·</span>
                  <span>{entry.author}</span>
                </div>
                <h4 className="text-sm font-semibold text-white">{entry.title}</h4>
                {entry.body && (
                  <pre className="mt-1 text-xs text-dark-200 whitespace-pre-wrap font-mono leading-relaxed max-h-32 overflow-y-auto">
                    {entry.body}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}