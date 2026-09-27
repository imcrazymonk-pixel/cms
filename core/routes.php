<?php
/**
 * Маршруты приложения
 * Подключается после инициализации ядра
 */

// ============================================
// Вспомогательные функции для маршрутов
// ============================================

/**
 * Загрузить пункты меню из БД
 */
function loadMenuItems(string $location = 'main', string $currentUri = ''): array
{
    $menu = new Menu();
    $items = $menu->getByLocation($location);

    foreach ($items as &$item) {
        $item['url'] = ltrim($item['url'], '/');
        $item['label'] = $item['name'];
        $item['active'] = ($item['url'] === trim($currentUri, '/')) ? true : false;
        if ($currentUri === '' && $item['url'] === '') {
            $item['active'] = true;
        }
    }

    return $items;
}

/**
 * Получить footer меню
 */
function loadFooterMenu(): array
{
    return loadMenuItems('footer', '');
}

/**
 * Получить SEO настройки
 */
function getSeoSettings(): array
{
    $settings = new Setting();
    $data = $settings->getAll();

    return [
        'title' => $data['site_name'] ?? SITE_NAME,
        'description' => $data['site_description'] ?? $data['meta_description'] ?? '',
        'keywords' => $data['meta_keywords'] ?? '',
    ];
}

/**
 * Получить активную тему
 */
function getActiveTheme(): string
{
    $setting = new Setting();
    return $setting->get('active_theme') ?: 'default';
}

/**
 * Создать TemplateEngine с активной темой
 */
function createTemplate(): TemplateEngine
{
    $template = new TemplateEngine();
    $template->setTheme(getActiveTheme());
    return $template;
}

// ============================================
// CORS middleware для API
// ============================================

/**
 * Set CORS headers for React SPA
 */
function apiCorsHeaders(): void
{
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type, Authorization');
    header('Access-Control-Max-Age: 86400');
}

/**
 * Send JSON response
 */
function apiJson(mixed $data, int $code = 200): void
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

/**
 * Send JSON error response
 */
function apiError(string $message, int $code = 400): void
{
    apiJson(['success' => false, 'error' => $message], $code);
}

/**
 * Authenticate API request via JWT Bearer token
 * Returns decoded payload or sends 401
 */
function apiAuth(): array
{
    $authHeader = $_SERVER['HTTP_AUTHORIZATION'] 
        ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] 
        ?? '';

    if (!preg_match('/^Bearer\s+(.+)$/i', $authHeader, $matches)) {
        apiError('Требуется авторизация. Укажите Bearer token в заголовке Authorization.', 401);
    }

    $payload = JWTAuth::validateToken($matches[1]);
    if (!$payload) {
        apiError('Токен недействителен или истёк', 401);
    }

    return $payload;
}

// ============================================
// API маршруты (React SPA)
// ============================================

// CORS preflight — разрешить все API-запросы
$router->addRoute('OPTIONS', 'api/auth/login', function() {
    apiCorsHeaders();
    http_response_code(204);
    exit;
});

$router->addRoute('OPTIONS', 'api/auth/me', function() {
    apiCorsHeaders();
    http_response_code(204);
    exit;
});

// POST /api/auth/login — JWT authentication
$router->post('api/auth/login', function() {
    apiCorsHeaders();

    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $login = trim($body['login'] ?? '');
    $password = $body['password'] ?? '';

    if (empty($login) || empty($password)) {
        apiError('Логин и пароль обязательны');
    }

    // Use existing Auth::attempt to verify credentials (returns user array or null)
    $user = Auth::attempt($login, $password);

    if (!$user) {
        apiError('Неверный логин или пароль', 401);
    }

    $token = JWTAuth::generateToken($user);

    apiJson([
        'success' => true,
        'token' => $token,
        'user' => [
            'id'    => (int)$user['id'],
            'login' => $user['login'],
            'email' => $user['email'] ?? '',
            'role'  => $user['role'],
        ],
    ]);
});

