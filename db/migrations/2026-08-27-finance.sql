-- ============================================
-- Миграция: финансовый модуль «Финансы»
-- Таблицы с префиксом fin_ (модульная схема CMS)
-- ============================================

CREATE TABLE IF NOT EXISTS `fin_transactions` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `date` DATE NOT NULL,
  `type` ENUM('income','expense') NOT NULL,
  `category` VARCHAR(100) NOT NULL,
  `participant` VARCHAR(100) DEFAULT NULL,
  `amount` DECIMAL(15,2) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_date` (`date`),
  INDEX `idx_type` (`type`),
  INDEX `idx_category` (`category`),
  INDEX `idx_participant` (`participant`),
  INDEX `idx_date_type` (`date`, `type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `fin_settings` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `setting_key` VARCHAR(100) NOT NULL UNIQUE,
  `setting_value` TEXT DEFAULT NULL,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_key` (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Настройки по умолчанию (JSON-массивы хранятся как JSON-строки)
INSERT INTO `fin_settings` (`setting_key`, `setting_value`) VALUES
  ('currency', '₽'),
  ('decimals', '2'),
  ('auto_refresh', '0'),
  ('avg_period', 'day'),
  ('avg_exclude_categories', '[]'),
  ('avg_exclude_income_keywords', '[]'),
  ('avg_exclude_expense_keywords', '[]'),
  ('quick_categories', '[]'),
  ('quick_participants', '[]'),
  ('platega_merchant_id', ''),
  ('platega_secret', ''),
  ('platega_days_back', '150'),
  ('platega_auto_sync', '0'),
  ('platega_last_sync', '')
ON DUPLICATE KEY UPDATE `setting_key` = `setting_key`;
