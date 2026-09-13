# NewWeb CMS — Agent Guide

## Перед началом работы

1. Прочитай `PROJECT.md` — полное описание проекта
2. Прочитай `docs/decisions/ADR-001-panel-design-system.md` — дизайн-система админки
3. Используй `kilo-config` skill для вопросов по конфигурации

## Какие skills использовать для разных задач

### Работа с дизайном (HexaVeil тема, блог, лендинг)
```markdown
/skill design-taste-frontend
/skill high-end-visual-design
```

### Планирование новой функциональности
```markdown
/skill spec-driven-development
/skill writing-plans
/skill brainstorming
```

### Реализация по готовому плану
```markdown
/skill executing-plans
/skill subagent-driven-development
/skill dispatching-parallel-agents
```

### Отладка и исправление ошибок
```markdown
/skill systematic-debugging
/skill verification-before-completion
```

### Работа с админкой (дизайн-система, UI)
```markdown
/skill design-system
/skill redesign-existing-projects
/skill industrial-brutalist-ui
/skill minimalist-ui
```

### Интеграция с Remnawave (VPN-биллинг, ноды)
```markdown
/skill remnawave-xray
```

### Финальная проверка, PR, мерж
```markdown
/skill verification-before-completion
/skill requesting-code-review
/skill finishing-a-development-branch
```

### Работа с git worktree (изолированная разработка)
```markdown
/skill using-git-worktrees
```

### Генерация изображений (баннеры, превью для блога)
```markdown
/skill imagegen-frontend-web
/skill image-to-code
/skill banner-design
```

## Технические ограничения проекта

- **Никаких npm/сборщиков** — только vanilla CSS/JS/PHP
- **Файлы не больше 500 строк** (исключение: style.css темы ~1800 строк)
- **Не коммитить папку `Fin/`**
- **Не менять маршруты/контроллеры/логику/имена полей форм** без явной необходимости
- **PHP 7.4+** для совместимости с Open Server Panel
- **MySQL** через `127.127.126.26` (виртуальный IP OSP)

## Домен и окружение

- Сайт: `http://hexacms`
- Админка: `http://hexacms/admin`
- Логин: `admin` / Пароль: `admin12345`
- Apache из Open Server Panel

## Ключевые файлы

| Файл | Назначение |
|------|------------|
| `PROJECT.md` | Полное описание проекта и roadmap |
| `core/routes.php` | Все маршруты сайта (добавлять ДО catch-all `{slug}`) |
| `core/models/Post.php` | Модель постов |
| `admin/templates/layouts/main.php` | Layout админки (там же CKEditor 5 init) |
| `templates/themes/hexaveil/` | Активная тема (лендинг + блог) |
| `public/hexaveil/css/style.css` | Стили темы (включая блог) |
| `docs/decisions/ADR-001-panel-design-system.md` | Документация дизайн-системы |

## Типовые задачи и их решение

### «Создать новую страницу на сайте»
1. Добавить маршрут в `core/routes.php` (ДО `{slug}`)
2. Создать шаблон в `templates/themes/hexaveil/`
3. Добавить стили в `public/hexaveil/css/style.css`
4. При необходимости — ссылку в навигацию (`layouts/main.php`)

### «Добавить функционал в админку»
1. Создать/дополнить контроллер в `admin/controllers/`
2. Создать/дополнить шаблон в `admin/templates/`
3. Использовать `DataGrid` для списков
4. Использовать `icon()` для иконок
5. Использовать дизайн-систему (tokens, themes, components CSS)

### «Поправить баг»
1. Прочитать `systematic-debugging` skill
2. Воспроизвести и залогировать ошибку
3. Найти причину
4. Исправить
5. Проверить через `verification-before-completion`