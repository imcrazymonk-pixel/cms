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
 * Генерация slug из строки (с транслитерацией кириллицы)
 * @param string $string
 * @return string
 */
function slugify(string $string): string
{
    // Таблица транслитерации кириллицы в латиницу
    $transliteration = [
        'а' => 'a', 'б' => 'b', 'в' => 'v', 'г' => 'g', 'д' => 'd',
        'е' => 'e', 'ё' => 'yo', 'ж' => 'zh', 'з' => 'z', 'и' => 'i',
        'й' => 'y', 'к' => 'k', 'л' => 'l', 'м' => 'm', 'н' => 'n',
        'о' => 'o', 'п' => 'p', 'р' => 'r', 'с' => 's', 'т' => 't',
        'у' => 'u', 'ф' => 'f', 'х' => 'h', 'ц' => 'c', 'ч' => 'ch',
        'ш' => 'sh', 'щ' => 'sch', 'ъ' => '', 'ы' => 'y', 'ь' => '',
        'э' => 'e', 'ю' => 'yu', 'я' => 'ya',
        'А' => 'A', 'Б' => 'B', 'В' => 'V', 'Г' => 'G', 'Д' => 'D',
        'Е' => 'E', 'Ё' => 'Yo', 'Ж' => 'Zh', 'З' => 'Z', 'И' => 'I',
        'Й' => 'Y', 'К' => 'K', 'Л' => 'L', 'М' => 'M', 'Н' => 'N',
        'О' => 'O', 'П' => 'P', 'Р' => 'R', 'С' => 'S', 'Т' => 'T',
        'У' => 'U', 'Ф' => 'F', 'Х' => 'H', 'Ц' => 'C', 'Ч' => 'Ch',
        'Ш' => 'Sh', 'Щ' => 'Sch', 'Ъ' => '', 'Ы' => 'Y', 'Ь' => '',
        'Э' => 'E', 'Ю' => 'Yu', 'Я' => 'Ya',
        '№' => '',
    ];

    // Транслитерируем кириллицу
    $string = strtr($string, $transliteration);

    // Приводим к нижнему регистру
    $string = mb_strtolower($string, 'UTF-8');

    // Удаляем все недопустимые символы
    $string = preg_replace('/[^a-z0-9\s-]/u', '', $string);

    // Заменяем пробелы и множественные дефисы на один дефис
    $string = preg_replace('/[\s-]+/', '-', $string);

    // Удаляем дефисы по краям и возвращаем результат
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

/**
 * Получить настройку темы (активной) с кэшированием в рамках запроса.
 * Ключ может быть указан без префикса ('hero_title') — тогда он будет
 * разрешён в '<имя_темы>_hero_title', или с префиксом ('hexaveil_hero_title').
 * @param string $key Ключ настройки
 * @param string $default Значение по умолчанию
 * @return string
 */
function theme_setting(string $key, string $default = ''): string
{
    static $settings = null;

    if ($settings === null) {
        try {
            $settings = (new Setting())->getAll();
        } catch (\Throwable $e) {
            $settings = [];
        }
    }

    $prefix = $settings['active_theme'] ?? 'default';
    $fullKey = (strpos($key, $prefix . '_') === 0) ? $key : $prefix . '_' . $key;

    return (string)($settings[$fullKey] ?? $default);
}

/**
 * Имя активной темы
 * @return string
 */
function active_theme_name(): string
{
    static $theme = null;

    if ($theme === null) {
        try {
            $theme = (new Setting())->get('active_theme') ?: 'default';
        } catch (\Throwable $e) {
            $theme = 'default';
        }
    }

    return $theme;
}

/**
 * Конфигурация темы (из templates/themes/{тема}/theme.php)
 * @param string $theme Имя темы (пусто = активная)
 * @return array
 */
function get_theme_config(string $theme = ''): array
{
    static $cache = [];

    $theme = $theme ?: active_theme_name();
    if (isset($cache[$theme])) {
        return $cache[$theme];
    }

    $file = TEMPLATES_PATH . '/themes/' . $theme . '/theme.php';
    $config = [];
    if (file_exists($file)) {
        $loaded = require $file;
        if (is_array($loaded)) {
            $config = $loaded;
        }
    }

    $cache[$theme] = $config;
    return $config;
}

// ============================================
// Хуки (actions & filters) — обёртки над Hooks
// ============================================

function add_action(string $tag, callable $callback, int $priority = 10): void
{
    Hooks::addAction($tag, $callback, $priority);
}

function do_action(string $tag, ...$args): void
{
    Hooks::doAction($tag, ...$args);
}

function add_filter(string $tag, callable $callback, int $priority = 10): void
{
    Hooks::addFilter($tag, $callback, $priority);
}

function apply_filters(string $tag, $value, ...$args)
{
    return Hooks::applyFilters($tag, $value, ...$args);
}

// ============================================
// Виджеты
// ============================================

/**
 * Вывести область виджетов темы
 * @param string $area Имя области (header, footer, sidebar ...)
 * @return string
 */
function render_widget_area(string $area): string
{
    try {
        $widgets = (new Widget())->getAllByArea($area);
    } catch (\Throwable $e) {
        return '';
    }

    if (!$widgets) {
        return apply_filters('widget_area_html', '', $area);
    }

    $html = '';
    foreach ($widgets as $widget) {
        $html .= '<div class="widget widget-' . TemplateEngine::e($area) . '">';
        if (!empty($widget['title'])) {
            $html .= '<h4 class="widget-title">' . TemplateEngine::e($widget['title']) . '</h4>';
        }
        $html .= apply_filters('widget_content', $widget['content'] ?? '', $widget);
        $html .= '</div>';
    }

    return apply_filters('widget_area_html', $html, $area);
}
