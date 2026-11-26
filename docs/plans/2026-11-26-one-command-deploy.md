# План: установка HexaVeil CMS на чистый сервер за 2–3 команды

- **Дата:** 2026-11-26
- **Статус:** план, готов к реализации (`coder`)
- **Область:** `deploy/`, `Dockerfile*`, `docker-compose*.yml`, `docker-entrypoint.sh`,
  `config/config.php`, `web/backend/core/{config,crypto}.py`, `.docker/nginx/default.conf`,
  `db/**/*.sql`, `deploy.sh`, `DEPLOY.md`, документация.
- **Запрещено менять:** маршруты, контроллеры, имена полей форм, бизнес-логику приложения.
- **Целевой результат:** на чистом Ubuntu/Debian сервере — клон репозитория и один
  запуск установщика; автоматический TLS, БД, миграции, админ; пароль показан один раз.

---

## 0. Решения (зафиксированы, без вариантов)

| Вопрос | Решение |
|---|---|
| Reverse proxy | **Caddy 2 в compose** с автоматическим TLS (ACME). Fallback — host nginx + certbot. |
| SPA в проде | **Собирается в Docker multi-stage** (`node:20-alpine` → `nginx:alpine`), не зависит от закоммиченного `dist`. |
| Bind-mount репозитория в проде | `app` — нет (код из образа); `web` — нет (public+dist из образа); `api` — `.:/var/www/html` **RW** (нужен для `templates/`, `tools/`, `nodes_stats.json`; технический долг, фиксируется в ADR). |
| Схема БД | Отдельный one-shot сервис **`migrate`** + ledger-таблица `schema_migrations`; `initdb`-mount в новом compose убирается. |
| Админ | Логин **`admin`** (как в `01-schema.sql`), пароль задаёт `deploy/bootstrap_admin.php`; `docker-entrypoint.sh` больше не трогает пароли. |
| Домены | Два домена: `SITE_DOMAIN` (публичный сайт) и `ADMIN_DOMAIN` (SPA `/admin/` + API). |
| Порт CMS в fallback | `127.0.0.1:3000` (совместимо с текущим продом). |
| Пароль в `.env` | Не хранится после bootstrap. Генерируется установщиком, пишется в `.install-credentials` (0600) и печатается один раз. |

---

## 1. Целевой UX

### 1.1 Клонирование (2 команды)

```bash
git clone https://github.com/imcrazymonk-pixel/cms.git /opt/hexaveil-cms
cd /opt/hexaveil-cms && sudo bash deploy/install.sh
```

`install.sh` сам спросит (при наличии TTY): `SITE_DOMAIN`, `ADMIN_DOMAIN`, `ACME_EMAIL`,
`ADMIN_LOGIN` (по умолчанию `admin`), `ADMIN_PASSWORD` (по умолчанию — сгенерировать),
`SITE_NAME`. Всё остальное — автоматически.

Полностью неинтерактивный вариант (2 команды, без вопросов):

```bash
git clone https://github.com/imcrazymonk-pixel/cms.git /opt/hexaveil-cms
cd /opt/hexaveil-cms && sudo bash deploy/install.sh \
  --site-domain example.com --admin-domain admin.example.com \
  --acme-email ops@example.com --non-interactive
```

### 1.2 `curl | bash` (1 команда)

```bash
curl -fsSL https://raw.githubusercontent.com/imcrazymonk-pixel/cms/main/deploy/install.sh \
  | sudo bash -s -- --site-domain example.com --admin-domain admin.example.com \
                     --acme-email ops@example.com
```

Правила для `curl|bash`:
- установщик не полагается на `$0`/текущий каталог: если рядом нет `docker-compose.yml`,
  клонирует репозиторий в `/opt/hexaveil-cms` (URL — `--repo` / `HEXAVEIL_REPO_URL`);
- все интерактивные вопросы читаются из **`/dev/tty`**, а не из stdin (stdin занят скриптом);
- при `--non-interactive` отсутствие обязательного флага — ошибка с подсказкой;
- репозиторий публичный (`imcrazymonk-pixel/cms`), поэтому `curl|bash` работает без SSH-ключа.

### 1.3 Что видит пользователь в конце

```
══════════════════════════════════════════════════════════════
 HexaVeil CMS установлен
══════════════════════════════════════════════════════════════
 Публичный сайт : https://example.com
 Админка        : https://admin.example.com/admin/
 Health         : https://admin.example.com/api/health  → 200
 Логин          : admin
 Пароль         : Xy7-... (сгенерирован)
                  сохранён в /opt/hexaveil-cms/.install-credentials (0600)
                  ⚠ сохраните и удалите файл: sudo rm /opt/hexaveil-cms/.install-credentials
 Каталог        : /opt/hexaveil-cms
 Управление     : cd /opt/hexaveil-cms && sudo docker compose -f deploy/compose.install.yml ps
 Логи           : ... logs -f
 Повторный запуск установщика безопасен (секреты и БД не меняются).
══════════════════════════════════════════════════════════════
```

