<?php
/**
 * AdminFinanceController — финансовый модуль «Финансы» в админке CMS.
 * Страница + JSON API (сводка, график, таблица, CRUD, импорт/экспорт CSV, настройки).
 */

class AdminFinanceController
{
    private $model;
    private $settings;
    private $db;

    public function __construct()
    {
        $this->model = new FinTransaction();
        $this->settings = new FinSetting();
        $this->db = Database::getInstance();
    }

    /* ─────────────────────────── Страница ─────────────────────────── */

    /**
     * Главная страница модуля
     */
    public function index()
    {
        Auth::requireAdmin();

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Финансы');
        $template->set('user', Auth::user());
        $template->set('finSettings', $this->settings->getAll());
        $template->set('cronToken', $this->ensureCronToken());
        $template->setLayout('layouts/main');
        $template->display('finance/index');
    }

    /* ─────────────────────────── Данные для дашборда ─────────────────────────── */

    /**
     * GET /admin/finance/api/data — всё для дашборда одним ответом.
     */
    public function apiData()
    {
        Auth::requireAdmin();

        try {
            $filters = $this->parseFilters();
            $page = max(1, (int)Request::get('page', 1));
            $perPage = (int)Request::get('per_page', 25);
            if ($perPage < 1) {
                $perPage = 25;
            }
            $sort = (string)Request::get('sort', 'date');
            $order = (string)Request::get('dir', 'desc');

            $list = $this->model->getAll($filters, $page, $perPage, $sort, $order);
            $summary = $this->model->getSummary();
            $averages = $this->model->getAverages();
            $chart = $this->model->getChartSeries($filters);
            $categories = $this->model->getCategories($filters);

            $transactions = [];
            foreach ($list['rows'] as $r) {
                $transactions[] = $this->formatRow($r);
            }

            $this->jsonResponse([
                'summary' => $summary,
                'averages' => $averages,
                'chart' => $chart,
                'categories' => $categories,
                'transactions' => $transactions,
                'pagination' => [
                    'page' => $page,
                    'per_page' => $perPage,
                    'total' => $list['total'],
                    'pages' => (int)ceil($list['total'] / max(1, $perPage)),
                ],
                'settings' => [
                    'currency' => $this->settings->get('currency', '₽'),
                    'decimals' => (int)$this->settings->get('decimals', 2),
                    'auto_refresh' => (int)$this->settings->get('auto_refresh', 0),
                    'avg_period' => $this->settings->get('avg_period', 'day'),
                    'platega_merchant_id' => $this->settings->get('platega_merchant_id', ''),
                    'platega_secret_raw' => $this->settings->get('platega_secret', ''),
                    'platega_days_back' => (int)$this->settings->get('platega_days_back', 150),
                    'platega_auto_sync' => (int)$this->settings->get('platega_auto_sync', 0),
                    'platega_last_sync' => $this->settings->get('platega_last_sync', ''),
                ],
                'all_months' => $this->allMonths(),
                'all_categories' => $this->model->distinctValues('category'),
                'all_participants' => $this->model->distinctValues('participant'),
                'anomalies' => $this->model->getAnomalies($filters),
            ]);
        } catch (\Throwable $e) {
            $this->jsonResponse(['error' => 'Ошибка загрузки данных: ' . $e->getMessage()], 500);
        }
    }

    /* ─────────────────────────── CRUD ─────────────────────────── */

