<?php
/**
 * Точка входа приложения
 * Все запросы идут через этот файл
 */

// Определяем корневую директорию (если ещё не определена)
if (!defined('ROOT_PATH')) {
    define('ROOT_PATH', dirname(__DIR__));
}

// Проверка установки CMS
if (!file_exists(ROOT_PATH . '/install.lock')) {
    header('Location: /install/');
    exit;
}

// Подключаем конфигурацию
if (!file_exists(ROOT_PATH . '/config/config.php')) {
    die('Файл конфигурации не найден. Запустите установщик.');
}

require_once ROOT_PATH . '/config/config.php';

// Подключаем ядро
require_once CORE_PATH . '/Autoloader.php';
Autoloader::register();

require_once CORE_PATH . '/helpers.php';

// Инициализация сессии
Session::init();

// Инициализация роутера
$router = new Router();

// ============================================
// Публичные маршруты
// ============================================

// Главная страница
$router->get('', function() {
    $db = Database::getInstance();
    
    // Получаем последние посты
    $posts = $db->fetchAll("
        SELECT p.*, c.name as category_name, u.login as author
        FROM posts p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN users u ON p.user_id = u.id
        WHERE p.status = 'published'
        ORDER BY p.created_at DESC
        LIMIT " . POSTS_PER_PAGE
    );
    
    $template = new TemplateEngine();
    $template->set('title', 'Главная');
    $template->set('posts', $posts);
    $template->display('index');
});

// Страница поста
$router->get('post/{slug}', function($slug) {
    $db = Database::getInstance();

    $post = $db->fetch("
        SELECT p.*, c.name as category_name, c.slug as category, u.login as author
        FROM posts p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN users u ON p.user_id = u.id
        WHERE p.slug = :slug
    ", ['slug' => $slug]);
    
    if (!$post) {
        http_response_code(404);
        $template = new TemplateEngine();
        $template->display('errors/404');
        return;
    }
    
    // Увеличиваем счётчик просмотров
    $db->update('posts', ['views' => $post['views'] + 1], 'id = :id', ['id' => $post['id']]);
    
    // Получаем комментарии
    $comments = $db->fetchAll(
        "SELECT * FROM comments WHERE post_id = :post_id AND status = 'approved' ORDER BY created_at DESC",
        ['post_id' => $post['id']]
    );
    
    // Получаем теги
    $tags = $db->fetchAll("
        SELECT t.* FROM tags t
        INNER JOIN post_tags pt ON t.id = pt.tag_id
        WHERE pt.post_id = :post_id
    ", ['post_id' => $post['id']]);
    
    $template = new TemplateEngine();
    $template->set('title', $post['title']);
    $template->set('post', $post);
    $template->set('comments', $comments);
    $template->set('tags', $tags);
    $template->display('post');
});

// Категория
$router->get('category/{slug}', function($slug) {
    $db = Database::getInstance();
    
    $category = $db->fetch("SELECT * FROM categories WHERE slug = :slug", ['slug' => $slug]);
    
    if (!$category) {
        http_response_code(404);
        $template = new TemplateEngine();
        $template->display('errors/404');
        return;
    }
    
    $posts = $db->fetchAll(
        "SELECT * FROM posts WHERE category_id = :category_id AND status = 'published' ORDER BY created_at DESC",
        ['category_id' => $category['id']]
    );
    
    $template = new TemplateEngine();
    $template->set('title', 'Категория: ' . $category['name']);
    $template->set('category', $category);
    $template->set('posts', $posts);
    $template->display('category');
});

// Статическая страница
$router->get('page/{slug}', function($slug) {
    $db = Database::getInstance();
    
    $page = $db->fetch("SELECT * FROM pages WHERE slug = :slug", ['slug' => $slug]);
    
    if (!$page) {
        http_response_code(404);
        $template = new TemplateEngine();
        $template->display('errors/404');
        return;
    }
    
    $template = new TemplateEngine();
    $template->set('title', $page['title']);
    $template->set('page', $page);
    $template->display('page');
});

// ============================================
// Маршруты админки
// ============================================

// Главная админки
$router->get('admin', function() {
    Auth::requireAdmin();
    
    $db = Database::getInstance();
    
    // Статистика
    $stats = [
        'posts' => $db->fetchOne("SELECT COUNT(*) FROM posts"),
        'comments' => $db->fetchOne("SELECT COUNT(*) FROM comments WHERE status = 'pending'"),
        'users' => $db->fetchOne("SELECT COUNT(*) FROM users"),
    ];
    
    // Последние посты
    $recentPosts = $db->fetchAll("SELECT id, title, status, created_at FROM posts ORDER BY created_at DESC LIMIT 5");
    
    $template = new TemplateEngine(ADMIN_PATH . '/templates');
    $template->set('title', 'Панель управления');
    $template->set('user', Auth::user());
    $template->set('stats', $stats);
    $template->set('recentPosts', $recentPosts);
    $template->display('dashboard');
});

// Логин админки
$router->get('admin/login', function() {
    if (Auth::check()) {
        redirect('/admin');
    }
    
    $error = Session::flash('login_error');
    
    $template = new TemplateEngine(ADMIN_PATH . '/templates');
    $template->set('title', 'Вход в админку');
    $template->set('error', $error);
    $template->display('login');
});

$router->post('admin/login', function() {
    if (!verify_csrf()) {
        die('CSRF token invalid');
    }
    
    $login = Request::clean('login');
    $password = Request::post('password');
    
    $user = Auth::attempt($login, $password);
    
    if ($user) {
        redirect('/admin');
    } else {
        Session::set('login_error', 'Неверный логин или пароль');
        redirect('/admin/login');
    }
});

// Выход
$router->get('admin/logout', function() {
    Auth::logout();
    redirect('/admin/login');
});

// ============================================
// Обработка запроса
// ============================================
$router->dispatch();
