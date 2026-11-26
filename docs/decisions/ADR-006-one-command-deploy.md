# ADR-006. Установка CMS одной командой: Caddy, образ SPA, ledger миграций

- **Статус:** принято
- **Дата:** 2026-11-26
- **Связано:** `docs/plans/2026-11-26-one-command-deploy.md`, ADR-005 (бэкапы)

## Контекст

До этого установка на чистый сервер была ручной: скопировать репозиторий,
заполнить `.env`, `cp docker-compose.prod.yml docker-compose.yml`, поднять
контейнеры, отдельно поставить certbot и править nginx, вручную доставить
собранный `dist`. На чистом клоне всплывали системные ошибки:

- `web/backend/Dockerfile` копировал `.env` в образ (ломает fresh clone);
- `docker-entrypoint.sh` содержал хардкод пароля и искал логин `admn`,
  тогда как `01-schema.sql` создаёт `admin`;
- внутренний nginx жёстко ставил `X-Forwarded-Proto $scheme`, из-за чего
  PHP за прокси строил `http://`-ссылки;
- CORS был зашит на `localhost`;
- `CMS_BIND_IP` был обязателен, иначе `docker compose up` падал;
- entrypoint ждал БД бесконечно;
- `deploy.sh` содержал фиксированный список миграций и хардкод `hexacms_web`.

Цель — на чистом Ubuntu/Debian: клон репозитория + один запуск установщика;
автоматический TLS, БД, миграции, админ; повторный запуск безопасен.

## Решение

### 1. Caddy 2 в compose; host nginx + certbot — единственный fallback

`deploy/compose.install.yml` содержит сервис `caddy:2-alpine`, который
публикует только 80/443 (и 443/udp) и терминирует TLS с автоматическим ACME.
Маршрутизация приложения не дублируется: Caddy проксирует на внутренний
`web:80`, где остаются все правила PHP/FastAPI (`map $http_x_forwarded_proto
$hv_proto`, bridge-пути, WebSocket).

Два домена: `SITE_DOMAIN` (публичный сайт) и `ADMIN_DOMAIN` (SPA `/admin/` +
`/api/*`); корень админ-домена отдаёт `302 → /admin/`. Лимит тела запроса
64 МБ согласован во всех слоях.

Fallback ровно один — `install.sh --behind-proxy`: `web` публикуется на
`127.0.0.1:${CMS_HTTP_PORT:-3000}`, установщик рендерит два server-блока для
host-nginx и получает сертификаты `certbot certonly --webroot`. Сертификаты
запрашиваются в два этапа: сначала HTTP-only bootstrap-конфиг с ACME-webroot
`/var/www/certbot`, затем TLS-блоки — только когда `fullchain.pem` есть для
**обоих** доменов. Это позволяет пройти `nginx -t` на пустом хосте.

### 2. SPA собирается в образе; закоммиченный `dist` — не источник истины

`deploy/Dockerfile.web` — multi-stage: `node:20-alpine` собирает SPA из
`web/frontend/` (`npm ci` + `npm run build`, `base: '/admin/'` уже в
`vite.config.ts`), затем `nginx:1.27-alpine` получает `public/`, вендорный
`.docker/nginx/default.conf` и собранный `dist`. Образ `web` самодостаточен,
репозиторий в него не монтируется.

`web/frontend/dist` остаётся в git на переходный период (его использует
dev-compose), но для прода истина — образ. Рассинхронизация старого `dist`
в git с образом не является дефектом деплоя.

### 3. One-shot `migrate` + ledger `schema_migrations` вместо списка в `deploy.sh`

Сервис `migrate` (`postgres:16-alpine`, `restart: "no"`) монтирует `db/` и
`deploy/migrate.sh` только на чтение. Скрипт:

1. ждёт `pg_isready` ≤ 60 с;
2. создаёт `schema_migrations(version, checksum, applied_at)`;
3. применяет `db/postgres/init/01-schema.sql` **только** если `public.users`
   отсутствует (иначе adopt-existing уже имеет схему);
4. применяет `db/postgres/migrations/*.sql`, затем `db/migrations/*.sql`
   (порядок имён), пропуская записи из ledger;
5. пишет sha256; расхождение контрольной суммы — предупреждение, ошибка SQL —
   код 1.