// GET /api/auth/me — verify token and return current user
$router->get('api/auth/me', function() {
    apiCorsHeaders();

    $payload = apiAuth();

    $db = Database::getInstance();
    $user = $db->fetch(
        "SELECT id, login, email, role FROM users WHERE id = :id",
        ['id' => $payload['sub']]
    );

    if (!$user) {
        apiError('Пользователь не найден', 404);
    }

    apiJson([
        'success' => true,
        'user' => [
            'id'    => (int)$user['id'],
            'login' => $user['login'],
            'email' => $user['email'] ?? '',
            'role'  => $user['role'],
        ],
    ]);
});

// OPTIONS preflight for all API routes
$router->addRoute('OPTIONS', 'api/dashboard/stats', function() {
    apiCorsHeaders();
    http_response_code(204);
    exit;
});

// GET /api/dashboard/stats — dashboard statistics
$router->get('api/dashboard/stats', function() {
    apiCorsHeaders();
    apiAuth();

    $post = new Post();
    $category = new Category();
    $user = new User();
    $comment = new Comment();

    apiJson([
        'success' => true,
        'stats' => [
            'posts' => $post->getCount(),
            'comments' => class_exists('Comment') ? $comment->getCountByStatus('pending') : 0,
            'users' => $user->getCount(),
            'categories' => $category->getCount(),
        ],
    ]);
});

// OPTIONS preflight for posts API
$router->addRoute('OPTIONS', 'api/posts', function() { apiCorsHeaders(); http_response_code(204); exit; });
$router->addRoute('OPTIONS', 'api/posts/(\d+)', function() { apiCorsHeaders(); http_response_code(204); exit; });

// GET /api/posts — paginated list
$router->get('api/posts', function() {
    apiCorsHeaders();
    apiAuth();

    $page = max(1, (int)($_GET['page'] ?? 1));
    $perPage = min(100, max(1, (int)($_GET['per_page'] ?? 20)));
    $sort = $_GET['sort'] ?? 'created_at';
    $dir = strtoupper($_GET['dir'] ?? 'DESC') === 'ASC' ? 'ASC' : 'DESC';
    $search = trim($_GET['search'] ?? '');

    $allowedSort = ['id', 'title', 'status', 'created_at', 'updated_at'];
    if (!in_array($sort, $allowedSort)) $sort = 'created_at';

    $db = Database::getInstance();
    $where = '';
    $params = [];
    if ($search) {
        $where = "WHERE (p.title ILIKE :search OR p.slug ILIKE :search2)";
        $params['search'] = "%{$search}%";
        $params['search2'] = "%{$search}%";
    }

    $total = (int)$db->fetchOne("SELECT COUNT(*) FROM posts p {$where}", $params);
    $offset = ($page - 1) * $perPage;

    $posts = $db->fetchAll(
        "SELECT p.*, c.name as category_name, u.login as author_name
         FROM posts p
         LEFT JOIN categories c ON p.category_id = c.id
         LEFT JOIN users u ON p.user_id = u.id
         {$where}
         ORDER BY p.{$sort} {$dir}
         LIMIT {$perPage} OFFSET {$offset}",
        $params
    );

    apiJson([
        'success' => true,
        'data' => $posts,
        'total' => $total,
        'page' => $page,
        'per_page' => $perPage,
    ]);
});

// GET /api/posts/{id} — single post
$router->get('api/posts/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();
    $post = new Post();
    $entity = $post->getById((int)$id);
    if (!$entity) apiError('Пост не найден', 404);
    apiJson(['success' => true, 'data' => $entity]);
});

// POST /api/posts — create
$router->post('api/posts', function() {
    apiCorsHeaders();
    $auth = apiAuth();

    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $title = trim($body['title'] ?? '');
    if (empty($title)) apiError('Заголовок обязателен');

    $slug = trim($body['slug'] ?? '');
    if (empty($slug)) {
        $slug = strtolower(trim(preg_replace('/[^a-zA-Z0-9\-]+/', '-', $title), '-'));
    }

    $post = new Post();
    $id = $post->create([
        'title' => $title,
        'slug' => $slug,
        'content' => $body['content'] ?? '',
        'excerpt' => $body['excerpt'] ?? '',
        'category_id' => (int)($body['category_id'] ?? 0) ?: null,
        'status' => $body['status'] ?? 'draft',
        'image' => $body['image'] ?? '',
        'user_id' => (int)$auth['sub'],
    ]);

    apiJson(['success' => true, 'data' => ['id' => $id]], 201);
});

