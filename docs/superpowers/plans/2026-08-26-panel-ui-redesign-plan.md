# План: Редизайн админ-панели CMS в стиле remnawave-admin (Итерация 1)

> **For agentic workers:** REQUIRED SUB-SKILL: `executing-plans` (или `subagent-driven-development` для параллельных задач). Шаги используют чекбоксы `- [ ]`.
> **Исходные данные:** дизайн-токены скопированы из репозитория `Case211/remnawave-admin` (`web/frontend/src/index.css`, `tailwind.config.js`). Референс: https://github.com/Case211/remnawave-admin
> **Спецификация:** `docs/superpowers/specs/2026-08-26-panel-ui-redesign-spec.md` — читать ДО начала.

## Global Constraints (нарушать нельзя)

- **HEXAVEIL НЕ ТРОГАЕМ** — ни один файл в `public/hexaveil/` и `templates/themes/hexaveil/`
- **БЛОГ НЕ ТРОГАЕМ** — `templates/themes/{default,modern,minimal}/` и `public/css/style.css`
- **МАРШРУТЫ И ЛОГИКА НЕ МЕНЯЮТСЯ** — `core/routes.php`, контроллеры, модели, POST-обработчики
- **Имена полей форм не менять** (`name="title"` остаётся `name="title"`)
- **Никаких npm/node_modules/сборщиков** — только vanilla CSS/JS/PHP
- **Никаких файлов-монстров** — каждый CSS/PHP/JS файл < 500 строк
- **Коммит после КАЖДОГО шага** (мелкие коммиты, откат через git)
- Если указано «заменить класс X на Y» — замена по всем файлам раздела

---

## Phase 1: Дизайн-система ядра (CSS-файлы)

### Task 1.1: Создать `public/css/panel/tokens.css`

**Цель:** базовые переменные — шрифты, размеры, радиусы, тени, glass/mesh-переменные. Единственный источник значений.

**Создать файл** `public/css/panel/tokens.css`:

```css
/* ============================================
   Panel Design Tokens (копия дизайн-системы remnawave-admin)
   ============================================ */

:root {
  /* Шрифты */
  --font-sans: 'Montserrat', system-ui, sans-serif;
  --font-mono: 'Fira Mono', 'JetBrains Mono', ui-monospace, monospace;
  --font-display: 'Unbounded', system-ui, sans-serif;

  /* Радиусы */
  --radius: 0.5rem;
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-glass: 14px;

  /* Плотность (default = comfortable) */
  --density-padding: 0.5rem;
  --density-gap: 0.5rem;
  --density-py: 0.5rem;
  --density-px: 0.75rem;

  /* Тени */
  --shadow-deep: 0 8px 32px rgba(0, 0, 0, 0.4);
  --shadow-card: 0 4px 16px rgba(0, 0, 0, 0.2);
  --shadow-glass: 0 8px 32px rgba(0, 0, 0, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  --shadow-glass-hover: 0 12px 40px rgba(0, 0, 0, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.08);

  /* Glass */
  --glass-blur: 24px;
  --glass-blur-heavy: 32px;

  /* Mesh */
  --mesh-color-1: #2d2a6e;
  --mesh-color-2: #4338ca;
  --mesh-color-3: #2563a0;
  --mesh-color-4: #162240;
  --mesh-color-5: #2d2a6e;

  /* Анимации */
  --transition-fast: 0.15s ease;
  --transition-normal: 0.25s ease;
  --transition-bounce: 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
```

**Проверка:** файл создан, содержит ровно приведённые переменные.

**Commit:** `feat(panel): add design tokens (tokens.css)`

---

### Task 1.2: Создать `public/css/panel/themes.css`

**Цель:** переменные цветов для тёмной темы (default Obsidian) + 5 дополнительных акцентов + светлый режим. Механика: `[data-theme="..."]` на `<html>`.

**Создать файл** `public/css/panel/themes.css`:

