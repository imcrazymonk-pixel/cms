# Spec: HexaVeil CMS — React Admin Migration

## Architecture

| Слой | Фаза 1 | Фаза 2 (потом) |
|------|--------|----------------|
| Frontend | React + TypeScript SPA | React + TypeScript SPA |
| Backend | PHP JSON API (существующий CMS) | Python FastAPI (как Remnawave) |
| Auth | JWT (POST /api/auth/login) | JWT + TOTP |
| БД | PostgreSQL (существующая) | PostgreSQL |

React SPA в `/cms-admin/`, потом переключение `/admin/` → SPA.

---

## Login Page

### Визуал (копия Remnawave 1:1)
- Mesh-градиентный фон (div.mesh-bg + mesh-layer)
- Glass-heavy карточка (Card: rounded-2xl, glass-heavy, box-shadow с glass-highlight)
- Верхняя градиентная accent-линия (accent-from → accent-to → transparent)
- Логотип HexaVeil (вместо BrandLogo Remnawave)
- Заголовок «Вход в админку HexaVeil»
- Анимации fade-in, scale-in, stagger
- Адаптив (max-w-[420px], центрирование, p-4)
- Поле Username с иконкой User слева
- Поле Password с иконкой Lock слева + кнопка show/hide (Eye/EyeOff)
- Кнопка входа: градиент teal-600 → cyan-600, h-11, w-full
- Ссылка «Вернуться на сайт» внизу
- Состояния: loading (спиннер), error (красный alert с крестиком)

### UI-компоненты для копирования (из remnawave-admin-main)
- Button.tsx — primary (teal→cyan gradient), ghost, variant, size
- Input.tsx — с иконками, glass-стиль
- Label.tsx — подписи полей
- Card.tsx — CardHeader, CardContent, glass-heavy
- PasswordInput — show/hide password

### Логика (адаптированная)
- Форма: username + password → POST /api/auth/login
- Ответ: { token: string, user: { id, username, email, role } }
- JWT → Zustand authStore + localStorage
- Редирект на /admin/ после успеха
- Если уже авторизован → сразу редирект
- Ошибка → показать красный alert с текстом и крестиком
- Loading → спиннер + disabled кнопка

### Не включаем (будут в Фазе 2 при Python-бэкенде)
- ❌ Telegram-виджет
- ❌ TOTP 2FA (setup + verify)
- ❌ Initial Setup (регистрация первого админа)
- ❌ Password strength meter
- ❌ Password generator
- ❌ i18n (используем русский текст напрямую)

### PHP API
- core/JWTAuth.php — генерация и проверка JWT (HMAC-SHA256)
- POST /api/auth/login — { login, password } → { token, user } | { error }
- POST /api/auth/me — Bearer token → { user }

---

## Dashboard

### Визуал (из Remnawave StatCard)
- StatCard компонент: стеклянная карточка с:
  - Левая часть: число (count-up анимация 0→N) + подпись
  - Правая часть: иконка в цветной обводке (p-2.5 rounded-xl)
  - Верхняя accent-линия (h-[2px], градиент)
  - Hover: подъём -translate-y-1, glow-эффект
  - Цвета: cyan, green, yellow, red, violet, pink
  - animation-delay для stagger
- Grid 4 карточки (responsive: 1→2→4 колонки)
- Glass-таблица «Последние посты» (ID, заголовок, статус badge, дата, действия edit/view)
- Glass-секция «Быстрые действия» (4 кнопки: Новый пост, Категории, Медиа, Настройки)

### Данные (наши метрики)
Вместо users/nodes/violations Remnawave — наши 4:
- Посты (Posts) — cyan
- Комментарии (Comments) — green
- Пользователи (Users) — violet
- Категории (Categories) — yellow

### API эндпоинты
- GET /api/stats — { posts, comments, users, categories }
- GET /api/posts?limit=5 — последние посты для таблицы

### Не включаем
- ❌ Recharts (графики)
- ❌ TanStack Query (простой fetch + useEffect)
- ❌ DnD (сортируемые секции)
- ❌ @dnd-kit
- ❌ Violations, Collector, Node Fleet, Billing, System Status, Updates
- ❌ i18n

---

## Posts (CRUD)

### Визуал (из Remnawave)
- DataGrid-таблица: стеклянная, с колонками, пагинацией, поиском
- Badge для статуса (published=green, draft=yellow, archived=red)
- Кнопки edit/delete в каждой строке
- Форма создания/редактирования поста
- Editor с CKEditor 5 (остаётся как есть, подключается через CDN)
- Модальное окно подтверждения удаления

### Страницы
1. **PostsList** — таблица всех постов (ID, заголовок, категория, статус, дата, действия)
2. **PostForm** — создание/редактирование (заголовок, slug, контент, категория, статус, мета-теги)
3. **Categories/CategoriesList** — таблица категорий (ID, название, slug, кол-во постов, действия)

### API эндпоинты
- GET /api/posts — список (с пагинацией: page, limit)
- GET /api/posts/{id} — один пост
- POST /api/posts — создать
- PUT /api/posts/{id} — обновить
- DELETE /api/posts/{id} — удалить
- GET /api/categories — список категорий
- POST /api/categories — создать
- PUT /api/categories/{id} — обновить
- DELETE /api/categories/{id} — удалить

