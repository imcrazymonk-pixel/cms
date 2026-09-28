import { useState } from 'react'
import { Button } from './button'

export interface Column<T> {
  key: string
  label: string
  sortable?: boolean
  render?: (row: T) => React.ReactNode
  width?: string
}

interface DataGridProps<T> {
  columns: Column<T>[]
  data: T[]
  keyField: string
  total: number
  page: number
  perPage: number
  onPageChange: (page: number) => void
  onSort?: (key: string, dir: 'asc' | 'desc') => void
  sortKey?: string
  sortDir?: 'asc' | 'desc'
  loading?: boolean
  selectable?: boolean
  selectedIds?: (string | number)[]
  onSelectionChange?: (ids: (string | number)[]) => void
  actions?: (row: T) => React.ReactNode
  emptyMessage?: string
}

export default function DataGrid<T extends Record<string, unknown>>({
  columns,
  data,
  keyField,
  total,
  page,
  perPage,
  onPageChange,
  onSort,
  sortKey,
  sortDir,
  loading = false,
  selectable = false,
  selectedIds = [],
  onSelectionChange,
  actions,
  emptyMessage = 'Нет данных',
}: DataGridProps<T>) {
  const totalPages = Math.max(1, Math.ceil(total / perPage))

  const toggleSelect = (id: string | number) => {
    if (!onSelectionChange) return
    const next = selectedIds.includes(id)
      ? selectedIds.filter((i) => i !== id)
      : [...selectedIds, id]
    onSelectionChange(next)
  }

  const toggleAll = () => {
    if (!onSelectionChange) return
    if (selectedIds.length === data.length) {
      onSelectionChange([])
    } else {
      onSelectionChange(data.map((r) => r[keyField] as string | number))
    }
  }

  return (
    <div className="space-y-4">
      {/* Table */}
      <div className="rounded-xl border border-[var(--glass-border)] overflow-hidden bg-[var(--glass-bg)] backdrop-blur-sm">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                {selectable && (
                  <th className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={data.length > 0 && selectedIds.length === data.length}
                      onChange={toggleAll}
                      className="rounded border-white/20 bg-transparent accent-[var(--accent)]"
                    />
                  </th>
                )}
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={`px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider ${
                      col.sortable ? 'cursor-pointer hover:text-[var(--text-primary)] select-none' : ''
                    }`}
                    style={col.width ? { width: col.width } : undefined}
                    onClick={() => {
                      if (!col.sortable || !onSort) return
                      const newDir = sortKey === col.key && sortDir === 'asc' ? 'desc' : 'asc'
                      onSort(col.key, newDir)
                    }}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {col.sortable && sortKey === col.key && (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
                          {sortDir === 'asc' ? (
                            <polyline points="18 15 12 9 6 15" />
                          ) : (
                            <polyline points="6 9 12 15 18 9" />
                          )}
                        </svg>
                      )}
                    </span>
                  </th>
                ))}
                {actions && <th className="w-12 px-4 py-3" />}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={columns.length + (selectable ? 1 : 0) + (actions ? 1 : 0)} className="text-center py-12">
                    <div className="inline-flex items-center gap-2 text-[var(--text-muted)]">
                      <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Загрузка...
                    </div>
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={columns.length + (selectable ? 1 : 0) + (actions ? 1 : 0)} className="text-center py-12 text-[var(--text-muted)]">
                    {emptyMessage}
                  </td>
                </tr>
              ) : (
                data.map((row) => (
                  <tr key={row[keyField] as string} className="hover:bg-white/[0.02] transition-colors">
                    {selectable && (
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(row[keyField] as string | number)}
                          onChange={() => toggleSelect(row[keyField] as string | number)}
                          className="rounded border-white/20 bg-transparent accent-[var(--accent)]"
                        />
                      </td>
                    )}
                    {columns.map((col) => (
                      <td key={col.key} className="px-4 py-3 text-sm text-[var(--text-primary)]">
                        {col.render ? col.render(row) : (row[col.key] as React.ReactNode) ?? '—'}
                      </td>
                    ))}
                    {actions && (
                      <td className="px-4 py-3 text-right">
                        <ActionsDropdown>{actions(row)}</ActionsDropdown>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-muted)]">
            {total > 0 ? `${(page - 1) * perPage + 1}–${Math.min(page * perPage, total)} из ${total}` : '0 записей'}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="h-8 w-8 flex items-center justify-center rounded-md text-[var(--text-secondary)] hover:bg-white/5 hover:text-[var(--text-primary)] disabled:opacity-30 disabled:pointer-events-none transition-colors"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6" /></svg>
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              const start = Math.max(1, Math.min(page - 3, totalPages - 6))
              const p = start + i
              if (p > totalPages) return null
              return (
                <button
                  key={p}
                  onClick={() => onPageChange(p)}
                  className={`h-8 w-8 rounded-md text-sm font-medium transition-colors ${
                    p === page
                      ? 'bg-[var(--accent)]/10 text-[var(--accent)]'
                      : 'text-[var(--text-secondary)] hover:bg-white/5 hover:text-[var(--text-primary)]'
                  }`}
                >
                  {p}
                </button>
              )
            })}
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="h-8 w-8 flex items-center justify-center rounded-md text-[var(--text-secondary)] hover:bg-white/5 hover:text-[var(--text-primary)] disabled:opacity-30 disabled:pointer-events-none transition-colors"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6" /></svg>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Simple actions dropdown (kebab menu)
function ActionsDropdown({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(!open) }}
        className="h-8 w-8 flex items-center justify-center rounded-md text-[var(--text-muted)] hover:bg-white/5 hover:text-[var(--text-primary)] transition-colors"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="5" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="19" r="2"/></svg>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 min-w-[140px] rounded-lg bg-[var(--bg-surface)] border border-white/10 shadow-xl py-1">
            {children}
          </div>
        </>
      )}
    </div>
  )
}