```css
/* ============================================
   Panel Themes — 6 акцентов + light mode
   Применяются через data-theme / data-mode на <html>
   ============================================ */

/* === Базовые (default = Obsidian, индиго) === */
:root,
[data-theme="obsidian"] {
  --background: 220 24% 7%;          /* hsl, основной фон */
  --foreground: 220 9% 84%;
  --card: 220 20% 10%;
  --card-foreground: 220 9% 84%;
  --popover: 220 20% 10%;
  --popover-foreground: 220 9% 84%;
  --primary: 239 84% 67%;            /* #6366f1 indigo */
  --primary-foreground: 0 0% 100%;
  --secondary: 220 14% 16%;
  --secondary-foreground: 220 9% 84%;
  --muted: 220 14% 16%;
  --muted-foreground: 220 9% 56%;
  --accent: 220 14% 16%;
  --accent-foreground: 220 9% 84%;
  --destructive: 0 72% 51%;
  --destructive-foreground: 0 0% 100%;
  --border: 220 14% 18%;
  --input: 220 14% 18%;
  --ring: 239 84% 67%;

  /* Sidebar */
  --sidebar-background: 220 22% 8%;
  --sidebar-foreground: 220 9% 84%;
  --sidebar-primary: 239 84% 67%;
  --sidebar-primary-foreground: 0 0% 100%;
  --sidebar-accent: 220 14% 14%;
  --sidebar-accent-foreground: 220 9% 84%;
  --sidebar-border: 220 14% 16%;
  --sidebar-ring: 239 84% 67%;

  /* Акцент/glow */
  --accent-from: #6366f1;
  --accent-to: #818cf8;
  --accent-from-light: #818cf8;
  --accent-to-light: #a5b4fc;
  --glow-rgb: 99, 102, 241;
  --selection-rgb: 99, 102, 241;

  /* Поверхности */
  --surface-body: #0f1318;
  --surface-card: #181e28;
  --surface-card-alpha: rgba(24, 30, 40, 0.8);
  --surface-hover: rgba(35, 40, 54, 0.5);
  --surface-table-header: rgba(15, 19, 24, 0.8);
  --surface-dropdown: rgba(24, 30, 40, 0.98);
  --surface-skeleton-shimmer: rgba(99, 102, 241, 0.04);

  /* Текст */
  --text-body: #d1d5db;
  --text-heading: #f3f4f6;
  --text-muted: #6b7280;

  /* Glass */
  --glass-bg: rgba(22, 28, 38, 0.5);
  --glass-bg-hover: rgba(22, 28, 38, 0.6);
  --glass-bg-solid: #181e28;
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-border-hover: rgba(255, 255, 255, 0.14);
  --glass-highlight: rgba(255, 255, 255, 0.04);

  /* Mesh */
  --mesh-color-1: #2d2a6e;
  --mesh-color-2: #4338ca;
  --mesh-color-3: #2563a0;
  --mesh-color-4: #162240;
}

/* === Halo (cyan/teal — фирменный) === */
[data-theme="halo"] {
  --primary: 190 90% 46%;
  --ring: 190 90% 46%;
  --sidebar-primary: 190 90% 46%;
  --sidebar-ring: 190 90% 46%;
  --accent-from: #22d3ee;
  --accent-to: #3b82f6;
  --accent-from-light: #67e8f9;
  --accent-to-light: #7dd3fc;
  --glow-rgb: 34, 211, 238;
  --selection-rgb: 34, 211, 238;
  --surface-skeleton-shimmer: rgba(34, 211, 238, 0.04);
  --mesh-color-1: #0e7e9c;
  --mesh-color-2: #2056ad;
  --mesh-color-3: #11a3c4;
  --mesh-color-4: #2a2f7a;
}

/* === Arctic (sky-blue) === */
[data-theme="arctic"] {
  --primary: 199 89% 48%;
  --ring: 199 89% 48%;
  --sidebar-primary: 199 89% 48%;
  --sidebar-ring: 199 89% 48%;
  --accent-from: #0ea5e9;
  --accent-to: #38bdf8;
  --accent-from-light: #38bdf8;
  --accent-to-light: #7dd3fc;
  --glow-rgb: 14, 165, 233;
  --selection-rgb: 14, 165, 233;
  --surface-skeleton-shimmer: rgba(14, 165, 233, 0.04);
  --mesh-color-1: #0e6da0;
  --mesh-color-2: #0284c7;
  --mesh-color-3: #1e6e8a;
  --mesh-color-4: #143860;
}

/* === Sakura (pink-rose) === */
[data-theme="sakura"] {
  --primary: 330 81% 60%;
  --ring: 330 81% 60%;
  --sidebar-primary: 330 81% 60%;
  --sidebar-ring: 330 81% 60%;
  --accent-from: #ec4899;
  --accent-to: #f472b6;
  --accent-from-light: #f472b6;
  --accent-to-light: #f9a8d4;
  --glow-rgb: 236, 72, 153;
  --selection-rgb: 236, 72, 153;
  --surface-skeleton-shimmer: rgba(236, 72, 153, 0.04);
  --mesh-color-1: #6e2560;
  --mesh-color-2: #9d3070;
  --mesh-color-3: #551845;
  --mesh-color-4: #2a1028;
}

/* === Twilight (purple-violet) === */
[data-theme="twilight"] {
  --primary: 263 70% 58%;
  --ring: 263 70% 58%;
  --sidebar-primary: 263 70% 58%;
  --sidebar-ring: 263 70% 58%;
  --accent-from: #8b5cf6;
  --accent-to: #a78bfa;
  --accent-from-light: #a78bfa;
  --accent-to-light: #c4b5fd;
  --glow-rgb: 139, 92, 246;
  --selection-rgb: 139, 92, 246;
  --surface-skeleton-shimmer: rgba(139, 92, 246, 0.04);
  --mesh-color-1: #4c1d95;
  --mesh-color-2: #5b21b6;
  --mesh-color-3: #2d2a6e;
  --mesh-color-4: #261545;
}

/* === Ember (warm amber) === */
[data-theme="ember"] {
  --primary: 38 92% 50%;
  --ring: 38 92% 50%;
  --sidebar-primary: 38 92% 50%;
  --sidebar-ring: 38 92% 50%;
  --accent-from: #f59e0b;
  --accent-to: #fbbf24;
  --accent-from-light: #fbbf24;
  --accent-to-light: #fcd34d;
  --glow-rgb: 245, 158, 11;
  --selection-rgb: 245, 158, 11;
  --surface-skeleton-shimmer: rgba(245, 158, 11, 0.04);
  --mesh-color-1: #6b2e08;
  --mesh-color-2: #a34e15;
  --mesh-color-3: #5a3510;
  --mesh-color-4: #2e1808;
}

/* === СВЕТЛЫЙ РЕЖИМ === */
[data-mode="light"] {
  --background: 0 0% 98%;
  --foreground: 220 28% 14%;
  --card: 0 0% 100%;
  --card-foreground: 220 28% 14%;
  --popover: 0 0% 100%;
  --popover-foreground: 220 28% 14%;
  --secondary: 220 14% 92%;
  --secondary-foreground: 220 28% 14%;
  --muted: 220 14% 92%;
  --muted-foreground: 220 9% 40%;
  --accent: 220 14% 92%;
  --accent-foreground: 220 28% 14%;
  --border: 220 14% 86%;
  --input: 220 14% 86%;

  --sidebar-background: 220 14% 96%;
  --sidebar-foreground: 220 28% 14%;
  --sidebar-accent: 220 14% 90%;
  --sidebar-accent-foreground: 220 28% 14%;
  --sidebar-border: 220 14% 88%;

  --surface-body: #f8fafc;
  --surface-card: #ffffff;
  --surface-card-alpha: rgba(255, 255, 255, 0.9);
  --surface-hover: rgba(241, 245, 249, 0.8);
  --surface-table-header: rgba(248, 250, 252, 0.95);
  --surface-dropdown: rgba(255, 255, 255, 0.98);

  --text-body: #1e293b;
  --text-heading: #0f172a;
  --text-muted: #64748b;
}
```

**Важно:** цвета в `--primary` и `--ring` заданы в формате **hsl без `hsl()`** (как в remnawave-admin), потому что будут использоваться так: `hsl(var(--primary))`. Это обязательное соглашение.

**Проверка:** все 6 тем + светлый режим присутствуют.

**Commit:** `feat(panel): add 6 accent themes + light mode (themes.css)`

---

### Task 1.3: Создать `public/css/panel/base.css`

**Цель:** базовый сброс, стили `html`/`body`, scrollbar, selection, focus-visible.

```css
/* ============================================
   Panel Base — reset, body, scrollbar, focus
   ============================================ */

*,
*::before,
*::after { box-sizing: border-box; }

html {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  margin: 0;
  min-height: 100vh;
  background-color: var(--surface-body);
  color: var(--text-body);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
}

/* Скроллбар — градиент акцента */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--surface-body); }
::-webkit-scrollbar-thumb {
  border-radius: 9999px;
  background: linear-gradient(180deg, var(--accent-from), var(--accent-to));
}
::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, var(--accent-from-light), var(--accent-to-light));
}

::selection { background: rgba(var(--selection-rgb), 0.3); }

*:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
  border-radius: 4px;
}

a { color: hsl(var(--primary)); text-decoration: none; }
a:hover { color: hsl(var(--ring)); }

/* Табличные числа — выравнивание цифр */
table, code, pre, kbd, .tabular-nums {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1;
}
```

**Commit:** `feat(panel): add base reset and global styles (base.css)`

---

### Task 1.4: Создать `public/css/panel/effects.css`

**Цель:** glass, glass-card, mesh-фон, glow, shimmer, анимации появления.

