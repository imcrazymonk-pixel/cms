<?php
/**
 * Модель пользовательских настроек панели (тема, режим и т.д.)
 */
class UserPreference
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    public function get(int $userId, string $key): ?string
    {
        $row = $this->db->fetch("SELECT pref_value FROM user_preferences WHERE user_id = ? AND pref_key = ?", [$userId, $key]);
        return $row['pref_value'] ?? null;
    }

    public function getAll(int $userId): array
    {
        $rows = $this->db->fetchAll("SELECT pref_key, pref_value FROM user_preferences WHERE user_id = ?", [$userId]);
        $result = [];
        foreach ($rows as $r) { $result[$r['pref_key']] = $r['pref_value']; }
        return $result;
    }

    public function set(int $userId, string $key, string $value): void
    {
        $this->db->query(
            "INSERT INTO user_preferences (user_id, pref_key, pref_value) VALUES (?, ?, ?)
             ON DUPLICATE KEY UPDATE pref_value = VALUES(pref_value)",
            [$userId, $key, $value]
        );
    }
}
