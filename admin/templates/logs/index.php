<?php
/**
 * Страница «Логи» — двухуровневая система табов:
 *   Ряд 1: Категории
 *   Ряд 2: Уровни
 *
 * Переменные:
 *   $categories    — все категории (label => name)
 *   $levels        — все уровни (label => name)
 *   $categoryIcons — иконки для категорий
 *   $activeCategory — активная категория
 *   $activeLevel   — активный уровень
 *   $logs          — записи
 *   $total         — всего
 *   $q             — поисковый запрос
 *   $page          — текущая страница
 *   $pages         — всего страниц
 *   $per_page      — записей на страницу
 *   $isExternal    — внешний источник (Docker/Loki)
 */
$categories    = $categories ?? [];
$levels        = $levels ?? [];
$categoryIcons = $categoryIcons ?? [];
$logs          = $logs ?? [];
$total         = $total ?? 0;
$page          = $page ?? 1;
$pages         = $pages ?? 1;
$per_page      = $per_page ?? 50;
$activeCategory = $activeCategory ?? 'all';
$activeLevel   = $activeLevel ?? '';
$q             = $q ?? '';
$isExternal    = $isExternal ?? false;

$levelBadge = [
    'info'    => 'badge-info',
    'warning' => 'badge-warning',
    'error'   => 'badge-error',
    'debug'   => 'badge-neutral',
];

$channelLabels = [
    'system'  => 'Система',
    'platega' => 'Platega',
    'yookassa' => 'ЮKassa',
    'auth'    => 'Авторизация',
    'finance' => 'Финансы',
    'user'    => 'Пользователи',
];

$channelIcons = [
    'system'  => 'settings',
    'platega' => 'credit-card',
    'yookassa' => 'wallet',
    'auth'    => 'shield',
    'finance' => 'bar-chart-2',
    'user'    => 'users',
];
?>
<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/logs.css?v=<?= @filemtime(PUBLIC_PATH . '/css/panel/logs.css') ?>">

<div class="logs-header">
    <!-- ====== Ряд 1: Табы по категориям ====== -->
    <div class="logs-tabs logs-cat-tabs" role="tablist">
        <?php foreach ($categories as $catKey => $catLabel): ?>
            <?php
            $url = '/admin/logs';
            $params = [];
            if ($catKey !== 'all') {
                $params['category'] = $catKey;
            }
            if ($activeLevel !== '') {
                $params['level'] = $activeLevel;
            }
            if ($params) {
                $url .= '?' . http_build_query($params);
            }
            $icon = $categoryIcons[$catKey] ?? 'terminal';
            ?>
            <a href="<?= $url ?>" class="logs-tab <?= $activeCategory === $catKey ? 'active' : '' ?>" role="tab">
                <?= icon($icon) ?> <?= TemplateEngine::e($catLabel) ?>
            </a>
        <?php endforeach; ?>
    </div>

    <!-- ====== Ряд 2: Табы по уровням ====== -->
    <div class="logs-tabs logs-level-tabs" role="tablist">
        <?php foreach ($levels as $lvlKey => $lvlLabel): ?>
            <?php
            $url = '/admin/logs';
            $params = [];
            if ($activeCategory !== 'all') {
                $params['category'] = $activeCategory;
            }
            if ($lvlKey !== '') {
                $params['level'] = $lvlKey;
            }
            if ($params) {
                $url .= '?' . http_build_query($params);
            }
            $isActive = ($lvlKey === '' && $activeLevel === '') || ($lvlKey === $activeLevel);
            ?>
            <a href="<?= $url ?>"
               class="logs-tab logs-level-tab <?= $isActive ? 'active' : '' ?> <?= $lvlKey !== '' ? 'level-' . $lvlKey : '' ?>"
               role="tab">
                <?= icon($lvlKey === 'error' ? 'alert-circle' : ($lvlKey === 'warning' ? 'alert-triangle' : 'info')) ?>
                <?= TemplateEngine::e($lvlLabel) ?>
            </a>
        <?php endforeach; ?>
    </div>

    <!-- ====== Фильтры и очистка ====== -->
    <div class="logs-actions">
        <form class="logs-filters" method="get" action="/admin/logs">
            <?php if ($activeCategory !== 'all'): ?>
                <input type="hidden" name="category" value="<?= TemplateEngine::e($activeCategory) ?>">
            <?php endif; ?>
            <?php if ($activeLevel !== ''): ?>
                <input type="hidden" name="level" value="<?= TemplateEngine::e($activeLevel) ?>">
            <?php endif; ?>
            <div class="form-group" style="flex:1;min-width:200px">
                <label>Поиск по сообщению</label>
                <input type="text" name="q" value="<?= TemplateEngine::e($q) ?>"
                       placeholder="Текст сообщения…" autocomplete="off"
                       style="width:100%">
            </div>
            <div class="form-group" style="display:flex;align-items:flex-end;gap:6px">
                <button type="submit" class="btn btn-secondary btn-sm"><?= icon('search') ?> Фильтр</button>
                <a href="/admin/logs<?= $activeCategory !== 'all' ? '?category=' . urlencode($activeCategory) : '' ?><?= $activeLevel !== '' ? ($activeCategory !== 'all' ? '&' : '?') . 'level=' . urlencode($activeLevel) : '' ?>"
                   class="btn btn-ghost btn-sm" title="Сбросить поиск"><?= icon('x') ?> Сброс</a>
            </div>
        </form>

        <?php if (!$isExternal): ?>
        <div class="logs-clear-wrap">
            <button type="button" class="btn btn-danger btn-sm" id="logs-clear-btn"
                    data-category="<?= $activeCategory !== 'all' ? TemplateEngine::e($activeCategory) : '' ?>">
                <?= icon('delete') ?> Очистить<?= $activeCategory !== 'all' ? ' (' . TemplateEngine::e($categories[$activeCategory] ?? $activeCategory) . ')' : ' все' ?>
            </button>
        </div>
        <?php endif; ?>
    </div>
