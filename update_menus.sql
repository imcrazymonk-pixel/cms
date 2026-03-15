-- Обновление таблицы menus для CMS
-- Запустить в phpMyAdmin

-- Отключаем проверку внешних ключей
SET FOREIGN_KEY_CHECKS = 0;

-- 1. Добавляем поле url (игнорируем ошибку если есть)
ALTER TABLE menus ADD COLUMN url VARCHAR(255) NOT NULL DEFAULT '' AFTER name;

-- 2. Добавляем поле location (игнорируем ошибку если есть)
ALTER TABLE menus ADD COLUMN location VARCHAR(50) DEFAULT 'main' AFTER url;

-- 3. Очищаем старые данные
TRUNCATE TABLE menus;

-- 4. Добавляем новые данные
INSERT INTO menus (name, url, location) VALUES
('Главная', '/', 'main'),
('Блог', '/blog', 'main'),
('О нас', '/about', 'main'),
('Контакты', '/contacts', 'main'),
('Главная (футер)', '/', 'footer'),
('О нас (футер)', '/about', 'footer'),
('Контакты (футер)', '/contacts', 'footer');

-- Включаем проверку внешних ключей обратно
SET FOREIGN_KEY_CHECKS = 1;
