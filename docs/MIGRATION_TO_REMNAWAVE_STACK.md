# Миграция CMS на стек Remnawave

## Полный план перехода: PHP SSR → React SPA + API → FastAPI

> **Дата:** 2026-10-04
> **Цель:** Полная замена архитектуры админки на React SPA (как remnawave-admin-main)
> с поэтапным замещением PHP-бэкенда на FastAPI.

---

## 1. ЧЕГО НЕ ДЕЛАТЬ (СТРОГИЕ ЗАПРЕТЫ)

Эти правила **нельзя нарушать**. Даже если кажется, что «так будет проще» или «это же очевидно».

### 1.1 PHP — ТОЛЬКО ДЛЯ ПРОМЕЖУТОЧНОГО ЭТАПА (не расширять без необходимости)
- **КОНЕЧНАЯ ЦЕЛЬ** — полный уход от PHP. Но не сразу, а поэтапно.
- **СЕЙЧАС** PHP остаётся как API-прослойка для React-фронтенда.
- **НЕЛЬЗЯ** переписывать существующие PHP-контроллеры, модели, маршруты
- **НЕЛЬЗЯ** менять имена полей в БД, формах, URL
- **НЕЛЬЗЯ** удалять PHP-файлы, даже если они кажутся «ненужными»
- **МОЖНО** ТОЛЬКО добавлять новые JSON-эндпоинты рядом с существующими
- **МОЖНО** править CSS-баги (только баги, не редизайн)

### 1.2 React-фронтенд — НЕ ДОБАВЛЯТЬ ЛИШНЕГО
- **НЕЛЬЗЯ** добавлять страницы/функции, которых нет в текущей PHP-админке
- **НЕЛЬЗЯ** менять дизайн-систему remnawave (цвета, шрифты, отступы, glass-эффекты)
- **НЕЛЬЗЯ** добавлять новые CSS-файлы — все стили в `src/index.css`
- **НЕЛЬЗЯ** использовать другие UI-библиотеки кроме shadcn/ui (Radix UI)
- **НЕЛЬЗЯ** менять структуру Sidebar/Header/Layout — 100% копия remnawave

### 1.3 API — НЕ МЕНЯТЬ СИГНАТУРЫ
- **НЕЛЬЗЯ** менять формат ответа существующих `/api/*` эндпоинтов (PHP)
- **НЕЛЬЗЯ** добавлять поля в JSON-ответ, которых нет в текущей PHP-модели
- **НЕЛЬЗЯ** удалять поля из JSON-ответа, даже если они «не используются»

### 1.4 Данные — НЕ ТРОГАТЬ
- **НЕЛЬЗЯ** менять схему БД (`db/postgres/init/01-schema.sql`)
- **НЕЛЬЗЯ** создавать параллельные таблицы с теми же данными
- **НЕЛЬЗЯ** мигрировать данные между PHP и FastAPI вручную

### 1.5 Инфраструктура
- **НЕЛЬЗЯ** трогать nginx на проде без теста на staging
- **НЕЛЬЗЯ** деплоить React-фронтенд пока не готова хотя бы Login + Dashboard
- **НЕЛЬЗЯ** удалять PHP-админку пока все страницы не перенесены

### 1.6 Отсебятина — СТРОЖАЙШИЙ ЗАПРЕТ
- **НЕ ДОБАВЛЯТЬ** «улучшения дизайна» — дизайн remnawave, никаких отсебятин
- **НЕ ДОБАВЛЯТЬ** новый функционал — только перенос существующего
- **НЕ УРЕЗАТЬ** функционал — всё что есть в PHP-админке должно быть в React
- **НЕ ПЕРЕИМЕНОВЫВАТЬ** разделы, кнопки, колонки
- **Любые «улучшения», «оптимизации», «дополнительные фишки» — только ПОСЛЕ полного завершения миграции.**
- Если React-разработчик говорит «а давайте добавим ещё и сортировку по рейтингу» или «тут можно сделать удобнее» — ответ один: **«Сначала делаем 1:1 копию, улучшения — потом»**.

---

## 2. КОНЕЧНАЯ ЦЕЛЬ

```
cms.hexaveil.xyz    → React SPA (админка, 100% копия remnawave)
hexaveil.xyz        → React (публичный сайт: лендинг + блог)

Бэкенд (сейчас PHP → потом FastAPI) → PostgreSQL
```

### Что куда

| URL | Сейчас | Цель | Стек |
|-----|--------|------|------|
| **hexaveil.xyz/admin** | PHP + CSS | → React SPA на `cms.hexaveil.xyz` | React |
| **hexaveil.xyz** | PHP + 3D-глобус | → React (лендинг + блог) | React |
| **cms.hexaveil.xyz** | нет | → Новая React-админка | React |

### Зачем так

