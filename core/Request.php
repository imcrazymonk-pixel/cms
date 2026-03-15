<?php
/**
 * Класс для работы с HTTP запросом
 */

class Request
{
    /**
     * Получить параметр из GET
     * @param string $key Имя параметра
     * @param mixed $default Значение по умолчанию
     * @return mixed
     */
    public static function get(string $key, $default = null)
    {
        return $_GET[$key] ?? $default;
    }

    /**
     * Получить параметр из POST
     * @param string $key Имя параметра
     * @param mixed $default Значение по умолчанию
     * @return mixed
     */
    public static function post(string $key, $default = null)
    {
        return $_POST[$key] ?? $default;
    }

    /**
     * Получить параметр из GET или POST
     * @param string $key Имя параметра
     * @param mixed $default Значение по умолчанию
     * @return mixed
     */
    public static function input(string $key, $default = null)
    {
        return self::post($key, self::get($key, $default));
    }

    /**
     * Получить все данные POST
     */
    public static function allPost(): array
    {
        return $_POST;
    }

    /**
     * Получить все данные GET
     */
    public static function allGet(): array
    {
        return $_GET;
    }

    /**
     * Проверить наличие параметра
     * @param string $key
     * @return bool
     */
    public static function has(string $key): bool
    {
        return isset($_POST[$key]) || isset($_GET[$key]);
    }

    /**
     * Получить HTTP метод
     * @return string
     */
    public static function method(): string
    {
        return $_SERVER['REQUEST_METHOD'];
    }

    /**
     * Проверить, что запрос AJAX
     * @return bool
     */
    public static function isAjax(): bool
    {
        return isset($_SERVER['HTTP_X_REQUESTED_WITH']) && 
               strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest';
    }

    /**
     * Получить URI запроса
     * @return string
     */
    public static function uri(): string
    {
        return parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
    }

    /**
     * Получить IP адрес клиента
     * @return string
     */
    public static function ip(): string
    {
        return $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
    }

    /**
     * Получить User Agent
     * @return string
     */
    public static function userAgent(): string
    {
        return $_SERVER['HTTP_USER_AGENT'] ?? '';
    }

    /**
     * Очистить входные данные (базовая санитизация)
     * @param string $key
     * @param mixed $default
     * @return string
     */
    public static function clean(string $key, $default = ''): string
    {
        $value = self::input($key, $default);
        return htmlspecialchars(trim($value), ENT_QUOTES, 'UTF-8');
    }
}
