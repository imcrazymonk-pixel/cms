-- ============================================
-- Миграция: расширение таблицы app_logs (PostgreSQL)
-- Добавляет category + source для группировки логов
-- по категориям (сайт, модули, система, инфраструктура, docker, loki)
-- ============================================

-- Добавляем колонки (IF NOT EXISTS — идиомат через DO)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'app_logs' AND column_name = 'category'
    ) THEN
        ALTER TABLE app_logs ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'system';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'app_logs' AND column_name = 'source'
    ) THEN
        ALTER TABLE app_logs ADD COLUMN source VARCHAR(50) DEFAULT NULL;
    END IF;
END $$;

-- Обновляем существующие записи с маппингом channel → category
UPDATE app_logs SET category = 'modules', source = 'platega' WHERE channel = 'platega';
UPDATE app_logs SET category = 'modules', source = 'yookassa' WHERE channel = 'yookassa';
UPDATE app_logs SET category = 'system' WHERE channel IN ('system', 'auth');
UPDATE app_logs SET category = 'users', source = 'user' WHERE channel = 'user';
UPDATE app_logs SET category = 'finance' WHERE channel = 'finance';

-- Индекс для быстрой фильтрации по категории + уровню
CREATE INDEX IF NOT EXISTS idx_category_level ON app_logs (category, level);