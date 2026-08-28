<?php
/**
 * FinSetting — настройки финансового модуля (таблица fin_settings)
 * Значения-массивы (JSON) хранятся как JSON-строки, декодирование — на стороне
 * контроллера/фронтенда, чтобы модель оставалась простой.
 */

class FinSetting
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Получить значение настройки
     * @param string $key
     * @param mixed $default
     * @return mixed
     */
    public function get(string $key, $default = null)
    {
        $value = $this->db->fetchOne(
            'SELECT setting_value FROM fin_settings WHERE setting_key = ?',
            [$key]
        );
        return $value === null ? $default : $value;
    }

    /**
     * Сохранить настройку (upsert)
     */
    public function set(string $key, $value): void
    {
        $this->db->query(
            'INSERT INTO fin_settings (setting_key, setting_value) VALUES (?, ?)
             ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)',
            [$key, (string)$value]
        );
    }

    /**
     * Все настройки как массив ключ => значение
     */
    public function getAll(): array
    {
        $rows = $this->db->fetchAll('SELECT setting_key, setting_value FROM fin_settings');
        $out = [];
        foreach ($rows as $row) {
            $out[$row['setting_key']] = $row['setting_value'];
        }
        return $out;
    }
}
