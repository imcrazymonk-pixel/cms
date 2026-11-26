# HexaVeil Full Stack — Project Overview

> **Актуальная архитектура.** Все фазы миграции (PHP SSR → React SPA → FastAPI) выполнены.
> Подробности архитектуры — `docs/ARCHITECTURE.md`, ключевые решения — `docs/decisions/ADR-*.md`.

---

## Что это за проект

VPN-сервис **HexaVeil**. Единая инфраструктура из 5 компонентов:

| Компонент | Технологии | URL / Доступ |
|-----------|-----------|--------------|
| **Публичный сайт** | PHP 8.1 (лендинг + блог) | `hexaveil.xyz` |
| **Админ-панель CMS** | React SPA + FastAPI | `hexaveil.xyz/admin/` |
| **Remnawave Panel** | Управление нодами/подписками | `panel.fortf.ru` |
| **7 Xray-нод** | VLESS+Reality / Hysteria2 / XHTTP | monoList.\* / pwrngers / zaqxs1 |
| **Bedolaga Bot + Cabinet** | Telegram-бот + личный кабинет | `@HexaVeil_bot` / `cabinet.fortf.ru` |

### Репозитории проекта

| Репозиторий | Путь | Назначение |
|------------|------|-----------|
| **NewWeb** (этот) | `C:\Users\Andre\Desktop\VPN\NewWeb` | CMS: публичный сайт + админка |
| **remnawave-admin-main** | `C:\Users\Andre\Desktop\VPN\remnawave-admin-main` (gitignored) | Эталон Remnawave, upstream: `github.com/Case211/remnawave-admin` |
| **ai-support** | `C:\Users\Andre\Desktop\VPN\NewWeb\ai-support` (gitignored) | Эталон техподдержки с ИИ (Telegram/Bedolaga/MiniShop), источник модулей для CMS, upstream: `github.com/tagashi666/ai-support` |
| **bot** | `C:\Users\Andre\Desktop\VPN\NewWeb\bot` (gitignored) | Существующий Telegram-бот HexaVeil (исходники), интегрируется в CMS |
| **Заглушка** | `C:\Users\Andre\Desktop\VPN\Заглушка` | Инфраструктура нод, decoy-страницы, конфиги |

---

## Архитектура CMS (NewWeb)

```
NewWeb/
├── index.php                 # Front-controller публичного сайта (PHP)
├── web/
│   ├── frontend/             # React SPA админки (Vite + TS + shadcn/ui)
│   │   └── dist/             # Сборка (коммитится в репо)
│   └── backend/              # FastAPI (JSON API для React)
├── core/                     # PHP-ядро публичного сайта
├── templates/themes/         # PHP-темы (hexaveil, default)
├── public/                   # Ассеты, uploads, дизайн-система
├── db/                       # Схема PostgreSQL, миграции
├── docs/                     # Документация, ADR, планы
├── docker-compose*.yml       # dev + prod
├── Dockerfile                # PHP 8.1-FPM
└── .docker/                  # Nginx + PHP конфиги
```

### Потоки запросов (прод)

```
браузер → hexaveil.xyz
  ├── /              → PHP (лендинг + блог) — core/ + templates/themes/hexaveil/
  ├── /admin/*       → React SPA (web/frontend/dist/)  
  └── /api/*         → FastAPI (web/backend/)
                       + bridge: /admin/finance/api/* → PHP
```

nginx-selfsteal (`network_mode: host`, порты 80/443) → reverse proxy на `hexacms_web` (:3000) → PHP-FPM / FastAPI.

### Стек CMS

| Слой | Технологии |
|------|-----------|
| **Публичный сайт** | PHP 8.1, vanilla, PostgreSQL 16 |
| **Фронтенд админки** | React 18 + TypeScript + Vite + Tailwind + shadcn/ui (Radix) |
| **Бэкенд админки** | FastAPI + SQLAlchemy async + PyJWT + Pydantic v2 + structlog |
| **Дизайн-система** | Remnawave-style: 6 пресетов, glass-эффекты, mesh-фон |
| **Инфраструктура** | Docker Compose (caddy / app / api / web / db / migrate) |

### Деплой CMS (2026-11-26)

Новый прод-стек — `deploy/compose.install.yml` (project name `hexaveil`) —
ставится одной командой на чистом Ubuntu/Debian: `sudo bash deploy/install.sh`.
Полный справочник — `DEPLOY.md`, решение — `docs/decisions/ADR-006-one-command-deploy.md`.

**Топология (Caddy-режим):**

