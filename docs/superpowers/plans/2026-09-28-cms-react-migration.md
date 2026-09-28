# CMS React Admin Migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Migrate the PHP-rendered admin panel to a React SPA at `hexaveil.xyz/admin`, pixel-perfect copy of Remnawave-admin visual design.

**Architecture:** Hybrid — public site stays PHP (SEO). Admin becomes a separate React SPA (Vite + TypeScript + Tailwind + Radix UI) inside the same Docker container. React talks to PHP via JSON API (`/api/*`) with JWT auth. Visual components copied from `remnawave-admin-main/web/frontend/`.

**Tech Stack:**
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + Radix UI + Zustand + TanStack Query
- Backend: PHP 8.1 (existing) + new JSON API endpoints
- Auth: JWT (firebase/php-jwt on PHP side, Bearer token on React side)
- Build: Vite, output to `public/cms-admin/`
- Deploy: Same Docker container, Nginx serves SPA + proxies API to PHP

## Global Constraints

- PHP 8.1+, no frameworks
- Vanilla CSS/JS (no npm on PHP side)
- Public site (`/*`) must NOT be modified
- React SPA at `/cms-admin/` during migration, later switch to `/admin/`
- JWT_SECRET must be stored in `.env` as `JWT_SECRET`
- All API responses must be JSON with `Content-Type: application/json`
- CORS headers: `Access-Control-Allow-Origin: same-origin` (not needed since same domain)
- All copied Remnawave components must be MIT-licensed (they are)

---

## File Structure

### New files to create:

```
cms-admin/                          # New React SPA project (root level)
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── tailwind.config.js
├── postcss.config.js
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css                   # Tailwind + CSS variables (copied from remnawave)
│   ├── vite-env.d.ts
│   ├── api/
│   │   ├── client.ts               # Axios client with JWT interceptor
│   │   ├── auth.ts                  # Auth API calls
│   │   ├── posts.ts                 # Posts CRUD API
│   │   ├── pages.ts                 # Pages CRUD API
│   │   ├── users.ts                 # Users CRUD API
│   │   ├── media.ts                 # Media API
│   │   ├── finance.ts               # Finance API
│   │   ├── settings.ts              # Settings API
│   │   ├── dashboard.ts             # Dashboard stats API
│   │   └── categories.ts            # Categories API
│   ├── store/
│   │   ├── authStore.ts             # JWT auth state (Zustand + localStorage)
│   │   ├── appearanceStore.ts        # Theme/mode/density (copied from remnawave)
│   │   └── permissionStore.ts        # RBAC permissions (simplified)
│   ├── config/
│   │   └── navigation.ts            # CMS admin navigation tree
│   ├── lib/
│   │   └── utils.ts                 # cn() helper (copied from remnawave)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Layout.tsx           # Copied from remnawave (mesh-bg, sidebar, header)
│   │   │   ├── Sidebar.tsx          # Copied, CMS navigation
│   │   │   ├── Header.tsx           # Copied, simplified
│   │   │   └── PageBreadcrumbs.tsx  # Copied
│   │   ├── ui/                      # 23 Radix UI components (copied from remnawave)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── input.tsx
│   │   │   ├── table.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── select.tsx
│   │   │   ├── switch.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── tooltip.tsx
│   │   │   ├── checkbox.tsx
│   │   │   ├── label.tsx
│   │   │   ├── scroll-area.tsx
│   │   │   ├── separator.tsx
│   │   │   ├── skeleton.tsx
│   │   │   ├── sonner.tsx
│   │   │   ├── textarea.tsx
│   │   │   ├── popover.tsx
│   │   │   ├── command.tsx
│   │   │   ├── alert-dialog.tsx
│   │   │   └── breadcrumb.tsx
│   │   ├── AppearancePanel.tsx      # Copied from remnawave
│   │   ├── CommandPalette.tsx       # Copied (CMS-specific search)
│   │   ├── EmptyState.tsx           # Copied
│   │   ├── ConfirmDialog.tsx        # Copied
│   │   └── PermissionGate.tsx       # Copied
│   └── pages/
│       ├── Login.tsx
│       ├── Dashboard.tsx
│       ├── NotFound.tsx
│       ├── posts/
│       │   ├── PostList.tsx
│       │   ├── PostForm.tsx
│       │   └── Categories.tsx
│       ├── pages/
│       │   ├── PageList.tsx
│       │   └── PageForm.tsx
│       ├── users/
│       │   ├── UserList.tsx
│       │   └── UserForm.tsx
│       ├── media/
│       │   └── MediaLibrary.tsx
│       ├── finance/
│       │   ├── FinanceDashboard.tsx
│       │   └── FinanceSettings.tsx
│       └── settings/
│           └── SettingsPage.tsx

core/
├── JWTAuth.php                     # NEW: JWT generation + verification
└── routes.php                       # MODIFY: add /api/* routes

config/
└── config.php                       # MODIFY: add JWT_SECRET constant

.docker/nginx/
└── default.conf                     # MODIFY: add /cms-admin/ location
```

