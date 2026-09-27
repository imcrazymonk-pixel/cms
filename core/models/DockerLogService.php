<?php
/**
 * DockerLogService — получение логов Docker-контейнеров.
 *
 * Работает через SSH-выполнение команды docker logs.
 * Требует настроенного SSH-доступа к серверу с Docker.
 *
 * Конфигурация (в settings.json или .env):
 *   docker_ssh_host    — хост SSH (по умолчанию localhost)
 *   docker_ssh_user    — пользователь SSH
 *   docker_ssh_port    — порт SSH (по умолчанию 22)
 *   docker_containers  — список контейнеров через запятую
 *   docker_lines       — количество строк на контейнер (по умолчанию 100)
 */
class DockerLogService
{
    private $settings;

    /**
     * Категория для Docker-логов в системе.
     */
    public const CATEGORY = 'docker';

    public function __construct()
    {
        $this->settings = $this->loadSettings();
    }

    /**
     * Загрузить настройки из БД (таблица settings).
     */
    private function loadSettings(): array
    {
        $defaults = [
            'docker_ssh_host'   => 'localhost',
            'docker_ssh_user'   => 'kilo',
            'docker_ssh_port'   => 356,
            'docker_containers' => '',
            'docker_lines'      => 100,
        ];
        try {
            $db = Database::getInstance();
            $row = $db->fetchOne("SELECT `value` FROM settings WHERE `key` = 'docker_config'");
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
     * Получить список контейнеров.
     */
    public function getContainers(): array
    {
        $raw = $this->settings['docker_containers'] ?? '';
        if ($raw === '') {
            return [];
        }
        $containers = explode(',', $raw);
        return array_map('trim', $containers);
    }

    /**
     * Проверить, доступен ли Docker (есть ли контейнеры в настройках).
     */
    public function isAvailable(): bool
    {
        return count($this->getContainers()) > 0;
    }

    /**
     * Получить логи указанного контейнера.
     *
     * @param string $container Имя контейнера
     * @param int    $lines     Количество последних строк
     * @param string $since     Смещение (например "10m", "1h")
     * @return array Массив строк лога
     */
    public function getContainerLogs(string $container, int $lines = 100, string $since = '30m'): array
    {
        $host = $this->settings['docker_ssh_host'] ?? 'localhost';
        $user = $this->settings['docker_ssh_user'] ?? 'kilo';
        $port = $this->settings['docker_ssh_port'] ?? 356;

        $cmd = sprintf(
            'docker logs --tail %d --since %s %s 2>&1',
            (int)$lines,
            escapeshellarg($since),
            escapeshellarg($container)
        );

        // Если это локальный хост — выполняем напрямую
        if ($host === 'localhost' || $host === '127.0.0.1') {
            return $this->execLocal($cmd, $container);
        }

        // Иначе через SSH
        return $this->execRemote($host, $user, $port, $cmd, $container);
    }

    /**
     * Получить логи ВСЕХ контейнеров (с объединением).
     *
     * @param int    $lines   Строк на контейнер
     * @param string $since   Временное смещение
     * @param string $level   Фильтр по уровню (error/warning/info)
     * @return array Массив записей, совместимых с app_logs форматом
     */
    public function getAllLogs(int $lines = 100, string $since = '30m', string $level = ''): array
    {
        $containers = $this->getContainers();
        if (empty($containers)) {
            return [];
        }

        $results = [];
        foreach ($containers as $container) {
            $logs = $this->getContainerLogs($container, $lines, $since);
            foreach ($logs as $entry) {
                $entryLevel = $this->detectLevel($entry['message'] ?? '');
                if ($level !== '' && $entryLevel !== $level) {
                    continue;
                }
                $entry['level'] = $entryLevel;
                $results[] = $entry;
            }
        }

        // Сортировка по времени (новые сверху)
        usort($results, function ($a, $b) {
            return strcmp($b['created_at'] ?? '', $a['created_at'] ?? '');
        });

        return $results;
    }

    /**
     * Определить уровень лога по содержимому строки.
     */
    private function detectLevel(string $message): string
    {
        if (preg_match('/\berror\b|\bfatal\b|\bexception\b|\bpanic\b/i', $message)) {
            return 'error';
        }
        if (preg_match('/\bwarn\b|\bwarning\b/i', $message)) {
            return 'warning';
        }
        return 'info';
    }

    /**
     * Выполнить команду локально.
     */
    private function execLocal(string $cmd, string $container): array
    {
        $output = [];
        $exitCode = 0;
        exec($cmd . ' 2>&1', $output, $exitCode);

        return $this->parseOutput($output, $container);
    }

    /**
     * Выполнить команду через SSH.
     */
    private function execRemote(string $host, string $user, int $port, string $cmd, string $container): array
    {
        $sshCmd = sprintf(
            'ssh -p %d -o StrictHostKeyChecking=no -o ConnectTimeout=5 %s@%s %s 2>&1',
            $port,
            escapeshellarg($user),
            escapeshellarg($host),
            escapeshellarg($cmd)
        );

        $output = [];
        exec($sshCmd, $output);

        return $this->parseOutput($output, $container);
    }

    /**
     * Парсинг сырого вывода docker logs в структурированный формат.
     */
    private function parseOutput(array $lines, string $container): array
    {
        $entries = [];
        foreach ($lines as $line) {
            $timestamp = date('Y-m-d H:i:s');
            // Docker log format: "2024-01-01T12:00:00.000000000Z message..."
            if (preg_match('/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})/', $line, $m)) {
                $timestamp = date('Y-m-d H:i:s', strtotime($m[1]));
                $line = substr($line, strlen($m[0]));
            }

            $entries[] = [
                'created_at' => $timestamp,
                'level'      => $this->detectLevel($line),
                'category'   => 'docker',
                'channel'    => 'docker',
                'source'     => $container,
                'message'    => trim($line),
                'context'    => null,
            ];
        }
        return $entries;
    }
}