| Сейчас (PHP) | Будет (React + API) |
|-------------|-------------------|
| PHP сам рисует кнопки и тащит данные | React рисует кнопки, API (PHP/FastAPI) отдаёт только данные |
| Чтобы изменить кнопку → лезешь в PHP | Чтобы изменить кнопку → React. Чтобы изменить логику → API |
| Нельзя заменить PHP без переписывания всего | Можно заменить PHP на FastAPI — React не заметит |

### Область действия документа

**Этот документ описывает ТОЛЬКО миграцию админки.** Публичный сайт (лендинг, блог) переписывается потом, отдельным планом.

---

## 3. ФАЗА 0: ПОДГОТОВКА PHP API (2-3 дня)

**Цель:** Добавить недостающие JSON-эндпоинты в PHP, чтобы React-фронтенд мог получать все данные.

### Что нужно сделать:

#### 3.1 Очерёдность

Из 6 разделов, для которых нет API, приоритет такой:

| Раздел | Нужен | Когда делать |
|--------|-------|-------------|
| **Медиа** | Загрузка картинок | ПОТОМ (можно позже) |
| **Меню** | Навигация сайта | Средний приоритет — не ломает сайт, но нужен |
| **Виджеты** | Боковые блоки | **ВЫСОКИЙ** — активно используются |
| **Настройки** | Название сайта, SEO | НИЗКИЙ — меняются раз в год |
| **Темы** | Настройки активной темы (цвета, шрифты, параметры) | СРЕДНИЙ — НУЖНО, но только настройки текущей темы (загрузку .zip и переключение между темами — НЕ ДЕЛАТЬ) |
| **Логи** | Просмотр логов | **ВЫСОКИЙ** — часто смотрю |
| **Настройки вида** | Тёмная/светлая тема в админке | React сам сохранит |

### 3.2 Что реально нужно сделать

**В первую очередь (ХАЙ):**
- `/api/widgets/*` — для виджетов (активно используются)
- `/api/logs/*` — для логов (часто смотришь)

**Во вторую (СРЕДНИЙ):**
- `/api/menus/*` — для меню (нужно, но не срочно)
- `/api/themes/settings` — для настроек активной темы (только чтение/запись настроек, без загрузки .zip и переключения)

**В последнюю (НИЗКИЙ / ПОТОМ):**
- `/api/media/*` — для медиатеки
- `/api/settings` — для настроек (раз в год)

#### Как выглядят новые эндпоинты (коротко)

Каждый новый эндпоинт — это просто «дай данные в JSON»:

- `GET /api/logs` → PHP лезет в БД, отдаёт JSON со списком логов
- `GET /api/widgets` → PHP лезет в БД, отдаёт JSON со списком виджетов
- `POST /api/widgets` → React говорит PHP «создай виджет», PHP создаёт
- `PUT /api/widgets/{id}` → React говорит «обнови виджет», PHP обновляет
- `DELETE /api/widgets/{id}` → React говорит «удали виджет», PHP удаляет

Тот же принцип что уже работает для постов (`/api/posts`), страниц, пользователей.

---

## 4. ФАЗА 1: REACT SPA (2-4 недели)

**Цель:** Получить работающий React-фронтенд с 100% визуалом remnawave,
подключённый к PHP API. Постепенно перенести все страницы.

**Где лежит React-проект:** Внутри текущего репозитория — `NewWeb/admin-react/`.
Всё в одном месте: PHP + React рядом. Когда PHP уйдёт, React останется в корне.

### 4.1 Структура React-проекта и порядок переноса

**Что берём из remnawave (копируем без изменений):**
- Дизайн (index.css) — вся красота: стеклянные карточки, mesh-фон, 6 тем
- Шапка и меню (Header, Sidebar) — левая панель, навигация
- Все кнопки, таблицы, модалки (23 shadcn/ui компонента) — строительные блоки
- Командная палитра (Ctrl+K) — поиск по разделам
- Панель настройки вида (темы, плотность)
- Zustand store — запоминает тёмную/светлую тему

**Порядок переноса страниц (строгий):**

1. **Login** — страница входа в админку (без неё никак)
2. **Dashboard** — главная после входа (без неё никак)
3. **Finance** — финансы (сразу после дашборда)
4. **Diagnostics** — диагностика (сразу после дашборда)
5. **LogsViewer** — логи (сразу после дашборда, часто смотришь)
6—17 — остальные по порядку из таблицы в п.4.8
- **ThemeManager** — ТОЛЬКО настройки активной темы (загрузка .zip и переключение тем НЕ НУЖНЫ)

