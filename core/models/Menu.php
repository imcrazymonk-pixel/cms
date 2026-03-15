<?php
/**
 * Модель меню
 */

class Menu
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Получить пункты меню по расположению
     */
    public function getByLocation(string $location): array
    {
        return $this->db->fetchAll(
            "SELECT id, name, url, location FROM menus WHERE location = :location ORDER BY id",
            ['location' => $location]
        );
    }

    /**
     * Получить пункт меню по ID
     */
    public function getById(int $id): ?array
    {
        return $this->db->fetch("SELECT * FROM menus WHERE id = :id", ['id' => $id]) ?: null;
    }

    /**
     * Получить все пункты меню
     */
    public function getAll(): array
    {
        return $this->db->fetchAll("SELECT * FROM menus ORDER BY id");
    }

    /**
     * Создать пункт меню
     */
    public function create(array $data): int
    {
        return $this->db->insert('menus', $data);
    }

    /**
     * Обновить пункт меню
     */
    public function update(int $id, array $data): bool
    {
        return $this->db->update('menus', $data, 'id = :id', ['id' => $id]) > 0;
    }

    /**
     * Удалить пункт меню
     */
    public function delete(int $id): bool
    {
        return $this->db->delete('menus', 'id = :id', ['id' => $id]);
    }
}
