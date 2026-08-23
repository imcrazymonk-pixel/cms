<?php
/**
 * Контроллер постов в админке
 */

class AdminPostsController
{
    private $post;

    public function __construct()
    {
        $this->post = new Post();
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
        $status = Request::post('status', 'draft');
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
        $status = Request::post('status', 'draft');
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
}