```
admin-react/
├── src/
│   ├── main.tsx              ← скопировать из remnawave
│   ├── App.tsx               ← скопировать, ИЗМЕНИТЬ роутер (убрать ремна-страницы)
│   ├── index.css             ← скопировать БЕЗ ИЗМЕНЕНИЙ (весь визуал)
│   ├── i18n.ts               ← скопировать, заменить переводы
│   ├── api/
│   │   ├── client.ts         ← ПЕРЕПИСАТЬ: PHP API вместо FastAPI
│   │   ├── auth.ts           ← ПЕРЕПИСАТЬ: PHP JWT auth
│   │   ├── posts.ts          ← НОВЫЙ: /api/posts
│   │   ├── pages.ts          ← НОВЫЙ: /api/pages
│   │   ├── users.ts          ← НОВЫЙ: /api/users
│   │   ├── media.ts          ← НОВЫЙ: /api/media
│   │   ├── menus.ts          ← НОВЫЙ: /api/menus
│   │   ├── widgets.ts        ← НОВЫЙ: /api/widgets
│   │   ├── settings.ts       ← НОВЫЙ: /api/settings
│   │   ├── themes.ts         ← НОВЫЙ: /api/themes/settings (только настройки)
│   │   ├── logs.ts           ← НОВЫЙ: /api/logs
│   │   ├── finance.ts        ← НОВЫЙ: /api/finance
│   │   └── dashboard.ts      ← НОВЫЙ: /api/dashboard
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Layout.tsx    ← скопировать БЕЗ ИЗМЕНЕНИЙ
│   │   │   ├── Sidebar.tsx   ← скопировать, ПОМЕНЯТЬ ПУНКТЫ МЕНЮ
│   │   │   ├── Header.tsx    ← скопировать БЕЗ ИЗМЕНЕНИЙ
│   │   │   └── PageBreadcrumbs.tsx ← скопировать БЕЗ ИЗМЕНЕНИЙ
│   │   ├── ui/               ← скопировать ВСЕ 23 компонента shadcn/ui БЕЗ ИЗМЕНЕНИЙ
│   │   ├── brand/
│   │   │   └── BrandLogo.tsx ← скопировать, ПОМЕНЯТЬ НА ЛОГОТИП CMS
│   │   ├── CommandPalette.tsx ← скопировать, ПОМЕНЯТЬ ПУНКТЫ
│   │   ├── ConfirmDialog.tsx  ← скопировать БЕЗ ИЗМЕНЕНИЙ
│   │   ├── AppearancePanel.tsx← скопировать БЕЗ ИЗМЕНЕНИЙ
│   │   ├── EmptyState.tsx     ← скопировать БЕЗ ИЗМЕНЕНИЙ
│   │   ├── ExportDropdown.tsx ← скопировать БЕЗ ИЗМЕНЕНИЙ
│   │   └── ErrorBoundary.tsx  ← скопировать БЕЗ ИЗМЕНЕНИЙ
│   ├── pages/
│   │   ├── Login.tsx         ← ПЕРЕПИСАТЬ ПОД PHP JWT
│   │   ├── Dashboard.tsx     ← ПЕРЕПИСАТЬ ПОД PHP API
│   │   ├── PostsList.tsx     ← НОВЫЙ
│   │   ├── PostEdit.tsx      ← НОВЫЙ
│   │   ├── PagesList.tsx     ← НОВЫЙ
│   │   ├── PageEdit.tsx      ← НОВЫЙ
│   │   ├── UsersList.tsx     ← НОВЫЙ
│   │   ├── UserEdit.tsx      ← НОВЫЙ
│   │   ├── MediaList.tsx     ← НОВЫЙ
│   │   ├── MenusList.tsx     ← НОВЫЙ
│   │   ├── MenuEdit.tsx      ← НОВЫЙ
│   │   ├── WidgetsList.tsx   ← НОВЫЙ
│   │   ├── ThemeManager.tsx  ← НОВЫЙ
│   │   ├── Settings.tsx      ← ПЕРЕПИСАТЬ ПОД PHP API
│   │   ├── LogsViewer.tsx    ← НОВЫЙ
│   │   ├── Finance.tsx       ← ПЕРЕПИСАТЬ ПОД PHP API
│   │   ├── Diagnostics.tsx   ← НОВЫЙ
│   │   └── NotFound.tsx      ← скопировать БЕЗ ИЗМЕНЕНИЙ
│   ├── store/
│   │   ├── authStore.ts      ← ПЕРЕПИСАТЬ ПОД PHP JWT
│   │   ├── useAppearanceStore.ts ← скопировать БЕЗ ИЗМЕНЕНИЙ
│   │   └── useFiltersStore.ts ← скопировать БЕЗ ИЗМЕНЕНИЙ
│   └── lib/
│       ├── utils.ts          ← скопировать БЕЗ ИЗМЕНЕНИЙ
│       ├── useFormatters.ts  ← скопировать БЕЗ ИЗМЕНЕНИЙ
│       └── export.ts         ← скопировать БЕЗ ИЗМЕНЕНИЙ
├── public/
│   ├── config.js             ← НОВЫЙ: URL бэкенда
│   ├── favicon.svg           ← СВОЙ
│   └── logo.svg              ← СВОЙ
├── package.json              ← скопировать, обновить зависимости
├── vite.config.ts            ← скопировать, ПОМЕНЯТЬ ПРОКСИ
├── tailwind.config.js        ← скопировать БЕЗ ИЗМЕНЕНИЙ
├── tsconfig.json             ← скопировать БЕЗ ИЗМЕНЕНИЙ
├── index.html                ← скопировать, ПОМЕНЯТЬ ЗАГОЛОВОК
├── nginx.conf                ← НОВЫЙ: конфиг для прода
└── Dockerfile                ← НОВЫЙ: Docker-образ
```

