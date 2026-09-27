<?php
/**
 * AppLog — централизованное логирование (таблица app_logs).
 * Таблица включает поля: level, category, channel, source, message, context.
 * Категории: system, site, modules, infrastructure, finance, users
 * Уровни: info, warning, error, debug
 */
class AppLog
{
    private $db;

    /**
     * Предопределённые категории с их метками.
     */
    public const CATEGORIES = [
        'system'         => 'Система',
        'site'           => 'Сайт',
        'modules'        => 'Модули',
        'infrastructure' => 'Инфраструктура',
        'finance'        => 'Финансы',
        'users'          => 'Пользователи',
    ];

    /**
     * Предопределённые уровни с метками.
     */
    public const LEVELS = [
        'info'    => 'Info',
        'warning' => 'Warning',
        'error'   => 'Error',
        'debug'   => 'Debug',
    ];

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Добавить запись в лог.
     */
    public static function add(
        string $level,
        string $channel,
        string $message,
        array $context = [],
        string $category = 'system',
        ?string $source = null
    ): void {
        try {
            $db = Database::getInstance();
            $db->query(
                'INSERT INTO app_logs (level, category, channel, source, message, context) VALUES (?, ?, ?, ?, ?, ?)',
                [
                    $level,
                    $category,
                    $channel,
                    $source,
                    $message,
                    $context ? json_encode($context, JSON_UNESCAPED_UNICODE) : null,
                ]
            );
        } catch (\Throwable $e) {
            // Не падаем, если логирование не удалось
        }
    }

    /**
     * Получить записи с фильтрацией.
     */
    public function getAll(array $filters = [], int $page = 1, int $perPage = 50): array
    {
        $where = [];
        $params = [];

        if (!empty($filters['level'])) {
            $where[] = 'level = ?';
            $params[] = $filters['level'];
        }
        if (!empty($filters['category'])) {
            $where[] = 'category = ?';
            $params[] = $filters['category'];
        }
        if (!empty($filters['channel'])) {
            $where[] = 'channel = ?';
            $params[] = $filters['channel'];
        }
        if (!empty($filters['source'])) {
            $where[] = 'source = ?';
            $params[] = $filters['source'];
        }
        if (!empty($filters['q'])) {
            $where[] = 'message LIKE ?';
            $params[] = '%' . $filters['q'] . '%';
        }

        $whereSql = $where ? ' WHERE ' . implode(' AND ', $where) : '';
        $total = (int)$this->db->fetchOne('SELECT COUNT(*) FROM app_logs' . $whereSql, $params);

        $offset = max(0, ($page - 1) * $perPage);
        $rows = $this->db->fetchAll(
            'SELECT * FROM app_logs' . $whereSql . ' ORDER BY id DESC LIMIT ' . (int)$perPage . ' OFFSET ' . (int)$offset,
            $params
        );

        return ['rows' => $rows, 'total' => $total];
    }

    /**
     * Очистить все логи.
     */
    public function clear(): int
    {
        return (int)$this->db->query('DELETE FROM app_logs')->rowCount();
    }

    /**
     * Очистить логи по категории.
     */
    public function clearByCategory(string $category): int
    {
        return (int)$this->db->query('DELETE FROM app_logs WHERE category = ?', [$category])->rowCount();
    }

    /**
     * Очистить логи по каналу.
     */
    public function clearByChannel(string $channel): int
    {
        return (int)$this->db->query('DELETE FROM app_logs WHERE channel = ?', [$channel])->rowCount();
    }

    /**
     * Получить уникальные категории из БД.
     */
    public function getCategories(): array
    {
        $rows = $this->db->fetchAll('SELECT DISTINCT category FROM app_logs ORDER BY category');
        $cats = [];
        foreach ($rows as $r) {
            $cats[] = $r['category'];
        }
        return $cats;
    }

    /**
     * Получить уникальные каналы из БД.
     */
    public function getChannels(): array
    {
        $rows = $this->db->fetchAll('SELECT DISTINCT channel FROM app_logs ORDER BY channel');
        $channels = [];
        foreach ($rows as $r) {
            $channels[] = $r['channel'];
        }
        return $channels;
    }

    /**
     * Получить уникальные уровни из БД.
     */
    public function getLevels(): array
    {
        $rows = $this->db->fetchAll('SELECT DISTINCT level FROM app_logs ORDER BY level');
        $levels = [];
        foreach ($rows as $r) {
            $levels[] = $r['level'];
        }
        return $levels;
    }

    /**
     * Получить уникальные источники из БД.
     */
    public function getSources(): array
    {
        $rows = $this->db->fetchAll('SELECT DISTINCT source FROM app_logs WHERE source IS NOT NULL ORDER BY source');
        $sources = [];
        foreach ($rows as $r) {
            $sources[] = $r['source'];
        }
        return $sources;
    }
}