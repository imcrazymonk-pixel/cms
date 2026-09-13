# NewWeb CMS — Project Overview

## Что это за проект

Собственная **PHP CMS** (без фреймворков) поверх MySQL. Изначально — стандартный
блог-движок, сейчас превращается в **многофункциональный сайт VPN-сервиса**:

- **Публичная часть** — лендинг HexaVeil (тема `hexaveil`) с 3D-глобусом серверов,
  тарифами, FAQ и **блогом** (добавлено недавно, см. `/blog`)
- **Админ-панель** — собственная система управления контентом с редизайном в стиле
  remnawave (тёмная тема, mesh-фон, glass-эффекты, командная палитра)

### Домен и окружение

- Домен: `http://hexacms` (Apache из Open Server Panel)
- PHP 8.1+ (последняя версия из OSPanel)
- MySQL через `127.127.126.26` (виртуальный IP Open Server Panel)
- **Никаких npm/сборщиков** — только vanilla CSS/JS/PHP

---

## Архитектура

```
NewWeb/
├── index.php              # Front-контроллер (маршрутизация)
├── config/config.php      # Настройки БД, путей, константы
├── core/                  # Ядро CMS
│   ├── Router.php         # Маршрутизатор (GET/POST, паттерны {slug})
│   ├── routes.php         # Все маршруты сайта
│   ├── TemplateEngine.php # Шаблонизатор (set/display, layouts)
│   ├── Database.php       # PDO-обёртка
│   ├── Post.php           # Модель постов (CRUD, категории, теги, комменты)
│   ├── Category.php       # Модель категорий
│   ├── Page.php           # Модель страниц
│   ├── User.php           # Модель пользователей
│   ├── Auth.php           # Аутентификация (admin)
│   ├── helpers.php        # Утилиты (truncate, format_date, createTemplate)
│   ├── helpers_icons.php  # Inline Lucide SVG-иконки (icon())
│   ├── DataGrid.php       # Рендерер таблиц для списков админки
│   └── Autoloader.php     # PSR-4 автозагрузка
├── admin/                 # Админ-панель
│   ├── controllers/       # Контроллеры (Posts, Pages, Categories, Media, etc.)
│   ├── templates/         # PHP-шаблоны (layouts/main, posts/form, login, etc.)
│   ├── js/panel.js        # JS панели (настройки вида, DataGrid, превью)
│   └── js/command-palette.js # Командная палитра (Ctrl+K)
├── templates/
│   └── themes/
│       ├── hexaveil/      # АКТИВНАЯ ТЕМА — VPN лендинг + блог
│       ├── modern/        # Запасная блог-тема
│       ├── minimal/       # Запасная блог-тема
│       └── default/       # Базовая блог-тема
├── public/
│   ├── hexaveil/          # CSS/JS/ассеты темы HexaVeil
│   │   └── css/
│   │       ├── variables.css  # CSS-переменные (цвета, шрифты)
│   │       ├── global.css     # Глобальные стили (контейнер, кнопки, типографика)
│   │       └── style.css      # Стили секций + БЛОГ (добавлено недавно)
│   └── css/panel/         # Дизайн-система админки (7 файлов)
└── docs/decisions/
    └── ADR-001-panel-design-system.md  # Документация редизайна админки
```

---

## Статус реализации

### ✅ Реализовано

#### Ядро CMS
- [x] Маршрутизация (GET/POST, параметры, catch-all `{slug}`)
- [x] PDO-обёртка (fetch, fetchAll, insert, update, delete)
- [x] Шаблонизатор (layouts, секции, PHP-шаблоны)
- [x] Аутентификация (admin/editor/author роли)
- [x] CSRF-защита
- [x] Сессии
- [x] DataGrid — единый рендерер таблиц для админки
- [x] Inline Lucide SVG-иконки (icon())

#### Блог
- [x] Таблицы: posts, categories, tags, post_tags, comments (MySQL)
- [x] Полный CRUD постов (админка)
- [x] TinyMCE → CKEditor 5 (ESM, все плагины, esm.sh CDN)
- [x] Категории, теги, комментарии (модерация)
- [x] Загрузка изображений (/admin/media/upload)
- [x] Счётчик просмотров
- [x] Маршруты: /blog, /post/{slug}, /category/{slug}
- [x] Шаблон блога в стиле HexaVeil (glass-карточки, pill-фильтр категорий)

#### Тема HexaVeil (лендинг)
- [x] 3D-глобус с серверами (Three.js)
- [x] Tagline + Hero-секция
- [x] Преимущества, тарифы (пробный доступ), сервисы
- [x] Технологии, реферальная программа
- [x] FAQ (аккордеон)
- [x] Подвал с меню и соцсетями
- [x] Звёздный фон (canvas)
- [x] Glassmorphism-карточки, тёмная киберпанк-эстетика
- [x] Адаптивность (мобильные планшеты)
- [x] **Блог** — добавлен недавно (маршрут + шаблон + стили + ссылка в навигации)
- [x] **Страница категории** — обновлена в стиле блога

#### Админ-панель
- [x] Редизайн: тёмная тема, mesh-фон, glass-эффекты
- [x] 6 акцентных пресетов (Obsidian, Halo, Arctic, Sakura, Twilight, Ember)
- [x] Светлая тема ([data-mode="light"])
- [x] Командная палитра (Ctrl+K)
- [x] Настройки вида (тема/режим/плотность/радиус/шрифт) — per-user в БД
- [x] DataGrid-таблицы для всех списков
- [x] CKEditor 5 (import map через esm.sh, все плагины)
- [x] Кастомный адаптер загрузки изображений для CKEditor

