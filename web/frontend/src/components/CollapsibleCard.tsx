import { useState, type ReactNode } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Card } from '@/components/ui/card'

/**
 * Collapsible card (accordion). Collapsed by default; click the header to
 * expand. Used for sidebar blocks in editors.
 */
export function CollapsibleCard({
  title,
  description,
  defaultOpen = false,
  children,
}: {
  title: string
  description?: string
  defaultOpen?: boolean
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <Card className="p-0 overflow-hidden rounded-xl">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-4 p-4 hover:bg-[var(--glass-bg)] transition-colors text-left"
      >
        <div className="flex items-center gap-3 min-w-0">
          {open ? (
            <ChevronDown className="w-5 h-5 text-dark-200 shrink-0" />
          ) : (
            <ChevronRight className="w-5 h-5 text-dark-200 shrink-0" />
          )}
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-white truncate">{title}</h2>
            {description && <p className="text-xs text-dark-300 mt-0.5">{description}</p>}
          </div>
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 border-t border-[var(--glass-border)]/50">
          {children}
        </div>
      )}
    </Card>
  )
}
