interface BadgeProps {
  children: string
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
}

const colors: Record<string, { bg: string; text: string }> = {
  default: { bg: 'bg-white/5', text: 'text-[var(--text-secondary)]' },
  success: { bg: 'bg-emerald-500/10', text: 'text-emerald-400' },
  warning: { bg: 'bg-amber-500/10', text: 'text-amber-400' },
  danger: { bg: 'bg-red-500/10', text: 'text-red-400' },
  info: { bg: 'bg-sky-500/10', text: 'text-sky-400' },
}

export default function Badge({ children, variant = 'default' }: BadgeProps) {
  const c = colors[variant] ?? colors.default
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      {children}
    </span>
  )
}