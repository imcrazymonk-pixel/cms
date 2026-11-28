import {
  LayoutDashboard,
  FileText,
  Folder,
  File,
  Menu,
  Image,
  Puzzle,
  Globe,
  SlidersHorizontal,
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
  BadgeCheck,
  ScrollText,
  LifeBuoy,
  Inbox,
  Gauge,
  BookOpen,
  Sparkles,
  FileStack,
  UserCog,
  TrendingUp,
  HardDrive,
  Server,
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

  { type: 'group', name: 'Сайт', icon: Globe, items: [
      { name: 'Посты', href: '/posts', icon: FileText, permission: null },
      { name: 'Категории', href: '/posts/categories', icon: Folder, permission: null },
      { name: 'Страницы', href: '/pages', icon: File, permission: null },
      { name: 'Меню', href: '/menus', icon: Menu, permission: null },
      { name: 'Медиа', href: '/media', icon: Image, permission: null },
      { name: 'Виджеты', href: '/widgets', icon: Puzzle, permission: null },
  ]},

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
      { name: 'Тарифы', href: '/bedolaga/tariffs', icon: BadgeCheck, permission: null },
      { name: 'Доход по тарифам', href: '/bedolaga/revenue', icon: TrendingUp, permission: null },
      { name: 'Промокоды', href: '/bedolaga/promo', icon: Ticket, permission: null },
      { name: 'Маркетинг', href: '/bedolaga/marketing', icon: Megaphone, permission: null },
      { name: 'Рефералы', href: '/bedolaga/referrals', icon: Share2, permission: null },
      { name: 'Настройки', href: '/settings?tab=integrations&from=bedolaga', icon: SlidersHorizontal, permission: null },
    ],
  },

  { type: 'section', name: 'Саппорт' },
  {
    type: 'group',
    name: 'Саппорт',
    icon: LifeBuoy,
    items: [
      { name: 'Очередь', href: '/support', icon: Inbox, permission: null },
      { name: 'Контроль SLA', href: '/support/sla', icon: Gauge, permission: null },
      { name: 'База знаний', href: '/support/kb', icon: BookOpen, permission: null },
      { name: 'ИИ-ассистент', href: '/support/ai', icon: Sparkles, permission: null },
      { name: 'Шаблоны', href: '/support/templates', icon: FileStack, permission: null },
      { name: 'Аналитика', href: '/support/analytics', icon: BarChart3, permission: null },
      { name: 'Команда', href: '/support/team', icon: UserCog, permission: null },
      { name: 'Настройки', href: '/settings?tab=support&from=support', icon: SlidersHorizontal, permission: null },
    ],
  },

  { type: 'section', name: 'Инфраструктура' },
  {
    type: 'group',
    name: 'Инфраструктура',
    icon: Server,
    items: [
      { name: 'Бэкапы', href: '/backups', icon: HardDrive, permission: null },
      { name: 'Ноды', href: '/infrastructure/nodes', icon: Server, permission: null },
      { name: 'Панель', href: '/infrastructure/panel', icon: Gauge, permission: null },
    ],
  },

  { type: 'section', name: 'Система' },
  { name: 'Пользователи', href: '/users', icon: Users, permission: null },
  { name: 'Настройки', href: '/settings', icon: Settings, permission: null },
  { name: 'Логи', href: '/logs', icon: Terminal, permission: null },
  { name: 'Диагностика', href: '/diagnostics', icon: Monitor, permission: null },

  { type: 'section', name: 'Документация' },
  { name: 'Ченжлог', href: '/changelog', icon: ScrollText, permission: null },
]

export default navigation