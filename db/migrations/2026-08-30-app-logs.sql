-- ============================================
-- Миграция: таблица app_logs для централизованного логирования
-- Используется модулём «Логи» в блоке «Система» админки,
-- а также для отслеживания событий Platega-синка.
-- ============================================

CREATE TABLE IF NOT EXISTS `app_logs` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `level` VARCHAR(20) NOT NULL DEFAULT 'info',
  `channel` VARCHAR(50) NOT NULL DEFAULT 'system',
  `message` TEXT NOT NULL,
  `context` TEXT DEFAULT NULL,
  INDEX `idx_created_at` (`created_at`),
  INDEX `idx_level_channel` (`level`, `channel`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
