import { useRef, useState, useEffect, type ChangeEvent } from 'react'
import { mediaApi, MediaItem } from '../api/media'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table'
import { QueryError } from '@/components/QueryError'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Image, Trash2, RefreshCw, Upload, ExternalLink } from 'lucide-react'

function formatSize(bytes: number): string {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

function formatDate(ts: number): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function MediaList() {
  const [data, setData] = useState<MediaItem[]>([])
  const [isPending, setIsPending] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [deletePath, setDeletePath] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const load = async () => {
    setIsPending(true); setError(null)
    try {
      const res = await mediaApi.list() as { success: boolean; data: MediaItem[] }
      if (res.success) setData(res.data)
      else setError('Не удалось загрузить медиафайлы')
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Ошибка') }
    finally { setIsPending(false) }
  }

  useEffect(() => { load() }, [])

  const onPickFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      await mediaApi.upload(fd)
      load()
    } catch { /* ignore */ }
    finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const doDelete = async () => {
    if (!deletePath) return
    try {
      await mediaApi.delete(deletePath)
      setDeletePath(null)
      load()
    } catch { /* ignore */ }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Медиафайлы</h1>
          <p className="text-sm text-dark-200 mt-1">Управление загруженными изображениями</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw className="w-4 h-4" /> Обновить</Button>
          <Button variant="default" size="sm" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            <Upload className="w-4 h-4" /> {uploading ? 'Загрузка…' : 'Загрузить'}
          </Button>
          <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={onPickFile} />
        </div>
      </div>

      {isPending && (
        <div className="space-y-2">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-12 rounded-lg" />)}
        </div>
      )}
      {error && <QueryError message={error} />}

      {!isPending && !error && (
        data.length === 0 ? (
          <Card className="rounded-xl"><CardContent className="p-10 text-center">
            <Image className="w-10 h-10 text-dark-300 mx-auto mb-3" />
            <p className="text-base font-semibold mb-2">Медиафайлов пока нет</p>
            <p className="text-sm text-dark-300 mb-3">Загрузите изображения кнопкой «Загрузить»</p>
          </CardContent></Card>
        ) : (
          <Card className="rounded-xl">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">Превью</TableHead>
                  <TableHead>Имя файла</TableHead>
                  <TableHead className="w-32">Размер</TableHead>
                  <TableHead className="w-48">Дата изменения</TableHead>
                  <TableHead className="w-28">Действия</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((file) => (
                  <TableRow key={file.path}>
                    <TableCell>
                      <img
                        src={file.url}
                        alt={file.name}
                        className="w-12 h-12 object-cover rounded-md border border-[var(--glass-border)] cursor-pointer"
                        onClick={() => window.open(file.url, '_blank')}
                      />
                    </TableCell>
                    <TableCell className="text-sm text-dark-100">{file.name}</TableCell>
                    <TableCell className="text-sm text-dark-300 tabular-nums">{formatSize(file.size)}</TableCell>
                    <TableCell className="text-sm text-dark-300 whitespace-nowrap">{formatDate(file.modified)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => window.open(file.url, '_blank')} title="Открыть">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-red-400" onClick={() => setDeletePath(file.path)} title="Удалить">
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )
      )}

      {!isPending && !error && (
        <div className="text-sm text-dark-300">Всего: <strong className="text-white">{data.length}</strong></div>
      )}

      <ConfirmDialog
        open={deletePath !== null}
        onOpenChange={(v) => { if (!v) setDeletePath(null) }}
        title="Удалить файл?"
        description="Файл будет удалён без возможности восстановления."
        confirmLabel="Удалить"
        variant="destructive"
        onConfirm={doDelete}
      />
    </div>
  )
}