## Task Structure

Each task produces independently testable work. Tasks are ordered by dependency.

---

### Task 0: PHP JWT Auth Foundation

**Files:**
- Create: `core/JWTAuth.php`
- Modify: `config/config.php` (lines 40-43)
- Modify: `core/routes.php` (before admin routes, add API auth routes)

**Interfaces:**
- Consumes: `Auth::attempt()`, `Auth::user()` from existing PHP
- Produces: `JWTAuth::generateJWT(array $payload): string`, `JWTAuth::verifyJWT(string $token): ?array`, `POST /api/auth/login` returns JSON, `GET /api/auth/me` returns JSON

- [ ] **Step 1: Create `core/JWTAuth.php`**

```php
<?php
/**
 * JWT implementation for CMS admin API
 * HMAC-SHA256 signing, no external dependencies
 */
class JWTAuth
{
    private static function getSecret(): string
    {
        return defined('JWT_SECRET') ? JWT_SECRET : getenv('JWT_SECRET');
    }

    /**
     * Base64 URL-safe encode
     */
    private static function base64UrlEncode(string $data): string
    {
        return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
    }

    /**
     * Base64 URL-safe decode
     */
    private static function base64UrlDecode(string $data): string
    {
        return base64_decode(strtr($data, '-_', '+/'));
    }

    /**
     * Generate a JWT token
     * @param array $payload Claims (user_id, role, exp, etc.)
     * @return string JWT string
     */
    public static function generateJWT(array $payload): string
    {
        $header = self::base64UrlEncode(json_encode(['typ' => 'JWT', 'alg' => 'HS256']));
        $payload['iat'] = $payload['iat'] ?? time();
        $payload['exp'] = $payload['exp'] ?? time() + 86400; // 24 hours default
        $payloadEncoded = self::base64UrlEncode(json_encode($payload));
        $signature = self::base64UrlEncode(
            hash_hmac('sha256', "$header.$payloadEncoded", self::getSecret(), true)
        );
        return "$header.$payloadEncoded.$signature";
    }

    /**
     * Verify and decode a JWT token
     * @param string $token JWT string
     * @return array|null Payload if valid, null if expired/invalid
     */
    public static function verifyJWT(string $token): ?array
    {
        $parts = explode('.', $token);
        if (count($parts) !== 3) return null;

        [$header, $payload, $signature] = $parts;

        // Verify signature
        $expectedSig = self::base64UrlEncode(
            hash_hmac('sha256', "$header.$payload", self::getSecret(), true)
        );
        if (!hash_equals($expectedSig, $signature)) return null;

        // Decode payload
        $data = json_decode(self::base64UrlDecode($payload), true);
        if (!$data || !isset($data['exp'])) return null;

        // Check expiration
        if ($data['exp'] < time()) return null;

        return $data;
    }

    /**
     * Get the authenticated user from the current request
     * @return array|null ['user_id' => int, 'role' => string] or null
     */
    public static function authenticate(): ?array
    {
        $header = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
        if (!preg_match('/^Bearer\s+(.+)$/i', $header, $matches)) return null;
        return self::verifyJWT($matches[1]);
    }

    /**
     * Require authentication for API routes. Sends 401 JSON and exits if not authenticated.
     * @return array Payload with user_id and role
     */
    public static function requireAuth(): array
    {
        $payload = self::authenticate();
        if (!$payload) {
            http_response_code(401);
            header('Content-Type: application/json');
            echo json_encode(['error' => 'Unauthorized', 'code' => 'token_invalid']);
            exit;
        }
        return $payload;
    }
}
```

