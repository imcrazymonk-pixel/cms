<?php
/**
 * Конфигурационный файл CMS
 * Сгенерирован установщиком 2026-03-13 19:34:39
 */

// Доступ к базе данных
define('DB_HOST', 'localhost');
define('DB_NAME', 'cms');
define('DB_USER', 'root');
define('DB_PASS', '');
define('DB_CHARSET', 'utf8mb4');

// Настройки сайта
define('SITE_NAME', 'Моя CMS');
define('SITE_URL', 'http://' . $_SERVER['HTTP_HOST']);
define('ADMIN_EMAIL', 'ilhar2k@ya.ru');

// Пути к директориям (если не определены в index.php)
if (!defined('ROOT_PATH')) define('ROOT_PATH', dirname(dirname(__DIR__)));
if (!defined('PUBLIC_PATH')) define('PUBLIC_PATH', ROOT_PATH . '/public');
if (!defined('ADMIN_PATH')) define('ADMIN_PATH', ROOT_PATH . '/admin');
if (!defined('CORE_PATH')) define('CORE_PATH', ROOT_PATH . '/core');
if (!defined('TEMPLATES_PATH')) define('TEMPLATES_PATH', ROOT_PATH . '/templates');

// Настройки сессии
define('SESSION_LIFETIME', 3600);

// Настройки безопасности
define('HASH_ALGO', PASSWORD_BCRYPT);
define('HASH_COST', 10);

// Отладка (false в production)
define('DEBUG', true);

// Постов на страницу
define('POSTS_PER_PAGE', 10);
