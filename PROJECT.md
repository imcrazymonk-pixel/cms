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
| **Инфраструктура** | Docker Compose (app / api / web / db) |

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

### Правила работы

- На живом сервере — только чтение (без явного одобрения владельца)
- Не поднимать второй бот на том же `BOT_TOKEN`
- Не давать локальному боту `REMNAWAVE_API_URL` прода
- Не коммитить секреты

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

*Последнее обновление: 2026-10-10. При изменении инфраструктуры обновлять секции нод и доступов.*