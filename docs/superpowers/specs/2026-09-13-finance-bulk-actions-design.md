# Finance Module — Bulk Actions Redesign (remnawave-style)

## Изменения

Привести UI финансового модуля к стилю remnawave-admin Users page:
- Плавающая стеклянная панель массовых действий
- remnawave-style dropdown меню (Экспорт, Тип)
- remnawave-style модалки для ввода (Категория, Участник, Описание)
- remnawave-style ConfirmDialog для удаления
- Анимация появления/исчезновения
- Выделение строк через чекбоксы (cross-page selection)

## Файлы изменений

### backend
- `admin/controllers/FinanceController.php` — новые API эндпоинты для bulk: type, category, participant, description, export-selected
- `core/models/FinTransaction.php` — bulkUpdate($ids, $data)

### frontend
- `admin/js/finance/finance.js` — bulk toolbar, dropdown, модалки, cross-page selection
- `public/css/panel/finance.css` — стеклянная панель, dropdown, анимация
  
### template
- `admin/templates/finance/index.php` — добавить разметку панели, dropdown, модалок

## API endpoints (новые)

| Method | Endpoint | Body | Описание |
|--------|----------|------|----------|
| POST | `/admin/finance/api/bulk/type` | { csrf_token, ids, type } | Сменить тип income/expense |
| POST | `/admin/finance/api/bulk/category` | { csrf_token, ids, category } | Сменить категорию |
| POST | `/admin/finance/api/bulk/participant` | { csrf_token, ids, participant } | Сменить участника |
| POST | `/admin/finance/api/bulk/description` | { csrf_token, ids, description } | Сменить описание |

## UI Components

### 1. Floating Bulk Toolbar (remnawave-style)
- `position: sticky; bottom: 1rem; z-index: 30`
- Glassmorphism: `backdrop-filter: blur(24px)`, border, shadow
- Animation: `animate-fade-in-up` (opacity 0→1, translateY 8px→0)
- Счётчик: "Выбрано: 3" (если часть не на странице: "(2 на этой странице)")

### 2. Dropdown Menu (Экспорт, Тип)
remnawave-style dropdown:
- `position: absolute; right: 0; min-width: 160px`
- Glassmorphism фон, border, тень
- Items: hover подсветка, иконка слева

### 3. Dialog модалки (Категория, Участник, Описание)
remnawave-style small dialog:
- `max-width: 400px`, border, glass bg
- Header: title + close (X)
- Body: поле ввода (input/textareа) + autocomplete datalist
- Footer: Cancel + Apply кнопки

### 4. Confirm Dialog (Удалить)
remnawave AlertDialog стиль:
- "Удалить N операций?" + пояснение
- Cancel + Delete (danger) кнопки

## Implementation order
1. Controller: bulk endpoints
2. Model: bulkUpdate
3. Template: разметка панели, dropdown, модалок
4. CSS: стеклянная панель, анимация, dropdown
5. JS: bulk toolbar, логика dropdown и модалок