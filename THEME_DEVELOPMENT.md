# Руководство по созданию тем для CMS

Это подробное руководство по созданию и кастомизации тем для вашей CMS.

---

## 📁 Структура темы

Каждая тема располагается в папке `templates/themes/{название_темы}/` и содержит:

```
templates/
└── themes/
    └── my-theme/              # Ваша тема
        ├── layouts/
        │   └── main.php       # Основной layout (обёртка)
        ├── errors/
        │   └── 404.php        # Страница 404
        ├── index.php          # Главная страница
        ├── post.php           # Страница поста
        ├── page.php           # Страница статической страницы
        └── category.php       # Страница категории
```

---

## 🚀 Быстрый старт

### Шаг 1: Создайте папку темы

```bash
templates/themes/my-theme/
```

### Шаг 2: Скопируйте базовые файлы

Скопируйте файлы из темы `default` как основу:

```bash
templates/themes/default/* → templates/themes/my-theme/
```

### Шаг 3: Выберите тему в админке

1. Откройте админ-панель
2. Перейдите в **Настройки** → **Внешний вид**
3. Выберите вашу тему из списка
4. Сохраните

---

## 📄 Layout (main.php)

Layout — это основной шаблон-обёртка, который используется для всех страниц.

### Обязательные элементы

```php
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- SEO Meta Tags -->
    <title><?= $seo['title'] ?? ($title ?? SITE_NAME) ?></title>
    <?php if (!empty($seo['description'])): ?>
    <meta name="description" content="<?= TemplateEngine::e($seo['description']) ?>">
    <?php endif; ?>
    
    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="<?= $seo['title'] ?? ($title ?? SITE_NAME) ?>">
    <meta property="og:url" content="<?= SITE_URL . ($_SERVER['REQUEST_URI'] ?? '') ?>">
    
    <!-- Canonical URL -->
    <link rel="canonical" href="<?= SITE_URL . ($_SERVER['REQUEST_URI'] ?? '') ?>">
    
    <!-- Styles -->
    <link rel="stylesheet" href="<?= TemplateEngine::asset('css/style.css') ?>">
</head>
<body class="<?= $bodyClass ?? '' ?>">
    <!-- Header -->
    <header class="site-header">
        <div class="container">
            <a href="<?= TemplateEngine::url() ?>" class="logo">
                <?= $siteLogo ?? SITE_NAME ?>
            </a>
            
            <nav class="main-navigation">
                <ul class="nav-menu">
                    <?php if (!empty($menuItems)): ?>
                        <?php foreach ($menuItems as $item): ?>
                        <li>
                            <a href="<?= TemplateEngine::e($item['url']) ?>"
                               class="<?= !empty($item['active']) ? 'active' : '' ?>">
                                <?= TemplateEngine::e($item['label']) ?>
                            </a>
                        </li>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </ul>
            </nav>
        </div>
    </header>

    <!-- Main Content -->
    <main class="site-main">
        <div class="container">
            <?= $content ?? '' ?>
        </div>
    </main>

    <!-- Footer -->
    <footer class="site-footer">
        <div class="container">
            <p>&copy; <?= date('Y') ?> <?= SITE_NAME ?>. Все права защищены.</p>
            
            <?php if (!empty($footerMenu)): ?>
            <nav class="footer-navigation">
                <ul class="footer-menu">
                    <?php foreach ($footerMenu as $item): ?>
                    <li><a href="<?= TemplateEngine::e($item['url']) ?>"><?= TemplateEngine::e($item['label']) ?></a></li>
                    <?php endforeach; ?>
                </ul>
            </nav>
            <?php endif; ?>
        </div>
    </footer>
</body>
</html>
```

### Переменные в layout

| Переменная | Описание | Тип |
|------------|----------|-----|
| `$seo['title']` | Заголовок страницы | string |
| `$seo['description']` | Meta description | string |
| `$seo['keywords']` | Meta keywords | string |
| `$content` | Основное содержимое страницы | string |
| `$menuItems` | Пункты главного меню | array |
| `$footerMenu` | Пункты меню футера | array |
| `$bodyClass` | CSS класс для body | string |
| `$siteLogo` | Логотип сайта | string |
| `$extraCss` | Дополнительные CSS файлы | array |
| `$extraJs` | Дополнительные JS файлы | array |

---

## 📋 Шаблоны страниц

### index.php — Главная страница

```php
<?php
/**
 * Шаблон главной страницы
 */
?>

<h1><?= SITE_NAME ?></h1>

<?php if (!empty($posts)): ?>
    <?php foreach ($posts as $post): ?>
    <article class="post-card">
        <h2>
            <a href="/post/<?= $post['slug'] ?>">
                <?= TemplateEngine::e($post['title']) ?>
            </a>
        </h2>
        
        <div class="post-meta">
            <span>Автор: <?= TemplateEngine::e($post['author']) ?></span>
            <span>Категория: <?= TemplateEngine::e($post['category_name']) ?></span>
            <span>Дата: <?= format_date($post['created_at']) ?></span>
        </div>
        
        <?php if (!empty($post['image'])): ?>
        <img src="<?= TemplateEngine::image($post['image']) ?>" alt="<?= TemplateEngine::e($post['title']) ?>">
        <?php endif; ?>
        
        <div class="post-excerpt">
            <?= TemplateEngine::e($post['excerpt'] ?? truncate(strip_tags($post['content']), 200)) ?>
        </div>
        
        <a href="/post/<?= $post['slug'] ?>" class="read-more">Читать далее →</a>
    </article>
    <?php endforeach; ?>
<?php else: ?>
    <p>Постов пока нет.</p>
<?php endif; ?>
```