```css
/* ============================================
   Panel Effects — glass, mesh, glow, shimmer, animations
   ============================================ */

/* === Glass === */
.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
}
.glass:hover {
  background: var(--glass-bg-hover);
  border-color: var(--glass-border-hover);
}

.glass-rim {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-top-color: rgba(255, 255, 255, 0.12);
  border-left-color: rgba(255, 255, 255, 0.04);
}

.glass-heavy {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur-heavy));
  -webkit-backdrop-filter: blur(var(--glass-blur-heavy));
  border: 1px solid var(--glass-border);
}

/* === Glass Card (с верхней акцентной линией) === */
.glass-card {
  --card-rgb: var(--card-accent-rgb, var(--glow-rgb));
  position: relative;
  background:
    linear-gradient(135deg, rgba(var(--card-rgb), 0.04) 0%, var(--glass-bg) 50%, rgba(var(--card-rgb), 0.02) 100%);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15), 0 1px 0 0 rgba(255, 255, 255, 0.04) inset;
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.3s ease, box-shadow 0.3s ease;
  overflow: hidden;
}
.glass-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: linear-gradient(90deg, transparent 5%, rgba(var(--card-rgb), 0.6) 50%, transparent 95%);
  opacity: 0.35;
  transition: opacity 0.3s ease;
  z-index: 1;
}
.glass-card:hover::before { opacity: 0.75; }
.glass-card:hover {
  transform: translateY(-2px);
  border-color: var(--glass-border-hover);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2), 0 1px 0 0 rgba(255, 255, 255, 0.06) inset, 0 0 20px -5px rgba(var(--card-rgb), 0.18);
}
.glass-card:active { transform: scale(0.985); }

/* === Mesh-фон (анимированный, фиксированный за контентом) === */
.mesh-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
.mesh-layer {
  position: absolute;
  inset: -25%;
  opacity: 0.22;
  will-change: transform;
  contain: layout paint;
}
.mesh-layer--1 { background: radial-gradient(ellipse 40% 33% at 23% 30%, var(--mesh-color-1) 0%, transparent 70%); animation: meshFloat1 25s ease-in-out infinite; }
.mesh-layer--2 { background: radial-gradient(ellipse 33% 40% at 70% 37%, var(--mesh-color-2) 0%, transparent 70%); animation: meshFloat2 30s ease-in-out infinite; }
.mesh-layer--3 { background: radial-gradient(ellipse 30% 37% at 37% 63%, var(--mesh-color-3) 0%, transparent 70%); animation: meshFloat3 35s ease-in-out infinite; }
.mesh-layer--4 { background: radial-gradient(ellipse 37% 30% at 63% 70%, var(--mesh-color-4) 0%, transparent 70%); animation: meshFloat1 28s ease-in-out infinite reverse; }
.mesh-layer--5 { background: radial-gradient(ellipse 27% 27% at 50% 50%, var(--mesh-color-1) 0%, transparent 60%); opacity: 0.12; animation: meshFloat2 32s ease-in-out infinite; }

[data-mode="light"] .mesh-layer { opacity: 0.08; }
[data-animations="false"] .mesh-layer { animation: none; }

@keyframes meshFloat1 {
  0%, 100% { transform: translate(0%, 0%) scale(1); }
  25% { transform: translate(5%, -8%) scale(1.05); }
  50% { transform: translate(-3%, 6%) scale(0.98); }
  75% { transform: translate(4%, 3%) scale(1.02); }
}
@keyframes meshFloat2 {
  0%, 100% { transform: translate(0%, 0%) scale(1); }
  33% { transform: translate(-4%, 5%) scale(1.03); }
  66% { transform: translate(6%, -3%) scale(0.97); }
}
@keyframes meshFloat3 {
  0%, 100% { transform: translate(0%, 0%) scale(1); }
  20% { transform: translate(3%, -6%) scale(1.04); }
  40% { transform: translate(-5%, 2%) scale(0.96); }
  60% { transform: translate(2%, 5%) scale(1.02); }
  80% { transform: translate(-3%, -4%) scale(0.99); }
}

/* === Glow === */
.glow-accent { box-shadow: 0 0 30px -5px rgba(var(--glow-rgb), 0.3); }
.glow-accent-hover:hover { box-shadow: 0 0 30px -5px rgba(var(--glow-rgb), 0.3); }

/* === Skeleton shimmer === */
.skeleton {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius);
  background: hsl(var(--muted));
}
.skeleton::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, var(--surface-skeleton-shimmer) 50%, transparent 100%);
  animation: shimmer 1.5s infinite;
}

/* === Анимации появления === */
@keyframes fadeIn { 0% { opacity: 0; } 100% { opacity: 1; } }
@keyframes fadeInUp { 0% { opacity: 0; transform: translateY(12px); } 100% { opacity: 1; transform: translateY(0); } }
@keyframes fadeInDown { 0% { opacity: 0; transform: translateY(-8px); } 100% { opacity: 1; transform: translateY(0); } }
@keyframes scaleIn { 0% { opacity: 0; transform: scale(0.95); } 100% { opacity: 1; transform: scale(1); } }
@keyframes shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }

.anim-fade-in { animation: fadeIn 0.2s ease-out; }
.anim-fade-in-up { animation: fadeInUp 0.35s ease-out both; }
.anim-fade-in-down { animation: fadeInDown 0.3s ease-out both; }
.anim-scale-in { animation: scaleIn 0.25s ease-out both; }

.stagger-1 { animation-delay: 0.05s; }
.stagger-2 { animation-delay: 0.1s; }
.stagger-3 { animation-delay: 0.15s; }
.stagger-4 { animation-delay: 0.2s; }

/* Уважение к prefers-reduced-motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .mesh-layer { animation: none !important; }
}

/* === Настройки вида === */
[data-animations="false"], [data-animations="false"] * {
  animation-duration: 0s !important;
  animation-delay: 0s !important;
  transition-duration: 0s !important;
}
```

**Commit:** `feat(panel): add glass, mesh, glow, shimmer effects (effects.css)`

---

### Task 1.5: Создать `public/css/panel/components.css`

**Цель:** кнопки, бейджи, карточки, формы, пустые состояния.

```css
/* ============================================
   Panel Components — buttons, badges, cards, forms, empty states
   ============================================ */

/* === Buttons === */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 18px;
  border: 1px solid transparent;
  border-radius: var(--radius);
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: background-color var(--transition-fast), box-shadow var(--transition-fast), transform var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast);
  user-select: none;
}
.btn:active { transform: scale(0.97); }
.btn:focus-visible { outline: 2px solid hsl(var(--ring)); outline-offset: 2px; }

.btn-primary {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}
.btn-primary:hover { background: hsl(var(--ring)); box-shadow: 0 0 20px -5px rgba(var(--glow-rgb), 0.4); }

.btn-secondary {
  background: hsl(var(--secondary));
  color: hsl(var(--secondary-foreground));
}
.btn-secondary:hover { background: hsl(var(--muted)); }

.btn-ghost {
  background: transparent;
  color: var(--text-body);
  border-color: var(--border);
}
.btn-ghost:hover { background: var(--surface-hover); border-color: var(--glass-border-hover); }

.btn-danger { background: hsl(var(--destructive)); color: hsl(var(--destructive-foreground)); }
.btn-danger:hover { filter: brightness(1.1); }

.btn-sm { padding: 6px 12px; font-size: 13px; }
.btn-lg { padding: 12px 24px; font-size: 16px; }
.btn-block { display: flex; width: 100%; justify-content: center; }

/* === Badges === */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.4;
  border: 1px solid transparent;
}
.badge-published, .badge-success { background: rgba(34, 197, 94, 0.15); color: #4ade80; border-color: rgba(34, 197, 94, 0.3); }
.badge-draft, .badge-warning { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3); }
.badge-archived, .badge-danger { background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.3); }
.badge-info { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border-color: rgba(59, 130, 246, 0.3); }
.badge-neutral { background: hsl(var(--secondary)); color: var(--text-body); }

[data-mode="light"] .badge-published { color: #16a34a; }
[data-mode="light"] .badge-draft { color: #b45309; }
[data-mode="light"] .badge-archived { color: #dc2626; }
[data-mode="light"] .badge-info { color: #2563eb; }

/* === Cards === */
.card {
  background: linear-gradient(135deg, var(--surface-card-alpha) 0%, var(--surface-card) 100%);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--density-padding);
  box-shadow: var(--shadow-card);
  animation: fadeInUp 0.35s ease-out both;
}
.card:hover { border-color: var(--glass-border-hover); }

/* === Forms === */
.form-group { margin-bottom: 16px; }
.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-body);
}
.form-group .help-text { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

input[type="text"], input[type="email"], input[type="password"],
input[type="number"], input[type="url"], input[type="date"], input[type="datetime-local"],
textarea, select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--input);
  border-radius: var(--radius);
  background: hsl(var(--card));
  color: var(--text-body);
  font-family: var(--font-sans);
  font-size: 14px;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: hsl(var(--ring));
  box-shadow: 0 0 0 1px hsl(var(--ring)), 0 0 15px -3px rgba(var(--glow-rgb), 0.3);
}

.form-actions { display: flex; gap: 8px; margin-top: 20px; }
.form-row { display: flex; gap: 16px; flex-wrap: wrap; }
.form-row .form-group { flex: 1; min-width: 200px; }

/* === Empty states === */
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}
.empty-state .empty-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin-bottom: 12px;
  border-radius: var(--radius);
  background: hsl(var(--secondary));
  color: var(--text-muted);
}
.empty-state h3 { margin: 0 0 6px; color: var(--text-body); font-size: 16px; }
.empty-state p { margin: 0 0 16px; font-size: 14px; }

/* === Alerts === */
.alert {
  padding: 12px 16px;
  border-radius: var(--radius);
  margin-bottom: 16px;
  font-size: 14px;
  border: 1px solid transparent;
}
.alert-error { background: rgba(239, 68, 68, 0.12); color: #f87171; border-color: rgba(239, 68, 68, 0.3); }
.alert-success { background: rgba(34, 197, 94, 0.12); color: #4ade80; border-color: rgba(34, 197, 94, 0.3); }
.alert-info { background: rgba(59, 130, 246, 0.12); color: #60a5fa; border-color: rgba(59, 130, 246, 0.3); }

/* === Density === */
[data-density="compact"] { --density-padding: 0.25rem; --density-gap: 0.25rem; --density-py: 0.25rem; --density-px: 0.5rem; }
[data-density="spacious"] { --density-padding: 0.75rem; --density-gap: 0.75rem; --density-py: 0.75rem; --density-px: 1rem; }

/* === Radius === */
[data-radius="sharp"] { --radius: 0px; }
[data-radius="default"] { --radius: 0.5rem; }
[data-radius="rounded"] { --radius: 0.75rem; }

/* === Font size === */
[data-font-size="small"] body { font-size: 13px; }
[data-font-size="default"] body { font-size: 14px; }
[data-font-size="large"] body { font-size: 16px; }
```

