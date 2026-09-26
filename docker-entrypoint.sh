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

echo "Starting PHP-FPM..."
exec php-fpm