`app` и `api` ждут `migrate` через `service_completed_successfully`, поэтому
к сломанной БД не поднимаются. `deploy.sh` больше не перечисляет миграции,
а `docker-compose.prod.yml` больше не монтирует initdb-каталог.

### 4. Канонический логин `admin`; bootstrap вне entrypoint

Единственный источник создания/сброса администратора —
`deploy/bootstrap_admin.php` (installer helper, не маршрут). Контракт:
`ADMIN_LOGIN` (по умолчанию `admin`), `ADMIN_PASSWORD`, `ADMIN_EMAIL`,
`FORCE_RESET=1`; коды выхода `0` (готово), `1` (БД/хеширование), `2` (нужен
пароль). Placeholder-хеш из `01-schema.sql` распознаётся и заменяется.

`docker-entrypoint.sh` больше не трогает пароли и не содержит секретов; он
лишь ждёт БД (60 попыток). Пароль задаёт установщик, он печатается один раз,
при генерации сохраняется в `.install-credentials` (0600, root) и удаляется
из `.env` после успешного bootstrap.

### 5. Принятый технический долг

- **`api` монтирует репозиторий RW** (`..:/var/www/html`): нужны `templates/`,
  `tools/`, `nodes_stats.json`. Планируемое сужение — отдельные mount'ы только
  для этих путей.
- **`app` монтирует `docker.sock`** — нужен backup-агенту (inline-бэкап CMS).
  Это root-equivalent доступ; API агента не публикуется наружу.
- **`npm ci --force`** в `deploy/Dockerfile.web`: в lockfile остались
  `"extraneous": true` записи чужих платформ (`@esbuild/netbsd-arm64` и др.),
  из-за которых обычный `npm ci` падает с `EBADPLATFORM` на linux/x64.
  Убрать `--force` после перегенерации `package-lock.json`.

### 6. Секреты и повторный запуск

Секреты (`DB_PASS`, `JWT_SECRET`, `APP_ENCRYPTION_KEY`) генерируются только
когда ключа нет в `.env`; `.env` пишется атомарно (`umask 077`, временный
файл + `mv`, `chmod 600`), старая версия — `.env.bak.<ts>`. Домены на повторном
запуске меняются только с `--reconfigure-domains`, пароль — только с
`--reset-admin-password`. Установщик никогда не вызывает `down -v`.

## Последствия

**Плюсы**

- установка — две команды (clone + installer), без пакетов и правок nginx на хосте;
- автоматический TLS и renewal без cron/certbot в основном пути;
- идемпотентность: повторный запуск не меняет секреты, тома, БД и пароль;
- ledger делает миграции отслеживаемыми, а adopt-existing — предсказуемым;
- один вход (Caddy) и одна точка маршрутизации (внутренний nginx);
- стабильные имена томов `hexaveil_*` (project name закреплён в compose).

**Минусы / риски**

- `app` с `docker.sock` = root на хосте при компрометации контейнера;
- RW-монтирование репозитория в `api` позволяет коду менять файлы хоста;
- `npm ci --force` может скрыть реальную несовместимость lockfile;
- Caddy — новая зависимость; при его недоступности остаётся только
  host-nginx fallback (без третьего варианта);
- `--behind-proxy` требует установленного `certbot`; установщик не ставит его молча.

## Откат

- **Код:** `git checkout <предыдущий коммит>` → `docker compose --env-file .env
  -f deploy/compose.install.yml up -d --build`.
- **БД:** восстановить `deploy/backups/pre-migrate-<ts>.sql` (создаётся перед
  миграциями при существующей схеме или `--adopt-existing`).
- **Полный снос** — только вручную: `docker compose --env-file .env
  -f deploy/compose.install.yml down -v` уничтожает тома `hexaveil_*`.
  Установщик этого не делает никогда.

## Альтернативы

- **Host nginx + certbot как основной путь** — отвергнут: требует пакетов и
  правок `/etc/nginx` на каждом сервере, ломает «две команды».
- **Traefik вместо Caddy** — отвергнут: больше конфигурации для двух доменов
  без выигрыша в данном сценарии.
- **Миграции фиксированным списком в `deploy.sh`** — отвергнут: не отслеживает
  применённое и не переносим на adopt-existing.
- **Bootstrap админа в entrypoint** — отвергнут: секрет в образе/окружении и
  невозможность идемпотентного сброса.
