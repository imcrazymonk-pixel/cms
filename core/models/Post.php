<?php
/**
 * Модель постов
 */

class Post
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Получить все опубликованные посты
     */
    public function getPublishedPosts(int $limit = 10): array
    {
        return $this->db->fetchAll("
            SELECT p.*, c.name as category_name, u.login as author
            FROM posts p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.status = 'published'
            ORDER BY p.created_at DESC
            LIMIT :limit
        ", ['limit' => $limit]);
    }

    /**
     * Получить пост по slug
     */
    public function getBySlug(string $slug): ?array
    {
        return $this->db->fetch("
            SELECT p.*, c.name as category_name, c.slug as category_slug, u.login as author
            FROM posts p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.slug = :slug
        ", ['slug' => $slug]) ?: null;
    }

    /**
     * Получить пост по ID
     */
    public function getById(int $id): ?array
    {
        return $this->db->fetch("SELECT * FROM posts WHERE id = :id", ['id' => $id]) ?: null;
    }

    /**
     * Увеличить счётчик просмотров
     */
    public function incrementViews(int $id): void
    {
        $post = $this->getById($id);
        if ($post) {
            $this->db->update('posts', ['views' => $post['views'] + 1], 'id = :id', ['id' => $id]);
        }
    }

    /**
     * Получить комментарии к посту
     */
    public function getComments(int $postId): array
    {
        return $this->db->fetchAll(
            "SELECT * FROM comments WHERE post_id = :post_id AND status = 'approved' ORDER BY created_at DESC",
            ['post_id' => $postId]
        );
    }

    /**
     * Получить теги поста
     */
    public function getTags(int $postId): array
    {
        return $this->db->fetchAll("
            SELECT t.* FROM tags t
            INNER JOIN post_tags pt ON t.id = pt.tag_id
            WHERE pt.post_id = :post_id
        ", ['post_id' => $postId]);
    }

    /**
     * Получить связанные посты
     */
    public function getRelated(int $categoryId, int $currentId, int $limit = 3): array
    {
        if (!$categoryId) {
            return [];
        }

        return $this->db->fetchAll(
            "SELECT id, title, slug, image FROM posts 
             WHERE category_id = :category_id AND id != :id AND status = 'published' 
             ORDER BY created_at DESC LIMIT :limit",
            ['category_id' => $categoryId, 'id' => $currentId, 'limit' => $limit]
        );
    }

    /**
     * Получить все посты (для админки)
     */
    public function getAll(): array
    {
        return $this->db->fetchAll("
            SELECT p.*, c.name as category_name, u.login as author_name
            FROM posts p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN users u ON p.user_id = u.id
            ORDER BY p.created_at DESC
        ");
    }

    /**
     * Создать пост
     */
    public function create(array $data): int
    {
        return $this->db->insert('posts', $data);
    }

    /**
     * Обновить пост
     */
    public function update(int $id, array $data): bool
    {
        return $this->db->update('posts', $data, 'id = :id', ['id' => $id]) > 0;
    }

    /**
     * Удалить пост
     */
    public function delete(int $id): bool
    {
        return $this->db->delete('posts', 'id = :id', ['id' => $id]);
    }

    /**
     * Получить количество постов
     */
    public function getCount(): int
    {
        return (int) $this->db->fetchOne("SELECT COUNT(*) FROM posts");
    }

    /**
     * Получить последние посты
     */
    public function getRecent(int $limit = 5): array
    {
        return $this->db->fetchAll(
            "SELECT id, title, slug, status, created_at FROM posts ORDER BY created_at DESC LIMIT :limit",
            ['limit' => $limit]
        );
    }
}
