<?php
/**
 * Финансовый модуль — главная страница
 * Конфиг для JS: window.FIN (csrf + настройки)
 */
$finSettings = $finSettings ?? [];
$finCurrency = $finSettings['currency'] ?? '₽';
$finDecimals = (int)($finSettings['decimals'] ?? 2);
?>
<meta name="csrf-token" content="<?= csrf_token() ?>">
<script>
window.FIN = {
    csrf: <?= json_encode(csrf_token()) ?>,
    settings: <?= json_encode($finSettings, JSON_UNESCAPED_UNICODE) ?>
};
</script>

<!-- Инструменты -->
<div class="finance-actions">
    <button type="button" class="btn btn-primary btn-sm" id="fin-btn-add"><?= icon('plus') ?> Добавить</button>
    <button type="button" class="btn btn-secondary btn-sm" id="fin-btn-import"><?= icon('upload') ?> Импорт</button>
    <button type="button" class="btn btn-secondary btn-sm" id="fin-btn-export"><?= icon('download') ?> Экспорт</button>
    <button type="button" class="btn btn-secondary btn-sm" id="fin-btn-platega"><?= icon('credit-card') ?> Platega</button>
    <span class="finance-spacer"></span>
    <button type="button" class="btn btn-secondary btn-sm" id="fin-btn-settings"><?= icon('settings') ?> Настройки</button>
    <button type="button" class="btn btn-icon btn-sm" id="fin-btn-refresh" title="Обновить"><?= icon('refresh-cw') ?></button>
</div>

<!-- Сводка -->
<div class="finance-summary">
    <div class="glass-card finance-kpi">
        <div class="finance-kpi-top">
            <span class="finance-kpi-label">Доходы</span>
            <?= icon('trending-up', 'finance-kpi-ic finance-kpi-ic-income') ?>
        </div>
        <div class="finance-kpi-value is-income" id="fin-income">—</div>
        <div class="finance-kpi-hint" id="fin-income-avg"></div>
    </div>
    <div class="glass-card finance-kpi">
        <div class="finance-kpi-top">
            <span class="finance-kpi-label">Расходы</span>
            <?= icon('trending-down', 'finance-kpi-ic finance-kpi-ic-expense') ?>
        </div>
        <div class="finance-kpi-value is-expense" id="fin-expense">—</div>
        <div class="finance-kpi-hint" id="fin-expense-avg"></div>
    </div>
    <div class="glass-card finance-kpi">
        <div class="finance-kpi-top">
            <span class="finance-kpi-label">Баланс</span>
            <?= icon('wallet', 'finance-kpi-ic finance-kpi-ic-accent') ?>
        </div>
        <div class="finance-kpi-value" id="fin-balance">—</div>
        <div class="finance-kpi-hint" id="fin-balance-hint"></div>
    </div>
    <div class="glass-card finance-kpi">
        <div class="finance-kpi-top">
            <span class="finance-kpi-label">Операций</span>
            <?= icon('credit-card', 'finance-kpi-ic finance-kpi-ic-neutral') ?>
        </div>
        <div class="finance-kpi-value" id="fin-count">—</div>
        <div class="finance-kpi-hint" id="fin-count-hint"></div>
    </div>
</div>

<!-- График -->
<div class="glass-card finance-chart-card">
    <div class="finance-chart-header">
        <h2 class="finance-chart-title">Доходы / Расходы</h2>
        <div class="finance-chart-controls">
            <label>Шкала</label>
            <select id="fin-scale">
                <option value="day">Дни</option>
                <option value="week">Недели</option>
                <option value="month" selected>Месяцы</option>
                <option value="year">Годы</option>
            </select>
            <div class="finance-chart-type" id="fin-chart-type">
                <button type="button" data-type="bar" class="active" title="Столбцы"><?= icon('bar-chart-2') ?></button>
                <button type="button" data-type="line" title="Линия"><?= icon('line-chart') ?></button>
                <button type="button" data-type="area" title="Область"><?= icon('trending-up') ?></button>
            </div>
            <div class="finance-range" id="fin-range">
                <button type="button" data-range="7d">7Д</button>
                <button type="button" data-range="1m">1М</button>
                <button type="button" data-range="3m">3М</button>
                <button type="button" data-range="1y">1Г</button>
                <button type="button" data-range="all" class="active">Всё</button>
            </div>
            <label class="finance-toggle"><input type="checkbox" id="fin-anomalies"><span>Аномалии</span></label>
        </div>
    </div>
    <div class="finance-chart-wrap">
        <canvas id="finChart"></canvas>
    </div>
