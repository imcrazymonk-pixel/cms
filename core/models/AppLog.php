<?php
/**
 * AppLog — централизованное логирование (таблица app_logs).
 * Пишет события из модуля финансов (Platega, настройки) и других частей системы.
 */

class AppLog
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    public static function add(string $level, string $channel, string $message, array $context = []): void
    {
        try {
            $db = Database::getInstance();
            $db->query(
                'INSERT INTO app_logs (`level`, `channel`, `message`, `context`) VALUES (?, ?, ?, ?)',
                [
                    $level,
                    $channel,
                    $message,
                    $context ? json_encode($context, JSON_UNESCAPED_UNICODE) : null,
                ]
            );
        } catch (\Throwable $e) {
            // Не падаем, если логирование не удалось
        }
    }

    public function getAll(array $filters = [], int $page = 1, int $perPage = 50): array
    {
        $where = [];
        $params = [];

        if (!empty($filters['level'])) {
            $where[] = 'level = ?';
            $params[] = $filters['level'];
        }
        if (!empty($filters['channel'])) {
            $where[] = 'channel = ?';
            $params[] = $filters['channel'];
        }
        if (!empty($filters['q'])) {
            $where[] = 'message LIKE ?';
            $params[] = '%' . $filters['q'] . '%';
        }

        $whereSql = $where ? ' WHERE ' . implode(' AND ', $where) : '';
        $total = (int)$this->db->fetchOne('SELECT COUNT(*) FROM app_logs' . $whereSql, $params);

        $offset = max(0, ($page - 1) * $perPage);
        $rows = $this->db->fetchAll(
            'SELECT * FROM app_logs' . $whereSql . ' ORDER BY id DESC LIMIT ' . (int)$offset . ', ' . (int)$perPage,
            $params
        );

        return ['rows' => $rows, 'total' => $total];
    }

    public function clear(): int
    {
        return (int)$this->db->query('DELETE FROM app_logs')->rowCount();
    }
}
