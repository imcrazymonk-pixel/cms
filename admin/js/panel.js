/**
 * Panel JS — темы, режим, настройки вида, сайдбар
 */
(function () {
  const STORAGE_KEY = 'panel-preferences';

  function getPrefs() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function setPrefs(prefs) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    applyPrefs(prefs);
  }

  function applyPrefs(prefs) {
    const html = document.documentElement;
    if (prefs.theme) html.setAttribute('data-theme', prefs.theme);
    if (prefs.mode) html.setAttribute('data-mode', prefs.mode);
    if (prefs.density) html.setAttribute('data-density', prefs.density);
    if (prefs.radius) html.setAttribute('data-radius', prefs.radius);
    if (prefs.fontSize) html.setAttribute('data-font-size', prefs.fontSize);
    if (prefs.animations === false) html.setAttribute('data-animations', 'false');
    else html.removeAttribute('data-animations');
  }

  function init() {
    const prefs = getPrefs();
    // Дефолты, если ничего не сохранено
    if (!prefs.theme) prefs.theme = 'obsidian';
    if (!prefs.mode) prefs.mode = 'dark';
    if (!prefs.density) prefs.density = 'comfortable';
    if (!prefs.radius) prefs.radius = 'default';
    if (!prefs.fontSize) prefs.fontSize = 'default';
    if (prefs.animations === undefined) prefs.animations = true;
    applyPrefs(prefs);

    // Переключение темы/режима через data-атрибуты на кнопках
    document.addEventListener('click', function (e) {
      const themeBtn = e.target.closest('[data-set-theme]');
      if (themeBtn) {
        const prefs = getPrefs();
        prefs.theme = themeBtn.getAttribute('data-set-theme');
        setPrefs(prefs);
        saveToServer('theme', prefs.theme);
        return;
      }
      const modeBtn = e.target.closest('[data-set-mode]');
      if (modeBtn) {
        const prefs = getPrefs();
        prefs.mode = modeBtn.getAttribute('data-set-mode');
        setPrefs(prefs);
        saveToServer('mode', prefs.mode);
        return;
      }
      const densityBtn = e.target.closest('[data-set-density]');
      if (densityBtn) {
        const prefs = getPrefs();
        prefs.density = densityBtn.getAttribute('data-set-density');
        setPrefs(prefs);
        return;
      }
    });

    // Сворачивание сайдбара
    const collapseBtn = document.getElementById('sidebar-collapse-btn');
    if (collapseBtn) {
      collapseBtn.addEventListener('click', function () {
        const sidebar = document.querySelector('.panel-sidebar');
        if (sidebar) sidebar.classList.toggle('sidebar-collapsed');
      });
    }

    // Подтверждение опасных действий (ссылки с data-confirm, рендерятся DataGrid)
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

  // Сохранение темы/режима на сервер (per-user)
  function saveToServer(key, value) {
    fetch('/admin/settings/save-preference', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: key, value: value }),
    }).catch(function () { /* тихо игнорируем */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
