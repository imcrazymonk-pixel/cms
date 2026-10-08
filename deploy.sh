#!/bin/sh
# ─────────────────────────────────────────────────────────────
# HexaVeil CMS — деплой одной командой
#   git pull && ./deploy.sh
# Делает: сборку/запуск контейнеров, применение миграций БД,
# перезагрузку конфига nginx. Идемпотентно — можно запускать повторно.
# ─────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

# Подхватить DB creds / порт из .env
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

DB_U="${DB_USER:-cms}"
DB_N="${DB_NAME:-cms}"

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
      echo "ok"
    else
      echo "SKIP/ERR"
    fi
  fi
done

echo "==> перезагрузка nginx (подхватить default.conf)"
docker exec hexacms_web nginx -t >/dev/null 2>&1 && docker exec hexacms_web nginx -s reload || echo "   nginx reload skipped"

echo "==> статус"
docker compose ps

echo "==> готово. Проверка: curl -s http://localhost:${CMS_HTTP_PORT:-80}/api/health"