### post.php — Страница поста

```php
<?php
/**
 * Шаблон отдельного поста
 */
?>

<article class="post-full">
    <header class="post-header">
        <h1><?= TemplateEngine::e($post['title']) ?></h1>
        
        <div class="post-meta">
            <span>Автор: <?= TemplateEngine::e($post['author']) ?></span>
            <span>Категория: <?= TemplateEngine::e($post['category_name']) ?></span>
            <span>Дата: <?= format_date($post['created_at']) ?></span>
            <span>Просмотров: <?= $post['views'] ?></span>
        </div>
    </header>
    
    <?php if (!empty($post['image'])): ?>
    <div class="post-featured-image">
        <img src="<?= TemplateEngine::image($post['image']) ?>" alt="<?= TemplateEngine::e($post['title']) ?>">
    </div>
    <?php endif; ?>
    
    <div class="post-content">
        <?= $post['content'] ?>
    </div>
    
    <?php if (!empty($tags)): ?>
    <div class="post-tags">
        <strong>Теги:</strong>
        <?php foreach ($tags as $tag): ?>
        <span class="tag"><?= TemplateEngine::e($tag['name']) ?></span>
        <?php endforeach; ?>
    </div>
    <?php endif; ?>
</article>

<!-- Комментарии -->
<?php if (!empty($comments)): ?>
<section class="comments">
    <h2>Комментарии (<?= count($comments) ?>)</h2>
    
    <?php foreach ($comments as $comment): ?>
    <div class="comment">
        <div class="comment-header">
            <span class="comment-author"><?= TemplateEngine::e($comment['author_name']) ?></span>
            <span class="comment-date"><?= format_date($comment['created_at']) ?></span>
        </div>
        <div class="comment-content">
            <?= TemplateEngine::e($comment['content']) ?>
        </div>
    </div>
    <?php endforeach; ?>
</section>
<?php endif; ?>
```

### page.php — Статическая страница

```php
<?php
/**
 * Шаблон статической страницы
 */
?>

<article class="static-page">
    <header class="page-header">
        <h1><?= TemplateEngine::e($page['title']) ?></h1>
    </header>
    
    <div class="page-content">
        <?= $page['content'] ?>
    </div>
</article>
```

### category.php — Категория

```php
<?php
/**
 * Шаблон категории
 */
?>

<header class="category-header">
    <h1>Категория: <?= TemplateEngine::e($category['name']) ?></h1>
    <?php if (!empty($category['description'])): ?>
    <p class="category-description"><?= TemplateEngine::e($category['description']) ?></p>
    <?php endif; ?>
</header>

<?php if (!empty($posts)): ?>
    <?php foreach ($posts as $post): ?>
    <article class="post-card">
        <h2>
            <a href="/post/<?= $post['slug'] ?>">
                <?= TemplateEngine::e($post['title']) ?>
            </a>
        </h2>
        <div class="post-excerpt">
            <?= TemplateEngine::e($post['excerpt'] ?? truncate(strip_tags($post['content']), 200)) ?>
        </div>
    </article>
    <?php endforeach; ?>
<?php else: ?>
    <p>В этой категории пока нет постов.</p>
<?php endif; ?>
```

### errors/404.php — Страница 404

```php
<?php
/**
 * Шаблон страницы 404
 */
?>

<div class="error-page">
    <h1>404</h1>
    <h2>Страница не найдена</h2>
    <p>К сожалению, запрашиваемая страница не существует.</p>
    <a href="<?= TemplateEngine::url() ?>" class="btn btn-primary">Вернуться на главную</a>
</div>

<style>
.error-page {
    text-align: center;
    padding: 100px 20px;
}

.error-page h1 {
    font-size: 8rem;
    margin: 0;
    color: #667eea;
}

.error-page h2 {
    font-size: 2rem;
    margin: 20px 0;
}

.error-page p {
    font-size: 1.2rem;
    color: #666;
    margin-bottom: 30px;
}
</style>
```

---

## 🔧 Вспомогательные функции

### TemplateEngine

| Функция | Описание | Пример |
|---------|----------|--------|
| `TemplateEngine::e($str)` | Экранирование HTML | `<?= TemplateEngine::e($title) ?>` |
| `TemplateEngine::url($path)` | Генерация URL | `<?= TemplateEngine::url('page/about') ?>` |
| `TemplateEngine::asset($path)` | Путь к asset | `<?= TemplateEngine::asset('css/style.css') ?>` |
| `TemplateEngine::image($path)` | Путь к изображению | `<?= TemplateEngine::image($post['image']) ?>` |
| `TemplateEngine::isActive($path)` | Активный пункт меню | `class="<?= TemplateEngine::isActive('about') ?>"` |

