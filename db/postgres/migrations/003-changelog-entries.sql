-- Changelog entries table for the Docs/Changelog page in CMS
CREATE TABLE IF NOT EXISTS changelog_entries (
    id SERIAL PRIMARY KEY,
    day_of_week VARCHAR(2) NOT NULL,
    entry_date DATE NOT NULL,
    entry_time TIME NOT NULL DEFAULT '12:00:00',
    author VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TRIGGER update_changelog_entries_updated_at BEFORE UPDATE ON changelog_entries
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_changelog_entries_sort ON changelog_entries(sort_order);

-- Import existing entries from docs/CHANGELOG_CMS.md into DB
DO $$
DECLARE
  entry_record RECORD;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM changelog_entries LIMIT 1) THEN
    -- Data import will be handled by the application on first API call
    RAISE NOTICE 'Changelog table created — data will be imported from file on first access';
  END IF;
END $$;