**Commit:** `feat(panel): add buttons, badges, cards, forms components (components.css)`

---

### Task 1.6: Создать `public/css/panel/table.css`

**Цель:** стили таблиц для DataGrid.

```css
/* ============================================
   Panel Table — DataGrid styles
   ============================================ */

.dg-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  color: var(--text-body);
  background: transparent;
}

.dg-table thead th {
  padding: 10px var(--density-px);
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: hsl(var(--muted-foreground));
  background: var(--surface-table-header);
  border-bottom: 1px solid hsl(var(--border) / 0.4);
  white-space: nowrap;
}

.dg-table tbody td {
  padding: 12px var(--density-px);
  border-top: 1px solid hsl(var(--border) / 0.1);
  vertical-align: middle;
}

.dg-table tbody tr { transition: background var(--transition-fast); }
.dg-table tbody tr:hover { background: var(--surface-hover); }

.dg-table th.sortable { cursor: pointer; user-select: none; }
.dg-table th.sortable:hover { color: var(--text-body); }
.dg-table th .sort-indicator { opacity: 0.4; margin-left: 4px; }
.dg-table th.sorted .sort-indicator { opacity: 1; color: hsl(var(--primary)); }

/* Обёртка таблицы (карточка) */
.dg-wrapper {
  background: hsl(var(--card));
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

/* Пагинация */
.dg-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  font-size: 13px;
  color: var(--text-muted);
}
.dg-pagination .pagination-links { display: flex; gap: 4px; }
.dg-pagination .page-link {
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  color: var(--text-body);
  text-decoration: none;
  border: 1px solid transparent;
}
.dg-pagination .page-link:hover { background: var(--surface-hover); }
.dg-pagination .page-link.active { background: hsl(var(--primary)); color: hsl(var(--primary-foreground)); }

/* Фильтры над таблицей */
.dg-filters {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--border);
  background: var(--surface-card-alpha);
}
.dg-filters input, .dg-filters select { width: auto; min-width: 150px; }

/* Экспорт/действия таблицы */
.dg-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

[data-density="compact"] .dg-table tbody td { padding: 6px var(--density-px); font-size: 12px; }
[data-density="spacious"] .dg-table tbody td { padding: 16px var(--density-px); }
```

**Commit:** `feat(panel): add DataGrid table styles (table.css)`

---

### Task 1.7: Создать `public/css/panel/layout.css`

**Цель:** сайдбар (сворачиваемый), шапка, breadcrumbs, layout-сетка, контент.

```css
/* ============================================
   Panel Layout — sidebar, header, content, density
   ============================================ */

.panel-layout {
  display: flex;
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

/* === Sidebar === */
.panel-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: hsl(var(--sidebar-background));
  border-right: 1px solid hsl(var(--sidebar-border));
  position: sticky;
  top: 0;
  height: 100vh;
  transition: width var(--transition-normal);
  overflow: hidden;
}

.panel-sidebar.sidebar-collapsed { width: 72px; }
.panel-sidebar.sidebar-collapsed .sidebar-text { display: none; }
.panel-sidebar.sidebar-collapsed .sidebar-group-title { display: none; }
.panel-sidebar.sidebar-collapsed .sidebar-nav-item { justify-content: center; }
.panel-sidebar.sidebar-collapsed .sidebar-logo span { display: none; }

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  font-family: var(--font-display);
  font-size: 16px;
  color: var(--text-heading);
  text-decoration: none;
  border-bottom: 1px solid hsl(var(--sidebar-border));
}

.sidebar-nav { flex: 1; padding: 12px 8px; overflow-y: auto; }
.sidebar-group-title {
  padding: 12px 12px 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.sidebar-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  margin: 2px 0;
  border-radius: var(--radius);
  color: var(--sidebar-foreground);
  text-decoration: none;
  font-size: 14px;
  position: relative;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.sidebar-nav-item:hover { background: var(--sidebar-accent); }
.sidebar-nav-item.active {
  background: hsl(var(--sidebar-primary) / 0.15);
  color: hsl(var(--sidebar-primary));
  box-shadow: inset 2px 0 0 hsl(var(--sidebar-primary));
}
.sidebar-nav-item svg { width: 18px; height: 18px; flex-shrink: 0; opacity: 0.75; }
.sidebar-nav-item.active svg { opacity: 1; }
.sidebar-nav-item:hover::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: radial-gradient(circle at var(--ripple-x, 50%) var(--ripple-y, 50%), rgba(var(--glow-rgb), 0.08) 0%, transparent 70%);
  pointer-events: none;
}

.sidebar-footer {
  padding: 12px 8px;
  border-top: 1px solid hsl(var(--sidebar-border));
}
.sidebar-footer .sidebar-nav-item.logout:hover { color: #f87171; }

/* === Main === */
.panel-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }

/* === Header === */
.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  background: var(--surface-card-alpha);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 10;
}
.header-title { font-size: 18px; font-weight: 600; color: var(--text-heading); }
.header-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }

.header-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid var(--input);
  border-radius: var(--radius);
  background: hsl(var(--card));
  color: var(--text-muted);
  min-width: 240px;
  cursor: pointer;
}
.header-search kbd {
  margin-left: auto;
  padding: 1px 6px;
  border-radius: 4px;
  background: hsl(var(--secondary));
  font-family: var(--font-mono);
  font-size: 11px;
}

/* === Content === */
.panel-content {
  padding: 24px;
  flex: 1;
  position: relative;
}

/* Breadcrumbs */
.breadcrumbs {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.breadcrumbs a { color: var(--text-muted); text-decoration: none; }
.breadcrumbs a:hover { color: var(--text-body); }
.breadcrumb-sep { opacity: 0.5; }

.page-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
  animation: fadeInUp 0.35s ease-out both;
}
@media (min-width: 640px) {
  .page-header { flex-direction: row; align-items: center; justify-content: space-between; }
}
.page-header-title { font-size: 22px; font-weight: 700; color: var(--text-heading); margin: 0; }
.page-header-actions { display: flex; align-items: center; gap: 8px; }

/* === Density === */
[data-density="compact"] .panel-content { padding: 12px; }
[data-density="compact"] .panel-header { padding: 8px 16px; }
[data-density="spacious"] .panel-content { padding: 32px; }
[data-density="spacious"] .panel-header { padding: 16px 32px; }

/* === Icon button === */
.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius);
  border: 1px solid var(--input);
  background: hsl(var(--card));
  color: var(--text-body);
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}
.btn-icon:hover { background: var(--surface-hover); border-color: var(--glass-border-hover); }

/* User info */
.user-info { display: flex; align-items: center; gap: 8px; }
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-weight: 600;
  font-size: 13px;
}
.user-name { font-size: 13px; color: var(--text-body); }
```

**Commit:** `feat(panel): add sidebar, header, layout styles (layout.css)`

---

