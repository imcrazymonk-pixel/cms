/* ============================================
   Финансовый модуль — график Chart.js
   Стиль по remnawave-admin (useChartTheme):
   акцент --accent-from, пунктирная сетка rgba(72,79,88,.3),
   тики 11px, стеклянный тултип со светлой подложкой,
   доходы #10b981 / расходы #ef4444 (приглушённые).
   ============================================ */

window.FinanceChart = (function () {
  'use strict';

  var chart = null;
  var legend = null; // HTML-легенда

  function isLight() {
    return (document.documentElement.getAttribute('data-mode') || 'dark') === 'light';
  }

  function cssVar(name, fb) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fb;
  }

  function theme() {
    var light = isLight();
    return {
      accent: cssVar('--accent-from', '#6366f1'),
      grid: light ? 'rgba(148, 163, 184, 0.2)' : 'rgba(72, 79, 88, 0.2)',
      tick: light ? '#334155' : '#c9d1d9',
      tooltipBg: light ? 'rgba(248, 250, 252, 0.97)' : 'rgba(15, 19, 24, 0.96)',
      tooltipBorder: light ? 'rgba(203, 213, 225, 0.8)' : 'rgba(30, 35, 45, 0.9)',
      tooltipText: light ? '#0f172a' : '#e2e8f0'
    };
  }

  function hexToRgba(hex, alpha) {
    var h = String(hex).replace('#', '');
    if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
    var n = parseInt(h, 16);
    if (isNaN(n) || h.length !== 6) return hex;
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + alpha + ')';
  }

  function barGradient(canvas, hexColor, alpha) {
    if (!canvas || !canvas.getContext) return hexToRgba(hexColor, alpha);
    var ctx = canvas.getContext('2d');
    var g = ctx.createLinearGradient(0, 0, 0, 300);
    g.addColorStop(0, hexToRgba(hexColor, 0.9));
    g.addColorStop(1, hexToRgba(hexColor, 0.3));
    return g;
  }

  function areaGradient(canvas, hexColor) {
    if (!canvas || !canvas.getContext) return hexToRgba(hexColor, 0.12);
    var ctx = canvas.getContext('2d');
    var g = ctx.createLinearGradient(0, 0, 0, 340);
    g.addColorStop(0, hexToRgba(hexColor, 0.25));
    g.addColorStop(1, hexToRgba(hexColor, 0));
    return g;
  }

  // Цвета — приглушённые (не #22c55e / #ef4444, а tinted)
  var INCOME_COLOR = '#34d399';
  var EXPENSE_COLOR = '#fb7185';
  var BALANCE_COLOR = '#fbbf24';

  /**
   * Отрисовать/обновить график.
   * @param canvas <canvas>
   * @param data {labels: [], income: [], expense: []}
   * @param opts {chartType: 'bar'|'line'|'area', fmt: fn(v)->str, fontFamily: str}
   */
  function render(canvas, data, opts) {
    if (!canvas) return;
    var th = theme();
    var fmt = (opts && opts.fmt) || function (v) { return String(v); };
    var type = (opts && opts.chartType) || 'bar';
    var isBar = type === 'bar';
    var isArea = type === 'area';
    var fontFamily = (opts && opts.fontFamily) || cssVar('--font-sans', 'sans-serif');

    var datasets = [
      {
        label: 'Доход', data: data.income,
        borderColor: INCOME_COLOR, borderWidth: 2,
        backgroundColor: isBar ? barGradient(canvas, INCOME_COLOR, 0.85) : (isArea ? areaGradient(canvas, INCOME_COLOR) : hexToRgba(INCOME_COLOR, 0.15)),
        fill: isArea, tension: 0.35,
        pointRadius: 0, pointHoverRadius: 4, pointHoverBackgroundColor: INCOME_COLOR
      },
      {
        label: 'Расход', data: data.expense,
        borderColor: EXPENSE_COLOR, borderWidth: 2,
        backgroundColor: isBar ? barGradient(canvas, EXPENSE_COLOR, 0.85) : (isArea ? areaGradient(canvas, EXPENSE_COLOR) : hexToRgba(EXPENSE_COLOR, 0.15)),
        fill: isArea, tension: 0.35,
        pointRadius: 0, pointHoverRadius: 4, pointHoverBackgroundColor: EXPENSE_COLOR
      }
    ];
    if (isBar) {
      datasets.forEach(function (ds) {
        ds.borderRadius = { topLeft: 6, topRight: 6, bottomLeft: 0, bottomRight: 0 };
        ds.categoryPercentage = 0.8;
        ds.barPercentage = 0.7;
      });
    }

    // Серия «Баланс»
    if (data.balance && data.balance.some(function (v) { return v != null; })) {
      var bal = {
        label: 'Баланс',
        data: data.balance,
        borderColor: BALANCE_COLOR,
        borderWidth: 2,
        pointRadius: 0, pointHoverRadius: 4,
        pointHoverBackgroundColor: BALANCE_COLOR, pointBackgroundColor: BALANCE_COLOR, pointBorderColor: BALANCE_COLOR,
        tension: 0.35
      };
      if (isBar) {
        bal.backgroundColor = hexToRgba(BALANCE_COLOR, 0.85);
        bal.borderRadius = { topLeft: 6, topRight: 6, bottomLeft: 0, bottomRight: 0 };
        bal.fill = false;
        bal.categoryPercentage = 0.8;
        bal.barPercentage = 0.7;
      } else if (isArea) {
        bal.backgroundColor = hexToRgba(BALANCE_COLOR, 0.15);
        bal.fill = true;
      } else {
        bal.fill = false;
      }
      datasets.push(bal);
    }

    if (chart) { chart.destroy(); chart = null; }

    // Рендерим HTML-легенду вручную
    renderLegend(canvas, datasets, fontFamily);

    chart = new Chart(canvas, {
      type: isBar ? 'bar' : 'line',
      data: { labels: data.labels || [], datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false }, // HTML-легенда вместо дефолтной
          tooltip: {
            backgroundColor: th.tooltipBg,
            borderColor: th.tooltipBorder,
            borderWidth: 1,
            cornerRadius: 10,
            titleColor: th.tooltipText,
            bodyColor: th.tooltipText,
            padding: { top: 10, right: 14, bottom: 10, left: 14 },
            titleFont: { size: 13, family: fontFamily },
            bodyFont: { size: 13, family: fontFamily },
            boxPadding: 6,
            usePointStyle: true,
            callbacks: {
              label: function (c) {
                var v = c.parsed.y != null ? c.parsed.y : c.parsed;
                return c.dataset.label + ': ' + fmt(v);
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: th.tick,
              font: { size: 10, family: fontFamily },
              autoSkip: true,
              maxTicksLimit: 12,
              maxRotation: 35,
              minRotation: 0
            }
          },
          y: {
            grid: { color: th.grid, drawBorder: false, borderDash: [3, 3] },
            border: { display: false },
            ticks: {
              color: th.tick,
              font: { size: 11, family: fontFamily },
              callback: function (v) { return fmt(v); },
              maxTicksLimit: 6
            }
          }
        }
      }
    });
  }

  /** HTML-легенда: цветной кружок + текст, над canvas */
  function renderLegend(canvas, datasets, fontFamily) {
    var container = canvas.parentElement;
    if (!container) return;

    // Удаляем старую легенду если есть
    var old = container.querySelector('.chart-html-legend');
    if (old) old.remove();

    var el = document.createElement('div');
    el.className = 'chart-html-legend';
    el.style.cssText = 'display:flex;gap:20px;justify-content:center;margin-bottom:8px;flex-wrap:wrap;';

    datasets.forEach(function (ds) {
      var color = ds.borderColor || ds.backgroundColor || '#6366f1';
      var item = document.createElement('span');
      item.style.cssText = 'display:inline-flex;align-items:center;gap:6px;font-size:0.857rem;color:var(--text-muted);font-family:' + fontFamily + ';';
      item.innerHTML = '<span style="display:inline-block;width:10px;height:10px;border-radius:9999px;background:' + color + ';flex-shrink:0;"></span>'
        + ds.label;
      el.appendChild(item);
    });

    container.insertBefore(el, canvas);
  }

  return { render: render, theme: theme };
})();