### 🔄 В процессе / запланировано

#### Финансы (VPN-биллинг)
- [ ] Интеграция с Remnawave panel API
- [ ] Отображение транзакций, подписок, статусов пользователей
- [ ] Страница /admin/finance (уже есть в меню, контроллер не реализован)

#### Блог (доработки)
- [ ] Пагинация на /blog (сейчас только POSTS_PER_PAGE без ссылок «далее/назад»)
- [ ] Поиск по постам
- [ ] RSS-лента
- [ ] Валидация slug-ов (если пост удалён, slug может конфликтовать)
- [ ] Автосохранение черновиков (есть закомментированный код в CKEditor config)

#### Тема HexaVeil (доработки)
- [ ] Секция тарифов (сейчас закомментирована в навигации)
- [ ] Страница «Политика конфиденциальности»
- [ ] Страница «Условия использования»
- [ ] Хлебные крошки на странице поста
- [ ] Счётчик слов/время чтения на статье
- [ ] Оптимизация Three.js для мобильных (сейчас грузит текстуру всегда)
- [ ] Tеги на карточках постов
- [ ] Related posts на странице поста (уже в роуте, надо отобразить)

#### Админ-панель
- [ ] CRUD категорий (админка есть — проверить/дополнить)
- [ ] CRUD тегов
- [ ] CRUD комментариев
- [ ] CRUD медиа (список есть, удаление есть, загрузка есть)
- [ ] CRUD меню
- [ ] CRUD виджетов
- [ ] Управление темой (активация/деактивация/настройки) — страница /admin/theme есть
- [ ] Логи (просмотр системных ошибок)
- [ ] Dashboard с графиками (Chart.js — уже подключён в теме hexaveil)
- [ ] Экспорт постов в Markdown/HTML

#### Общее
- [ ] Резервное копирование БД
- [ ] Sitemap.xml
- [ ] robots.txt
- [ ] Кеширование (APCu или файловый кеш)
- [ ] SEO-оптимизация (meta, og, canonical — базово есть)
- [ ] Мультиязычность (RU/en)
- [ ] Тесты (хотя бы smoke-тесты для маршрутов)

---

## Ключевые паттерны и решения

### Добавление новой страницы

1. Добавить маршрут в `core/routes.php` (ДО catch-all `{slug}`)
2. Создать шаблон в `templates/themes/hexaveil/`
3. Стили — в `public/hexaveil/css/style.css`
4. Если нужно в навигации — добавить ссылку в `layouts/main.php`

### Обработка форм

```php
$router->post('admin/posts/store', function() {
    Auth::requireAdmin();
    if (!verify_csrf()) die('CSRF token invalid');
    $title = trim(Request::post('title', ''));
    // ... process & redirect
});
```

### Шаблонизатор

```php
$template = createTemplate();  // автоматически выбирает активную тему
$template->set('title', 'Заголовок');
$template->set('seo', ['title' => '...', 'description' => '...']);
$template->set('menuItems', loadMenuItems('main', 'current-slug'));
$template->set('footerMenu', loadFooterMenu());
$template->setLayout('layouts/main');
$template->display('template-name'); // templates/themes/{theme}/template-name.php
```

### Тема HexaVeil — дизайн-токены (CSS-переменные)

```css
--bg-primary: #0a0a1a;        /* основной фон */
--bg-glass: rgba(24,24,27,0.6); /* glass-карточки */
--accent-primary: #a855f7;     /* purple (кнопки, ссылки) */
--accent-glow: rgba(168,85,247,0.4); /* свечение */
--text-primary: #fafafa;
--text-secondary: #a1a1aa;
--border-color: rgba(168,85,247,0.2);
--font-heading: 'Noto Serif', Georgia, serif;
--font-body: 'Inter', system-ui, sans-serif;
```

### Админ-панель — дизайн-токены

```css
--bg-base: hsl(222 22% 8%);        /* фон */
--bg-surface: hsl(222 18% 12%);   /* поверхности */
--glass-bg: hsla(222 18% 18% / 0.4); /* glassmorphism */
--accent: hsl(239 84% 67%);       /* акцент (по умолчанию Obsidian) */
--text-primary: hsl(210 17% 92%);
--text-secondary: hsl(215 14% 65%);
```

---

## Как запустить

Проект работает на **Open Server Panel**:
- Домен: `http://hexacms`
- Админка: `http://hexacms/admin`
- Логин: `admin`
- Пароль: `admin12345`
- MySQL: `127.127.126.26`, БД: `cms`

Обычная установка:
1. Скопировать файлы в `C:\OSPanel\home\HexaCMS\public\`
2. Импортировать `database.sql` в MySQL
3. Настроить `config/config.php` (DB_HOST, DB_NAME, DB_USER, DB_PASS)
4. Открыть `http://hexacms` в браузере

---

## Технические ограничения

- **Никаких npm/сборщиков** — весь код vanilla
- **Файлы не больше 500 строк** (правило проекта; style.css — исключение ~1800 строк)
- **Не трогать публичную часть** (если задача только про админку)
- **Не менять маршруты/контроллеры/логику/имена полей форм** без необходимости
- **PHP 7.4+** для совместимости с OSPanel
- **Не коммитить папку `Fin/`**