// POST /api/posts/{id} — update
$router->post('api/posts/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();

    $post = new Post();
    $existing = $post->getById((int)$id);
    if (!$existing) apiError('Пост не найден', 404);

    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $data = [];
    foreach (['title', 'slug', 'content', 'excerpt', 'status', 'image'] as $field) {
        if (isset($body[$field])) $data[$field] = trim($body[$field]);
    }
    if (isset($body['category_id'])) $data['category_id'] = (int)$body['category_id'] ?: null;

    if (!empty($data)) {
        $data['updated_at'] = date('Y-m-d H:i:s');
        $post->update((int)$id, $data);
    }

    apiJson(['success' => true]);
});

// DELETE /api/posts/{id} — delete
$router->addRoute('DELETE', 'api/posts/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();

    $post = new Post();
    $existing = $post->getById((int)$id);
    if (!$existing) apiError('Пост не найден', 404);

    $post->delete((int)$id);
    apiJson(['success' => true]);
});

// Categories API
$router->addRoute('OPTIONS', 'api/categories', function() { apiCorsHeaders(); http_response_code(204); exit; });
$router->addRoute('OPTIONS', 'api/categories/(\d+)', function() { apiCorsHeaders(); http_response_code(204); exit; });

$router->get('api/categories', function() {
    apiCorsHeaders();
    apiAuth();
    $category = new Category();
    apiJson(['success' => true, 'data' => $category->getAll()]);
});

$router->post('api/categories', function() {
    apiCorsHeaders();
    apiAuth();
    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $name = trim($body['name'] ?? '');
    if (empty($name)) apiError('Название обязательно');
    $slug = trim($body['slug'] ?? strtolower(trim(preg_replace('/[^a-z0-9-]+/', '-', $name), '-')));
    $category = new Category();
    $id = $category->create(['name' => $name, 'slug' => $slug, 'description' => $body['description'] ?? '']);
    apiJson(['success' => true, 'data' => ['id' => $id]], 201);
});

$router->post('api/categories/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();
    $category = new Category();
    if (!$category->getById((int)$id)) apiError('Категория не найдена', 404);
    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $data = [];
    foreach (['name', 'slug', 'description'] as $f) {
        if (isset($body[$f])) $data[$f] = trim($body[$f]);
    }
    if (!empty($data)) $category->update((int)$id, $data);
    apiJson(['success' => true]);
});

$router->delete('api/categories/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();
    $category = new Category();
    if (!$category->getById((int)$id)) apiError('Категория не найдена', 404);
    $category->delete((int)$id);
    apiJson(['success' => true]);
});

// Pages API
$router->addRoute('OPTIONS', 'api/pages', function() { apiCorsHeaders(); http_response_code(204); exit; });
$router->addRoute('OPTIONS', 'api/pages/(\d+)', function() { apiCorsHeaders(); http_response_code(204); exit; });

$router->get('api/pages', function() {
    apiCorsHeaders();
    apiAuth();
    $page = new Page();
    apiJson(['success' => true, 'data' => $page->getAll()]);
});

$router->get('api/pages/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();
    $page = new Page();
    $entity = $page->getById((int)$id);
    if (!$entity) apiError('Страница не найдена', 404);
    apiJson(['success' => true, 'data' => $entity]);
});