```
Интернет ──► caddy :80/:443 (авто-TLS, ACME)
               ├── SITE_DOMAIN  ──► web:80 ──► app:9000 (PHP) / api:8000 (/api/*)
               └── ADMIN_DOMAIN ──► web:80 ──► / → 302 /admin/ (SPA)
                                              └─ /api/* → api:8000
db:5432 (postgres:16) ◄── app / api / migrate
migrate (one-shot) ──► ledger schema_migrations ──► app/api ждут exit 0
```

**Два домена:**

| Домен | Роль |
|-------|------|
| `SITE_DOMAIN` | публичный сайт (PHP: лендинг, блог, страницы) |
| `ADMIN_DOMAIN` | SPA `/admin/` + FastAPI `/api/*` + bridge-пути; корень → `302 /admin/` |

**Установка, данные, миграции:**

- путь по умолчанию `/opt/hexaveil-cms` (`--dir`), TLS — автоматический через Caddy;
- тома стабильны: `hexaveil_pgdata`, `hexaveil_uploads_data`, `hexaveil_backup_data`,
  `hexaveil_caddy_data`, `hexaveil_caddy_config`;
- `.env` — `0600`, секреты генерируются только при отсутствии; пароль админа —
  в `.install-credentials` (`0600`, удалить после сохранения);
- миграции: сервис `migrate` применяет `db/postgres/migrations/*.sql`, затем
  `db/migrations/*.sql`, учитывая версии в `schema_migrations` (sha256);
  `db/postgres/init/01-schema.sql` — только если таблицы `users` нет;
- обновление: `git pull && sudo bash deploy/install.sh --non-interactive`
  (секреты, тома, БД и пароль не меняются);
- существующая установка: `--adopt-existing` (переиспользует `.env`, делает
  `pg_dump` перед миграциями, никогда не вызывает `down -v`).

**Legacy-прод и fallback:**

- текущий прод — `docker-compose.prod.yml` + `deploy.sh`: host nginx (на проде
  `nginx-selfsteal`, порты 80/443) → `127.0.0.1:3000` → `web`; контейнеры
  `hexacms_*`, имя проекта Compose берётся из каталога. Перевод:
  `sudo bash deploy/install.sh --adopt-existing --behind-proxy`;
- fallback без Caddy — `--behind-proxy`: `web` публикуется только на
  `127.0.0.1:3000`, установщик рендерит server-блоки `deploy/nginx-host/*`,
  сертификаты — `certbot` в два этапа (ACME webroot → TLS-блоки).

---

## Инфраструктура нод

### Состав (7 нод)

| Нода | IP | Роль | Протоколы |
|------|----|------|-----------|
| `files.monolist.art` | 144.31.96.78 | DE-origin, CDN-релей | VLESS+Reality |
| `audio.monolist.art` | 31.77.128.251 | FI | VLESS+Reality |
| `photo.monolist.art` | 31.77.146.75 | NL | VLESS+Reality + Hysteria2 |
| `video.monolist.art` | 159.194.221.84 | RU (Beget) | VLESS+Reality |
| `data.monolist.art` | 162.217.248.186 | US | VLESS+Reality |
| `istra.pwrngers.ru` | 85.198.98.18 | VK CDN-релей | XHTTP |
| `vps.zaqxs1.ru` | 155.212.131.4 | Yandex CDN-релей | XHTTP |

### Панельный сервер (144.31.156.172)

- Remnawave Panel **3.4.3** на `panel.fortf.ru`
- Bedolaga Bot **v4.7.0** (`@HexaVeil_bot`) + Cabinet **v1.71.0** (`cabinet.fortf.ru`)
- SSH: порт 356, user `kilo`
- Caddy на домены: `panel.fortf.ru`, `bot.fortf.ru`, `cabinet.fortf.ru`, `admin.fortf.ru`

### Общие правила нод

- SSH: порт 356 (кроме data: 22), user `kilo`/`kilorules123`
- Всё в контейнере **remnanode** (host-network, Xray 26.7.28)
- Конфиг: `/opt/remnanode/docker-compose.yml`
- Decoy-nginx: на files/audio/video — docker `nginx-selfsteal`; на photo/data — системный nginx
- Reality: serverNames = decoy-домен, target = `127.0.0.1:9443`, xver: 1
- Сертификаты: acme.sh (admin@monolist.art) или certbot
- ufw: включён на всех; открыты 80, 443/tcp+udp, 2222, ssh-порт

---

## Bedolaga Bot + Cabinet

### Состояние (актуально)

- **Бот:** `@HexaVeil_bot`, v4.7.0, исходники `github.com/BEDOLAGA-DEV/remnawave-bedolaga-telegram-bot`
- **Кабинет:** `cabinet.fortf.ru`, v1.71.0, статика `/srv/cabinet`, источник `ghcr.io/bedolaga-dev/bedolaga-cabinet:latest`
- **Связка аккаунтов** — полностью реализована (Telegram, email, Google OAuth). Не хватает заметности: нужно добавить баннер-напоминание на главной кабинета.

