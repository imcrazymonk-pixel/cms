<?php
/**
 * Класс для работы с сессиями
 */

class Session
{
    private static bool $initialized = false;

    /**
     * Инициализация сессии
     */
    public static function init(): void
    {
        if (!self::$initialized && session_status() === PHP_SESSION_NONE) {
            session_start();
            self::$initialized = true;
        }
    }

    /**
     * Установить значение в сессию
     * @param string $key
     * @param mixed $value
     */
    public static function set(string $key, $value): void
    {
        self::init();
        $_SESSION[$key] = $value;
    }

    /**
     * Получить значение из сессии
     * @param string $key
     * @param mixed $default
     * @return mixed
     */
    public static function get(string $key, $default = null)
    {
        self::init();
        return $_SESSION[$key] ?? $default;
    }

    /**
     * Проверить наличие ключа в сессии
     * @param string $key
     * @return bool
     */
    public static function has(string $key): bool
    {
        self::init();
        return isset($_SESSION[$key]);
    }

    /**
     * Удалить значение из сессии
     * @param string $key
     */
    public static function remove(string $key): void
    {
        self::init();
        unset($_SESSION[$key]);
    }

    /**
     * Получить и удалить значение (flash message)
     * @param string $key
     * @param mixed $default
     * @return mixed
     */
    public static function flash(string $key, $default = null)
    {
        $value = self::get($key, $default);
        self::remove($key);
        return $value;
    }

    /**
     * Уничтожить сессию
     */
    public static function destroy(): void
    {
        self::init();
        session_destroy();
        $_SESSION = [];
    }

    /**
     * Регенерировать ID сессии
     */
    public static function regenerate(): void
    {
        self::init();
        session_regenerate_id(true);
    }
}
