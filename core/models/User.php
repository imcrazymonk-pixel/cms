<?php
/**
 * Модель пользователей
 */

class User
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /**
     * Найти пользователя по логину/email
     */
    public function findByLogin(string $login): ?array
    {
        return $this->db->fetch(
            "SELECT * FROM users WHERE login = :login OR email = :login",
            ['login' => $login]
        ) ?: null;
    }

    /**
     * Получить пользователя по ID
     */
    public function getById(int $id): ?array
    {
        return $this->db->fetch("SELECT * FROM users WHERE id = :id", ['id' => $id]) ?: null;
    }

    /**
     * Получить всех пользователей
     */
    public function getAll(): array
    {
        return $this->db->fetchAll("SELECT id, login, email, role, created_at FROM users ORDER BY id");
    }

    /**
     * Создать пользователя
     */
    public function create(array $data): int
    {
        return $this->db->insert('users', $data);
    }

    /**
     * Обновить пользователя
     */
    public function update(int $id, array $data): bool
    {
        return $this->db->update('users', $data, 'id = :id', ['id' => $id]) > 0;
    }

    /**
     * Удалить пользователя
     */
    public function delete(int $id): bool
    {
        return $this->db->delete('users', 'id = :id', ['id' => $id]);
    }

    /**
     * Получить количество пользователей
     */
    public function getCount(): int
    {
        return (int) $this->db->fetchOne("SELECT COUNT(*) FROM users");
    }
}
