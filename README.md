# HexaVeil CMS

Собственная PHP CMS (vanilla, без фреймворков) для VPN-сервиса. Запуск через Docker.

## 🚀 Быстрый старт (Docker)

```bash
# 1. Клонировать репозиторий
git clone <repo> && cd NewWeb

# 2. Настроить .env (можно оставить дефолтный)
cp .env.example .env
# Отредактировать если нужно: пароль БД, ключ шифрования

# 3. Запустить
docker compose up --build -d

# 4. Открыть в браузере
open http://localhost
```

### Логин по умолчанию

- **Сайт**: `http://localhost`
- **Админка**: `http://localhost/admin`
- **Логин**: `admin`
- **Пароль**: `Cke;bkb2Njdfhbof`

### Основные команды

```bash
# Запустить
docker compose up -d

# Пересобрать после изменений
docker compose up --build -d

# Остановить
docker compose down

# Смотреть логи
docker compose logs -f app

# Зайти в контейнер PHP
docker compose exec app sh

# Подключиться к БД
docker compose exec db psql -U cms -d cms
```

## 📋 Требования

### Docker (рекомендуется)
- Docker Engine 24+
- Docker Compose v2
- 1 CPU, 1 GB RAM

## 🐘 База данных

### Docker (PostgreSQL)
При первом запуске БД создаётся автоматически через `db/postgres/init/01-schema.sql`:
- Все таблицы: users, posts, categories, tags, comments, pages, menus, widgets, media, settings, fin_transactions, app_logs, user_preferences
- Seed-данные: администратор, категории, настройки сайта, настройки финансов
- `install.lock` создаётся автоматически entrypoint-ом

Вся конфигурация читается из переменных окружения (`.env`).

## 🗂️ Структура проекта

```
NewWeb/
├── index.php                 # Front-контроллер
├── Dockerfile                # PHP 8.1-FPM Alpine
├── docker-compose.yml        # Nginx + PHP + PostgreSQL
├── docker-entrypoint.sh      # Инициализация при старте
├── .env                      # Переменные окружения (НЕ в git)
├── .env.example              # Шаблон .env
├── .docker/
│   ├── nginx/default.conf    # Nginx vhost
│   └── php/php.ini           # PHP настройки
├── config/
│   └── config.php            # Конфигурация (env-aware)
├── core/                     # Ядро CMS
│   ├── models/               # Модели (Post, User, Category, FinTransaction...)
│   ├── Database.php          # PDO-wrapper (mysql/pgsql)
│   ├── Router.php            # Маршрутизатор
│   ├── TemplateEngine.php    # Шаблонизатор
│   ├── Auth.php              # Аутентификация
│   ├── DataGrid.php          # Рендерер таблиц
│   └── ...
├── admin/                    # Админ-панель
│   ├── controllers/          # Контроллеры (Posts, Finance, Theme...)
│   ├── templates/            # Шаблоны
│   └── js/                   # panel.js, command-palette.js
├── templates/themes/
│   └── hexaveil/             # VPN-лендинг тема (HexaVeil)
├── public/
│   ├── hexaveil/css/         # Стили темы
│   └── css/panel/            # Дизайн-система админки (7 файлов)
├── db/
│   ├── postgres/init/01-schema.sql  # PostgreSQL схема
│   └── migrations/           # MySQL-миграции (legacy)
├── database.sql              # MySQL схема (legacy)
└── install/                  # Веб-установщик (не используется в Docker)
```

## 🎨 Темы оформления

### Активная тема: HexaVeil
- **Лендинг**: 3D-глобус (Three.js), тарифы, FAQ, звёздный фон, glassmorphism
- **Блог**: glass-карточки, pill-фильтр категорий, floating-виджет

### Дизайн-система админки
- 6 акцентных пресетов (Obsidian, Halo, Arctic, Sakura, Twilight, Ember)
- Тёмный/светлый режим
- Glass-эффекты, mesh-фон, командная палитра (Ctrl+K)
- DataGrid-таблицы с массовыми действиями

## 🧩 Функционал

### Публичная часть
- Лендинг VPN-сервиса с 3D-визуализацией серверов
- Блог (посты, категории, теги, комментарии)
- Статические страницы
- SEO: Open Graph, canonical URL

### Админ-панель
- **Посты**: CRUD, CKEditor 5, статусы, категории, теги
- **Страницы**: CRUD, шаблоны (default, fullwidth, landing, blank)
- **Категории, теги, комментарии**: управление + модерация
- **Медиа**: загрузка изображений (JPG, PNG, WebP, SVG)
- **Пользователи**: роли admin/editor/author
- **Финансы**: транзакции, графики, импорт CSV, интеграция Platega и YooKassa
- **Логи**: централизованное логирование событий
- **Настройки темы**: конфигурация активной темы через админку
- **Настройки вида**: тема/режим/плотность/радиус/шрифт (per-user)

## 🔧 Разработка

### Добавление новой страницы
1. Маршрут в `core/routes.php` (ДО `{slug}`)
2. Шаблон в `templates/themes/hexaveil/`
3. Стили в `public/hexaveil/css/style.css`

### Команды для разработки

```bash
# Режим отладки (включён по умолчанию в .env)
APP_DEBUG=true
```

## 🐛 Отладка

```bash
# PHP ошибки
docker compose logs app

# Nginx ошибки
docker compose logs web

# PostgreSQL логи
docker compose logs db

# SQL-запросы (включить логирование в PostgreSQL)
docker compose exec db psql -U cms -c "ALTER SYSTEM SET log_statement = 'all';"
docker compose restart db
```

## 📄 Лицензия

Свободное использование и модификация.

---

**Версия**: 2.0  
**Дата обновления**: 2026-09-26