<?php
/**
 * Контроллер категорий в админке
 */

class AdminCategoriesController
{
    private $category;

    public function __construct()
    {
        $this->category = new Category();
    }

    /**
     * Список всех категорий
     */
    public function index()
    {
        Auth::requireAdmin();

        $categories = $this->category->getAll();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Категории');
        $template->set('user', Auth::user());
        $template->set('categories', $categories);
        $template->setLayout('layouts/main');
        $template->display('categories/index');
    }

    /**
     * Создание категории
     */
    public function store()
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
            redirect('/admin/categories');
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

        redirect('/admin/categories?success=created');
    }

    /**
     * Обновление категории
     */
    public function update($id)
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $category = $this->category->getById($id);
        if (!$category) {
            redirect('/admin/categories?error=not_found');
            return;
        }

        $name = trim(Request::post('name', ''));
        $slug = trim(Request::post('slug', ''));
        $description = trim(Request::post('description', ''));

        if (empty($name)) {
            Session::set('category_error', 'Название обязательно');
            redirect('/admin/categories');
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

        redirect('/admin/categories?success=updated');
    }

    /**
     * Удаление категории
     */
    public function delete($id)
    {
        Auth::requireAdmin();

        $this->category->delete($id);

        redirect('/admin/categories?success=deleted');
    }
}
