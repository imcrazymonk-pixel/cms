-- Fix out-of-sync id sequences (caused by data imports).
-- Without this, INSERT into these tables fails with "duplicate key ... _pkey".
SELECT setval(pg_get_serial_sequence('posts','id'),            COALESCE((SELECT MAX(id) FROM posts),0)+1,            false);
SELECT setval(pg_get_serial_sequence('categories','id'),       COALESCE((SELECT MAX(id) FROM categories),0)+1,       false);
SELECT setval(pg_get_serial_sequence('users','id'),            COALESCE((SELECT MAX(id) FROM users),0)+1,            false);
SELECT setval(pg_get_serial_sequence('pages','id'),            COALESCE((SELECT MAX(id) FROM pages),0)+1,            false);
SELECT setval(pg_get_serial_sequence('menus','id'),            COALESCE((SELECT MAX(id) FROM menus),0)+1,            false);
SELECT setval(pg_get_serial_sequence('menu_items','id'),       COALESCE((SELECT MAX(id) FROM menu_items),0)+1,       false);
SELECT setval(pg_get_serial_sequence('widgets','id'),          COALESCE((SELECT MAX(id) FROM widgets),0)+1,          false);
SELECT setval(pg_get_serial_sequence('tags','id'),             COALESCE((SELECT MAX(id) FROM tags),0)+1,             false);
SELECT setval(pg_get_serial_sequence('media','id'),            COALESCE((SELECT MAX(id) FROM media),0)+1,            false);
SELECT setval(pg_get_serial_sequence('comments','id'),         COALESCE((SELECT MAX(id) FROM comments),0)+1,         false);
SELECT setval(pg_get_serial_sequence('app_logs','id'),         COALESCE((SELECT MAX(id) FROM app_logs),0)+1,         false);
SELECT setval(pg_get_serial_sequence('fin_transactions','id'), COALESCE((SELECT MAX(id) FROM fin_transactions),0)+1, false);
