/* ============================================
   Финансовый модуль — график Chart.js
   Стиль по remnawave-admin (useChartTheme):
   акцент --accent-from, пунктирная сетка rgba(72,79,88,.3),
   тики 11px, стеклянный тултип со светлой подложкой,
   доходы #10b981 / расходы #ef4444.
   ============================================ */

window.FinanceChart = (function () {
  'use strict';

  var chart = null;

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
      grid: light ? 'rgba(148, 163, 184, 0.3)' : 'rgba(72, 79, 88, 0.3)',
      tick: light ? '#334155' : '#c9d1d9',
      tooltipBg: 'rgba(248, 250, 252, 0.97)',
      tooltipBorder: light ? 'rgba(203, 213, 225, 0.8)' : 'rgba(148, 163, 184, 0.5)',
      tooltipText: '#0f172a'
    };
  }

  function hexToRgba(hex, alpha) {
    var h = String(hex).replace('#', '');
    if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
    var n = parseInt(h, 16);
    if (isNaN(n) || h.length !== 6) return hex;
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + alpha + ')';
  }

  function areaGradient(canvas, hexColor) {
    if (!canvas || !canvas.getContext) return hexToRgba(hexColor, 0.12);
    var ctx = canvas.getContext('2d');
    var g = ctx.createLinearGradient(0, 0, 0, 340);
    g.addColorStop(0, hexToRgba(hexColor, 0.3));
    g.addColorStop(1, hexToRgba(hexColor, 0));
    return g;
  }

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
        borderColor: '#10b981', borderWidth: 2,
        backgroundColor: isBar ? hexToRgba('#10b981', 0.85) : (isArea ? areaGradient(canvas, '#10b981') : 'rgba(0,0,0,0)'),
        fill: isArea, tension: 0.35,
        pointRadius: 0, pointHoverRadius: 4, pointHoverBackgroundColor: '#10b981'
      },
      {
        label: 'Расход', data: data.expense,
        borderColor: '#ef4444', borderWidth: 2,
        backgroundColor: isBar ? hexToRgba('#ef4444', 0.85) : (isArea ? areaGradient(canvas, '#ef4444') : 'rgba(0,0,0,0)'),
        fill: isArea, tension: 0.35,
        pointRadius: 0, pointHoverRadius: 4, pointHoverBackgroundColor: '#ef4444'
      }
    ];
    if (isBar) {
      datasets.forEach(function (ds) { ds.borderRadius = { topLeft: 3, topRight: 3, bottomLeft: 0, bottomRight: 0 }; });
    }

    // Серия «Баланс» — в том же виде, что и график (как в FIN: #fbbf24)
    if (data.balance && data.balance.some(function (v) { return v != null; })) {
      var bal = {
        label: 'Баланс',
        data: data.balance,
        borderColor: '#fbbf24',
        borderWidth: 2,
        pointRadius: 0, pointHoverRadius: 4,
        pointHoverBackgroundColor: '#fbbf24', pointBackgroundColor: '#fbbf24', pointBorderColor: '#fbbf24',
        tension: 0.35
      };
      if (isBar) {
        bal.backgroundColor = '#fbbf24';
        bal.borderRadius = { topLeft: 3, topRight: 3, bottomLeft: 0, bottomRight: 0 };
        bal.fill = false;
      } else if (isArea) {
        bal.backgroundColor = 'rgba(251, 191, 36, 0.2)';
        bal.fill = true;
      } else {
        bal.fill = false;
      }
      datasets.push(bal);
    }

    if (chart) { chart.destroy(); chart = null; }

    chart = new Chart(canvas, {
      type: isBar ? 'bar' : 'line',
      data: { labels: data.labels || [], datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: true, labels: { color: th.tick, font: { size: 11, family: fontFamily } } },
          tooltip: {
            backgroundColor: th.tooltipBg,
            borderColor: th.tooltipBorder,
            borderWidth: 1,
            cornerRadius: 8,
            titleColor: th.tooltipText,
            bodyColor: th.tooltipText,
            padding: { top: 8, right: 12, bottom: 8, left: 12 },
            titleFont: { size: 13 },
            bodyFont: { size: 13 },
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
            ticks: { color: th.tick, font: { size: 11 } }
          },
          y: {
            grid: { color: th.grid, drawBorder: false, borderDash: [3, 3] },
            border: { display: false },
            ticks: { color: th.tick, font: { size: 11 }, callback: function (v) { return fmt(v); } }
          }
        }
      }
    });
  }

  return { render: render, theme: theme };
})();
