# Контекст проекта HexaVeil CMS

**Стек:**
- Публичный сайт: PHP 8.1 (vanilla) + PostgreSQL 16
- Фронтенд админки: React 18 + TypeScript + Vite + Tailwind + shadcn/ui (Radix)
- Бэкенд админки: FastAPI + SQLAlchemy async + PyJWT + Pydantic v2 + structlog
- База данных: PostgreSQL 16
- Инфраструктура: Docker Compose (nginx-selfsteal → PHP-FPM / FastAPI)

**Главные соглашения:**
- Типизация strict, запрет на `any` в TypeScript и Python
- Архитектурный паттерн: MVC-like (маршруты → контроллеры → модели → представления)
- Запрет на тяжёлые библиотеки в продакшене (только vanilla CSS/JS/PHP для публичного сайта)
- Дизайн-система админки: Remnawave стиль (glass-эффекты, mesh-фон, 6 акцентных пресетов)
- Формат API ответов: `{success, data}` / `{success, error}` (PHP‑совместимость)
- Версия API: `/api/v1` (независимое версионирование)
- CSRF защита: проверка для всех эндпоинтов, кроме внутренних UI‑эндпоинтов (save‑preference)
- Хранение настроек вида: тема/режим в БД (таблица `user_preferences`), остальное в `localStorage`

**Ключевые команды:**
- Dev: `docker compose up --build`
- Prod: `docker compose -f docker-compose.prod.yml up -d --build`
- Тесты backend: `pytest`
- Тесты frontend: `npm run test` (если настроены)
- Логи: `docker compose logs -f`

**Ограничения проекта:**
- Нет npm/сборщиков для публичного сайта (только vanilla CSS/JS/PHP)
- Не коммитить папку `Fin/`
- Не менять маршруты/контроллеры/логику/имена полей форм без явной необходимости
- На живом сервере — только чтение (без явного одобрения владельца)
- Секреты хранятся в `.env` (не в репозитории); `.env.example` присутствует

**Интеграции:**
- Bedolaga Bot Web API проксируется через `/api/bedolaga/*`
- Тарифы читаются напрямую из БД бота (read-only пользователь `cms_ro`) через socat‑мост `bot-db-cms-bridge` (порт 5434)
- Remnawave Panel управляет нодами, подписками, пользователями
- Decoy‑сайты (HTML‑заглушки) для маскировки Reality tráfico

**Эталон Remnawave** (`remnawave-admin-main/`, не часть проекта):
- UI и логика: `web/frontend/src/{components,lib,store,api,pages}`
- Backend: `web/backend/{api,core,schemas}`
- Читать только конкретный файл по пути, каталоги не сканировать. Карта — `REFERENCE.md`.
- `node_modules` эталона закрыт в `.kilocodeignore`, исходники доступны.
