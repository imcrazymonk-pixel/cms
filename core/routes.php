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
$router->get('admin/posts/edit/{id}', [$postsController, 'edit']);
$router->post('admin/posts/update/{id}', [$postsController, 'update']);
$router->get('admin/posts/delete/{id}', [$postsController, 'delete']);

// CRUD категорий
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

// Меню
$router->get('admin/menus', [$menusController, 'index']);
$router->post('admin/menus/store', [$menusController, 'store']);
$router->get('admin/menus/delete/{id}', [$menusController, 'delete']);
$router->get('admin/menus/edit/{id}', [$menusController, 'edit']);
$router->post('admin/menus/update/{id}', [$menusController, 'update']);

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

    $template = createTemplate();
    $template->set('title', 'Главная');
    $template->set('seo', $seoSettings);
    $template->set('posts', $posts);
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

$router->get('blog', function() {
    redirect('/');
});
