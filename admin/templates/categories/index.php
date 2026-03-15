<div class="page-header-actions">
    <h2>Категории</h2>
    <button type="button" class="btn btn-primary" onclick="toggleCategoryForm()">➕ Добавить категорию</button>
</div>

<?php if (Request::get('success') === 'created'): ?>
<div class="alert alert-success">Категория создана</div>
<?php elseif (Request::get('success') === 'updated'): ?>
<div class="alert alert-success">Категория обновлена</div>
<?php elseif (Request::get('success') === 'deleted'): ?>
<div class="alert alert-info">Категория удалена</div>
<?php endif; ?>

<!-- Форма добавления -->
<div id="category-form" class="form-container" style="display: none;">
    <form method="POST" action="/admin/categories/store" class="form-inline">
        <?= csrf_field() ?>
        <input type="text" name="name" class="form-control" placeholder="Название категории" required>
        <input type="text" name="slug" class="form-control" placeholder="Slug (URL)">
        <input type="text" name="description" class="form-control" placeholder="Описание">
        <button type="submit" class="btn btn-success">Сохранить</button>
        <button type="button" class="btn btn-secondary" onclick="toggleCategoryForm()">Отмена</button>
    </form>
</div>

<table class="data-table">
    <thead>
        <tr>
            <th>ID</th>
            <th>Название</th>
            <th>Slug</th>
            <th>Описание</th>
            <th>Постов</th>
            <th>Действия</th>
        </tr>
    </thead>
    <tbody>
        <?php if (!empty($categories)): ?>
            <?php foreach ($categories as $cat): ?>
            <tr>
                <td><?= $cat['id'] ?></td>
                <td>
                    <form method="POST" action="/admin/categories/update/<?= $cat['id'] ?>" class="form-inline">
                        <?= csrf_field() ?>
                        <input type="text" name="name" class="form-control" value="<?= TemplateEngine::e($cat['name']) ?>" required>
                    </form>
                </td>
                <td><?= TemplateEngine::e($cat['slug']) ?></td>
                <td><?= TemplateEngine::e($cat['description']) ?></td>
                <td><?= $cat['posts_count'] ?></td>
                <td class="actions">
                    <button type="submit" form="update-cat-<?= $cat['id'] ?>" class="btn btn-sm btn-primary" title="Сохранить">✏️</button>
                    <a href="/admin/categories/delete/<?= $cat['id'] ?>" class="btn btn-sm btn-danger"
                       onclick="return confirm('Удалить категорию?')" title="Удалить">🗑️</a>
                </td>
            </tr>
            <?php endforeach; ?>
        <?php else: ?>
            <tr>
                <td colspan="6" class="text-center">Категорий пока нет</td>
            </tr>
        <?php endif; ?>
    </tbody>
</table>

<script>
function toggleCategoryForm() {
    const form = document.getElementById('category-form');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}
</script>
