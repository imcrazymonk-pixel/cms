<?php
/**
 * Класс для работы с базой данных (PDO wrapper)
 * Все запросы используют подготовленные выражения
 */

class Database
{
    private static ?Database $instance = null;
    private PDO $pdo;

    /**
     * Конструктор (Singleton)
     */
    private function __construct()
    {
        $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET;
        
        $options = [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ];

        try {
            $this->pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
        } catch (PDOException $e) {
            if (DEBUG) {
                die('Ошибка подключения к БД: ' . $e->getMessage());
            }
            die('Ошибка подключения к базе данных');
        }
    }

    /**
     * Получить экземпляр класса
     */
    public static function getInstance(): Database
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    /**
     * Выполнить SQL запрос с подготовленными выражениями
     * @param string $sql SQL запрос
     * @param array $params Параметры для подстановки
     * @return PDOStatement
     */
    public function query(string $sql, array $params = []): PDOStatement
    {
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);
        return $stmt;
    }

    /**
     * Получить одну строку результата
     * @param string $sql SQL запрос
     * @param array $params Параметры
     * @return array|null
     */
    public function fetch(string $sql, array $params = []): ?array
    {
        $result = $this->query($sql, $params);
        $row = $result->fetch();
        return $row ?: null;
    }

    /**
     * Получить все строки результата
     * @param string $sql SQL запрос
     * @param array $params Параметры
     * @return array
     */
    public function fetchAll(string $sql, array $params = []): array
    {
        $result = $this->query($sql, $params);
        return $result->fetchAll();
    }

    /**
     * Получить одно значение
     * @param string $sql SQL запрос
     * @param array $params Параметры
     * @return mixed
     */
    public function fetchOne(string $sql, array $params = [])
    {
        $result = $this->query($sql, $params);
        $row = $result->fetch(PDO::FETCH_NUM);
        return $row ? $row[0] : null;
    }

    /**
     * Вставить запись в таблицу
     * @param string $table Имя таблицы
     * @param array $data Ассоциативный массив данных
     * @return int ID вставленной записи
     */
    public function insert(string $table, array $data): int
    {
        $columns = implode(', ', array_keys($data));
        $placeholders = ':' . implode(', :', array_keys($data));
        
        $sql = "INSERT INTO {$table} ({$columns}) VALUES ({$placeholders})";
        
        $this->query($sql, $data);
        
        return (int) $this->pdo->lastInsertId();
    }

    /**
     * Обновить записи в таблице
     * @param string $table Имя таблицы
     * @param array $data Данные для обновления
     * @param string $where WHERE условие (например, "id = :id")
     * @param array $whereParams Параметры WHERE условия
     * @return int Количество затронутых строк
     */
    public function update(string $table, array $data, string $where, array $whereParams = []): int
    {
        $setParts = [];
        foreach (array_keys($data) as $column) {
            $setParts[] = "{$column} = :{$column}";
        }
        $set = implode(', ', $setParts);
        
        $sql = "UPDATE {$table} SET {$set} WHERE {$where}";
        
        $params = array_merge($data, $whereParams);
        $stmt = $this->query($sql, $params);
        
        return $stmt->rowCount();
    }

    /**
     * Удалить записи из таблицы
     * @param string $table Имя таблицы
     * @param string $where WHERE условие
     * @param array $params Параметры
     * @return int Количество удаленных строк
     */
    public function delete(string $table, string $where, array $params = []): int
    {
        $sql = "DELETE FROM {$table} WHERE {$where}";
        $stmt = $this->query($sql, $params);
        return $stmt->rowCount();
    }

    /**
     * Начать транзакцию
     */
    public function beginTransaction(): bool
    {
        return $this->pdo->beginTransaction();
    }

    /**
     * Зафиксировать транзакцию
     */
    public function commit(): bool
    {
        return $this->pdo->commit();
    }

    /**
     * Откатить транзакцию
     */
    public function rollback(): bool
    {
        return $this->pdo->rollBack();
    }
}