</div>

<!-- Фильтры -->
<div class="finance-filters">
    <label>Месяц</label>
    <input type="month" id="fin-filter-month" value="">
    <label>Тип</label>
    <select id="fin-filter-type">
        <option value="">Все</option>
        <option value="income">Доход</option>
        <option value="expense">Расход</option>
    </select>
    <label>Поиск</label>
    <input type="text" id="fin-filter-q" placeholder="Участник, категория…" autocomplete="off">
    <label>Строк</label>
    <select id="fin-per-page">
        <option value="10">10</option>
        <option value="25" selected>25</option>
        <option value="50">50</option>
        <option value="100">100</option>
    </select>
</div>

<!-- Таблица -->
<div class="dg-wrapper">
    <div class="finance-table-scroll">
        <table class="dg-table finance-table">
            <thead>
            <tr>
                <th data-sort="date" class="sortable sorted desc">Дата <span class="sort-indicator">↕</span></th>
                <th>Тип</th>
                <th data-sort="category" class="sortable">Категория <span class="sort-indicator">↕</span></th>
                <th data-sort="participant" class="sortable">Участник <span class="sort-indicator">↕</span></th>
                <th data-sort="amount" class="sortable fin-amt-col">Сумма <span class="sort-indicator">↕</span></th>
                <th>Описание</th>
                <th class="fin-actions-col"></th>
            </tr>
            </thead>
            <tbody id="fin-tbody">
            <tr><td colspan="7" class="fin-empty-cell">Загрузка…</td></tr>
            </tbody>
        </table>
    </div>
    <div class="dg-pagination">
        <span class="finance-total" id="fin-total"></span>
        <div class="pagination-links" id="fin-pagination"></div>
    </div>
</div>

<!-- Модалка: добавить/редактировать -->
<div class="finance-modal-overlay" id="finModal" hidden>
    <div class="finance-modal">
        <div class="finance-modal-header">
            <h3 id="finModalTitle">Добавить операцию</h3>
            <button type="button" class="finance-modal-close" data-close="finModal"><?= icon('x') ?></button>
        </div>
        <input type="hidden" id="finTxnId">
        <div class="finance-modal-body">
            <div class="form-row">
                <div class="form-group">
                    <label>Дата</label>
                    <input type="date" id="finTxnDate" required>
                </div>
                <div class="form-group">
                    <label>Тип</label>
                    <select id="finTxnType">
                        <option value="income">Доход</option>
                        <option value="expense">Расход</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>Категория</label>
                <input type="text" id="finTxnCategory" list="finCatList" placeholder="Прибыль, Сервер, Домен…" autocomplete="off">
                <datalist id="finCatList"></datalist>
            </div>
            <div class="form-group">
                <label>Участник / Получатель</label>
                <input type="text" id="finTxnParticipant" list="finPartList" placeholder="Platega, Beget, Иванов И…" autocomplete="off">
                <datalist id="finPartList"></datalist>
            </div>
            <div class="form-group">
                <label>Сумма (<?= $finCurrency ?>)</label>
                <input type="number" id="finTxnAmount" step="0.01" min="0" placeholder="0.00" required>
            </div>
            <div class="form-group">
                <label>Описание</label>
                <textarea id="finTxnDescription" rows="2" placeholder="Необязательно"></textarea>
            </div>
            <div class="finance-error" id="finTxnError" hidden></div>
        </div>
        <div class="finance-modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" data-close="finModal">Отмена</button>
            <button type="button" class="btn btn-primary btn-sm" id="finTxnSave">Сохранить</button>
        </div>
    </div>
