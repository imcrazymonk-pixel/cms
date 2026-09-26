FROM php:8.1-fpm

# Install system dependencies
RUN apt-get update && apt-get install -y \
        libpq-dev \
        libicu-dev \
        libonig-dev \
        postgresql-client \
        unzip \
        git \
    && rm -rf /var/lib/apt/lists/*

# Install PHP extensions
RUN docker-php-ext-install \
        pdo_pgsql \
        pdo_mysql \
        mbstring \
        intl \
        opcache

WORKDIR /var/www/html

COPY . .

RUN chown -R www-data:www-data /var/www/html/public/uploads 2>/dev/null || true

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["php-fpm"]