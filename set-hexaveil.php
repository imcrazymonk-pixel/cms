<?php
/**
 * ВРЕМЕННЫЙ скрипт активации темы HexaVeil.
 *
 * Запуск на сервере (в корне проекта, где есть PHP + MySQL):
 *     php set-hexaveil.php
 *
 * Что делает:
 *   1. Включает тему 'hexaveil' (лендинг станет главной страницей).
 *   2. Меняет название сайта на "HexaVeil".
 *   3. Сбрасывает флаг главной страницы (is_home=0), чтобы главной
 *      отображался лендинг темы, а не статическая страница CMS.
 *
 * ВНИМАНИЕ: после успешного запуска УДАЛИТЕ этот файл.
 */

// CLI: $_SERVER['HTTP_HOST'] может отсутствовать, а config.php его использует
$_SERVER['HTTP_HOST'] = $_SERVER['HTTP_HOST'] ?? 'localhost';

define('ROOT_PATH', __DIR__);

require_once ROOT_PATH . '/config/config.php';
require_once CORE_PATH . '/Autoloader.php';
Autoloader::register();
require_once CORE_PATH . '/helpers.php';

$setting = new Setting();
$setting->set('active_theme', 'hexaveil');
$setting->set('site_name', 'HexaVeil');
$setting->set('site_description', 'Обходи блокировки и пользуйся любимыми иностранными сервисами. Современный VPN с киберпанк-эстетикой.');

// Сбрасываем главную страницу: главной станет лендинг (index темы).
// Если позже понадобится вернуть статическую страницу на главную —
// назначьте её в админке (Страницы → Сделать главной).
Database::getInstance()->query('UPDATE pages SET is_home = 0');

echo "OK: тема hexaveil активирована.\n";
echo "Удалите файл set-hexaveil.php с сервера.\n";
