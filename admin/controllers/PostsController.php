<?php
/**
 * Контроллер постов в админке
 */

class AdminPostsController
{
    private $post;
    private $category;

    public function __construct()
    {
        $this->post = new Post();
        $this->category = new Category();
    }

    /**
     * Список всех постов
     */
    public function index()
    {
        Auth::requireAdmin();

        $posts = $this->post->getAll();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Посты');
        $template->set('user', Auth::user());
        $template->set('posts', $posts);
        $template->setLayout('layouts/main');
        $template->display('posts/index');
    }

    /**
     * Форма создания поста
     */
    public function create()
    {
        Auth::requireAdmin();

        $categories = (new Category())->getAll();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Новый пост');
        $template->set('user', Auth::user());
        $template->set('categories', $categories);
        $template->setLayout('layouts/main');
        $template->display('posts/form');
    }

    /**
     * Создание поста
     */
    public function store()
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $title = trim(Request::post('title', ''));
        $slug = trim(Request::post('slug', ''));
        $content = Request::post('content', '');
        $excerpt = trim(Request::post('excerpt', ''));
        $category_id = $this->resolveCategoryId(Request::post('category_id', 0));
        $status = Request::post('status', 'published');
        $image = trim(Request::post('image', ''));

        $errors = [];
        if (empty($title)) {
            $errors[] = 'Заголовок обязателен';
        }
        if (empty($content)) {
            $errors[] = 'Содержимое обязательно';
        }

        if (!empty($errors)) {
            Session::set('post_errors', $errors);
            Session::set('post_old', $_POST);
            redirect('/admin/posts/create');
            return;
        }

        if (empty($slug)) {
            $slug = slugify($title);
        }

        $existing = $this->post->getBySlug($slug);
        if ($existing) {
            $slug .= '-' . time();
        }

        $this->post->create([
            'title' => $title,
            'slug' => $slug,
            'content' => $content,
            'excerpt' => $excerpt,
            'category_id' => $category_id,
            'status' => $status,
            'image' => $image,
            'user_id' => Auth::id(),
        ]);