Пароль:
- если сгенерирован — печатается **один раз** и пишется в `.install-credentials` (0600, root);
- если задан пользователем — в файл не пишется, печатается только логин и напоминание;
- после успешной установки строка `ADMIN_PASSWORD` из `.env` удаляется.

---

## 2. Установщик `deploy/install.sh`

POSIX-совместимый bash, `set -euo pipefail`, идемпотентный, без внешних зависимостей кроме
`curl`, `openssl`, `git`, `docker`.

### 2.1 Флаги и env-переменные

| Флаг | Env | Назначение |
|---|---|---|
| `--site-domain` | `SITE_DOMAIN` | публичный домен |
| `--admin-domain` | `ADMIN_DOMAIN` | домен админки/API |
| `--acme-email` | `ACME_EMAIL` | ACME-аккаунт Caddy/certbot |
| `--admin-login` | `ADMIN_LOGIN` | по умолчанию `admin` |
| `--admin-password` | `ADMIN_PASSWORD` | если нет — сгенерировать |
| `--site-name` | `SITE_NAME` | заголовок сайта |
| `--repo` | `HEXAVEIL_REPO_URL` | URL для клонирования (curl-режим) |
| `--dir` | `INSTALL_DIR` | по умолчанию `/opt/hexaveil-cms` |
| `--behind-proxy` / `--proxy=host-nginx` | — | не занимать 80/443, слушать `127.0.0.1:3000` |
| `--adopt-existing` | — | миграция существующей установки без изменения секретов/данных |
| `--reset-admin-password` | — | принудительно сменить пароль существующего админа |
| `--reconfigure-domains` | — | разрешить менять домены на повторном запуске |
| `--no-install-docker` | — | не ставить Docker автоматически |
| `--non-interactive` | — | не задавать вопросов |
| `--dry-run` | — | проверки + генерация `.env`, без `up` |

### 2.2 Проверки (до любых изменений)

1. **root** (`id -u == 0`) — иначе понятная ошибка `sudo`.
2. **ОС**: Debian/Ubuntu (`/etc/os-release`), иначе warning + продолжение.
3. **Docker**: `docker` + `docker compose version`. Если нет и не `--no-install-docker` —
   официальный `https://get.docker.com` (curl|sh), затем `systemctl enable --now docker`.
4. **Порты**: `ss -ltn` на `:80` и `:443` (или `:3000` в `--behind-proxy`).
   Заняты → abort с PID/именем процесса; для текущего прод-сервера — `--behind-proxy`.
5. **Диск**: ≥ 5 ГБ свободно на `$INSTALL_DIR`; **RAM** ≥ 1 ГБ (warning).
6. **DNS**: A-запись `SITE_DOMAIN`/`ADMIN_DOMAIN` должна указывать на внешний IP
   (`curl -s https://api.ipify.org`). Несовпадение — **warning**, не abort (NAT/прокси).
7. **Домены**: непустые, различны, валидный формат; иначе abort.
8. **Повторный запуск**: если `.env` уже есть — домены должны совпадать, иначе abort
   с подсказкой `--reconfigure-domains`.

### 2.3 Что генерируется (только если ключа нет в `.env`)

```
DB_NAME=cms
DB_USER=cms
DB_PASS=$(openssl rand -base64 36 | tr -dc 'A-Za-z0-9' | cut -c1-32)
JWT_SECRET=$(openssl rand -hex 32)
APP_ENCRYPTION_KEY=$(openssl rand -hex 32)        # 64 hex, общий для PHP и FastAPI
APP_DEBUG=false
SITE_NAME=...
SITE_URL=https://${SITE_DOMAIN}
CMS_PUBLIC_URL=https://${ADMIN_DOMAIN}
CORS_ORIGINS=https://${ADMIN_DOMAIN},https://${SITE_DOMAIN}
ADMIN_EMAIL=${ACME_EMAIL}
ADMIN_LOGIN=${ADMIN_LOGIN}
SITE_DOMAIN=${SITE_DOMAIN}
ADMIN_DOMAIN=${ADMIN_DOMAIN}
ACME_EMAIL=${ACME_EMAIL}
TZ=$(cat /etc/timezone 2>/dev/null || echo UTC)
MAX_UPLOAD_SIZE=67108864
LOG_DIR=/app/logs
```

`APP_SECRET` не вводится: PHP использует `APP_ENCRYPTION_KEY`, FastAPI — `JWT_SECRET`
(с fallback на `APP_ENCRYPTION_KEY`). Дублировать секрет не нужно.

