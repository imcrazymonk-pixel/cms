<?php
/**
 * Точка входа приложения (корень сайта)
 * Все маршруты находятся в core/routes.php
 */

// Определяем корневую директорию
define('ROOT_PATH', __DIR__);

// Константы по умолчанию (переопределяются в config.php если существует)
if (!defined('CORE_PATH')) define('CORE_PATH', ROOT_PATH . '/core');
if (!defined('ADMIN_PATH')) define('ADMIN_PATH', ROOT_PATH . '/admin');
if (!defined('PUBLIC_PATH')) define('PUBLIC_PATH', ROOT_PATH . '/public');
if (!defined('TEMPLATES_PATH')) define('TEMPLATES_PATH', ROOT_PATH . '/templates');

// Подключаем конфигурацию (если существует)
if (file_exists(ROOT_PATH . '/config/config.php')) {
    require_once ROOT_PATH . '/config/config.php';
}

// Проверка установки CMS
if (!file_exists(ROOT_PATH . '/install.lock')) {
    if (!file_exists(ROOT_PATH . '/config/config.php')) {
        header('Location: /install/');
        exit;
    }
    
    // Показываем страницу пока идёт установка
    echo '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Установка CMS</title>';
    echo '<meta http-equiv="refresh" content="1;url=/install/">';
    echo '</head><body><p>Идёт установка CMS... <a href="/install/">Перейти</a></p></body></html>';
    exit;
}

// ============================================
// Инициализация ядра
// ============================================

require_once CORE_PATH . '/Autoloader.php';
Autoloader::register();

require_once CORE_PATH . '/helpers.php';
require_once CORE_PATH . '/helpers_icons.php';

// Инициализация сессии
Session::init();

// ============================================
// Загрузка плагинов и функций активной темы
// ============================================

$pluginsDir = ROOT_PATH . '/plugins';
if (is_dir($pluginsDir)) {
    foreach (glob($pluginsDir . '/*.php') ?: [] as $pluginFile) {
        require_once $pluginFile;
    }
}

try {
    $themeFunctionsFile = TEMPLATES_PATH . '/themes/' . active_theme_name() . '/functions.php';
    if (file_exists($themeFunctionsFile)) {
        require_once $themeFunctionsFile;
    }
} catch (\Throwable $e) {
    // Тема может отсутствовать — не критично
}

// Событие после инициализации темы/плагинов
do_action('after_setup_theme');

// Инициализация роутера
$router = new Router();

// ============================================
// Инициализация контроллеров админки
// ============================================

if (file_exists(ROOT_PATH . '/install.lock') && file_exists(ROOT_PATH . '/config/config.php')) {
    require_once ADMIN_PATH . '/controllers/PostsController.php';
    require_once ADMIN_PATH . '/controllers/CategoriesController.php';
    require_once ADMIN_PATH . '/controllers/PagesController.php';
    require_once ADMIN_PATH . '/controllers/UsersController.php';
    require_once ADMIN_PATH . '/controllers/MediaController.php';
    require_once ADMIN_PATH . '/controllers/SettingsController.php';
    require_once ADMIN_PATH . '/controllers/MenusController.php';
    require_once ADMIN_PATH . '/controllers/ThemeController.php';
    require_once ADMIN_PATH . '/controllers/WidgetsController.php';

    $postsController = new AdminPostsController();
    $categoriesController = new AdminCategoriesController();
    $pagesController = new AdminPagesController();
    $usersController = new AdminUsersController();
    $mediaController = new AdminMediaController();
    $settingsController = new AdminSettingsController();
    $menusController = new AdminMenusController();
    $themeController = new AdminThemeController();
    $widgetsController = new AdminWidgetsController();
}

// ============================================
// Загрузка маршрутов
// ============================================

require_once CORE_PATH . '/routes.php';

// ============================================
// Обработка запроса
// ============================================

$router->dispatch();
