// server-panel.js — панель серверов: список, поиск, флаги, CTA.
// Данные — из js/data.js, выбор сервера — через API js/planet.js (HV_PLANET).
// Выбранный сервер «разворачивается» прямо в списке: под строкой появляются
// метки и кнопка подключения — без отдельного мини-блока с информацией.
(function () {
  'use strict';

  // Guard: данные должны загрузиться до нас
  if (!window.HV_DATA_WAIT) {
    console.error('server-panel.js: js/data.js не загружен (HV_DATA_WAIT не найден)');
    return;
  }

  var rows = {}; // cityKey -> DOM-элемент .server-row
  var data = null;

  function buildList(D) {
    var list = document.getElementById('serverList');
    var count = document.getElementById('serverCount');
    if (!list) return;
    var servers = Object.keys(D.CITY_INFO)
      .filter(function (k) { return D.CITY_INFO[k].hub !== false; })
      .sort(function (a, b) {
        // Сначала доступные серверы, затем недоступные. Внутри каждой группы:
        // Россия первой, дальше страны по алфавиту (русская сортировка),
        // внутри страны — по отклику.
        var A = D.CITY_INFO[a];
        var B = D.CITY_INFO[b];
        var oa = A.connected === false ? 1 : 0;
        var ob = B.connected === false ? 1 : 0;
        if (oa !== ob) return oa - ob;
        var aRu = A.country === 'Россия' ? 0 : 1;
        var bRu = B.country === 'Россия' ? 0 : 1;
        if (aRu !== bRu) return aRu - bRu;
        if (A.country !== B.country) return A.country.localeCompare(B.country, 'ru');
        return A.ping - B.ping;
      });
    if (count) count.textContent = servers.length;
    list.innerHTML = '';
    rows = {};
    servers.forEach(function (key) {
      var info = D.CITY_INFO[key];
      var offline = info.connected === false;
      var row = document.createElement('div');
      row.className = 'server-row' + (offline ? ' offline' : '');
      row.dataset.city = key;
      row.dataset.search = (info.ru + ' ' + info.en + ' ' + info.country).toLowerCase();
      // a11y: строка ведёт себя как кнопка
      row.setAttribute('role', 'button');
      row.setAttribute('tabindex', '0');
      row.setAttribute('aria-expanded', 'false');
      row.setAttribute('aria-selected', 'false');
      // Строка: флаг + страна (основной текст) + город (приглушённый) + отклик.
      // У недоступных серверов вместо отклика — красное «n/a», строка серая,
      // в развёрнутой области — метка «Сервер недоступен» вместо CTA.
      row.innerHTML =
        '<div class="server-row-main">' +
          '<img class="server-flag" src="' + D.flagUrl(info.flag) + '" alt="' + info.country + '" loading="lazy" />' +
          '<div class="server-name" title="' + info.ru + ' · ' + info.country + '">' + info.country +
            '<span class="server-city">' + info.ru + '</span>' +
          '</div>' +
          (offline
            ? '<span class="server-ping server-ping-offline">n/a</span>'
            : '<span class="server-ping" style="color:' + D.pingColor(info.ping) + '">' +
                info.ping + ' мс</span>') +
        '</div>' +
        '<div class="server-row-detail">' +
          '<div class="server-row-tags"></div>' +
          (offline
            ? '<span class="server-offline-label">Сервер недоступен</span>'
            : '<a class="btn btn-primary server-row-connect" href="' + D.CONNECT_URL + '" target="_blank" rel="noopener">' +
                'Подключиться</a>') +
        '</div>';
      // Клик по строке выбирает сервер; клик по CTA-ссылке — нет
      row.addEventListener('click', function (e) {
        if (e.target.closest('.server-row-connect')) return;
        window.HV_PLANET.selectServer(key);
      });
      // Клавиатура: Enter/Space — выбор (toggle), Escape — снять выделение
      row.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          window.HV_PLANET.selectServer(key);
        } else if (e.key === 'Escape' && row.classList.contains('active')) {
          window.HV_PLANET.selectServer(key);
        }
      });
      list.appendChild(row);
      rows[key] = row;
    });
  }

  // Заполняет развёрнутую область выбранного сервера: метки + соседние маршруты
  function fillDetail(row, key) {
    var tagsEl = row.querySelector('.server-row-tags');
    if (!tagsEl) return;
    var info = data.CITY_INFO[key];
    tagsEl.innerHTML = '';
    var chips = (info.tags || []).slice();
    if (info.connected !== false && info.ping < 70) chips.push('низкий пинг');
    data.neighborsOf(key).forEach(function (n) { chips.push(data.CITY_INFO[n].ru); });
    if (!chips.length) chips.push('—');
    chips.forEach(function (t) {
      var s = document.createElement('span');
      s.className = 'server-tag';
      s.textContent = t;
      tagsEl.appendChild(s);
    });
  }

  function initSearch() {
    var search = document.getElementById('serverSearch');
    var clear = document.getElementById('serverSearchClear');
    if (!search) return;
    function apply(q) {
      q = (q || '').trim().toLowerCase();
      Object.keys(rows).forEach(function (key) {
        var row = rows[key];
        row.style.display = (!q || row.dataset.search.indexOf(q) !== -1) ? '' : 'none';
      });
      if (clear) clear.style.display = q ? 'inline-flex' : 'none';
    }
    search.addEventListener('input', function () { apply(search.value); });
    // Enter — выбрать первый видимый результат
    search.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter') return;
      var first = null;
      Object.keys(rows).forEach(function (key) {
        if (!first && rows[key].style.display !== 'none') first = rows[key];
      });
      if (first) {
        e.preventDefault();
        window.HV_PLANET.selectServer(first.dataset.city);
      }
    });
    if (clear) {
      clear.addEventListener('click', function () {
        search.value = '';
        apply('');
        search.focus();
      });
    }
    apply('');
  }

  window.HV_PANEL = {
    // Вызывается из planet.js после изменения выбора: выделяет и разворачивает
    // выбранную строку, остальные сворачивает.
    refresh: function (key) {
      Object.keys(rows).forEach(function (k) {
        var row = rows[k];
        var active = k === key;
        row.classList.toggle('active', active);
        row.setAttribute('aria-expanded', active ? 'true' : 'false');
        row.setAttribute('aria-selected', active ? 'true' : 'false');
        if (active) {
          fillDetail(row, k);
          // Развёрнутый сервер держим в видимой области списка
          row.scrollIntoView({ block: 'nearest' });
        }
      });
    },
    init: function (D) {
      data = D;
      buildList(D);
      initSearch();
    },
  };

  window.HV_DATA_WAIT(function (D) {
    window.HV_PANEL.init(D);
  });
})();