</div>

<div class="dg-wrapper">
    <?php if ($isExternal && empty($logs)): ?>
        <div class="ex-log-hint">
            <div style="text-align:center;padding:40px 20px;color:var(--text-muted)">
                <?= icon('bar-chart', 'icon-lg') ?>
                <p style="margin-top:12px;font-size:1.1rem">Внешний источник логов не настроен</p>
                <p style="font-size:0.9rem">Настройте параметры в <a href="/admin/settings?tab=logs">Настройках</a></p>
            </div>
        </div>
    <?php else: ?>
    <div class="logs-table-scroll">
        <table class="dg-table logs-table">
            <colgroup>
                <col style="width:150px">
                <col style="width:80px">
                <col style="width:105px">
                <col style="width:120px">
                <col>
                <col style="width:40px">
            </colgroup>
            <thead>
                <tr>
                    <th>Дата</th>
                    <th>Уровень</th>
                    <th>Категория</th>
                    <th>Канал</th>
                    <th>Сообщение</th>
                    <th title="Контекст">Ctx</th>
                </tr>
            </thead>
            <tbody id="logs-tbody">
            <?php if (empty($logs)): ?>
                <tr><td colspan="6" class="fin-empty-cell">
                    <div style="text-align:center;padding:40px 20px;color:var(--text-muted)">
                        <?= icon('terminal', 'icon-lg') ?>
                        <p style="margin-top:12px;font-size:1.1rem">Логов пока нет</p>
                        <p style="font-size:0.9rem">Логи появляются здесь по мере работы системы</p>
                    </div>
                </td></tr>
            <?php else: ?>
                <?php foreach ($logs as $row): ?>
                    <?php
                    $hasContext = !empty($row['context'])
                        && $row['context'] !== 'null'
                        && $row['context'] !== '[]';
                    $cat = $row['category'] ?? 'system';
                    $catLabel = $categories[$cat] ?? $cat;
                    $ch = $row['channel'] ?? '';
                    $chLabel = $channelLabels[$ch] ?? $ch;
                    ?>
                    <tr class="logs-row">
                        <td class="logs-date" title="<?= TemplateEngine::e($row['created_at']) ?>">
                            <?= TemplateEngine::e(date('d.m.Y H:i:s', strtotime($row['created_at']))) ?>
                        </td>
                        <td>
                            <span class="badge <?= $levelBadge[$row['level']] ?? 'badge-info' ?>">
                                <?= TemplateEngine::e($row['level']) ?>
                            </span>
                        </td>
                        <td>
                            <span class="logs-category-pill logs-cat-<?= TemplateEngine::e($cat) ?>">
                                <?= icon($categoryIcons[$cat] ?? 'terminal') ?>
                                <?= TemplateEngine::e($catLabel) ?>
                            </span>
                        </td>
                        <td>
                            <span class="logs-channel">
                                <?php if (isset($channelIcons[$ch])): ?>
                                    <?= icon($channelIcons[$ch]) ?>
                                <?php endif; ?>
                                <?= TemplateEngine::e($chLabel) ?>
                            </span>
                        </td>
                        <td class="logs-msg">
                            <code><?= TemplateEngine::e($row['message']) ?></code>
                            <?php if ($hasContext): ?>
                            <button type="button" class="btn btn-ghost btn-xs logs-ctx-toggle" title="Показать контекст">
                                <?= icon('info') ?>
                            </button>
                            <pre class="logs-context" style="display:none;margin-top:6px;font-size:0.8rem;background:var(--bg-surface);padding:8px;border-radius:6px;overflow-x:auto;max-width:600px"><?php
                                $ctx = json_decode($row['context'], true);
                                echo TemplateEngine::e(is_array($ctx) ? json_encode($ctx, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT) : $row['context']);
                            ?></pre>
                            <?php endif; ?>
                        </td>
                        <td style="text-align:center">
                            <?= $hasContext ? '<span class="badge badge-neutral" title="Есть контекст">+</span>' : '' ?>
                        </td>
                    </tr>
                <?php endforeach; ?>
            <?php endif; ?>
            </tbody>
        </table>
    </div>
    <?php endif; ?>

    <?php if (!$isExternal): ?>
    <?php
    $baseParams = [];
    if ($activeCategory !== 'all') {
        $baseParams['category'] = $activeCategory;
    }
    if ($activeLevel !== '') {
        $baseParams['level'] = $activeLevel;
    }
    if ($q !== '') {
        $baseParams['q'] = $q;
    }
    ?>
    <div class="dg-pagination">
        <span class="finance-total">Всего: <strong><?= (int)$total ?></strong></span>
        <div class="pagination-links" id="logs-pagination">
            <?php if ($pages > 1): ?>
                <?php if ($page > 1): ?>
                    <a href="?<?= http_build_query(array_merge($baseParams, ['page' => $page - 1, 'per_page' => $per_page])) ?>" class="page-link">‹</a>
                <?php endif; ?>
                <?php
                $start = max(1, $page - 2);
                $end = min($pages, $page + 2);
                for ($i = $start; $i <= $end; $i++):
                ?>
                    <a href="?<?= http_build_query(array_merge($baseParams, ['page' => $i, 'per_page' => $per_page])) ?>"
                       class="page-link<?= $i === $page ? ' active' : '' ?>"><?= $i ?></a>
                <?php endfor; ?>
                <?php if ($page < $pages): ?>
                    <a href="?<?= http_build_query(array_merge($baseParams, ['page' => $page + 1, 'per_page' => $per_page])) ?>" class="page-link">›</a>
                <?php endif; ?>
            <?php endif; ?>
        </div>
        <div class="per-page-selector" style="display:flex;align-items:center;gap:6px">
            <label style="font-size:0.857rem;color:var(--text-muted)">Показывать:</label>
            <select onchange="location.href=this.value" style="font-size:0.857rem;padding:4px 8px;border-radius:6px;background:var(--bg-surface);border:1px solid var(--border-color);color:var(--text-primary)">
                <?php foreach ([25, 50, 100, 200] as $pp): ?>
                    <?php
                    $ppParams = array_merge($baseParams, ['page' => 1, 'per_page' => $pp]);
                    ?>
                    <option value="?<?= http_build_query($ppParams) ?>" <?= $per_page == $pp ? 'selected' : '' ?>><?= $pp ?></option>
                <?php endforeach; ?>
            </select>
        </div>
    </div>
    <?php endif; ?>
</div>

<script>
(function () {
  var CSRF = '<?= csrf_token() ?>';

  // Очистка логов
  var clearBtn = document.getElementById('logs-clear-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      var category = clearBtn.getAttribute('data-category') || '';
      var msg = category
        ? 'Очистить все логи категории "' + category + '"? Это действие необратимо.'
        : 'Очистить все логи? Это действие необратимо.';
      if (!confirm(msg)) return;
      var body = { csrf_token: CSRF };
      if (category) body.category = category;
      fetch('/admin/logs/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(body)
      }).then(function (r) { return r.json(); }).then(function (res) {
        if (res.success) {
          location.reload();
        } else {
          alert(res.error || 'Ошибка очистки');
        }
      });
    });
  }

  // Toggle контекста
  document.querySelectorAll('.logs-ctx-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var pre = this.nextElementSibling;
      if (pre && pre.classList.contains('logs-context')) {
        pre.style.display = pre.style.display === 'none' ? 'block' : 'none';
      }
    });
  });
})();
</script>