### Другие функции

| Функция | Описание | Пример |
|---------|----------|--------|
| `format_date($date, $format)` | Форматирование даты | `format_date($post['created_at'], 'd.m.Y')` |
| `truncate($text, $length)` | Обрезка текста | `truncate($content, 200, '...')` |
| `SITE_NAME` | Название сайта | `<?= SITE_NAME ?>` |
| `SITE_URL` | URL сайта | `<?= SITE_URL ?>` |
| `ADMIN_EMAIL` | Email администратора | `<?= ADMIN_EMAIL ?>` |

---

## 🎨 CSS и JavaScript

### Подключение CSS

В layout:

```php
<link rel="stylesheet" href="<?= TemplateEngine::asset('css/style.css') ?>">

<?php if (!empty($extraCss)): ?>
    <?php foreach ($extraCss as $css): ?>
    <link rel="stylesheet" href="<?= $css ?>">
    <?php endforeach; ?>
<?php endif; ?>
```

### Подключение JavaScript

В layout (перед закрывающим `</body>`):

```php
<?php if (!empty($extraJs)): ?>
    <?php foreach ($extraJs as $js): ?>
    <script src="<?= $js ?>"></script>
    <?php endforeach; ?>
<?php endif; ?>
```

### Встроенные стили

Можно добавлять стили прямо в шаблон:

```php
<style>
.my-custom-class {
    color: #667eea;
    padding: 20px;
}
</style>
```

---

## 📦 Передача дополнительных данных

В контроллере или маршруте:

```php
$template = createTemplate();
$template->set('title', 'Моя страница');
$template->set('seo', [
    'title' => 'SEO заголовок',
    'description' => 'SEO описание',
    'keywords' => 'ключевые, слова',
]);
$template->set('bodyClass', 'custom-page');
$template->set('extraCss', ['/css/custom.css']);
$template->set('extraJs', ['/js/custom.js']);
$template->setLayout('layouts/main');
$template->display('page');
```

---

## 🎯 Примеры тем

### Минималистичная тема

```php
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $seo['title'] ?? SITE_NAME ?></title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        header, footer {
            padding: 20px 0;
            border-bottom: 1px solid #eee;
        }
        nav ul {
            list-style: none;
            padding: 0;
            display: flex;
            gap: 20px;
        }
        a { color: #333; }
        a:hover { text-decoration: none; }
    </style>
</head>
<body>
    <header>
        <a href="<?= TemplateEngine::url() ?>"><?= SITE_NAME ?></a>
        <nav>
            <ul>
                <?php foreach ($menuItems as $item): ?>
                <li><a href="<?= $item['url'] ?>"><?= $item['label'] ?></a></li>
                <?php endforeach; ?>
            </ul>
        </nav>
    </header>
    
    <main>
        <?= $content ?>
    </main>
    
    <footer>
        <p>&copy; <?= date('Y') ?> <?= SITE_NAME ?></p>
    </footer>
</body>
</html>
```

### Тема с тёмной темой

```php
<style>
:root {
    --bg-color: #1a1a2e;
    --text-color: #eee;
    --accent-color: #e94560;
}

@media (prefers-color-scheme: light) {
    :root {
        --bg-color: #fff;
        --text-color: #333;
        --accent-color: #667eea;
    }
}

body {
    background: var(--bg-color);
    color: var(--text-color);
}

a { color: var(--accent-color); }
</style>
```

---

## ✅ Чек-лист перед публикацией темы

- [ ] Все шаблоны созданы (index, post, page, category, 404)
- [ ] Layout содержит все необходимые meta-теги
- [ ] Меню выводится через `$menuItems` и `$footerMenu`
- [ ] Все переменные экранированы через `TemplateEngine::e()`
- [ ] CSS и JS подключены корректно
- [ ] Тема выбрана в настройках админ-панели
- [ ] Проверено на мобильных устройствах
- [ ] Проверена работа всех страниц

---

## 🐛 Отладка

### Включить режим отладки

В `config/config.php`:

```php
define('DEBUG', true);
```

### Вывод переменных

```php
<?php dd($posts); ?>
```

### Проверка существования переменной

```php
<?php if (!empty($variable)): ?>
    <!-- код -->
<?php endif; ?>
```

---

## 📚 Дополнительные ресурсы

- [PHP официальная документация](https://www.php.net/manual/ru/)
- [HTML5 шаблон](https://html5boilerplate.com/)
- [CSS Flexbox руководство](https://css-tricks.com/snippets/css/a-guide-to-flexbox/)
- [CSS Grid руководство](https://css-tricks.com/snippets/css/complete-guide-grid/)

---

**Версия руководства**: 1.0  
**Дата обновления**: 2026-03-16
