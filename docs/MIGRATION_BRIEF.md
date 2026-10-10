# Brief для агента-исполнителя: миграция админки на React SPA

> Прочитай этот файл ПЕРВЫМ. Это главная инструкция.

---

## 1. ЧТО ПРОЧИТАТЬ (строго в этом порядке)

| Очередь | Файл | Зачем |
|---------|------|-------|
| **1** | `docs/MIGRATION_TO_REMNAWAVE_STACK.md` | Полный план миграции — три фазы, очерёдность, запреты |
| **2** | `PROJECT.md` | Полное описание проекта — структура, БД, API, маршруты |
| **3** | `AGENTS.md` | Инструкции для ИИ-агентов в этом проекте |
| **4** | `core/routes.php` | Все маршруты и API-эндпоинты (смотреть строки 130–538 — это API для React) |
| **5** | `admin/templates/layouts/main.php` | Текущий layout админки (понять что уже есть) |

**Исходник remnawave:**
- `C:\Users\Andre\Desktop\VPN\remnawave-admin-main\web\frontend\` — React-фронтенд для копирования
- `C:\Users\Andre\Desktop\VPN\remnawave-admin-main\web\backend\` — FastAPI-бэкенд (для Фазы 2)

---

## 2. ЗАДАЧА

Перенести админку CMS с PHP SSR на React SPA, копируя remnawave-admin-main.

### Этапы (по порядку)

**Фаза 0 — расширить PHP API**
Добавить JSON-эндпоинты для: Widgets, Logs, Menus, Settings, Media, Themes (только настройки).
Смотреть существующие API-эндпоинты в `core/routes.php` (строки 130–538) — делать по аналогии.
Модели и контроллеры уже есть в `core/models/` и `admin/controllers/`.

**Фаза 1 — React SPA**
1. Скопировать `remnawave-admin-main/web/frontend/` → `admin-react/`
2. Удалить Remnawave-страницы (из `src/pages/` — всё кроме Login, Dashboard, Settings, NotFound; SystemLogs адаптировать)
3. Настроить vite.config.ts (прокси `/api` на PHP)
4. Переписать API-клиент (`src/api/client.ts`) под PHP JWT
5. Сделать страницы в порядке:
   - Login → Dashboard → Finance → Diagnostics → Logs → Posts → Pages → Users → Categories → Widgets → Menus → Settings → Media → ThemeManager
6. Гибридный режим: кнопка «Новая панель» в PHP-настройках

**Фаза 2 — FastAPI (когда Фаза 1 готова)**
1. Создать `backend/` со структурой как в remnawave (`web/backend/`)
2. SQLAlchemy модели под CMS-таблицы (posts, pages, users, media, menus, widgets, settings, fin_transactions, app_logs)
3. Переносить эндпоинты по одному: PHP → FastAPI

---

## 3. ЧЕГО НЕ ДЕЛАТЬ (ЖЁСТКИЕ ЗАПРЕТЫ)

### Дизайн
- НЕ менять дизайн remnawave — ни цвета, ни шрифты, ни отступы, ни glass-эффекты
- НЕ добавлять свои CSS-файлы — весь CSS в `src/index.css`
- НЕ использовать другие UI-библиотеки — только shadcn/ui (Radix UI)
- НЕ менять структуру Sidebar/Header/Layout — 100% копия remnawave
- Никаких «улучшений» дизайна — только точная копия

### Функционал
- НЕ добавлять страницы/функции, которых нет в PHP-админке
- НЕ урезать функционал — всё что есть в PHP, должно быть в React
- НЕ переименовывать разделы, кнопки, колонки
- Любые улучшения — только после полного завершения миграции

### API и данные
- НЕ менять формат ответа существующих `/api/*` эндпоинтов
- НЕ менять имена полей в JSON (PHP возвращает `created_at` — в React и FastAPI тоже `created_at`)
- НЕ менять схему БД (`db/postgres/init/01-schema.sql`)
- НЕ создавать параллельных таблиц с теми же данными
- НЕ мигрировать данные между PHP и FastAPI вручную

### Безопасность
- НЕ трогать nginx на проде без теста
- НЕ деплоить React пока не готов Login + Dashboard
- НЕ удалять PHP-админку пока все страницы не перенесены
- НЕ удалять PHP-файлы — они всё ещё нужны как API (Фаза 1) или как fallback

---

## 4. ГДЕ ЧТО ЛЕЖИТ

| Что | Путь |
|-----|------|
| **Новый React-проект** (создать) | `admin-react/` |
| **PHP JSON API** (уже есть) | `core/routes.php` (строки 130–538) |
| **Модели PHP** | `core/models/` |
| **Контроллеры админки** | `admin/controllers/` |
| **Схема БД** | `db/postgres/init/01-schema.sql` |
| **Докер-композ** | `docker-compose.yml` |
| **Nginx конфиг** | `.docker/nginx/default.conf` |
| **Исходник remnawave фронтенд** | `C:\Users\Andre\Desktop\VPN\remnawave-admin-main\web\frontend\` |
| **Исходник remnawave бэкенд** | `C:\Users\Andre\Desktop\VPN\remnawave-admin-main\web\backend\` |
| **Текущий CSS админки (PHP)** | `public/css/panel/*.css` |
| **Текущие шаблоны админки (PHP)** | `admin/templates/` |

---

## 5. ОЧЕРЁДНОСТЬ СТРАНИЦ (строгая)

| # | Страница | API готов | Когда |
|---|----------|-----------|-------|
| 1 | Login | ✅ есть `/api/auth/login` | Фаза 1, шаг 1 |
| 2 | Dashboard | ✅ есть `/api/dashboard/stats` | Фаза 1, шаг 1 |
| 3 | Finance | ✅ есть Finance API | Фаза 1, шаг 2 |
| 4 | Diagnostics | ✅ есть `/admin/diagnostics/api/data` | Фаза 1, шаг 2 |
| 5 | Logs | ⚠️ нужен `/api/logs/*` | Фаза 0 + Фаза 1 |
| 6 | PostsList + PostEdit | ✅ есть `/api/posts/*` | Фаза 1, шаг 3 |
| 7 | PagesList + PageEdit | ✅ есть `/api/pages/*` | Фаза 1, шаг 3 |
| 8 | UsersList + UserEdit | ✅ есть `/api/users/*` | Фаза 1, шаг 4 |
| 9 | Categories | ✅ есть `/api/categories/*` | Фаза 1, шаг 4 |
| 10 | Widgets | ⚠️ нужен `/api/widgets/*` | Фаза 0 + Фаза 1 |
| 11 | Menus | ⚠️ нужен `/api/menus/*` | Фаза 0 + Фаза 1 |
| 12 | Settings | ⚠️ нужен `/api/settings` | Фаза 0 + Фаза 1 |
| 13 | Media | ⚠️ нужен `/api/media/*` | Фаза 0 + Фаза 1 |
| 14 | ThemeManager | ⚠️ нужен `/api/themes/settings` | Фаза 0 + Фаза 1 |

---

## 6. КЛЮЧЕВЫЕ РЕШЕНИЯ (НЕ ПЕРЕСПРАШИВАТЬ)

- React-проект лежит в `admin-react/` внутри этого репозитория
- Публичный сайт (лендинг) остаётся на PHP — НЕ ТРОГАТЬ
- Гибридный режим: кнопка «Новая панель» в PHP-настройках
- ThemeManager: только настройки активной темы (без .zip загрузки и переключения)
- После Фазы 1 → Фаза 2 (FastAPI) для интеграции с Remnawave
- Иконки: Lucide React (из remnawave)

---

## 7. ФОРМАТ ОТВЕТА API (ВЕЗДЕ ОДИНАКОВЫЙ)

```json
{
  "success": true,
  "data": [ ... ]
}
```

При ошибке:
```json
{
  "success": false,
  "error": "Описание ошибки"
}
```

---

## 8. ПРОВЕРКА ПЕРЕД ДЕПЛОЕМ

- [ ] Login + Dashboard работают на React
- [ ] Все API-эндпоинты отвечают (нет 404/500 на React-запросах)
- [ ] Гибридный режим: кнопка переключает между React и PHP
- [ ] PHP-админка всё ещё доступна (для страниц, которые ещё не в React)
- [ ] Дизайн совпадает с remnawave (проверить на глаз: sidebar, карточки, таблицы, mesh-фон, темы)
- [ ] Нет CORS-ошибок в консоли браузера
- [ ] Настройки вида (тема, плотность, радиус) сохраняются и применяются