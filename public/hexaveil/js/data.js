// data.js — загрузка данных серверов.
//
// Единый источник правды — файл servers.json (реальный, обновляемый).
// При каждом билде (scripts/bust-cache.mjs) его содержимое встраивается в
// index.html в тег <script type="application/json" id="servers-data"> — это
// фолбэк для офлайн-режима и открытия через file://.
// Свежая версия servers.json всегда запрашивается заново (?_=timestamp),
// чтобы браузер не отдавал закешированную старую копию.
(function () {
  'use strict';

  // Базовый путь к статике темы (задаётся в layouts/main.php).
  // Для автономного режима (file://) остаётся пустым.
  var HV_BASE = window.HV_BASE || '';

  var WAITERS = [];
  var published = false;

  // Регистрация потребителя: колбэк получит готовые данные (window.HV_DATA)
  window.HV_DATA_WAIT = function (cb) {
    if (published) { cb(window.HV_DATA); return; }
    WAITERS.push(cb);
  };

  // Встроенная в HTML копия данных (фолбэк при недоступности servers.json)
  function readInlineData() {
    var el = document.getElementById('servers-data');
    if (!el || !el.textContent) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  // Нормализация: добавляем служебные функции к данным.
  // Все поля имеют безопасные фолбэки, поэтому normalize работает с любым
  // частичным набором (и с пустым объектом).
  function normalize(data) {
    var d = data || {};

    // Приводим относительные пути к абсолютным относительно HV_BASE
    function absUrl(u) {
      if (!u) return u;
      if (/^https?:\/\//i.test(u)) return u;
      if (u.indexOf(HV_BASE) === 0) return u;
      return HV_BASE + u;
    }

    var out = {
      TEXTURE_URL: absUrl(d.textureUrl || 'assets/earth-night.jpg'),
      TEXTURE_URL_FALLBACK: d.textureUrlFallback || 'https://unpkg.com/three-globe/example/img/earth-night.jpg',
      ROTATION_MS: d.rotationMs || 90000,
      CONNECT_URL: d.connectUrl || 'https://cabinet.fortf.ru/login',
      CITIES: d.cities || {},
      CITY_INFO: d.cityInfo || {},
      CABLES: d.cables || [],
    };

    // Цвет отклика: зелёный < 80, жёлтый < 160, оранжевый < 250, красный ≥ 250
    out.pingColor = function (ping) {
      if (ping < 80) return '#34d399';
      if (ping < 160) return '#fbbf24';
      if (ping < 250) return '#fb923c';
      return '#f87171';
    };

    // Соседи города по маршрутам (для тултипа, деталей и приоритета подписей)
    out.neighborsOf = function (key) {
      var seen = {};
      var list = [];
      for (var r = 0; r < out.CABLES.length; r++) {
        var route = out.CABLES[r];
        var i = route.indexOf(key);
        if (i === -1) continue;
        if (i > 0 && !seen[route[i - 1]]) { seen[route[i - 1]] = true; list.push(route[i - 1]); }
        if (i < route.length - 1 && !seen[route[i + 1]]) { seen[route[i + 1]] = true; list.push(route[i + 1]); }
      }
      return list;
    };

    // Эмодзи-флаг (🇷🇺) → ISO-код страны (ru). Эмодзи-флаги не рендерятся
    // как флаги на Windows (показываются буквы «RU», «FI»...), поэтому флаги
    // отображаем локальными PNG из assets/flags/.
    function emojiToCode(flag) {
      if (!flag) return null;
      var chars = Array.from(flag);
      if (chars.length < 2) return null;
      var a = chars[0].codePointAt(0);
      var b = chars[1].codePointAt(0);
      if (a < 0x1f1e6 || a > 0x1f1ff || b < 0x1f1e6 || b > 0x1f1ff) return null;
      return String.fromCharCode(a - 0x1f1e6 + 65) + String.fromCharCode(b - 0x1f1e6 + 65);
    }

    // URL картинки флага по эмодзи-флагу из данных
    out.flagUrl = function (flag) {
      var code = emojiToCode(flag);
      return code ? absUrl('assets/flags/' + code.toLowerCase() + '.png') : '';
    };

    return out;
  }

  function publish(data) {
    if (published) return;
    published = true;
    window.HV_DATA = normalize(data);
    for (var i = 0; i < WAITERS.length; i++) WAITERS[i](window.HV_DATA);
    WAITERS = [];
  }

  // Пытаемся получить servers.json; при любой ошибке используем встроенные данные
  function fetchJson() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', HV_BASE + 'servers.json?_=' + Date.now(), true); // без кеша браузера
    xhr.timeout = 3000;
    xhr.onload = function () {
      if (xhr.status === 200) {
        try { publish(JSON.parse(xhr.responseText)); return; } catch (e) { /* иначе — фолбэк */ }
      }
      publish(readInlineData() || {});
    };
    xhr.onerror = function () { publish(readInlineData() || {}); };
    xhr.ontimeout = function () { publish(readInlineData() || {}); };
    xhr.send();
  }

  fetchJson();
})();
