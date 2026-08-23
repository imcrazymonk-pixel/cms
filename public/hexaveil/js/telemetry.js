// telemetry.js — телеметрия и монитор сети (расположены внутри панели серверов).
// Телеметрия читается из planet.js через API window.HV_PLANET.getTelemetry().
// (Файл раньше назывался settings.js и отвечал за настройки планеты, которых
// больше нет — имя приведено в соответствие с реальной функцией.)
(function () {
  'use strict';

  // ============ ТЕЛЕМЕТРИЯ ============
  var smoothed = 0;
  function updateTelemetry() {
    var bar = document.getElementById('telemetryBar');
    var pct = document.getElementById('telemetryPct');
    if (!bar || !pct) return;
    var t = window.HV_PLANET.getTelemetry();
    // Сглаживание: «загрузка» плавно следует за реальным числом видимых сигналов
    smoothed = smoothed === 0 ? t.load : smoothed * 0.8 + t.load * 0.2;
    var s = Math.max(4, Math.min(96, Math.round(smoothed)));
    bar.style.width = s + '%';
    pct.textContent = s + '%';
    var routes = document.getElementById('telemetryRoutes');
    if (routes) routes.textContent = t.routes;
    var speed = document.getElementById('telemetrySpeed');
    if (speed) speed.textContent = t.active;
  }

  // ============ МОНИТОР СЕТИ (терминал-лог) ============
  function addLogLine(text) {
    var log = document.getElementById('netLog');
    if (!log) return;
    var line = document.createElement('div');
    line.className = 'net-log-line';
    var now = new Date();
    var ts = now.getHours() + ':' + String(now.getMinutes()).padStart(2, '0') + ':' +
      String(now.getSeconds()).padStart(2, '0');
    line.innerHTML = '<span class="net-log-time">[' + ts + ']</span> ' + text;
    log.appendChild(line);
    while (log.children.length > 4) log.removeChild(log.firstChild);
    // подсветка новой строки
    line.classList.add('fresh');
    setTimeout(function () { line.classList.remove('fresh'); }, 1500);
  }

  function startLog(D) {
    addLogLine('Монитор сети инициализирован');
    setInterval(function () {
      var route = D.CABLES[Math.floor(Math.random() * D.CABLES.length)];
      var a = D.CITY_INFO[route[0]].ru;
      var b = D.CITY_INFO[route[route.length - 1]].ru;
      var verbs = [
        'Импульс направлен: ' + a + ' → ' + b,
        'Маршрут активен: ' + a + ' ↔ ' + b,
        'Канал синхронизирован: ' + a + ' → ' + b,
        'Пакет передан: ' + a + ' → ' + b,
      ];
      addLogLine(verbs[Math.floor(Math.random() * verbs.length)]);
    }, 2600);
  }

  window.HV_TELEMETRY = {
    updateTelemetry: updateTelemetry,
    init: function (D) {
      startLog(D);
      updateTelemetry();
      setInterval(updateTelemetry, 600);
    },
  };

  // Guard: данные должны загрузиться до нас
  if (!window.HV_DATA_WAIT) {
    console.error('telemetry.js: js/data.js не загружен (HV_DATA_WAIT не найден)');
    return;
  }
  window.HV_DATA_WAIT(function (D) {
    window.HV_TELEMETRY.init(D);
  });
})();
