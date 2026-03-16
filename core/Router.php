<?php
/**
 * Роутер - маршрутизация запросов
 * Различает запросы к админке (/admin) и публичной части
 */

class Router
{
    private array $routes = [];
    private string $basePath = '';

    /**
     * Конструктор
     */
    public function __construct()
    {
        // Определяем базовый путь (для работы в подпапках)
        $scriptName = $_SERVER['SCRIPT_NAME'];
        $this->basePath = rtrim(dirname($scriptName), '/\\');
    }

    /**
     * Зарегистрировать маршрут
     * @param string $method HTTP метод (GET, POST, etc.)
     * @param string $path Путь URL
     * @param callable|array $handler Обработчик (контроллер@метод)
     */
    public function addRoute(string $method, string $path, $handler): void
    {
        $this->routes[] = [
            'method' => strtoupper($method),
            'path' => $path,
            'handler' => $handler,
        ];
    }

    /**
     * Добавить GET маршрут
     */
    public function get(string $path, $handler): void
    {
        $this->addRoute('GET', $path, $handler);
    }

    /**
     * Добавить POST маршрут
     */
    public function post(string $path, $handler): void
    {
        $this->addRoute('POST', $path, $handler);
    }

    /**
     * Обработать текущий запрос
     * @return mixed Результат работы контроллера
     */
    public function dispatch()
    {
        $method = $_SERVER['REQUEST_METHOD'];
        $uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

        // Убираем index.php из URI
        $uri = preg_replace('#/index\.php$#', '', $uri);
        
        // Убираем trailing slash
        $uri = rtrim($uri, '/');

        // Нормализуем URI
        if ($uri === '') {
            $uri = '';
        }

        // Ищем подходящий маршрут
        $params = [];
        foreach ($this->routes as $route) {
            if ($route['method'] !== $method) {
                continue;
            }

            if ($this->matchRoute($route['path'], $uri, $params)) {
                return $this->callHandler($route['handler'], $params);
            }
        }

        // Маршрут не найден - 404
        return $this->notFound();
    }

    /**
     * Проверить соответствие маршрута
     * @param string $pattern Шаблон маршрута
     * @param string $uri Текущий URI
     * @param array &$params Найденные параметры
     * @return bool
     */
    private function matchRoute(string $pattern, string $uri, array &$params = []): bool
    {
        // Особый случай: пустой маршрут (главная страница)
        if ($pattern === '' && $uri === '') {
            return true;
        }
        
        // Преобразуем шаблон в regex
        $pattern = '/' . trim($pattern, '/');
        $pattern = preg_replace('/\{([a-zA-Z_]+)\}/', '(?P<$1>[^/]+)', $pattern);
        $pattern = '#^' . $pattern . '$#';

        if (preg_match($pattern, $uri, $matches)) {
            $params = array_filter($matches, 'is_string', ARRAY_FILTER_USE_KEY);
            return true;
        }

        return false;
    }

    /**
     * Вызвать обработчик маршрута
     * @param callable|array $handler
     * @param array $params Параметры из URL
     * @return mixed
     */
    private function callHandler($handler, array $params)
    {
        if (is_callable($handler)) {
            return call_user_func_array($handler, $params);
        }

        if (is_array($handler) && count($handler) === 2) {
            [$controller, $action] = $handler;
            
            if (class_exists($controller)) {
                $instance = new $controller();
                if (method_exists($instance, $action)) {
                    return call_user_func_array([$instance, $action], $params);
                }
            }
        }

        throw new Exception("Handler not found: " . print_r($handler, true));
    }

    /**
     * Страница 404
     */
    private function notFound()
    {
        http_response_code(404);

        // Ищем 404 в активной теме или в default
        $themePath = TEMPLATES_PATH . '/themes/default/errors/404.php';
        if (file_exists($themePath)) {
            include $themePath;
        } elseif (file_exists(TEMPLATES_PATH . '/errors/404.php')) {
            include TEMPLATES_PATH . '/errors/404.php';
        } else {
            echo '<h1>404 - Страница не найдена</h1>';
        }

        return null;
    }

    /**
     * Получить текущий URI
     */
    public function getCurrentUri(): string
    {
        $uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
        if ($this->basePath && strpos($uri, $this->basePath) === 0) {
            $uri = substr($uri, strlen($this->basePath));
        }
        return '/' . trim($uri, '/');
    }

    /**
     * Получить все маршруты (для отладки)
     */
    public function getRoutes(): array
    {
        return $this->routes;
    }

    /**
     * Проверить, является ли запрос админским
     */
    public function isAdminRequest(): bool
    {
        $uri = $this->getCurrentUri();
        return strpos($uri, '/admin') === 0 || $uri === '/admin';
    }
}
