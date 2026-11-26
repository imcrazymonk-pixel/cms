# Деплой HexaVeil CMS — установка одной командой

Установщик `deploy/install.sh` сам генерирует `.env`, поднимает PostgreSQL,
применяет миграции по ledger, собирает SPA в образе, запускает стек
(Caddy → web → app/api) и создаёт администратора. Архитектурное решение —
`docs/decisions/ADR-006-one-command-deploy.md`.

- Каталог установки по умолчанию: `/opt/hexaveil-cms`
- Compose-файл прода: `deploy/compose.install.yml` (project name `hexaveil`)
- Нужны: Debian/Ubuntu, root, `curl`, `openssl`; `git` — для режима `curl | bash`

---

## 1. Быстрый старт

Репозиторий: **https://github.com/imcrazymonk-pixel/cms** (ветка `main`, публичный).

### Одна команда (`curl | bash`)

```bash
curl -fsSL https://raw.githubusercontent.com/imcrazymonk-pixel/cms/main/deploy/install.sh \
  | sudo bash -s -- --site-domain example.com --admin-domain admin.example.com \
                     --acme-email ops@example.com
```

В этом режиме репозиторий клонируется в `--dir` (по умолчанию
`/opt/hexaveil-cms`), а вопросы читаются из `/dev/tty`, не из stdin.

### Клонирование (2 команды)

```bash
git clone https://github.com/imcrazymonk-pixel/cms.git /opt/hexaveil-cms
cd /opt/hexaveil-cms && sudo bash deploy/install.sh
```

Установщик спросит `SITE_DOMAIN`, `ADMIN_DOMAIN`, `ACME_EMAIL` и пароль
администратора (Enter — сгенерировать). Логин по умолчанию `admin`.

Без вопросов:

```bash
cd /opt/hexaveil-cms && sudo bash deploy/install.sh \
  --site-domain example.com --admin-domain admin.example.com \
  --acme-email ops@example.com --non-interactive
```

Домены должны быть разными и уже указывать A-записями на сервер; ACME нужен
входящий TCP 80.

---

## 2. Флаги

