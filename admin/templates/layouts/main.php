<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?= $title ?? 'Админ-панель' ?> - <?= SITE_NAME ?></title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="<?= SITE_URL ?>/admin/css/admin.css?v=<?= filemtime(ADMIN_PATH . '/css/admin.css') ?>">
        <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📊</text></svg>">
        <!-- TinyMCE -->
    <script src="https://cdn.jsdelivr.net/npm/tinymce@7/tinymce.min.js"></script>
</head>
<body>
    <div class="admin-wrapper">
        <aside class="admin-sidebar">
            <div class="sidebar-header">
                <a href="/admin" class="admin-logo"><?= icon('dashboard') ?> <?= SITE_NAME ?></a>
            </div>
            
            <nav class="sidebar-nav">
                <a href="/admin" class="nav-item <?= TemplateEngine::isActive('admin') ?>">
                    <?= icon('dashboard') ?>
                    <span>Дашборд</span>
                </a>
                <a href="/admin/posts" class="nav-item <?= TemplateEngine::isActive('admin/posts') ?>">
                    <?= icon('posts') ?>
                    <span>Посты</span>
                </a>
                <a href="/admin/categories" class="nav-item <?= TemplateEngine::isActive('admin/categories') ?>">
                    <?= icon('categories') ?>
                    <span>Категории</span>
                </a>
                <a href="/admin/pages" class="nav-item <?= TemplateEngine::isActive('admin/pages') ?>">
                    <?= icon('pages') ?>
                    <span>Страницы</span>
                </a>
                <a href="/admin/menus" class="nav-item <?= TemplateEngine::isActive('admin/menus') ?>">
                    <?= icon('menus') ?>
                    <span>Меню</span>
                </a>
                <a href="/admin/media" class="nav-item <?= TemplateEngine::isActive('admin/media') ?>">
                    <?= icon('media') ?>
                    <span>Медиа</span>
                </a>
                <a href="/admin/users" class="nav-item <?= TemplateEngine::isActive('admin/users') ?>">
                    <?= icon('users') ?>
                    <span>Пользователи</span>
                </a>
                <a href="/admin/settings" class="nav-item <?= TemplateEngine::isActive('admin/settings') ?>">
                    <?= icon('settings') ?>
                    <span>Настройки</span>
                </a>
                <a href="/admin/theme" class="nav-item <?= TemplateEngine::isActive('admin/theme') ?>">
                    <?= icon('theme') ?>
                    <span>Темы</span>
                </a>
                <a href="/admin/widgets" class="nav-item <?= TemplateEngine::isActive('admin/widgets') ?>">
                    <?= icon('widgets') ?>
                    <span>Виджеты</span>
                </a>
            </nav>
            
            <div class="sidebar-footer">
                <a href="/" class="nav-item" target="_blank">
                    <?= icon('external') ?>
                    <span>На сайт</span>
                </a>
                <a href="/admin/logout" class="nav-item logout">
                    <?= icon('logout') ?>
                    <span>Выйти</span>
                </a>
            </div>
        </aside>
        
        <main class="admin-content">
            <header class="admin-header">
                <h1 class="page-title"><?= $title ?? 'Панель управления' ?></h1>
                <div class="user-info">
                    <span class="user-name"><?= $user['login'] ?? 'Администратор' ?></span>
                </div>
            </header>
            
            <div class="content-body">
                <?php if (isset($error)): ?>
                <div class="alert alert-error"><?= TemplateEngine::e($error) ?></div>
                <?php endif; ?>
                
                <?php if (isset($success)): ?>
                <div class="alert alert-success"><?= TemplateEngine::e($success) ?></div>
                <?php endif; ?>
                
                <?php if (isset($message)): ?>
                <div class="alert alert-info"><?= TemplateEngine::e($message) ?></div>
                <?php endif; ?>
                
                <?= $content ?? '' ?>
            </div>
        </main>
    </div>
    
    <script>
        // Инициализация TinyMCE
        tinymce.init({
            selector: '.editor',
            license_key: 'gpl',
            language: 'ru',
            language_url: '/admin/js/tinymce-lang-ru.js',
            height: 500,
            plugins: 'anchor autolink charmap code codesample emoticons image link lists media searchreplace table visualblocks wordcount',
            toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | link image media table | align lineheight | numlist bullist indent outdent | emoticons charmap code | removeformat',
            content_style: 'body { font-family: Outfit, system-ui, sans-serif; font-size: 16px }',
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