## Phase 2: Подключение дизайн-системы

### Task 2.1: Создать `admin/js/panel.js`

**Цель:** инициализация тем, режимов, настроек вида, сайдбара. Использует localStorage для настроек + синхронизирует тему с сервером через POST.

```javascript
/**
 * Panel JS — темы, режим, настройки вида, сайдбар
 */
(function () {
  const STORAGE_KEY = 'panel-preferences';

  function getPrefs() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function setPrefs(prefs) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    applyPrefs(prefs);
  }

  function applyPrefs(prefs) {
    const html = document.documentElement;
    if (prefs.theme) html.setAttribute('data-theme', prefs.theme);
    if (prefs.mode) html.setAttribute('data-mode', prefs.mode);
    if (prefs.density) html.setAttribute('data-density', prefs.density);
    if (prefs.radius) html.setAttribute('data-radius', prefs.radius);
    if (prefs.fontSize) html.setAttribute('data-font-size', prefs.fontSize);
    if (prefs.animations === false) html.setAttribute('data-animations', 'false');
    else html.removeAttribute('data-animations');
  }

  function init() {
    const prefs = getPrefs();
    // Дефолты, если ничего не сохранено
    if (!prefs.theme) prefs.theme = 'obsidian';
    if (!prefs.mode) prefs.mode = 'dark';
    if (!prefs.density) prefs.density = 'comfortable';
    if (!prefs.radius) prefs.radius = 'default';
    if (!prefs.fontSize) prefs.fontSize = 'default';
    if (prefs.animations === undefined) prefs.animations = true;
    applyPrefs(prefs);

    // Переключение темы/режима через data-атрибуты на кнопках
    document.addEventListener('click', function (e) {
      const themeBtn = e.target.closest('[data-set-theme]');
      if (themeBtn) {
        const prefs = getPrefs();
        prefs.theme = themeBtn.getAttribute('data-set-theme');
        setPrefs(prefs);
        saveToServer('theme', prefs.theme);
        return;
      }
      const modeBtn = e.target.closest('[data-set-mode]');
      if (modeBtn) {
        const prefs = getPrefs();
        prefs.mode = modeBtn.getAttribute('data-set-mode');
        setPrefs(prefs);
        saveToServer('mode', prefs.mode);
        return;
      }
      const densityBtn = e.target.closest('[data-set-density]');
      if (densityBtn) {
        const prefs = getPrefs();
        prefs.density = densityBtn.getAttribute('data-set-density');
        setPrefs(prefs);
        return;
      }
    });

    // Сворачивание сайдбара
    const collapseBtn = document.getElementById('sidebar-collapse-btn');
    if (collapseBtn) {
      collapseBtn.addEventListener('click', function () {
        const sidebar = document.querySelector('.panel-sidebar');
        if (sidebar) sidebar.classList.toggle('sidebar-collapsed');
      });
    }
  }

  // Сохранение темы/режима на сервер (per-user)
  function saveToServer(key, value) {
    fetch('/admin/settings/save-preference', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: key, value: value }),
    }).catch(function () { /* тихо игнорируем */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

**Примечание:** `data-theme`/`data-mode` ставятся до загрузки CSS чтобы избежать «вспышки» — этот скрипт можно подключить в `<head>` (async, не блокирует). Для этого при первом рендере layout ставит дефолт `data-theme="obsidian" data-mode="dark"` прямо в HTML-атрибутах `<html>`.

**Commit:** `feat(panel): add theme/mode/density initialization (panel.js)`

---

### Task 2.2: Обновить `admin/templates/layouts/main.php`

**Цель:** новый каркас: mesh-фон, сайдбар с группами, шапка с поиском (палитра), подключение CSS+JS+шрифтов.

**Шаги:**

1. В `<head>` заменить подключение стилей на:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Unbounded:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/tokens.css">
<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/themes.css">
<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/base.css">
<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/effects.css">
<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/components.css">
<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/table.css">
<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/layout.css">
<script src="<?= SITE_URL ?>/admin/js/panel.js" defer></script>
```

2. На `<html>` добавить атрибуты: `data-theme="obsidian" data-mode="dark" data-density="comfortable" data-radius="default" data-font-size="default"` (считывать из сохранённых настроек, если есть — см. Task 3.1).

3. Вставить mesh-фон в начало `<body>`:
```html
<div class="mesh-bg" aria-hidden="true">
  <div class="mesh-layer mesh-layer--1"></div>
  <div class="mesh-layer mesh-layer--2"></div>
  <div class="mesh-layer mesh-layer--3"></div>
  <div class="mesh-layer mesh-layer--4"></div>
  <div class="mesh-layer mesh-layer--5"></div>
</div>
```

4. Перестроить layout на структуру:
```html
<div class="panel-layout">
  <aside class="panel-sidebar" id="panel-sidebar">
    <a href="/admin" class="sidebar-logo">
      <?= icon('hexa', 'icon-lg') ?><span><?= SITE_NAME ?></span>
    </a>
    <nav class="sidebar-nav">
      <!-- Группа: Главное -->
      <div class="sidebar-group-title">Главное</div>
      <a href="/admin" class="sidebar-nav-item <?= TemplateEngine::isActive('admin') ?>"><?= icon('dashboard') ?><span class="sidebar-text">Дашборд</span></a>
      <a href="/admin/posts" class="sidebar-nav-item <?= TemplateEngine::isActive('admin/posts') ?>"><?= icon('file-text') ?><span class="sidebar-text">Посты</span></a>
      <a href="/admin/categories" class="sidebar-nav-item <?= TemplateEngine::isActive('admin/categories') ?>"><?= icon('folder') ?><span class="sidebar-text">Категории</span></a>

      <!-- Группа: Контент -->
      <div class="sidebar-group-title">Контент</div>
      <a href="/admin/pages" class="sidebar-nav-item <?= TemplateEngine::isActive('admin/pages') ?>"><?= icon('file') ?><span class="sidebar-text">Страницы</span></a>
      <a href="/admin/menus" class="sidebar-nav-item <?= TemplateEngine::isActive('admin/menus') ?>"><?= icon('menu') ?><span class="sidebar-text">Меню</span></a>
      <a href="/admin/media" class="sidebar-nav-item <?= TemplateEngine::isActive('admin/media') ?>"><?= icon('image') ?><span class="sidebar-text">Медиа</span></a>
      <a href="/admin/widgets" class="sidebar-nav-item <?= TemplateEngine::isActive('admin/widgets') ?>"><?= icon('widgets') ?><span class="sidebar-text">Виджеты</span></a>

      <!-- Группа: Система -->
      <div class="sidebar-group-title">Система</div>
      <a href="/admin/users" class="sidebar-nav-item <?= TemplateEngine::isActive('admin/users') ?>"><?= icon('users') ?><span class="sidebar-text">Пользователи</span></a>
      <a href="/admin/settings" class="sidebar-nav-item <?= TemplateEngine::isActive('admin/settings') ?>"><?= icon('settings') ?><span class="sidebar-text">Настройки</span></a>
      <a href="/admin/theme" class="sidebar-nav-item <?= TemplateEngine::isActive('admin/theme') ?>"><?= icon('palette') ?><span class="sidebar-text">Темы</span></a>
    </nav>
    <div class="sidebar-footer">
      <a href="/" class="sidebar-nav-item" target="_blank"><?= icon('external') ?><span class="sidebar-text">На сайт</span></a>
      <a href="/admin/logout" class="sidebar-nav-item logout"><?= icon('logout') ?><span class="sidebar-text">Выйти</span></a>
    </div>
  </aside>

  <main class="panel-main">
    <header class="panel-header">
      <button class="btn-icon" id="sidebar-collapse-btn" title="Свернуть меню"><?= icon('menu') ?></button>
      <div class="header-search" id="command-palette-trigger">
        <span>Поиск по разделам...</span><kbd>Ctrl K</kbd>
      </div>
      <div class="header-actions">
        <!-- Переключатель тем и режима -->
        <button class="btn-icon" id="theme-toggle" title="Сменить тему"><?= icon('palette') ?></button>
        <div class="user-info">
          <span class="user-avatar"><?= strtoupper(substr($user['login'] ?? 'A', 0, 1)) ?></span>
          <span class="user-name"><?= $user['login'] ?? 'Администратор' ?></span>
        </div>
      </div>
    </header>
    <div class="panel-content">
      <div class="breadcrumbs">
        <a href="/admin">Главная</a>
        <?php if (!empty($breadcrumbs)): ?>
          <?php foreach ($breadcrumbs as $crumb): ?>
            <span class="breadcrumb-sep">/</span>
            <?php if (!empty($crumb['url'])): ?><a href="<?= $crumb['url'] ?>"><?= TemplateEngine::e($crumb['title']) ?></a>
            <?php else: ?><span><?= TemplateEngine::e($crumb['title']) ?></span><?php endif; ?>
          <?php endforeach; ?>
        <?php else: ?><span class="breadcrumb-sep">/</span><span><?= $title ?? 'Панель управления' ?></span><?php endif; ?>
      </div>
      <div class="page-header">
        <h1 class="page-header-title"><?= $title ?? 'Панель управления' ?></h1>
        <div class="page-header-actions"><?= $headerActions ?? '' ?></div>
      </div>
      <?php if (isset($error)): ?><div class="alert alert-error"><?= TemplateEngine::e($error) ?></div><?php endif; ?>
      <?php if (isset($success)): ?><div class="alert alert-success"><?= TemplateEngine::e($success) ?></div><?php endif; ?>
      <?= $content ?? '' ?>
    </div>
  </main>
</div>

<!-- Командная палитра -->
<div id="command-palette" class="command-palette" hidden></div>
```