        redirect('/admin/posts?success=created');
    }

    /**
     * Форма редактирования поста
     */
    public function edit($id)
    {
        Auth::requireAdmin();

        $post = $this->post->getById($id);
        if (!$post) {
            redirect('/admin/posts?error=not_found');
            return;
        }

        $categories = (new Category())->getAll();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Редактировать пост');
        $template->set('user', Auth::user());
        $template->set('post', $post);
        $template->set('categories', $categories);
        $template->setLayout('layouts/main');
        $template->display('posts/form');
    }

    /**
     * Обновление поста
     */
    public function update($id)
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $post = $this->post->getById($id);
        if (!$post) {
            redirect('/admin/posts?error=not_found');
            return;
        }

        $title = trim(Request::post('title', ''));
        $slug = trim(Request::post('slug', ''));
        $content = Request::post('content', '');
        $excerpt = trim(Request::post('excerpt', ''));
        $category_id = $this->resolveCategoryId(Request::post('category_id', 0));
        $status = Request::post('status', 'published');
        $image = trim(Request::post('image', ''));

        $errors = [];
        if (empty($title)) {
            $errors[] = 'Заголовок обязателен';
        }
        if (empty($content)) {
            $errors[] = 'Содержимое обязательно';
        }

        if (!empty($errors)) {
            Session::set('post_errors', $errors);
            Session::set('post_old', $_POST);
            redirect('/admin/posts/edit/' . $id);
            return;
        }

        if (empty($slug)) {
            $slug = slugify($title);
        }

        $existing = $this->post->getBySlug($slug);
        if ($existing && $existing['id'] != $id) {
            $slug .= '-' . time();
        }

        $this->post->update($id, [
            'title' => $title,
            'slug' => $slug,
            'content' => $content,
            'excerpt' => $excerpt,
            'category_id' => $category_id,
            'status' => $status,
            'image' => $image,
        ]);

        redirect('/admin/posts?success=updated');
    }

    /**
     * Удаление поста
     */
    public function delete($id)
    {
        Auth::requireAdmin();

        $this->post->delete($id);

        redirect('/admin/posts?success=deleted');
    }

    // ── V2: Новый редактор постов ─────────────────────────────────────

    /**
     * Список постов для v2 редактора
     */
    public function editorIndex()
    {
        Auth::requireAdmin();
        redirect('/admin/posts/v2/create');
    }

    /**
     * V2 — форма создания поста
     */
    public function editorCreate()
    {
        Auth::requireAdmin();
        $categories = (new Category())->getAll();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Новый пост — Редактор v2');
        $template->set('subtitle', 'Расширенный редактор с SEO, тегами и AI-ассистентом');
        $template->set('user', Auth::user());
        $template->set('categories', $categories);
        $template->setLayout('layouts/main');
        $template->display('posts/editor');
    }

    /**
     * V2 — форма редактирования поста
     */
    public function editorEdit($id)
    {
        Auth::requireAdmin();

        $post = $this->post->getById($id);
        if (!$post) {
            redirect('/admin/posts?error=not_found');
            return;
        }

        // Получаем теги поста
        $post['tags'] = $this->post->getTags($id);

        $categories = (new Category())->getAll();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Редактировать пост — Редактор v2');
        $template->set('subtitle', 'Расширенный редактор с SEO, тегами и AI-ассистентом');
        $template->set('user', Auth::user());
        $template->set('post', $post);
        $template->set('categories', $categories);
        $template->setLayout('layouts/main');
        $template->display('posts/editor');
    }

    /**
     * V2 — создание поста
     */
    public function editorStore()
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $title = trim(Request::post('title', ''));
        $slug = trim(Request::post('slug', ''));
        $content = Request::post('content', '');
        $excerpt = trim(Request::post('excerpt', ''));
        $category_id = $this->resolveCategoryId(Request::post('category_id', 0));
        $status = Request::post('status', 'draft');
        $image = trim(Request::post('image', ''));
        $seo_title = trim(Request::post('seo_title', ''));
        $seo_description = trim(Request::post('seo_description', ''));
        $tags_raw = trim(Request::post('tags', ''));
        $publish_date = trim(Request::post('publish_date', ''));

        $errors = [];
        if (empty($title)) {
            $errors[] = 'Заголовок обязателен';
        }

        if (!empty($errors)) {
            Session::set('post_errors', $errors);
            Session::set('post_old', $_POST);
            redirect('/admin/posts/v2/create');
            return;
        }

        if (empty($slug)) {
            $slug = slugify($title);
        }

        $existing = $this->post->getBySlug($slug);
        if ($existing) {
            $slug .= '-' . time();
        }

        $postData = [
            'title' => $title,
            'slug' => $slug,
            'content' => $content,
            'excerpt' => $excerpt,
            'category_id' => $category_id,
            'status' => $status,
            'image' => $image,
            'user_id' => Auth::id(),
        ];
        if ($publish_date) {
            $postData['created_at'] = $publish_date;
        }

        $newId = $this->post->create($postData);

        redirect('/admin/posts/v2/edit/' . $newId . '?success=created');
    }

    /**
     * V2 — обновление поста
     */
    public function editorUpdate($id)
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $post = $this->post->getById($id);
        if (!$post) {
            redirect('/admin/posts?error=not_found');
            return;
        }

        $title = trim(Request::post('title', ''));
        $slug = trim(Request::post('slug', ''));
        $content = Request::post('content', '');
        $excerpt = trim(Request::post('excerpt', ''));
        $category_id = $this->resolveCategoryId(Request::post('category_id', 0));
        $status = Request::post('status', 'draft');
        $image = trim(Request::post('image', ''));
        $seo_title = trim(Request::post('seo_title', ''));
        $seo_description = trim(Request::post('seo_description', ''));
        $tags_raw = trim(Request::post('tags', ''));
        $publish_date = trim(Request::post('publish_date', ''));

        $errors = [];
        if (empty($title)) {
            $errors[] = 'Заголовок обязателен';
        }

        if (!empty($errors)) {
            Session::set('post_errors', $errors);
            Session::set('post_old', $_POST);
            redirect('/admin/posts/v2/edit/' . $id);
            return;
        }

        if (empty($slug)) {
            $slug = slugify($title);
        }

        $existing = $this->post->getBySlug($slug);
        if ($existing && $existing['id'] != $id) {
            $slug .= '-' . time();
        }

        $updateData = [
            'title' => $title,
            'slug' => $slug,
            'content' => $content,
            'excerpt' => $excerpt,
            'category_id' => $category_id,
            'status' => $status,
            'image' => $image,
        ];
        if ($publish_date) {
            $updateData['created_at'] = $publish_date;
        }

        $this->post->update($id, $updateData);

        redirect('/admin/posts/v2/edit/' . $id . '?success=updated');
    }

    /**
     * Проверить, что категория существует; вернуть её ID или null,
     * чтобы не нарушать внешний ключ posts.category_id.
     */
    private function resolveCategoryId($categoryId)
    {
        $id = (int) $categoryId;
        if ($id <= 0) {
            return null;
        }
        $category = (new Category())->getById($id);
        return $category ? $id : null;
    }

    // ── Категории постов ──────────────────────────────────────────────

    /**
     * Список категорий
     */
    public function categories()
    {
        Auth::requireAdmin();

        $categories = $this->category->getAll();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Категории');
        $template->set('user', Auth::user());
        $template->set('categories', $categories);
        $template->setLayout('layouts/main');
        $template->display('posts/categories');
    }

    /**
     * Создание категории
     */
    public function categoryStore()
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $name = trim(Request::post('name', ''));
        $slug = trim(Request::post('slug', ''));
        $description = trim(Request::post('description', ''));

        if (empty($name)) {
            Session::set('category_error', 'Название обязательно');
            redirect('/admin/posts/categories');
            return;
        }

        if (empty($slug)) {
            $slug = slugify($name);
        }

        $existing = $this->category->getBySlug($slug);
        if ($existing) {
            $slug .= '-' . time();
        }

        $this->category->create([
            'name' => $name,
            'slug' => $slug,
            'description' => $description,
        ]);

        redirect('/admin/posts/categories?success=created');
    }

    /**
     * Обновление категории
     */
    public function categoryUpdate($id)
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $category = $this->category->getById($id);
        if (!$category) {
            redirect('/admin/posts/categories?error=not_found');
            return;
        }

        $name = trim(Request::post('name', ''));
        $slug = trim(Request::post('slug', ''));
        $description = trim(Request::post('description', ''));

        if (empty($name)) {
            Session::set('category_error', 'Название обязательно');
            redirect('/admin/posts/categories');
            return;
        }

        if (empty($slug)) {
            $slug = slugify($name);
        }

        $existing = $this->category->getBySlug($slug);
        if ($existing && $existing['id'] != $id) {
            $slug .= '-' . time();
        }

        $this->category->update($id, [
            'name' => $name,
            'slug' => $slug,
            'description' => $description,
        ]);

        redirect('/admin/posts/categories?success=updated');
    }

    /**
     * Удаление категории
     */
    public function categoryDelete($id)
    {
        Auth::requireAdmin();

        $this->category->delete($id);

        redirect('/admin/posts/categories?success=deleted');
    }
}
