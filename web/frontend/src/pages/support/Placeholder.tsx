import type { LucideIcon } from 'lucide-react'
import { Construction } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'

interface SupportPlaceholderProps {
  title: string
  description: string
  icon?: LucideIcon
}

/**
 * Экран «Раздел в разработке» — заглушка подпунктов меню «Саппорт»,
 * пока их фазовый бэкенд/UI не готовы.
 */
export default function SupportPlaceholder({ title, description, icon }: SupportPlaceholderProps) {
  const Icon = icon || Construction
  return (
    <div className="space-y-4 md:space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-header-title">{title}</h1>
          <p className="mt-1 text-sm text-dark-200">Раздел «Саппорт»</p>
        </div>
      </div>
      <div className="glass-card">
        <EmptyState
          icon={Icon}
          size="lg"
          title={`Раздел в разработке`}
          description={description}
        />
      </div>
    </div>
  )
}
