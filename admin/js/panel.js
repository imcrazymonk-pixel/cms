/**
 * Panel JS — темы, режим, настройки вида, сайдбар
 * Все настройки сохраняются в БД одним JSON-блобом (ключ panel_ui_state).
 * Интерфейс: одна кнопка «Вид» → панель с опциями (как в remnawave-admin).
 */
(function () {
  const STORAGE_KEY = 'panel-preferences';

  // Дефолты
  const DEFAULTS = {
    theme: 'obsidian',
    mode: 'dark',
    density: 'comfortable',
    radius: 'default',
    fontSize: 'default',
    animations: true,
    sidebarCollapsed: false,
  };

  function getPrefs() {
    try { return Object.assign({}, DEFAULTS, JSON.parse(localStorage.getItem(STORAGE_KEY))); }
    catch (e) { return Object.assign({}, DEFAULTS); }
  }

  function savePrefs(prefs, saveToServerFlag) {
    if (saveToServerFlag === undefined) saveToServerFlag = true;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    applyPrefs(prefs);
    if (saveToServerFlag) saveAllToServer(prefs);
  }

  // Режим 'auto' резолвится в светлый/тёмный по системной теме
  function resolveMode(mode) {
    if (mode !== 'auto') return mode;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function applyPrefs(prefs) {
    const html = document.documentElement;
    if (prefs.theme) html.setAttribute('data-theme', prefs.theme);
    if (prefs.mode) html.setAttribute('data-mode', resolveMode(prefs.mode));
    if (prefs.density) html.setAttribute('data-density', prefs.density);
    if (prefs.radius) html.setAttribute('data-radius', prefs.radius);
    if (prefs.fontSize) html.setAttribute('data-font-size', prefs.fontSize);
    if (prefs.animations === false) html.setAttribute('data-animations', 'false');
    else html.removeAttribute('data-animations');
    // Сайдбар
    const sidebar = document.querySelector('.panel-sidebar');
    if (sidebar && prefs.sidebarCollapsed) {
      sidebar.classList.add('sidebar-collapsed');
      const collapseBtn = document.getElementById('sidebar-collapse-btn');
      if (collapseBtn) collapseBtn.setAttribute('data-tooltip', 'Развернуть меню');
    } else if (sidebar) {
      sidebar.classList.remove('sidebar-collapsed');
      const collapseBtn = document.getElementById('sidebar-collapse-btn');
      if (collapseBtn) collapseBtn.setAttribute('data-tooltip', 'Свернуть меню');
    }
    updateActiveStates(prefs);
  }

  // Подсветка активных опций в dropdown настроек
  function updateActiveStates(prefs) {
    document.querySelectorAll('[data-set-theme]').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-set-theme') === prefs.theme);
    });
    document.querySelectorAll('[data-set-mode]').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-set-mode') === prefs.mode);
    });
    document.querySelectorAll('[data-set-density]').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-set-density') === prefs.density);
    });
    document.querySelectorAll('[data-set-radius]').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-set-radius') === prefs.radius);
    });
    document.querySelectorAll('[data-set-font-size]').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-set-font-size') === prefs.fontSize);
    });
    const animToggle = document.querySelector('[data-set-animations]');
    if (animToggle) animToggle.checked = prefs.animations !== false;
  }

  function closeAllDropdowns() {
    document.querySelectorAll('.dropdown-menu.open').forEach(function (m) {
      m.classList.remove('open');
    });
  }

  // Bulk-сохранение всех настроек на сервер (один JSON в panel_ui_state)
  function saveAllToServer(prefs) {
    var payload = {};
    // Сохраняем только то, что может измениться (не дефолты, но всё для простоты)
    payload.theme = prefs.theme;
    payload.mode = prefs.mode;
    payload.density = prefs.density;
    payload.radius = prefs.radius;
    payload.fontSize = prefs.fontSize;
    payload.animations = prefs.animations;
    if (prefs.sidebarCollapsed !== undefined) payload.sidebarCollapsed = prefs.sidebarCollapsed;

    fetch('/admin/settings/save-all-preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).catch(function () { /* тихо игнорируем */ });
  }

  function init() {
    var prefs = getPrefs();

    // Если localStorage пуст (новый браузер/устройство), но сервер вернул
    // panel_ui_state — используем серверные настройки, чтобы не потерять
    // тему/режим, сохранённые с другого устройства.
    var localRaw = (function() {
      try { return localStorage.getItem(STORAGE_KEY); } catch(e) { return null; }
    })();
    if (!localRaw && window.__panelState && typeof window.__panelState === 'object') {
      prefs = Object.assign({}, DEFAULTS, window.__panelState);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    }

    applyPrefs(prefs);

    // Клики: dropdown, настройки вида, сайдбар
    document.addEventListener('click', function (e) {
      // Открытие/закрытие dropdown
      const toggle = e.target.closest('[data-dropdown-toggle]');
      if (toggle) {
        e.preventDefault();
        const menu = toggle.parentElement.querySelector('.dropdown-menu');
        const willOpen = menu && !menu.classList.contains('open');
        closeAllDropdowns();
        if (menu && willOpen) menu.classList.add('open');
        return;
      }

      // Закрытие dropdown при клике вне его
      if (!e.target.closest('.dropdown')) closeAllDropdowns();

      const themeBtn = e.target.closest('[data-set-theme]');
      if (themeBtn) {
        prefs.theme = themeBtn.getAttribute('data-set-theme');
        savePrefs(prefs);
      }

      const modeBtn = e.target.closest('[data-set-mode]');
      if (modeBtn) {
        prefs.mode = modeBtn.getAttribute('data-set-mode');
        savePrefs(prefs);
      }

      const densityBtn = e.target.closest('[data-set-density]');
      if (densityBtn) {
        prefs.density = densityBtn.getAttribute('data-set-density');
        savePrefs(prefs);
      }

      const radiusBtn = e.target.closest('[data-set-radius]');
      if (radiusBtn) {
        prefs.radius = radiusBtn.getAttribute('data-set-radius');
        savePrefs(prefs);
      }

      const fontSizeBtn = e.target.closest('[data-set-font-size]');
      if (fontSizeBtn) {
        prefs.fontSize = fontSizeBtn.getAttribute('data-set-font-size');
        savePrefs(prefs);
      }

      // Панель «Вид» остаётся открытой при выборе (как поповер в remnawave-admin)
      // — закрывается по клику вне или Escape.
    });

    // Переключатель анимаций (чекбокс)
    document.addEventListener('change', function (e) {
      const animToggle = e.target.closest('[data-set-animations]');
      if (animToggle) {
        prefs.animations = animToggle.checked;
        savePrefs(prefs);
      }
    });

    // Сброс настроек вида к значениям по умолчанию
    const resetBtn = document.getElementById('ap-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        prefs = Object.assign({}, DEFAULTS);
        savePrefs(prefs);
      });
    }

    // Режим 'auto': перерисовка при смене системной темы
    const mq = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)');
    if (mq && mq.addEventListener) {
      mq.addEventListener('change', function () {
        prefs = getPrefs();
        if (prefs.mode === 'auto') applyPrefs(prefs);
      });
    }

    // Escape закрывает dropdown
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeAllDropdowns();
    });

    // Сворачивание сайдбара
    const collapseBtn = document.getElementById('sidebar-collapse-btn');
    if (collapseBtn) {
      collapseBtn.addEventListener('click', function () {
        const sidebar = document.querySelector('.panel-sidebar');
        if (sidebar) {
          const collapsed = sidebar.classList.toggle('sidebar-collapsed');
          prefs.sidebarCollapsed = collapsed;
          collapseBtn.setAttribute('data-tooltip', collapsed ? 'Развернуть меню' : 'Свернуть меню');
          savePrefs(prefs);
        }
      });
    }

    // Кастомный тултип для свёрнутого сайдбара
    const tooltip = document.createElement('div');
    tooltip.className = 'sidebar-tooltip';
    document.body.appendChild(tooltip);

    document.addEventListener('mouseover', function (e) {
      const sidebar = document.querySelector('.panel-sidebar');
      const item = e.target.closest('.sidebar-logo, .sidebar-nav-item, .sidebar-tool-btn');
      if (!sidebar || !sidebar.classList.contains('sidebar-collapsed') || !item) {
        tooltip.classList.remove('visible');
        return;
      }
      const textEl = item.querySelector('.sidebar-text');
      const text = item.getAttribute('data-tooltip') || (textEl ? textEl.textContent.trim() : '');
      if (!text) {
        tooltip.classList.remove('visible');
        return;
      }
      tooltip.textContent = text;
      const rect = item.getBoundingClientRect();
      tooltip.style.left = (rect.right + 12) + 'px';
      tooltip.style.top = (rect.top + rect.height / 2) + 'px';
      tooltip.classList.add('visible');
    });
    document.addEventListener('mouseout', function (e) {
      const sidebar = document.querySelector('.panel-sidebar');
      if (!sidebar || !sidebar.classList.contains('sidebar-collapsed')) return;
      const next = e.relatedTarget;
      if (!next || !(next.closest && next.closest('.sidebar-logo, .sidebar-nav-item, .sidebar-tool-btn'))) {
        tooltip.classList.remove('visible');
      }
    });

    // Подтверждение опасных действий (ссылки с data-confirm)
    document.addEventListener('click', function (e) {
      const link = e.target.closest('[data-confirm]');
      if (link) {
        const msg = link.getAttribute('data-confirm');
        if (msg && !window.confirm(msg)) {
          e.preventDefault();
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();