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

// В Docker-окружении install.lock создаётся entrypoint-ом
if (!file_exists(ROOT_PATH . '/install.lock')) {
    @touch(ROOT_PATH . '/install.lock');
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

// ============================================
// Legacy PHP admin + JSON API disabled (Phase 2 migration)
// ============================================
// Админка отдаётся React SPA (admin-react/dist), весь JSON — FastAPI (backend/).
// Старые PHP-маршруты admin/* и /api/* недоступны. Публичный сайт не затрагивается.
// Для аварийного отката: set LEGACY_PHP_ADMIN = true (или константу в config.php).
if (!defined('LEGACY_PHP_ADMIN')) {
    define('LEGACY_PHP_ADMIN', false);
}
if (!LEGACY_PHP_ADMIN) {
    $__reqPath = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
    if (preg_match('#^/(admin|api)(/|$)#', $__reqPath)) {
        http_response_code(404);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['success' => false, 'error' => 'Not Found']);
        exit;
    }
    unset($__reqPath);
}

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
    require_once ADMIN_PATH . '/controllers/FinanceController.php';
    require_once ADMIN_PATH . '/controllers/LogController.php';
    require_once ADMIN_PATH . '/controllers/DiagnosticsController.php';

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