### 4.2 Что можно удалить из remnawave (НЕ ПЕРЕНОСИТЬ)

**Из `src/pages/` оставить и переписать под PHP API:**
- `Login.tsx` — переписать (JWT auth под PHP)
- `Dashboard.tsx` — переписать (KPI под PHP)
- `Settings.tsx` — переписать (настройки CMS)
- `SystemLogs.tsx` — переписать (в CMS это LogsViewer)

**Из `src/pages/` удалить (Remnawave-специфичные):**
- `Users.tsx` — заменить своей версией
- `UserDetail.tsx` — не нужно (у CMS простая модель пользователя)
- `Servers.tsx`, `Fleet.tsx`, `Hosts.tsx`, `Nodes.tsx` — Remnawave-специфичное
- `Activity.tsx`, `Blocking.tsx`, `Notifications.tsx` — нет в CMS
- `Billing.tsx`, `Backup.tsx`, `Analytics.tsx`, `AuditLog.tsx` — Remnawave
- `Admins.tsx`, `AdminPlugins.tsx`, `MailServer.tsx` — Remnawave
- `Squads.tsx`, `AccessPoliciesTab.tsx`, `ApiKeys.tsx` — Remnawave
- `Reports.tsx`, `Resources.tsx`, `Violations.tsx` — Remnawave
- ВСЁ из `pages/automations/` — Remnawave
- ВСЁ из `pages/bedolaga/` — Bedolaga управляется отдельно
- ВСЁ из `pages/xray/` — Remnawave

**Из `src/api/` удалить ВСЁ:**
- `billing.ts`, `servers.ts`, `squads.ts`, `nodes.ts`, `hosts.ts` и т.д.
- Оставить ТОЛЬКО `client.ts` и `auth.ts` (переписать под PHP)

**Из `src/` удалить:**
- `plugins/` — Remnawave-плагины
- `types/` — Remnawave-типы (оставить только если нужны)
- `PermissionGate.tsx` — если в CMS нет RBAC
- `LazyGeoMap.tsx` — если не нужна карта
- `SavedFiltersDropdown.tsx` — если не нужно

### 4.3 Sidebar — что должно быть

> 100% копия remnawave по структуре. Меняются ТОЛЬКО пункты меню.

```tsx
// src/components/layout/Sidebar.tsx
// В remnawave — 5 пунктов (Dashboard, Users, Servers, Activity, Settings)
// В CMS — другие пункты, НО ТА ЖЕ ГРУППИРОВКА (NavItem, NavGroup, NavSection)

const navItems = [
  NavSection({ label: 'Главное' }),
  NavItem({ icon: LayoutDashboard, label: 'Дашборд', href: '/' }),
  
  NavSection({ label: 'Сайт' }),
  NavItem({ icon: FileText, label: 'Посты', href: '/posts' }),
  NavItem({ icon: Folder, label: 'Категории', href: '/posts/categories' }),
  NavItem({ icon: File, label: 'Страницы', href: '/pages' }),
  NavItem({ icon: Menu, label: 'Меню', href: '/menus' }),
  NavItem({ icon: Image, label: 'Медиа', href: '/media' }),
  NavItem({ icon: Widget, label: 'Виджеты', href: '/widgets' }),
  NavItem({ icon: Palette, label: 'Темы', href: '/themes' }),

  NavSection({ label: 'Финансы' }),
  NavItem({ icon: Wallet, label: 'Финансы', href: '/finance' }),

  NavSection({ label: 'Система' }),
  NavItem({ icon: Users, label: 'Пользователи', href: '/users' }),
  NavItem({ icon: Settings, label: 'Настройки', href: '/settings' }),
  NavItem({ icon: Terminal, label: 'Логи', href: '/logs' }),
  NavItem({ icon: Monitor, label: 'Диагностика', href: '/diagnostics' }),
];
```

Иконки — из Lucide React (те же что в remnawave, уже есть в `lucide-react` пакете).

### 4.4 Роутер (App.tsx)

