<div class="page-header-actions">
    <h2>Страницы</h2>
    <a href="/admin/pages/create" class="btn btn-primary"><?= icon('add') ?> Добавить страницу</a>
</div>

<?php if (Request::get('success') === 'created'): ?>
<div class="alert alert-success">Страница создана</div>
<?php elseif (Request::get('success') === 'updated'): ?>
<div class="alert alert-success">Страница обновлена</div>
<?php elseif (Request::get('success') === 'deleted'): ?>
<div class="alert alert-info">Страница удалена</div>
<?php elseif (Request::get('success') === 'home_set'): ?>
<div class="alert alert-success">Главная страница установлена</div>
<?php elseif (Request::get('error') === 'cannot_delete_home'): ?>
<div class="alert alert-error">Нельзя удалить главную страницу</div>
<?php endif; ?>

<table class="data-table">
    <thead>
        <tr>
            <th>ID</th>
            <th>Заголовок</th>
            <th>Slug</th>
            <th>Автор</th>
            <th>Главная</th>
            <th>Действия</th>
        </tr>
    </thead>
    <tbody>
        <?php if (!empty($pages)): ?>
            <?php foreach ($pages as $page): ?>
            <tr>
                <td><?= $page['id'] ?></td>
                <td>
                    <strong><a href="/admin/pages/edit/<?= $page['id'] ?>"><?= TemplateEngine::e($page['title']) ?></a></strong>
                </td>
                <td><?= TemplateEngine::e($page['slug']) ?></td>
                <td><?= TemplateEngine::e($page['author_name'] ?? '—') ?></td>
                <td>
                    <label style="cursor: pointer;">
                        <input type="radio" name="home_page" value="<?= $page['id'] ?>" 
                               <?= $page['is_home'] ? 'checked' : '' ?> 
                               onchange="setHomePage(<?= $page['id'] ?>)"
                               title="Сделать этой страницей главную">
                    </label>
                </td>
                <td class="actions">
                    <a href="/admin/pages/edit/<?= $page['id'] ?>" class="btn btn-sm btn-primary" title="Редактировать"><?= icon('edit') ?></a>
                    <a href="/page/<?= $page['slug'] ?>" class="btn btn-sm btn-info" target="_blank" title="Просмотр"><?= icon('eye') ?></a>
                    <a href="/admin/pages/delete/<?= $page['id'] ?>" class="btn btn-sm btn-danger"
                       onclick="return confirm('Удалить страницу?')" title="Удалить">🗑️</a>
                </td>
            </tr>
            <?php endforeach; ?>
        <?php else: ?>
            <tr>
                <td colspan="6" class="text-center">
                    <div class="empty-state">
                        <div class="empty-icon"><?= icon('pages') ?></div>
                        <h3>Страниц пока нет</h3>
                        <p>Создайте первую страницу для статического контента</p>
                        <a href="/admin/pages/create" class="btn btn-primary"><?= icon('add') ?> Создать страницу</a>
                    </div>
                </td>
            </tr>
        <?php endif; ?>
    </tbody>
</table>

<script>
function setHomePage(pageId) {
    if (confirm('Установить эту страницу главной?')) {
        window.location.href = '/admin/pages/set-home/' + pageId;
    }
}
</script>
