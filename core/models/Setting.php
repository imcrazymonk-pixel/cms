<?php
/**
 * Модель настроек
 */

class Setting
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Получить настройку по ключу
     */
    public function get(string $key): ?string
    {
        $result = $this->db->fetch(
            "SELECT setting_value FROM settings WHERE setting_key = :key",
            ['key' => $key]
        );
        return $result ? $result['setting_value'] : null;
    }

    /**
     * Получить все настройки
     */
    public function getAll(): array
    {
        $settings = $this->db->fetchAll("SELECT * FROM settings");
        $result = [];
        foreach ($settings as $setting) {
            $result[$setting['setting_key']] = $setting['setting_value'];
        }
        return $result;
    }

    /**
     * Сохранить настройку (upsert — INSERT ON CONFLICT DO UPDATE).
     * Избегает проблем с sequence в PostgreSQL.
     */
    public function set(string $key, string $value): bool
    {
        $db = Database::getInstance();
        $driver = DB_DRIVER;

        if ($driver === 'pgsql') {
            // Сброс sequence на max(id)+1, чтобы избежать конфликта первичного ключа
            $db->query("SELECT setval('settings_id_seq', COALESCE((SELECT MAX(id) FROM settings), 0) + 1, false)");
            $db->query(
                'INSERT INTO settings (setting_key, setting_value) VALUES (:key, :value)
                 ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value',
                ['key' => $key, 'value' => $value]
            );
        } else {
            // MySQL fallback
            $db->query(
                'INSERT INTO settings (setting_key, setting_value) VALUES (:key, :value)
                 ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)',
                ['key' => $key, 'value' => $value]
            );
        }
        return true;
    }

    /**
     * Сохранить несколько настроек
     */
    public function setMultiple(array $settings): bool
    {
        foreach ($settings as $key => $value) {
            $this->set($key, $value);
        }
        return true;
    }
}
