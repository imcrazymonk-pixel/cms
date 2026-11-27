# TASK — Фикс «Настройки → Интеграции»: пустая/свёрнутая вкладка и игнор `from`

> Статус: **план, к реализации**
> Дата: 2026-11-21
> Роль: архитектор/планировщик
> Предыдущий TASK сохранён: `docs/plans/2026-11-21-bedolaga-tariffs-revenue-plan.md`

---

## 1. Жалоба пользователя

> «Когда переходишь в Настройки - Интеграции (Далее выбираешь либо Телеграм/саппорт либо Прокси по умолчанию), то перемещает на какую то страницу заглушку где во вкладке Интеграции нет настроек)»

## 2. Диагноз (проверено по коду)

Маршрутизация тут **не виновата**: `/settings?tab=integrations&from=...` корректно рендерит `pages/Settings` (`App.tsx:117`), вкладка `integrations` есть (`Settings.tsx:711-719`), клик по аккордеону раскрывает блок.

Причин визуального эффекта три:

1. **Все блоки свёрнуты по умолчанию.** `Section.defaultOpen = false` (`web/frontend/src/pages/Settings.tsx:41-42`), а `renderIntegrationCategory` не передаёт `defaultOpen` (`Settings.tsx:586-621`). Вкладка «Интеграции» показывает только заголовки категорий («Telegram / Саппорт», «Прокси по умолчанию», …) с числом и кнопкой «Проверить» — ни одного поля ввода. Воспринимается как «вкладка без настроек».
2. **Параметр `from` игнорируется.** `navigation.ts:85,102` формируют `?tab=integrations&from=bedolaga|support`, но `Settings.tsx` читает только `tab` (`Settings.tsx:303-305, 388-390`). Deep-link не открывает и не прокручивает нужный блок, к тому же `setSearchParams({ tab })` (`Settings.tsx:708`) выбрасывает `from`.
3. **Рядом настоящие заглушки.** Подпункты «Саппорт» (`/support/sla|kb|ai|templates|analytics|team`) → `pages/support/Placeholder.tsx` «Раздел в разработке» (`App.tsx:133-138`). Пользователь может путать их с пунктом «Настройки» в той же группе меню.

## 3. Границы задачи

- Только фронтенд (`web/frontend`). Backend, `settings_registry.py`, API-контракты, маршруты, имена полей форм — **не трогать**.
- Не менять поведение остальных вкладок настроек: там блоки остаются свёрнутыми по умолчанию (коммит 85e196b).
- Прод не трогать; сборка `dist` — в репозитории.

## 4. План правок

### P1. `web/frontend/src/pages/Settings.tsx` — `Section` (стр. 39-90)

- Добавить проп `id?: string`, прокинуть на корневой `Card`.
- Реагировать на изменение `defaultOpen`: `useEffect(() => { if (defaultOpen) setOpen(true) }, [defaultOpen])` (не сбрасывает ручное закрытие, т.к. значение не меняется).
- Сделать заголовок одной кнопкой: `<button type="button" ...>` на всю левую часть строки, `action`/счётчик — сиблинги вне кнопки. Сейчас `<button>` вложен в кликабельный `<div>` (стр. 57-65) — убрать двойной обработчик.
- Добавить `aria-expanded={open}` и `aria-controls`, панели — `role="region"` и `id`.
- Визуальные классы и анимации не менять.

### P2. `Settings.tsx` — маппинг `from` → категория (рядом с `INTEGRATION_TEST_IDS`, стр. 191-199)

Добавить константы:

- `FROM_TO_CATEGORY`:
  - `bedolaga` → `'Bedolaga Bot'`
  - `support` → `'Telegram / Саппорт'`
  - `bot_db` → `'Bedolaga БД'`
  - `platega` → `'Platega'`
  - `yookassa` → `'YooKassa'`
  - `proxy` → `'Прокси по умолчанию'`
- `CATEGORY_ANCHOR: Record<string, string>` — ASCII-якоря (`settings-cat-bedolaga`, `settings-cat-support`, …). Не строить DOM-id из кириллицы/пробелов.

### P3. `Settings.tsx` — фокус и скролл (внутри `Settings`, стр. 302-390)

- `const fromParam = searchParams.get('from') || ''`.
- `const focusCategory = tab === 'integrations' ? (FROM_TO_CATEGORY[fromParam] || '') : ''`.
- `useEffect` на `[focusCategory, isPending, items.length]`: после загрузки найти `document.getElementById(CATEGORY_ANCHOR[focusCategory])` и `scrollIntoView({ block: 'start', behavior: 'smooth' })` через `requestAnimationFrame`.
- Если задан `from`, а `tab` нет — начальная вкладка `integrations` (правка выражения `tab || 'basic'` в стр. 304 и 389).

### P4. `Settings.tsx` — `renderIntegrationCategory` (стр. 586-621)

- Передать `defaultOpen`: `!!q || focusCategory === category || !fromParam` (без `from` — раскрыты все блоки вкладки «Интеграции»; с `from` — только целевой).
- Передать `id={CATEGORY_ANCHOR[category]}`.
- `renderCategory` (стр. 547-567) не менять.

### P2-опционально. `web/frontend/src/components/layout/Sidebar.tsx:97-105`

Подсветка пункта «Настройки» в группах Bedolaga/Саппорт: сравнивать `pathname` + только `tab`, а не весь `search`. Делать только если не затрагивает остальные ссылки; иначе пропустить.

### P5. Пересборка `dist`

`web/frontend/dist` коммитится — после правок выполнить `npm run build` в `web/frontend`.

## 5. Обновить документацию (DoD)

- `docs/CODEBASE_INDEX.md`:
  - блок «Settings (`/settings`)» (стр. ~1372-1376): `?from=` маппится в категорию вкладки «Интеграции», выполняется `scrollIntoView`, блоки «Интеграций» раскрыты по умолчанию (при `from` — только целевой), у `Section` есть `id`/`aria-expanded`/`aria-controls`;
  - 5.3 Sidebar (стр. ~1438, 1443): `from=bedolaga`/`from=support` потребляются страницей Settings;
  - строки ~1447-1449 — только если сделана правка Sidebar.
- `PROJECT.md` / ADR — без изменений.

## 6. Чек-лист проверки

Ручные (локально `npm run dev`, `http://localhost:3000/admin/settings`):

1. «Настройки → Интеграции» без query: видны поля всех 6 блоков.
2. Клик по заголовку: блок раскрывается/сворачивается, URL не меняется, никуда не уводит.
3. Кнопка «Проверить» в «Telegram / Саппорт» и «Прокси по умолчанию»: только toast, без перехода.
4. `?tab=integrations&from=support`: активна вкладка «Интеграции», блок «Telegram / Саппорт» раскрыт и прокручен в зону видимости, остальные свёрнуты.
5. `from=bedolaga` и hard reload по deep-link — тот же результат.
6. `?from=proxy` вручную → раскрыт «Прокси по умолчанию».
7. Регресс: «Основные», «SEO», «Финансы», «Сайт», «Логи» — блоки свёрнуты по умолчанию, поиск/сохранение работают.
8. «Саппорт → Контроль SLA и т.п.» по-прежнему показывают «Раздел в разработке».

Автоматические:

- `cd web/frontend && npm run typecheck`
- `npm run lint`
- `npm run build`
