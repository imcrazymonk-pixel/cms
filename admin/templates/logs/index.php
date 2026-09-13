<?php
/**
 * Страница «Логи» — список записей из app_logs.
 * Фильтры: уровень, канал, поиск по сообщению.
 */

$levels = $levels ?? [];
$channels = $channels ?? [];
$filters = $filters ?? [];
$logs = $logs ?? [];
$total = $total ?? 0;
$page = $page ?? 1;
$pages = $pages ?? 1;
$per_page = $per_page ?? 50;

$levelBadge = [
    'info' => 'badge-info',
    'warning' => 'badge-warning',
    'error' => 'badge-error',
];
?>
<link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/logs.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/logs.css') ?>">

<div class="logs-actions">
    <form class="logs-filters" method="get" action="/admin/logs">
        <div class="form-group">
            <label>Уровень</label>
            <select name="level">
                <option value="">Все</option>
                <?php foreach ($levels as $lvl): ?>
                    <option value="<?= TemplateEngine::e($lvl) ?>" <?= ($filters['level'] ?? '') === $lvl ? ' selected' : '' ?>><?= TemplateEngine::e($lvl) ?></option>
                <?php endforeach; ?>
            </select>
        </div>
        <div class="form-group">
            <label>Канал</label>
            <select name="channel">
                <option value="">Все</option>
                <?php foreach ($channels as $ch): ?>
                    <option value="<?= TemplateEngine::e($ch) ?>" <?= ($filters['channel'] ?? '') === $ch ? ' selected' : '' ?>><?= TemplateEngine::e($ch) ?></option>
                <?php endforeach; ?>
            </select>
        </div>
        <div class="form-group">
            <label>Поиск</label>
            <input type="text" name="q" value="<?= TemplateEngine::e($filters['q'] ?? '') ?>" placeholder="Текст сообщения…">
        </div>
        <div class="form-group" style="display:flex;align-items:flex-end">
            <button type="submit" class="btn btn-secondary btn-sm"><?= icon('search') ?> Фильтр</button>
        </div>
    </form>
    <div class="logs-clear-wrap">
        <button type="button" class="btn btn-danger btn-sm" id="logs-clear-btn"><?= icon('delete') ?> Очистить логи</button>
    </div>
</div>

<div class="dg-wrapper">
    <div class="logs-table-scroll">
        <table class="dg-table logs-table">
            <thead>
                <tr>
                    <th style="width:170px">Дата</th>
                    <th style="width:90px">Уровень</th>
                    <th style="width:110px">Канал</th>
                    <th>Сообщение</th>
                </tr>
            </thead>
            <tbody id="logs-tbody">
            <?php if (empty($logs)): ?>
                <tr><td colspan="4" class="fin-empty-cell">Логов пока нет.</td></tr>
            <?php else: ?>
                <?php foreach ($logs as $row): ?>
                    <tr>
                        <td class="logs-date"><?= TemplateEngine::e($row['created_at']) ?></td>
                        <td><span class="badge <?= $levelBadge[$row['level']] ?? 'badge-info' ?>"><?= TemplateEngine::e($row['level']) ?></span></td>
                        <td><?= TemplateEngine::e($row['channel']) ?></td>
                        <td class="logs-msg"><?= TemplateEngine::e($row['message']) ?></td>
                    </tr>
                <?php endforeach; ?>
            <?php endif; ?>
            </tbody>
        </table>
    </div>
    <div class="dg-pagination">
        <span class="finance-total">Всего: <?= (int)$total ?></span>
        <div class="pagination-links" id="logs-pagination">
            <?php if ($pages > 1): ?>
                <?php if ($page > 1): ?><a href="?<?= http_build_query(array_merge($filters, ['page' => $page - 1, 'per_page' => $per_page])) ?>" class="page-link">‹</a><?php endif; ?>
                <?php
                $start = max(1, $page - 2);
                $end = min($pages, $page + 2);
                for ($i = $start; $i <= $end; $i++):
                ?>
                    <a href="?<?= http_build_query(array_merge($filters, ['page' => $i, 'per_page' => $per_page])) ?>" class="page-link<?= $i === $page ? ' active' : '' ?>"><?= $i ?></a>
                <?php endfor; ?>
                <?php if ($page < $pages): ?><a href="?<?= http_build_query(array_merge($filters, ['page' => $page + 1, 'per_page' => $per_page])) ?>" class="page-link">›</a><?php endif; ?>
            <?php endif; ?>
        </div>
    </div>
</div>

<script>
(function () {
  var CSRF = '<?= csrf_token() ?>';
  var btn = document.getElementById('logs-clear-btn');
  if (!btn) return;
  btn.addEventListener('click', function () {
    if (!confirm('Очистить все логи? Это действие необратимо.')) return;
    fetch('/admin/logs/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ csrf_token: CSRF })
    }).then(function (r) { return r.json(); }).then(function (res) {
      if (res.success) {
        location.reload();
      } else {
        alert(res.error || 'Ошибка очистки');
      }
    });
  });
})();
</script>
