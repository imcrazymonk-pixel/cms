import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Github,
  MessageCircle,
  Heart,
  Globe,
  Link,
  Plus,
  Trash2,
  RotateCcw,
  GripVertical,
} from 'lucide-react'
import {
  useSidebarLinksStore,
  type SidebarLink,
} from '../store/useSidebarLinksStore'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

const ICON_MAP: Record<string, React.ElementType> = {
  Github,
  MessageCircle,
  Heart,
  Globe,
  Link,
}

const ICON_OPTIONS = [
  { value: 'Github', label: 'GitHub' },
  { value: 'MessageCircle', label: 'Telegram' },
  { value: 'Heart', label: 'Heart' },
  { value: 'Globe', label: 'Globe' },
  { value: 'Link', label: 'Link' },
]

function IconPreview({ iconName, className }: { iconName: string; className?: string }) {
  const Icon = ICON_MAP[iconName] || Link
  return <Icon className={cn('w-4 h-4', className)} />
}

export function SidebarLinksPanel() {
  const { t } = useTranslation()
  const { links, setLinks, resetToDefaults } = useSidebarLinksStore()
  const [localLinks, setLocalLinks] = useState<SidebarLink[]>(links)

  const handleOpenChange = (open: boolean) => {
    if (open) {
      setLocalLinks([...links])
    }
  }

  const handleSave = () => {
    setLinks(localLinks)
  }

  const handleReset = () => {
    resetToDefaults()
    setLocalLinks([...useSidebarLinksStore.getState().links])
  }

  const addLink = () => {
    const newLink: SidebarLink = {
      id: `custom-${Date.now()}`,
      label: '',
      url: '',
      icon: 'Link',
      enabled: true,
    }
    setLocalLinks([...localLinks, newLink])
  }

  const removeLink = (id: string) => {
    setLocalLinks(localLinks.filter((l) => l.id !== id))
  }

  const updateLocalLink = (id: string, partial: Partial<SidebarLink>) => {
    setLocalLinks(localLinks.map((l) => (l.id === id ? { ...l, ...partial } : l)))
  }

  const moveLink = (index: number, direction: -1 | 1) => {
    const newIndex = index + direction
    if (newIndex < 0 || newIndex >= localLinks.length) return
    const items = [...localLinks]
    ;[items[index], items[newIndex]] = [items[newIndex], items[index]]
    setLocalLinks(items)
  }

  return (
    <Popover onOpenChange={handleOpenChange}>
      <Tooltip>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="icon" className="relative" aria-label={t('sidebar.linksSettings', 'Sidebar Links')}>
              <Link className="w-5 h-5" />
            </Button>
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent>{t('sidebar.linksSettings', 'Sidebar Links')}</TooltipContent>
      </Tooltip>

      <PopoverContent align="end" className="w-96 p-0">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--glass-border)]">
          <h4 className="text-sm font-semibold text-white">
            {t('sidebar.linksSettings', 'Sidebar Links')}
          </h4>
          <div className="flex items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-dark-300 hover:text-white"
                  onClick={handleReset}
                  aria-label={t('common.reset')}
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{t('appearance.resetToDefaults')}</TooltipContent>
            </Tooltip>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-primary-400 hover:text-primary-300"
              onClick={addLink}
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              {t('common.add', 'Add')}
            </Button>
          </div>
        </div>

        <ScrollArea className="max-h-[60vh]">
          <div className="p-4 space-y-3">
            {localLinks.map((link, index) => (
              <div
                key={link.id}
                className="bg-[var(--glass-bg)] rounded-lg border border-[var(--glass-border)] p-3 space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1">
                    <button className="cursor-grab active:cursor-grabbing text-dark-300 hover:text-white p-0.5" aria-label="Drag to reorder">
                      <GripVertical className="w-3.5 h-3.5" />
                    </button>
                    <IconPreview iconName={link.icon} />
                    <span className="text-xs text-dark-200 font-medium ml-1">
                      {link.label || t('common.unnamed', 'Unnamed')}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Switch
                      checked={link.enabled}
                      onCheckedChange={(checked) => updateLocalLink(link.id, { enabled: checked })}
                    />
                    {!link.id.startsWith('custom-') ? null : (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-dark-300 hover:text-red-400"
                        onClick={() => removeLink(link.id)}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <Label className="text-[10px] text-dark-300 uppercase tracking-wider">
                    {t('common.label', 'Label')}
                  </Label>
                  <Input
                    value={link.label}
                    onChange={(e) => updateLocalLink(link.id, { label: e.target.value })}
                    placeholder="GitHub"
                    className="h-8 text-xs"
                  />
                </div>

                <div className="space-y-1">
                  <Label className="text-[10px] text-dark-300 uppercase tracking-wider">
                    URL
                  </Label>
                  <Input
                    value={link.url}
                    onChange={(e) => updateLocalLink(link.id, { url: e.target.value })}
                    placeholder="https://github.com/..."
                    className="h-8 text-xs font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <Label className="text-[10px] text-dark-300 uppercase tracking-wider">
                    {t('common.icon', 'Icon')}
                  </Label>
                  <div className="flex gap-1 flex-wrap">
                    {ICON_OPTIONS.map((opt) => {
                      const isActive = link.icon === opt.value
                      return (
                        <button
                          key={opt.value}
                          onClick={() => updateLocalLink(link.id, { icon: opt.value })}
                          className={cn(
                            'flex items-center gap-1 px-2 py-1 text-[10px] rounded-md transition-all',
                            isActive
                              ? 'bg-primary/20 text-primary-400 border border-primary/30'
                              : 'bg-dark-600/30 text-dark-200 border border-[var(--glass-border)] hover:border-white/20'
                          )}
                        >
                          <IconPreview iconName={opt.value} />
                          {opt.label}
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div className="flex justify-end gap-1 pt-1">
                  <button
                    onClick={() => moveLink(index, -1)}
                    disabled={index === 0}
                    className="text-xs text-dark-300 hover:text-white disabled:opacity-30 px-1 py-0.5"
                  >↑</button>
                  <button
                    onClick={() => moveLink(index, 1)}
                    disabled={index === localLinks.length - 1}
                    className="text-xs text-dark-300 hover:text-white disabled:opacity-30 px-1 py-0.5"
                  >↓</button>
                </div>
              </div>
            ))}

            {localLinks.length === 0 && (
              <div className="py-8 text-center text-dark-200 text-sm">
                <Link className="w-8 h-8 mx-auto mb-2 opacity-30" />
                <p>{t('sidebar.noLinks', 'No sidebar links configured')}</p>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="px-4 py-3 border-t border-[var(--glass-border)]">
          <Button className="w-full text-sm h-9" onClick={handleSave}>
            {t('common.apply', 'Apply')}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}