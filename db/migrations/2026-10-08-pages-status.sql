-- Pages: status + updated_at.
-- The PHP pages API (core/routes.php) and the React PageEdit both read/write
-- `status`, and PHP writes `updated_at` on update. The base schema lacked both,
-- so page creation failed (column "status" does not exist).
-- Idempotent — safe to run where the columns already exist.
ALTER TABLE pages ADD COLUMN IF NOT EXISTS status varchar(50) NOT NULL DEFAULT 'draft';
ALTER TABLE pages ADD COLUMN IF NOT EXISTS updated_at timestamp without time zone NOT NULL DEFAULT now();
