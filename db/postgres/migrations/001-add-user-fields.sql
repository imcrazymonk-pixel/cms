-- Migration 001: Add display_name, status, updated_at to users
-- Run: docker compose exec db psql -U cms -d cms -f /docker-entrypoint-initdb.d/migrations/001-add-user-fields.sql

ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(100) DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Add CHECK constraint for status if not exists (PostgreSQL doesn't have IF NOT EXISTS for CHECK)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'users_status_check'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_status_check CHECK (status IN ('active', 'inactive', 'banned'));
    END IF;
END $$;

-- Create or replace the trigger
CREATE OR REPLACE FUNCTION update_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists and recreate
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_users_updated_at();

-- Update existing users to have active status
UPDATE users SET status = 'active', updated_at = NOW() WHERE status IS NULL;

-- Update existing users to have display_name from login where null
UPDATE users SET display_name = login WHERE display_name IS NULL;