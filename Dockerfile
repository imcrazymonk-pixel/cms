FROM php:8.1-fpm-alpine

RUN set -eux; \
    apk add --no-cache \
        postgresql-client \
        unzip \
        git \
    ; \
    docker-php-ext-install -j$(nproc) \
        pdo_pgsql \
        pdo_mysql \
        intl \
        mbstring \
        opcache \
    ; \
    docker-php-ext-enable opcache

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

COPY . .

RUN chown -R www-data:www-data /var/www/html/public/uploads 2>/dev/null || true

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["php-fpm"]