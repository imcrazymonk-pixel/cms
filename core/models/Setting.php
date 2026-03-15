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
     * Обновить настройку
     */
    public function set(string $key, string $value): bool
    {
        return $this->db->update('settings', ['setting_value' => $value], 'setting_key = :key', ['key' => $key]) > 0;
    }

    /**
     * Обновить несколько настроек
     */
    public function setMultiple(array $settings): bool
    {
        foreach ($settings as $key => $value) {
            $this->set($key, $value);
        }
        return true;
    }
}
