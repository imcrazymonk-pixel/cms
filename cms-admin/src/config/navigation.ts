export interface NavItem {
  label: string
  path: string
  icon: string
  children?: NavItem[]
}

export type NavEntry = NavItem | { type: 'section'; label: string }

export const navigation: NavEntry[] = [
  { label: 'Дашборд', path: '/admin', icon: 'layout-dashboard' },

  { type: 'section', label: 'Контент' },
  { label: 'Посты', path: '/admin/posts', icon: 'file-text',
    children: [
      { label: 'Все посты', path: '/admin/posts', icon: 'list' },
      { label: 'Категории', path: '/admin/posts/categories', icon: 'folder-tree' },
    ],
  },
  { label: 'Страницы', path: '/admin/pages', icon: 'files' },
  { label: 'Медиа', path: '/admin/media', icon: 'image' },

  { type: 'section', label: 'Внешний вид' },
  { label: 'Темы', path: '/admin/theme', icon: 'palette' },
  { label: 'Виджеты', path: '/admin/widgets', icon: 'layout-grid' },
  { label: 'Меню', path: '/admin/menus', icon: 'menu' },

  { type: 'section', label: 'Пользователи' },
  { label: 'Пользователи', path: '/admin/users', icon: 'users' },

  { type: 'section', label: 'Система' },
  { label: 'Настройки', path: '/admin/settings', icon: 'settings' },
  { label: 'Логи', path: '/admin/logs', icon: 'scroll-text' },
  { label: 'Финансы', path: '/admin/finance', icon: 'wallet' },
]