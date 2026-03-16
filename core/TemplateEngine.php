<?php
/**
 * Шаблонизатор CMS
 * Поддержка: переменные, partials, layout, кэширование, темы
 */

class TemplateEngine
{
    private string $templatePath;
    private array $data = [];
    private ?string $layout = null;
    private array $sections = [];
    private ?string $currentSection = null;
    private string $cachePath;
    private bool $cacheEnabled;
    private ?string $activeTheme = null;
    private static ?TemplateEngine $instance = null;

    public function __construct(string $templatePath = null, ?string $cachePath = null)
    {
        $this->templatePath = $templatePath ?? TEMPLATES_PATH;
        $this->cachePath = $cachePath ?? ROOT_PATH . '/storage/cache/templates';
        $this->cacheEnabled = $cachePath !== null && DEBUG === false;

        if ($this->cacheEnabled && !is_dir($this->cachePath)) {
            mkdir($this->cachePath, 0755, true);
        }

        // Сохраняем экземпляр для доступа из шаблонов
        self::$instance = $this;
    }

    /**
     * Установить активную тему
     */
    public function setTheme(string $theme): self
    {
        $this->activeTheme = $theme;
        return $this;
    }

    /**
     * Получить путь к активной теме
     */
    public function getThemePath(): string
    {
        if ($this->activeTheme && file_exists($this->templatePath . '/themes/' . $this->activeTheme)) {
            return $this->templatePath . '/themes/' . $this->activeTheme;
        }
        // По умолчанию используем тему 'default'
        if (file_exists($this->templatePath . '/themes/default')) {
            return $this->templatePath . '/themes/default';
        }
        return $this->templatePath;
    }

    /**
     * Получить текущий экземпляр TemplateEngine
     */
    public static function getInstance(): ?TemplateEngine
    {
        return self::$instance;
    }

    public function set(string $key, $value): self
    {
        $this->data[$key] = $value;
        return $this;
    }

    public function with(array $data): self
    {
        $this->data = array_merge($this->data, $data);
        return $this;
    }

    public function setLayout(string $layout): self
    {
        $this->layout = $layout;
        return $this;
    }

    public function startSection(string $name): void
    {
        $this->currentSection = $name;
        ob_start();
    }

    public function stopSection(): void
    {
        if ($this->currentSection) {
            $this->sections[$this->currentSection] = ob_get_clean();
            $this->currentSection = null;
        }
    }

    public function yieldSection(string $name, ?string $default = null): string
    {
        return $this->sections[$name] ?? $default ?? '';
    }

    public function render(string $template): string
    {
        $templateFile = $this->findTemplate($template);

        if (!file_exists($templateFile)) {
            throw new Exception("Template not found: {$template}");
        }

        $compiledFile = null;
        if ($this->cacheEnabled) {
            $compiledFile = $this->compile($templateFile);
        }

        extract($this->data);
        ob_start();

        if ($this->layout) {
            $content = $this->renderTemplate($templateFile, $compiledFile);
            $this->data['content'] = $content;
            extract($this->data);
            $layoutFile = $this->findTemplate($this->layout);
            if (file_exists($layoutFile)) {
                include $layoutFile;
            } else {
                echo $content;
            }
        } else {
            if ($compiledFile) {
                include $compiledFile;
            } else {
                include $templateFile;
            }
        }

        return ob_get_clean();
    }

    public function display(string $template): void
    {
        echo $this->render($template);
    }

    public function partial(string $template, array $data = []): string
    {
        $templateFile = $this->findTemplate('partials/' . $template);

        if (!file_exists($templateFile)) {
            return '';
        }

        extract(array_merge($this->data, $data));
        ob_start();
        include $templateFile;
        return ob_get_clean();
    }

    private function findTemplate(string $template): string
    {
        if (!pathinfo($template, PATHINFO_EXTENSION)) {
            $template .= '.php';
        }

        // Определяем базовый путь (тема или корень)
        $basePath = $this->getThemePath();

        // Ищем шаблон в базовой директории темы
        $templatePath = $basePath . '/' . $template;
        if (file_exists($templatePath)) {
            return $templatePath;
        }

        // Для layout ищем в папке layouts темы
        $layoutPath = $basePath . '/layouts/' . basename($template);
        if (file_exists($layoutPath)) {
            return $layoutPath;
        }

        // Для шаблонов страниц (page/xxx) ищем в templates/page/
        if (strpos($template, 'page/') === 0) {
            $pageTemplate = $this->templatePath . '/page/' . str_replace('page/', '', $template);
            if (file_exists($pageTemplate)) {
                return $pageTemplate;
            }
        }

        // Дополнительные пути для поиска
        $paths = [
            $this->templatePath . '/pages/' . $template,
        ];

        foreach ($paths as $path) {
            if (file_exists($path)) {
                return $path;
            }
        }

        // Если ничего не найдено, возвращаем путь к теме по умолчанию
        return $basePath . '/' . $template;
    }

    private function renderTemplate(string $templateFile, ?string $compiledFile = null): string
    {
        extract($this->data);
        ob_start();
        if ($compiledFile) {
            include $compiledFile;
        } else {
            include $templateFile;
        }
        return ob_get_clean();
    }

    private function compile(string $templateFile): string
    {
        $hash = md5_file($templateFile);
        $compiledFile = $this->cachePath . '/' . $hash . '.php';

        if (!file_exists($compiledFile)) {
            $content = file_get_contents($templateFile);

            $content = preg_replace_callback('/\{\{\s*\$(\w+)\s*\}\}/', function($m) {
                return '<?php echo ' . $m[1] . '; ?>';
            }, $content);

            $content = preg_replace_callback('/\{\{\s*\$(\w+)\|upper\s*\}\}/', function($m) {
                return '<?php echo strtoupper(' . $m[1] . '); ?>';
            }, $content);

            $content = preg_replace_callback('/\{\{\s*\$(\w+)\|lower\s*\}\}/', function($m) {
                return '<?php echo strtolower(' . $m[1] . '); ?>';
            }, $content);

            $content = preg_replace_callback('/\{\{\s*\$(\w+)\|e\s*\}\}/', function($m) {
                return '<?php echo htmlspecialchars(' . $m[1] . ', ENT_QUOTES, "UTF-8"); ?>';
            }, $content);

            file_put_contents($compiledFile, $content);
        }

        return $compiledFile;
    }

    public static function e(string $string): string
    {
        return htmlspecialchars($string, ENT_QUOTES, 'UTF-8');
    }

    public static function url(string $path = ''): string
    {
        return SITE_URL . '/' . ltrim($path, '/');
    }

    public static function asset(string $path): string
    {
        return SITE_URL . '/public/' . ltrim($path, '/');
    }

    /**
     * Получить URL изображения
     * Если путь начинается с /public/, добавляет SITE_URL
     */
    public static function image(string $path): string
    {
        if (empty($path)) {
            return '';
        }
        // Если путь уже абсолютный (с доменом) - возвращаем как есть
        if (strpos($path, 'http://') === 0 || strpos($path, 'https://') === 0) {
            return $path;
        }
        // Если путь начинается с /public/ - добавляем SITE_URL
        if (strpos($path, '/public/') === 0) {
            return SITE_URL . $path;
        }
        // Иначе считаем что это относительный путь от public/
        return SITE_URL . '/public/' . ltrim($path, '/');
    }

    public static function isActive(string $path, string $class = 'active'): string
    {
        $currentUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
        if ($currentUri === '/' . trim($path, '/')) {
            return $class;
        }
        return '';
    }
}