### Нюансы
- CKEditor 5 грузится с CDN (как сейчас в PHP) — React-обёртка
- Slug авто-генерация из заголовка
- Статусы: published, draft, archived

---

## Pages (CRUD)

### Визуал
- DataGrid-таблица страниц
- Form для создания/редактирования (заголовок, slug, контент, шаблон, статус)

### Страницы
1. **PagesList** — таблица всех страниц
2. **PageForm** — создание/редактирование

### API
- GET /api/pages — список
- GET /api/pages/{id} — одна страница
- POST /api/pages — создать
- PUT /api/pages/{id} — обновить
- DELETE /api/pages/{id} — удалить

---

## Users (CRUD)

### Визуал
- DataGrid-таблица пользователей (ID, логин, email, роль, дата регистрации, статус)
- Form создания/редактирования (логин, email, пароль, роль)
- Подтверждение удаления (нельзя удалить себя)

### API
- GET /api/users — список
- GET /api/users/{id} — один пользователь
- POST /api/users — создать
- PUT /api/users/{id} — обновить
- DELETE /api/users/{id} — удалить

---

## Media (File Manager)

### Визуал
- Grid миниатюр (imgs), список файлов
- Drag & drop загрузка
- Upload progress bar
- Копирование URL файла

### API
- GET /api/media — список файлов
- POST /api/media/upload — загрузить файл (multipart)
- DELETE /api/media/{id} — удалить

---

## Menus

### Визуал
- Drag & drop редактор меню (стеклянные items)
- Добавление пунктов (ссылка, заголовок)
- Reorder

### API
- GET /api/menus — список меню
- POST /api/menus — создать
- PUT /api/menus/{id} — обновить
- DELETE /api/menus/{id} — удалить
- PUT /api/menus/{id}/items — обновить порядок пунктов

---

## Widgets

### Визуал
- Список виджетов
- Включение/выключение
- Порядок

### API
- GET /api/widgets — список
- PUT /api/widgets/{id} — обновить (вкл/выкл, порядок)

---

## Theme

### Визуал
- Превью текущей темы
- Загрузка .zip темы
- Аккордеон-секции настроек

### API
- GET /api/theme — текущая тема
- POST /api/theme/upload — загрузить .zip

---

## Settings

### Визуал
- Форма настроек (группы: основные, почта, SEO, безопасность)
- Сохранение через auto-save или кнопку

### API
- GET /api/settings — все настройки
- POST /api/settings — сохранить

---

## Finance

### Визуал
- Статистика (итого за месяц, всего)
- DataGrid транзакций (дата, сумма, статус, провайдер)
- Настройки провайдеров

### API
- GET /api/finance/stats — статистика
- GET /api/finance/transactions — список транзакций
- GET /api/finance/providers — список провайдеров

---

## Logs

### Визуал
- DataGrid логов (дата, уровень, сообщение, источник)
- Фильтры по уровню и дате

### API
- GET /api/logs — список логов (с фильтрами)

---

## Layout (общий для всех страниц)

### Визуал (из Remnawave)
- **Sidebar**: стеклянный, фиксированный, с иконками, секциями (Контент, Внешний вид, Пользователи, Система)
- **Header**: стеклянный, с breadcrumbs, аватаром пользователя, выпадающим меню (выйти)
- **Content area**: padding, scroll
- **Theme system**: 6 пресетов (obsidian, halo, arctic, sakura, twilight, ember) + dark/light mode

### Навигация
- Posts, Pages, Categories → секция «Контент»
- Theme, Menus, Widgets → секция «Внешний вид»
- Users → секция «Пользователи»
- Media, Settings, Finance, Logs → секция «Система»

### Auth flow
1. Login → JWT → localStorage + Zustand
2. ProtectedRoute проверяет authStore, редиректит на /login при отсутствии токена
3. axios-интерцептор добавляет Bearer token к каждому запросу
4. При 401 → очистка authStore, редирект на /login

---

## UI-компоненты (общие)

Из remnawave-admin-main/web/frontend/src/components/ui/ копируем:
- Button.tsx
- Input.tsx
- Label.tsx
- Card.tsx (CardHeader, CardContent, CardTitle)
- Badge.tsx
- Separator.tsx
- Checkbox.tsx
- Select.tsx
- ScrollArea.tsx
- Tooltip.tsx

### Утилиты
- lib/utils.ts — cn() для classnames
- lib/api-client.ts — axios instance с Bearer token
- store/authStore.ts — Zustand store

---

## Порядок миграции (страницы)

1. Task 0: PHP JWT Auth (core/JWTAuth.php + /api/auth/ endpoints)
2. Task 1: Scaffold React + Layout (Sidebar, Header, themes)
3. Task 2: Login Page
4. Task 3: Dashboard
5. Task 4: Posts (List + Form + Categories)
6. Task 5: Pages
7. Task 6: Users
8. Task 7: Media
9. Task 8: Menus + Widgets + Theme
10. Task 9: Settings + Finance + Logs
11. Task 10: Nginx cutover (/admin → React SPA)