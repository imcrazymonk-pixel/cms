<?php
/**
 * Конфигурационный файл CMS
 * Сгенерирован установщиком 2026-03-16 08:41:55
 */

// Доступ к базе данных.
// PostgreSQL через переменные окружения Docker.
define('DB_DRIVER', getenv('DB_DRIVER') ?: 'pgsql');
define('DB_HOST', getenv('DB_HOST') ?: 'db');
define('DB_PORT', getenv('DB_PORT') ?: '5432');
define('DB_NAME', getenv('DB_NAME') ?: 'cms');
define('DB_USER', getenv('DB_USER') ?: 'cms');
define('DB_PASS', getenv('DB_PASS') ?: 'cms');
define('DB_CHARSET', 'utf8');

// Настройки сайта
define('SITE_NAME', getenv('SITE_NAME') ?: 'Моя CMS');
$__scheme = ((!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https')) ? 'https' : 'http';
define('SITE_URL', $__scheme . '://' . $_SERVER['HTTP_HOST']);
unset($__scheme);
define('ADMIN_EMAIL', getenv('ADMIN_EMAIL') ?: 'ilhar2k@ya.ru');

// Пути к директориям
defined('ROOT_PATH') or define('ROOT_PATH', dirname(dirname(__DIR__)));
defined('PUBLIC_PATH') or define('PUBLIC_PATH', ROOT_PATH . '/public');
defined('ADMIN_PATH') or define('ADMIN_PATH', ROOT_PATH . '/admin');
defined('CORE_PATH') or define('CORE_PATH', ROOT_PATH . '/core');
defined('TEMPLATES_PATH') or define('TEMPLATES_PATH', ROOT_PATH . '/templates');

// Настройки сессии
define('SESSION_LIFETIME', 3600);

// Настройки безопасности
define('HASH_ALGO', PASSWORD_BCRYPT);
define('HASH_COST', 10);

// Ключ шифрования чувствительных данных (API-ключи платёжных систем).
// AES-256-CBC. НЕ МЕНЯТЬ после внесения ключей — данные перестанут расшифровываться.
define('APP_ENCRYPTION_KEY', getenv('APP_ENCRYPTION_KEY') ?: '140ce5c3fc65a29787e350261b047dc01997ce19a76d7dbe760d2106e371dcab');

// Отладка (false в production)
define('DEBUG', getenv('APP_DEBUG') ? strtolower(getenv('APP_DEBUG')) === 'true' : true);

// Постов на страницу
define('POSTS_PER_PAGE', 10);
