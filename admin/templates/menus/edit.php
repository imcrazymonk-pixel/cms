<div class="page-header-actions">
    <h2>Редактировать пункт меню</h2>
    <a href="/admin/menus" class="btn btn-secondary">← Назад к меню</a>
</div>

<?php if (Session::get('menu_errors')): ?>
<div class="alert alert-error">
    <ul>
        <?php foreach (Session::flash('menu_errors') as $error): ?>
        <li><?= TemplateEngine::e($error) ?></li>
        <?php endforeach; ?>
    </ul>
</div>
<?php endif; ?>

<?php $old = Session::flash('menu_old') ?: []; ?>

<form method="POST" action="/admin/menus/update/<?= $menuItem['id'] ?>" class="form-horizontal">
    <?= csrf_field() ?>

    <div class="form-group">
        <label for="name">Название</label>
        <input type="text" id="name" name="name" class="form-control"
               value="<?= TemplateEngine::e($old['name'] ?? $menuItem['name']) ?>" required>
    </div>

    <div class="form-group">
        <label for="url">URL (например, /about)</label>
        <input type="text" id="url" name="url" class="form-control"
               value="<?= TemplateEngine::e($old['url'] ?? $menuItem['url']) ?>" required>
    </div>

    <div class="form-group">
        <label for="location">Расположение</label>
        <select id="location" name="location" class="form-control">
            <option value="main" <?= ($old['location'] ?? $menuItem['location']) === 'main' ? 'selected' : '' ?>>Главное меню</option>
            <option value="footer" <?= ($old['location'] ?? $menuItem['location']) === 'footer' ? 'selected' : '' ?>>Футер</option>
        </select>
    </div>

    <div class="form-actions">
        <button type="submit" class="btn btn-primary">💾 Сохранить</button>
        <a href="/admin/menus" class="btn btn-secondary">Отмена</a>
    </div>
</form>
