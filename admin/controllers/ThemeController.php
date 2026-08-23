<?php
/**
 * Контроллер тем в админке:
 *  - менеджер установленных тем (список, активация, загрузка .zip);
 *  - универсальные настройки активной темы (из theme.php).
 */

class AdminThemeController
{
    private $setting;

    public function __construct()
    {
        $this->setting = new Setting();
    }

    /**
     * Страница «Темы»: список тем + настройки активной темы
     */
    public function index()
    {
        Auth::requireAdmin();

        $themeName = active_theme_name();
        $config = get_theme_config($themeName);
        $settings = $this->setting->getAll();
        $themes = $this->listThemes();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Темы');
        $template->set('user', Auth::user());
        $template->set('settings', $settings);
        $template->set('themeConfig', $config);
        $template->set('themeName', $themeName);
        $template->set('themes', $themes);
        $template->setLayout('layouts/main');
        $template->display('theme/index');
    }

    /**
     * Сохранение настроек активной темы
     */
    public function update()
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $themeName = active_theme_name();
        $prefix = $themeName . '_';
        $settingsData = Request::post('settings', []);

        $filtered = [];
        if (is_array($settingsData)) {
            foreach ($settingsData as $key => $value) {
                if (is_string($value)) {
                    $filtered[$prefix . $key] = trim($value);
                }
            }
        }

        $this->setting->setMultiple($filtered);

        redirect('/admin/theme?success=updated');
    }

    /**
     * Активация выбранной темы
     */
    public function activate()
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $theme = (string)Request::post('theme', '');
        $safeName = preg_match('/^[a-zA-Z0-9_-]+$/', $theme) ? $theme : '';

        if ($safeName && is_dir(TEMPLATES_PATH . '/themes/' . $safeName)) {
            $this->setting->set('active_theme', $safeName);
            redirect('/admin/theme?success=activated');
        }

        redirect('/admin/theme?error=badtheme');
    }

    /**
     * Загрузка темы из .zip архива.
     * Поддерживает два формата: архив с верхней папкой темы и архив
     * с файлами темы в корне. Статика из папки public/ уходит в public/{тема}.
     */
    public function upload()
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        if (!class_exists('ZipArchive')) {
            redirect('/admin/theme?error=nozip');
        }

        $file = $_FILES['theme_zip'] ?? null;
        if (!$file || ($file['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
            redirect('/admin/theme?error=upload');
        }

        $zip = new ZipArchive();
        if ($zip->open($file['tmp_name']) !== true) {
            redirect('/admin/theme?error=zip');
        }

        // 1) Список файлов в архиве (без директорий)
        $entries = [];
        for ($i = 0; $i < $zip->numFiles; $i++) {
            $entry = str_replace('\\', '/', $zip->getNameIndex($i));
            if ($entry !== '' && substr($entry, -1) !== '/') {
                $entries[] = $entry;
            }
        }

        if (!$entries) {
            $zip->close();
            redirect('/admin/theme?error=emptyzip');
        }

        // 2) Безопасная распаковка во временную папку
        $tmpBase = ROOT_PATH . '/storage/tmp_theme_' . uniqid();
        mkdir($tmpBase, 0755, true);

        foreach ($entries as $entry) {
            if (strpos($entry, '..') !== false) {
                continue;
            }
            if ($entry[0] === '/' || preg_match('/^[a-zA-Z]:/', $entry)) {
                continue;
            }
            $dest = $tmpBase . '/' . $entry;
            $dir = dirname($dest);
            if (!is_dir($dir)) {
                mkdir($dir, 0755, true);
            }
            $stream = $zip->getStream($entry);
            if ($stream) {
                $fp = fopen($dest, 'wb');
                if ($fp) {
                    stream_copy_to_stream($stream, $fp);
                    fclose($fp);
                }
                fclose($stream);
            }
        }
        $zip->close();

        // 3) Корень темы внутри архива (общая верхняя папка?)
        $prefix = '';
        $firstParts = explode('/', $entries[0]);
        if (count($firstParts) > 1) {
            $candidate = $firstParts[0];
            $allShare = true;
            foreach ($entries as $entry) {
                if (strpos($entry, $candidate . '/') !== 0) {
                    $allShare = false;
                    break;
                }
            }
            if ($allShare) {
                $prefix = $candidate;
            }
        }
        $srcRoot = $prefix ? ($tmpBase . '/' . $prefix) : $tmpBase;

        // 4) Имя темы: папка архива или название из theme.php
        $config = [];
        if (file_exists($srcRoot . '/theme.php')) {
            $loaded = require $srcRoot . '/theme.php';
            if (is_array($loaded)) {
                $config = $loaded;
            }
        }

        $themeName = '';
        if ($prefix) {
            $themeName = $prefix;
        } elseif (!empty($config['name'])) {
            $themeName = slugify((string)$config['name']);
        }

        if (!preg_match('/^[a-zA-Z0-9_-]+$/', $themeName) || $themeName === '') {
            $themeName = 'theme-' . date('YmdHis');
        }

        // 5) Копируем в templates/themes/{имя} и public/{имя}
        $themeDest = TEMPLATES_PATH . '/themes/' . $themeName;
        if (is_dir($themeDest)) {
            $this->removeDir($themeDest);
        }
        mkdir($themeDest, 0755, true);

        foreach (new DirectoryIterator($srcRoot) as $item) {
            if ($item->isDot()) {
                continue;
            }
            $fileName = $item->getFilename();
            if ($fileName === 'public') {
                // Статика темы → public/{имя}
                $publicDest = PUBLIC_PATH . '/' . $themeName;
                if (is_dir($publicDest)) {
                    $this->removeDir($publicDest);
                }
                $this->copyPath($item->getPathname(), $publicDest);
                continue;
            }
            $this->copyPath($item->getPathname(), $themeDest . '/' . $fileName);
        }

        // 6) Уборка временной папки
        $this->removeDir($tmpBase);

        redirect('/admin/theme?success=uploaded');
    }

    /**
     * Рекурсивное копирование файла/папки
     */
    private function copyPath(string $src, string $dest): void
    {
        if (is_dir($src)) {
            if (!is_dir($dest)) {
                mkdir($dest, 0755, true);
            }
            foreach (new DirectoryIterator($src) as $item) {
                if ($item->isDot()) {
                    continue;
                }
                $this->copyPath($item->getPathname(), $dest . '/' . $item->getFilename());
            }
            return;
        }
        if (is_file($src)) {
            copy($src, $dest);
        }
    }

    /**
     * Рекурсивное удаление папки
     */
    private function removeDir(string $dir): void
    {
        if (!is_dir($dir)) {
            return;
        }
        $items = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS),
            RecursiveIteratorIterator::CHILD_FIRST
        );
        foreach ($items as $item) {
            $item->isDir() ? rmdir($item->getPathname()) : unlink($item->getPathname());
        }
        rmdir($dir);
    }

    /**
     * Список установленных тем
     */
    private function listThemes(): array
    {
        $dir = TEMPLATES_PATH . '/themes';
        $active = active_theme_name();
        $themes = [];

        if (!is_dir($dir)) {
            return $themes;
        }

        foreach (scandir($dir) as $name) {
            if ($name === '.' || $name === '..' || !is_dir($dir . '/' . $name)) {
                continue;
            }
            $config = get_theme_config($name);
            $themes[] = [
                'name'        => $name,
                'label'       => $config['name'] ?? $name,
                'description' => $config['description'] ?? '',
                'active'      => ($name === $active),
            ];
        }

        return $themes;
    }
}
