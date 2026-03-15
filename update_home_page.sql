-- Миграция: добавление поля is_home для выбора главной страницы
-- Дата: 2026-03-15

ALTER TABLE pages ADD COLUMN is_home TINYINT(1) DEFAULT 0 AFTER template;
ALTER TABLE pages ADD INDEX idx_is_home (is_home);

-- Сбрасываем все страницы (на случай если уже есть поле)
UPDATE pages SET is_home = 0;
