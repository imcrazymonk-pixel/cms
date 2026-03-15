-- Обновление базы данных для CMS
-- Запустить в phpMyAdmin (вкладка SQL) или через консоль MySQL

-- 1. Обновляем таблицу pages (добавляем новые поля)
ALTER TABLE pages 
ADD COLUMN IF NOT EXISTS meta_description VARCHAR(255) DEFAULT NULL AFTER content,
ADD COLUMN IF NOT EXISTS user_id INT DEFAULT NULL AFTER meta_description;

-- 2. Добавляем внешние ключи (если их нет)
ALTER TABLE pages 
ADD CONSTRAINT fk_pages_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- 3. Добавляем недостающие настройки (если их нет)
INSERT INTO settings (setting_key, setting_value) VALUES
('meta_description', ''),
('meta_keywords', '')
ON DUPLICATE KEY UPDATE setting_value = setting_value;
