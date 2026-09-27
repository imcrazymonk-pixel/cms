-- ============================================
-- Миграция: расширение таблицы app_logs
-- Добавляет category + source для группировки логов
-- по категориям (сайт, модули, система, инфраструктура, docker, loki)
-- ============================================

-- Добавляем колонку category (группа логов)
ALTER TABLE `app_logs`
  ADD COLUMN `category` VARCHAR(50) NOT NULL DEFAULT 'system'
  AFTER `level`,
  ADD COLUMN `source` VARCHAR(50) DEFAULT NULL
  AFTER `channel`;

-- Обновляем существующие записи с маппингом channel → category
UPDATE `app_logs` SET `category` = 'modules', `source` = 'platega' WHERE `channel` = 'platega';
UPDATE `app_logs` SET `category` = 'modules', `source` = 'yookassa' WHERE `channel` = 'yookassa';
UPDATE `app_logs` SET `category` = 'system' WHERE `channel` IN ('system', 'auth');
UPDATE `app_logs` SET `category` = 'users', `source` = 'user' WHERE `channel` = 'user';
UPDATE `app_logs` SET `category` = 'finance' WHERE `channel` = 'finance';

-- Индекс для быстрой фильтрации по категории + уровню
ALTER TABLE `app_logs`
  ADD INDEX `idx_category_level` (`category`, `level`);