| Флаг | Env | Назначение |
|------|-----|------------|
| `--site-domain DOMAIN` | `SITE_DOMAIN` | публичный сайт |
| `--admin-domain DOMAIN` | `ADMIN_DOMAIN` | SPA `/admin/` + `/api/*` |
| `--acme-email EMAIL` | `ACME_EMAIL` | ACME-аккаунт (Let's Encrypt) |
| `--admin-login LOGIN` | `ADMIN_LOGIN` | по умолчанию `admin` |
| `--admin-password PASS` | `ADMIN_PASSWORD` | иначе сгенерировать |
| `--site-name NAME` | `SITE_NAME` | заголовок сайта, по умолчанию `HexaVeil` |
| `--repo URL` | `HEXAVEIL_REPO_URL` | git-URL для режима `curl \| bash` |
| `--dir PATH` | `INSTALL_DIR` | каталог клонирования (по умолчанию `/opt/hexaveil-cms`) |
| `--behind-proxy` / `--proxy=host-nginx` | — | не занимать 80/443, слушать `127.0.0.1:3000` |
| `--adopt-existing` | — | сохранить секреты/данные, `pg_dump` перед миграциями |
| `--reset-admin-password` | — | сменить пароль существующего админа |
| `--reconfigure-domains` | — | разрешить смену доменов на повторном запуске |
| `--no-install-docker` | — | не устанавливать Docker автоматически |
| `--non-interactive` | — | без вопросов; обязательные флаги должны быть заданы |
| `--dry-run` | — | проверки + `.env` + валидация Caddyfile, без запуска |
| `--help`, `-h` | — | справка |

В интерактивном режиме спрашиваются только домены, email и пароль. В
`--non-interactive` отсутствие `--site-domain`, `--admin-domain` или
`--acme-email` — ошибка (кроме повторного запуска, когда значения берутся
из существующего `.env`).

Что делает установщик до изменений: проверяет root, ОС, Docker/Compose,
занятость портов (80/443, либо 3000), ≥ 5 ГБ диска, ≥ 1 ГБ RAM (warning),
DNS-записи (warning), формат доменов/email. Docker при отсутствии ставится
с `https://get.docker.com`, если не указан `--no-install-docker`.

`--dry-run` дополнительно валидирует `deploy/Caddyfile` через
`caddy:2-alpine` и не запускает контейнеры.

---

## 3. `--behind-proxy` (host nginx уже на 80/443)

```bash
sudo bash deploy/install.sh --behind-proxy \
  --site-domain example.com --admin-domain admin.example.com \
  --acme-email ops@example.com
```

- `web` публикуется только на `127.0.0.1:${CMS_HTTP_PORT:-3000}:80`
  (override `deploy/compose.behind-proxy.yml`), Caddy не запускается;
- установщик кладёт `00-upgrade-map.conf` в `/etc/nginx/conf.d/` и рендерит
  `hexaveil-site.conf` / `hexaveil-admin.conf` из `deploy/nginx-host/*`;
- сертификаты получаются в два этапа: сначала HTTP-only
  `hexaveil-bootstrap.conf` с ACME-webroot `/var/www/certbot`, затем
  `certbot certonly --webroot -d <site> -d <admin>`; TLS-блоки включаются
  только когда `fullchain.pem` есть для обоих доменов;
- `certbot` молча не устанавливается. Если его нет, остаётся bootstrap-конфиг
  и печатается команда для ручного запуска; повторный запуск установщика
  безопасно доводит переключение.

Команда для ручного получения сертификатов:

```bash
sudo certbot certonly --webroot -w /var/www/certbot \
  -d example.com -d admin.example.com --email ops@example.com --agree-tos -n
sudo bash deploy/install.sh --behind-proxy
```

Повторный запуск не перезаписывает nginx-конфиг без маркера
`# managed by hexaveil install.sh`.

---

## 4. `--adopt-existing` (перевод существующей установки)

```bash
sudo bash deploy/install.sh --adopt-existing --non-interactive
```

- существующий `.env` переиспользуется, секреты не меняются;
- тома (`hexaveil_pgdata`) не пересоздаются, `down -v` не вызывается;
- перед `migrate` делается `pg_dump` в `deploy/backups/pre-migrate-<ts>.sql`;
- `init/01-schema.sql` пропускается (таблица `users` уже есть);
- ledger создаётся пустым, поэтому файловые миграции должны быть
  идемпотентны; уже применённые объекты пропускаются guard'ами;
- существующий `admin` с реальным хешем не меняется (только с
  `--reset-admin-password`).

Если на старом проде host nginx слушает 80/443 — добавьте `--behind-proxy`.

---

## 5. Повторный запуск и обновление

Повторный запуск идемпотентен:

- недостающие ключи дописываются в `.env`, существующие не меняются
  (старый файл — `.env.bak.<ts>`);
- `migrate` пропускает всё, что уже в `schema_migrations`;
- пароль админа не меняется без `--reset-admin-password`;
- домены не меняются без `--reconfigure-domains`;
- тома `hexaveil_*` не трогаются.

Обновление кода:

```bash
cd /opt/hexaveil-cms
git pull
sudo bash deploy/install.sh --non-interactive   # домены возьмутся из .env
```

Пересобрать образы и прогнать миграции без установщика:

```bash
docker compose --env-file .env -f deploy/compose.install.yml up -d --build
```

---

## 6. Что печатает установщик

В конце — сводка: `https://<site>`, `https://<admin>/admin/`, результат
health-проверки, логин, каталог, команды управления и напоминание, что
повторный запуск безопасен.

Пароль:

- сгенерирован — печатается **один раз** и пишется в
  `<каталог>/.install-credentials` (0600, root);
- задан пользователем — в файл не пишется;
- после успешного bootstrap строка `ADMIN_PASSWORD` удаляется из `.env`.

---

## 7. Управление

Из каталога установки:

```bash
sudo docker compose --env-file .env -f deploy/compose.install.yml ps
sudo docker compose --env-file .env -f deploy/compose.install.yml logs -f
sudo docker compose --env-file .env -f deploy/compose.install.yml logs -f caddy api app web
sudo docker compose --env-file .env -f deploy/compose.install.yml restart api
```

Повторно применить миграции вручную:

```bash
sudo docker compose --env-file .env -f deploy/compose.install.yml run --rm migrate
```

Тома (project name закреплён как `hexaveil`):

| Том | Что внутри |
|-----|-----------|
| `hexaveil_pgdata` | PostgreSQL |
| `hexaveil_uploads_data` | `public/uploads` (общий для `web`, `app`, `api`) |
| `hexaveil_backup_data` | локальные бэкапы CMS (`/var/lib/hexaveil/backups`) |
| `hexaveil_caddy_data` | сертификаты и ACME-аккаунт Caddy |
| `hexaveil_caddy_config` | автогенерируемый конфиг Caddy |

---

## 8. Legacy-стек (host nginx → 127.0.0.1:3000)

`docker-compose.prod.yml` + `deploy.sh` сохранены для текущего прода и
сценариев без Caddy. Это отдельный проект Compose (имя проекта берётся из
каталога, контейнеры `hexacms_*`, тома `postgres_data` / `uploads_data` /
`backup_data`).

```bash
cp docker-compose.prod.yml docker-compose.yml
docker compose up -d --build
sh deploy.sh          # up -d --build + nginx -s reload + health
```

- `web` публикуется на `${CMS_BIND_IP:-127.0.0.1}:${CMS_HTTP_PORT:-3000}:80`;
- снаружи — хостовый nginx на 80/443 (на текущем проде это `nginx-selfsteal`,
  его не трогать);
- сервис `migrate` есть и здесь; initdb-каталог не монтируется;
- контейнеры `hexacms_*` — legacy, не смешивайте их с проектом `hexaveil`.

Перевод на новый стек: остановить legacy, выполнить
`sudo bash deploy/install.sh --adopt-existing --behind-proxy` (если 80/443
заняты) или без флага (если Caddy может занять порты).

---

## 9. Troubleshooting

| Симптом | Что делать |
|---------|-----------|
| `port 80/443 is already in use` | `ss -ltnp \| grep -E ':(80\|443)\b'`; остановить слушателя или `--behind-proxy` |
| DNS warning / TLS не выдаётся | A-записи обоих доменов → IP сервера; входящий TCP 80 открыт; `logs caddy` |
| `TLS is not ready after 120s` | проверить DNS/порт 80, затем повторить установщик; ACME staging — раскомментировать `acme_ca` в `deploy/Caddyfile` |
| Забыли пароль админа | `sudo bash deploy/install.sh --reset-admin-password --admin-password 'новый'` (или интерактивно, без флага пароля) |
| `migrations failed` | `docker compose --env-file .env -f deploy/compose.install.yml logs migrate`; исправить SQL/данные, повторить `run --rm migrate` |
| `WARNING: checksum mismatch` | файл миграции изменили после применения; это предупреждение, не ошибка. Не удаляйте строку из ledger и не переименовывайте версию |
| 502 от Caddy/host nginx | `ps` + `logs web api app`; `migrate` должен быть `exited (0)`, `db` — `healthy` |
| 413 при загрузке | лимит 64 МБ: `request_body` Caddy, `client_max_body_size`, `MAX_UPLOAD_SIZE` |
| `--behind-proxy`, TLS не переключился | нет `certbot` или сертификата для одного из доменов; выполнить команду `certbot certonly` из лога и повторить установщик |

---

## 10. Секреты и приватность

- `.install-credentials` содержит пароль администратора — сохраните его в
  менеджер паролей и удалите: `sudo rm /opt/hexaveil-cms/.install-credentials`.
- `deploy/backups/` содержит полные дампы БД (`pre-migrate-*.sql`) — не
  коммитить, не публиковать, хранить с правами `0600`/`0700`.
- `.env` содержит `DB_PASS`, `JWT_SECRET`, `APP_ENCRYPTION_KEY` — `0600`,
  не коммитить, не копировать в образ (`.dockerignore` это гарантирует).
- Бэкапами в проде управляет подсистема CMS: **Инфраструктура → Бэкапы**
  (`docs/decisions/ADR-005-backup-system.md`).