$router->post('api/pages', function() {
    apiCorsHeaders();
    apiAuth();
    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $title = trim($body['title'] ?? '');
    if (empty($title)) apiError('Заголовок обязателен');
    $slug = trim($body['slug'] ?? strtolower(trim(preg_replace('/[^a-z0-9-]+/', '-', $title), '-')));
    $page = new Page();
    $id = $page->create([
        'title' => $title,
        'slug' => $slug,
        'content' => $body['content'] ?? '',
        'meta_description' => $body['meta_description'] ?? '',
        'status' => $body['status'] ?? 'draft',
    ]);
    apiJson(['success' => true, 'data' => ['id' => $id]], 201);
});

$router->post('api/pages/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();
    $page = new Page();
    if (!$page->getById((int)$id)) apiError('Страница не найдена', 404);
    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $data = [];
    foreach (['title', 'slug', 'content', 'meta_description', 'status'] as $f) {
        if (isset($body[$f])) $data[$f] = trim($body[$f]);
    }
    if (!empty($data)) {
        $data['updated_at'] = date('Y-m-d H:i:s');
        $page->update((int)$id, $data);
    }
    apiJson(['success' => true]);
});

$router->delete('api/pages/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();
    $page = new Page();
    if (!$page->getById((int)$id)) apiError('Страница не найдена', 404);
    $page->delete((int)$id);
    apiJson(['success' => true]);
});

// Users API
$router->addRoute('OPTIONS', 'api/users', function() { apiCorsHeaders(); http_response_code(204); exit; });
$router->addRoute('OPTIONS', 'api/users/(\d+)', function() { apiCorsHeaders(); http_response_code(204); exit; });

$router->get('api/users', function() {
    apiCorsHeaders();
    apiAuth();
    $user = new User();
    $users = $user->getAll();
    // Strip passwords from output
    foreach ($users as &$u) unset($u['password']);
    apiJson(['success' => true, 'data' => $users]);
});

$router->get('api/users/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();
    $user = new User();
    $entity = $user->getById((int)$id);
    if (!$entity) apiError('Пользователь не найден', 404);
    unset($entity['password']);
    apiJson(['success' => true, 'data' => $entity]);
});

$router->post('api/users', function() {
    apiCorsHeaders();
    apiAuth();
    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $login = trim($body['login'] ?? '');
    $password = $body['password'] ?? '';
    if (empty($login) || empty($password)) apiError('Логин и пароль обязательны');
    $user = new User();
    $id = $user->create([
        'login' => $login,
        'email' => trim($body['email'] ?? ''),
        'password' => password_hash($password, HASH_ALGO),
        'role' => $body['role'] ?? 'author',
        'display_name' => trim($body['display_name'] ?? ''),
        'status' => $body['status'] ?? 'active',
    ]);
    apiJson(['success' => true, 'data' => ['id' => $id]], 201);
});

$router->post('api/users/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();
    $user = new User();
    if (!$user->getById((int)$id)) apiError('Пользователь не найден', 404);
    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $data = [];
    foreach (['login', 'email', 'role', 'display_name', 'status'] as $f) {
        if (isset($body[$f])) $data[$f] = trim($body[$f]);
    }
    if (!empty($body['password'])) {
        $data['password'] = password_hash($body['password'], HASH_ALGO);
    }
    if (!empty($data)) $user->update((int)$id, $data);
    apiJson(['success' => true]);
});

$router->delete('api/users/(\d+)', function($id) {
    apiCorsHeaders();
    apiAuth();
    if ((int)$id === (int)apiAuth()['sub']) apiError('Нельзя удалить самого себя');
    $user = new User();
    if (!$user->getById((int)$id)) apiError('Пользователь не найден', 404);
    $user->delete((int)$id);
    apiJson(['success' => true]);
});

// ============================================
// Маршруты админки
// ============================================

// Дашборд
$router->get('admin', function() {
    Auth::requireAdmin();

    $post = new Post();
    $category = new Category();
    $user = new User();
    $comment = new Comment();

    $stats = [
        'posts' => $post->getCount(),
        'comments' => $comment->getCountByStatus('pending'),
        'users' => $user->getCount(),
        'categories' => $category->getCount(),
    ];

    $recentPosts = $post->getRecent(5);

    $template = new TemplateEngine(ADMIN_PATH . '/templates');
    $template->set('title', 'Панель управления');
    $template->set('user', Auth::user());
    $template->set('stats', $stats);
    $template->set('recentPosts', $recentPosts);
    $template->setLayout('layouts/main');
    $template->display('dashboard');
});

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

