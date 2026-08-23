<?php
/**
 * Простая система хуков в стиле WordPress.
 *
 * Actions — события, к которым можно подцепить свой код (add_action/do_action).
 * Filters — функции, изменяющие значение (add_filter/apply_filters).
 *
 * Примеры использования (в plugins/*.php или templates/themes/{тема}/functions.php):
 *   add_action('theme_footer_start', function() { echo '<p>Привет</p>'; });
 *   add_filter('theme_option', function($value, $key) { ... return $value; }, 10, 2);
 */

class Hooks
{
    private static array $actions = [];
    private static array $filters = [];

    /**
     * Зарегистрировать функцию на событие
     */
    public static function addAction(string $tag, callable $callback, int $priority = 10): void
    {
        self::$actions[$tag][$priority][] = $callback;
        ksort(self::$actions[$tag]);
    }

    /**
     * Вызвать все функции, зарегистрированные на событие
     */
    public static function doAction(string $tag, ...$args): void
    {
        if (empty(self::$actions[$tag])) {
            return;
        }
        foreach (self::$actions[$tag] as $callbacks) {
            foreach ($callbacks as $callback) {
                call_user_func_array($callback, $args);
            }
        }
    }

    /**
     * Зарегистрировать фильтр
     */
    public static function addFilter(string $tag, callable $callback, int $priority = 10): void
    {
        self::$filters[$tag][$priority][] = $callback;
        ksort(self::$filters[$tag]);
    }

    /**
     * Пропустить значение через все фильтры
     */
    public static function applyFilters(string $tag, $value, ...$args)
    {
        if (empty(self::$filters[$tag])) {
            return $value;
        }
        $args = array_merge([$value], $args);
        foreach (self::$filters[$tag] as $callbacks) {
            foreach ($callbacks as $callback) {
                $value = call_user_func_array($callback, $args);
                $args[0] = $value;
            }
        }
        return $value;
    }

    /**
     * Проверить, есть ли хуки на событии/фильтре
     */
    public static function has(string $tag): bool
    {
        return !empty(self::$actions[$tag]) || !empty(self::$filters[$tag]);
    }
}
