<?php
/**
 * Автозагрузчик классов
 * PSR-4 стиль для простого проекта
 */

class Autoloader
{
    /**
     * Регистрация автозагрузчика
     */
    public static function register(): void
    {
        spl_autoload_register([self::class, 'load']);
    }

    /**
     * Загрузка класса
     * @param string $class Имя класса
     */
    public static function load(string $class): void
    {
        // Маппинг классов к файлам
        $classMap = [
            'Database' => CORE_PATH . '/Database.php',
            'Router' => CORE_PATH . '/Router.php',
            'TemplateEngine' => CORE_PATH . '/TemplateEngine.php',
            'Request' => CORE_PATH . '/Request.php',
            'Session' => CORE_PATH . '/Session.php',
            'Auth' => CORE_PATH . '/Auth.php',
            'Hooks' => CORE_PATH . '/Hooks.php',
        ];

        if (isset($classMap[$class])) {
            if (file_exists($classMap[$class])) {
                require_once $classMap[$class];
            }
            return;
        }

        // Модели (Post, Page, Category, User, Comment, Menu, Setting)
        $modelFile = CORE_PATH . '/models/' . $class . '.php';
        if (file_exists($modelFile)) {
            require_once $modelFile;
            return;
        }

        // Автозагрузка контроллеров админки
        if (strpos($class, 'Admin') === 0 && strpos($class, 'Controller') !== false) {
            $controllerFile = ADMIN_PATH . '/controllers/' . str_replace('Controller', '', $class) . '.php';
            if (file_exists($controllerFile)) {
                require_once $controllerFile;
            }
        }
    }
}
