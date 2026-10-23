NewWeb/
├── index.php                 # Front‑controller публичного сайта (PHP)
├── web/
│   ├── frontend/             # React SPA админки
│   │   ├── src/              # Исходники (TS + компоненты)
│   │   │   ├── App.tsx       # Роутинг
│   │   │   ├── main.tsx      # Entry point
│   │   │   ├── index.css     # Дизайн‑система Remnawave (токены)
│   │   │   ├── api/          # API‑клиенты (auth, posts, pages, …)
│   │   │   ├── components/   # layout/ + ui/ (23 shadcn компонента)
│   │   │   │   ├── layout/   # Header, Sidebar, etc.
│   │   │   │   └── ui/       # Button, Input, Modal, Table, …
│   │   │   ├── pages/        # Все страницы админки (dashboard, posts, …)
│   │   │   ├── store/        # Zustand (auth, appearance, filters, permission)
│   │   │   └── lib/          # Утилиты (useTabParam, mutationToast, …)
│   │   ├── public/           # config.js, favicon, logo
│   │   ├── dist/             # Сборка (коммитится в репо)
│   │   └── vite.config.ts    # Прокси /api → FastAPI
│   └── backend/              # FastAPI (JSON API)
│       ├── main.py           # FastAPI app + CORS + middleware
│       ├── api/v1/           # Роутеры (auth, posts, pages, users, …)
│       │   └── bedolaga/     # Прокси Bedolaga Bot Web API
│       ├── core/             # config, security, database, errors
│       │   ├── config.py     # Pydantic‑настройки (.env)
│       │   ├── security.py   # JWT (совместим с PHP)
│       │   ├── database.py   # SQLAlchemy async + engine
│       │   └── errors.py     # Кастомные исключения
│       ├── schemas/          # Pydantic‑модели per‑domain (post, category, …)
│       └── tests/            # unit + e2e smoke tests
├── core/                     # PHP‑ядро публичного сайта
│   ├── Router.php            # Маршрутизация
│   ├── routes.php            # Все маршруты публичного сайта
│   ├── TemplateEngine.php    # Шаблонизатор
│   ├── Database.php          # PDO‑обёртка
│   ├── models/               # Post, Category, Page, User, …
│   ├── helpers.php           # Утилиты
│   └── helpers_icons.php     # Inline Lucide SVG‑иконки
├── templates/themes/         # PHP‑темы (hexaveil — активная)
│   └── hexaveil/
│       ├── theme.php         # Конфиг темы (настройки, виджеты)
│       └── /                 # Шаблоны лендинга и блога
├── public/                   # Ассеты, uploads, дизайн‑система
│   ├── hexaveil/             # Стили темы (style.css)
│   └── css/panel/            # Дизайн‑система админки (tokens, themes, …)
├── db/                       # Схема PostgreSQL, миграции, дампы
│   └── schema.sql
├── docs/                     # Документация, ADR, планы
│   ├── ARCHITECTURE.md
│   ├── decisions/
│   │   ├── ADR-001-panel-design-system.md
│   │   └── ADR-002-remnawave-structure-parity.md
│   └── plans/
├── .docker/                  # Nginx + PHP конфиги
│   ├── nginx.conf
│   └── php-fpm.conf
├── Dockerfile                # PHP 8.1‑FPM
├── docker-compose.yml        # dev
├── docker-compose.prod.yml   # prod
└── docker-entrypoint.sh      # Инициализация при старте