- [ ] **Step 2: Add JWT_SECRET to config**

In `config/config.php`, after `APP_ENCRYPTION_KEY` line (line 40):

```php
// JWT secret for admin API authentication
define('JWT_SECRET', getenv('JWT_SECRET') ?: bin2hex(random_bytes(32)));
```

In `.env` and `.env.example`, add:
```
JWT_SECRET=your-secure-random-secret-here
```

- [ ] **Step 3: Add API auth routes to `core/routes.php`**

Add BEFORE the admin routes section (before `// Маршруты админки`):

```php
// ============================================
// API маршруты для React админки
// ============================================

$router->post('api/auth/login', function() {
    header('Content-Type: application/json');

    $body = json_decode(file_get_contents('php://input'), true);
    $login = trim($body['login'] ?? '');
    $password = $body['password'] ?? '';

    if ($login === '' || $password === '') {
        http_response_code(422);
        echo json_encode(['error' => 'Login and password required']);
        return;
    }

    // Use existing Auth system to verify credentials
    $user = Auth::attempt($login, $password);
    if (!$user) {
        http_response_code(401);
        echo json_encode(['error' => 'Invalid credentials']);
        return;
    }

    $jwt = JWTAuth::generateJWT([
        'user_id' => $user['id'],
        'username' => $user['login'],
        'role' => $user['role'],
    ]);

    echo json_encode([
        'access_token' => $jwt,
        'user' => [
            'id' => $user['id'],
            'username' => $user['login'],
            'role' => $user['role'],
        ],
    ]);
});

$router->get('api/auth/me', function() {
    header('Content-Type: application/json');
    $payload = JWTAuth::requireAuth();

    $user = new User();
    $userData = $user->getById($payload['user_id']);
    if (!$userData) {
        http_response_code(404);
        echo json_encode(['error' => 'User not found']);
        return;
    }

    echo json_encode([
        'id' => $userData['id'],
        'username' => $userData['login'],
        'role' => $userData['role'],
        'email' => $userData['email'] ?? '',
    ]);
});

$router->post('api/auth/logout', function() {
    header('Content-Type: application/json');
    // JWT is stateless — client just discards the token
    // For extra security, we could blacklist tokens here
    echo json_encode(['ok' => true]);
});
```

- [ ] **Step 4: Test JWT with curl**

```bash
# Login
curl -X POST http://localhost/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"admn","password":"Cke;bkb2Njdfhbof"}'
# Expected: {"access_token":"eyJ...", "user": {...}}

# Get me (with token)
curl http://localhost/api/auth/me \
  -H 'Authorization: Bearer eyJ...'
# Expected: {"id":1, "username":"admn", "role":"admin"}

# Without token
curl http://localhost/api/auth/me
# Expected: 401 {"error":"Unauthorized"}
```

- [ ] **Step 5: Commit**

```bash
git add core/JWTAuth.php config/config.php core/routes.php .env .env.example
git commit -m "feat: add JWT auth system for React admin API"
```

---

### Task 1: Scaffold React CMS Admin Project

**Files:**
- Create: `cms-admin/package.json`
- Create: `cms-admin/vite.config.ts`
- Create: `cms-admin/tsconfig.json`
- Create: `cms-admin/tsconfig.node.json`
- Create: `cms-admin/tailwind.config.js`
- Create: `cms-admin/postcss.config.js`
- Create: `cms-admin/index.html`
- Create: `cms-admin/src/main.tsx`
- Create: `cms-admin/src/vite-env.d.ts`
- Create: `cms-admin/src/lib/utils.ts`
- Create: `cms-admin/src/index.css`

**Interfaces:**
- Consumes: Nothing yet
- Produces: A Vite dev server that runs `npm run dev` on `:5173`, and `npm run build` outputs to `../public/cms-admin/`

- [ ] **Step 1: Create `cms-admin/package.json`**

