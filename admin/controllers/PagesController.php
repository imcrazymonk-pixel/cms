<?php
/**
 * Контроллер страниц в админке
 */

class AdminPagesController
{
    private $page;

    public function __construct()
    {
        $this->page = new Page();
    }

    /**
     * Список всех страниц
     */
    public function index()
    {
        Auth::requireAdmin();

        $pages = $this->page->getAll();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Страницы');
        $template->set('user', Auth::user());
        $template->set('pages', $pages);
        $template->setLayout('layouts/main');
        $template->display('pages/index');
    }

    /**
     * Форма создания страницы
     */
    public function create()
    {
        Auth::requireAdmin();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Новая страница');
        $template->set('user', Auth::user());
        $template->setLayout('layouts/main');
        $template->display('pages/form');
    }

    /**
     * Создание страницы
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
        $meta_description = trim(Request::post('meta_description', ''));

        $errors = [];
        if (empty($title)) {
            $errors[] = 'Заголовок обязателен';
        }
        if (empty($content)) {
            $errors[] = 'Содержимое обязательно';
        }

        if (!empty($errors)) {
            Session::set('page_errors', $errors);
            Session::set('page_old', $_POST);
            redirect('/admin/pages/create');
            return;
        }

        if (empty($slug)) {
            $slug = slugify($title);
        }

        $existing = $this->page->getBySlug($slug);
        if ($existing) {
            $slug .= '-' . time();
        }

        $this->page->create([
            'title' => $title,
            'slug' => $slug,
            'content' => $content,
            'meta_description' => $meta_description,
            'user_id' => Auth::id(),
        ]);

        redirect('/admin/pages?success=created');
    }

    /**
     * Форма редактирования страницы
     */
    public function edit($id)
    {
        Auth::requireAdmin();

        $page = $this->page->getById($id);
        if (!$page) {
            redirect('/admin/pages?error=not_found');
            return;
        }

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Редактировать страницу');
        $template->set('user', Auth::user());
        $template->set('page', $page);
        $template->setLayout('layouts/main');
        $template->display('pages/form');
    }

    /**
     * Обновление страницы
     */
    public function update($id)
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $page = $this->page->getById($id);
        if (!$page) {
            redirect('/admin/pages?error=not_found');
            return;
        }

        $title = trim(Request::post('title', ''));
        $slug = trim(Request::post('slug', ''));
        $content = Request::post('content', '');
        $meta_description = trim(Request::post('meta_description', ''));

        $errors = [];
        if (empty($title)) {
            $errors[] = 'Заголовок обязателен';
        }
        if (empty($content)) {
            $errors[] = 'Содержимое обязательно';
        }

        if (!empty($errors)) {
            Session::set('page_errors', $errors);
            Session::set('page_old', $_POST);
            redirect('/admin/pages/edit/' . $id);
            return;
        }

        if (empty($slug)) {
            $slug = slugify($title);
        }

        $existing = $this->page->getBySlug($slug);
        if ($existing && $existing['id'] != $id) {
            $slug .= '-' . time();
        }

        $this->page->update($id, [
            'title' => $title,
            'slug' => $slug,
            'content' => $content,
            'meta_description' => $meta_description,
        ]);

        redirect('/admin/pages?success=updated');
    }

    /**
     * Удаление страницы
     */
    public function delete($id)
    {
        Auth::requireAdmin();

        $page = $this->page->getById($id);
        if ($page) {
            // Нельзя удалить главную страницу
            if ($page['is_home']) {
                redirect('/admin/pages?error=cannot_delete_home');
                return;
            }
            $this->page->delete($id);
        }

        redirect('/admin/pages?success=deleted');
    }

    /**
     * Установка главной страницы
     */
    public function setHome($id)
    {
        Auth::requireAdmin();

        $page = $this->page->getById($id);
        if (!$page) {
            redirect('/admin/pages?error=not_found');
            return;
        }

        $this->page->setAsHome($id);

        redirect('/admin/pages?success=home_set');
    }
}