Запись `.env`: `umask 077`, во временный файл → `mv` (атомарно), `chmod 600`.
Существующий `.env` → `.env.bak.<timestamp>`.

### 2.4 Порядок запуска (важен для бэкапа и миграций)

1. Проверки и генерация `.env` (см. выше).
2. `docker compose -f deploy/compose.install.yml up -d db`
3. Дождаться `pg_isready` (≤ 60 с).
4. Если в БД уже есть `users` — **автобэкап**:
   `pg_dump` → `deploy/backups/pre-migrate-<ts>.sql` (вне тома БД).
5. `docker compose ... up -d --build` → сервис `migrate` выполняется и завершается
   с кодом 0, затем поднимаются `app`, `api`, `web`, `caddy`.
6. Ждать `api` health (`docker compose ps` + HTTP 200 на `/api/health`, ≤ 90 с).
7. Bootstrap админа: `docker compose exec -T app php deploy/bootstrap_admin.php`
   (логин/пароль через `-e`, не через `.env`).
8. Удалить `ADMIN_PASSWORD` из `.env`.
9. Дождаться TLS: `curl --resolve admin…:443:127.0.0.1 https://…/api/health` ≤ 120 с;
   при неудаче — warning + инструкция (DNS/порт 80).
10. Сводка + `.install-credentials`.

### 2.5 Идемпотентность повторного запуска

- секреты не перегенерируются; `.env` только дополняется недостающими ключами;
- `docker compose up -d --build` пересоздаёт контейнеры, тома (`pgdata`, `uploads_data`,
  `backup_data`, `caddy_data`) не трогаются;
- `migrate` пропускает уже применённые файлы по ledger;
- пароль админа **не меняется** без `--reset-admin-password`;
- `install.lock` создаётся entrypoint'ом, повторно не ломает;
- `--reconfigure-domains` меняет только домены/CORS/Caddyfile-render и перезапускает `caddy`.

---

## 3. Reverse proxy

### 3.1 Выбор: Caddy 2 в compose

