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

<div class="card" style="margin-bottom: 20px;">
    <h3 class="page-header-title" style="margin: 0 0 16px;"><?= $editWidget ? 'Редактирование виджета #' . $editWidget['id'] : 'Новый виджет' ?></h3>

    <form method="POST" action="<?= $editWidget ? '/admin/widgets/update/' . $editWidget['id'] : '/admin/widgets/store' ?>">
        <?= csrf_field() ?>

        <div class="form-group">
            <label for="widget-area">Область</label>
            <select id="widget-area" name="area">
                <?php foreach ($areas as $areaKey => $areaLabel): ?>
                <option value="<?= TemplateEngine::e($areaKey) ?>" <?= (($editWidget['area'] ?? '') === $areaKey) ? 'selected' : '' ?>><?= TemplateEngine::e($areaLabel) ?></option>
                <?php endforeach; ?>
            </select>
        </div>

        <div class="form-group">
            <label for="widget-title">Заголовок (необязательно)</label>
            <input type="text" id="widget-title" name="title"
                   value="<?= TemplateEngine::e($editWidget['title'] ?? '') ?>">
        </div>

        <div class="form-group">
            <label for="widget-content">Содержимое (HTML)</label>
            <textarea id="widget-content" name="content" class="editor" rows="6"><?= TemplateEngine::e($editWidget['content'] ?? '') ?></textarea>
        </div>

        <div class="form-group">
            <label for="widget-sort">Порядок сортировки</label>
            <input type="number" id="widget-sort" name="sort_order"
                   value="<?= (int)($editWidget['sort_order'] ?? 0) ?>" min="0" max="999" style="max-width:120px;">
        </div>

        <div class="form-actions">
            <button type="submit" class="btn btn-primary"><?= $editWidget ? icon('save') . ' Сохранить' : icon('add') . ' Добавить' ?></button>
            <?php if ($editWidget): ?>
            <a href="/admin/widgets" class="btn btn-ghost">Отмена</a>
            <?php endif; ?>
        </div>
    </form>
</div>

<div class="card">
    <h3 class="page-header-title" style="margin: 0 0 16px;">Установленные виджеты</h3>

    <?php if (empty($widgets)): ?>
    <div class="empty-state">
        <div class="empty-icon"><?= icon('widgets') ?></div>
        <h3>Виджетов пока нет</h3>
        <p>Добавьте первый виджет, используя форму выше</p>
    </div>
    <?php else: ?>
    <?php foreach ($areas as $areaKey => $areaLabel): ?>
        <?php
        $areaWidgets = array_values(array_filter($widgets, function ($w) use ($areaKey) {
            return $w['area'] === $areaKey;
        }));
        if (empty($areaWidgets)) continue;
        ?>
        <h4 style="margin: 20px 0 10px;"><?= TemplateEngine::e($areaLabel) ?></h4>
        <?php
        echo DataGrid::render([
            'columns' => [
                ['key' => 'id', 'label' => 'ID', 'sortable' => true],
                ['key' => 'title', 'label' => 'Заголовок', 'html' => function ($row) {
                    return TemplateEngine::e($row['title'] ?: '(без заголовка)');
                }],
                ['key' => 'sort_order', 'label' => 'Порядок', 'format' => function ($v) {
                    return (int)$v;
                }],
            ],
            'rows' => $areaWidgets,
            'actions' => [
                ['label' => 'edit', 'url' => '/admin/widgets?edit={id}', 'icon' => 'edit'],
                ['label' => 'delete', 'url' => '/admin/widgets/delete/{id}', 'icon' => 'delete', 'confirm' => 'Удалить виджет?'],
            ],
        ]);
        ?>
    <?php endforeach; ?>
    <?php endif; ?>
</div>