The version pins match what Remnawave-admin uses (React 18, Vite 5, Tailwind 3).

```json
{
  "name": "hexaveil-cms-admin",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.2",
    "@tanstack/react-query": "^5.17.0",
    "zustand": "^4.4.7",
    "axios": "^1.6.5",
    "lucide-react": "^0.563.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^3.4.0",
    "class-variance-authority": "^0.7.1",
    "@radix-ui/react-avatar": "^1.1.11",
    "@radix-ui/react-dialog": "^1.1.15",
    "@radix-ui/react-dropdown-menu": "^2.1.16",
    "@radix-ui/react-label": "^2.1.8",
    "@radix-ui/react-popover": "^1.1.15",
    "@radix-ui/react-scroll-area": "^1.2.10",
    "@radix-ui/react-select": "^2.2.6",
    "@radix-ui/react-separator": "^1.1.8",
    "@radix-ui/react-slot": "^1.2.4",
    "@radix-ui/react-switch": "^1.2.6",
    "@radix-ui/react-tabs": "^1.1.13",
    "@radix-ui/react-tooltip": "^1.2.8",
    "@radix-ui/react-checkbox": "^1.3.3",
    "@radix-ui/react-alert-dialog": "^1.1.15",
    "cmdk": "^1.1.1",
    "sonner": "^2.0.7",
    "recharts": "^2.10.3",
    "date-fns": "^3.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.48",
    "@types/react-dom": "^18.2.18",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.0.11",
    "tailwindcss": "^3.4.1",
    "postcss": "^8.4.33",
    "autoprefixer": "^10.4.17"
  }
}
```

- [ ] **Step 2: Create `cms-admin/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: '/cms-admin/',
  build: {
    outDir: '../public/cms-admin',
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: Create `cms-admin/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Create `cms-admin/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Create `cms-admin/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: 'rgb(var(--primary-50) / <alpha-value>)',
          100: 'rgb(var(--primary-100) / <alpha-value>)',
          200: 'rgb(var(--primary-200) / <alpha-value>)',
          300: 'rgb(var(--primary-300) / <alpha-value>)',
          400: 'rgb(var(--primary-400) / <alpha-value>)',
          500: 'rgb(var(--primary-500) / <alpha-value>)',
          600: 'rgb(var(--primary-600) / <alpha-value>)',
          700: 'rgb(var(--primary-700) / <alpha-value>)',
          800: 'rgb(var(--primary-800) / <alpha-value>)',
          900: 'rgb(var(--primary-900) / <alpha-value>)',
        },
        dark: {
          50: '#e1e1e6',
          100: '#c4c4cc',
          200: '#a1a1aa',
          300: '#7c7c8a',
          400: '#52525b',
          500: '#3f3f46',
          600: '#323238',
          700: '#29292e',
          800: '#202024',
          900: '#121214',
        },
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 6: Create `cms-admin/postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 7: Create `cms-admin/index.html`**

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CMS Admin — HexaVeil</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 8: Create `cms-admin/src/main.tsx`**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30000,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
```

- [ ] **Step 9: Create `cms-admin/src/vite-env.d.ts`**

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 10: Create `cms-admin/src/lib/utils.ts`**

```typescript
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 11: Create `cms-admin/src/index.css` — Tailwind + CSS variables**

This will be populated in Task 2 when we copy the visual system. For now, a minimal stub:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  font-family: Inter, system-ui, -apple-system, sans-serif;
}

/* CSS variables will be populated from Remnawave theme system */
```

- [ ] **Step 12: Build test**

```bash
cd cms-admin
npm install
npm run build
# Expected: dist/ created with index.html, assets/*
```

- [ ] **Step 13: Commit**

```bash
git add cms-admin/
git commit -m "feat: scaffold React CMS admin project"
```

---

### Task 2: Copy Remnawave Visual System

