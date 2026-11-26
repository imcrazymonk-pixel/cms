#!/bin/sh
set -e

echo "=== HexaVeil CMS Docker EntryPoint ==="

echo "Waiting for PostgreSQL..."
attempt=0
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        echo "ERROR: PostgreSQL is not ready after 60 attempts (${DB_HOST}:${DB_PORT})." >&2
        echo "       Check the db service health and DB_* environment variables." >&2
        exit 1
    fi
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
