<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $title ?? 'Админ-панель' ?> - <?= SITE_NAME ?></title>
    <link rel="stylesheet" href="<?= SITE_URL ?>/admin/css/admin.css?v=<?= filemtime(ADMIN_PATH . '/css/admin.css') ?>">
    <!-- TinyMCE -->
    <script src="https://cdn.jsdelivr.net/npm/tinymce@7/tinymce.min.js"></script>
</head>
<body>
    <div class="admin-wrapper">
        <aside class="admin-sidebar">
            <div class="sidebar-header">
                <a href="/admin" class="admin-logo">📊 <?= SITE_NAME ?></a>
            </div>
            
            <nav class="sidebar-nav">
                <a href="/admin" class="nav-item <?= TemplateEngine::isActive('admin') ?>">
                    <span class="nav-icon">🏠</span>
                    <span>Дашборд</span>
                </a>
                <a href="/admin/posts" class="nav-item <?= TemplateEngine::isActive('admin/posts') ?>">
                    <span class="nav-icon">📝</span>
                    <span>Посты</span>
                </a>
                <a href="/admin/categories" class="nav-item <?= TemplateEngine::isActive('admin/categories') ?>">
                    <span class="nav-icon">📁</span>
                    <span>Категории</span>
                </a>
                <a href="/admin/pages" class="nav-item <?= TemplateEngine::isActive('admin/pages') ?>">
                    <span class="nav-icon">📄</span>
                    <span>Страницы</span>
                </a>
                <a href="/admin/menus" class="nav-item <?= TemplateEngine::isActive('admin/menus') ?>">
                    <span class="nav-icon">📋</span>
                    <span>Меню</span>
                </a>
                <a href="/admin/media" class="nav-item <?= TemplateEngine::isActive('admin/media') ?>">
                    <span class="nav-icon">🖼️</span>
                    <span>Медиа</span>
                </a>
                <a href="/admin/users" class="nav-item <?= TemplateEngine::isActive('admin/users') ?>">
                    <span class="nav-icon">👥</span>
                    <span>Пользователи</span>
                </a>
                <a href="/admin/settings" class="nav-item <?= TemplateEngine::isActive('admin/settings') ?>">
                    <span class="nav-icon">⚙️</span>
                    <span>Настройки</span>
                </a>
            </nav>
            
            <div class="sidebar-footer">
                <a href="/" class="nav-item" target="_blank">
                    <span class="nav-icon">🌐</span>
                    <span>На сайт</span>
                </a>
                <a href="/admin/logout" class="nav-item logout">
                    <span class="nav-icon">🚪</span>
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
            plugins: 'anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount',
            toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | link image media table | align lineheight | numlist bullist indent outdent | emoticons charmap | removeformat',
            content_style: 'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 16px }',
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
