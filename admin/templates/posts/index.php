<div class="dg-toolbar">
    <a href="/admin/posts/create" class="btn btn-primary"><?= icon('add') ?> Добавить пост</a>
</div>

<div class="dg-filters">
    <form method="GET" action="/admin/posts" class="filters-form">
        <select name="status" onchange="this.form.submit()">
            <option value="">Все статусы</option>
            <option value="published" <?= ($status ?? '') === 'published' ? 'selected' : '' ?>>Опубликованы</option>
            <option value="draft" <?= ($status ?? '') === 'draft' ? 'selected' : '' ?>>Черновики</option>
            <option value="archived" <?= ($status ?? '') === 'archived' ? 'selected' : '' ?>>Архив</option>
        </select>

        <select name="category" onchange="this.form.submit()">
            <option value="">Все категории</option>
            <?php foreach ($categories ?? [] as $cat): ?>
            <option value="<?= $cat['id'] ?>" <?= (($category ?? '') == $cat['id']) ? 'selected' : '' ?>>
                <?= TemplateEngine::e($cat['name']) ?>
            </option>
            <?php endforeach; ?>
        </select>
    </form>
</div>

<?php
echo DataGrid::render([
    'columns' => [
        ['key' => 'id', 'label' => 'ID', 'sortable' => true],
        ['key' => 'title', 'label' => 'Заголовок', 'html' => function ($row) {
            return '<strong><a href="/admin/posts/edit/' . $row['id'] . '">' . TemplateEngine::e($row['title']) . '</a></strong>';
        }],
        ['key' => 'category_name', 'label' => 'Категория', 'html' => function ($row) {
            return TemplateEngine::e($row['category_name'] ?? '—');
        }],
        ['key' => 'status', 'label' => 'Статус', 'html' => function ($row) {
            $labels = ['published' => 'Опубликован', 'draft' => 'Черновик', 'archived' => 'Архив'];
            $st = $row['status'] ?? 'draft';
            return '<span class="badge badge-' . $st . '">' . ($labels[$st] ?? $st) . '</span>';
        }],
        ['key' => 'created_at', 'label' => 'Дата', 'format' => function ($v) {
            return format_date($v, 'd.m.Y');
        }],
        ['key' => 'views', 'label' => 'Просмотры', 'sortable' => true],
    ],
    'rows' => $posts ?? [],
    'actions' => [
        ['label' => 'edit', 'url' => '/admin/posts/edit/{id}', 'icon' => 'edit'],
        ['label' => 'view', 'url' => '/post/{slug}', 'icon' => 'eye', 'target' => '_blank'],
        ['label' => 'delete', 'url' => '/admin/posts/delete/{id}', 'icon' => 'delete', 'confirm' => 'Удалить пост?'],
    ],
    'empty' => [
        'title' => 'Постов пока нет',
        'text' => 'Создайте первый пост, чтобы начать наполнять сайт',
        'action' => '/admin/posts/create',
        'action_label' => 'Создать пост',
        'icon' => 'posts',
    ],
]);
?>
