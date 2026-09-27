<?php
/**
 * AdminLogController — страница «Логи» с табами и внешними источниками.
 *
 * Ряд 1 — Категории: Все | Система | Сайт | Модули | Инфраструктура | Docker | Loki | Финансы | Пользователи
 * Ряд 2 — Уровни:    Все | Info | Warning | Error
 *
 * Docker/Loki подключаются через сервисы, настроенные в settings.
 */

class AdminLogController
{
    private $model;

    private const CATEGORY_LABELS = [
        'all'          => 'Все',
        'system'       => 'Система',
        'site'         => 'Сайт',
        'modules'      => 'Модули',
        'infrastructure' => 'Инфраструктура',
        'docker'       => 'Docker',
        'loki'         => 'Loki',
        'finance'      => 'Финансы',
        'users'        => 'Пользователи',
    ];

    private const CATEGORY_ICONS = [
        'all'          => 'terminal',
        'system'       => 'settings',
        'site'         => 'globe',
        'modules'      => 'package',
        'infrastructure' => 'server',
        'docker'       => 'container',
        'loki'         => 'bar-chart',
        'finance'      => 'wallet',
        'users'        => 'users',
    ];

    private const LEVEL_LABELS = [
        ''       => 'Все уровни',
        'info'   => 'Info',
        'warning' => 'Warning',
        'error'  => 'Error',
    ];

    private const EXTERNAL_CATEGORIES = ['docker', 'loki'];

    public function __construct()
    {
        $this->model = new AppLog();
    }

    public function index(): void
    {
        Auth::requireAdmin();

        $category = (string)Request::get('category', '');
        $level    = (string)Request::get('level', '');
        $q        = (string)Request::get('q', '');
        $page     = max(1, (int)Request::get('page', 1));
        $perPage  = $this->sanitizePerPage((int)Request::get('per_page', 50));

        if (in_array($category, self::EXTERNAL_CATEGORIES, true)) {
            $logs  = $this->fetchExternalLogs($category, $level);
            $total = count($logs);
            $pages = 1;
        } else {
            $filters = $this->buildFilters($category, $level, $q);
            $list    = $this->model->getAll($filters, $page, $perPage);
            $logs    = $list['rows'];
            $total   = $list['total'];
            $pages   = max(1, (int)ceil($total / $perPage));
        }

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Логи');
        $template->set('user', Auth::user());
        $template->set('logs', $logs);
        $template->set('total', $total);
        $template->set('categories', self::CATEGORY_LABELS);
        $template->set('levels', self::LEVEL_LABELS);
        $template->set('categoryIcons', self::CATEGORY_ICONS);
        $template->set('activeCategory', $category ?: 'all');
        $template->set('activeLevel', $level);
        $template->set('q', $q);
        $template->set('page', $page);
        $template->set('per_page', $perPage);
        $template->set('pages', $pages);
        $template->set('isExternal', in_array($category, self::EXTERNAL_CATEGORIES, true));
        $template->setLayout('layouts/main');
        $template->display('logs/index');
    }

    public function clear(): void
    {
        Auth::requireAdmin();
        $body = json_decode(file_get_contents('php://input'), true) ?: [];
        $token = $body['csrf_token'] ?? '';
        if ($token === '' || $token !== Session::get('csrf_token')) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }

        $category = $body['category'] ?? '';
        if ($category !== '' && $category !== 'all') {
            if (in_array($category, self::EXTERNAL_CATEGORIES, true)) {
                $deleted = 0;
            } else {
                $deleted = $this->model->clearByCategory($category);
            }
        } else {
            $deleted = $this->model->clear();
        }

        $this->jsonResponse(['success' => true, 'deleted' => $deleted]);
    }

    public function dockerPreview(): void
    {
        Auth::requireAdmin();
        $docker = new DockerLogService();
        if (!$docker->isAvailable()) {
            $this->jsonResponse(['success' => false, 'error' => 'Docker not configured'], 400);
            return;
        }
        $container = (string)Request::get('container', '');
        $lines = (int)Request::get('lines', 50);
        $since = (string)Request::get('since', '30m');
        $level = (string)Request::get('level', '');

        if ($container !== '') {
            $logs = $docker->getContainerLogs($container, $lines, $since);
        } else {
            $logs = $docker->getAllLogs($lines, $since, $level);
        }

        $this->jsonResponse(['success' => true, 'logs' => $logs, 'total' => count($logs)]);
    }

    public function lokiPreview(): void
    {
        Auth::requireAdmin();
        $loki = new LokiLogService();
        if (!$loki->isAvailable()) {
            $this->jsonResponse(['success' => false, 'error' => 'Loki not configured'], 400);
            return;
        }
        $query = (string)Request::get('query', '');
        $limit = (int)Request::get('limit', 100);
        $sinceSec = (int)Request::get('since', 1800);
        $level = (string)Request::get('level', '');

        $logs = $loki->queryLogs($query, $limit, $sinceSec, $level);
        $this->jsonResponse(['success' => true, 'logs' => $logs, 'total' => count($logs)]);
    }

    private function buildFilters(string $category, string $level, string $q): array
    {
        $filters = [];
        if ($category !== '' && $category !== 'all') {
            $filters['category'] = $category;
        }
        if ($level !== '') {
            $filters['level'] = $level;
        }
        if ($q !== '') {
            $filters['q'] = $q;
        }
        return $filters;
    }

    private function fetchExternalLogs(string $category, string $level): array
    {
        if ($category === 'docker') {
            $docker = new DockerLogService();
            if (!$docker->isAvailable()) {
                return [];
            }
            return $docker->getAllLogs(100, '30m', $level);
        }

        if ($category === 'loki') {
            $loki = new LokiLogService();
            if (!$loki->isAvailable()) {
                return [];
            }
            return $loki->queryLogs('', 100, 1800, $level);
        }

        return [];
    }

    private function sanitizePerPage(int $perPage): int
    {
        if ($perPage < 1) return 50;
        return min($perPage, 200);
    }

    private function jsonResponse(array $data, int $status = 200): void
    {
        http_response_code($status);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($data, JSON_UNESCAPED_UNICODE);
        exit;
    }
}