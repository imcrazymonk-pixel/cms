#!/bin/sh
# ─────────────────────────────────────────────────────────────
# HexaVeil CMS — деплой одной командой:  git pull && sh deploy.sh
# Сборка/запуск контейнеров (включая one-shot `migrate`), reload nginx.
# Идемпотентно. .env НЕ исполняется (там бывают значения с пробелами).
# ─────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

# Безопасно прочитать значение из .env
env_get() {
  grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^"//; s/"$//'
}
HTTP_PORT=$(env_get CMS_HTTP_PORT); HTTP_PORT=${HTTP_PORT:-80}

echo "==> docker compose up -d --build (сервис migrate применяет миграции)"
docker compose up -d --build

echo "==> перезагрузка nginx (подхватить default.conf)"
if docker compose exec -T web nginx -t >/dev/null 2>&1; then
  docker compose exec -T web nginx -s reload || echo "   reload skipped"
else
  echo "   reload skipped (nginx config test failed)"
fi

echo "==> статус"
docker compose ps

echo "==> проверка health"
curl -fsS "http://localhost:${HTTP_PORT}/api/health" || echo "   health check failed — см. docker compose logs"

echo "==> готово"
