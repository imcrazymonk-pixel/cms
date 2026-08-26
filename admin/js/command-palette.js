/**
 * Command Palette — Ctrl+K поиск по разделам админки
 * Vanilla JS, без зависимостей.
 */
(function () {
  // Инлайн-иконки Lucide (stroke-based) для результатов палитры
  const ICONS = {
    dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>',
    'file-text': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/></svg>',
    image: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
    users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    palette: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/></svg>',
    widgets: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  };

  const SEARCH_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>';

  // Все разделы админки (название + URL + иконка)
  const SECTIONS = [
    { name: 'Дашборд', url: '/admin', icon: 'dashboard' },
    { name: 'Посты', url: '/admin/posts', icon: 'file-text' },
    { name: 'Категории', url: '/admin/categories', icon: 'folder' },
    { name: 'Страницы', url: '/admin/pages', icon: 'file' },
    { name: 'Меню', url: '/admin/menus', icon: 'menu' },
    { name: 'Медиа', url: '/admin/media', icon: 'image' },
    { name: 'Пользователи', url: '/admin/users', icon: 'users' },
    { name: 'Настройки', url: '/admin/settings', icon: 'settings' },
    { name: 'Темы', url: '/admin/theme', icon: 'palette' },
    { name: 'Виджеты', url: '/admin/widgets', icon: 'widgets' },
  ];

  const root = document.getElementById('command-palette');
  if (!root) return;

  let items = [];
  let activeIndex = 0;
  let searchInput = null;
  let listEl = null;

  function build() {
    root.innerHTML = '';

    const overlay = document.createElement('div');
    overlay.className = 'cp-overlay';

    const panel = document.createElement('div');
    panel.className = 'cp-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Командная палитра');

    const search = document.createElement('div');
    search.className = 'cp-search';
    search.innerHTML = SEARCH_ICON;

    searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.id = 'cp-search-input';
    searchInput.placeholder = 'Поиск по разделам...';
    searchInput.autocomplete = 'off';
    searchInput.spellcheck = false;
    searchInput.setAttribute('aria-label', 'Поиск по разделам');

    const kbd = document.createElement('kbd');
    kbd.textContent = 'ESC';

    search.appendChild(searchInput);
    search.appendChild(kbd);

    listEl = document.createElement('div');
    listEl.className = 'cp-list';

    panel.appendChild(search);
    panel.appendChild(listEl);
    root.appendChild(overlay);
    root.appendChild(panel);

    searchInput.addEventListener('input', render);
    searchInput.addEventListener('keydown', onKeydown);
    overlay.addEventListener('click', close);
  }

  function setActive(index) {
    const nodes = listEl.querySelectorAll('.cp-item');
    nodes.forEach(function (n, i) {
      n.classList.toggle('active', i === index);
    });
    activeIndex = index;
    const active = nodes[index];
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  function render() {
    const q = searchInput.value.trim().toLowerCase();
    items = SECTIONS.filter(function (s) {
      return s.name.toLowerCase().indexOf(q) !== -1;
    });
    activeIndex = 0;

    listEl.innerHTML = '';
    if (!items.length) {
      const empty = document.createElement('div');
      empty.className = 'cp-empty';
      empty.textContent = 'Ничего не найдено';
      listEl.appendChild(empty);
      return;
    }

    items.forEach(function (s, i) {
      const a = document.createElement('a');
      a.className = 'cp-item' + (i === 0 ? ' active' : '');
      a.href = s.url;
      a.innerHTML = (ICONS[s.icon] || '') + '<span>' + s.name + '</span>';
      a.addEventListener('click', function () { close(); });
      a.addEventListener('mouseenter', function () { setActive(i); });
      listEl.appendChild(a);
    });
  }

  function onKeydown(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      close();
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (items.length) setActive((activeIndex + 1) % items.length);
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (items.length) setActive((activeIndex - 1 + items.length) % items.length);
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      const target = items[activeIndex];
      if (target) location.href = target.url;
    }
  }

  function open() {
    if (root.hidden) {
      root.hidden = false;
      render();
      if (searchInput) searchInput.focus();
    }
  }

  function close() {
    if (!root.hidden) root.hidden = true;
  }

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      open();
    }
  });

  const trigger = document.getElementById('command-palette-trigger');
  if (trigger) trigger.addEventListener('click', open);

  build();
})();
