export interface NavItem {
  label: string
  path: string
  icon: string
  children?: NavItem[]
}

export const navigation: NavItem[] = [
  { label: 'Дашборд', path: '/admin', icon: 'layout-dashboard' },
  {
    label: 'Посты', path: '/admin/posts', icon: 'file-text',
    children: [
      { label: 'Все посты', path: '/admin/posts', icon: 'list' },
      { label: 'Категории', path: '/admin/posts/categories', icon: 'folder-tree' },
    ],
  },
  { label: 'Страницы', path: '/admin/pages', icon: 'files' },
  { label: 'Пользователи', path: '/admin/users', icon: 'users' },
  { label: 'Медиа', path: '/admin/media', icon: 'image' },
  { label: 'Настройки', path: '/admin/settings', icon: 'settings' },
  { label: 'Темы', path: '/admin/theme', icon: 'palette' },
  { label: 'Виджеты', path: '/admin/widgets', icon: 'layout-grid' },
  { label: 'Меню', path: '/admin/menus', icon: 'menu' },
  { label: 'Логи', path: '/admin/logs', icon: 'scroll-text' },
  { label: 'Финансы', path: '/admin/finance', icon: 'wallet' },
]