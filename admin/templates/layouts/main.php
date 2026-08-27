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
    <script src="<?= SITE_URL ?>/admin/js/panel.js?v=<?= filemtime(ADMIN_PATH . '/js/panel.js') ?>" defer></script>
    <script src="<?= SITE_URL ?>/admin/js/command-palette.js?v=<?= filemtime(ADMIN_PATH . '/js/command-palette.js') ?>" defer></script>
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
                <div class="sidebar-footer-tools">
                    <button type="button" class="sidebar-tool-btn" id="sidebar-collapse-btn" title="Свернуть меню">
                        <span class="collapse-icon collapse-icon-collapse"><?= icon('chevrons-left') ?></span>
                        <span class="collapse-icon collapse-icon-expand"><?= icon('chevrons-right') ?></span>
                    </button>
                </div>
                <div class="sidebar-footer-links">
                    <a href="/" class="sidebar-nav-item" target="_blank"><?= icon('external') ?><span class="sidebar-text">На сайт</span></a>
                </div>
                <div class="user-info">
                    <span class="user-avatar"><?= strtoupper(substr($user['login'] ?? 'A', 0, 1)) ?></span>
                    <div class="user-meta">
                        <span class="user-name"><?= $user['login'] ?? 'Администратор' ?></span>
                        <span class="user-role"><?= ($user['role'] ?? '') === 'admin' ? 'Администратор' : (($user['role'] ?? '') === 'editor' ? 'Редактор' : ($user['role'] ?? '')) ?></span>
                    </div>
                    <a href="/admin/logout" class="user-logout" title="Выйти"><?= icon('logout') ?></a>
                </div>
            </div>
        </aside>

        <main class="panel-main" id="main-content">
            <header class="panel-header">
                <div class="header-search" id="command-palette-trigger">
                    <?= icon('search') ?><span>Поиск по разделам...</span><kbd>Ctrl K</kbd>
                </div>
                <div class="header-actions">
                    <div class="header-status" title="Панель онлайн">
                        <span class="status-dot"></span><span>Online</span>
                    </div>
                    <div class="header-divider"></div>
                    <!-- Настройки вида (одна кнопка → панель, как в remnawave-admin) -->
                    <div class="dropdown">
                        <button type="button" class="btn-icon" id="theme-toggle" data-dropdown-toggle title="Вид"><?= icon('paintbrush') ?></button>
                        <div class="dropdown-menu ap-panel">
                            <div class="ap-header">
                                <span class="ap-title">Вид</span>
                                <button type="button" class="ap-reset" id="ap-reset" title="Сбросить к настройкам по умолчанию"><?= icon('rotate-ccw') ?></button>
                            </div>
                            <div class="ap-body">
                                <div class="ap-section">
                                    <div class="ap-label">Тема</div>
                                    <div class="ap-theme-grid">
                                        <button type="button" class="ap-swatch" data-set-theme="obsidian" title="Obsidian"><span class="ap-swatch-dot" style="background:linear-gradient(135deg,#6366f1,#818cf8)"></span><span class="ap-swatch-name">Obsidian</span></button>
                                        <button type="button" class="ap-swatch" data-set-theme="halo" title="Halo"><span class="ap-swatch-dot" style="background:linear-gradient(135deg,#22d3ee,#3b82f6)"></span><span class="ap-swatch-name">Halo</span></button>
                                        <button type="button" class="ap-swatch" data-set-theme="arctic" title="Arctic"><span class="ap-swatch-dot" style="background:linear-gradient(135deg,#0ea5e9,#38bdf8)"></span><span class="ap-swatch-name">Arctic</span></button>
                                        <button type="button" class="ap-swatch" data-set-theme="sakura" title="Sakura"><span class="ap-swatch-dot" style="background:linear-gradient(135deg,#ec4899,#f472b6)"></span><span class="ap-swatch-name">Sakura</span></button>
                                        <button type="button" class="ap-swatch" data-set-theme="twilight" title="Twilight"><span class="ap-swatch-dot" style="background:linear-gradient(135deg,#8b5cf6,#a78bfa)"></span><span class="ap-swatch-name">Twilight</span></button>
                                        <button type="button" class="ap-swatch" data-set-theme="ember" title="Ember"><span class="ap-swatch-dot" style="background:linear-gradient(135deg,#f59e0b,#fbbf24)"></span><span class="ap-swatch-name">Ember</span></button>
                                    </div>
                                </div>
                                <hr class="ap-sep">
                                <div class="ap-section">
                                    <div class="ap-label">Режим</div>
                                    <div class="ap-row">
                                        <button type="button" class="ap-option" data-set-mode="dark"><?= icon('moon') ?>Тёмный</button>
                                        <button type="button" class="ap-option" data-set-mode="light"><?= icon('sun') ?>Светлый</button>
                                        <button type="button" class="ap-option" data-set-mode="auto"><?= icon('monitor') ?>Авто</button>
                                    </div>
                                </div>
                                <hr class="ap-sep">
                                <div class="ap-section">
                                    <div class="ap-label">Плотность</div>
                                    <div class="ap-row">
                                        <button type="button" class="ap-option" data-set-density="compact">Compact</button>
                                        <button type="button" class="ap-option" data-set-density="comfortable">Comfort</button>
                                        <button type="button" class="ap-option" data-set-density="spacious">Spacious</button>
                                    </div>
                                </div>
                                <hr class="ap-sep">
                                <div class="ap-section">
                                    <div class="ap-label">Радиус</div>
                                    <div class="ap-row">
                                        <button type="button" class="ap-option" data-set-radius="sharp"><span class="ap-radius-box" style="border-radius:0"></span>Sharp</button>
                                        <button type="button" class="ap-option" data-set-radius="default"><span class="ap-radius-box" style="border-radius:6px"></span>Default</button>
                                        <button type="button" class="ap-option" data-set-radius="rounded"><span class="ap-radius-box" style="border-radius:12px"></span>Rounded</button>
                                    </div>
                                </div>
                                <hr class="ap-sep">
                                <div class="ap-section">
                                    <div class="ap-label">Размер шрифта</div>
                                    <div class="ap-row">
                                        <button type="button" class="ap-option" data-set-font-size="small">S</button>
                                        <button type="button" class="ap-option" data-set-font-size="default">M</button>
                                        <button type="button" class="ap-option" data-set-font-size="large">L</button>
                                    </div>
                                </div>
                                <hr class="ap-sep">
                                <div class="ap-section ap-switch-row">
                                    <label class="ap-switch-label" for="panel-animations">Анимации</label>
                                    <label class="ap-switch"><input type="checkbox" id="panel-animations" data-set-animations><span class="ap-switch-slider"></span></label>
                                </div>
                            </div>
                        </div>
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
