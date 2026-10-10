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
  Bot,
  BarChart3,
  Ticket,
  Megaphone,
  Share2,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  type?: 'item'
  name: string
  href: string
  icon: LucideIcon
  permission: null
}

export interface NavGroup {
  type: 'group'
  name: string
  icon: LucideIcon
  items: NavItem[]
}

export interface NavSection {
  type: 'section'
  name: string
}

type NavigationEntry = NavItem | NavGroup | NavSection

const navigation: NavigationEntry[] = [
  { type: 'section', name: 'Главное' },
  { name: 'Дашборд', href: '/', icon: LayoutDashboard, permission: null },

  { type: 'section', name: 'Сайт' },
  { name: 'Посты', href: '/posts', icon: FileText, permission: null },
  { name: 'Категории', href: '/posts/categories', icon: Folder, permission: null },
  { name: 'Страницы', href: '/pages', icon: File, permission: null },
  { name: 'Меню', href: '/menus', icon: Menu, permission: null },
  { name: 'Медиа', href: '/media', icon: Image, permission: null },
  { name: 'Виджеты', href: '/widgets', icon: Puzzle, permission: null },
  { name: 'Темы', href: '/themes', icon: Palette, permission: null },

  { type: 'section', name: 'Финансы' },
  { name: 'Финансы', href: '/finance', icon: Wallet, permission: null },

  { type: 'section', name: 'Bedolaga' },
  {
    type: 'group',
    name: 'Bedolaga Bot',
    icon: Bot,
    items: [
      { name: 'Дашборд', href: '/bedolaga', icon: BarChart3, permission: null },
      { name: 'Клиенты', href: '/bedolaga/customers', icon: Users, permission: null },
      { name: 'Промокоды', href: '/bedolaga/promo', icon: Ticket, permission: null },
      { name: 'Маркетинг', href: '/bedolaga/marketing', icon: Megaphone, permission: null },
      { name: 'Рефералы', href: '/bedolaga/referrals', icon: Share2, permission: null },
    ],
  },

  { type: 'section', name: 'Система' },
  { name: 'Пользователи', href: '/users', icon: Users, permission: null },
  { name: 'Настройки', href: '/settings', icon: Settings, permission: null },
  { name: 'Логи', href: '/logs', icon: Terminal, permission: null },
  { name: 'Диагностика', href: '/diagnostics', icon: Monitor, permission: null },
]

export default navigation