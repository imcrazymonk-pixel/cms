<?php
// Настройки вида панели из БД (тема/режим/плотность/радиус/шрифт), дефолты если пусто
$panelPrefs = [];
try {
    if (Auth::id()) {
        $panelPrefs = (new UserPreference())->getAll(Auth::id());
    }
} catch (\Throwable $e) {
    $panelPrefs = [];
}
$panelTheme = $panelPrefs['theme'] ?? 'obsidian';
$panelMode = $panelPrefs['mode'] ?? 'dark';
$panelDensity = $panelPrefs['density'] ?? 'comfortable';
$panelRadius = $panelPrefs['radius'] ?? 'default';
$panelFontSize = $panelPrefs['fontSize'] ?? 'default';
$panelAnimationsOff = (isset($panelPrefs['animations']) && $panelPrefs['animations'] === 'false');
?>
<!DOCTYPE html>
<html lang="ru" data-theme="<?= $panelTheme ?>" data-mode="<?= $panelMode ?>" data-density="<?= $panelDensity ?>" data-radius="<?= $panelRadius ?>" data-font-size="<?= $panelFontSize ?>"<?= $panelAnimationsOff ? ' data-animations="false"' : '' ?>>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $title ?? 'Админ-панель' ?> - <?= SITE_NAME ?></title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Unbounded:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/tokens.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/tokens.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/themes.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/themes.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/base.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/base.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/effects.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/effects.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/components.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/components.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/table.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/table.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/layout.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/layout.css') ?>">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%236366f1'/%3E%3Ctext x='50' y='72' font-size='56' font-family='Arial' font-weight='bold' text-anchor='middle' fill='white'%3EC%3C/text%3E%3C/svg%3E">
    <!-- TinyMCE -->
    <script src="https://cdn.jsdelivr.net/npm/tinymce@7/tinymce.min.js"></script>
    <script src="<?= SITE_URL ?>/admin/js/panel.js" defer></script>
    <script src="<?= SITE_URL ?>/admin/js/command-palette.js" defer></script>
</head>
<body>
    <a href="#main-content" class="skip-link">Перейти к содержимому</a>

    <!-- Mesh-фон (анимированный градиент, фиксированный за контентом) -->
    <div class="mesh-bg" aria-hidden="true">
        <div class="mesh-layer mesh-layer--1"></div>
        <div class="mesh-layer mesh-layer--2"></div>
        <div class="mesh-layer mesh-layer--3"></div>
        <div class="mesh-layer mesh-layer--4"></div>
        <div class="mesh-layer mesh-layer--5"></div>
    </div>

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

        <main class="panel-main" id="main-content">
            <header class="panel-header">
                <button type="button" class="btn-icon" id="sidebar-collapse-btn" title="Свернуть меню"><?= icon('menu') ?></button>
                <div class="header-search" id="command-palette-trigger">
                    <span>Поиск по разделам...</span><kbd>Ctrl K</kbd>
                </div>
                <div class="header-actions">
                    <!-- Переключатель тем и режима -->
                    <button type="button" class="btn-icon" id="theme-toggle" title="Сменить тему"><?= icon('palette') ?></button>
                    <!-- Настройки вида -->
                    <div class="dropdown">
                        <button type="button" class="btn-icon" data-dropdown-toggle title="Настройки вида"><?= icon('settings') ?></button>
                        <div class="dropdown-menu">
                            <div class="dropdown-group-title">Тема</div>
                            <button type="button" class="dropdown-item" data-set-theme="obsidian"><span>Obsidian</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-theme="halo"><span>Halo</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-theme="arctic"><span>Arctic</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-theme="sakura"><span>Sakura</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-theme="twilight"><span>Twilight</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-theme="ember"><span>Ember</span><span class="check">✓</span></button>

                            <div class="dropdown-group-title">Режим</div>
                            <button type="button" class="dropdown-item" data-set-mode="dark"><span>Тёмный</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-mode="light"><span>Светлый</span><span class="check">✓</span></button>

                            <div class="dropdown-group-title">Плотность</div>
                            <button type="button" class="dropdown-item" data-set-density="compact"><span>Compact</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-density="comfortable"><span>Comfortable</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-density="spacious"><span>Spacious</span><span class="check">✓</span></button>

                            <div class="dropdown-group-title">Радиус</div>
                            <button type="button" class="dropdown-item" data-set-radius="sharp"><span>Sharp</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-radius="default"><span>Default</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-radius="rounded"><span>Rounded</span><span class="check">✓</span></button>

                            <div class="dropdown-group-title">Размер шрифта</div>
                            <button type="button" class="dropdown-item" data-set-font-size="small"><span>S</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-font-size="default"><span>M</span><span class="check">✓</span></button>
                            <button type="button" class="dropdown-item" data-set-font-size="large"><span>L</span><span class="check">✓</span></button>

                            <div class="dropdown-group-title">Анимации</div>
                            <label class="dropdown-item" for="panel-animations">
                                <span>Включены</span>
                                <input type="checkbox" id="panel-animations" data-set-animations>
                            </label>
                        </div>
                    </div>
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
                <?php if (isset($message)): ?><div class="alert alert-info"><?= TemplateEngine::e($message) ?></div><?php endif; ?>
                <?= $content ?? '' ?>
            </div>
        </main>
    </div>

    <!-- Командная палитра -->
    <div id="command-palette" class="command-palette" hidden></div>

    <script>
        // Инициализация TinyMCE (тёмная тема редактора)
        tinymce.init({
            selector: '.editor',
            license_key: 'gpl',
            language: 'ru',
            language_url: '/admin/js/tinymce-lang-ru.js',
            height: 500,
            skin: 'oxide-dark',
            content_css: 'dark',
            plugins: 'anchor autolink charmap code codesample emoticons image link lists media searchreplace table visualblocks wordcount',
            toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | link image media table | align lineheight | numlist bullist indent outdent | emoticons charmap code | removeformat',
            content_style: 'body { font-family: Montserrat, system-ui, sans-serif; font-size: 16px; background-color: #181e28; color: #d1d5db; }',
            images_upload_url: '/admin/media/upload',
            automatic_uploads: true,
            file_picker_types: 'image',
            file_picker_callback: function(cb, value, meta) {
                const input = document.createElement('input');
                input.setAttribute('type', 'file');
                input.setAttribute('accept', 'image/*');
                input.addEventListener('change', function(e) {
                    const file = e.target.files[0];
                    const reader = new FileReader();
                    reader.addEventListener('load', function() {
                        const id = 'blobid' + (new Date()).getTime();
                        const blobCache = tinymce.activeEditor.editorUpload.blobCache;
                        const base64 = reader.result.split(',')[1];
                        const blobInfo = blobCache.create(id, file, base64);
                        blobCache.add(blobInfo);
                        cb(blobInfo.blobUri(), { title: file.name });
                    });
                    reader.readAsDataURL(file);
                });
                input.click();
            }
        });
    </script>
</body>
</html>