```tsx
// src/App.tsx
const routes = [
  // Публичные
  { path: '/login', component: lazy(() => import('./pages/Login')) },
  { path: '/', component: lazy(() => import('./pages/Dashboard')) },

  // Сайт
  { path: '/posts', component: lazy(() => import('./pages/PostsList')) },
  { path: '/posts/create', component: lazy(() => import('./pages/PostEdit')) },
  { path: '/posts/:id', component: lazy(() => import('./pages/PostEdit')) },
  { path: '/posts/categories', component: lazy(() => import('./pages/CategoriesList')) },
  { path: '/pages', component: lazy(() => import('./pages/PagesList')) },
  { path: '/pages/create', component: lazy(() => import('./pages/PageEdit')) },
  { path: '/pages/:id', component: lazy(() => import('./pages/PageEdit')) },

  // Медиа, меню, виджеты, темы
  { path: '/media', component: lazy(() => import('./pages/MediaList')) },
  { path: '/menus', component: lazy(() => import('./pages/MenusList')) },
  { path: '/menus/:id', component: lazy(() => import('./pages/MenuEdit')) },
  { path: '/widgets', component: lazy(() => import('./pages/WidgetsList')) },
  { path: '/themes', component: lazy(() => import('./pages/ThemeManager')) },

  // Финансы
  { path: '/finance', component: lazy(() => import('./pages/Finance')) },

  // Система
  { path: '/users', component: lazy(() => import('./pages/UsersList')) },
  { path: '/users/:id', component: lazy(() => import('./pages/UserEdit')) },
  { path: '/settings', component: lazy(() => import('./pages/Settings')) },
  { path: '/logs', component: lazy(() => import('./pages/LogsViewer')) },
  { path: '/diagnostics', component: lazy(() => import('./pages/Diagnostics')) },

  // 404
  { path: '*', component: lazy(() => import('./pages/NotFound')) },
];
```

### 4.5 API-клиент (client.ts)

```ts
// src/api/client.ts — ПЕРЕПИСАТЬ ПОЛНОСТЬЮ
// Вместо FastAPI → PHP API

import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Interceptor: добавляем Bearer token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Interceptor: 401 → редирект на логин
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### 4.6 Api-модули для каждой сущности

Каждый модуль — тонкая обёртка над Axios с типами.

```ts
// src/api/posts.ts
import { api } from './client';

export interface Post {
  id: number;
  title: string;
  slug: string;
  content: string;
  status: 'published' | 'draft' | 'archived';
  category_id?: number;
  meta_description?: string;
  created_at: string;
  updated_at: string;
}

export const postsApi = {
  list: (params?: { page?: number; per_page?: number; sort?: string; dir?: string; search?: string }) =>
    api.get('/posts', { params }).then(r => r.data),

  get: (id: number) =>
    api.get(`/posts/${id}`).then(r => r.data),

  create: (data: Partial<Post>) =>
    api.post('/posts', data).then(r => r.data),

  update: (id: number, data: Partial<Post>) =>
    api.post(`/posts/${id}`, data).then(r => r.data),

  delete: (id: number) =>
    api.delete(`/posts/${id}`).then(r => r.data),
};
```

Аналогично для всех сущностей:
- `pages.ts`, `users.ts`, `media.ts`, `menus.ts`, `widgets.ts`
- `settings.ts`, `themes.ts`, `logs.ts`, `finance.ts`, `dashboard.ts`

### 4.7 Страницы — шаблон реализации

Каждая страница следует одному паттерну:

```tsx
// src/pages/НоваяСтраница.tsx
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '../components/ui/table';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
// ... остальные импорты

export default function PageName() {
  // 1. Данные через API
  const { data } = await api.get('/api/...');

  // 2. UI через shadcn/ui компоненты
  return (
    <div>
      <Card>
        <CardHeader>
          <CardTitle>Заголовок</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>...</Table>
        </CardContent>
      </Card>
    </div>
  );
}
```

**ВАЖНО:** Всегда использовать shadcn/ui компоненты из `src/components/ui/`.
НЕ писать сырой HTML/CSS. НЕ добавлять стили через className="..." вручную.

### 4.8 План переноса страниц (порядок имеет значение)

| Очередь | Страница | API готов? | Зависит от | Время |
|---------|----------|-----------|------------|-------|
| **1** | **Login** | ✅ (PHP) | Нет | 2-4 ч |
| **2** | **Dashboard** | ✅ (PHP) | Login | 3-5 ч |
| **3** | **Finance** | ✅ (PHP) | Нет | 6-8 ч |
| **4** | **Diagnostics** | ✅ (PHP) | Нет | 3-4 ч |
| **5** | **LogsViewer** | ⚠️ (Фаза 0 — API дописать) | Фаза 0 | 4-6 ч |
| **6** | **PostsList** | ✅ (PHP) | Нет | 4-6 ч |
| **7** | **PostEdit** | ✅ (PHP) | PostsList | 8-12 ч |
| **8** | **PagesList** | ✅ (PHP) | Нет | 3-4 ч |
| **9** | **PageEdit** | ✅ (PHP) | PagesList | 4-6 ч |
| **10** | **UsersList** | ✅ (PHP) | Нет | 3-4 ч |
| **11** | **UserEdit** | ✅ (PHP) | UsersList | 4-6 ч |
| **12** | **CategoriesList** | ✅ (PHP) | Нет | 2-3 ч |
| **13** | **WidgetsList** | ⚠️ (Фаза 0 — API дописать) | Фаза 0 | 2-3 ч |
| **14** | **MenusList + MenuEdit** | ⚠️ (Фаза 0 — API дописать) | Фаза 0 | 4-6 ч |
| **15** | **Settings** | ⚠️ (Фаза 0 — API дописать) | Нет | 3-5 ч |
| **16** | **MediaList** | ⚠️ (Фаза 0 — API дописать) | Фаза 0 | 3-4 ч |
| **17** | **ThemeManager** | **ТОЛЬКО НАСТРОЙКИ АКТИВНОЙ ТЕМЫ** (загрузку и переключение не делать) | — | 2-3 ч |

**Правило:** Страницы из очереди N можно делать только после очереди N-1.
Исключение: Finance, Diagnostics, Logs можно делать параллельно (у них нет зависимостей).

### 4.9 Гибридный режим — кнопка «Новая панель»

Пока не все страницы React готовы, работает кнопка переключения в настройках.

**Как работает:**
1. В старой PHP-админке (Настройки) есть переключатель «Новая панель»
2. Включил → пользователь видит React SPA
3. Выключил → работает старая PHP-админка
4. Настройка хранится в БД

**Реализация (кнопка в PHP):**
```php
// admin/templates/settings/index.php
<label>Новая панель управления</label>
<label><input type="checkbox" id="use-react-admin" 
       <?= ($prefs['use_react_admin'] ?? false) ? 'checked' : '' ?>></label>