### Интеграция в админку CMS (2026-10-10)

CMS проксирует Bedolaga Bot Web API (`/api/bedolaga/*`) и читает каталог тарифов из БД бота:

| Возможность | Путь в CMS | Источник |
|------------|-----------|----------|
| Дашборд бота (статистика, здоровье, тех. работы) | `/admin/#/bedolaga` | Bot Web API |
| Клиенты (CRUD, баланс, подписки, активность) | `/admin/#/bedolaga/customers` | Bot Web API |
| **Тарифы (каталог, цены, периоды, лимиты)** | `/admin/#/bedolaga/tariffs` | **БД бота (read-only)** |
| Промокоды | `/admin/#/bedolaga/promo` | Bot Web API |
| Маркетинг (кампании, рассылки, партнёры) | `/admin/#/bedolaga/marketing` | Bot Web API |
| Реферальная сеть | `/admin/#/bedolaga/referrals` | Bot Web API |

**Тарифы из БД:** у Bot Web API нет эндпоинта каталога тарифов (он живёт только в Cabinet API с админским JWT). Поэтому CMS читает таблицу `tariffs` из PostgreSQL бота напрямую — через **read-only** пользователя `cms_ro` (только SELECT, без записи). Соединение идёт через socat-мост `bot-db-cms-bridge` (systemd на панельном сервере, порт 5434, UFW разрешает только IP CMS-сервера).

**Что отдаёт `GET /api/bedolaga/tariffs`:**
- `name`, `description`, `panel_tag` — название, описание, тег панели
- `period_prices_list` — `[{days, price_kopeks, price_rubles}]` — цены за периоды
- `traffic_limit_gb`, `device_limit` — лимиты трафика и устройств
- `is_trial_available`, `trial_duration_days` — триал
- `is_daily`, `daily_price_kopeks` — дневной тариф
- `custom_days_enabled`, `price_per_day_kopeks` — произвольный период
- `is_active`, `is_highlighted`, `show_in_gift`, `allow_traffic_topup`
- `allowed_squads`, `external_squad_uuid` — серверы/сквады

**В карточке клиента** (`/admin/#/bedolaga/customers/:id`) — строка «Тариф» в блоке «Подписка» (имя тарифа из Web API бота: поля `tariff_id`/`tariff_name` в `GET /users/{id}`).

### Настройки интеграций и прокси (2026-11-15)

Все исходящие подключения настраиваются в **Настройки → Интеграции**:

| Блок | Что настраивается | Прокси |
|------|-------------------|--------|
| Bedolaga Bot | URL, токен, таймаут, вкл/выкл | да |
| Telegram / Саппорт | токен бота, группа-форум, интервалы, окно ответа | да |
| Bedolaga БД | host, port, база, логин, пароль (read-only) | **нет** (TCP, нужен SSH-туннель/VPN) |
| Platega | credentials + автосинк (существующие) | да |
| YooKassa | credentials + автосинк (существующие) | да |

Прокси: глобальный по умолчанию (`OUTBOUND_PROXY_*`) плюс режим у каждой HTTP-интеграции
`inherit | direct | custom`. Поддерживаются `http`, `https`, `socks5`, `socks5h`,
логин/пароль и список исключений (`no_proxy`). Все клиенты создаются с `trust_env=False`,
поэтому `HTTP_PROXY` из окружения не подхватывается неявно.

Сохранение применяется без рестарта контейнера: клиент Bedolaga пересоздаётся, Telegram-канал
перезапускается in-place (живые WebSocket-подписки не рвутся), Bedolaga DB переподключается.
У каждого блока есть кнопка проверки подключения, у прокси — проверка с показом внешнего IP.
ENV-переменные `BEDOLAGA_*`, `SUPPORT_*`, `BOT_DB_*` остаются стартовыми значениями;
сохранённое в админке имеет приоритет.

### Правила работы

- На живом сервере — только чтение (без явного одобрения владельца)
- Не поднимать второй бот на том же `BOT_TOKEN`
- Не давать локальному боту `REMNAWAVE_API_URL` прода
- Не коммитить секреты
- Пользователь БД `cms_ro` — **только SELECT**, без прав записи; не расширять без необходимости
- socat-мост `bot-db-cms-bridge` — только с UFW-ограничением на IP CMS-сервера

---

## Decoy-сайты (маскировка Reality)

