/* ============================================
   Финансовый модуль — клиентская логика
   График стилизован по remnawave-admin (useChartTheme):
   акцент --accent-from, пунктирная сетка, тики 11px,
   стеклянный тултип со светлой подложкой, income #10b981 / expense #ef4444.
   ============================================ */

(function () {
  'use strict';

  var CSRF = (window.FIN && window.FIN.csrf) || '';

  var DEFAULTS = {
    currency: '₽', decimals: 2, auto_refresh: 0, avg_period: 'day',
    avg_exclude_categories: [], avg_exclude_income_keywords: [],
    avg_exclude_expense_keywords: [], quick_categories: [], quick_participants: []
  };
  var settings = Object.assign({}, DEFAULTS, (window.FIN && window.FIN.settings) || {});

  var state = {
    month: '', type: '', q: '', page: 1, per_page: 25,
    sort: 'date', dir: 'desc',
    scale: 'month', chartType: 'bar', range: 'all', anomalies: false
  };

  var lastData = null;
  var autoTimer = null;
  var qDebounce = null;
  var pendingDelete = null;


  /* ─────── Утилиты ─────── */
  function qs(sel) { return document.querySelector(sel); }
  function qsa(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  function esc(s) { var d = document.createElement('div'); d.textContent = String(s == null ? '' : s); return d.innerHTML; }

  function fmtMoney(v) {
    var n = Number(v) || 0;
    var dec = Math.min(6, Math.max(0, Number(settings.decimals) || 0));
    return n.toLocaleString('ru-RU', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + ' ' + settings.currency;
  }

  function toast(msg) {
    var el = qs('#finToast');
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.hidden = true; }, 2600);
  }

  function showModal(id) { qs('#' + id).hidden = false; }
  function hideModal(id) { qs('#' + id).hidden = true; }

  function showError(sel, msg) {
    var el = qs(sel);
    if (!el) return;
    el.textContent = msg;
    el.hidden = false;
  }

  function iconSvg(name) {
    var paths = {
      edit: '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/>',
      delete: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>'
    };
    return '<span class="icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + (paths[name] || '') + '</svg></span>';
  }

  function isoLocal(d) {
    var m = String(d.getMonth() + 1).padStart(2, '0');
    return d.getFullYear() + '-' + m + '-' + String(d.getDate()).padStart(2, '0');
  }


  /* ─────── Загрузка данных ─────── */
  function rangeSince(r) {
    var d = new Date();
    switch (r) {
      case '7d': d.setDate(d.getDate() - 7); return isoLocal(d);
      case '1m': d.setMonth(d.getMonth() - 1); return isoLocal(d);
      case '3m': d.setMonth(d.getMonth() - 3); return isoLocal(d);
      case '1y': d.setFullYear(d.getFullYear() - 1); return isoLocal(d);
      default: return '';
    }
  }

  function buildQuery() {
    var p = new URLSearchParams();
    p.set('page', state.page);
    p.set('per_page', state.per_page);
    p.set('sort', state.sort);
    p.set('dir', state.dir);
    if (state.range !== 'all') {
      p.set('since', rangeSince(state.range));
    } else if (state.month) {
      p.set('month', state.month);
    }
    if (state.type) p.set('type', state.type);
    if (state.q) p.set('q', state.q);
    return p.toString();
  }

  function loadData() {
    fetch('/admin/finance/api/data?' + buildQuery(), {
      headers: { 'Accept': 'application/json' }
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        lastData = data;
        render(data);
        startAutoRefresh(data.settings);
      })
      .catch(function (err) {
        qs('#fin-tbody').innerHTML = '<tr><td colspan="7" class="fin-empty-cell">Ошибка загрузки данных: ' + esc(err.message) + '</td></tr>';
        console.error('[Finance] loadData error:', err);
      });
  }

  function startAutoRefresh(s) {
    var sec = s && Number(s.auto_refresh) || 0;
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
    if (sec > 0) autoTimer = setInterval(loadData, sec * 1000);
  }

  function initPlatega() {
    startPlategaAutoSync();
  }


  /* ─────── Рендер ─────── */
  function render(data) {
    renderSummary(data);
    renderChart();
    renderTable();
    renderPagination();
    renderDatalists(data);
  }

  function renderSummary(d) {
    var s = d.summary || {}, av = d.averages || {};
    var period = settings.avg_period || 'day';
    var iAvg = av.avg_income ? av.avg_income[period] : 0;
    var eAvg = av.avg_expense ? av.avg_expense[period] : 0;
    var labels = { day: 'в день', week: 'в неделю', month: 'в месяц', year: 'в год' };

    qs('#fin-income').textContent = fmtMoney(s.income);
    qs('#fin-expense').textContent = fmtMoney(s.expense);
    qs('#fin-balance').textContent = fmtMoney(s.balance);
    qs('#fin-count').textContent = String(s.count != null ? s.count : (d.pagination ? d.pagination.total : 0));

    var bal = qs('#fin-balance');
    bal.classList.remove('is-income', 'is-expense');
    if ((s.balance || 0) > 0) bal.classList.add('is-income');
    else if ((s.balance || 0) < 0) bal.classList.add('is-expense');

    qs('#fin-income-avg').textContent = 'Средний ' + fmtMoney(iAvg) + ' ' + (labels[period] || '');
    qs('#fin-expense-avg').textContent = 'Средний ' + fmtMoney(eAvg) + ' ' + (labels[period] || '');
    qs('#fin-balance-hint').textContent = 'Доходы − расходы';
    qs('#fin-count-hint').textContent = 'Всего операций';
  }

  function renderChart() {
    var chartKey = { day: 'daily', week: 'weekly', month: 'monthly', year: 'yearly' }[state.scale] || 'monthly';
    var series = (lastData.chart && lastData.chart[chartKey]) || [];
    window.FinanceChart.render(qs('#finChart'), {
      labels: series.map(function (s) { return s.label; }),
      income: series.map(function (s) { return s.income; }),
      expense: series.map(function (s) { return s.expense; }),
      balance: series.map(function (s) { return s.balance != null ? s.balance : null; })
    }, { chartType: state.chartType, fmt: fmtMoney });
  }

  function renderTable() {
    var tb = qs('#fin-tbody');
    var rows = (lastData.transactions) || [];
    var anom = lastData.anomalies || [];
    var anomSet = {};
    anom.forEach(function (id) { anomSet[id] = true; });

    if (!rows.length) {
      tb.innerHTML = '<tr><td colspan="7" class="fin-empty-cell">Нет транзакций. Нажмите «Добавить» или импортируйте CSV.</td></tr>';
      return;
    }

    tb.innerHTML = rows.map(function (r) {
      var isIn = r.type === 'income';
      var badge = isIn ? 'badge-income' : 'badge-expense';
      var sign = isIn ? '+' : '−';
      var anomaly = state.anomalies && anomSet[r.id]
        ? '<span class="fin-anomaly-dot" title="Аномалия (значение сильно выше среднего)"></span>'
        : '';
      return '<tr class="' + (state.anomalies && anomSet[r.id] ? 'fin-row-anomaly' : '') + '">' +
        '<td class="fin-date">' + esc(r.date_display) + '</td>' +
        '<td><span class="' + badge + '">' + (isIn ? 'Доход' : 'Расход') + '</span></td>' +
        '<td>' + esc(r.category) + '</td>' +
        '<td>' + esc(r.participant) + '</td>' +
        '<td class="fin-amt ' + (isIn ? 'is-income' : 'is-expense') + '">' + sign + ' ' + fmtMoney(r.amount) + '</td>' +
        '<td class="fin-desc" title="' + esc(r.description) + '">' + esc(r.description) + '</td>' +
        '<td class="fin-actions-col">' + anomaly +
        '<button type="button" class="btn btn-sm btn-ghost fin-edit" data-id="' + r.id + '" title="Редактировать">' + iconSvg('edit') + '</button>' +
        '<button type="button" class="btn btn-sm btn-ghost fin-del" data-id="' + r.id + '" title="Удалить">' + iconSvg('delete') + '</button>' +
        '</td></tr>';
    }).join('');
  }

  function renderPagination() {
    var p = lastData.pagination || { page: 1, total: 0, pages: 1 };
    qs('#fin-total').textContent = 'Всего: ' + p.total;
    var el = qs('#fin-pagination');
    if (p.pages <= 1) { el.innerHTML = ''; return; }
    var cur = p.page;
    var html = '';
    if (cur > 1) html += '<a href="#" class="page-link" data-page="' + (cur - 1) + '">‹</a>';
    var start = Math.max(1, cur - 2), end = Math.min(p.pages, cur + 2);
    for (var i = start; i <= end; i++) {
      html += '<a href="#" class="page-link' + (i === cur ? ' active' : '') + '" data-page="' + i + '">' + i + '</a>';
    }
    if (cur < p.pages) html += '<a href="#" class="page-link" data-page="' + (cur + 1) + '">›</a>';
    el.innerHTML = html;
  }

  function renderDatalists(d) {
    var cats = (d.all_categories || []).map(function (c) { return '<option value="' + esc(c) + '">'; }).join('');
    var parts = (d.all_participants || []).map(function (p) { return '<option value="' + esc(p) + '">'; }).join('');
    qs('#finCatList').innerHTML = cats;
    qs('#finPartList').innerHTML = parts;
  }


  function openAdd(id) {
    qs('#finTxnId').value = '';
    qs('#finTxnDate').value = isoLocal(new Date());
    qs('#finTxnType').value = 'expense';
    qs('#finTxnCategory').value = '';
    qs('#finTxnParticipant').value = '';
    qs('#finTxnAmount').value = '';
    qs('#finTxnDescription').value = '';
    qs('#finTxnError').hidden = true;

    if (id != null) {
      var row = null;
      (lastData.transactions || []).some(function (r) { if (r.id === id) { row = r; return true; } return false; });
      if (row) {
        qs('#finTxnId').value = row.id;
        qs('#finTxnDate').value = row.date;
        qs('#finTxnType').value = row.type;
        qs('#finTxnCategory').value = row.category;
        qs('#finTxnParticipant').value = row.participant || '';
        qs('#finTxnAmount').value = row.amount;
        qs('#finTxnDescription').value = row.description || '';
      }
    }

    qs('#finModalTitle').textContent = id != null ? 'Редактировать операцию' : 'Добавить операцию';
    showModal('finModal');
  }

  function saveTxn() {
    var id = qs('#finTxnId').value;
    var payload = {
      csrf_token: CSRF,
      date: qs('#finTxnDate').value,
      type: qs('#finTxnType').value,
      category: qs('#finTxnCategory').value,
      participant: qs('#finTxnParticipant').value,
      amount: qs('#finTxnAmount').value,
      description: qs('#finTxnDescription').value
    };
    if (id) payload.id = Number(id);
    if (!payload.date || !payload.category.trim() || !(Number(payload.amount) > 0)) {
      showError('#finTxnError', 'Заполните дату, категорию и сумму (больше нуля)');
      return;
    }
    var url = id ? '/admin/finance/api/edit' : '/admin/finance/api/add';
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res.success) {
          hideModal('finModal');
          toast(id ? 'Изменено' : 'Добавлено');
          loadData();
        } else {
          showError('#finTxnError', res.error || 'Ошибка сохранения');
        }
      })
      .catch(function () { showError('#finTxnError', 'Ошибка сети'); });
  }

  function confirmDelete(id) {
    pendingDelete = id;
    qs('#finConfirmText').textContent = 'Удалить операцию #' + id + '?';
    showModal('finConfirmModal');
  }

  function doDelete() {
    if (pendingDelete == null) return;
    var id = pendingDelete;
    pendingDelete = null;
    hideModal('finConfirmModal');
    fetch('/admin/finance/api/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ csrf_token: CSRF, id: id })
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        toast(res.success ? 'Удалено' : (res.error || 'Ошибка удаления'));
        if (res.success) loadData();
      });
  }


  /* ─────── Импорт / экспорт ─────── */
  function exportCsv() {
    var p = new URLSearchParams();
    if (state.range !== 'all') p.set('since', rangeSince(state.range));
    else if (state.month) p.set('month', state.month);
    if (state.type) p.set('type', state.type);
    if (state.q) p.set('q', state.q);
    window.location.href = '/admin/finance/api/export/csv?' + p.toString();
  }

  function doImport() {
    var file = qs('#finImportFile').files[0];
    if (!file) { showError('#finImportError', 'Выберите файл CSV'); return; }
    qs('#finImportError').hidden = true;
    qs('#finImportResult').hidden = true;
    var fd = new FormData();
    fd.append('csrf_token', CSRF);
    fd.append('file', file);
    qs('#finImportBtn').disabled = true;
    fetch('/admin/finance/api/import', { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        qs('#finImportBtn').disabled = false;
        if (res.success) {
          qs('#finImportResult').textContent = 'Импортировано: ' + res.imported + ', пропущено: ' + res.skipped +
            (res.errors && res.errors.length ? ' Ошибки: ' + res.errors.join('; ') : '');
          qs('#finImportResult').hidden = false;
          loadData();
        } else {
          showError('#finImportError', res.error || 'Ошибка импорта');
        }
      })
      .catch(function () {
        qs('#finImportBtn').disabled = false;
        showError('#finImportError', 'Ошибка сети');
      });
  }


  /* ─────── Настройки ─────── */
  function jsonOrArray(v) {
    if (Array.isArray(v)) return v;
    try { var p = JSON.parse(v || '[]'); return Array.isArray(p) ? p : []; } catch (e) { return []; }
  }

  function openSettings() {
    qs('#finSetCurrency').value = settings.currency || '₽';
    qs('#finSetDecimals').value = String(settings.decimals || 2);
    qs('#finSetAutoRefresh').value = String(settings.auto_refresh || 0);
    qs('#finSetAvgPeriod').value = settings.avg_period || 'day';
    qs('#finSetExcludeCats').value = jsonOrArray(settings.avg_exclude_categories).join(', ');
    qs('#finSetQuickCats').value = jsonOrArray(settings.quick_categories).join(', ');
    qs('#finSetQuickParts').value = jsonOrArray(settings.quick_participants).join(', ');
    qs('#finSetPlategaMerchant').value = settings.platega_merchant_id || '';
    qs('#finSetPlategaSecret').value = settings.platega_secret_raw || '';
    qs('#finSetPlategaDays').value = settings.platega_days_back || '150';
    qs('#finSetPlategaAuto').value = settings.platega_auto_sync || '0';
    qs('#finSettingsError').hidden = true;
    showModal('finSettingsModal');
  }

  function saveSettings() {
    var toArr = function (v) {
      return String(v || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    };
    var payload = {
      csrf_token: CSRF,
      currency: qs('#finSetCurrency').value,
      decimals: Number(qs('#finSetDecimals').value),
      auto_refresh: Number(qs('#finSetAutoRefresh').value),
      avg_period: qs('#finSetAvgPeriod').value,
      avg_exclude_categories: toArr(qs('#finSetExcludeCats').value),
      quick_categories: toArr(qs('#finSetQuickCats').value),
      quick_participants: toArr(qs('#finSetQuickParts').value),
      platega_merchant_id: qs('#finSetPlategaMerchant').value,
      platega_secret: qs('#finSetPlategaSecret').value,
      platega_days_back: Number(qs('#finSetPlategaDays').value),
      platega_auto_sync: Number(qs('#finSetPlategaAuto').value),
    };
    fetch('/admin/finance/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (res) {
        if (res.success) {
          settings = Object.assign({}, settings, payload);
          hideModal('finSettingsModal');
          toast('Настройки сохранены');
          loadData();
          startPlategaAutoSync();
        } else {
          showError('#finSettingsError', res.error || 'Ошибка сохранения');
        }
      });
  }


  /* ─────── Platega ─────── */
  var _plategaData = [];
  var _plategaAutoTimer = null;
  var _plategaFirstTimer = null;

  function openPlatega() {
    qs('#finPlategaError').hidden = true;
    qs('#finPlategaBody').innerHTML = '<tr><td colspan="6" class="fin-empty-cell">Нажмите «Превью» для загрузки платежей</td></tr>';
    qs('#finPlategaSelectAll').checked = true;
    _plategaData = [];
    var lastSync = settings.platega_last_sync || '';
    qs('#finPlategaSummary').textContent = lastSync
      ? 'Последняя синхронизация: ' + new Date(lastSync).toLocaleString('ru-RU')
      : '';
    loadPlategaSettings();
    showModal('finPlategaModal');
  }

  function loadPlategaSettings() {
    fetch('/admin/finance/api/platega/settings', {
      headers: { 'Accept': 'application/json', 'X-CSRF-Token': CSRF }
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        if (data.merchant_id) qs('#finPlategaMerchant').value = data.merchant_id;
        if (data.secret_raw) qs('#finPlategaSecret').value = data.secret_raw;
        qs('#finPlategaDays').value = data.days_back || 150;
      })
      .catch(function (e) {
        console.error('[Platega] load settings error:', e);
      });
  }

  function savePlategaSettings() {
    var payload = {
      csrf_token: CSRF,
      merchant_id: qs('#finPlategaMerchant').value,
      secret: qs('#finPlategaSecret').value,
      days_back: qs('#finPlategaDays').value,
    };
    fetch('/admin/finance/api/platega/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).catch(function () {});
  }

  function runPlategaPreview() {
    var merchantId = qs('#finPlategaMerchant').value.trim();
    var secret = qs('#finPlategaSecret').value.trim();
    var daysBack = parseInt(qs('#finPlategaDays').value, 10) || 150;

    qs('#finPlategaError').hidden = true;
    qs('#finPlategaBody').innerHTML = '<tr><td colspan="6" class="fin-empty-cell">Загрузка... <span class="bf-spinner"></span></td></tr>';
    qs('#finPlategaSummary').textContent = '';

    var payload = { csrf_token: CSRF, merchant_id: merchantId, secret: secret, days_back: daysBack };
    fetch('/admin/finance/api/platega/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-CSRF-Token': CSRF },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, status: r.status, data: data }; }); })
      .then(function (res) {
        if (!res.ok || !res.data || !res.data.success) {
          var msg = (res.data && res.data.error) ? res.data.error : 'HTTP ' + res.status;
          qs('#finPlategaBody').innerHTML = '<tr><td colspan="6" class="fin-empty-cell" style="color:var(--red)">Ошибка: ' + esc(msg) + '</td></tr>';
          qs('#finPlategaError').textContent = msg;
          qs('#finPlategaError').hidden = false;
          return;
        }
        _plategaData = res.data.transactions || [];
        renderPlategaTable(_plategaData);
        savePlategaSettings();
      })
      .catch(function (e) {
        console.error('[Platega] preview error:', e);
        qs('#finPlategaBody').innerHTML = '<tr><td colspan="6" class="fin-empty-cell" style="color:var(--red)">Ошибка сети: ' + esc(e.message || e) + '</td></tr>';
        qs('#finPlategaError').textContent = e.message || 'Ошибка сети';
        qs('#finPlategaError').hidden = false;
      });
  }

  function renderPlategaTable(transactions) {
    var tbody = qs('#finPlategaBody');
    var statusLabel = { new: '', duplicate: 'уже добавлен', skipped: 'отменён / пропущен', excluded: 'исключён' };

    tbody.innerHTML = transactions.map(function (t, i) {
      var selectable = t.status === 'new';
      var checked = selectable ? 'checked' : '';
      var disabled = !selectable ? 'disabled' : '';
      var label = statusLabel[t.status] || '';
      var gross = Number(t.gross) || 0;
      var net = Number(t.amount) || 0;
      return '<tr' + (selectable ? '' : ' style="opacity:0.5"') + '>' +
        '<td style="text-align:center"><input type="checkbox" class="platega-row-cb" data-idx="' + i + '" ' + checked + ' ' + disabled + '></td>' +
        '<td>' + esc(t.date) + '</td>' +
        '<td>' + gross.toFixed(2) + ' ₽</td>' +
        '<td style="color:var(--red)">-' + (gross * 0.1).toFixed(2) + ' ₽</td>' +
        '<td style="font-weight:600">' + net.toFixed(2) + ' ₽</td>' +
        '<td>' + esc(t.description) + (label ? ' <span style="color:var(--text-muted)">(' + label + ')</span>' : '') + '</td>' +
        '</tr>';
    }).join('');

    var selectAll = qs('#finPlategaSelectAll');
    selectAll.onchange = function () {
      qsa('.platega-row-cb:not(:disabled)').forEach(function (cb) { cb.checked = selectAll.checked; });
      updatePlategaSummary();
    };

    qsa('.platega-row-cb').forEach(function (cb) {
      cb.onchange = updatePlategaSummary;
    });

    updatePlategaSummary();
  }

  function updatePlategaSummary() {
    var total = _plategaData.length;
    var newCount = _plategaData.filter(function (t) { return t.status === 'new'; }).length;
    var checked = qsa('.platega-row-cb:checked').length;
    qs('#finPlategaSummary').textContent = 'Всего: ' + total + ' · можно импортировать: ' + newCount + ' · выбрано: ' + checked;
  }

  function importPlategaSelected() {
    var tbody = qs('#finPlategaBody');
    var checks = qsa('.platega-row-cb:checked');
    if (!checks.length) {
      qs('#finPlategaError').textContent = 'Ничего не выбрано';
      qs('#finPlategaError').hidden = false;
      return;
    }

    var payload = {
      csrf_token: CSRF,
      transactions: _plategaData.map(function (t, i) {
        return { record_id: t.record_id, include: t.status === 'new' && t.amount > 0 };
      }),
    };

    fetch('/admin/finance/api/platega/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-CSRF-Token': CSRF },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (res) {
        if (res.success) {
          toast('Импортировано: ' + res.added + ', пропущено: ' + res.skipped);
          hideModal('finPlategaModal');
          loadData();
        } else {
          qs('#finPlategaError').textContent = res.error || 'Ошибка импорта';
          qs('#finPlategaError').hidden = false;
        }
      })
      .catch(function (e) {
        console.error('[Platega] import error:', e);
        qs('#finPlategaError').textContent = 'Ошибка сети: ' + (e.message || '');
        qs('#finPlategaError').hidden = false;
      });
  }

  function syncPlategaAuto() {
    // Автоимпорт на сервере: /api/platega/sync сам берёт сохранённые
    // merchant_id/secret, делает preview и импортирует новые платежи.
    fetch('/admin/finance/api/platega/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-CSRF-Token': CSRF },
      body: JSON.stringify({ csrf_token: CSRF })
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (res) {
        if (!res.success) {
          if (res.error) console.warn('[Platega] auto sync:', res.error);
          return;
        }
        if (res.added > 0) {
          toast('Platega авто: +' + res.added);
          loadData();
        }
      })
      .catch(function (e) {
        console.error('[Platega] auto sync error:', e);
      });
  }

  function startPlategaAutoSync() {
    if (_plategaAutoTimer) { clearInterval(_plategaAutoTimer); _plategaAutoTimer = null; }
    if (_plategaFirstTimer) { clearTimeout(_plategaFirstTimer); _plategaFirstTimer = null; }
    var autoSync = parseInt((settings.platega_auto_sync || '0'), 10);
    if (autoSync > 0) {
      _plategaAutoTimer = setInterval(syncPlategaAuto, 5 * 60 * 1000);
      // Первый синк сразу после загрузки страницы (не ждём 5 минут)
      _plategaFirstTimer = setTimeout(syncPlategaAuto, 2000);
    }
  }


  /* ─────── События ─────── */
  function bindEvents() {
    qs('#fin-btn-add').addEventListener('click', function () { openAdd(); });
    qs('#fin-btn-refresh').addEventListener('click', loadData);
    qs('#fin-btn-export').addEventListener('click', exportCsv);
    qs('#fin-btn-import').addEventListener('click', function () {
      qs('#finImportFile').value = ''; qs('#finImportError').hidden = true; qs('#finImportResult').hidden = true;
      showModal('finImportModal');
    });
    qs('#fin-btn-settings').addEventListener('click', openSettings);
    qs('#fin-btn-platega').addEventListener('click', openPlatega);
    qs('#finPlategaPreviewBtn').addEventListener('click', runPlategaPreview);
    qs('#finPlategaImportBtn').addEventListener('click', importPlategaSelected);

    // Контролы графика
    qs('#fin-scale').addEventListener('change', function () { state.scale = this.value; renderChart(); });
    qsa('#fin-chart-type button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.chartType = this.getAttribute('data-type');
        qsa('#fin-chart-type button').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active'); renderChart();
      });
    });
    qsa('#fin-range button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.range = this.getAttribute('data-range'); state.month = ''; qs('#fin-filter-month').value = '';
        qsa('#fin-range button').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active'); state.page = 1; loadData();
      });
    });
    qs('#fin-anomalies').addEventListener('change', function () { state.anomalies = this.checked; if (lastData) renderTable(); });

    // Фильтры
    qs('#fin-filter-month').addEventListener('change', function () {
      state.month = this.value; state.range = 'all';
      qsa('#fin-range button').forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-range') === 'all'); });
      state.page = 1; loadData();
    });
    qs('#fin-filter-type').addEventListener('change', function () { state.type = this.value; state.page = 1; loadData(); });
    qs('#fin-filter-q').addEventListener('input', function () {
      var v = this.value; clearTimeout(qDebounce);
      qDebounce = setTimeout(function () { state.q = v.trim(); state.page = 1; loadData(); }, 350);
    });
    qs('#fin-per-page').addEventListener('change', function () { state.per_page = Number(this.value); state.page = 1; loadData(); });
    // Таблица: сортировка, действия, пагинация
    var table = qs('.finance-table');
    if (table) {
      table.querySelectorAll('th.sortable').forEach(function (th) {
        th.addEventListener('click', function () {
          var key = this.getAttribute('data-sort');
          if (state.sort === key) state.dir = state.dir === 'desc' ? 'asc' : 'desc';
          else { state.sort = key; state.dir = 'desc'; }
          state.page = 1;
          table.querySelectorAll('th.sortable').forEach(function (h) { h.classList.remove('sorted', 'asc', 'desc'); });
          this.classList.add('sorted', state.dir);
          loadData();
        });
      });
    }
    qs('#fin-tbody').addEventListener('click', function (e) {
      var edit = e.target.closest('.fin-edit');
      if (edit) { openAdd(Number(edit.getAttribute('data-id'))); return; }
      var del = e.target.closest('.fin-del');
      if (del) { confirmDelete(Number(del.getAttribute('data-id'))); }
    });
    qs('#fin-pagination').addEventListener('click', function (e) {
      var a = e.target.closest('.page-link');
      if (!a) return;
      e.preventDefault();
      state.page = Number(a.getAttribute('data-page'));
      loadData();
    });

    // Модалки
    qsa('[data-close]').forEach(function (btn) {
      btn.addEventListener('click', function () { hideModal(this.getAttribute('data-close')); });
    });
    qsa('.finance-modal-overlay').forEach(function (ov) {
      ov.addEventListener('mousedown', function (e) { if (e.target === ov) ov.hidden = true; });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') qsa('.finance-modal-overlay').forEach(function (ov) { ov.hidden = true; });
    });

    qs('#finTxnSave').addEventListener('click', saveTxn);
    qs('#finConfirmOk').addEventListener('click', doDelete);
    qs('#finImportBtn').addEventListener('click', doImport);
    qs('#finSettingsSave').addEventListener('click', saveSettings);

    // Перекраска графика при смене темы/режима панели
    new MutationObserver(function (muts) {
      muts.forEach(function (m) {
        if ((m.attributeName === 'data-mode' || m.attributeName === 'data-theme') && lastData) renderChart();
      });
    }).observe(document.documentElement, { attributes: true });
  }


  /* ─────── Init ─────── */
  function init() {
    bindEvents();
    loadData();
    initPlatega();
  }

  window.Finance = { init: init };
})();
