// planet.js — ядро планеты: canvas-рендер, подписи, тултип, выбор сервера с подлётом.
// Данные приходят из js/data.js (window.HV_DATA_WAIT). Один источник времени
// (requestAnimationFrame) — линии всегда синхронны с картой.
(function () {
  'use strict';

  var D = null; // данные из js/data.js
  var REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var signalVelocity = 110; // единая видимая скорость сигналов, px/сек

  var canvas = document.getElementById('planetCanvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  if (!ctx) return;
  // Guard: данные должны загрузиться до нас
  if (!window.HV_DATA_WAIT) {
    console.error('planet.js: js/data.js не загружен (HV_DATA_WAIT не найден)');
    return;
  }

  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var width = 0;
  var height = 0;
  var pad = 0; // отступ от края canvas до диска (для атмосферы за кромкой)

  // Географическая координата → точка на полосе 2×ширина
  function toXY(city) {
    return {
      x: ((city.lng + 180) / 360) * width * 2,
      y: ((90 - city.lat) / 180) * height,
    };
  }

  var cables = [];
  var signals = [];

  // Бегущие сигналы: рассинхронизированные по фазам и направлению.
  // Единая видимая скорость задаётся в buildCables() по длине каждого кабеля.
  function buildSignals() {
    signals = D.CABLES.map(function (_, i) {
      return {
        t: (i * 0.13) % 1,
        speed: 0, // вычисляется после сборки кабелей
        dir: i % 2 === 0 ? 1 : -1,
      };
    });
  }

  function buildCables() {
    cables = D.CABLES.map(function (keys) {
      var pts = keys.map(function (k) { return toXY(D.CITIES[k]); });
      // Разрешаем переход через линию дат (разрыв > ширины полосы)
      for (var i = 1; i < pts.length; i++) {
        while (pts[i].x - pts[i - 1].x > width)  pts[i].x -= width * 2;
        while (pts[i].x - pts[i - 1].x < -width) pts[i].x += width * 2;
      }
      var segs = [];
      var cum = [0];
      var total = 0;
      for (var j = 1; j < pts.length; j++) {
        var dx = pts[j].x - pts[j - 1].x;
        var dy = pts[j].y - pts[j - 1].y;
        var len = Math.hypot(dx, dy);
        segs.push({ x1: pts[j - 1].x, y1: pts[j - 1].y, x2: pts[j].x, y2: pts[j].y, len: len });
        total += len;
        cum.push(total);
      }
      return { pts: pts, segs: segs, total: total, cum: cum };
    });
    // Единая видимая скорость: каждый сигнал движется с одной скоростью px/сек,
    // независимо от длины кабеля (чтобы все ускорились одинаково).
    // dt в цикле — миллисекунды, поэтому speed = доля пути за 1 мс.
    updateSignalSpeeds();
  }

  function updateSignalSpeeds() {
    for (var i = 0; i < signals.length; i++) {
      signals[i].speed = signalVelocity / ((cables[i].total || 1) * 1000);
    }
  }

  // Точка на пути по пройденной дистанции (без зацикливания)
  function pointAtDist(cable, d) {
    d = Math.max(0, Math.min(d, cable.total));
    for (var i = 0; i < cable.segs.length; i++) {
      var s = cable.segs[i];
      if (d <= s.len) {
        var f = s.len === 0 ? 0 : d / s.len;
        return { x: s.x1 + (s.x2 - s.x1) * f, y: s.y1 + (s.y2 - s.y1) * f };
      }
      d -= s.len;
    }
    var p = cable.pts[cable.pts.length - 1];
    return { x: p.x, y: p.y };
  }

  // Хвост «кометы»: ломаная кабеля от хвоста до головы — по траектории, не по прямой.
  // dir > 0 — движение вперёд (хвост позади, t уменьшается от головы);
  // dir < 0 — движение назад (хвост впереди по t).
  function pathBetween(cable, tHead, tailPx, dir) {
    var headD = Math.max(0, Math.min(tHead, 1)) * cable.total;
    var tailD = dir < 0
      ? Math.min(cable.total, headD + tailPx)
      : Math.max(0, headD - tailPx);
    var out = [pointAtDist(cable, tailD)];
    for (var i = 1; i < cable.pts.length - 1; i++) {
      var c = cable.cum[i];
      if (dir < 0 ? (c > headD && c < tailD) : (c > tailD && c < headD)) {
        out.push({ x: cable.pts[i].x, y: cable.pts[i].y });
      }
    }
    var h = pointAtDist(cable, headD);
    var last = out[out.length - 1];
    if (Math.abs(last.x - h.x) > 0.01 || Math.abs(last.y - h.y) > 0.01) out.push(h);
    return out;
  }

  var texture = null;
  var textureReady = false;

  function drawTexture(offset) {
    if (!textureReady) return;
    var w2 = width * 2;
    // Во время подлёта offset может быть отрицательным — приводим к [0, 2W)
    var o = ((offset % w2) + w2) % w2;
    ctx.drawImage(texture, -o, 0, w2, height);
    ctx.drawImage(texture, -o + w2, 0, w2, height);
  }

  function strokeCable(pts, shift, color, lw) {
    ctx.strokeStyle = color;
    ctx.lineWidth = lw;
    ctx.beginPath();
    for (var i = 0; i < pts.length; i++) {
      if (i === 0) ctx.moveTo(pts[i].x + shift, pts[i].y);
      else ctx.lineTo(pts[i].x + shift, pts[i].y);
    }
    ctx.stroke();
  }

  function drawCables(offset) {
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    var w2 = width * 2;
    for (var i = 0; i < cables.length; i++) {
      var pts = cables[i].pts;
      // Три копии (±2W) — шов невидим; -offset двигает линии вместе с картой
      var shifts = [-w2, 0, w2];
      for (var s = 0; s < shifts.length; s++) {
        strokeCable(pts, shifts[s] - offset, 'rgba(0, 220, 255, 0.1)', 4.5); // мягкое свечение
        strokeCable(pts, shifts[s] - offset, 'rgba(0, 220, 255, 0.4)', 1.1); // ядро
      }
    }
  }

  function drawSignals(offset) {
    var w2 = width * 2;
    for (var i = 0; i < cables.length; i++) {
      var cable = cables[i];
      var t = signals[i].t;
      // Затухание: сигнал плавно появляется на старте и гаснет на финише
      var fade = Math.min(1, t * 10) * Math.min(1, (1 - t) * 10);
      // Хвост фиксированной длины (до половины пути на коротких кабелях)
      var tailPx = Math.min(38, cable.total * 0.5);
      var trail = pathBetween(cable, t, tailPx, signals[i].dir);
      var head = trail[trail.length - 1];
      var first = trail[0];
      var shifts = [-w2, 0, w2];
      for (var s = 0; s < shifts.length; s++) {
        var sx = shifts[s] - offset; // сигналы вращаются вместе с картой
        var grad = ctx.createLinearGradient(first.x + sx, first.y, head.x + sx, head.y);
        grad.addColorStop(0, 'rgba(0, 240, 255, ' + (0 * fade).toFixed(3) + ')');
        grad.addColorStop(1, 'rgba(200, 250, 255, ' + (0.95 * fade).toFixed(3) + ')');
        ctx.strokeStyle = grad;
        ctx.lineWidth = 2;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        ctx.beginPath();
        for (var j = 0; j < trail.length; j++) {
          var p = trail[j];
          if (j === 0) ctx.moveTo(p.x + sx, p.y);
          else ctx.lineTo(p.x + sx, p.y);
        }
        ctx.stroke();
        ctx.fillStyle = 'rgba(230, 255, 255, ' + fade.toFixed(3) + ')';
        ctx.beginPath();
        ctx.arc(head.x + sx, head.y, 1.8, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  // Лимб-затемнение: объём сферы (внутренние тени CSS не видны поверх canvas)
  function drawLimb() {
    var cx = width / 2;
    var cy = height / 2;
    var r = Math.min(width, height) / 2;
    var g = ctx.createRadialGradient(cx, cy * 0.92, r * 0.55, cx, cy, r);
    g.addColorStop(0, 'rgba(10, 10, 26, 0)');
    g.addColorStop(1, 'rgba(10, 10, 26, 0.55)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, width, height);
  }

  // Атмосфера планеты: яркое голубое кольцо на кромке + мягкое свечение наружу.
  // Рисуется ПОСЛЕ клипа (см. render), поэтому выходит за пределы диска.
  function drawAtmosphere() {
    var cx = width / 2;
    var cy = height / 2;
    var R = Math.min(width, height) / 2;
    var outer = R * 1.4;
    var g = ctx.createRadialGradient(cx, cy, 0, cx, cy, outer);
    g.addColorStop(0.0, 'rgba(150, 200, 255, 0)');
    g.addColorStop(0.7, 'rgba(150, 200, 255, 0)');
    g.addColorStop(0.707, 'rgba(160, 215, 255, 0.5)');
    g.addColorStop(0.786, 'rgba(130, 190, 255, 0.22)');
    g.addColorStop(0.893, 'rgba(110, 170, 255, 0.08)');
    g.addColorStop(1.0, 'rgba(100, 160, 255, 0)');
    ctx.fillStyle = g;
    ctx.fillRect(-pad, -pad, width + 2 * pad, height + 2 * pad);
  }

  // Масштаб canvas относительно диска планеты: 1.4 позволяет атмосфере
  // выходить за кромку (canvas больше, чем вписанный круг планеты).
  var CANVAS_SCALE = 1.4;

  function resize() {
    var parent = canvas.parentElement;
    if (!parent) return;
    var rect = parent.getBoundingClientRect();
    width = Math.max(1, rect.width);
    height = Math.max(1, rect.height);
    // Битмап больше диска: свечение атмосферы не обрезается краем canvas
    canvas.width = Math.round(width * CANVAS_SCALE * dpr);
    canvas.height = Math.round(height * CANVAS_SCALE * dpr);
    // Центр canvas = центр диска: сдвигаем начало координат
    pad = ((canvas.width / dpr) - width) / 2;
    ctx.setTransform(dpr, 0, 0, dpr, pad * dpr, pad * dpr);
    buildCables();
    // В статичном режиме (prefers-reduced-motion) раф-цикл не идёт, поэтому
    // после resize canvas очищается и планета пропадает — перерисовываем вручную.
    if (REDUCED_MOTION) renderStatic();
  }

  // Одиночная отрисовка для режима prefers-reduced-motion: карта + кабели,
  // без бегущих сигналов и без вращения.
  function renderStatic() {
    var offset = currentOffset(performance.now());
    render(performance.now(), false, offset);
    updateLabels(offset);
  }

  // Текущее смещение карты: начальный кадр центрирован на Москве, далее вращение.
  // Пауза складывается из независимых причин: кнопка «Вращение» (rotationEnabled),
  // наведение на город (hoverPause) и выбранный сервер (selectionPause).
  // pausedOffset фиксирует кадр во время паузы; подлёт (fly) временно управляет
  // смещением сам.
  var rotationEnabled = true;
  var hoverPause = false;
  var selectionPause = false;
  var pausedOffset = null;
  var pausedAt = 0;
  var fly = null; // { from, to, start, dur } — плавный подлёт к выбранному серверу

  function isRotationPaused() {
    return !rotationEnabled || hoverPause || selectionPause;
  }

  function easeInOutCubic(p) {
    return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
  }

  function finalizeFly(now) {
    if (!fly) return;
    var to = fly.to;
    fly = null;
    var w2 = width * 2;
    pausedOffset = ((to % w2) + w2) % w2;
    pausedAt = now;
  }

  // Синхронизирует pausedOffset / startTime с текущими причинами паузы.
  function updatePause(now) {
    if (fly) return; // во время подлёта паузой управляет анимация
    if (isRotationPaused()) {
      if (pausedOffset === null) {
        pausedOffset = currentOffset(now);
        pausedAt = now;
      }
    } else if (pausedOffset !== null) {
      // Компенсируем время паузы: иначе (now − startTime) включит её,
      // и планета «проскочит» пропущенный путь.
      startTime += now - pausedAt;
      pausedOffset = null;
    }
  }

  // Смещение, центрирующее город в canvas
  function centeringOffset(key) {
    var w2 = width * 2;
    var c = D.CITIES[key];
    var sx = ((c.lng + 180) / 360) * w2;
    return ((sx - width / 2) % w2 + w2) % w2;
  }

  // Плавный подлёт к городу (в reduced-motion — мгновенный переход)
  function flyTo(key, now) {
    var w2 = width * 2;
    var target = centeringOffset(key);
    var from = currentOffset(now);
    // Кратчайший путь по зацикленной полосе
    while (target - from > w2 / 2) target -= w2;
    while (target - from < -w2 / 2) target += w2;
    if (REDUCED_MOTION) {
      pausedOffset = centeringOffset(key);
      pausedAt = now;
      renderStatic();
      return;
    }
    fly = { from: from, to: target, start: now, dur: 900 };
  }

  function currentOffset(now) {
    if (fly) {
      var p = Math.min(1, (now - fly.start) / fly.dur);
      var off = fly.from + (fly.to - fly.from) * easeInOutCubic(p);
      if (p >= 1) finalizeFly(now);
      return off;
    }
    if (pausedOffset !== null) return pausedOffset;
    var w2 = width * 2;
    var startOffset = ((D.CITIES.mow.lng + 180) / 360) * w2 - width / 2;
    if (REDUCED_MOTION) return startOffset;
    return (((startOffset + ((now - startTime) / D.ROTATION_MS) % 1 * w2) % w2) + w2) % w2;
  }

  function render(now, withSignals, offset) {
    if (offset === undefined) offset = currentOffset(now);
    ctx.clearRect(-pad, -pad, width + 2 * pad, height + 2 * pad);

    // Контент планеты (карта, кабели, сигналы) обрезаем по кругу диска
    var cx = width / 2;
    var cy = height / 2;
    var R = Math.min(width, height) / 2;
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.clip();
    drawTexture(offset);
    if (cablesVisible) drawCables(offset);
    if (withSignals) drawSignals(offset);
    drawSelection(offset);
    drawLimb();
    ctx.restore();

    // Атмосфера — вне клипа, поэтому свечение выходит за кромку диска
    drawAtmosphere();
  }

  var startTime = 0;
  var last = 0;
  var raf = null;
  var frame = 0; // счётчик кадров для троттлинга подписей

  function startRendering() {
    if (!raf) raf = requestAnimationFrame(loop);
  }

  function stopRendering() {
    if (raf) {
      cancelAnimationFrame(raf);
      raf = null;
    }
  }

  // ============ ПОДПИСИ ГОРОДОВ И ТУЛТИП ============
  var labels = [];
  var tooltip = null;
  var lastMouse = { x: 0, y: 0 };

  function buildLabels() {
    var layer = document.getElementById('planetLabels');
    if (!layer) return;
    layer.innerHTML = '';
    labels = Object.keys(D.CITY_INFO).map(function (key) {
      var info = D.CITY_INFO[key];
      // Точки, не являющиеся серверами присутствия: маршрут проходит через них, но хаба нет
      if (info.hub === false) return null;
      var el = document.createElement('div');
      // Недоступные серверы — серые точки (визуально отличимы от живых)
      el.className = 'planet-label' + (info.connected === false ? ' offline' : '');
      el.innerHTML =
        '<span class="dot"></span>' +
        '<span class="planet-label-text">' + info.ru +
          '<span class="planet-label-ping">' + (info.connected === false ? 'n/a' : info.ping + ' мс') + '</span>' +
        '</span>';
      el.addEventListener('mouseenter', function () {
        hoverPause = true;
        updatePause(performance.now());
        showTooltip(key);
      });
      el.addEventListener('mouseleave', function () {
        hoverPause = false;
        updatePause(performance.now());
        hideTooltip();
      });
      // Клик по узлу на планете → выбор сервера (двусторонняя связь)
      el.addEventListener('click', function (e) {
        e.stopPropagation();
        selectServer(key);
      });
      layer.appendChild(el);
      return {
        key: key,
        el: el,
        textEl: el.querySelector('.planet-label-text'),
        info: info,
        prio: D.neighborsOf(key).length,
        blocked: 0,
        choice: null,
      };
    }).filter(Boolean);
  }

  function buildTooltip() {
    tooltip = document.createElement('div');
    tooltip.className = 'planet-tooltip';
    document.body.appendChild(tooltip);
    document.addEventListener('mousemove', function (e) {
      lastMouse.x = e.clientX;
      lastMouse.y = e.clientY;
      if (tooltip.style.display === 'block') positionTooltip();
    }, true);
  }

  function showTooltip(key) {
    if (!tooltip) return;
    var info = D.CITY_INFO[key];
    var city = D.CITIES[key];
    var neighbors = D.neighborsOf(key);
    var latDir = city.lat >= 0 ? 'N' : 'S';
    var lngDir = city.lng >= 0 ? 'E' : 'W';
    var offline = info.connected === false;
    // У недоступных серверов отклик — «n/a», статус — OFFLINE
    var pingHtml = offline
      ? '<span class="tt-ping" style="color:#f87171">n/a</span>'
      : '<span class="tt-ping" style="color:' + D.pingColor(info.ping) + '">' +
          info.ping + ' мс</span>';
    var statusHtml = offline
      ? '<span class="tt-status tt-status-offline">OFFLINE</span>'
      : '<span class="tt-status">ONLINE</span>';
    tooltip.innerHTML =
      '<div class="tt-title">' + info.ru + '</div>' +
      '<div class="tt-sub">' + info.en + '</div>' +
      '<table>' +
        '<tr><td>Страна</td><td>' + info.country + '</td></tr>' +
        '<tr><td>Координаты</td><td>' + Math.abs(city.lat).toFixed(1) + '°' + latDir + ', ' +
          Math.abs(city.lng).toFixed(1) + '°' + lngDir + '</td></tr>' +
        '<tr><td>Отклик</td><td>' + pingHtml + '</td></tr>' +
        '<tr><td>Соединений</td><td>' + neighbors.length + '</td></tr>' +
        '<tr><td>Соседи</td><td>' +
          neighbors.map(function (n) { return D.CITY_INFO[n].ru; }).join(', ') + '</td></tr>' +
        '<tr><td>Статус</td><td>' + statusHtml + '</td></tr>' +
      '</table>' +
      '<div class="tt-note">Отклик замерен из Москвы</div>';
    tooltip.style.display = 'block';
    positionTooltip();
  }

  function hideTooltip() {
    if (tooltip) tooltip.style.display = 'none';
  }

  function positionTooltip() {
    if (!tooltip || tooltip.style.display !== 'block') return;
    var padX = 16;
    var x = lastMouse.x + padX;
    var y = lastMouse.y + padX;
    if (x + tooltip.offsetWidth > window.innerWidth - 8) x = lastMouse.x - tooltip.offsetWidth - padX;
    if (y + tooltip.offsetHeight > window.innerHeight - 8) y = lastMouse.y - tooltip.offsetHeight - padX;
    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';
  }

  // Позиционирование подписей каждый кадр (вращаются вместе с картой).
  // Точка всегда на городе; текст — на постоянном смещении от точки (dx, dy),
  // поэтому он движется вместе с ней при вращении.
  // Коллизии разрешаются сменой смещения (текст влево/вправо, вверх/вниз).
  // У края круга — затухание по opacity; скрытие только когда некуда встать,
  // и с гистерезисом (blocked), чтобы не мерцало.
  function updateLabels(offset) {
    if (!labels.length) return;
    var w2 = width * 2;
    var cx = width / 2;
    var cy = height / 2;
    var R = Math.min(width, height) / 2 - 8;
    var FADE = 16;
    var TEXT_H = 16;

    var candidates = [];
    for (var i = 0; i < labels.length; i++) {
      var item = labels[i];
      var city = D.CITIES[item.key];
      var sx = ((city.lng + 180) / 360) * w2;
      var y = ((90 - city.lat) / 180) * height;
      var x = ((sx - offset) % w2 + w2) % w2;
      if (x > width) x -= w2;
      var d = Math.hypot(x - cx, y - cy);
      candidates.push({
        item: item,
        x: x, // центр точки = позиция города
        y: y,
        textW: item.info.ru.length * 6 + 12,
        edgeDist: R - d,
        // Выбранный сервер всегда размещается первым, чтобы его подпись была
        // у его точки, а соседние подписи (например Хельсинки рядом с СПб)
        // не наезжали на него.
        prio: item.key === selectedServer ? 1e9 : item.prio,
      });
    }
    candidates.sort(function (a, b) { return b.prio - a.prio; });

    // Жадное размещение: выбираем относительное смещение текста от точки
    var placed = [];
    for (var c = 0; c < candidates.length; c++) {
      var cand = candidates[c];
      var opts = [];
      // Стабильность: пробуем прошлый выбор первым
      if (cand.item.choice) opts.push(cand.item.choice);
      opts.push({ dx: 10, dy: 0 });                       // текст вправо
      opts.push({ dx: -8 - cand.textW, dy: 0 });          // текст влево (флип)
      var dys = [16, -16, 32, -32];
      for (var k = 0; k < dys.length; k++) {
        opts.push({ dx: 10, dy: dys[k] });
      }
      var chosen = null;
      for (var o = 0; o < opts.length; o++) {
        if (fits(cand, opts[o], placed)) { chosen = opts[o]; break; }
      }
      if (chosen) {
        cand.item.choice = chosen;
        cand.item.blocked = 0;
        placed.push({
          left: cand.x + chosen.dx,
          right: cand.x + chosen.dx + cand.textW,
          top: cand.y + chosen.dy,
          bottom: cand.y + chosen.dy + TEXT_H,
        });
      } else {
        cand.item.choice = null;
        if (cand.item.blocked < 8) cand.item.blocked++; // гистерезис
      }
    }

    // Применяем видимость и позиции
    for (var i2 = 0; i2 < candidates.length; i2++) {
      var cc = candidates[i2];
      var it = cc.item;
      var isSelected = it.key === selectedServer;
      it.el.classList.toggle('selected', isSelected);
      if (cc.edgeDist < 0) {
        it.el.style.opacity = '0';
        it.el.style.pointerEvents = 'none';
        continue;
      }
      var edgeFade = Math.max(0, Math.min(1, cc.edgeDist / FADE));
      var declutterFade = it.blocked > 0 ? 0 : 1;
      // Выбранный сервер не прячем из-за коллизий — он всегда виден
      var opacity = isSelected ? edgeFade : edgeFade * declutterFade;
      it.el.style.opacity = opacity.toFixed(3);
      it.el.style.pointerEvents = opacity > 0.05 ? 'auto' : 'none';
      // Точка привязана к городу (left/top = x−2, y−2 для 4px точки)
      it.el.style.left = (cc.x - 2) + 'px';
      it.el.style.top = (cc.y - 2) + 'px';
      // Текст — на постоянном смещении от точки (движется вместе с ней)
      if (it.choice) {
        it.textEl.style.left = it.choice.dx + 'px';
        it.textEl.style.top = it.choice.dy + 'px';
      }
    }
  }

  function fits(cand, o, placed) {
    var left = cand.x + o.dx;
    var top = cand.y + o.dy;
    var right = left + cand.textW;
    var bottom = top + 16;
    for (var i = 0; i < placed.length; i++) {
      var p = placed[i];
      if (left < p.right && right > p.left && top < p.bottom && bottom > p.top) return false;
    }
    return true;
  }

  // ============ ВЫБОР СЕРВЕРА ============
  var selectedServer = null;
  var cablesVisible = true;

  function selectServer(key, toggle) {
    var now = performance.now();
    if (toggle !== false && selectedServer === key) {
      // Повторный клик — снять выделение: вращение возобновляется
      selectedServer = null;
      selectionPause = false;
      if (fly) finalizeFly(now);
      updatePause(now);
      if (REDUCED_MOTION) renderStatic();
    } else {
      selectedServer = key;
      selectionPause = true;
      if (fly) finalizeFly(now); // обрываем предыдущий подлёт на текущей позиции
      flyTo(key, now);
    }
    if (window.HV_PANEL && window.HV_PANEL.refresh) window.HV_PANEL.refresh(selectedServer);
  }

  // Подсветка выбранного сервера на планете: пульсирующее кольцо,
  // точка и пунктирная линия «Вы (Москва) → сервер»
  function drawSelection(offset) {
    if (!selectedServer) return;
    var w2 = width * 2;
    var cx = width / 2;
    var cy = height / 2;
    var R = Math.min(width, height) / 2;

    var toCanvas = function (key) {
      var c = D.CITIES[key];
      var sx = ((c.lng + 180) / 360) * w2;
      var x = ((sx - offset) % w2 + w2) % w2;
      if (x > width) x -= w2;
      return { x: x, y: ((90 - c.lat) / 180) * height };
    };

    var server = toCanvas(selectedServer);
    if (Math.hypot(server.x - cx, server.y - cy) > R) return; // узел за краем

    var t = (performance.now() / 1000) % 1;
    var pulse = 1 - t;
    // Недоступный сервер — красное кольцо вместо голубого
    var offline = D.CITY_INFO[selectedServer] && D.CITY_INFO[selectedServer].connected === false;
    var ringBase = offline ? 'rgba(248, 113, 113,' : 'rgba(0, 240, 255,';

    // Пульсирующее кольцо
    ctx.beginPath();
    ctx.arc(server.x, server.y, 8 + t * 12, 0, Math.PI * 2);
    ctx.strokeStyle = ringBase + (0.8 * pulse).toFixed(3) + ')';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = ringBase + '0.95)';
    ctx.beginPath();
    ctx.arc(server.x, server.y, 4, 0, Math.PI * 2);
    ctx.fill();

    // Пунктирная линия «Вы → сервер» из Москвы + точка «Вы»
    if (selectedServer !== 'mow') {
      var from = toCanvas('mow');
      if (Math.hypot(from.x - cx, from.y - cy) <= R) {
        ctx.strokeStyle = 'rgba(52, 211, 153, 0.6)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(server.x, server.y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(52, 211, 153, 1)';
        ctx.beginPath();
        ctx.arc(from.x, from.y, 3.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  // ============ НАСТРОЙКИ (через API для settings.js) ============
  function setRotation(on) {
    rotationEnabled = on;
    updatePause(performance.now());
  }

  function setCablesVisible(v) {
    cablesVisible = v;
  }

  function setSpeed(px) {
    signalVelocity = px;
    updateSignalSpeeds();
  }

  // Реальная телеметрия: видимые сигналы и доля задействованной магистрали
  function getTelemetry() {
    var w2 = width * 2;
    var o = currentOffset(performance.now());
    var active = 0;
    for (var i = 0; i < signals.length; i++) {
      var cable = cables[i];
      var head = pointAtDist(cable, signals[i].t * cable.total);
      var x = ((head.x - o) % w2 + w2) % w2;
      if (x > width) x -= w2;
      if (x >= 0 && x <= width && head.y >= 0 && head.y <= height) active++;
    }
    return {
      routes: cables.length,
      active: active,
      load: Math.round((active / Math.max(1, signals.length)) * 100),
    };
  }

  // ============ ТЕКСТУРА ============
  function loadTexture() {
    var tryLoad = function (url, cross) {
      var img = new Image();
      if (cross) img.crossOrigin = 'anonymous';
      img.onload = function () {
        texture = img;
        textureReady = true;
        onTextureReady();
      };
      img.onerror = function () {
        // Локальная копия не открылась — пробуем удалённую (и наоборот)
        if (url !== D.TEXTURE_URL_FALLBACK) tryLoad(D.TEXTURE_URL_FALLBACK, false);
      };
      img.src = url;
    };
    tryLoad(D.TEXTURE_URL, true);
  }

  // Текстура грузится асинхронно и может прийти уже после статичной отрисовки.
  // В reduced-motion раф-цикл не идёт, поэтому перерисовываем вручную.
  function onTextureReady() {
    if (REDUCED_MOTION) renderStatic();
  }

  function loop(now) {
    var dt = Math.min(now - last, 100); // защита от скачков при вкладке в фоне
    last = now;
    for (var i = 0; i < signals.length; i++) {
      signals[i].t = (signals[i].t + signals[i].speed * signals[i].dir * dt) % 1;
      if (signals[i].t < 0) signals[i].t += 1;
    }
    var offset = currentOffset(now);
    render(now, true, offset);
    // Подписи — DOM-записи по 17 элементам, каждый кадр это дорого на мобильных.
    // Обновляем через кадр: при 60fps визуально это незаметно.
    if ((frame++ & 1) === 0) updateLabels(offset);
    raf = requestAnimationFrame(loop);
  }

  function init() {
    startTime = performance.now();
    last = startTime;
    resize();
    loadTexture();
    buildLabels();
    buildTooltip();
    window.addEventListener('resize', resize);
    // Не тратим ресурсы на отрисовку планеты, когда она за экраном
    // (особенно важно на мобильных).
    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) startRendering();
          else stopRendering();
        });
      }, { rootMargin: '150px' });
      observer.observe(canvas);
    }
    if (REDUCED_MOTION) {
      renderStatic();
    } else {
      startRendering();
    }
  }

  // Данные приходят асинхронно (js/data.js): ждём их, затем стартуем
  window.HV_DATA_WAIT(function (data) {
    D = data;
    buildSignals();
    init();
  });

  // Публичный API для server-panel.js и settings.js
  window.HV_PLANET = {
    selectServer: selectServer,
    setRotation: setRotation,
    setCablesVisible: setCablesVisible,
    setSpeed: setSpeed,
    getTelemetry: getTelemetry,
    get speed() { return signalVelocity; },
    get selected() { return selectedServer; },
  };

  // Debug-хендл для проверки (не влияет на работу)
  window.__planetDebug = {
    get signals() { return signals.map(function (s) { return +((s.t % 1).toFixed(3)); }); },
    get speeds() { return signals.map(function (s) { return +(s.speed * 1000).toFixed(3); }); },
    cableLen: function (idx) { return Math.round(cables[idx].total); },
    get cablesCount() { return cables.length; },
    get textureReady() { return textureReady; },
    get animating() { return !!raf; },
    get offset() { return Math.round(currentOffset(performance.now())); },
    get selected() { return selectedServer; },
    canvasPos: function (key) {
      var o = currentOffset(performance.now());
      var c = D.CITIES[key];
      var w2 = width * 2;
      var x = ((c.lng + 180) / 360) * w2 - o;
      while (x < -w2 / 2) x += w2;
      while (x > w2 / 2) x -= w2;
      return [Math.round(x), Math.round(((90 - c.lat) / 180) * height)];
    },
    moscowCanvasPos: function () {
      var o = currentOffset(performance.now());
      var x = ((D.CITIES.mow.lng + 180) / 360) * width * 2 - o;
      var y = ((90 - D.CITIES.mow.lat) / 180) * height;
      return [Math.round(x), Math.round(y)];
    },
    trail: function (idx, t) {
      var c = cables[idx];
      return pathBetween(c, t, Math.min(38, c.total * 0.5)).map(function (p) {
        return [Math.round(p.x), Math.round(p.y)];
      });
    },
    headPos: function (idx) {
      var c = cables[idx];
      var offset = currentOffset(performance.now());
      var trail = pathBetween(c, signals[idx].t, Math.min(38, c.total * 0.5));
      var h = trail[trail.length - 1];
      // canvas-координата головы (с учётом вращения карты)
      return [Math.round(h.x - offset), Math.round(h.y), +signals[idx].t.toFixed(3)];
    },
    vertices: function (idx) {
      return cables[idx].pts.map(function (p) { return [Math.round(p.x), Math.round(p.y)]; });
    },
  };
})();