5. **TinyMCE оставить** (для форм постов/страниц), но селектор и стили подогнать под тёмную тему (content_style с тёмным фоном).

6. Убедиться, что переменная `$title` используется в `.page-header-title`, а `$content` — в `.panel-content`.

**Проверка:** открыть админку — тёмный сайдбар, шапка, mesh-фон, группы меню. Сайдбар сворачивается по кнопке.

**Commit:** `feat(panel): rebuild admin layout with sidebar groups and header`

---

## Phase 3: Командная палитра

### Task 3.1: Создать `admin/js/command-palette.js`

**Цель:** Ctrl+K палитра поиска по разделам админки.

**Шаги:**
1. Создать файл с массивом `SECTIONS` (название + URL + иконка) для всех разделов:
   - Дашборд `/admin`, Посты `/admin/posts`, Категории `/admin/categories`, Страницы `/admin/pages`, Меню `/admin/menus`, Медиа `/admin/media`, Пользователи `/admin/users`, Настройки `/admin/settings`, Темы `/admin/theme`, Виджеты `/admin/widgets`
2. Показ палитры по Ctrl+K (ввод фильтрует список, Enter/клик — переход)
3. Оверлей + поле ввода + список результатов, стили в `effects.css` (добавить блок `.command-palette` + `#command-palette .cp-overlay` и т.д.)
4. Подключить в `main.php` после panel.js

**Проверка:** Ctrl+K открывает палитру, поиск работает, Enter переходит по URL.

**Commit:** `feat(panel): add command palette (Ctrl+K)`

---

## Phase 4: Переключатель тем и сохранение настроек

### Task 4.1: Таблица `user_preferences` + миграция

**Цель:** хранить тему/режим per-user в БД.

**Создать файл** `db/migrations/2026-08-26-user-preferences.sql`:
```sql
CREATE TABLE IF NOT EXISTS user_preferences (
  user_id INT NOT NULL,
  pref_key VARCHAR(50) NOT NULL,
  pref_value VARCHAR(100) NOT NULL,
  PRIMARY KEY (user_id, pref_key),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Выполнить** через phpMyAdmin или SQL-клиент (один раз, вручную) ИЛИ добавить в `install/` скрипт. Важно: `users(id)` — существующая таблица CMS.

**Commit:** `feat(db): add user_preferences table for panel settings`

---

### Task 4.2: Модель `core/models/UserPreference.php`

**Создать файл** `core/models/UserPreference.php`:
```php
<?php
/**
 * Модель пользовательских настроек панели (тема, режим и т.д.)
 */
class UserPreference
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    public function get(int $userId, string $key): ?string
    {
        $row = $this->db->fetch("SELECT pref_value FROM user_preferences WHERE user_id = ? AND pref_key = ?", [$userId, $key]);
        return $row['pref_value'] ?? null;
    }

    public function getAll(int $userId): array
    {
        $rows = $this->db->fetchAll("SELECT pref_key, pref_value FROM user_preferences WHERE user_id = ?", [$userId]);
        $result = [];
        foreach ($rows as $r) { $result[$r['pref_key']] = $r['pref_value']; }
        return $result;
    }

    public function set(int $userId, string $key, string $value): void
    {
        $this->db->query(
            "INSERT INTO user_preferences (user_id, pref_key, pref_value) VALUES (?, ?, ?)
             ON DUPLICATE KEY UPDATE pref_value = VALUES(pref_value)",
            [$userId, $key, $value]
        );
    }
}
```

**Проверка синтаксиса:** `php -l core/models/UserPreference.php` (если доступен). Убедиться, что методы `fetch`, `fetchAll`, `query` существуют в `core/Database.php` (проверить фактические сигнатуры, при несоответствии адаптировать).

**Commit:** `feat(db): add UserPreference model`

---

### Task 4.3: Эндпоинт сохранения настройки

**Цель:** POST `/admin/settings/save-preference` (без изменения существующих маршрутов — просто добавить новый в `core/routes.php`).

**Добавить в `core/routes.php`** (в конец, не меняя существующее):
```php
// Сохранение пользовательской настройки панели (тема/режим)
$router->post('admin/settings/save-preference', function() {
    Auth::requireAdmin();
    if (!verify_csrf() && empty($_SERVER['HTTP_X_CSRF'])) {
        // для fetch отключаем строгий CSRF, т.к. это internal (опционально)
    }
    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $key = $body['key'] ?? '';
    $value = $body['value'] ?? '';
    $allowed = ['theme', 'mode', 'density', 'radius', 'fontSize'];
    if (in_array($key, $allowed, true) && $value !== '') {
        $pref = new UserPreference();
        $pref->set(Auth::id(), $key, (string)$value);
    }
    header('Content-Type: application/json');
    echo json_encode(['ok' => true]);
});
```

**Проверка:** в браузере (консоль) — переключение темы сохраняется, после перезагрузки страницы тема применяется. Для этого в `main.php` при рендере нужно читать `(new UserPreference())->getAll(Auth::id())` и ставить атрибуты на `<html>` (заменить хардкод из Task 2.2).

**Commit:** `feat(panel): add preference save endpoint + apply saved theme on render`

---

## Phase 5: DataGrid — компонент ядра

### Task 5.1: Создать `core/DataGrid.php`

**Цель:** универсальный рендерер таблиц. Принимает готовые данные (без запросов к БД), отдаёт HTML.

```php
<?php
/**
 * DataGrid — универсальный рендерер таблиц админки
 * Принимает готовые данные, НЕ выполняет запросы к БД.
 *
 * Использование:
 * echo DataGrid::render([
 *   'columns' => [
 *       ['key' => 'id', 'label' => 'ID', 'sortable' => true],
 *       ['key' => 'title', 'label' => 'Заголовок', 'sortable' => true],
 *   ],
 *   'rows' => $rows,
 *   'actions' => [
 *       ['label' => 'edit', 'url' => '/admin/posts/edit/{id}', 'icon' => 'edit'],
 *       ['label' => 'view', 'url' => '/post/{slug}', 'icon' => 'eye', 'target' => '_blank'],
 *   ],
 *   'pagination' => ['page' => 1, 'total' => 100, 'per_page' => 25, 'base_url' => '/admin/posts'],
 *   'empty' => ['title' => 'Нет данных', 'text' => 'Создайте первую запись', 'action' => '/admin/posts/create'],
 * ]);
 */