$router->get('admin/logout', function() {
    Auth::logout();
    redirect('/admin/login');
});

// CRUD постов
$router->get('admin/posts', [$postsController, 'index']);
$router->get('admin/posts/create', [$postsController, 'create']);
$router->post('admin/posts/store', [$postsController, 'store']);
$router->get('admin/posts/edit/{id}', [$postsController, 'editorEdit']);
$router->post('admin/posts/update/{id}', [$postsController, 'editorUpdate']);
$router->get('admin/posts/delete/{id}', [$postsController, 'delete']);

// V2 — Новый редактор постов (параллельная разработка)
$router->get('admin/posts/v2', [$postsController, 'editorIndex']);
$router->get('admin/posts/v2/create', [$postsController, 'editorCreate']);
$router->get('admin/posts/v2/edit/{id}', [$postsController, 'editorEdit']);
$router->post('admin/posts/v2/store', [$postsController, 'editorStore']);
$router->post('admin/posts/v2/update/{id}', [$postsController, 'editorUpdate']);

// Категории постов (внутри меню Постов)
$router->get('admin/posts/categories', [$postsController, 'categories']);
$router->post('admin/posts/categories/store', [$postsController, 'categoryStore']);
$router->post('admin/posts/categories/update/{id}', [$postsController, 'categoryUpdate']);
$router->get('admin/posts/categories/delete/{id}', [$postsController, 'categoryDelete']);

// CRUD категорий (старый, пока оставляем для обратной совместимости)
$router->get('admin/categories', [$categoriesController, 'index']);
$router->post('admin/categories/store', [$categoriesController, 'store']);
$router->post('admin/categories/update/{id}', [$categoriesController, 'update']);
$router->get('admin/categories/delete/{id}', [$categoriesController, 'delete']);

// CRUD страниц
$router->get('admin/pages', [$pagesController, 'index']);
$router->get('admin/pages/create', [$pagesController, 'create']);
$router->post('admin/pages/store', [$pagesController, 'store']);
$router->get('admin/pages/edit/{id}', [$pagesController, 'edit']);
$router->post('admin/pages/update/{id}', [$pagesController, 'update']);
$router->get('admin/pages/delete/{id}', [$pagesController, 'delete']);
$router->get('admin/pages/set-home/{id}', [$pagesController, 'setHome']);

// Пользователи
$router->get('admin/users', [$usersController, 'index']);
$router->post('admin/users/store', [$usersController, 'store']);
$router->post('admin/users/update/{id}', [$usersController, 'update']);
$router->get('admin/users/delete/{id}', [$usersController, 'delete']);

// Медиа
$router->get('admin/media', [$mediaController, 'index']);
$router->post('admin/media/upload', [$mediaController, 'upload']);
$router->post('admin/media/delete', [$mediaController, 'delete']);

// Настройки
$router->get('admin/settings', [$settingsController, 'index']);
$router->post('admin/settings/update', [$settingsController, 'update']);

// Темы (менеджер + настройки активной темы)
$router->get('admin/theme', [$themeController, 'index']);
$router->post('admin/theme/update', [$themeController, 'update']);
$router->post('admin/theme/activate', [$themeController, 'activate']);
$router->post('admin/theme/upload', [$themeController, 'upload']);

// Виджеты
$router->get('admin/widgets', [$widgetsController, 'index']);
$router->post('admin/widgets/store', [$widgetsController, 'store']);
$router->post('admin/widgets/update/{id}', [$widgetsController, 'update']);
$router->get('admin/widgets/delete/{id}', [$widgetsController, 'delete']);