```

**Реализация (PHP Router проверяет и редиректит):**
```php
// PHP Router
$router->get('admin', function() {
    Auth::requireAdmin();
    $prefs = getUserPrefs(Auth::id());
    if ($prefs['use_react_admin'] ?? false) {
        // Кидаем на React SPA
        header('Location: /');
        http_response_code(302);
        exit;
    }
    // Иначе — рендерим PHP шаблон
});
```

### Чеклист Фазы 1:
- [ ] Скопирован React-проект из remnawave
- [ ] Удалены все Remnawave-страницы
- [ ] Оставлены: Layout, Sidebar, Header, Login, Dashboard, Settings, NotFound
- [ ] Sidebar переписан под CMS-разделы
- [ ] API-клиент переписан под PHP
- [ ] Login работает (подключён к /api/auth/login)
- [ ] Dashboard работает (подключён к /api/dashboard/stats)
- [ ] Finance работает (подключён к /api/finance)
- [ ] Diagnostics работает (подключён к /api/diagnostics)
- [ ] LogsViewer (нужен API из Фазы 0)
- [ ] PostsList + PostEdit
- [ ] PagesList + PageEdit
- [ ] UsersList + UserEdit
- [ ] CategoriesList
- [ ] MediaList (нужен API из Фазы 0)
- [ ] MenusList + MenuEdit (нужен API из Фазы 0)
- [ ] WidgetsList (нужен API из Фазы 0)
- [ ] ThemeManager (только настройки; нужен API из Фазы 0)
- [ ] Settings (нужен API из Фазы 0)
- [ ] React SPA работает на dev-сервере
- [ ] React SPA задеплоен на продакшен
- [ ] Гибридный режим работает (кнопка «Новая панель»)
- [ ] Все страницы PHP-админки доступны через запасной вариант

---

## 5. ФАЗА 2: FASTAPI (1-2 месяца, обязательно для интеграции с Remnawave)

**Цель:** Заменить PHP-API на FastAPI, чтобы иметь единый Python-стек с remnawave.

### Почему это важно

FastAPI = тот же фреймворк, что используется в remnawave-admin-main. Когда CMS переедет на FastAPI:

1. Можно использовать готовые модули из remnawave (авторизация, JWT, RBAC, плагины, аудит)
2. React-фронтенд НЕ МЕНЯЕТСЯ — он по-прежнему стучится на `/api/posts`, `/api/users` и т.д.
3. В будущем можно объединить бэкенды CMS и Remnawave в один инстанс FastAPI
4. PHP полностью уходит из админки

### Как устроен FastAPI в remnawave

```
remnawave-admin-main/web/backend/
├── api/v2/         # API endpoints (версионированные)
├── api/v3/         # Новая версия API
├── core/           # 40 модулей (config, security, rbac, auth, и т.д.)
├── schemas/        # Pydantic модели (вход/выход данных)
├── main.py         # Точка входа
└── tests/          # Тесты
```

Наш CMS-бэкенд будет зеркалить эту структуру:

```
NewWeb/backend/
├── main.py              # FastAPI приложение
├── requirements.txt     # Зависимости
├── api/
│   └── v1/              # Наша версия API
│       ├── auth.py      # /api/auth/*
│       ├── posts.py     # /api/posts/*
│       ├── pages.py     # /api/pages/*
│       ├── users.py     # /api/users/*
│       ├── media.py     # /api/media/*
│       ├── menus.py     # /api/menus/*
│       ├── widgets.py   # /api/widgets/*
│       ├── settings.py  # /api/settings/*
│       ├── themes.py    # /api/themes/*
│       ├── logs.py      # /api/logs/*
│       ├── finance.py   # /api/finance/*
│       └── dashboard.py # /api/dashboard/*
├── core/
│   ├── config.py        # Настройки (из .env)
│   ├── security.py      # JWT (совместимый с PHP)
│   ├── rbac.py          # Права доступа (когда понадобятся)
│   └── database.py      # PostgreSQL (SQLAlchemy async)
├── models/              # SQLAlchemy модели (таблицы БД)
│   ├── post.py
│   ├── page.py
│   ├── user.py
│   ├── media.py
│   ├── menu.py
│   ├── widget.py
│   ├── setting.py
│   ├── log.py
│   └── finance.py
└── schemas/             # Pydantic (что приходит и уходит в JSON)
    ├── post.py
    ├── page.py
    └── ...
