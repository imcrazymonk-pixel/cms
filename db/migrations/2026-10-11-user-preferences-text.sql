-- Migration: expand user_preferences.pref_value from VARCHAR(100) to TEXT
-- Reason: panel_ui_state JSON blob can exceed 100 chars (sidebar links + appearance)

ALTER TABLE user_preferences ALTER COLUMN pref_value TYPE TEXT;