<?php
/**
 * LokiLogService — получение логов из Grafana Loki через HTTP API.
 *
 * Требует настроенного URL к Loki и базовой аутентификации (если нужна).
 *
 * Конфигурация (в settings.json или .env):
 *   loki_url      — полный URL к Loki API (например http://loki:3100)
 *   loki_user     — пользователь Basic Auth (если нужен)
 *   loki_password — пароль Basic Auth (если нужен)
 *   loki_query    — LogQL-запрос по умолчанию (например '{job="varlog"}')
 *   loki_limit    — лимит записей (по умолчанию 100)
 */
class LokiLogService
{
    private $settings;

    /**
     * Категория для Loki-логов.
     */
    public const CATEGORY = 'loki';

    /** Loki API endpoint для query range */
    private const LOKI_QUERY_RANGE = '/loki/api/v1/query_range';

    public function __construct()
    {
        $this->settings = $this->loadSettings();
    }

    /**
     * Загрузить настройки.
     */
    private function loadSettings(): array
    {
        $defaults = [
            'loki_url'      => '',
            'loki_user'     => '',
            'loki_password' => '',
            'loki_query'    => '{job="varlog"}',
            'loki_limit'    => 100,
        ];
        try {
            $db = Database::getInstance();
            $row = $db->fetchOne("SELECT `value` FROM settings WHERE `key` = 'loki_config'");
            if ($row) {
                $cfg = json_decode($row, true);
                if (is_array($cfg)) {
                    return array_merge($defaults, $cfg);
                }
            }
        } catch (\Throwable $e) {
            // используем defaults
        }
        return $defaults;
    }

    /**
     * Проверить доступность Loki (настроен ли URL).
     */
    public function isAvailable(): bool
    {
        $url = $this->settings['loki_url'] ?? '';
        return $url !== '' && filter_var($url, FILTER_VALIDATE_URL) !== false;
    }

    /**
     * Получить логи из Loki.
     *
     * @param string $query    LogQL-запрос (переопределяет умолчание)
     * @param int    $limit    Количество записей
     * @param int    $sinceSec За сколько секунд назад
     * @param string $level    Фильтр уровня (error/warning/info)
     * @return array Массив записей, совместимых с app_logs форматом
     */
    public function queryLogs(string $query = '', int $limit = 100, int $sinceSec = 1800, string $level = ''): array
    {
        if (!$this->isAvailable()) {
            return [];
        }

        $baseUrl = rtrim($this->settings['loki_url'], '/');
        $query = $query ?: ($this->settings['loki_query'] ?? '{job="varlog"}');

        $params = [
            'query' => $query,
            'limit' => $limit,
            'start' => (time() - $sinceSec) * 1_000_000_000,
            'end'   => time() * 1_000_000_000,
            'direction' => 'BACKWARD',
        ];

        $url = $baseUrl . self::LOKI_QUERY_RANGE . '?' . http_build_query($params);

        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 15,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        ]);

        $user = $this->settings['loki_user'] ?? '';
        $pass = $this->settings['loki_password'] ?? '';
        if ($user !== '' || $pass !== '') {
            curl_setopt($ch, CURLOPT_HTTPAUTH, CURLAUTH_BASIC);
            curl_setopt($ch, CURLOPT_USERPWD, $user . ':' . $pass);
        }

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode !== 200 || $response === false) {
            return [];
        }

        $data = json_decode($response, true);
        if (!isset($data['data']['result'])) {
            return [];
        }

        return $this->parseResult($data['data']['result'], $level);
    }

    /**
     * Парсинг результата Loki query_range в плоский массив.
     */
    private function parseResult(array $result, string $levelFilter = ''): array
    {
        $entries = [];
        foreach ($result as $stream) {
            $labels = $stream['stream'] ?? [];
            $source = implode('/', array_map(function ($k, $v) {
                return $k . '=' . $v;
            }, array_keys($labels), $labels));

            $values = $stream['values'] ?? [];
            foreach ($values as $val) {
                $ts = (int)($val[0] / 1_000_000_000);
                $message = $val[1] ?? '';
                $entryLevel = $this->detectLevel($message);
                if ($levelFilter !== '' && $entryLevel !== $levelFilter) {
                    continue;
                }
                $entries[] = [
                    'created_at' => date('Y-m-d H:i:s', $ts),
                    'level'      => $entryLevel,
                    'category'   => 'loki',
                    'channel'    => 'loki',
                    'source'     => mb_substr($source, 0, 50),
                    'message'    => $message,
                    'context'    => json_encode($labels, JSON_UNESCAPED_UNICODE),
                ];
            }
        }

        // Сортировка по времени (новые сверху)
        usort($entries, function ($a, $b) {
            return strcmp($b['created_at'] ?? '', $a['created_at'] ?? '');
        });

        return $entries;
    }

    /**
     * Определить уровень лога.
     */
    private function detectLevel(string $message): string
    {
        if (preg_match('/\berror\b|\bfatal\b|\bexception\b|\bpanic\b|\bcritical\b/i', $message)) {
            return 'error';
        }
        if (preg_match('/\bwarn\b|\bwarning\b/i', $message)) {
            return 'warning';
        }
        return 'info';
    }

    /**
     * Получить доступные метки (labels) из Loki.
     */
    public function getLabels(): array
    {
        if (!$this->isAvailable()) {
            return [];
        }
        $baseUrl = rtrim($this->settings['loki_url'], '/');
        $url = $baseUrl . '/loki/api/v1/labels';

        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 10,
        ]);

        $user = $this->settings['loki_user'] ?? '';
        $pass = $this->settings['loki_password'] ?? '';
        if ($user !== '' || $pass !== '') {
            curl_setopt($ch, CURLOPT_HTTPAUTH, CURLAUTH_BASIC);
            curl_setopt($ch, CURLOPT_USERPWD, $user . ':' . $pass);
        }

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode !== 200 || $response === false) {
            return [];
        }
        $data = json_decode($response, true);
        return $data['data'] ?? [];
    }
}