**Files:**
- Create: `cms-admin/src/store/appearanceStore.ts` (copy from remnawave)
- Create: `cms-admin/src/components/ui/*.tsx` (copy 23 component files)
- Create: `cms-admin/src/components/AppearancePanel.tsx` (copy)
- Modify: `cms-admin/src/index.css` (add CSS variables + Tailwind theme)
- Create: `cms-admin/src/components/layout/Layout.tsx` (copy, adapt)
- Create: `cms-admin/src/components/layout/Sidebar.tsx` (copy, use CMS nav)
- Create: `cms-admin/src/components/layout/Header.tsx` (copy, simplify)
- Create: `cms-admin/src/components/layout/PageBreadcrumbs.tsx` (copy)
- Create: `cms-admin/src/config/navigation.ts` (CMS-specific)
- Create: `cms-admin/src/App.tsx` (minimal shell with routing)

- [ ] **Step 1: Copy `useAppearanceStore.ts` from remnawave**

Source: `remnawave-admin-main/web/frontend/src/store/useAppearanceStore.ts`

Change the localStorage key from `remnawave-appearance` to `hexaveil-appearance`.

- [ ] **Step 2: Copy all 23 UI components**

Source: `remnawave-admin-main/web/frontend/src/components/ui/*.tsx`

Copy each file verbatim. These are MIT-licensed shadcn/ui components.

- [ ] **Step 3: Copy `AppearancePanel.tsx`**

Source: `remnawave-admin-main/web/frontend/src/components/AppearancePanel.tsx`

- [ ] **Step 4: Create `cms-admin/src/config/navigation.ts`**

This replaces the Remnawave navigation with CMS-specific navigation:

```typescript
import {
  LayoutDashboard, FileText, Files, Users, Image,
  Settings, Menu, Grid3x3, Wallet, ScrollText,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  type?: 'item'
  name: string
  href: string
  icon: LucideIcon
  permission?: { resource: string; action: string } | null
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

export type NavigationEntry = NavItem | NavGroup | NavSection

const navigation: NavigationEntry[] = [
  { type: 'section', name: 'Основное' },
  {
    type: 'item', name: 'Дашборд', href: '/',
    icon: LayoutDashboard,
  },
  { type: 'section', name: 'Контент' },
  {
    type: 'group', name: 'Посты', icon: FileText,
    items: [
      { name: 'Все посты', href: '/posts', icon: FileText },
      { name: 'Категории', href: '/posts/categories', icon: Grid3x3 },
    ],
  },
  {
    type: 'item', name: 'Страницы', href: '/pages',
    icon: Files,
  },
  {
    type: 'item', name: 'Медиа', href: '/media',
    icon: Image,
  },
  {
    type: 'item', name: 'Меню', href: '/menus',
    icon: Menu,
  },
  {
    type: 'item', name: 'Виджеты', href: '/widgets',
    icon: Grid3x3,
  },
  { type: 'section', name: 'Система' },
  {
    type: 'item', name: 'Пользователи', href: '/users',
    icon: Users,
  },
  {
    type: 'item', name: 'Финансы', href: '/finance',
    icon: Wallet,
  },
  {
    type: 'item', name: 'Логи', href: '/logs',
    icon: ScrollText,
  },
  {
    type: 'item', name: 'Настройки', href: '/settings',
    icon: Settings,
  },
]

export default navigation
```

- [ ] **Step 5: Create `App.tsx` with routing**

