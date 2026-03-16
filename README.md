# Моя CMS

Лёгкая и простая система управления контентом (CMS) на PHP с использованием MySQL.

## 📋 Требования

- PHP 7.4 или выше
- MySQL 5.7 или выше / MariaDB
- mod_rewrite для Apache
- Расширения PHP: PDO, pdo_mysql, mbstring, json

## 🚀 Установка

1. Скопируйте файлы CMS в корневую директорию вашего сайта
2. Откройте сайт в браузере
3. Автоматически откроется мастер установки
4. Следуйте инструкциям:
   - Проверка требований
   - Настройка базы данных (создаётся автоматически)
   - Создание учётной записи администратора
5. После установки удалите файл `install.lock` для повторной установки (если нужно)

## 📁 Структура проекта

```
cms/
├── admin/                      # Админ-панель
│   ├── controllers/            # Контроллеры админки
│   │   ├── CategoriesController.php
│   │   ├── MediaController.php
│   │   ├── MenusController.php
│   │   ├── PagesController.php
│   │   ├── PostsController.php
│   │   ├── SettingsController.php
│   │   └── UsersController.php
│   ├── css/
│   │   └── admin.css           # Стили админки
│   ├── js/
│   │   └── tinymce-lang-ru.js  # Локализация TinyMCE
│   ├── templates/              # Шаблоны админки
│   ├── .htaccess
│   └── index.php               # Точка входа админки
├── config/
│   └── config.php              # Конфигурация (генерируется)
├── core/                       # Ядро CMS
│   ├── models/                 # Модели данных
│   │   ├── Category.php
│   │   ├── Comment.php
│   │   ├── Menu.php
│   │   ├── Page.php
│   │   ├── Post.php
│   │   ├── Setting.php
│   │   └── User.php
│   ├── Auth.php                # Аутентификация
│   ├── Autoloader.php          # Автозагрузчик классов
│   ├── Database.php            # Работа с БД (PDO wrapper)
│   ├── helpers.php             # Вспомогательные функции
│   ├── Request.php             # HTTP запросы
│   ├── Router.php              # Маршрутизация
│   ├── routes.php              # Определение маршрутов
│   ├── Session.php             # Работа с сессиями
│   └── TemplateEngine.php      # Шаблонизатор
├── install/
│   └── index.php               # Мастер установки
├── public/
│   └── css/
│       └── style.css           # Стили сайта
├── templates/                  # Шаблоны сайта
│   ├── page/                   # Шаблоны страниц (default, fullwidth, landing, blank)
│   └── themes/                 # Темы оформления
│       ├── default/            # Классическая тема
│       │   ├── layouts/
│       │   ├── errors/
│       │   ├── index.php
│       │   ├── post.php
│       │   ├── page.php
│       │   └── category.php
│       ├── modern/             # Современная тема
│       └── minimal/            # Минималистичная тема
├── .htaccess                   # Главный .htaccess
├── database.sql                # Схема базы данных
├── index.php                   # Точка входа
└── install.lock                # Блокировка установки
```

## 🔧 Функционал

### Публичная часть

- **Главная страница** — список опубликованных постов
- **Просмотр постов** — полная страница поста с комментариями
- **Категории** — фильтрация постов по категориям
- **Страницы** — статические страницы с поддержкой главной страницы
- **Меню** — динамическое меню из БД (главное + футер)
- **SEO** — meta-теги, canonical URL, Open Graph

### Админ-панель

#### 📝 Посты
- Создание, редактирование, удаление постов
- Статусы: черновик, опубликован, архив
- Привязка к категориям
- Загрузка изображений
- Счётчик просмотров
- Автогенерация URL (slug) с транслитерацией

#### 📂 Категории
- Управление категориями
- Подсчёт количества постов
- Автогенерация slug

#### 📄 Страницы
- Создание статических страниц
- Назначение главной страницы
- Meta-описания
- Автогенерация slug
- **Переключение шаблонов** (default, fullwidth, landing, blank)

#### 👥 Пользователи
- Управление пользователями
- Роли: admin, editor, author
- Защита от удаления текущего пользователя

#### 🖼️ Медиа
- Загрузка изображений
- Поддержка форматов: JPG, PNG, GIF, WebP, SVG
- Интеграция с TinyMCE

#### ⚙️ Настройки
- Название сайта
- URL сайта
- Email администратора
- Постов на страницу
- Meta-теги по умолчанию
- **Переключение тем оформления** (default, modern, minimal)

#### 🍔 Меню
- Управление пунктами меню
- Расположение: главное меню / футер
- Автогенерация URL с транслитерацией

## 🗄️ База данных

### Таблицы

| Таблица | Описание |
|---------|----------|
| `users` | Пользователи (логин, email, пароль, роль) |
| `posts` | Посты (заголовок, контент, статус, категория) |
| `categories` | Категории постов |
| `pages` | Статические страницы |
| `comments` | Комментарии к постам |
| `tags` | Теги |
| `post_tags` | Связь постов и тегов |
| `menus` | Пункты меню |
| `settings` | Настройки сайта |
| `media` | Медиафайлы |

## 🔐 Безопасность

- Хеширование паролей (bcrypt)
- CSRF-токены для всех форм
- Prepared statements для защиты от SQL-инъекций
- Экранирование вывода (XSS защита)
- Проверка прав доступа (роли)
- Защита от удаления критических данных