Причины:
- автоматический TLS (Let's Encrypt/ZeroSSL), HTTP→HTTPS, renewal — без cron и certbot;
- WebSocket Upgrade проксируется «из коробки»;
- два домена описываются двумя блоками, конфиг читает env (`{$SITE_DOMAIN}`);
- «2–3 команды» реально достижимы: нет установки пакетов на хост и правок `/etc/nginx`;
- единая точка входа, а вся маршрутизация остаётся во внутреннем nginx
  (`.docker/nginx/default.conf`) — не дублируем правила.

### 3.2 Маршрутизация двух доменов

```
SITE_DOMAIN  ──► caddy:443 ──► web:80 (внутренний nginx) ──► PHP (app:9000)
                                                          └─► /api/* → api:8000

ADMIN_DOMAIN ──► caddy:443 ──► web:80
   /            → 302 /admin/
   /admin/*     → SPA из dist (alias, try_files → /admin/index.html)
   /api/*       → api:8000
   /api/support/ws → api:8000 (Upgrade)
   /admin/diagnostics/api/, /admin/finance/api/, /admin/settings/save-* → api:8000
```

Решение по SPA: **остаётся на `/admin/`**. `vite.config.ts` уже `base: '/admin/'`,
роутер — basename `/admin`; перенос SPA в корень потребовал бы менять сборку и роутинг.
Корень `ADMIN_DOMAIN` отдаёт `302 → /admin/`.

### 3.3 Caddyfile (скелет)

```caddyfile
{
    email {$ACME_EMAIL}
}

{$SITE_DOMAIN} {
    encode zstd gzip
    request_body { max_size 64MB }

    reverse_proxy web:80 {
        header_up Host              {host}
        header_up X-Real-IP         {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}

{$ADMIN_DOMAIN} {
    encode zstd gzip
    request_body { max_size 64MB }

    redir / /admin/ 302

    reverse_proxy web:80 {
        header_up Host              {host}
        header_up X-Real-IP         {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

Замечания:
- лимит 64 МБ согласован с `client_max_body_size 64M` и `MAX_UPLOAD_SIZE=67108864`;
- WebSocket не требует отдельного блока: Caddy пробрасывает Upgrade, внутренний nginx —
  отдельный `location /api/support/ws`;
- ACME staging при отладке: `CADDY_ACME_CA=https://acme-staging-v02.api.letsencrypt.org/directory`
  (передаётся в `caddy` env), чтобы не упереться в rate limit.

### 3.4 Обязательная правка внутреннего nginx

Сейчас `.docker/nginx/default.conf` жёстко ставит `X-Forwarded-Proto $scheme` (за прокси это
всегда `http`), из-за чего PHP строит `SITE_URL` как `http://…`. Исправить:

```nginx
map $http_x_forwarded_proto $hv_proto {
    default $http_x_forwarded_proto;
    ""      $scheme;
}

# во всех proxy_set_header:
proxy_set_header X-Forwarded-Proto $hv_proto;

# в location ~ \.php$:
include fastcgi_params;
fastcgi_param HTTP_X_FORWARDED_PROTO $hv_proto;
```

`server_name localhost hexacms;` → `server_name _;` (домены решает Caddy).

### 3.5 Fallback: host nginx + certbot (если Caddy недоступен)

Один fallback, без третьего варианта. Установщик `--proxy=host-nginx`:
- `web` публикует только `127.0.0.1:3000:80` (как текущий прод);
- генерирует два server-блока из `deploy/nginx-host/*.template` в `/etc/nginx/sites-available/`;
- получает сертификаты `certbot --nginx -d "$SITE_DOMAIN" -d "$ADMIN_DOMAIN" --email "$ACME_EMAIL" --agree-tos -n`;
- `certbot.timer` (пакет ставит unit) обеспечивает renewal.

Скелет (оба домена аналогичны, отличается `server_name` и редиректом корня):

```nginx
server {
    listen 80;
    server_name example.com;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl http2;
    server_name example.com;
    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    client_max_body_size 64M;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        $connection_upgrade;
    }
}
```

(для `ADMIN_DOMAIN` добавить `location = / { return 302 /admin/; }`)

---

## 4. Docker: чистая сборка с нуля

### 4.1 `.dockerignore` (новый, критично)

Сейчас контекст сборки — весь репозиторий (`remnawave-admin-main` ≈ 425 МБ, `bot` ≈ 49 МБ,
`web` ≈ 343 МБ). Без `.dockerignore` свежая сборка медленная и **запекает `.env`**.

Исключить: `.git`, `.env`, `.env.*` (кроме `.env.example`), `Fin/`, `remnawave-admin-main/`,
`bot/`, `ai-support/`, `docs/`, `.agents/`, `.kilo/`, `.claude/`, `*.png` в корне,
`web/frontend/node_modules/`, `web/frontend/dist/` (для web-образа dist собирается),
`deploy/backups/`, `db/postgres/` (кроме нужного образам), `install.lock`.

### 4.2 `deploy/Dockerfile.web` (новый, multi-stage)

```dockerfile
FROM node:20-alpine AS build
WORKDIR /src
COPY web/frontend/package.json web/frontend/package-lock.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npm run build                 # dist, base '/admin/' уже в vite.config.ts

FROM nginx:1.27-alpine
COPY .docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY public/ /var/www/html/public/
COPY --from=build /src/dist /var/www/html/web/frontend/dist/
```

- `npm ci` использует существующий `package-lock.json`;
- образ `web` самодостаточен: SPA + статика `public/`, без bind-mount репозитория;
- `uploads_data` монтируется поверх `/var/www/html/public/uploads`.

### 4.3 `web/backend/Dockerfile`

- **удалить** `COPY .env /app/.env` (строка 28) — источник поломки на чистом клоне;
- переменные приходят только через `env_file: .env` в compose;
- добавить `COPY tools/ /app/tools/` не нужно, пока `api` монтирует репозиторий;
- healthcheck остаётся `python -c urllib…/api/health`.

### 4.4 Корневой `Dockerfile`

Оставить php:8.1-fpm, но:
- `.dockerignore` гарантирует, что `.env` и мусор не попадают в образ;
- `COPY . .` оставить (образ `app` самодостаточен), `public/uploads` уже chown'ится;
- entrypoint — см. п. 6.

### 4.5 `deploy/compose.install.yml` (новый)

Сервисы: `caddy`, `web`, `app`, `api`, `db`, `migrate`. Обязательных переменных, кроме
доменов для Caddy, нет — везде `${VAR:-default}`.

```yaml
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    env_file: .env
    ports: ["80:80", "443:443", "443:443/udp"]
    volumes:
      - ./deploy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on: [web]

  web:
    build:
      context: .
      dockerfile: deploy/Dockerfile.web
    restart: unless-stopped
    volumes:
      - uploads_data:/var/www/html/public/uploads
    depends_on: [app, api]
    # портов наружу нет — только caddy

  app:
    build: .
    restart: unless-stopped
    env_file: .env
    depends_on:
      db: { condition: service_healthy }
      migrate: { condition: service_completed_successfully }
    volumes:
      - uploads_data:/var/www/html/public/uploads
      - /var/run/docker.sock:/var/run/docker.sock   # backup agent
    healthcheck:
      test: ["CMD", "php-fpm", "-t"]

  api:
    build: { context: ., dockerfile: web/backend/Dockerfile }
    restart: unless-stopped
    env_file: .env
    depends_on:
      db: { condition: service_healthy }
      migrate: { condition: service_completed_successfully }
    volumes:
      - .:/var/www/html            # RW: templates/, tools/, nodes_stats.json
      - uploads_data:/var/www/html/public/uploads
      - backup_data:/var/lib/hexaveil/backups
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]

  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME:-cms}
      POSTGRES_USER: ${DB_USER:-cms}
      POSTGRES_PASSWORD: ${DB_PASS:?DB_PASS is required}
    command: ["postgres", "-c", "log_min_messages=warning"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      # initdb-каталог НЕ монтируем: схему применяет migrate (единая точка)
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-cms} -d ${DB_NAME:-cms}"]

  migrate:
    image: postgres:16-alpine
    env_file: .env
    depends_on:
      db: { condition: service_healthy }
    volumes:
      - ./db:/db:ro
      - ./deploy/migrate.sh:/migrate.sh:ro
    entrypoint: ["/bin/sh", "/migrate.sh"]
    restart: "no"

volumes:
  pgdata:
  uploads_data:
  backup_data:
  caddy_data:
  caddy_config:
```

`DB_PASS` — единственная «жёсткая» переменная, её всегда генерирует установщик.
`docker compose -f deploy/compose.install.yml config` должен проходить без доменов.

### 4.6 `docker-compose.prod.yml`

Оставить для legacy host-nginx сценария, но:
- `ports` для `web`: `${CMS_BIND_IP:-127.0.0.1}:${CMS_HTTP_PORT:-3000}:80` (убрать
  обязательность `CMS_BIND_IP`, иначе `docker compose up` падает);
- добавить сервис `migrate` (тот же, что в install-compose);
- `api` mount `.:/var/www/html` оставить RW (diagnostics/themes);
- `web` bind-mount `.:/var/www/html:ro` можно оставить для legacy, но новый install-compose
  его не использует.

---

## 5. БД: bootstrap и миграции

### 5.1 Механизм: ledger + psql-цикл

Таблица:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text PRIMARY KEY,
    checksum   text,
    applied_at timestamptz NOT NULL DEFAULT now()
);
```

`deploy/migrate.sh` (в контейнере `postgres:16-alpine`, монтируется `/db`):

1. Ждать `pg_isready` (на случай гонки, хотя есть `depends_on: service_healthy`).
2. Создать `schema_migrations`.
3. **Bootstrap схемы**: если `to_regclass('public.users') IS NULL` → применить
   `db/postgres/init/01-schema.sql`, записать версию. Если `users` уже есть — **не выполнять**
   (в файле есть `CREATE TRIGGER`, повторный запуск упадёт).
4. Применить по порядку:
   - `db/postgres/migrations/*.sql` (003, 004 — сначала),
   - `db/migrations/*.sql` (даты — затем).
   Для каждого файла: если `version` уже в ledger — skip; иначе
   `psql -v ON_ERROR_STOP=1 -f "$f"`, затем `INSERT … ON CONFLICT DO NOTHING`.
   Ошибка → abort с именем файла и кодом 1; `restart: "no"` + `service_completed_successfully`
   не пустят `app/api` к сломанной БД.
5. `checksum` = `sha256sum` файла; несовпадение у применённой версии — warning
   (не abort), чтобы правки комментариев не блокировали деплой.

### 5.2 Идемпотентность SQL-файлов (обязательная подготовка)

Ledger не спасает при **adopt-existing** (у прода ledger пуст). Поэтому все файлы
нормализуются к идемпотентному виду:

- `db/postgres/init/01-schema.sql`: все `CREATE TRIGGER` обернуть в
  `DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = '…') THEN CREATE TRIGGER …; END IF; END $$;`
- `db/migrations/2026-09-27-app-logs-expand.sql` — уже DO-блоки, проверить.
- `2026-10-08-{posts-metadata,pages-status}.sql` — `ADD COLUMN IF NOT EXISTS`, ок.
- `2026-10-08-fix-sequences.sql` — `setval(max(id))`, ок.
- `2026-10-11-user-preferences-text.sql` — проверить/добавить guard.
- `2026-11-21-backup-system.sql` — `CREATE TABLE/INDEX IF NOT EXISTS`, ок.
- `db/postgres/migrations/003-changelog-entries.sql`, `004-support-foundation.sql` —
  проверить `CREATE TABLE IF NOT EXISTS` для всех объектов, включая индексы/триггеры.

### 5.3 Что остаётся в app-startup DDL

`web/backend/main.py` (lifespan) продолжает best-effort создавать
`user_columns`, changelog, docs, support, backup schema. Это **safety net** для старых
установок; он должен оставаться идемпотентным. `migrate` — единственный источник истины
для «файловых» миграций; startup DDL не удаляем (не ломаем существующий прод).

### 5.4 Adopt-existing

`install.sh --adopt-existing`:
- `.env` существующей установки переиспользуется (секреты не меняются);
- `pgdata` не пересоздаётся; `docker compose down -v` не вызывается никогда;
- перед `migrate` делается `pg_dump`;
- `01-schema.sql` пропускается (users есть);
- ledger создаётся пустым → все файловые миграции выполняются с guard'ами
  (поэтому п. 5.2 обязателен);
- admin bootstrap видит существующего `admin` с непустым хешем → **ничего не меняет**
  (кроме явного `--reset-admin-password`).

---

## 6. Исправления для корректного первого запуска

| Проблема | Файл | Решение |
|---|---|---|
| Seed `admin`, entrypoint ищет `admn` | `db/postgres/init/01-schema.sql`, `docker-entrypoint.sh` | Канонический логин `admin`; entrypoint **удаляет** блок смены пароля полностью; bootstrap — отдельный скрипт |
| Хардкод пароля в entrypoint | `docker-entrypoint.sh` | Удалить; пароль только через `deploy/bootstrap_admin.php` |
| Разные fallback-ключи шифрования | `config/config.php:40`, `web/backend/core/crypto.py:17` | Один литерал `hexacms-default-key-change-me` в обоих; прод всегда с `APP_ENCRYPTION_KEY` |
| `SITE_URL` всегда из `HTTP_HOST` | `config/config.php:20` | `getenv('SITE_URL') ?: ($__scheme.'://'.($_SERVER['HTTP_HOST'] ?? 'localhost'))`; установщик задаёт `SITE_URL` |
| `X-Forwarded-Proto` затирается внутренним nginx | `.docker/nginx/default.conf` | `map $http_x_forwarded_proto $hv_proto` + `fastcgi_param HTTP_X_FORWARDED_PROTO` |
| CORS только localhost | `web/backend/core/config.py`, `.env` | Установщик пишет `CORS_ORIGINS` из доменов; backend fallback: если пусто — из `CMS_PUBLIC_URL` + `SITE_URL` |
| `COPY .env` ломает fresh clone | `web/backend/Dockerfile:28` | Удалить строку |
| `CMS_BIND_IP` обязателен в prod | `docker-compose.prod.yml:38` | `:-127.0.0.1` + `CMS_HTTP_PORT:-3000` |
| entrypoint ждёт БД бесконечно | `docker-entrypoint.sh:7` | Таймаут 60 попыток → понятная ошибка |
| `install.lock` в образе | `docker-entrypoint.sh:13` | Оставить; `install.lock` в `.gitignore` уже есть |

`deploy/bootstrap_admin.php` (installer helper, не часть роутов):
- читает `ADMIN_LOGIN`, `ADMIN_PASSWORD`, `ADMIN_EMAIL` из env;
- `SELECT password FROM users WHERE login = :login`;
- если строки нет → `INSERT … role='admin'`;
- если хеш равен placeholder `$2y$10$change_this_to_a_real_bcrypt_hash` или передан
  `--reset-admin-password` → `UPDATE … password = password_hash(...)`;
- иначе → «admin exists, password unchanged»;
- всегда `exit 0` при успехе, `exit 1` при ошибке БД/хеширования.

---

## 7. Файлы: что создать и что изменить

### Новые

| Путь | Назначение |
|---|---|
| `deploy/install.sh` | установщик (п. 2), режимы clone/curl, prompts из `/dev/tty` |
| `deploy/compose.install.yml` | прод-стек: caddy/web/app/api/db/migrate |
| `deploy/Dockerfile.web` | multi-stage node build → nginx |
| `deploy/Caddyfile` | два домена, TLS, 64 МБ, WS |
| `deploy/migrate.sh` | ledger + psql-цикл |
| `deploy/bootstrap_admin.php` | идемпотентный админ |
| `deploy/nginx-host/site.conf.template` | fallback server-block |
| `deploy/nginx-host/admin.conf.template` | fallback server-block |
| `.dockerignore` | контекст сборки, исключить `.env` и тяжёлые каталоги |
| `docs/plans/2026-11-26-one-command-deploy.md` | этот план |
| `docs/decisions/ADR-006-one-command-deploy.md` | ADR (п. 10) |

### Изменяемые

| Путь | Что |
|---|---|
| `web/backend/Dockerfile` | удалить `COPY .env` |
| `docker-entrypoint.sh` | убрать пароль/`admn`, добавить таймаут БД |
| `config/config.php` | `SITE_URL` из env; единый fallback ключа |
| `web/backend/core/crypto.py` | оставить fallback, синхронизировать с PHP (литерал) |
| `web/backend/core/config.py` | CORS fallback из `CMS_PUBLIC_URL`/доменов |
| `.docker/nginx/default.conf` | `server_name _`, `map` для proto, fastcgi param |
| `docker-compose.prod.yml` | `CMS_BIND_IP:-127.0.0.1`, `CMS_HTTP_PORT`, сервис `migrate` |
| `db/postgres/init/01-schema.sql` | идемпотентные триггеры |
| `db/migrations/*.sql`, `db/postgres/migrations/*.sql` | guard'ы идемпотентности |
| `deploy.sh` | убрать фиксированный список миграций и hardcoded `hexacms_web`; `docker compose up -d` + `exec web nginx -s reload` |
| `.env.example` | новые ключи: `SITE_DOMAIN`, `ADMIN_DOMAIN`, `ACME_EMAIL`, `ADMIN_LOGIN`, `SITE_URL`, `CMS_HTTP_PORT` |
| `.env.prod` | привести к генерируемому шаблону (без плейсхолдеров-кириллицы) |
| `DEPLOY.md` | новый quickstart (2 команды), legacy-раздел, fallback |
| `docs/CODEBASE_INDEX.md` | deployment/runtime-раздел (п. 10) |
| `PROJECT.md` | топология, домены, порты, путь установки, ledger |

`web/frontend/dist` остаётся в git на переходный период (dev-compose его использует),
но **источник истины для прода** — образ `deploy/Dockerfile.web`. Отдельным коммитом
после проверки dev-потока можно добавить `dist/` в `.gitignore`.

---

## 8. Проверка (fresh-VM dry run)

### 8.1 До установки

- [ ] `docker compose -f deploy/compose.install.yml config` без ошибок интерполяции.
- [ ] `shellcheck deploy/install.sh deploy/migrate.sh` (если доступен).
- [ ] `docker build -f deploy/Dockerfile.web .` собирается; `dist/index.html` внутри.
- [ ] `docker build -f web/backend/Dockerfile .` **не** требует `.env`.
- [ ] `.dockerignore` реально уменьшает контекст (`docker build` лог: < 50 МБ).

### 8.2 Чистая VM (Ubuntu 24.04, без Docker)

1. `git clone … /opt/hexaveil-cms && cd /opt/hexaveil-cms && sudo bash deploy/install.sh`.
2. Установщик сам ставит Docker, поднимает стек, печатает пароль.
3. `docker compose -f deploy/compose.install.yml ps` → `db`, `caddy`, `web`, `app`, `api`
   `healthy`; `migrate` — `exited (0)`.
4. `curl -fsS https://admin.<domain>/api/health` → `{"status":"ok"…}` (или фактический контракт).
5. `curl -sI https://<site-domain>/` → `200`.
6. `curl -sI https://admin.<domain>/` → `302` на `/admin/`.
7. `curl -sI https://admin.<domain>/admin/` → `200`, `text/html`.
8. Логин в UI `admin` / пароль из сводки → дашборд открывается.
9. `openssl s_client -connect admin.<domain>:443 -servername admin.<domain>` →
   валидный сертификат, срок ≥ 80 дней.
10. WebSocket: страница Support → в DevTools `101 Switching Protocols` на
    `/api/support/ws`.
11. Upload: файл 60 МБ проходит, 70 МБ → `413`.
12. `POST`-проверка PHP-bridge путей: `/admin/diagnostics/api/data`,
    `/admin/finance/api/...`, `/admin/settings/save-preference` отвечают JSON, не 404.
13. Повторный `sudo bash deploy/install.sh --non-interactive`:
    - `.env` не изменился (diff секретов пуст);
    - пароль админа не изменился;
    - данные (пост/настройка) на месте;
    - `migrate` снова `exited (0)`, ledger не растёт.
14. `docker compose … down && up -d` → данные сохранились (тома).
15. Adopt-existing на копии прод-данных: `pg_dump` до/после совпадает по `users`;
    миграции не падают; админ не перезаписан.

### 8.3 Откат

- код: `git checkout <prev>` + `up -d --build`;
- БД: восстановление из `deploy/backups/pre-migrate-<ts>.sql`;
- полный снос (только вручную): `docker compose down -v` — установщик этого не делает.

---

## 9. Риски и откат

| Риск | Митигация |
|---|---|
| Порт 80/443 занят host nginx (текущий прод) | установщик abort'ит с PID; `--behind-proxy` → `127.0.0.1:3000`, генерирует nginx-блоки |
| `docker compose down -v` по ошибке | установщик никогда не вызывает `-v`; README/сводка предупреждают |
| Повторный запуск меняет секреты | генерация только при отсутствии ключа; `.env` бэкапится |
| Adopt-existing ломает прод-БД | `pg_dump` перед migrate; ledger + идемпотентные SQL; `users` guard |
| ACME rate limit при ошибке DNS | DNS-пречек, `CADDY_ACME_CA` staging, TLS-ожидание с warning вместо abort |
| `.env` попадает в образ | `.dockerignore` + удаление `COPY .env`; проверить `docker run --rm image ls -a /app` |
| Docker socket в `app` = root на хосте | оставить (нужен backup-agent), зафиксировать в ADR как принятый риск; не публиковать API наружу |
| `api` RW-mount репозитория | технический долг; в ADR зафиксировать и запланировать выделение `templates/`+`tools/` в отдельные mount'ы |
| Caddy недоступен/заблокирован | единственный fallback — host nginx + certbot (п. 3.5) |
| Старый `dist` в git расходится с образом | источник истины — образ; в DEPLOY.md явно указано |

---

## 10. Документация по Definition of Done

### `docs/CODEBASE_INDEX.md` — добавить раздел «Deployment & Runtime»

- новые compose-файлы и сервисы (`caddy`, `migrate`), порты;
- реестр ENV: `SITE_DOMAIN`, `ADMIN_DOMAIN`, `ACME_EMAIL`, `ADMIN_LOGIN`, `SITE_URL`,
  `CMS_HTTP_PORT`, `CADDY_ACME_CA`; правила деривации `CORS_ORIGINS`;
- `deploy/install.sh` — флаги и режимы (`--behind-proxy`, `--adopt-existing`,
  `--reset-admin-password`, `--non-interactive`);
- `deploy/migrate.sh` + `schema_migrations` (поля, порядок применения);
- `deploy/bootstrap_admin.php` (контракт env/поведение);
- Dockerfile-контракты: `deploy/Dockerfile.web`, отсутствие `.env` в API-образе;
- nginx-контракт: `map $http_x_forwarded_proto`, bridge-пути, WS.

### `PROJECT.md`

- новая топология: Caddy 80/443 → `web:80` → `app:9000` / `api:8000`;
- два домена и их роли;
- путь установки `/opt/hexaveil-cms`, тома, ledger;
- legacy-прод (host nginx → 127.0.0.1:3000) и путь его перевода на новый стек;
- fallback host-nginx.

### `docs/decisions/ADR-006-one-command-deploy.md`

Зафиксировать:
1. Caddy-in-compose вместо host nginx+certbot (и единственный fallback);
2. SPA собирается в образе, `dist` в git — не источник истины для прода;
3. `migrate`-сервис + ledger вместо фиксированного списка в `deploy.sh`;
4. канонический логин `admin`, bootstrap вне entrypoint;
5. принятый технический долг: RW-mount репозитория в `api`, docker.sock в `app`.

`DEPLOY.md` переписать в стиле quickstart (2 команды) + раздел «Legacy / behind proxy» +
раздел «Troubleshooting» (порты, DNS, TLS, пароль).

---

## 11. Порядок реализации для `coder`

1. **Гигиена сборки:** `.dockerignore`, удалить `COPY .env` из `web/backend/Dockerfile`,
   проверить `docker build` обоих образов на чистом клоне.
2. **Сборка SPA:** `deploy/Dockerfile.web`, `deploy/compose.install.yml` (пока без caddy),
   проверить, что `web` отдаёт `/admin/` из собранного dist.
3. **Прокси:** `deploy/Caddyfile`, правки `.docker/nginx/default.conf` (`map` proto,
   `server_name _`), проверить `X-Forwarded-Proto` и `SITE_URL` через `php -r`.
4. **БД:** идемпотентность SQL, `deploy/migrate.sh`, сервис `migrate`,
   прогнать на пустом томе и на копии прода.
5. **Админ и entrypoint:** `deploy/bootstrap_admin.php`, чистка `docker-entrypoint.sh`.
6. **Конфиги:** `SITE_URL`, единый fallback-ключ, CORS fallback.
7. **Установщик:** `deploy/install.sh` (флаги, TTY, идемпотентность, сводка).
8. **Legacy:** правки `docker-compose.prod.yml`, `deploy.sh`, `.env.example`, `.env.prod`.
9. **Dry run** по чек-листу п. 8 на чистой VM.
10. **Документация:** `CODEBASE_INDEX.md`, `PROJECT.md`, `ADR-006`, `DEPLOY.md`.
11. Коммит по Conventional Commits, например:
    `feat(deploy): установка CMS одной командой — Caddy, сборка SPA в образе, ledger миграций`.

**Критерий готовности:** на чистой VM установка проходит ровно двумя командами (clone +
installer), TLS валиден, админ входит, повторный запуск не меняет секреты и данные,
`/api/health` = 200, `docs/CODEBASE_INDEX.md` и `PROJECT.md` отражают фактическое состояние.