class DataGrid
{
    public static function render(array $config): string
    {
        $columns = $config['columns'] ?? [];
        $rows = $config['rows'] ?? [];
        $actions = $config['actions'] ?? [];
        $empty = $config['empty'] ?? [];
        $pagination = $config['pagination'] ?? null;

        if (!$columns) return '';

        $html = '<div class="dg-wrapper">';
        $html .= '<table class="dg-table"><thead><tr>';
        foreach ($columns as $col) {
            $label = TemplateEngine::e($col['label'] ?? $col['key']);
            if (!empty($col['sortable'])) {
                $html .= '<th class="sortable" data-sort="' . TemplateEngine::e($col['key']) . '">' . $label . '<span class="sort-indicator">↕</span></th>';
            } else {
                $html .= '<th>' . $label . '</th>';
            }
        }
        if ($actions) $html .= '<th class="dg-actions-col">Действия</th>';
        $html .= '</tr></thead><tbody>';

        if (empty($rows) && !empty($empty)) {
            $html .= '<tr><td colspan="' . (count($columns) + ($actions ? 1 : 0)) . '">';
            $html .= '<div class="empty-state">';
            if (!empty($empty['icon'])) $html .= '<div class="empty-icon">' . icon($empty['icon']) . '</div>';
            if (!empty($empty['title'])) $html .= '<h3>' . TemplateEngine::e($empty['title']) . '</h3>';
            if (!empty($empty['text'])) $html .= '<p>' . TemplateEngine::e($empty['text']) . '</p>';
            if (!empty($empty['action']) && !empty($empty['action_label'])) {
                $html .= '<a href="' . $empty['action'] . '" class="btn btn-primary">' . $empty['action_label'] . '</a>';
            }
            $html .= '</div></td></tr>';
        }

        foreach ($rows as $row) {
            $html .= '<tr>';
            foreach ($columns as $col) {
                $value = $row[$col['key']] ?? '';
                if (!empty($col['format']) && is_callable($col['format'])) {
                    $value = $col['format']($value, $row);
                } elseif (!empty($col['html'])) {
                    $value = $col['html']($row);
                } else {
                    $value = TemplateEngine::e((string)$value);
                }
                $html .= '<td>' . $value . '</td>';
            }
            if ($actions) {
                $html .= '<td class="actions">';
                foreach ($actions as $act) {
                    $url = str_replace('{id}', (string)($row['id'] ?? ''), $act['url'] ?? '#');
                    $target = !empty($act['target']) ? ' target="' . $act['target'] . '"' : '';
                    $title = $act['label'] ?? '';
                    $html .= '<a href="' . $url . '" class="btn btn-sm btn-ghost" title="' . TemplateEngine::e($title) . '"' . $target . '>';
                    if (!empty($act['icon'])) $html .= icon($act['icon']);
                    elseif ($act['label'] ?? '') $html .= TemplateEngine::e($act['label']);
                    $html .= '</a>';
                }
                $html .= '</td>';
            }
            $html .= '</tr>';
        }

        $html .= '</tbody></table>';

        if ($pagination) {
            $html .= self::renderPagination($pagination);
        }

        $html .= '</div>';
        return $html;
    }

    private static function renderPagination(array $p): string
    {
        $page = (int)($p['page'] ?? 1);
        $total = (int)($p['total'] ?? 0);
        $per = (int)($p['per_page'] ?? 25);
        $pages = max(1, (int)ceil($total / $per));
        $base = $p['base_url'] ?? '/admin';

        $html = '<div class="dg-pagination">';
        $html .= '<span>Стр. ' . $page . ' из ' . $pages . ' (всего ' . $total . ')</span>';
        $html .= '<div class="pagination-links">';
        for ($i = 1; $i <= $pages; $i++) {
            if ($pages > 10 && $i > 1 && $i < $pages - 1 && abs($i - $page) > 2) {
                if ($i == 2 || $i == $pages - 2) $html .= '<span>...</span>';
                continue;
            }
            $sep = strpos($base, '?') !== false ? '&' : '?';
            $url = $base . $sep . 'page=' . $i;
            $cls = $i === $page ? 'page-link active' : 'page-link';
            $html .= '<a href="' . $url . '" class="' . $cls . '">' . $i . '</a>';
        }
        $html .= '</div></div>';
        return $html;
    }
}
```

**Проверка:** `php -l core/DataGrid.php`; убедиться в наличии методов `icon()` (helpers_icons.php) и `TemplateEngine::e()`.

**Commit:** `feat(core): add DataGrid component`

---

### Task 5.2: Перевести список постов на DataGrid

**Файл:** `admin/templates/posts/index.php`

**Шаги:**
1. Открыть текущий файл, посмотреть какие данные передаются из контроллера (переменные `$posts`, `$total`, `$page`, `$perPage`, пагинация).
2. Заменить ручную таблицу на:
```php
<?php
echo DataGrid::render([
    'columns' => [
        ['key' => 'id', 'label' => 'ID', 'sortable' => true],
        ['key' => 'title', 'label' => 'Заголовок', 'sortable' => true, 'html' => function($row) {
            return '<a href="/admin/posts/edit/' . $row['id'] . '">' . TemplateEngine::e($row['title']) . '</a>';
        }],
        ['key' => 'status', 'label' => 'Статус', 'html' => function($row) {
            $map = ['published' => 'published', 'draft' => 'draft', 'archived' => 'archived'];
            $label = ['published' => 'Опубликован', 'draft' => 'Черновик', 'archived' => 'Архив'];
            $st = $row['status'] ?? 'draft';
            return '<span class="badge badge-' . ($map[$st] ?? 'neutral') . '">' . ($label[$st] ?? $st) . '</span>';
        }],
        ['key' => 'created_at', 'label' => 'Дата', 'format' => function($v) {
            return format_date($v, 'd.m.Y');
        }],
    ],
    'rows' => $posts ?? [],
    'actions' => [
        ['label' => 'edit', 'url' => '/admin/posts/edit/{id}', 'icon' => 'edit'],
        ['label' => 'view', 'url' => '/post/{slug}', 'icon' => 'eye', 'target' => '_blank'],
        ['label' => 'delete', 'url' => '/admin/posts/delete/{id}', 'icon' => 'delete'],
    ],
    'pagination' => [
        'page' => $page ?? 1,
        'total' => $total ?? 0,
        'per_page' => $perPage ?? 25,
        'base_url' => '/admin/posts',
    ],
    'empty' => [
        'title' => 'Постов пока нет',
        'text' => 'Создайте первый пост',
        'action' => '/admin/posts/create',
        'action_label' => 'Создать пост',
        'icon' => 'file-text',
    ],
]);
?>
```
3. Пагинация/фильтры — контроллер уже передаёт `$page`/`$total`/`$perPage`? Проверить `admin/controllers/PostsController.php`. Если нет — использовать `DataGrid` без пагинации на текущем этапе (пагинацию не ломать, добавить позже).

**Проверка:** список постов выглядит как тёмная таблица, действия работают.

**Commit:** `feat(panel): migrate posts list to DataGrid`

---

### Task 5.3–5.8: Перевести остальные списки на DataGrid

Аналогично Task 5.2, по одному коммиту на раздел:

- **Task 5.3:** `admin/templates/categories/index.php` (колонки: id, name, slug, count; действия edit/delete)
- **Task 5.4:** `admin/templates/pages/index.php` (id, title, slug, status, template; действия edit/view/delete)
- **Task 5.5:** `admin/templates/media/index.php` (id, filename/thumbnail, type, size, created_at; действия delete)
- **Task 5.6:** `admin/templates/menus/index.php` (id, name, location, url; действия edit/delete)
- **Task 5.7:** `admin/templates/users/index.php` (id, login, email, role; действия edit/delete)
- **Task 5.8:** `admin/templates/widgets/index.php` (id, name, position, enabled; действия edit/delete)

**Правило для каждого:** сначала посмотреть текущий шаблон и какие данные отдаёт контроллер, затем заменить таблицу на `DataGrid::render(...)` с теми же колонками и действиями. URL и поведение НЕ менять.

**Каждый Task — отдельный коммит:** `feat(panel): migrate X list to DataGrid`

---

## Phase 6: Дашборд, логин, формы (перекраска)

### Task 6.1: Дашборд `admin/templates/dashboard.php`

**Шаги:**
1. Карточки статистики `.stats-grid` → стили в стиле remnawave-admin: использовать `.glass-card`, числовые акценты, анимация stagger.
2. Таблица «Последние посты» → заменить на `DataGrid` (без пагинации, или с ограниченным числом строк).
3. «Быстрые действия» → `.glass-card` + кнопки.
4. Сохранить все переменные (`$stats`, `$recentPosts`) без изменений.

**Проверка:** дашборд выглядит как панель управления, все карточки работают.

**Commit:** `feat(panel): restyle dashboard with glass cards and DataGrid`

---

### Task 6.2: Логин `admin/templates/login.php`

**Шаги:**
1. Заменить фоновый градиент на mesh-фон + тёмный `login-bg` (как в remnawave-admin: `#0a0e14` → `#111820`, анимированный градиент).
2. Карточка входа → `.glass-card` с анимацией появления, логотип со свечением (`.login-logo-glow`).
3. Кнопка входа → `.btn-primary btn-lg btn-block`.
4. Поля → стандартные стили форм.

