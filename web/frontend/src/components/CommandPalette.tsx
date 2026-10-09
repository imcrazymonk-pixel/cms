import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  LayoutDashboard,
  FileText,
  Folder,
  File,
  Menu,
  Image,
  Puzzle,
  Palette,
  Wallet,
  Users,
  Settings,
  Terminal,
  Monitor,
} from 'lucide-react'
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from '@/components/ui/command'

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [search, setSearch] = useState('')

  // Reset search when closing
  useEffect(() => {
    if (!open) {
      setSearch('')
    }
  }, [open])

  const runCommand = useCallback(
    (command: () => void) => {
      onOpenChange(false)
      command()
    },
    [onOpenChange],
  )

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput
        placeholder={t('commandPalette.placeholder')}
        value={search}
        onValueChange={setSearch}
      />
      <CommandList>
        <CommandEmpty>{t('commandPalette.noResults')}</CommandEmpty>

        {/* Navigation — CMS sections (mirrors CMS Sidebar) */}
        <CommandGroup heading={t('commandPalette.navigation')}>
          <CommandItem
            value="dashboard дашборд"
            onSelect={() => runCommand(() => navigate('/'))}
          >
            <LayoutDashboard className="mr-2 h-4 w-4" />
            {t('nav.dashboard')}
          </CommandItem>
          <CommandItem
            value="posts посты статьи"
            onSelect={() => runCommand(() => navigate('/posts'))}
          >
            <FileText className="mr-2 h-4 w-4" />
            {t('nav.posts')}
          </CommandItem>
          <CommandItem
            value="categories категории рубрики"
            onSelect={() => runCommand(() => navigate('/posts/categories'))}
          >
            <Folder className="mr-2 h-4 w-4" />
            {t('nav.categories')}
          </CommandItem>
          <CommandItem
            value="pages страницы"
            onSelect={() => runCommand(() => navigate('/pages'))}
          >
            <File className="mr-2 h-4 w-4" />
            {t('nav.pages')}
          </CommandItem>
          <CommandItem
            value="menus меню навигация"
            onSelect={() => runCommand(() => navigate('/menus'))}
          >
            <Menu className="mr-2 h-4 w-4" />
            {t('nav.menus')}
          </CommandItem>
          <CommandItem
            value="media медиа файлы изображения"
            onSelect={() => runCommand(() => navigate('/media'))}
          >
            <Image className="mr-2 h-4 w-4" />
            {t('nav.media')}
          </CommandItem>
          <CommandItem
            value="widgets виджеты блоки"
            onSelect={() => runCommand(() => navigate('/widgets'))}
          >
            <Puzzle className="mr-2 h-4 w-4" />
            {t('nav.widgets')}
          </CommandItem>
          <CommandItem
            value="themes темы оформление"
            onSelect={() => runCommand(() => navigate('/themes'))}
          >
            <Palette className="mr-2 h-4 w-4" />
            {t('nav.themes')}
          </CommandItem>
          <CommandItem
            value="finance финансы деньги транзакции"
            onSelect={() => runCommand(() => navigate('/finance'))}
          >
            <Wallet className="mr-2 h-4 w-4" />
            {t('nav.finance')}
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Administration */}
        <CommandGroup heading={t('commandPalette.administration')}>
          <CommandItem
            value="users пользователи"
            onSelect={() => runCommand(() => navigate('/users'))}
          >
            <Users className="mr-2 h-4 w-4" />
            {t('nav.users')}
          </CommandItem>
          <CommandItem
            value="settings настройки"
            onSelect={() => runCommand(() => navigate('/settings'))}
          >
            <Settings className="mr-2 h-4 w-4" />
            {t('nav.settings')}
          </CommandItem>
          <CommandItem
            value="logs логи системные"
            onSelect={() => runCommand(() => navigate('/logs'))}
          >
            <Terminal className="mr-2 h-4 w-4" />
            {t('nav.logs')}
          </CommandItem>
          <CommandItem
            value="diagnostics диагностика ноды"
            onSelect={() => runCommand(() => navigate('/diagnostics'))}
          >
            <Monitor className="mr-2 h-4 w-4" />
            {t('nav.diagnostics')}
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
