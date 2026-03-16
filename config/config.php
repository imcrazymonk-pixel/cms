<?php
/**
 * Конфигурационный файл CMS
 * Сгенерирован установщиком 2026-03-16 08:41:55
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

// Отладка (false в production)
define('DEBUG', true);

// Постов на страницу
define('POSTS_PER_PAGE', 10);