// Меню
$router->get('admin/menus', [$menusController, 'index']);
$router->post('admin/menus/store', [$menusController, 'store']);
$router->get('admin/menus/delete/{id}', [$menusController, 'delete']);
$router->get('admin/menus/edit/{id}', [$menusController, 'edit']);
$router->post('admin/menus/update/{id}', [$menusController, 'update']);

// Логи
$router->get('admin/logs', [AdminLogController::class, 'index']);
$router->post('admin/logs/clear', [AdminLogController::class, 'clear']);
$router->get('admin/logs/docker/preview', [AdminLogController::class, 'dockerPreview']);
$router->get('admin/logs/loki/preview', [AdminLogController::class, 'lokiPreview']);

// Финансовый модуль
$router->get('admin/finance', [AdminFinanceController::class, 'index']);
$router->get('admin/finance/api/data', [AdminFinanceController::class, 'apiData']);
$router->post('admin/finance/api/add', [AdminFinanceController::class, 'apiAdd']);
$router->post('admin/finance/api/edit', [AdminFinanceController::class, 'apiEdit']);
$router->post('admin/finance/api/delete', [AdminFinanceController::class, 'apiDelete']);
$router->post('admin/finance/api/delete-bulk', [AdminFinanceController::class, 'apiDeleteBulk']);
$router->post('admin/finance/api/import', [AdminFinanceController::class, 'apiImport']);
$router->get('admin/finance/api/export/csv', [AdminFinanceController::class, 'apiExportCsv']);
$router->get('admin/finance/api/settings', [AdminFinanceController::class, 'apiSettings']);
$router->post('admin/finance/api/settings', [AdminFinanceController::class, 'apiSettings']);

// Platega import
$router->post('admin/finance/api/platega/preview', [AdminFinanceController::class, 'apiPlategaPreview']);
$router->post('admin/finance/api/platega/import', [AdminFinanceController::class, 'apiPlategaImport']);
$router->post('admin/finance/api/platega/sync', [AdminFinanceController::class, 'apiPlategaSync']);
$router->get('admin/finance/api/platega/cron-sync', [AdminFinanceController::class, 'apiPlategaCronSync']);
$router->get('admin/finance/api/platega/settings', [AdminFinanceController::class, 'apiPlategaSettings']);
$router->post('admin/finance/api/platega/settings', [AdminFinanceController::class, 'apiPlategaSaveSettings']);

// YooKassa import
$router->post('admin/finance/api/yookassa/preview', [AdminFinanceController::class, 'apiYooKassaPreview']);
$router->post('admin/finance/api/yookassa/import', [AdminFinanceController::class, 'apiYooKassaImport']);
$router->post('admin/finance/api/yookassa/sync', [AdminFinanceController::class, 'apiYooKassaSync']);
$router->get('admin/finance/api/yookassa/cron-sync', [AdminFinanceController::class, 'apiYooKassaCronSync']);
$router->get('admin/finance/api/yookassa/settings', [AdminFinanceController::class, 'apiYooKassaSettings']);
$router->post('admin/finance/api/yookassa/settings', [AdminFinanceController::class, 'apiYooKassaSaveSettings']);

// Bulk actions
$router->post('admin/finance/api/bulk/type', [AdminFinanceController::class, 'apiBulkType']);
$router->post('admin/finance/api/bulk/category', [AdminFinanceController::class, 'apiBulkCategory']);
$router->post('admin/finance/api/bulk/participant', [AdminFinanceController::class, 'apiBulkParticipant']);
$router->post('admin/finance/api/bulk/description', [AdminFinanceController::class, 'apiBulkDescription']);
$router->post('admin/finance/api/export/selected', [AdminFinanceController::class, 'apiExportSelected']);

// ============================================
// Публичные маршруты
// ============================================