```

### Процесс миграции (эндпоинт за эндпоинтом)

1. Берём PHP-эндпоинт (например `/api/posts`)
2. Пишем FastAPI-аналог: те же поля, тот же формат JSON-ответа
3. Тестируем (curl, Postman или сам React-фронтенд)
4. Меняем nginx: `/api/posts` теперь идёт в FastAPI вместо PHP
5. Убеждаемся, что React-фронтенд работает без изменений
6. PHP-версию помечаем как `// DEPRECATED`, удаляем позже

**Формат ответа строго как в PHP:**
```json
{
  "success": true,
  "data": [
    { "id": 1, "title": "...", "status": "published", "created_at": "2026-01-01" }
  ]
}
```

**Имена полей совпадают с PHP** — `created_at`, не `createdAt`. React-фронтенд не должен замечать, что бэкенд сменился.

### Когда FastAPI полностью готов

- Все `/api/*` эндпоинты работают через FastAPI
- PHP в админке больше не используется
- Можно подключить remnawave-модули (аудит, плагины, RBAC)
- PHP остаётся только для публичного сайта

### Можно ли остановиться на полпути?

Да. Если перевели только часть эндпоинтов — они идут через FastAPI, остальные через PHP. React работает в обоих случаях. Останавливаться можно на любом этапе.

### Чеклист Фазы 2:
- [ ] FastAPI сервер запущен
- [ ] SQLAlchemy модели для CMS
- [ ] Миграции БД через Alembic
- [ ] JWT auth в FastAPI (совместимый с PHP)
- [ ] `/api/auth/*` migrated to FastAPI
- [ ] `/api/posts/*` migrated to FastAPI
- [ ] `/api/pages/*` migrated to FastAPI
- [ ] `/api/categories/*` migrated to FastAPI
- [ ] `/api/users/*` migrated to FastAPI
- [ ] `/api/media/*` migrated to FastAPI
- [ ] `/api/menus/*` migrated to FastAPI
- [ ] `/api/widgets/*` migrated to FastAPI
- [ ] `/api/settings` migrated to FastAPI
- [ ] `/api/themes/settings` migrated to FastAPI
- [ ] `/api/logs/*` migrated to FastAPI
- [ ] `/api/finance/*` migrated to FastAPI
- [ ] `/api/dashboard/stats` migrated to FastAPI
- [ ] `/api/preferences/*` migrated to FastAPI
- [ ] PHP-API полностью отключён (или весь трафик на FastAPI)

---

## 6. ССЫЛКИ И РЕСУРСЫ

