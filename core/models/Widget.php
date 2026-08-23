<?php
/**
 * Модель виджетов
 */

class Widget
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Все виджеты области
     */
    public function getAllByArea(string $area): array
    {
        return $this->db->fetchAll(
            "SELECT * FROM widgets WHERE area = :area ORDER BY sort_order ASC, id ASC",
            ['area' => $area]
        );
    }

    /**
     * Все виджеты (для админки)
     */
    public function getAll(): array
    {
        return $this->db->fetchAll("SELECT * FROM widgets ORDER BY area ASC, sort_order ASC, id ASC");
    }

    /**
     * Виджет по ID
     */
    public function getById(int $id): ?array
    {
        return $this->db->fetch("SELECT * FROM widgets WHERE id = :id", ['id' => $id]) ?: null;
    }

    /**
     * Создать виджет
     */
    public function create(array $data): int
    {
        return $this->db->insert('widgets', $data);
    }

    /**
     * Обновить виджет
     */
    public function update(int $id, array $data): bool
    {
        return $this->db->update('widgets', $data, 'id = :id', ['id' => $id]) > 0;
    }

    /**
     * Удалить виджет
     */
    public function delete(int $id): bool
    {
        return $this->db->delete('widgets', 'id = :id', ['id' => $id]);
    }
}
