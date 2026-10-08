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
// API и PHP-админка перенесены на FastAPI + React SPA (см. docs/MIGRATION_STATUS.md).
// nginx: /api/* и /admin/* в PHP не идут (см. .docker/nginx/default.conf).
// Здесь — только публичный сайт (лендинг + блог).
// ============================================

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
// Настройки вида панели (preferences) перенесены на FastAPI
// (/admin/settings/save-preference, /save-all-preferences) — nginx их сюда не пропускает.
// ============================================