```tsx
import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/layout/Layout'

// Eager pages
import Login from './pages/Login'

// Lazy pages
const Dashboard = lazy(() => import('./pages/Dashboard'))

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return (
    <BrowserRouter basename="/cms-admin">
      <Routes>
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/" replace /> : <Login />
        } />
        <Route path="/*" element={
          <ProtectedRoute>
            <Layout>
              <Suspense fallback={null}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="*" element={<div>Page not found</div>} />
                </Routes>
              </Suspense>
            </Layout>
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 6: Copy `Layout.tsx`** from remnawave, adapt to use CMS navigation and remove WebSocket reference (not needed initially).

- [ ] **Step 7: Copy `Sidebar.tsx`** from remnawave, adapt to use `@/config/navigation` (CMS nav) instead of `@/config/navigation` (Remnawave nav). Remove plugin references.

- [ ] **Step 8: Copy `Header.tsx`** from remnawave, simplify — remove i18n, remove notifications API calls (stub them).

- [ ] **Step 9: Copy `PageBreadcrumbs.tsx`** from remnawave.

- [ ] **Step 10: Copy mesh-gradient CSS classes into `index.css`**

- [ ] **Step 11: Build test**

```bash
cd cms-admin
npm run build
# Expected: builds successfully, no TS errors
```

- [ ] **Step 12: Commit**

```bash
git add cms-admin/
git commit -m "feat: copy Remnawave visual system (UI library + appearance store + layout)"
```

---

### Task 3: JWT Auth Store + Login Page

**Files:**
- Create: `cms-admin/src/store/authStore.ts`
- Create: `cms-admin/src/api/client.ts`
- Create: `cms-admin/src/api/auth.ts`
- Create: `cms-admin/src/pages/Login.tsx`
- Modify: `cms-admin/src/App.tsx` (ensure login routing)

- [ ] **Step 1: Create `cms-admin/src/api/client.ts`**

Copy from `remnawave-admin-main/web/frontend/src/api/client.ts`, but:
- Change `baseURL` to `''` (relative, same-domain)
- Remove WebSocket and i18n references
- Simplify refresh logic

```typescript
import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const client = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/cms-admin/login'
    }
    return Promise.reject(error)
  }
)

export default client
```

- [ ] **Step 2: Create `cms-admin/src/store/authStore.ts`**

Simplified version of Remnawave's authStore. JWT-based, persisted to localStorage.

```typescript
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import client from '../api/client'