**Проверка:** страница входа выглядит как у remnawave-admin, вход работает.

**Commit:** `feat(panel): restyle login page with mesh background and glass card`

---

### Task 6.3: Формы (перекраска классов)

**Файлы:** `posts/form.php`, `pages/form.php`, `menus/edit.php`, `settings/index.php`, `theme/index.php`

**Шаги:** заменить классы:
- `.btn btn-primary` → уже совпадает (в components.css определён)
- Старые обёртки форм → `.form-group`, `.form-row`, `.form-actions`
- Старые карточки → `.card`
- Старые alert → `.alert alert-*`
- Убрать `style="..."` инлайн-стили, если они конфликтуют с темой

**Правило:** структуру HTML и имена полей НЕ менять, только классы.

**Commit:** `feat(panel): restyle form pages with new components`

---

## Phase 7: Иконки Lucide

### Task 7.1: Заменить `core/helpers_icons.php` на Lucide

**Цель:** заменить Phosphor-подобные SVG на официальные иконки Lucide (stroke-based, 24×24, viewBox="0 0 24 24", stroke-width=2).

**Шаги:**
1. Скачать актуальные SVG-пути Lucide для нужных иконок с https://lucide.dev (имена: `dashboard`→`layout-dashboard`, `posts`→`file-text`, `categories`→`folder`, `pages`→`file`, `menus`→`menu`, `media`→`image`, `users`→`users`, `settings`→`settings`, `theme`→`palette`, `widgets`→`layout-grid`, `external`→`external-link`, `logout`→`log-out`, `back`→`arrow-left`, `add`→`plus`, `edit`→`pencil`, `delete`→`trash-2`, `save`→`save`, `view`/`eye`→`eye`, `message`→`message-square`, `search`→`search`, `hexa`→`hexagon`, `menu`→`panel-left` и т.д.)
2. Заменить массив `$icons` в `helpers_icons.php`, сохранив сигнатуру `icon($name, $class = '')`.
3. Каждая иконка — полный Lucide SVG: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">...` (пути с официального сайта).
4. **Совместимость:** имена ключей в массиве (`posts`, `categories` и т.д.) оставить прежними, чтобы не ломать вызовы `icon('posts')` в шаблонах. В layout (Task 2.2) при желании использовать новые ключи, добавив их в массив.

**Проверка:** все разделы админки отображают иконки, ни одна не пустая (пройтись по всем экранам).

**Commit:** `feat(panel): replace icons with Lucide set`

---

## Phase 8: Настройки вида (панель в шапке)

### Task 8.1: Выпадающая панель настроек

**Цель:** UI для переключения плотности, радиуса, размера шрифта, анимаций, темы и режима.

**Шаги:**
1. В `main.php` добавить рядом с `#theme-toggle` кнопку «Настройки вида» + dropdown с опциями:
   - Темы: 6 пресетов (Obsidian, Halo, Arctic, Sakura, Twilight, Ember) — `data-set-theme="obsidian"` и т.д.
   - Режим: Тёмный / Светлый — `data-set-mode="dark|light"`
   - Плотность: Compact / Comfortable / Spacious — `data-set-density="..."`
   - Радиус: Sharp / Default / Rounded — `data-set-radius="..."`
   - Размер шрифта: S / M / L — `data-set-font-size="..."`
   - Анимации: чекбокс вкл/выкл
2. Стили dropdown — в `components.css` (блок `.dropdown-menu`, `.dropdown-item`).
3. `panel.js` уже обрабатывает клики по `[data-set-*]` (добавить обработчики для radius/fontSize/animations, если не были добавлены).
4. Светлый/тёмный режим и тема сохраняются на сервер (Task 4.3), остальное — в localStorage.

**Проверка:** все настройки применяются сразу и сохраняются после перезагрузки.

**Commit:** `feat(panel): add appearance settings dropdown`

---

## Phase 9: Чистка и финальная проверка

### Task 9.1: Проверка «ничего не сломали»

**Шаги:**
1. Пройтись по ВСЕМ разделам админки: дашборд, посты (CRUD), категории (CRUD), страницы (CRUD + set-home), меню (CRUD), медиа (загрузка/удаление), пользователи (CRUD), настройки (сохранение), темы (активация), виджеты (CRUD), логин, логаут.
2. Проверить, что HexaVeil (главная страница) визуально не изменился.
3. Проверить, что блог (`/post/...`, `/category/...`, страницы) визуально не изменился.
4. Проверить отсутствие console-ошибок в браузере.
5. Убедиться, что ни один файл > 500 строк в новых файлах панели.

### Task 9.2: Обновить документацию

- Обновить `README.md` (структура, новые файлы).
- Записать решение в `docs/decisions/` (см. скил `documentation-and-adrs`): ADR-001 «Дизайн-система панели на базе remnawave-admin».

**Commit:** `docs: update README and add ADR-001 for panel design system`

---

## Финальный чек-лист (Success Criteria из спеки)

- [ ] Админка выглядит как remnawave-admin (тёмный сайдбар, glass, mesh, шрифты)
- [ ] Переключаются 6 тем + светлый режим, сохраняется в БД
- [ ] Настройки вида работают (плотность/радиус/шрифт/анимации)
- [ ] Все 7 списков на DataGrid
- [ ] Командная палитра Ctrl+K работает
- [ ] Сайдбар сворачивается
- [ ] Все CRUD работает 1:1
- [ ] HexaVeil и блог не изменились
- [ ] Нет файлов-монстров

---

## Примечания для исполнителя

- **Ветка:** рекомендуется `git checkout -b feat/panel-redesign` перед стартом.
- **Откат:** каждый шаг = коммит, откат через `git revert`/`git checkout`.
- **Незнакомые места:** перед изменением шаблона открыть соответствующий контроллер (`admin/controllers/*.php`) и посмотреть, какие переменные он передаёт.
- **Если встречается жёстко прописанный цвет** в старых шаблонах (`style="color:#fff"` и т.п.) — заменить на CSS-переменные или удалить.
- **Не удалять** `public/css/cms-tokens.css` и `public/css/style.css` — они нужны блогу. Админка переключается на `public/css/panel/*`.