| Ресурс | Путь |
|--------|------|
| Исходный remnawave-фронтенд | `C:\Users\Andre\Desktop\VPN\remnawave-admin-main\web\frontend\` |
| Наш PHP-бэкенд | `C:\Users\Andre\Desktop\VPN\NewWeb\` |
| PHP-маршруты (все API) | `core/routes.php` |
| Дизайн-система PHP | `docs/decisions/ADR-001-panel-design-system.md` |
| Наш CSS (10 файлов) | `public/css/panel/*.css` |
| Полное описание проекта | `PROJECT.md` |

### Ключевые файлы remnawave для копирования:
| Файл | Назначение |
|------|-----------|
| `src/index.css` | **Главный — вся дизайн-система** |
| `src/components/layout/Layout.tsx` | Layout |
| `src/components/layout/Sidebar.tsx` | Sidebar |
| `src/components/layout/Header.tsx` | Header |
| `src/components/layout/PageBreadcrumbs.tsx` | Breadcrumbs |
| `src/components/ui/*.tsx` | Все 23 shadcn/ui компонента |
| `src/components/AppearancePanel.tsx` | Панель настройки вида |
| `src/components/CommandPalette.tsx` | Cmd+K |
| `src/components/ConfirmDialog.tsx` | Подтверждение |
| `src/components/EmptyState.tsx` | Пустое состояние |
| `src/components/ErrorBoundary.tsx` | Отлов ошибок |
| `src/store/useAppearanceStore.ts` | Состояние темы |
| `src/i18n.ts` | Локализация |
| `src/lib/useFormatters.ts` | Форматирование |
| `src/lib/utils.ts` | Утилиты |
| `tailwind.config.js` | Конфиг Tailwind |
| `vite.config.ts` | Сборщик |
| `index.html` | Точка входа |

---

## 7. АРХИТЕКТУРНАЯ ДИАГРАММА

```
┌─────────────────────────────────────────────────────────┐
│                    Браузер пользователя                    │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              React SPA (админка)                   │   │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────────────┐   │   │
│  │  │ Layout  │ │ Sidebar  │ │     Страницы       │   │   │
│  │  │ Header  │ │ Cmd+K    │ │ Posts, Pages, ...  │   │   │
│  │  └─────────┘ └──────────┘ └──────────────────┘   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │          Публичный сайт (PHP SSR)                   │   │
│  │  Лендинг, блог, страницы                           │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────┬──────────────────────────────────────────┘
               │ HTTP
               ▼
┌─────────────────────────────────────────────────────────┐
│                    nginx (85.198.99.102)                   │
│                                                         │
│  /api/* → ──────────────────────────────────────────┐   │
│           │  PHP API (Фаза 1) / FastAPI (Фаза 2)    │   │
│           │  /api/auth/login                         │   │
│           │  /api/posts, /api/pages, /api/users...   │   │
│           │  /api/finance/*, /api/diagnostics/*      │   │
│           └──────────────────┬───────────────────────┘   │
│                              │                           │
│  /admin/* → ─────────────────┼─────────────────────┐   │
│           │  React SPA (dist/)                    │   │
│           │  PHP SSR (fallback, кука)             │   │
│           └───────────────────────────────────────┘   │
│                                                         │
│  / → ───────────────────────────────────────────────┐   │
│     │  Публичный сайт (PHP SSR)                    │   │
│     │  Тема HexaVeil (лендинг + блог)              │   │
│     └──────────────────────────────────────────────┘   │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│                   PostgreSQL (один инстанс)               │
│                                                         │
│  Таблицы CMS: posts, pages, users, media, menus,        │
│  widgets, settings, categories, logs, user_preferences   │
└─────────────────────────────────────────────────────────┘
```

---

## 8. ТИПОВЫЕ ОШИБКИ И ИХ РЕШЕНИЯ

| Ошибка | Причина | Решение |
|--------|---------|---------|
| React не видит API | CORS не настроен | Проверить `apiCorsHeaders()` в PHP |
| 401 на API | Нет/протух токен | Перелогиниться |
| Страница не загружается | Не прописана в App.tsx | Добавить маршрут |
| Съехала вёрстка | Не подключен tailwind.css | `@import 'tailwindcss/base'` в index.css |
| Пропали иконки | Не установлен `lucide-react` | `npm install lucide-react` |
| Glass-эффекты не работают | Нет атрибутов на `<html>` | `data-theme data-mode data-density` |
| React не стартует | Неправильный vite.config | Проверить proxy на /api |
| Не сохраняются настройки вида | panel.js конфликтует | У panel.js должен быть режим "только PHP" |
| Страница 404 в React | Нет lazy-импорта | Проверить `component: lazy(() => import(...))` |

---

## 9. КОМАНДЫ ДЛЯ РАЗРАБОТКИ

```bash
# React dev server (порт 3000 с прокси на PHP)
cd admin-react
npm install
npm run dev

# Сборка React для прода
npm run build
# результат: admin-react/dist/

# FastAPI dev server
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# PHP (как есть)
docker-compose up -d   # или php -S 0.0.0.0:3000
```

---

## 10. ИТОГ

| Фаза | Результат | Время | Когда делать |
|------|-----------|-------|-------------|
| **0** | PHP API готов к React | 2-3 дня | Сейчас |
| **1** | React SPA c 100% визуалом remnawave | 2-4 недели | После Фазы 0 |
| **2** | FastAPI вместо PHP (интеграция с Remnawave) | 1-2 месяца | После Фазы 1 |

**После Фазы 1:**
- Админка выглядит как remnawave (100%) — React SPA
- Работает через PHP-бэкенд
- Можно переключаться между React и PHP
- Все страницы работают
- Промежуточный этап, можно пользоваться

**После Фазы 2:**
- Админка выглядит как remnawave (100%) — React SPA
- Работает через FastAPI — тот же стек что и в remnawave
- PHP полностью ушёл из админки
- Единый Python-стек с remnawave
- Лёгкий путь к полной интеграции (общие модули, авторизация, плагины)

**Главное правило:** На каждом этапе прод работает, данные целы, админкой можно пользоваться.
Ничего не ломается, ничего не удаляется без необходимости.