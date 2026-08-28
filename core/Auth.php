<?php
/**
 * Класс для аутентификации пользователей
 */

class Auth
{
    /**
     * Войти пользователя
     * @param string $login Логин или email
     * @param string $password Пароль
     * @return array|null Данные пользователя или null при ошибке
     */
    public static function attempt(string $login, string $password): ?array
    {
        $db = Database::getInstance();

        $user = $db->fetch(
            "SELECT * FROM users WHERE login = :login OR email = :email LIMIT 1",
            ['login' => $login, 'email' => $login]
        );

        if ($user && password_verify($password, $user['password'])) {
            Session::set('user_id', $user['id']);
            Session::set('user_login', $user['login']);
            Session::set('user_role', $user['role']);

            return $user;
        }

        return null;
    }

    /**
     * Проверить, авторизован ли пользователь
     * @return bool
     */
    public static function check(): bool
    {
        return Session::has('user_id');
    }

    /**
     * Получить текущего пользователя
     * @return array|null
     */
    public static function user(): ?array
    {
        if (!self::check()) {
            return null;
        }

        $db = Database::getInstance();
        return $db->fetch("SELECT id, login, email, role FROM users WHERE id = :id", [
            'id' => Session::get('user_id')
        ]);
    }

    /**
     * Получить ID текущего пользователя
     * @return int|null
     */
    public static function id(): ?int
    {
        return Session::get('user_id');
    }

    /**
     * Получить роль текущего пользователя
     * @return string|null
     */
    public static function role(): ?string
    {
        return Session::get('user_role');
    }

    /**
     * Выйти из системы
     */
    public static function logout(): void
    {
        Session::remove('user_id');
        Session::remove('user_login');
        Session::remove('user_role');
    }

    /**
     * Проверить роль пользователя
     * @param string|array $roles Роль или массив ролей
     * @return bool
     */
    public static function hasRole($roles): bool
    {
        if (!self::check()) {
            return false;
        }

        $userRole = self::role();
        
        if (is_array($roles)) {
            return in_array($userRole, $roles);
        }

        return $userRole === $roles;
    }

    /**
     * Проверить, что пользователь админ
     * @return bool
     */
    public static function isAdmin(): bool
    {
        return self::hasRole('admin');
    }

    /**
     * Проверить, что запрос AJAX
     * @return bool
     */
    private static function isAjax(): bool
    {
        return isset($_SERVER['HTTP_X_REQUESTED_WITH']) &&
               strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest';
    }

    /**
     * Требовать авторизацию (редирект на login если не авторизован)
     */
    public static function requireLogin(): void
    {
        if (!self::check()) {
            if (self::isAjax()) {
                http_response_code(401);
                header('Content-Type: application/json; charset=utf-8');
                echo json_encode(['success' => false, 'error' => 'Требуется авторизация']);
                exit;
            }
            header('Location: /admin/login');
            exit;
        }
    }

    /**
     * Требовать роль администратора
     */
    public static function requireAdmin(): void
    {
        self::requireLogin();
        if (!self::isAdmin()) {
            http_response_code(403);
            if (self::isAjax()) {
                header('Content-Type: application/json; charset=utf-8');
                echo json_encode(['success' => false, 'error' => 'Доступ запрещён. Требуется роль admin']);
                exit;
            }
            die('Доступ запрещён. Ваша роль: ' . self::role() . ', требуется: admin');
        }
    }
}
