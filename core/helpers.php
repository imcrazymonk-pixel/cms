<?php
/**
 * Вспомогательные функции
 */

/**
 * Отладка - вывод переменных
 * @param mixed ...$vars
 */
function dd(...$vars): void
{
    echo '<pre>';
    foreach ($vars as $var) {
        var_dump($var);
        echo "\n";
    }
    echo '</pre>';
    die;
}

/**
 * Установить layout для текущего шаблона
 * @param string $layout
 * @return bool
 */
function setLayout(string $layout): bool
{
    $template = TemplateEngine::getInstance();
    if ($template) {
        $template->setLayout($layout);
        return true;
    }
    return false;
}

/**
 * Экранировать строку
 * @param string $string
 * @return string
 */
function e(string $string): string
{
    return htmlspecialchars($string, ENT_QUOTES, 'UTF-8');
}

/**
 * Редирект
 * @param string $url
 */
function redirect(string $url): void
{
    header('Location: ' . $url);
    exit;
}

/**
 * Редирект назад
 */
function back(): void
{
    $referer = $_SERVER['HTTP_REFERER'] ?? '/';
    redirect($referer);
}

/**
 * Получить значение из конфигурации
 * @param string $key
 * @param mixed $default
 * @return mixed
 */
function config(string $key, $default = null)
{
    $constants = [
        'DB_HOST' => DB_HOST,
        'DB_NAME' => DB_NAME,
        'DB_USER' => DB_USER,
        'DB_PASS' => DB_PASS,
        'SITE_NAME' => SITE_NAME,
        'SITE_URL' => SITE_URL,
        'ADMIN_EMAIL' => ADMIN_EMAIL,
        'DEBUG' => DEBUG,
        'POSTS_PER_PAGE' => POSTS_PER_PAGE,
    ];
    
    return $constants[$key] ?? $default;
}

/**
 * Проверка на AJAX запрос
 * @return bool
 */
function is_ajax(): bool
{
    return Request::isAjax();
}

/**
 * Получить CSRF токен
 * @return string
 */
function csrf_token(): string
{
    if (!Session::has('csrf_token')) {
        Session::set('csrf_token', bin2hex(random_bytes(32)));
    }
    return Session::get('csrf_token');
}

/**
 * CSRF поле для формы
 * @return string
 */
function csrf_field(): string
{
    return '<input type="hidden" name="csrf_token" value="' . csrf_token() . '">';
}

/**
 * Проверка CSRF токена
 * @param string|null $token
 * @return bool
 */
function verify_csrf(?string $token = null): bool
{
    $token = $token ?? Request::post('csrf_token');
    return $token && $token === Session::get('csrf_token');
}

/**
 * Форматирование даты
 * @param string $date
 * @param string $format
 * @return string
 */
function format_date(string $date, string $format = 'd.m.Y H:i'): string
{
    return date($format, strtotime($date));
}

/**
 * Обрезка текста
 * @param string $text
 * @param int $length
 * @param string $suffix
 * @return string
 */
function truncate(string $text, int $length = 100, string $suffix = '...'): string
{
    if (mb_strlen($text) <= $length) {
        return $text;
    }
    return mb_substr($text, 0, $length) . $suffix;
}

/**
 * Генерация slug из строки
 * @param string $string
 * @return string
 */
function slugify(string $string): string
{
    $string = mb_strtolower($string, 'UTF-8');
    $string = preg_replace('/[^a-z0-9\u0400-\u04FF\s-]/u', '', $string);
    $string = preg_replace('/[\s-]+/', '-', $string);
    return trim($string, '-') ?: uniqid();
}

/**
 * Логирование
 * @param string $message
 * @param string $level
 */
function log_message(string $message, string $level = 'info'): void
{
    if (!DEBUG) {
        return;
    }
    
    $logFile = ROOT_PATH . '/logs/app.log';
    $dir = dirname($logFile);
    
    if (!is_dir($dir)) {
        mkdir($dir, 0755, true);
    }
    
    $timestamp = date('Y-m-d H:i:s');
    $logEntry = "[{$timestamp}] [{$level}] {$message}" . PHP_EOL;
    
    file_put_contents($logFile, $logEntry, FILE_APPEND);
}
