<?php
/**
 * Временный CLI-скрипт: перенос данных финансового модуля из SQLite (Fin) в MySQL (CMS).
 *
 * Запуск (из корня CMS):  php db/migrate_sqlite_to_mysql.php
 *
 * Требования:
 *  - расширение PDO sqlite (pdo_sqlite) и pdo_mysql
 *  - путь к SQLite-базе FIN: аргумент CLI либо константа FIN_SQLITE_PATH ниже
 */

error_reporting(E_ALL);
ini_set('display_errors', '1');

// Путь к источнику: SQLite-база FIN ИЛИ JSON-экспорт (если pdo_sqlite недоступен).
// JSON-экспорт можно получить: python db/export_sqlite.py
// Флаг --reset очищает fin_transactions перед переносом (для повторного запуска).
$args = array_slice($argv, 1);
$reset = in_array('--reset', $args, true);
$args = array_values(array_filter($args, function ($a) { return $a !== '--reset'; }));
$sourcePath = $args[0] ?? __DIR__ . '/backups/fin-source/finance.db';

if (!file_exists($sourcePath)) {
    fwrite(STDERR, "Источник не найден: {$sourcePath}\n");
    exit(1);
}

$isJson = strtolower(pathinfo($sourcePath, PATHINFO_EXTENSION)) === 'json';

// Подключаем конфиг CMS (определяет DB_HOST/DB_NAME/DB_USER/DB_PASS/DB_CHARSET)
$root = dirname(__DIR__);
$configFile = $root . '/config/config.php';
if (!file_exists($configFile)) {
    fwrite(STDERR, "Нет config/config.php — запустите установку CMS.\n");
    exit(1);
}
require_once $configFile;
if (!defined('DB_HOST') || !defined('DB_NAME') || !defined('DB_USER')) {
    fwrite(STDERR, "Не определены константы БД в config.php\n");
    exit(1);
}

echo "Источник: {$sourcePath} (" . ($isJson ? 'JSON' : 'SQLite') . ")\n";
echo "MySQL: " . DB_HOST . '/' . DB_NAME . "\n\n";

// 1. Читаем из источника
if ($isJson) {
    $json = file_get_contents($sourcePath);
    $rows = json_decode($json ?: '', true);
    if (!is_array($rows)) {
        fwrite(STDERR, "Некорректный JSON в источнике.\n");
        exit(1);
    }
} else {
    if (!extension_loaded('pdo_sqlite')) {
        fwrite(STDERR, "Нет pdo_sqlite. Сначала выполните: python db/export_sqlite.py, затем запустите скрипт с JSON: php db/migrate_sqlite_to_mysql.php db/sqlite_export.json\n");
        exit(1);
    }
    try {
        $lite = new PDO('sqlite:' . $sourcePath);
        $lite->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $lite->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        fwrite(STDERR, "SQLite: " . $e->getMessage() . "\n");
        exit(1);
    }

    $hasTable = $lite->query("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")->fetch();
    if (!$hasTable) {
        fwrite(STDERR, "В SQLite-базе нет таблицы transactions — нечего переносить.\n");
        exit(1);
    }
    $rows = $lite->query("SELECT id, date, type, participant, category, amount, description FROM transactions ORDER BY date ASC, id ASC")->fetchAll();
}

echo 'Найдено записей в источнике: ' . count($rows) . "\n";

// 2. Подключаемся к MySQL и создаём таблицы
$dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET;
try {
    $mysql = new PDO($dsn, DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (PDOException $e) {
    fwrite(STDERR, "MySQL: " . $e->getMessage() . "\n");
    exit(1);
}

// Применяем миграцию (CREATE TABLE + настройки по умолчанию)
$migration = file_get_contents(__DIR__ . '/migrations/2026-08-27-finance.sql');
if ($migration !== false) {
    $mysql->exec($migration);
    echo "Таблицы fin_* созданы (миграция применена).\n";
}

if ($reset) {
    $mysql->exec('TRUNCATE TABLE fin_transactions');
    echo "fin_transactions очищена (--reset).\n";
}

// 3. Перенос данных (маппинг полей + конвертация типов)
$mapType = function (string $type): string {
    $t = mb_strtolower(trim($type));
    if (in_array($t, ['доход', 'income', 'приход', 'плюс'], true)) return 'income';
    if (in_array($t, ['расход', 'expense', 'отток', 'минус'], true)) return 'expense';
    return 'expense';
};

$insert = $mysql->prepare(
    "INSERT INTO fin_transactions (`date`, `type`, `category`, `participant`, `amount`, `description`, `created_at`)
     VALUES (:date, :type, :category, :participant, :amount, :description, :created_at)"
);
$insertNoCreated = $mysql->prepare(
    "INSERT INTO fin_transactions (`date`, `type`, `category`, `participant`, `amount`, `description`)
     VALUES (:date, :type, :category, :participant, :amount, :description)"
);

$imported = 0;
$skipped = 0;

foreach ($rows as $row) {
    $date = (string)($row['date'] ?? '');
    $type = $mapType((string)($row['type'] ?? ''));
    $category = trim((string)($row['category'] ?? ''));
    $participant = trim((string)($row['participant'] ?? ''));
    $amount = (float)($row['amount'] ?? 0);
    $description = (string)($row['description'] ?? '');
    $createdAt = null;
    if (isset($row['created_at']) && $row['created_at'] !== null && $row['created_at'] !== '') {
        $createdAt = date('Y-m-d H:i:s', strtotime((string)$row['created_at']));
    }

    // Проверка формата даты
    if (!$date || !preg_match('/^\d{4}-\d{2}-\d{2}$/', $date)) {
        $skipped++;
        continue;
    }
    if ($category === '') {
        $category = 'Другое';
    }

    // Примечание: дедупликацию НЕ применяем — в исходной базе есть корректные
    // операции с одинаковыми (date, type, participant, amount), но разными
    // описаниями. Переносим все строки без потерь.

    if ($createdAt !== null) {
        $insert->execute([
            'date' => $date,
            'type' => $type,
            'category' => $category,
            'participant' => $participant !== '' ? $participant : null,
            'amount' => $amount,
            'description' => $description,
            'created_at' => $createdAt,
        ]);
    } else {
        $insertNoCreated->execute([
            'date' => $date,
            'type' => $type,
            'category' => $category,
            'participant' => $participant !== '' ? $participant : null,
            'amount' => $amount,
            'description' => $description,
        ]);
    }
    $imported++;

    if ($imported % 500 === 0) {
        echo "  ... импортировано {$imported}, пропущено {$skipped}\n";
    }
}

echo "\nГотово: импортировано {$imported}, пропущено дубликатов/битых: {$skipped}\n";
echo "Проверка: SELECT COUNT(*) FROM fin_transactions;\n";
