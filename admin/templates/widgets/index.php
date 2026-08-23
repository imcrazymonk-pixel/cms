<div class="page-header-actions">
    <h2>Виджеты</h2>
</div>

<?php if (Request::get('success') === 'created'): ?>
<div class="alert alert-success">Виджет добавлен</div>
<?php elseif (Request::get('success') === 'updated'): ?>
<div class="alert alert-success">Виджет обновлён</div>
<?php elseif (Request::get('success') === 'deleted'): ?>
<div class="alert alert-success">Виджет удалён</div>
<?php endif; ?>

<div class="alert alert-info">
    Виджеты выводятся в областях, объявленных активной темой (шапка, подвал и т.д.).
    Содержимое поддерживает HTML.
</div>

<div class="settings-section">
    <h3><?= $editWidget ? '✏️ Редактирование виджета #' . $editWidget['id'] : '➕ Новый виджет' ?></h3>

    <form method="POST" action="<?= $editWidget ? '/admin/widgets/update/' . $editWidget['id'] : '/admin/widgets/store' ?>">
        <?= csrf_field() ?>

        <div class="form-group">
            <label for="widget-area">Область</label>
            <select id="widget-area" name="area" class="form-control">
                <?php foreach ($areas as $areaKey => $areaLabel): ?>
                <option value="<?= TemplateEngine::e($areaKey) ?>" <?= (($editWidget['area'] ?? '') === $areaKey) ? 'selected' : '' ?>><?= TemplateEngine::e($areaLabel) ?></option>
                <?php endforeach; ?>
            </select>
        </div>

        <div class="form-group">
            <label for="widget-title">Заголовок (необязательно)</label>
            <input type="text" id="widget-title" name="title" class="form-control"
                   value="<?= TemplateEngine::e($editWidget['title'] ?? '') ?>">
        </div>

        <div class="form-group">
            <label for="widget-content">Содержимое (HTML)</label>
            <textarea id="widget-content" name="content" class="form-control editor" rows="6"><?= TemplateEngine::e($editWidget['content'] ?? '') ?></textarea>
        </div>

        <div class="form-group">
            <label for="widget-sort">Порядок сортировки</label>
            <input type="number" id="widget-sort" name="sort_order" class="form-control"
                   value="<?= (int)($editWidget['sort_order'] ?? 0) ?>" min="0" max="999" style="max-width:120px;">
        </div>

        <button type="submit" class="btn btn-primary"><?= $editWidget ? '💾 Сохранить' : '➕ Добавить' ?></button>
        <?php if ($editWidget): ?>
        <a href="/admin/widgets" class="btn">Отмена</a>
        <?php endif; ?>
    </form>
</div>

<div class="settings-section">
    <h3>Установленные виджеты</h3>

    <?php if (empty($widgets)): ?>
    <p style="color: var(--text-light);">Виджетов пока нет. Добавьте первый выше.</p>
    <?php else: ?>
    <?php foreach ($areas as $areaKey => $areaLabel): $areaWidgets = array_filter($widgets, fn($w) => $w['area'] === $areaKey); ?>
    <?php if (empty($areaWidgets)) continue; ?>
    <h4 style="margin: 20px 0 10px;"><?= TemplateEngine::e($areaLabel) ?></h4>
    <table class="admin-table">
        <thead>
            <tr>
                <th>ID</th>
                <th>Заголовок</th>
                <th>Порядок</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($areaWidgets as $widget): ?>
            <tr>
                <td><?= $widget['id'] ?></td>
                <td><?= TemplateEngine::e($widget['title'] ?: '(без заголовка)') ?></td>
                <td><?= (int)$widget['sort_order'] ?></td>
                <td>
                    <a href="/admin/widgets?edit=<?= $widget['id'] ?>" class="btn btn-sm">✏️</a>
                    <a href="/admin/widgets/delete/<?= $widget['id'] ?>" class="btn btn-sm btn-danger" onclick="return confirm('Удалить виджет?');">🗑️</a>
                </td>
            </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
    <?php endforeach; ?>
    <?php endif; ?>
</div>

<style>
.admin-table { width: 100%; border-collapse: collapse; }
.admin-table th, .admin-table td { padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--gray-300); }
.btn-sm { padding: 4px 8px; font-size: 14px; }
.btn-danger { color: #dc3545; }
</style>