</div>

<!-- Модалка: импорт -->
<div class="finance-modal-overlay" id="finImportModal" hidden>
    <div class="finance-modal">
        <div class="finance-modal-header">
            <h3>Импорт из CSV</h3>
            <button type="button" class="finance-modal-close" data-close="finImportModal"><?= icon('x') ?></button>
        </div>
        <div class="finance-modal-body">
            <p class="finance-help">Формат: <code>date;type;category;participant;amount;description</code><br>
            Тип: <code>Доход</code> или <code>Расход</code>. Разделитель «;» или «,» (определяется автоматически).<br>
            Для XLSX — сохраните файл в Excel как CSV (UTF-8).</p>
            <input type="file" id="finImportFile" accept=".csv,.txt" class="finance-file-input">
            <div class="finance-error" id="finImportError" hidden></div>
            <div class="finance-success" id="finImportResult" hidden></div>
        </div>
        <div class="finance-modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" data-close="finImportModal">Закрыть</button>
            <button type="button" class="btn btn-primary btn-sm" id="finImportBtn">Импортировать</button>
        </div>
    </div>
</div>

<!-- Модалка: настройки -->
<div class="finance-modal-overlay" id="finSettingsModal" hidden>
    <div class="finance-modal">
        <div class="finance-modal-header">
            <h3>Настройки</h3>
            <button type="button" class="finance-modal-close" data-close="finSettingsModal"><?= icon('x') ?></button>
        </div>
        <div class="finance-modal-body">
            <div class="form-row">
                <div class="form-group">
                    <label>Валюта</label>
                    <select id="finSetCurrency">
                        <option value="₽">₽</option>
                        <option value="$">$</option>
                        <option value="€">€</option>
                        <option value="руб">руб</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Знаков после запятой</label>
                    <select id="finSetDecimals">
                        <option value="0">0</option>
                        <option value="1">1</option>
                        <option value="2">2</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Автообновление</label>
                    <select id="finSetAutoRefresh">
                        <option value="0">Нет</option>
                        <option value="10">10 сек</option>
                        <option value="30">30 сек</option>
                        <option value="60">60 сек</option>
                        <option value="120">2 мин</option>
                        <option value="300">5 мин</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Период средних</label>
                    <select id="finSetAvgPeriod">
                        <option value="day">День</option>
                        <option value="week">Неделя</option>
                        <option value="month">Месяц</option>
                        <option value="year">Год</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>Исключить категории из средних (через запятую)</label>
                <input type="text" id="finSetExcludeCats" placeholder="Инвестиции, Взнос…">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Быстрые категории</label>
                    <input type="text" id="finSetQuickCats" placeholder="Прибыль, Сервер, Домен…">
                </div>
                <div class="form-group">
                    <label>Быстрые участники</label>
                    <input type="text" id="finSetQuickParts" placeholder="Platega, Beget…">
                </div>
            </div>
            <div class="finance-error" id="finSettingsError" hidden></div>
            <hr class="finance-hr">
            <h4 class="finance-subtitle">Platega</h4>
            <div class="form-row">
                <div class="form-group">
                    <label>Merchant ID</label>
                    <input type="text" id="finSetPlategaMerchant" placeholder="c66751a9-...">
                </div>
                <div class="form-group">
                    <label>Secret Key</label>
                    <input type="password" id="finSetPlategaSecret" placeholder="••••••••">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Дней назад</label>
                    <input type="number" id="finSetPlategaDays" value="150" min="1" max="730">
                </div>
                <div class="form-group">
                    <label>Автоимпорт</label>
                    <select id="finSetPlategaAuto">
                        <option value="0">Нет</option>
                        <option value="1">Да</option>
                    </select>
                </div>
            </div>
        </div>
        <div class="finance-modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" data-close="finSettingsModal">Закрыть</button>
            <button type="button" class="btn btn-primary btn-sm" id="finSettingsSave">Сохранить</button>
        </div>
    </div>
