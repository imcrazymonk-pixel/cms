import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  padding?: boolean
}

export default function Card({ children, className = '', padding = true }: CardProps) {
  return (
    <div
      className={`rounded-xl bg-[var(--glass-bg)] border border-[var(--glass-border)] backdrop-blur-sm ${
        padding ? 'p-5' : ''
      } ${className}`}
    >
      {children}
    </div>
  )
}