// Главная страница
$router->get('', function() {
    $page = new Page();
    $post = new Post();
    $category = new Category();

    // Проверяем, есть ли назначенная главная страница
    $homePage = $page->getHomePage();

    if ($homePage) {
        $template = createTemplate();
        $template->set('title', $homePage['title']);
        $template->set('seo', [
            'title' => $homePage['title'],
            'description' => $homePage['meta_description'] ?? '',
            'keywords' => '',
        ]);
        $template->set('page', $homePage);
        $template->set('menuItems', loadMenuItems('main', ''));
        $template->set('footerMenu', loadFooterMenu());
        
        // Используем шаблон из БД или default
        $templateName = 'page/' . ($homePage['template'] ?? 'default');
        $template->setLayout('layouts/main');
        $template->display($templateName);
        return;
    }

    // Если нет назначенной страницы - показываем список постов
    $posts = $post->getPublishedPosts(POSTS_PER_PAGE);
    $categories = $category->getAll();
    $seoSettings = getSeoSettings();
    
    // Посты для блог-секции на лендинге (берём из настроек темы)
    $blogPreviewCount = (int)(theme_setting('hexaveil_blog_preview_count', '3') ?: 3);
    $blogPosts = $post->getPublishedPosts($blogPreviewCount);

    $template = createTemplate();
    $template->set('title', 'Главная');
    $template->set('seo', $seoSettings);
    $template->set('posts', $posts);
    $template->set('blogPosts', $blogPosts);
    $template->set('categories', $categories);
    $template->set('menuItems', loadMenuItems('main', ''));
    $template->set('footerMenu', loadFooterMenu());
    $template->setLayout('layouts/main');
    $template->display('index');
});

// Страница поста
$router->get('post/{slug}', function($slug) {
    $post = new Post();
    $postEntity = $post->getBySlug($slug);

    if (!$postEntity) {
        http_response_code(404);
        $template = createTemplate();
        $template->set('title', 'Страница не найдена');
        $template->set('seo', ['title' => 'Страница не найдена']);
        $template->display('errors/404');
        return;
    }

    $post->incrementViews($postEntity['id']);

    $template = createTemplate();
    $template->set('title', $postEntity['title']);
    $template->set('seo', [
        'title' => $postEntity['title'],
        'description' => truncate(strip_tags($postEntity['excerpt'] ?? $postEntity['content']), 160),
        'keywords' => '',
    ]);
    $template->set('post', $postEntity);
    $template->set('comments', $post->getComments($postEntity['id']));
    $template->set('tags', $post->getTags($postEntity['id']));
    $template->set('relatedPosts', $post->getRelated($postEntity['category_id'], $postEntity['id']));
    $template->set('ogImage', $postEntity['image'] ?? '');
    $template->set('menuItems', loadMenuItems('main', 'post/' . $postEntity['slug']));
    $template->set('footerMenu', loadFooterMenu());
    $template->setLayout('layouts/main');
    $template->display('post');
});

// Категория
$router->get('category/{slug}', function($slug) {
    $category = new Category();
    $categoryEntity = $category->getBySlug($slug);

    if (!$categoryEntity) {
        http_response_code(404);
        $template = createTemplate();
        $template->set('title', 'Страница не найдена');
        $template->set('seo', ['title' => 'Страница не найдена']);
        $template->display('errors/404');
        return;
    }

    $template = createTemplate();
    $template->set('title', 'Категория: ' . $categoryEntity['name']);
    $template->set('seo', [
        'title' => 'Категория: ' . $categoryEntity['name'],
        'description' => $categoryEntity['description'] ?? '',
        'keywords' => '',
    ]);
    $template->set('categories', $category->getAll());
    $template->set('currentCategory', $slug);
    $template->set('category', $categoryEntity);
    $template->set('posts', $category->getPosts($categoryEntity['id']));
    $template->set('menuItems', loadMenuItems('main', 'category/' . $slug));
    $template->set('footerMenu', loadFooterMenu());
    $template->setLayout('layouts/main');
    $template->display('category');
});

