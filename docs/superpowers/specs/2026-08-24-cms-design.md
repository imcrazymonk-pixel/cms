# Design System: CMS NewWeb (Admin Panel + Blog)

> **HEXAVEIL THEME IS OUT OF SCOPE.** This design system covers only:
> - Admin panel (`admin/`)
> - Blog frontend (`public/css/style.css` + theme templates)

---

## 1. Visual Theme & Atmosphere

**Admin Panel** — "Instrumental, clean, confident." A professional tool for developers and content managers. Not entertaining, but pleasant to work in. Density: 6/10, Variance: 5/10, Motion: 5/10. Neutral base with a single indigo accent. Dark sidebar anchors the layout, light body keeps content readable.

**Blog Frontend** — "Reader-first, airy, typographic." Content takes center stage. Density: 4/10, Variance: 6/10, Motion: 4/10. Warm off-white background, dark charcoal text, generous whitespace around articles.

---

## 2. Color Palette & Roles

### Admin Panel

| Name | Hex | Role |
|---|---|---|
| **Canvas** | `#f5f5f7` | Page background |
| **Card** | `#ffffff` | Cards, tables, forms |
| **Sidebar** | `#1e1e2e` | Navigation panel background |
| **Sidebar Hover** | `#2a2a3e` | Nav item hover |
| **Indigo** | `#6366f1` | Primary accent — CTAs, active nav, links |
| **Indigo Hover** | `#4f46e5` | Button hover |
| **Text Primary** | `#1a1a2e` | Headings, body |
| **Text Secondary** | `#6b7280` | Labels, descriptions |
| **Text Muted** | `#9ca3af` | Meta, timestamps |
| **Border** | `#e5e7eb` | Card borders, dividers |
| **Green** | `#22c55e` | Success |
| **Red** | `#ef4444` | Danger |
| **Amber** | `#f59e0b` | Warning |

**Banned:** Purple/blue gradient (`#667eea → #764ba2`), pure blue (`#3b82f6`), pure black (`#000000`).

### Blog Frontend

| Name | Hex | Role |
|---|---|---|
| **Canvas** | `#fafafa` | Page background |
| **Card** | `#ffffff` | Post cards, comments |
| **Text Primary** | `#18181b` | Headings |
| **Text Body** | `#3f3f46` | Body content |
| **Text Muted** | `#a1a1aa` | Meta, timestamps |
| **Accent** | `#6366f1` | Links, tags, badges |
| **Footer** | `#18181b` | Site footer |

**Banned:** Inter font, system-ui stack, purple gradient on hero.

---

## 3. Typography Rules

- **Display/UI (Admin):** `Outfit` — clean geometric sans, 400/500/600/700 weights. Tight tracking for UI elements.
- **Body (Blog):** `Outfit` — same family across admin and blog for consistency.
- **Mono:** `JetBrains Mono` — for code, IDs, timestamps, metadata.
- **Scale:** 12px (captions) → 14px (body) → 16px (large body) → 20px (h3) → 24px (h2) → 28-36px (h1).
- **Max body width:** 65ch for paragraphs.
- **Banned:** Inter, Roboto, Arial, Open Sans, Helvetica, Times New Roman, Georgia, Garamond.

---

## 4. Component Stylings

### Buttons
- Flat, no outer glow. `border-radius: 6px`.
- Primary: Indigo fill (`#6366f1`), white text.
- Secondary: Muted gray fill (`#9ca3af`), white text.
- Hover: Background shift + subtle shadow elevation.
- Active: `scale(0.97)` for tactile feedback.
- Focus-visible: 2px solid Indigo outline + 2px offset.
- Icons inside buttons: `gap: 8px`, inline SVG at 1.25em.

### Cards
- Used only when elevation communicates hierarchy.
- White background, 1px solid border (`#e5e7eb`), tinted shadow (`0 1px 3px rgba(0,0,0,0.06)`).
- `border-radius: 10px` (--radius-md).
- Hover: subtle translateY(-2px) + deeper shadow.
- **No** border + shadow + white triple combo on every card — vary by context.

### Sidebar
- Dark background (`#1e1e2e`), fixed position, full height.
- Nav items: 3px left border accent on active state.
- Icons: 18px, opacity 0.7, full opacity on active.
- Footer section with logout — red tint on hover.

### Tables
- Border-collapse: separate with `border-spacing: 0`.
- Header row: uppercase, 12px, muted color, letter-spacing 0.05em.
- Row hover: subtle gray background.
- Last row: no bottom border.
- Actions column: flex with 4px gap, no wrap.

### Forms
- Labels above input. Helper text below.
- Input: 2px border, 12px padding, rounded 6px.
- Focus: Indigo border + subtle glow (`rgba(99,102,241,0.12)`).
- Error text below input in red.

### Skeleton Loaders
- Shimmer animation (gradient sweep left to right).
- Shapes: text lines, cards, table rows.
- Match layout dimensions exactly.

### Empty States
- Centered illustration (icon in rounded box) + heading + description + CTA button.
- Never just "No data found" text.

---

## 5. Layout Principles

- **CSS Grid** over flexbox math. No `calc()` percentage hacks.
- **Max-width** container at 1200px for blog, fluid for admin.
- **Full-height sections:** use `min-height: 100dvh`, never `h-screen`.
- **3 equal columns** is BANNED for feature rows. Use asymmetric or 2-column zig-zag.
- **Admin sidebar:** fixed 260px, content area uses margin-left.
- **Responsive collapse:** below 768px — sidebar slides off-screen, table stacks, grid collapses to 1 column.

---

## 6. Motion & Interaction

- **Transitions:** 150ms ease for micro-interactions (hover, focus).
- **Spring-like:** `250ms ease` for larger transitions (card hover lift).
- **Scroll reveal:** smooth `scroll-behavior: smooth` on `html`.
- **Button press:** `scale(0.97)` on `:active`.
- **No** animation of `top`, `left`, `width`, `height` — only `transform` and `opacity`.
- **No** GSAP, no external animation libraries.

---

## 7. Responsive Rules

- **Mobile-first collapse (< 768px):** multi-column → single column.
- **No horizontal scroll** on any viewport.
- **Typography:** headlines scale via `clamp()`. Body minimum `14px`.
- **Touch targets:** interactive elements minimum `44px` tap target.
- **Sidebar on mobile:** hidden off-screen, no toggle button yet (future).

---

## 8. Anti-Patterns (Banned)

- No emojis in UI (use SVG icons instead)
- No Inter font
- No system-ui font stack without replacement
- No pure black (`#000000`) backgrounds
- No generic `box-shadow: 0 2px 8px rgba(0,0,0,0.1)` — use tinted shadows
- No purple/blue gradient (`#667eea → #764ba2`)
- No 3-column equal card rows
- No "border + shadow + white bg" combo on every card
- No AI copywriting clichés ("Elevate", "Seamless", "Next-Gen")
- No Lorem Ipsum — write real content
- No `window.alert()` for errors
- No broken image links — use proper fallbacks
- No left sidebar as default admin layout without consideration of alternatives