## 🎨 Шаблонизатор

### Использование в шаблонах

```php
// Переменные
<?= $variable ?>

// Экранирование
<?= TemplateEngine::e($variable) ?>

// URL
<?= TemplateEngine::url('page/slug') ?>

// Assets
<?= TemplateEngine::asset('css/style.css') ?>

// Изображения
<?= TemplateEngine::image($post['image']) ?>

// Активный пункт меню
<?= TemplateEngine::isActive('about') ?>
```

### Layouts

```php
// В контроллере
$template->setLayout('layouts/main');
$template->display('template');
```

## 🛠️ Вспомогательные функции

| Функция | Описание |
|---------|----------|
| `slugify($string)` | Генерация URL-friendly строки с транслитерацией |
| `truncate($text, $length)` | Обрезка текста |
| `e($string)` | Экранирование HTML |
| `redirect($url)` | Редирект |
| `csrf_field()` | CSRF поле для формы |
| `verify_csrf()` | Проверка CSRF токена |
| `config($key)` | Получение настройки |
| `dd($vars)` | Отладка (dump + die) |

## 📝 Конфигурация

После установки создаётся файл `config/config.php`:

```php
// База данных
define('DB_HOST', 'localhost');
define('DB_NAME', 'cms');
define('DB_USER', 'root');
define('DB_PASS', '');
define('DB_CHARSET', 'utf8mb4');

// Настройки сайта
define('SITE_NAME', 'Моя CMS');
define('SITE_URL', 'http://localhost');
define('ADMIN_EMAIL', 'admin@localhost');

// Пути
define('ROOT_PATH', '/path/to/root');
define('PUBLIC_PATH', ROOT_PATH . '/public');
define('ADMIN_PATH', ROOT_PATH . '/admin');
define('CORE_PATH', ROOT_PATH . '/core');
define('TEMPLATES_PATH', ROOT_PATH . '/templates');

// Настройки
define('DEBUG', true);
define('POSTS_PER_PAGE', 10);
define('SESSION_LIFETIME', 3600);
```

## 🔌 Расширение

### Добавление модели

```php
// core/models/MyModel.php
class MyModel
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    public function getAll(): array
    {
        return $this->db->fetchAll("SELECT * FROM my_table");
    }
}
```

### Добавление контроллера

```php
// admin/controllers/MyController.php
class AdminMyController
{
    public function index()
    {
        Auth::requireAdmin();
        
        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Мой раздел');
        $template->set('user', Auth::user());
        $template->setLayout('layouts/main');
        $template->display('my/index');
    }
}
```

### Добавление маршрута

```php
// core/routes.php
$router->get('my-page', function() {
    $template = new TemplateEngine();
    $template->set('title', 'Моя страница');
    $template->setLayout('layouts/main');
    $template->display('my-page');
});
```

## 🐛 Отладка

Включите режим отладки в `config/config.php`:

```php
define('DEBUG', true);
```

Логирование в `logs/app.log`:

```php
log_message('Сообщение', 'error');
```

## 🎨 Шаблоны и темы

### Темы оформления

CMS поддерживает переключение тем для всего сайта. Тема выбирается в настройках админ-панели.

| Тема | Описание |
|------|----------|
| 📄 Classic (default) | Классический дизайн с header и footer |
| 🚀 Modern | Современный дизайн с градиентами, sticky header и hero-секцией |
| 📝 Minimal | Минималистичный дизайн без лишних элементов |

### Переключение темы

1. Откройте админ-панель → Настройки
2. В разделе "Внешний вид" выберите тему
3. Сохраните настройки
4. Сайт обновится с новой темой

### Шаблоны страниц

Для отдельных страниц можно выбрать индивидуальный шаблон:

| Шаблон | Файл | Описание |
|--------|------|----------|
| 📄 Default | `page/default.php` | Стандартный шаблон с боковыми отступами |
| 📐 Fullwidth | `page/fullwidth.php` | На всю ширину с яркой hero-секцией |
| 🎯 Landing | `page/landing.php` | Лендинг с секциями и footer |
| 📝 Blank | `page/blank.php` | Чистый шаблон без layout (для спец. страниц) |

### Создание своего шаблона

1. Создайте файл `templates/page/your-template.php`
2. Используйте переменную `$page` для доступа к данным:
   - `$page['title']` — заголовок
   - `$page['content']` — содержимое
   - `$page['meta_description']` — SEO описание
3. Выберите шаблон в админ-панели при редактировании страницы

### Пример простого шаблона

```php
<?php
/**
 * Мой шаблон страницы
 */
?>
<article class="my-template">
    <h1><?= TemplateEngine::e($page['title']) ?></h1>
    <div class="content">
        <?= $page['content'] ?>
    </div>
</article>

<style>
.my-template {
    padding: 40px;
    background: #f5f5f5;
}
</style>
```

## 📄 Лицензия

Свободное использование и модификация.

## 👥 Авторы

Разработано для обучения и личного использования.

## 📞 Поддержка

При возникновении проблем:
1. Проверьте требования
2. Включите режим отладки
3. Проверьте логи ошибок PHP
4. Убедитесь, что БД доступна

---

**Версия**: 1.0  
**Дата обновления**: 2026-03-16