// Статическая страница с префиксом /page/
$router->get('page/{slug}', function($slug) {
    $page = new Page();
    $pageEntity = $page->getBySlug($slug);

    if (!$pageEntity) {
        http_response_code(404);
        $template = createTemplate();
        $template->set('title', 'Страница не найдена');
        $template->set('seo', ['title' => 'Страница не найдена']);
        $template->display('errors/404');
        return;
    }

    $template = createTemplate();
    $template->set('title', $pageEntity['title']);
    $template->set('seo', [
        'title' => $pageEntity['title'],
        'description' => $pageEntity['meta_description'] ?? '',
        'keywords' => '',
    ]);
    $template->set('page', $pageEntity);
    $template->set('menuItems', loadMenuItems('main', 'page/' . $slug));
    $template->set('footerMenu', loadFooterMenu());
    $template->setLayout('layouts/main');
    
    // Используем шаблон из БД или default
    $templateName = 'page/' . ($pageEntity['template'] ?? 'default');
    $template->display($templateName);
});

// Универсальный роутинг для статических страниц (красивые URL без префикса /page/)

// Маршрут блога — ДО {slug}, иначе catch-all перехватит "blog"
$router->get('blog', function() {
    $post = new Post();
    $category = new Category();

    $posts = $post->getPublishedPosts(POSTS_PER_PAGE);
    $categories = $category->getAll();
    $seoSettings = getSeoSettings();

    $template = createTemplate();
    $template->set('title', 'Блог');
    $template->set('seo', [
        'title' => 'Блог | ' . ($seoSettings['title'] ?? SITE_NAME),
        'description' => 'Полезные статьи и новости сервиса',
        'keywords' => '',
    ]);
    $template->set('posts', $posts);
    $template->set('categories', $categories);
    $template->set('currentCategory', '');
    $template->set('menuItems', loadMenuItems('main', 'blog'));
    $template->set('footerMenu', loadFooterMenu());
    $template->setLayout('layouts/main');
    $template->display('blog');
});

$router->get('{slug}', function($slug) {
    $page = new Page();
    $pageEntity = $page->getBySlug($slug);

    if (!$pageEntity) {
        http_response_code(404);
        $template = createTemplate();
        $template->set('title', 'Страница не найдена');
        $template->set('seo', ['title' => 'Страница не найдена']);
        $template->display('errors/404');
        return;
    }

    $template = createTemplate();
    $template->set('title', $pageEntity['title']);
    $template->set('seo', [
        'title' => $pageEntity['title'],
        'description' => $pageEntity['meta_description'] ?? '',
        'keywords' => '',
    ]);
    $template->set('page', $pageEntity);
    $template->set('menuItems', loadMenuItems('main', $slug));
    $template->set('footerMenu', loadFooterMenu());
    $template->setLayout('layouts/main');
    
    // Используем шаблон из БД или default
    $templateName = 'page/' . ($pageEntity['template'] ?? 'default');
    $template->display($templateName);
});

// ============================================
// Настройки вида панели (добавлено: редизайн админки)
// ============================================

// Bulk-сохранение всех настроек вида одним JSON-блобом (Variant C)
// Вся панель UI: тема, режим, плотность, радиус, шрифт, анимации,
// свёрнутый сайдбар, колонки и т.д. — всё в одном ключе panel_ui_state.
$router->post('admin/settings/save-all-preferences', function() {
    Auth::requireAdmin();
    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    if (!empty($body)) {
        $pref = new UserPreference();
        $pref->set(Auth::id(), 'panel_ui_state', json_encode($body, JSON_UNESCAPED_UNICODE));
    }
    header('Content-Type: application/json');
    echo json_encode(['ok' => true]);
});

// Старый эндпоинт — сохранён для обратной совместимости (не используется в panel.js)
$router->post('admin/settings/save-preference', function() {
    Auth::requireAdmin();
    $body = json_decode(file_get_contents('php://input'), true) ?: [];
    $key = $body['key'] ?? '';
    $value = $body['value'] ?? '';
    $allowed = ['theme', 'mode', 'density', 'radius', 'fontSize'];
    if (in_array($key, $allowed, true) && $value !== '') {
        $pref = new UserPreference();
        $pref->set(Auth::id(), $key, (string)$value);
    }
    header('Content-Type: application/json');
    echo json_encode(['ok' => true]);
});
