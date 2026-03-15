<?php
/**
 * Контроллер меню в админке
 */

class AdminMenusController
{
    private $menu;

    public function __construct()
    {
        $this->menu = new Menu();
    }

    /**
     * Список меню
     */
    public function index()
    {
        Auth::requireAdmin();

        $menus = $this->menu->getAll();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Меню');
        $template->set('user', Auth::user());
        $template->set('menus', $menus);
        $template->setLayout('layouts/main');
        $template->display('menus/index');
    }

    /**
     * Создание пункта меню
     */
    public function store()
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $name = trim(Request::post('name', ''));
        $url = trim(Request::post('url', ''));
        $location = Request::post('location', 'main');

        if (empty($name) || empty($url)) {
            Session::set('menu_error', 'Название и URL обязательны');
            redirect('/admin/menus');
            return;
        }

        $this->menu->create([
            'name' => $name,
            'url' => $url,
            'location' => $location,
        ]);

        redirect('/admin/menus?success=created');
    }

    /**
     * Форма редактирования пункта меню
     */
    public function edit($id)
    {
        Auth::requireAdmin();

        $menuItem = $this->menu->getById($id);
        if (!$menuItem) {
            redirect('/admin/menus?error=not_found');
            return;
        }

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Редактировать меню');
        $template->set('user', Auth::user());
        $template->set('menuItem', $menuItem);
        $template->setLayout('layouts/main');
        $template->display('menus/edit');
    }

    /**
     * Обновление пункта меню
     */
    public function update($id)
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $menuItem = $this->menu->getById($id);
        if (!$menuItem) {
            redirect('/admin/menus?error=not_found');
            return;
        }

        $name = trim(Request::post('name', ''));
        $url = trim(Request::post('url', ''));
        $location = Request::post('location', 'main');

        if (empty($name) || empty($url)) {
            Session::set('menu_errors', ['Название и URL обязательны']);
            Session::set('menu_old', $_POST);
            redirect('/admin/menus/edit/' . $id);
            return;
        }

        $this->menu->update($id, [
            'name' => $name,
            'url' => $url,
            'location' => $location,
        ]);

        redirect('/admin/menus?success=updated');
    }

    /**
     * Удаление пункта меню
     */
    public function delete($id)
    {
        Auth::requireAdmin();

        $this->menu->delete($id);

        redirect('/admin/menus?success=deleted');
    }
}
