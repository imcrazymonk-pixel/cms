-- Post editor metadata: SEO, featured, comments, canonical.
-- These fields are surfaced by the post editor (both PHP v2 and the React SPA).
ALTER TABLE posts ADD COLUMN IF NOT EXISTS seo_title varchar(255);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS seo_description text;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS canonical varchar(255);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS featured boolean NOT NULL DEFAULT false;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS comments_enabled boolean NOT NULL DEFAULT true;
