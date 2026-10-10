import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Info } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * InfoTooltip — small info icon that shows a tooltip on hover.
 * 
 * Adapted from remnawave-admin-main. Drop-in replacement.
 */
export function InfoTooltip({ text, side = 'right' }: { text: string; side?: 'top' | 'bottom' | 'left' | 'right' }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={cn('inline-flex items-center justify-center w-4 h-4 cursor-help text-dark-400 hover:text-primary-400 transition-colors')}>
          <Info className="w-3.5 h-3.5" />
        </span>
      </TooltipTrigger>
      <TooltipContent side={side}>
        <p className="text-xs max-w-[220px]">{text}</p>
      </TooltipContent>
    </Tooltip>
  )
}