<?php
/**
 * Контроллер медиа в админке
 */

class AdminMediaController
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Просмотр всех медиафайлов
     */
    public function index()
    {
        Auth::requireAdmin();

        $uploadDir = ROOT_PATH . '/public/uploads/';
        $files = [];

        if (is_dir($uploadDir)) {
            $iterator = new RecursiveIteratorIterator(
                new RecursiveDirectoryIterator($uploadDir)
            );

            foreach ($iterator as $file) {
                if ($file->isFile() && in_array(strtolower($file->getExtension()), ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'])) {
                    $relativePath = str_replace(ROOT_PATH, '', $file->getPathname());
                    $files[] = [
                        'path' => $relativePath,
                        'url' => '/public' . str_replace('/public', '', $relativePath),
                        'name' => $file->getFilename(),
                        'size' => $file->getSize(),
                        'modified' => $file->getMTime(),
                    ];
                }
            }
        }

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Медиафайлы');
        $template->set('user', Auth::user());
        $template->set('files', $files);
        $template->setLayout('layouts/main');
        $template->display('media/index');
    }

    /**
     * Загрузка файла
     */
    public function upload()
    {
        Auth::requireAdmin();

        if (!isset($_FILES['file']) && !isset($_FILES['image'])) {
            http_response_code(400);
            echo json_encode(['error' => 'Файл не найден']);
            return;
        }

        $file = $_FILES['file'] ?? $_FILES['image'];

        $allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
        $maxSize = 10 * 1024 * 1024;

        if (!in_array($file['type'], $allowed)) {
            http_response_code(400);
            echo json_encode(['error' => 'Недопустимый тип файла']);
            return;
        }

        if ($file['size'] > $maxSize) {
            http_response_code(400);
            echo json_encode(['error' => 'Файл слишком большой']);
            return;
        }

        $uploadDir = ROOT_PATH . '/public/uploads/images/';
        if (!is_dir($uploadDir)) {
            mkdir($uploadDir, 0755, true);
        }

        $ext = pathinfo($file['name'], PATHINFO_EXTENSION);
        $filename = uniqid() . '.' . $ext;
        $filepath = $uploadDir . $filename;

        if (move_uploaded_file($file['tmp_name'], $filepath)) {
            $url = '/public/uploads/images/' . $filename;
            
            // Для TinyMCE
            if (isset($_FILES['image'])) {
                echo json_encode(['location' => $url]);
            } else {
                echo json_encode(['success' => true, 'url' => $url]);
            }
        } else {
            http_response_code(500);
            echo json_encode(['error' => 'Ошибка загрузки']);
        }
    }

    /**
     * Удаление файла
     */
    public function delete()
    {
        Auth::requireAdmin();

        $path = Request::post('path', '');
        $filepath = ROOT_PATH . $path;

        if (file_exists($filepath) && strpos($path, '/public/uploads/') === 0) {
            unlink($filepath);
            echo json_encode(['success' => true]);
        } else {
            http_response_code(400);
            echo json_encode(['error' => 'Файл не найден']);
        }
    }
}
