-- Миграция для обновления таблицы pages
-- Запустить в phpMyAdmin или через консоль MySQL

ALTER TABLE pages 
ADD COLUMN IF NOT EXISTS meta_description VARCHAR(255) DEFAULT NULL AFTER content,
ADD COLUMN IF NOT EXISTS user_id INT DEFAULT NULL AFTER meta_description,
ADD CONSTRAINT fk_pages_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
