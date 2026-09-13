<?php
/**
 * AdminLogController — страница «Логи» в блоке «Система» админки.
 * Список записей из app_logs с фильтрами и очисткой.
 */

class AdminLogController
{
    private $model;

    public function __construct()
    {
        $this->model = new AppLog();
    }

    public function index()
    {
        Auth::requireAdmin();

        $level = (string)Request::get('level', '');
        $channel = (string)Request::get('channel', '');
        $q = (string)Request::get('q', '');
        $page = max(1, (int)Request::get('page', 1));
        $perPage = (int)Request::get('per_page', 50);
        if ($perPage < 1) {
            $perPage = 50;
        }
        if ($perPage > 200) {
            $perPage = 200;
        }

        $filters = [];
        if ($level !== '') {
            $filters['level'] = $level;
        }
        if ($channel !== '') {
            $filters['channel'] = $channel;
        }
        if ($q !== '') {
            $filters['q'] = $q;
        }

        $list = $this->model->getAll($filters, $page, $perPage);
        $levels = ['info', 'warning', 'error'];
        $channels = ['platega', 'auth', 'system'];

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Логи');
        $template->set('user', Auth::user());
        $template->set('logs', $list['rows']);
        $template->set('total', $list['total']);
        $template->set('levels', $levels);
        $template->set('channels', $channels);
        $template->set('filters', $filters);
        $template->set('page', $page);
        $template->set('per_page', $perPage);
        $template->set('pages', (int)ceil($list['total'] / max(1, $perPage)));
        $template->setLayout('layouts/main');
        $template->display('logs/index');
    }

    public function clear()
    {
        Auth::requireAdmin();
        $body = json_decode(file_get_contents('php://input'), true) ?: [];
        $token = $body['csrf_token'] ?? '';
        if ($token === '' || $token !== Session::get('csrf_token')) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }

        $deleted = $this->model->clear();
        $this->jsonResponse(['success' => true, 'deleted' => $deleted]);
    }

    private function jsonResponse(array $data, int $status = 200)
    {
        http_response_code($status);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($data, JSON_UNESCAPED_UNICODE);
        exit;
    }
}