    /**
     * POST /admin/finance/api/add
     */
    public function apiAdd()
    {
        Auth::requireAdmin();
        $body = $this->jsonBody();
        if (!$this->verifyJsonCsrf($body)) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }
        $error = $this->validateTransaction($body);
        if ($error) {
            $this->jsonResponse(['success' => false, 'error' => $error], 400);
            return;
        }
        try {
            $id = $this->model->create($this->cleanTransaction($body));
            $this->jsonResponse(['success' => true, 'id' => $id]);
        } catch (\Throwable $e) {
            $this->jsonResponse(['success' => false, 'error' => 'Ошибка сохранения'], 500);
        }
    }

    /**
     * POST /admin/finance/api/edit
     */
    public function apiEdit()
    {
        Auth::requireAdmin();
        $body = $this->jsonBody();
        if (!$this->verifyJsonCsrf($body)) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }
        $id = (int)($body['id'] ?? 0);
        $existing = $id ? $this->model->find($id) : null;
        if (!$existing) {
            $this->jsonResponse(['success' => false, 'error' => 'Запись не найдена'], 404);
            return;
        }
        $error = $this->validateTransaction($body);
        if ($error) {
            $this->jsonResponse(['success' => false, 'error' => $error], 400);
            return;
        }
        try {
            $this->model->update($id, $this->cleanTransaction($body));
            $this->jsonResponse(['success' => true]);
        } catch (\Throwable $e) {
            $this->jsonResponse(['success' => false, 'error' => 'Ошибка сохранения'], 500);
        }
    }

    /**
     * POST /admin/finance/api/delete
     */
    public function apiDelete()
    {
        Auth::requireAdmin();
        $body = $this->jsonBody();
        if (!$this->verifyJsonCsrf($body)) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }
        $id = (int)($body['id'] ?? 0);
        $existing = $id ? $this->model->find($id) : null;
        if (!$existing) {
            $this->jsonResponse(['success' => false, 'error' => 'Запись не найдена'], 404);
            return;
        }
        try {
            $this->model->delete($id);
            $this->jsonResponse(['success' => true]);
        } catch (\Throwable $e) {
            $this->jsonResponse(['success' => false, 'error' => 'Ошибка удаления'], 500);
        }
    }

    /* ─────────────────────────── Импорт / экспорт ─────────────────────────── */

    /**
     * POST /admin/finance/api/import — импорт CSV (multipart/form-data: file)
     */
    public function apiImport()
    {
        Auth::requireAdmin();
        if (!verify_csrf()) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }
        if (empty($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
            $this->jsonResponse(['success' => false, 'error' => 'Файл не загружен'], 400);
            return;
        }

        $path = $_FILES['file']['tmp_name'];
        $imported = 0;
        $skipped = 0;
        $errors = [];

        $handle = @fopen($path, 'r');
        if (!$handle) {
            $this->jsonResponse(['success' => false, 'error' => 'Не удалось прочитать файл'], 400);
            return;
        }

        // Убираем BOM
        $firstChunk = fgets($handle);
        if ($firstChunk !== false) {
            $firstChunk = preg_replace('/^\xEF\xBB\xBF/', '', $firstChunk);
        }

        // Автоопределение разделителя по первой строке
        $delimiter = $this->detectDelimiter($firstChunk);

        $line = 0;
        $normalized = $this->normalizeCsvLine($firstChunk, $delimiter);
        $isHeader = $normalized && mb_strtolower(trim((string)$normalized[0])) === 'date';
        if (!$isHeader) {
            // Первая строка — данные, обрабатываем её
            $line = $this->importCsvRow($normalized, $imported, $skipped, $errors);
        }

        while (($raw = fgets($handle)) !== false) {
            $row = $this->normalizeCsvLine($raw, $delimiter);
            $line = $this->importCsvRow($row, $imported, $skipped, $errors);
        }
        fclose($handle);

        $this->jsonResponse([
            'success' => true,
            'imported' => $imported,
            'skipped' => $skipped,
            'errors' => array_slice($errors, 0, 20),
        ]);
    }

    /**
     * GET /admin/finance/api/export/csv — выгрузка по текущим фильтрам
     */
    public function apiExportCsv()
    {
        Auth::requireAdmin();
        $filters = $this->parseFilters();
        $rows = $this->model->getFilteredAll($filters);

        header('Content-Type: text/csv; charset=utf-8');
        header('Content-Disposition: attachment; filename="finance_' . date('Ymd_His') . '.csv"');
        echo "\xEF\xBB\xBF"; // BOM для Excel

        $out = fopen('php://output', 'w');
        fputcsv($out, ['date', 'type', 'category', 'participant', 'amount', 'description'], ';');
        foreach ($rows as $r) {
            fputcsv($out, [
                $r['date'],
                $r['type'] === 'income' ? 'Доход' : 'Расход',
                $r['category'],
                $r['participant'] ?? '',
                $r['amount'],
                $r['description'] ?? '',
            ], ';');
        }
        fclose($out);
        exit;
    }

    /* ─────────────────────────── Platega ─────────────────────────── */

    /**
     * POST /admin/finance/api/platega/preview
     * Body: { merchant_id?, secret?, days_back? }
     * Returns preview rows with status: new|duplicate|skipped|excluded
     */
    public function apiPlategaPreview()
    {
        Auth::requireAdmin();
        $body = $this->jsonBody();
        if (!$this->verifyJsonCsrf($body)) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }

        $merchantId = trim((string)($body['merchant_id'] ?? ''));
        $secret = trim((string)($body['secret'] ?? ''));
        $daysBack = (int)($body['days_back'] ?? 150);
        if ($daysBack < 1 || $daysBack > 730) {
            $daysBack = 150;
        }

        // Если поля пустые — берём сохранённые настройки (как в FIN)
        if ($merchantId === '') {
            $merchantId = trim((string)$this->settings->get('platega_merchant_id', ''));
        }
        if ($secret === '') {
            $secret = trim((string)$this->settings->get('platega_secret', ''));
        }

        if (!$merchantId || !$secret) {
            $this->jsonResponse(['success' => false, 'error' => 'Укажите merchant_id и secret'], 400);
            return;
        }

        try {
            $preview = $this->fetchPlategaPreview($merchantId, $secret, $daysBack);
            $this->jsonResponse(['success' => true, 'transactions' => $preview]);
        } catch (\Throwable $e) {
            $msg = 'Platega preview error: ' . $e->getMessage();
            error_log($msg);
            $this->jsonResponse(['success' => false, 'error' => $msg], 500);
        }
    }

    /**
     * POST /admin/finance/api/platega/import
     * Body: { transactions: [...], include: true }
     * Only rows with include=true and status=new are imported.
     */
    public function apiPlategaImport()
    {
        Auth::requireAdmin();
        $body = $this->jsonBody();
        if (!$this->verifyJsonCsrf($body)) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }

        $txnList = $body['transactions'] ?? [];
        if (!is_array($txnList)) {
            $this->jsonResponse(['success' => false, 'error' => 'Некорректные данные'], 400);
            return;
        }

        $includeIds = [];
        foreach ($txnList as $t) {
            if (!empty($t['include']) && isset($t['record_id'])) {
                $includeIds[] = (string)$t['record_id'];
            }
        }

        if (empty($includeIds)) {
            $this->jsonResponse(['success' => true, 'added' => 0, 'skipped' => 0]);
            return;
        }

        try {
            $result = $this->commitPlategaImport($txnList, $includeIds);
            $this->settings->set('platega_last_sync', date('c'));
            $this->jsonResponse(['success' => true, 'added' => $result['added'], 'skipped' => $result['skipped']]);
        } catch (\Throwable $e) {
            $this->jsonResponse(['success' => false, 'error' => 'Ошибка импорта: ' . $e->getMessage()], 500);
        }
    }

    /**
     * POST /admin/finance/api/platega/sync
     * Автоимпорт Platega одним вызовом (для клиентского таймера):
     * preview новых платежей по сохранённым настройкам → импорт всех 'new' → обновление last_sync.
     */
    public function apiPlategaSync()
    {
        Auth::requireAdmin();
        $body = $this->jsonBody();
        if (!$this->verifyJsonCsrf($body)) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }
        $this->jsonResponse($this->runPlategaSync());
    }

    /**
     * GET /admin/finance/api/platega/cron-sync?token=XXX
     * Серверный автоимпорт для cron — работает БЕЗ сессии/CSRF, защищён токеном.
     * Вызывается cron'ом каждые 5 минут, например:
     *   curl -s "https://site/admin/finance/api/platega/cron-sync?token=XXX"
     */
    public function apiPlategaCronSync()
    {
        $token = (string)Request::get('token', '');
        $stored = (string)$this->settings->get('platega_cron_token', '');
        if ($stored === '' || !hash_equals($stored, $token)) {
            $this->jsonResponse(['success' => false, 'error' => 'forbidden'], 403);
            return;
        }
        $res = $this->runPlategaSync();
        $res['cron'] = true;
        $this->jsonResponse($res, $res['success'] ? 200 : ($res['code'] ?? 500));
    }

    /**
     * Общая логика Platega-синка (preview → импорт новых → last_sync).
     * Используется клиентским таймером и cron-эндпоинтом.
     * @return array ['success', 'added', 'skipped', 'new', ...]
     */
    private function runPlategaSync(): array
    {
        $merchantId = trim((string)$this->settings->get('platega_merchant_id', ''));
        $secret = trim((string)$this->settings->get('platega_secret', ''));
        $daysBack = (int)$this->settings->get('platega_days_back', 150);
        if ($daysBack < 1 || $daysBack > 730) {
            $daysBack = 150;
        }

        if (!$merchantId || !$secret) {
            return ['success' => false, 'error' => 'Platega не настроен (merchant_id/secret пусты)', 'code' => 400];
        }

        // Анти-гонка: если другой синк выполнялся менее 30 секунд назад — пропускаем,
        // чтобы два одновременных запроса не импортировали один и тот же платёж дважды.
        $lock = (int)$this->settings->get('platega_sync_lock', 0);
        if ($lock && (time() - $lock) < 30) {
            return ['success' => true, 'added' => 0, 'skipped' => 0, 'new' => 0, 'skipped_lock' => true];
        }
        $this->settings->set('platega_sync_lock', (string)time());

        try {
            $preview = $this->fetchPlategaPreview($merchantId, $secret, $daysBack);

            $newRows = [];
            foreach ($preview as $t) {
                if (isset($t['status']) && $t['status'] === 'new') {
                    $newRows[] = $t;
                }
            }

            $added = 0;
            $skipped = 0;
            if ($newRows) {
                $includeIds = array_map(function ($t) {
                    return (string)$t['record_id'];
                }, $newRows);
                $result = $this->commitPlategaImport($newRows, $includeIds);
                $added = (int)$result['added'];
                $skipped = (int)$result['skipped'];
            }

            $this->settings->set('platega_last_sync', date('c'));
            $this->settings->set('platega_sync_lock', '');

            return ['success' => true, 'added' => $added, 'skipped' => $skipped, 'new' => count($newRows)];
        } catch (\Throwable $e) {
            $this->settings->set('platega_sync_lock', '');
            error_log('Platega sync error: ' . $e->getMessage());
            return ['success' => false, 'error' => $e->getMessage(), 'code' => 500];
        }
    }

    /**
     * Гарантировать наличие токена для cron-синка (создать при первом обращении).
     */
    private function ensureCronToken(): string
    {
        $token = (string)$this->settings->get('platega_cron_token', '');
        if ($token === '') {
            $token = bin2hex(random_bytes(24));
            $this->settings->set('platega_cron_token', $token);
        }
        return $token;
    }

    /**
     * GET /admin/finance/api/platega/settings
     * Returns Platega-specific settings (merchant_id masked).
     */
    public function apiPlategaSettings()
    {
        Auth::requireAdmin();
        $merchantId = $this->settings->get('platega_merchant_id', '');
        $secret = $this->settings->get('platega_secret', '');
        $daysBack = (int)$this->settings->get('platega_days_back', 150);
        $autoSync = (int)$this->settings->get('platega_auto_sync', 0);
        $lastSync = $this->settings->get('platega_last_sync', '');

        $this->jsonResponse([
            'merchant_id' => $merchantId,
            'secret' => $secret ? '***' . substr($secret, -4) : '',
            'secret_raw' => $secret,
            'days_back' => $daysBack,
            'auto_sync' => $autoSync,
            'last_sync' => $lastSync,
        ]);
    }

    /**
     * POST /admin/finance/api/platega/settings
     * Saves Platega-specific settings.
     */
    public function apiPlategaSaveSettings()
    {
        Auth::requireAdmin();
        $body = $this->jsonBody();
        if (!$this->verifyJsonCsrf($body)) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }

        $allowed = ['platega_merchant_id', 'platega_secret', 'platega_days_back', 'platega_auto_sync'];
        foreach ($allowed as $key) {
            if (!array_key_exists($key, $body)) {
                continue;
            }
            $value = (string)$body[$key];
            if ($key === 'platega_days_back' || $key === 'platega_auto_sync') {
                $value = (string)max(0, (int)$value);
            }
            $this->settings->set($key, $value);
        }

        $this->jsonResponse(['success' => true]);
    }

    /* ─────────────────────────── Настройки ─────────────────────────── */

    /**
     * GET/POST /admin/finance/api/settings
     */
    public function apiSettings()
    {
        Auth::requireAdmin();

        if (Request::isAjax() && $_SERVER['REQUEST_METHOD'] === 'GET') {
            $this->jsonResponse($this->settings->getAll());
            return;
        }

        // POST — JSON body
        $body = $this->jsonBody();
        if (!$this->verifyJsonCsrf($body)) {
            $this->jsonResponse(['success' => false, 'error' => 'CSRF token invalid'], 403);
            return;
        }

        $allowed = [
            'currency', 'decimals', 'auto_refresh', 'avg_period',
            'avg_exclude_categories', 'avg_exclude_income_keywords',
            'avg_exclude_expense_keywords', 'quick_categories', 'quick_participants',
            'platega_merchant_id', 'platega_secret', 'platega_days_back', 'platega_auto_sync',
        ];
        foreach ($allowed as $key) {
            if (!array_key_exists($key, $body)) {
                continue;
            }
            $value = $body[$key];
            if (in_array($key, ['decimals', 'auto_refresh'], true)) {
                $value = (int)$value;
            }
            if (in_array($key, ['avg_exclude_categories', 'avg_exclude_income_keywords', 'avg_exclude_expense_keywords', 'quick_categories', 'quick_participants'], true)) {
                if (is_string($value)) {
                    $value = $value !== '' ? json_decode($value, true) : [];
                }
                $value = is_array($value) ? json_encode(array_values($value), JSON_UNESCAPED_UNICODE) : '[]';
            }
            $this->settings->set($key, (string)$value);
        }

        $this->jsonResponse(['success' => true]);
    }

    /* ─────────────────────────── Приватные помощники ─────────────────────────── */

    private function jsonResponse(array $data, int $status = 200)
    {
        http_response_code($status);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($data, JSON_UNESCAPED_UNICODE);
        exit;
    }

    private function jsonBody(): array
    {
        $raw = file_get_contents('php://input');
        $data = json_decode($raw ?: '', true);
        return is_array($data) ? $data : [];
    }

    private function verifyJsonCsrf(array $body): bool
    {
        $token = $body['csrf_token'] ?? '';
        return $token !== '' && $token === Session::get('csrf_token');
    }

    private function parseFilters(): array
    {
        return [
            'month' => (string)Request::get('month', ''),
            'since' => (string)Request::get('since', ''),
            'until' => (string)Request::get('until', ''),
            'type' => (string)Request::get('type', ''),
            'q' => (string)Request::get('q', ''),
        ];
    }

    private function validateTransaction(array $d): ?string
    {
        $date = (string)($d['date'] ?? '');
        if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date) || !strtotime($date)) {
            return 'Некорректная дата';
        }
        $type = (string)($d['type'] ?? '');
        if (!in_array($type, ['income', 'expense'], true)) {
            return 'Некорректный тип';
        }
        if (trim((string)($d['category'] ?? '')) === '') {
            return 'Категория обязательна';
        }
        $amount = (float)($d['amount'] ?? 0);
        if ($amount <= 0) {
            return 'Сумма должна быть больше нуля';
        }
        return null;
    }

    private function cleanTransaction(array $d): array
    {
        return [
            'date' => (string)$d['date'],
            'type' => (string)$d['type'],
            'category' => trim((string)($d['category'] ?? '')),
            'participant' => trim((string)($d['participant'] ?? '')),
            'amount' => round((float)$d['amount'], 2),
            'description' => trim((string)($d['description'] ?? '')),
        ];
    }

    private function formatRow(array $r): array
    {
        return [
            'id' => (int)$r['id'],
            'date' => $r['date'],
            'date_display' => date('d.m.Y', strtotime($r['date'])),
            'month' => substr($r['date'], 0, 7),
            'type' => $r['type'],
            'participant' => $r['participant'] ?? '',
            'category' => $r['category'],
            'amount' => (float)$r['amount'],
            'description' => $r['description'] ?? '',
        ];
    }

    private function allMonths(): array
    {
        $rows = Database::getInstance()->fetchAll(
            "SELECT DISTINCT DATE_FORMAT(`date`, '%Y-%m') AS m FROM fin_transactions ORDER BY m DESC"
        );
        $out = [];
        foreach ($rows as $r) {
            $out[] = $r['m'];
        }
        return $out;
    }

    private function detectDelimiter(string $line): string
    {
        if (substr_count($line, ';') >= substr_count($line, ',')) {
            return ';';
        }
        return ',';
    }

    private function normalizeCsvLine(string $raw, string $delimiter): ?array
    {
        $line = rtrim($raw, "\r\n");
        if ($line === '') {
            return null;
        }
        $fields = str_getcsv($line, $delimiter);
        $out = [];
        foreach ($fields as $f) {
            $out[] = $this->toUtf8(trim($f));
        }
        return $out;
    }

    private function toUtf8(string $s): string
    {
        if (mb_check_encoding($s, 'UTF-8')) {
            return $s;
        }
        $conv = @mb_convert_encoding($s, 'UTF-8', 'Windows-1251');
        return $conv !== false ? $conv : $s;
    }

    /* ─────────────────────────── Platega helpers ─────────────────────────── */

    private function httpPost(string $url, array $headers, string $body): string
    {
        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt_array($ch, [
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => $body,
                CURLOPT_HTTPHEADER => $headers,
                CURLOPT_TIMEOUT => 30,
            ]);
            $resp = curl_exec($ch);
            if ($resp === false) {
                throw new \RuntimeException('HTTP error: ' . curl_error($ch));
            }
            curl_close($ch);
            return $resp;
        }

        $opts = [
            'http' => [
                'method' => 'POST',
                'header' => implode("\r\n", $headers) . "\r\n",
                'content' => $body,
                'timeout' => 30,
            ],
            'ssl' => [
                'verify_peer' => true,
                'verify_peer_name' => true,
            ],
        ];
        $ctx = stream_context_create($opts);
        $resp = @file_get_contents($url, false, $ctx);
        if ($resp === false) {
            throw new \RuntimeException('HTTP error: unable to fetch ' . $url);
        }
        return $resp;
    }

    private function httpGet(string $url, array $headers = []): string
    {
        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt_array($ch, [
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_FOLLOWLOCATION => true,
                CURLOPT_TIMEOUT => 30,
                CURLOPT_HTTPHEADER => $headers,
                CURLOPT_USERAGENT => 'HexaVeil/1.0',
            ]);
            $text = curl_exec($ch);
            if ($text === false) {
                throw new \RuntimeException('HTTP error: ' . curl_error($ch));
            }
            curl_close($ch);
            return $text;
        }

        $opts = [
            'http' => [
                'method' => 'GET',
                'header' => implode("\r\n", $headers) . "\r\n",
                'timeout' => 30,
            ],
            'ssl' => [
                'verify_peer' => true,
                'verify_peer_name' => true,
            ],
        ];
        $ctx = stream_context_create($opts);
        $text = @file_get_contents($url, false, $ctx);
        if ($text === false) {
            throw new \RuntimeException('HTTP error: unable to fetch ' . $url);
        }
        return $text;
    }

    private function fetchPlategaPreview(string $merchantId, string $secret, int $daysBack): array
    {
        $from = gmdate('Y-m-d\TH:i:s\Z', strtotime('-' . $daysBack . ' days'));
        $to = gmdate('Y-m-d\TH:i:s\Z');

        $payload = [
            'statuses' => ['6', '7'],
            'paymentMethods' => ['2', '10', '11', '12', '13'],
            'from' => $from,
            'to' => $to,
            'timeZoneId' => 'Europe/Moscow',
        ];

        $resp = $this->httpPost(
            'https://app.platega.io/transaction/export/csv',
            [
                'Content-Type: application/json',
                'X-MerchantId: ' . $merchantId,
                'X-Secret: ' . $secret,
            ],
            json_encode($payload)
        );

        $data = json_decode($resp, true);
        if (!is_array($data) || empty($data['url'])) {
            throw new \RuntimeException('Platega API response missing url field');
        }

        $csvUrl = $data['url'];
        $csvText = $this->httpGet($csvUrl, ['User-Agent: HexaVeil/1.0']);

        $existingKeys = $this->plategaExistingKeys();
        $existingRecordIds = $this->plategaExistingRecordIds();
        $preview = [];
        $rows = $this->parsePlategaCsv($csvText);

        foreach ($rows as $row) {
            $recordId = (string)($row['RecordId'] ?? '');
            $status = strtoupper((string)($row['Status'] ?? ''));
            $createdAt = (string)($row['CreatedAt'] ?? '');
            $amount = (float)($row['Amount'] ?? 0);
            $description = (string)($row['Description'] ?? '');

            if ($status !== 'CONFIRMED') {
                $preview[] = [
                    'record_id' => $recordId,
                    'date' => substr($createdAt, 0, 10),
                    'type' => 'Доход',
                    'participant' => 'Platega пополнение',
                    'category' => 'Прибыль',
                    'amount' => 0,
                    'gross' => $amount,
                    'description' => mb_substr($description, 0, 60),
                    'status' => 'skipped',
                ];
                continue;
            }

            $dt = DateTime::createFromFormat('Y-m-d H:i:s', substr($createdAt, 0, 19));
            $date = $dt ? $dt->format('Y-m-d') : substr($createdAt, 0, 10);
            $gross = abs($amount);
            $net = round($gross * 0.9, 2);

            $desc = 'Пополнение на ' . (int)$gross . ' ₽';
            if (preg_match('/на\s+(\d+(?:[.,]\d+)?)\s*(?:₽|руб)/iu', $description, $m)) {
                $desc = 'Пополнение на ' . (int)round((float)str_replace(',', '.', $m[1])) . ' ₽';
            }

            // Дедупликация ТОЛЬКО по уникальному record_id: каждый платёж Platega
            // уникален, поэтому два платежа от разных людей с одинаковой датой/суммой
            // никогда не пересекутся. Составной ключ — фолбэк лишь для строк без
            // record_id (битые/нестандартные CSV-строки).
            if ($recordId !== '') {
                $isDup = in_array($recordId, $existingRecordIds, true);
            } else {
                $dupKey = $this->plategaDupKey($date, 'Доход', 'Platega пополнение', $net);
                $isDup = in_array($dupKey, $existingKeys, true);
            }

            $preview[] = [
                'record_id' => $recordId,
                'date' => $date,
                'type' => 'Доход',
                'participant' => 'Platega пополнение',
                'category' => 'Прибыль',
                'amount' => $net,
                'gross' => $gross,
                'description' => $desc,
                'status' => $isDup ? 'duplicate' : 'new',
            ];
        }

        return $preview;
    }

    private function downloadCsv(string $url): string
    {
        return $this->httpGet($url, ['User-Agent: HexaVeil/1.0']);
    }

    private function parsePlategaCsv(string $text): array
    {
        $text = preg_replace('/^\xEF\xBB\xBF/', '', $text);
        $lines = explode("\n", $text);
        $rows = [];
        foreach ($lines as $line) {
            $line = rtrim($line, "\r\n");
            if ($line === '') {
                continue;
            }
            $fields = str_getcsv($line, ';');
            $row = [];
            foreach ($fields as $f) {
                $row[] = $this->toUtf8(trim($f));
            }
            $rows[] = $row;
        }

        if (empty($rows)) {
            return [];
        }

        $header = array_shift($rows);
        $out = [];
        foreach ($rows as $row) {
            $assoc = [];
            foreach ($header as $i => $col) {
                $assoc[$col] = $row[$i] ?? '';
            }
            $out[] = $assoc;
        }
        return $out;
    }

    private function plategaExistingKeys(): array
    {
        $rows = $this->db->fetchAll(
            'SELECT `date`, `type`, COALESCE(`participant`, \'\') AS participant, `amount` FROM fin_transactions WHERE participant = ?',
            ['Platega пополнение']
        );
        $keys = [];
        foreach ($rows as $r) {
            $keys[] = $this->plategaDupKey($r['date'], $r['type'], $r['participant'], $r['amount']);
        }
        return $keys;
    }

    /**
     * Уникальные record_id уже импортированных Platega-платежей.
     * record_id уникален для КАЖДОГО платежа Platega, в отличие от
     * (date, type, participant, amount), где participant всегда
     * 'Platega пополнение' и два платежа от разных людей с одинаковой
     * датой/суммой неразличимы (такие платежи НЕЛЬЗЯ считать дубликатами).
     */
    private function plategaExistingRecordIds(): array
    {
        $rows = $this->db->fetchAll(
            "SELECT `record_id` FROM fin_transactions WHERE participant = ? AND `record_id` IS NOT NULL AND `record_id` != ''",
            ['Platega пополнение']
        );
        $out = [];
        foreach ($rows as $r) {
            $out[] = (string)$r['record_id'];
        }
        return $out;
    }

    /**
     * Канонический ключ дедупликации Platega-транзакции.
     * Нормализует тип (Доход/income → income, Расход/expense → expense)
     * и сумму (900.0 → '900.00'), чтобы ключи из preview, БД и импорта
     * всегда совпадали. Без этого дедупликация не работает: в БД тип
     * хранится латиницей, а сумма — DECIMAL(15,2) с двумя знаками.
     */
    private function plategaDupKey(string $date, string $type, string $participant, $amount): string
    {
        $t = mb_strtolower(trim($type));
        if (in_array($t, ['доход', 'income', 'приход', 'плюс', 'прибыль'], true)) {
            $t = 'income';
        } else {
            $t = 'expense';
        }
        $amt = number_format(round((float)$amount, 2), 2, '.', '');
        return $date . '|' . $t . '|' . trim($participant) . '|' . $amt;
    }

    private function commitPlategaImport(array $previewRows, array $includeIds): array
    {
        $existingKeys = $this->plategaExistingKeys();
        $existingRecordIds = $this->plategaExistingRecordIds();
        $added = 0;
        $skipped = 0;

        $map = [];
        foreach ($previewRows as $t) {
            $map[(string)$t['record_id']] = $t;
        }

        foreach ($includeIds as $rid) {
            $t = $map[$rid] ?? null;
            if (!$t) {
                $skipped++;
                continue;
            }
            if ($t['status'] !== 'new') {
                $skipped++;
                continue;
            }

            $recordId = (string)($t['record_id'] ?? '');
            // Только record_id решает: два разных платежа с одинаковой датой/суммой
            // от разных людей не считаем дубликатами. Составной ключ — фолбэк для
            // строк без record_id.
            if ($recordId !== '') {
                if (in_array($recordId, $existingRecordIds, true)) {
                    $skipped++;
                    continue;
                }
            } else {
                $dupKey = $this->plategaDupKey($t['date'], $t['type'], $t['participant'], $t['amount']);
                if (in_array($dupKey, $existingKeys, true)) {
                    $skipped++;
                    continue;
                }
            }

            try {
                $this->model->create([
                    'date' => $t['date'],
                    'type' => 'income',
                    'category' => $t['category'],
                    'participant' => $t['participant'],
                    'amount' => (float)$t['amount'],
                    'description' => $t['description'],
                    'record_id' => $recordId,
                ]);
                if ($recordId !== '') {
                    $existingRecordIds[] = $recordId;
                } else {
                    $existingKeys[] = $dupKey;
                }
                $added++;
            } catch (\Throwable $e) {
                $skipped++;
            }
        }

        return ['added' => $added, 'skipped' => $skipped];
    }

    private function importCsvRow(?array $row, int &$imported, int &$skipped, array &$errors): int
    {
        if (!$row || count($row) < 5) {
            return 0;
        }
        // Колонки: date; type; category; participant; amount; description
        $date = (string)$row[0];
        $type = $this->csvType((string)($row[1] ?? ''));
        $category = (string)($row[2] ?? '');
        $participant = (string)($row[3] ?? '');
        $amount = (float)str_replace(',', '.', (string)($row[4] ?? '0'));
        $description = (string)($row[5] ?? '');

        if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date) || !strtotime($date)) {
            return 0;
        }
        if ($type === '' || $amount <= 0) {
            $skipped++;
            return 0;
        }
        if ($category === '') {
            $category = 'Другое';
        }

        $clean = $this->cleanTransaction([
            'date' => $date,
            'type' => $type,
            'category' => $category,
            'participant' => $participant,
            'amount' => $amount,
            'description' => $description,
        ]);

        // Дедупликация
        $dup = $this->model->findDuplicate($clean);
        if ($dup) {
            $skipped++;
            return 0;
        }

        try {
            $this->model->create($clean);
            $imported++;
        } catch (\Throwable $e) {
            $errors[] = $date . ': ' . $e->getMessage();
            $skipped++;
        }
        return 0;
    }

    private function csvType(string $v): string
    {
        $t = mb_strtolower(trim($v));
        if (in_array($t, ['доход', 'income', 'приход', 'плюс', 'прибыль'], true)) {
            return 'income';
        }
        if (in_array($t, ['расход', 'expense', 'отток', 'минус'], true)) {
            return 'expense';
        }
        return '';
    }
}
