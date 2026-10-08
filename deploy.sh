#!/bin/sh
# ─────────────────────────────────────────────────────────────
# HexaVeil CMS — деплой одной командой:  git pull && sh deploy.sh
# Сборка/запуск контейнеров, применение миграций БД, reload nginx.
# Идемпотентно. .env НЕ исполняется (там бывают значения с пробелами).
# ─────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

# Безопасно прочитать значение из .env
env_get() {
  grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^"//; s/"$//'
}
DB_U=$(env_get DB_USER);      DB_U=${DB_U:-cms}
DB_N=$(env_get DB_NAME);      DB_N=${DB_N:-cms}
HTTP_PORT=$(env_get CMS_HTTP_PORT); HTTP_PORT=${HTTP_PORT:-80}

echo "==> docker compose up -d --build"
docker compose up -d --build

echo "==> миграции БД (идемпотентные)"
for f in \
  db/migrations/2026-09-27-app-logs-expand.sql \
  db/migrations/2026-10-08-posts-metadata.sql \
  db/migrations/2026-10-08-pages-status.sql \
  db/migrations/2026-10-08-fix-sequences.sql ; do
  if [ -f "$f" ]; then
    printf '   - %s ... ' "$f"
    if docker exec -i hexacms_db psql -U "$DB_U" -d "$DB_N" < "$f" >/dev/null 2>&1; then
      echo ok
    else
      echo "SKIP/ERR"
    fi
  fi
done

echo "==> перезагрузка nginx (подхватить default.conf)"
docker exec hexacms_web nginx -t >/dev/null 2>&1 && docker exec hexacms_web nginx -s reload || echo "   reload skipped"

echo "==> статус"
docker compose ps

echo "==> готово. Проверка: curl -s http://localhost:${HTTP_PORT}/api/health"
