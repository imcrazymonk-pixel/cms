<?php
/**
 * DiagnosticsController — Мониторинг нод VPN (страница диагностики).
 *
 * Читает nodes_stats.json, сгенерированный Python-коллектором.
 * Предоставляет:
 *   - GET /admin/diagnostics — страница диагностики
 *   - GET /admin/diagnostics/api/data — AJAX-эндпоинт со свежими данными
 *   - POST /admin/diagnostics/api/collect — запуск сбора статистики
 */

class AdminDiagnosticsController
{
    private const STATS_FILE = ROOT_PATH . '/nodes_stats.json';
    private const COLLECT_SCRIPT = ROOT_PATH . '/tools/collect_stats.py';
    private const COLLECT_LOCK = ROOT_PATH . '/nodes_stats.lock';

    public function index(): void
    {
        Auth::requireAdmin();

        $data = $this->loadStats();
        $summary = $this->buildSummary($data);
        $isCollecting = file_exists(self::COLLECT_LOCK);

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Диагностика нод');
        $template->set('user', Auth::user());
        $template->set('nodes', $data['nodes'] ?? []);
        $template->set('summary', $summary);
        $template->set('collectedAt', $data['collected_at'] ?? null);
        $template->set('hasData', !empty($data));
        $template->set('isCollecting', $isCollecting);
        $template->set('scriptExists', file_exists(self::COLLECT_SCRIPT));
        $template->setLayout('layouts/main');
        $template->display('diagnostics/index');
    }

    public function apiData(): void
    {
        Auth::requireAdmin();

        $data = $this->loadStats();
        $summary = $this->buildSummary($data);
        $isCollecting = file_exists(self::COLLECT_LOCK);

        header('Content-Type: application/json; charset=utf-8');
        echo json_encode([
            'success' => true,
            'collected_at' => $data['collected_at'] ?? null,
            'nodes' => $data['nodes'] ?? [],
            'summary' => $summary,
            'is_collecting' => $isCollecting,
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }

    public function apiCollect(): void
    {
        Auth::requireAdmin();

        // Проверяем, не запущен ли уже сбор
        if (file_exists(self::COLLECT_LOCK)) {
            $this->jsonResponse(['success' => false, 'error' => 'Сбор уже запущен'], 409);
            return;
        }

        // Проверяем, существует ли скрипт
        if (!file_exists(self::COLLECT_SCRIPT)) {
            $this->jsonResponse(['success' => false, 'error' => 'Скрипт не найден: tools/collect_stats.py'], 404);
            return;
        }

        // Запускаем сбор в фоне: создаём lock, запускаем скрипт, удаляем lock по завершению
        $cmd = sprintf(
            'touch %s && python3 %s --save %s 2>&1; rm -f %s &',
            escapeshellarg(self::COLLECT_LOCK),
            escapeshellarg(self::COLLECT_SCRIPT),
            escapeshellarg(self::STATS_FILE),
            escapeshellarg(self::COLLECT_LOCK)
        );

        $output = [];
        exec($cmd, $output);

        $this->jsonResponse([
            'success' => true,
            'message' => 'Сбор статистики запущен в фоне',
        ]);
    }

    private function loadStats(): array
    {
        if (!file_exists(self::STATS_FILE)) {
            return [];
        }

        try {
            $content = file_get_contents(self::STATS_FILE);
            if (empty($content)) return [];

            $decoded = json_decode($content, true);
            return is_array($decoded) ? $decoded : [];
        } catch (\Throwable $e) {
            return [];
        }
    }

    private function buildSummary(array $data): array
    {
        $nodes = $data['nodes'] ?? [];
        $total = count($nodes);
        $reachable = 0;
        $unreachable = 0;
        $problems = 0;
        $avgLoad = 0.0;
        $loadCount = 0;

        foreach ($nodes as $n) {
            if ($n['reachable']) {
                $reachable++;
                $d = $n['data'] ?? [];
                if ($d['load']['1m'] ?? false) {
                    $avgLoad += (float)$d['load']['1m'];
                    $loadCount++;
                }
                // Проверки на проблемы
                $tcp = $d['tcp'] ?? [];
                if ($tcp['retrans_pct'] !== null && $tcp['retrans_pct'] >= 2) $problems++;
                if (($d['speed_download_mbps'] ?? 100) < 3) $problems++;
                if (($d['load']['1m'] ?? 0) > 0.8) $problems++;
                if (($d['nginx']['status'] ?? '') === 'error') $problems++;
            } else {
                $unreachable++;
                $problems++;
            }
        }

        return [
            'total' => $total,
            'reachable' => $reachable,
            'unreachable' => $unreachable,
            'problems' => $problems,
            'avgLoad' => $loadCount > 0 ? round($avgLoad / $loadCount, 2) : 0,
        ];
    }

    private function jsonResponse(array $data, int $status = 200): void
    {
        http_response_code($status);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($data, JSON_UNESCAPED_UNICODE);
        exit;
    }
}