<?php
/**
 * Модель страниц
 */

class Page
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Получить страницу по slug
     */
    public function getBySlug(string $slug): ?array
    {
        return $this->db->fetch("SELECT * FROM pages WHERE slug = :slug", ['slug' => $slug]) ?: null;
    }

    /**
     * Получить страницу по ID
     */
    public function getById(int $id): ?array
    {
        return $this->db->fetch("SELECT * FROM pages WHERE id = :id", ['id' => $id]) ?: null;
    }

    /**
     * Получить главную страницу
     */
    public function getHomePage(): ?array
    {
        return $this->db->fetch("SELECT * FROM pages WHERE is_home = 1 LIMIT 1") ?: null;
    }

    /**
     * Получить все страницы
     */
    public function getAll(): array
    {
        return $this->db->fetchAll("
            SELECT p.*, u.login as author_name
            FROM pages p
            LEFT JOIN users u ON p.user_id = u.id
            ORDER BY p.title
        ");
    }

    /**
     * Установить страницу главной
     */
    public function setAsHome(int $id): bool
    {
        // Сбросить все главные страницы
        $this->db->query("UPDATE pages SET is_home = 0");
        // Установить новую главную
        return $this->db->update('pages', ['is_home' => 1], 'id = :id', ['id' => $id]) > 0;
    }

    /**
     * Создать страницу
     */
    public function create(array $data): int
    {
        return $this->db->insert('pages', $data);
    }

    /**
     * Обновить страницу
     */
    public function update(int $id, array $data): bool
    {
        return $this->db->update('pages', $data, 'id = :id', ['id' => $id]) > 0;
    }

    /**
     * Удалить страницу
     */
    public function delete(int $id): bool
    {
        return $this->db->delete('pages', 'id = :id', ['id' => $id]);
    }

    /**
     * Проверить, является ли страница главной
     */
    public function isHomePage(int $id): bool
    {
        $page = $this->getById($id);
        return $page && $page['is_home'] == 1;
    }
}
