<?php
/**
 * Модель комментариев
 */

class Comment
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Получить комментарий по ID
     */
    public function getById(int $id): ?array
    {
        return $this->db->fetch("SELECT * FROM comments WHERE id = :id", ['id' => $id]) ?: null;
    }

    /**
     * Получить комментарии к посту
     */
    public function getByPostId(int $postId, string $status = 'approved'): array
    {
        return $this->db->fetchAll(
            "SELECT * FROM comments WHERE post_id = :post_id AND status = :status ORDER BY created_at DESC",
            ['post_id' => $postId, 'status' => $status]
        );
    }

    /**
     * Получить все комментарии
     */
    public function getAll(): array
    {
        return $this->db->fetchAll("
            SELECT c.*, p.title as post_title, u.login as author_login
            FROM comments c
            LEFT JOIN posts p ON c.post_id = p.id
            LEFT JOIN users u ON c.user_id = u.id
            ORDER BY c.created_at DESC
        ");
    }

    /**
     * Создать комментарий
     */
    public function create(array $data): int
    {
        return $this->db->insert('comments', $data);
    }

    /**
     * Обновить комментарий
     */
    public function update(int $id, array $data): bool
    {
        return $this->db->update('comments', $data, 'id = :id', ['id' => $id]) > 0;
    }

    /**
     * Удалить комментарий
     */
    public function delete(int $id): bool
    {
        return $this->db->delete('comments', 'id = :id', ['id' => $id]);
    }

    /**
     * Получить количество комментариев со статусом
     */
    public function getCountByStatus(string $status = 'pending'): int
    {
        return (int) $this->db->fetchOne(
            "SELECT COUNT(*) FROM comments WHERE status = :status",
            ['status' => $status]
        );
    }
}
