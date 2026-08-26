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

<div class="dg-toolbar">
    <a href="/admin/pages/create" class="btn btn-primary"><?= icon('add') ?> Добавить страницу</a>
</div>

<?php
echo DataGrid::render([
    'columns' => [
        ['key' => 'id', 'label' => 'ID', 'sortable' => true],
        ['key' => 'title', 'label' => 'Заголовок', 'html' => function ($row) {
            return '<strong><a href="/admin/pages/edit/' . $row['id'] . '">' . TemplateEngine::e($row['title']) . '</a></strong>';
        }],
        ['key' => 'slug', 'label' => 'Slug'],
        ['key' => 'author_name', 'label' => 'Автор', 'html' => function ($row) {
            return TemplateEngine::e($row['author_name'] ?? '—');
        }],
        ['key' => 'is_home', 'label' => 'Главная', 'html' => function ($row) {
            return '<label style="cursor: pointer;" title="Сделать этой страницей главную">'
                . '<input type="radio" name="home_page" value="' . $row['id'] . '"'
                . ($row['is_home'] ? ' checked' : '')
                . ' onchange="setHomePage(' . $row['id'] . ')"></label>';
        }],
    ],
    'rows' => $pages ?? [],
    'actions' => [
        ['label' => 'edit', 'url' => '/admin/pages/edit/{id}', 'icon' => 'edit'],
        ['label' => 'view', 'url' => '/page/{slug}', 'icon' => 'eye', 'target' => '_blank'],
        ['label' => 'delete', 'url' => '/admin/pages/delete/{id}', 'icon' => 'delete', 'confirm' => 'Удалить страницу?'],
    ],
    'empty' => [
        'title' => 'Страниц пока нет',
        'text' => 'Создайте первую страницу для статического контента',
        'action' => '/admin/pages/create',
        'action_label' => 'Создать страницу',
        'icon' => 'pages',
    ],
]);
?>

<script>
function setHomePage(pageId) {
    if (confirm('Установить эту страницу главной?')) {
        window.location.href = '/admin/pages/set-home/' + pageId;
    }
}
</script>
