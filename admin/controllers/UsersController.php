<?php
/**
 * Контроллер пользователей в админке
 */

class AdminUsersController
{
    private $user;

    public function __construct()
    {
        $this->user = new User();
    }

    /**
     * Список всех пользователей
     */
    public function index()
    {
        Auth::requireAdmin();

        $users = $this->user->getAll();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Пользователи');
        $template->set('user', Auth::user());
        $template->set('users', $users);
        $template->setLayout('layouts/main');
        $template->display('users/index');
    }

    /**
     * Создание пользователя
     */
    public function store()
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $login = trim(Request::post('login', ''));
        $email = trim(Request::post('email', ''));
        $password = Request::post('password', '');
        $role = Request::post('role', 'author');

        $errors = [];
        if (empty($login)) {
            $errors[] = 'Логин обязателен';
        }
        if (empty($email)) {
            $errors[] = 'Email обязателен';
        }
        if (empty($password)) {
            $errors[] = 'Пароль обязателен';
        }

        if (!empty($errors)) {
            Session::set('user_errors', $errors);
            Session::set('user_old', $_POST);
            redirect('/admin/users');
            return;
        }

        $this->user->create([
            'login' => $login,
            'email' => $email,
            'password' => password_hash($password, HASH_ALGO),
            'role' => $role,
        ]);

        redirect('/admin/users?success=created');
    }

    /**
     * Обновление пользователя
     */
    public function update($id)
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $user = $this->user->getById($id);
        if (!$user) {
            redirect('/admin/users?error=not_found');
            return;
        }

        $login = trim(Request::post('login', ''));
        $email = trim(Request::post('email', ''));
        $password = Request::post('password', '');
        $role = Request::post('role', 'author');

        $errors = [];
        if (empty($login)) {
            $errors[] = 'Логин обязателен';
        }
        if (empty($email)) {
            $errors[] = 'Email обязателен';
        }

        if (!empty($errors)) {
            Session::set('user_errors', $errors);
            Session::set('user_old', $_POST);
            redirect('/admin/users');
            return;
        }

        $data = [
            'login' => $login,
            'email' => $email,
            'role' => $role,
        ];

        if (!empty($password)) {
            $data['password'] = password_hash($password, HASH_ALGO);
        }

        $this->user->update($id, $data);

        redirect('/admin/users?success=updated');
    }

    /**
     * Удаление пользователя
     */
    public function delete($id)
    {
        Auth::requireAdmin();

        // Нельзя удалить самого себя
        if ($id == Auth::id()) {
            redirect('/admin/users?error=cannot_delete_self');
            return;
        }

        $this->user->delete($id);

        redirect('/admin/users?success=deleted');
    }
}
