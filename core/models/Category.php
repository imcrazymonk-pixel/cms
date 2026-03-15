<?php
/**
 * Модель категорий
 */

class Category
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Получить категорию по slug
     */
    public function getBySlug(string $slug): ?array
    {
        return $this->db->fetch("SELECT * FROM categories WHERE slug = :slug", ['slug' => $slug]) ?: null;
    }

    /**
     * Получить категорию по ID
     */
    public function getById(int $id): ?array
    {
        return $this->db->fetch("SELECT * FROM categories WHERE id = :id", ['id' => $id]) ?: null;
    }

    /**
     * Получить все категории
     */
    public function getAll(): array
    {
        return $this->db->fetchAll("SELECT id, name, slug, description FROM categories ORDER BY name");
    }

    /**
     * Получить посты категории
     */
    public function getPosts(int $categoryId): array
    {
        return $this->db->fetchAll(
            "SELECT * FROM posts WHERE category_id = :category_id AND status = 'published' ORDER BY created_at DESC",
            ['category_id' => $categoryId]
        );
    }

    /**
     * Создать категорию
     */
    public function create(array $data): int
    {
        return $this->db->insert('categories', $data);
    }

    /**
     * Обновить категорию
     */
    public function update(int $id, array $data): bool
    {
        return $this->db->update('categories', $data, 'id = :id', ['id' => $id]) > 0;
    }

    /**
     * Удалить категорию
     */
    public function delete(int $id): bool
    {
        return $this->db->delete('categories', 'id = :id', ['id' => $id]);
    }

    /**
     * Получить количество категорий
     */
    public function getCount(): int
    {
        return (int) $this->db->fetchOne("SELECT COUNT(*) FROM categories");
    }
}