interface User {
  id: number
  username: string
  role: string
  email?: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (login: string, password: string) => Promise<void>
  logout: () => void
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (login: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const { data } = await client.post('/api/auth/login', { login, password })
          set({
            user: data.user,
            accessToken: data.access_token,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error: any) {
          const message = error.response?.data?.error || 'Login failed'
          set({ isLoading: false, error: message })
          throw new Error(message)
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          error: null,
        })
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'hexaveil-cms-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
```

- [ ] **Step 3: Create `cms-admin/src/api/auth.ts`**

```typescript
import client from './client'

export const authApi = {
  login: (login: string, password: string) =>
    client.post('/api/auth/login', { login, password }),
  me: () => client.get('/api/auth/me'),
  logout: () => client.post('/api/auth/logout'),
}
```

- [ ] **Step 4: Create `cms-admin/src/pages/Login.tsx`**

Copy from Remnawave's Login.tsx, simplify — no Telegram login, no 2FA, just login/password form with glass effect.

```tsx
import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { LogIn, Eye, EyeOff } from 'lucide-react'

export default function Login() {
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const { login: authLogin, isLoading, error } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await authLogin(login, password)
      navigate('/')
    } catch {}
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative mesh-bg">
      <div className="mesh-layer mesh-layer--1" />
      <div className="mesh-layer mesh-layer--2" />
      <div className="mesh-layer mesh-layer--3" />
      <div className="mesh-layer mesh-layer--4" />
      <div className="mesh-layer mesh-layer--5" />

      <div className="relative z-10 w-full max-w-md px-4">
        <div className="glass-card rounded-2xl p-8 shadow-2xl border border-[var(--glass-border)] backdrop-blur-2xl">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-white">CMS Admin</h1>
            <p className="text-sm text-muted-foreground mt-1">HexaVeil</p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Логин</label>
              <input
                type="text"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                className="w-full h-11 px-4 rounded-xl bg-[var(--glass-bg)] border border-[var(--glass-border)] text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500/50 transition-all"
                placeholder="Введите логин"
                required
              />
            </div>
            <div className="relative">
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Пароль</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-11 px-4 pr-12 rounded-xl bg-[var(--glass-bg)] border border-[var(--glass-border)] text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500/50 transition-all"
                  placeholder="Введите пароль"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-11 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-medium transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <><LogIn className="w-4 h-4" /> Войти</>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Nginx config — add `/cms-admin/` SPA routing**

In `.docker/nginx/default.conf`, after `location ~ \.php$` block, add:

```nginx
# React CMS Admin SPA
location /cms-admin/ {
    alias /var/www/html/public/cms-admin/;
    try_files $uri $uri/ /cms-admin/index.html;
}
```

- [ ] **Step 6: Build + test login flow**

```bash
cd cms-admin && npm run build
# Restart Docker containers
docker compose restart web
# Open http://localhost/cms-admin/login
```

- [ ] **Step 7: Verify Login → Dashboard redirect works**

1. Open `/cms-admin/login` — should see glass login form
2. Enter `admn` / `Cke;bkb2Njdfhbof` — should redirect to `/cms-admin/`
3. Check localStorage for `hexaveil-cms-auth` token
4. Open `/cms-admin/` directly (authenticated) — should show dashboard

- [ ] **Step 8: Commit**

```bash
git add cms-admin/src/store/authStore.ts cms-admin/src/api/ cms-admin/src/pages/Login.tsx .docker/nginx/default.conf
git commit -m "feat: add JWT auth store and login page"
```

---

### Task 4: Dashboard Page

**Files:**
- Create: `cms-admin/src/pages/Dashboard.tsx`
- Create: `cms-admin/src/api/dashboard.ts`
- Modify: `core/routes.php` (add `/api/dashboard/stats`)
- Modify: `cms-admin/src/App.tsx` (add lazy import)

- [ ] **Step 1: Create PHP endpoint in `core/routes.php`**

```php
$router->get('api/dashboard/stats', function() {
    header('Content-Type: application/json');
    JWTAuth::requireAuth();

    $post = new Post();
    $category = new Category();
    $user = new User();
    $comment = new Comment();

    echo json_encode([
        'stats' => [
            'posts' => $post->getCount(),
            'comments' => $comment->getCountByStatus('pending'),
            'users' => $user->getCount(),
            'categories' => $category->getCount(),
        ],
        'recentPosts' => $post->getRecent(5),
    ]);
});
```

- [ ] **Step 2: Create `cms-admin/src/api/dashboard.ts`**

```typescript
import client from './client'

export interface DashboardStats {
  posts: number
  comments: number
  users: number
  categories: number
}

export interface RecentPost {
  id: number
  title: string
  slug: string
  created_at: string
  status: string
}

export interface DashboardData {
  stats: DashboardStats
  recentPosts: RecentPost[]
}

export const dashboardApi = {
  getStats: () => client.get<DashboardData>('/api/dashboard/stats'),
}
```

- [ ] **Step 3: Create `cms-admin/src/pages/Dashboard.tsx`**

Copy visual style from Remnawave's Dashboard.tsx, but use CMS stats. Four glass stat cards + recent posts table.

- [ ] **Step 4: Build + test dashboard**

```bash
cd cms-admin && npm run build
# Open /cms-admin — should show dashboard with real stats from PHP
```

- [ ] **Step 5: Commit**

```bash
git add cms-admin/src/pages/Dashboard.tsx cms-admin/src/api/dashboard.ts core/routes.php
git commit -m "feat: add dashboard page with CMS stats"
```

---

### Task 5: Posts List + Categories

**Files:**
- Create: `cms-admin/src/api/posts.ts`
- Create: `cms-admin/src/api/categories.ts`
- Create: `cms-admin/src/pages/posts/PostList.tsx`
- Create: `cms-admin/src/pages/posts/Categories.tsx`
- Modify: `core/routes.php` (add `/api/posts/*`, `/api/categories/*`)
- Modify: `cms-admin/src/App.tsx` (add post routes)
- Modify: `cms-admin/src/config/navigation.ts` (already has Posts)

- [ ] **Step 1: Create PHP API endpoints in `core/routes.php`**

Add after JWT auth check:

```php
// API: Posts CRUD
$router->get('api/posts', function() {
    header('Content-Type: application/json');
    JWTAuth::requireAuth();
    $post = new Post();
    echo json_encode($post->getAll());
});

$router->get('api/posts/{id}', function($id) {
    header('Content-Type: application/json');
    JWTAuth::requireAuth();
    $post = new Post();
    $data = $post->getById((int)$id);
    echo json_encode($data ?: ['error' => 'Not found']);
});

$router->post('api/posts', function() {
    header('Content-Type: application/json');
    JWTAuth::requireAuth();
    // Create post from JSON body
});

// API: Categories CRUD
$router->get('api/categories', function() {
    header('Content-Type: application/json');
    JWTAuth::requireAuth();
    $cat = new Category();
    echo json_encode($cat->getAll());
});
```

(Full CRUD endpoints to be detailed during implementation.)

- [ ] **Step 2: Create React PostList page** with DataGrid (copied Remnawave table style), status badges, kebab menu.

- [ ] **Step 3: Create React Categories page** as modal/sidebar panel inside Posts section.

- [ ] **Step 4: Add routing in App.tsx** for `/posts` and `/posts/categories`.

- [ ] **Step 5: Build, test, commit**

---

### Task 6: Post Form (Create/Edit)

**Files:**
- Create: `cms-admin/src/pages/posts/PostForm.tsx`

- [ ] **Step 1: Create PostForm.tsx** with:
  - Title input
  - CKEditor 5 integration (or simple textarea for initial version)
  - Category select
  - Status toggle (draft/publish)
  - Save button → POST/PUT to `/api/posts`

- [ ] **Step 2: Add route** for `/posts/create` and `/posts/:id/edit`

- [ ] **Step 3: Build, test, commit**

---

### Task 7: Pages CRUD

**Files:**
- Create: `cms-admin/src/api/pages.ts`
- Create: `cms-admin/src/pages/pages/PageList.tsx`
- Create: `cms-admin/src/pages/pages/PageForm.tsx`
- Modify: `core/routes.php` (add `/api/pages/*`)

Similar structure to Posts. Build, test, commit.

---

### Task 8: Users CRUD

**Files:**
- Create: `cms-admin/src/api/users.ts`
- Create: `cms-admin/src/pages/users/UserList.tsx`
- Create: `cms-admin/src/pages/users/UserForm.tsx`
- Modify: `core/routes.php` (add `/api/users/*`)

---

### Task 9: Media Library

**Files:**
- Create: `cms-admin/src/api/media.ts`
- Create: `cms-admin/src/pages/media/MediaLibrary.tsx`
- Modify: `core/routes.php` (add `/api/media/*`)

---

### Task 10: Finance Dashboard

**Files:**
- Create: `cms-admin/src/api/finance.ts`
- Create: `cms-admin/src/pages/finance/FinanceDashboard.tsx`
- Create: `cms-admin/src/pages/finance/FinanceSettings.tsx`
- Modify: `core/routes.php` (add `/api/finance/*`)

Note: Finance already has API endpoints (`/admin/finance/api/*`) that can be adapted.

---

### Task 11: Settings Page

**Files:**
- Create: `cms-admin/src/api/settings.ts`
- Create: `cms-admin/src/pages/settings/SettingsPage.tsx`
- Modify: `core/routes.php` (add `/api/settings/*`)

---

### Task 12: Nginx Switch — Move React to `/admin/`

**Files:**
- Modify: `.docker/nginx/default.conf` (change `/cms-admin/` → `/admin/`)

When all pages are migrated and tested:

```nginx
# Old PHP admin — redirected to new React admin
location /admin {
    alias /var/www/html/public/cms-admin/;
    try_files $uri $uri/ /cms-admin/index.html;
}

# Keep /cms-admin/ working for backward compatibility
location /cms-admin/ {
    alias /var/www/html/public/cms-admin/;
    try_files $uri $uri/ /cms-admin/index.html;
}
```

---

## Execution Plan

| Phase | Tasks | Duration |
|-------|-------|----------|
| **Phase 0: Foundation** | Task 0 (JWT) + Task 1 (Scaffold) + Task 2 (Visual copy) | ~2-3 hours |
| **Phase 1: Auth** | Task 3 (Login) | ~1 hour |
| **Phase 2: Core** | Task 4 (Dashboard) | ~1 hour |
| **Phase 3: Content** | Tasks 5-6 (Posts) | ~2-3 hours |
| **Phase 4: Pages** | Task 7 (Pages) | ~1 hour |
| **Phase 5: System** | Tasks 8-11 (Users, Media, Finance, Settings) | ~4-6 hours |
| **Phase 6: Cutover** | Task 12 (Nginx switch to /admin/) | ~30 min |

**Total estimated: 12-16 hours of dev time** (spread across days, page by page as requested).