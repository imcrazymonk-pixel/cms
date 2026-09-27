#!/bin/sh
set -e

echo "=== HexaVeil CMS Docker EntryPoint ==="

echo "Waiting for PostgreSQL..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL is ready."

# Ensure install.lock exists (skip the web installer)
if [ ! -f /var/www/html/install.lock ]; then
    echo "Creating install.lock..."
    touch /var/www/html/install.lock
    chown www-data:www-data /var/www/html/install.lock
fi

# Generate admin password hash if it's still a placeholder (safe mode, no fail)
ADMIN_PW="${ADMIN_PASSWORD:-admin12345}"
ADMIN_HASH=$(php -r "echo password_hash('$ADMIN_PW', PASSWORD_BCRYPT);" 2>/dev/null || true)
if [ -n "$ADMIN_HASH" ]; then
    PG_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM users WHERE login='admin' AND password='\$2y\$10\$change_this_to_a_real_bcrypt_hash';" 2>/dev/null || echo "0")
    if [ "$PG_COUNT" = "1" ]; then
        echo "Updating admin password hash..."
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "UPDATE users SET password='$ADMIN_HASH' WHERE login='admin';" >/dev/null 2>&1 || true
    fi
fi

echo "Starting PHP-FPM..."
exec php-fpm