</div>

<!-- Модалка: подтверждение -->
<div class="finance-modal-overlay" id="finConfirmModal" hidden>
    <div class="finance-modal finance-modal-sm">
        <div class="finance-modal-header">
            <h3 id="finConfirmTitle">Подтверждение</h3>
        </div>
        <div class="finance-modal-body">
            <p id="finConfirmText" class="finance-help"></p>
        </div>
        <div class="finance-modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" data-close="finConfirmModal">Отмена</button>
            <button type="button" class="btn btn-danger btn-sm" id="finConfirmOk">Удалить</button>
        </div>
    </div>
</div>

<!-- Модалка: Platega preview -->
<div class="finance-modal-overlay" id="finPlategaModal" hidden>
    <div class="finance-modal" style="max-width:860px">
        <div class="finance-modal-header">
            <h3>Импорт из Platega</h3>
            <button type="button" class="finance-modal-close" data-close="finPlategaModal"><?= icon('x') ?></button>
        </div>
        <div class="finance-modal-body">
            <p class="finance-help">Настройки подключения и превью платежей. Уже добавленные и отменённые отмечены серым.</p>
            <div class="form-row">
                <div class="form-group">
                    <label>Merchant ID</label>
                    <input type="text" id="finPlategaMerchant" placeholder="c66751a9-...">
                </div>
                <div class="form-group">
                    <label>Secret Key</label>
                    <input type="password" id="finPlategaSecret" placeholder="••••••••">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Дней назад</label>
                    <input type="number" id="finPlategaDays" value="150" min="1" max="730">
                </div>
                <div class="form-group" style="display:flex;align-items:flex-end">
                    <button type="button" class="btn btn-primary btn-sm" id="finPlategaPreviewBtn">Превью</button>
                </div>
            </div>
            <div class="finance-error" id="finPlategaError" hidden></div>
            <div style="max-height:50vh;overflow-y:auto;margin-top:12px">
                <table class="dg-table finance-table" id="finPlategaTable">
                    <thead>
                    <tr>
                        <th style="width:40px"><input type="checkbox" id="finPlategaSelectAll" checked></th>
                        <th>Дата</th>
                        <th>Сумма gross</th>
                        <th>Комиссия 10%</th>
                        <th>К зачислению</th>
                        <th>Описание</th>
                    </tr>
                    </thead>
                    <tbody id="finPlategaBody">
                    <tr><td colspan="6" class="fin-empty-cell">Нажмите «Превью» для загрузки платежей</td></tr>
                    </tbody>
                </table>
            </div>
            <div class="finance-help" id="finPlategaSummary" style="margin-top:8px"></div>
            <?php if (!empty($cronToken)): ?>
            <div class="finance-help" style="margin-top:10px;font-size:12px;line-height:1.5">
                <strong>Автоимпорт без открытой страницы (cron):</strong><br>
                <code style="word-break:break-all">*/5 * * * * curl -s "<?= rtrim(SITE_URL, '/') ?>/admin/finance/api/platega/cron-sync?token=<?= $cronToken ?>" &gt; /dev/null</code>
            </div>
            <?php endif; ?>
        </div>
        <div class="finance-modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" data-close="finPlategaModal">Закрыть</button>
            <button type="button" class="btn btn-primary btn-sm" id="finPlategaImportBtn">Импортировать выбранные</button>
        </div>
    </div>
</div>

<!-- Уведомление -->
<div class="finance-toast" id="finToast" hidden></div>

<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/finance.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/finance.css') ?>">
<script src="<?= SITE_URL ?>/public/finance/vendor/chart.umd.min.js"></script>
<script src="<?= SITE_URL ?>/admin/js/finance/chart.js?v=<?= filemtime(ADMIN_PATH . '/js/finance/chart.js') ?>"></script>
<script src="<?= SITE_URL ?>/admin/js/finance/finance.js?v=<?= filemtime(ADMIN_PATH . '/js/finance/finance.js') ?>"></script>
<script>Finance.init();</script>
