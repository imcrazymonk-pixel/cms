<div class="page-header-actions">
    <h2>Все посты</h2>
    <a href="/admin/posts/create" class="btn btn-primary"><?= icon('add') ?> Добавить пост</a>
</div>

<div class="filters">
    <form method="GET" action="/admin/posts" class="filters-form">
        <select name="status" class="form-control" onchange="this.form.submit()">
            <option value="">Все статусы</option>
            <option value="published" <?= ($status ?? '') === 'published' ? 'selected' : '' ?>>Опубликованы</option>
            <option value="draft" <?= ($status ?? '') === 'draft' ? 'selected' : '' ?>>Черновики</option>
            <option value="archived" <?= ($status ?? '') === 'archived' ? 'selected' : '' ?>>Архив</option>
        </select>
        
        <select name="category" class="form-control" onchange="this.form.submit()">
            <option value="">Все категории</option>
            <?php foreach ($categories ?? [] as $cat): ?>
            <option value="<?= $cat['id'] ?>" <?= (($category ?? '') == $cat['id']) ? 'selected' : '' ?>>
                <?= TemplateEngine::e($cat['name']) ?>
            </option>
            <?php endforeach; ?>
        </select>
    </form>
</div>

<table class="data-table">
    <thead>
        <tr>
            <th width="50"><input type="checkbox" id="select-all"></th>
            <th width="50">ID</th>
            <th>Заголовок</th>
            <th width="150">Категория</th>
            <th width="100">Статус</th>
            <th width="120">Дата</th>
            <th width="100">Просмотры</th>
            <th width="120">Действия</th>
        </tr>
    </thead>
    <tbody>
        <?php if (!empty($posts)): ?>
            <?php foreach ($posts as $post): ?>
            <tr>
                <td><input type="checkbox" name="posts[]" value="<?= $post['id'] ?>"></td>
                <td><?= $post['id'] ?></td>
                <td>
                    <strong><a href="/admin/posts/edit/<?= $post['id'] ?>"><?= TemplateEngine::e($post['title']) ?></a></strong>
                </td>
                <td><?= TemplateEngine::e($post['category_name'] ?? '—') ?></td>
                <td>
                    <span class="badge badge-<?= $post['status'] ?>">
                        <?= $post['status'] === 'published' ? 'Опубликован' : ($post['status'] === 'draft' ? 'Черновик' : 'Архив') ?>
                    </span>
                </td>
                <td><?= format_date($post['created_at'], 'd.m.Y') ?></td>
                <td><?= $post['views'] ?></td>
                <td class="actions">
                    <a href="/admin/posts/edit/<?= $post['id'] ?>" class="btn btn-sm btn-primary" title="Редактировать"><?= icon('edit') ?></a>
                    <a href="/post/<?= $post['slug'] ?>" class="btn btn-sm btn-info" target="_blank" title="Просмотр"><?= icon('eye') ?></a>
                    <a href="/admin/posts/delete/<?= $post['id'] ?>" class="btn btn-sm btn-danger" 
                       onclick="return confirm('Удалить пост?')" title="Удалить">🗑️</a>
                </td>
            </tr>
            <?php endforeach; ?>
        <?php else: ?>
            <tr>
                <td colspan="8" class="text-center">
                    <div class="empty-state">
                        <div class="empty-icon"><?= icon('posts') ?></div>
                        <h3>Постов пока нет</h3>
                        <p>Создайте первый пост, чтобы начать наполнять сайт</p>
                        <a href="/admin/posts/create" class="btn btn-primary"><?= icon('add') ?> Создать пост</a>
                    </div>
                </td>
            </tr>
        <?php endif; ?>
    </tbody>
</table>

<?php if (!empty($pagination)): ?>
<div class="pagination">
    <?= $pagination ?>
</div>
<?php endif; ?>

<script>
document.getElementById('select-all')?.addEventListener('change', function() {
    document.querySelectorAll('input[name="posts[]"]').forEach(cb => cb.checked = this.checked);
});
</script>