HTML-заглушки в `C:\Users\Andre\Desktop\VPN\Заглушка\decoy\`:
- files.monolist.art — файловый конвертер
- audio.monolist.art — аудио-конвертер
- photo.monolist.art — фото/фильтры
- video.monolist.art — видео-конвертер
- data.monolist.art — конвертер данных
- hash/index.html, qrcode/index.html — доп. страницы

---

## Документация проекта

| Файл | О чём | Актуальность |
|------|-------|-------------|
| `docs/ARCHITECTURE.md` | Архитектура и история проекта | ✅ |
| `docs/decisions/ADR-001-panel-design-system.md` | Дизайн-система админки | ✅ |
| `docs/decisions/ADR-002-remnawave-structure-parity.md` | Структурный паритет с Remnawave | ✅ |
| `AGENTS.md` | Инструкции для ИИ-агентов | ✅ |
| `CONTRIBUTING.md` | Правила коммитов | ✅ |
| `DEPLOY.md` | Деплой | ✅ |

Исторические файлы миграции (`docs/MIGRATION_*`, `docs/plans/`) сохранены для ретроспективы, но описывают уже пройденный путь.

---

## Ключевые решения (зафиксированы в ADR)

| Решение | Суть |
|---------|------|
| **Дизайн-система админки** (ADR-001) | Токены CSS, 6 акцентных пресетов, настройки вида per-user |
| **Структурный паритет с Remnawave** (ADR-002) | `web/frontend` + `web/backend` — 1:1 с эталоном; формат ответа `{success,data}` — осознанное отклонение |

---

## Серверы и доступы

| Сервер | IP | SSH порт | Пользователь |
|--------|-----|----------|-------------|
| Панель | 144.31.156.172 | 356 | kilo |
| files (DE) | 144.31.96.78 | 356 | kilo |
| audio (FI) | 31.77.128.251 | 356 | kilo |
| photo (NL) | 31.77.146.75 | 356 | kilo |
| video (RU) | 159.194.221.84 | 356 | kilo |
| data (US) | 162.217.248.186 | 22 | kilo |
| istra (VK) | 85.198.98.18 | 356 | kilo |
| vps (Yandex) | 155.212.131.4 | 356 | kilo |

SSH-ключ: `~/.ssh/id_ed25519` (`kilo-ops@desktop`)

---

## Типовые операции

### Обновление remnanode на ноде
```bash
docker compose -f /opt/remnanode/docker-compose.yml pull remnanode
docker compose -f /opt/remnanode/docker-compose.yml up -d remnanode
docker exec remnanode mkdir -p /var/log/remnanode
```

### Типовые неисправности

| Симптом | Причина / Решение |
|---------|-------------------|
| Нода не поднимается | Нет `/var/log/remnanode` внутри контейнера |
| Decoy по https молчит | target в Reality указывает на сокет, а не `127.0.0.1:9443` |
| Бот спамит `RemnaWaveConfigurationError` | В `.env` бота добавить `REMNAWAVE_API_URL=http://remnawave-panel:3000` |
| Бот-лог «короткий» | Полный лог: `/opt/remnawave-bedolaga-telegram-bot/logs/bot.log` |

---

## Бэкапы и DR (2026-11-21)

Подсистема `backup-*` в CMS + отдельный агент `backup-agent/` на серверах.
Спроектировано в `docs/plans/2026-11-21-backup-system.md`, решение — `docs/decisions/ADR-005-backup-system.md`.

| Компонент | Где | Роль |
|-----------|-----|------|
| CMS-оркестратор | `web/backend/core/backup/`, `api/v1/backups/` | рецепты, политики, манифесты, планировщик, UI |
| Агент | `backup-agent/` (Docker, `/opt/hexaveil-backup-agent`) | pg_dump/tar/age, локальное расписание, spool |
| API агента | `/api/backup-agent/v1/*` | регистрация, heartbeat, state, inventory, runs, upload, commands |
| БД | таблицы `backup_*` | хосты, агенты, компоненты, политики/уровни, запуски, артефакты, восстановления, уведомления |
| UI | `/admin/backups`, `/admin/infrastructure/nodes`, `/admin/infrastructure/panel` | управление и мониторинг |

Инварианты:

- плановые уровни всегда `online`; `quiesce` — только вручную;
- retention по умолчанию: БД — 48 копий (48 ч), полный — 14 дней, `min_copies=3`;
- SLA: БД не старше 1 ч, полный — 24 ч;
- артефакты шифруются `age`; приватный ключ — в CMS (обёрнут `APP_ENCRYPTION_KEY`) + офлайн;
- для хоста CMS (`role=self`, `transport=inline`) запрещено единственное локальное хранилище;
- удаление хоста не удаляет артефакты — они помечаются `orphaned`.

---

*Последнее обновление: 2026-11-26. При изменении инфраструктуры обновлять секции нод и доступов.*