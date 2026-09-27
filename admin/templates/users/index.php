<?php if (Request::get('success') === 'created'): ?>
<div class="alert alert-success"><?= icon('check') ?> Пользователь создан</div>
<?php elseif (Request::get('success') === 'updated'): ?>
<div class="alert alert-success"><?= icon('check') ?> Пользователь обновлён</div>
<?php elseif (Request::get('success') === 'deleted'): ?>
<div class="alert alert-info"><?= icon('info') ?> Пользователь удалён</div>
<?php endif; ?>

<?php if (Request::get('error') === 'cannot_delete_self'): ?>
<div class="alert alert-error"><?= icon('alert-triangle') ?> Нельзя удалить самого себя</div>
<?php elseif (Request::get('error') === 'not_found'): ?>
<div class="alert alert-error"><?= icon('alert-triangle') ?> Пользователь не найден</div>
<?php endif; ?>

<!-- Форма добавления -->
<div id="user-form" class="card" style="display: none; margin-bottom: 16px;">
    <form method="POST" action="/admin/users/store">
        <?= csrf_field() ?>
        <h3 style="margin-bottom:16px"><?= icon('user-plus') ?> Новый пользователь</h3>
        <div class="form-row">
            <div class="form-group">
                <label>Логин</label>
                <input type="text" name="login" placeholder="Логин" required>
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" placeholder="Email" required>
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Пароль</label>
                <input type="password" name="password" placeholder="Пароль" required>
            </div>
            <div class="form-group">
                <label>Отображаемое имя</label>
                <input type="text" name="display_name" placeholder="Имя (необязательно)">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Роль</label>
                <select name="role">
                    <option value="author">Автор</option>
                    <option value="editor">Редактор</option>
                    <option value="admin">Администратор</option>
                </select>
            </div>
            <div class="form-group">
                <label>Статус</label>
                <select name="status">
                    <option value="active">Активен</option>
                    <option value="inactive">Неактивен</option>
                    <option value="banned">Заблокирован</option>
                </select>
            </div>
        </div>
        <div class="form-actions">
            <button type="submit" class="btn btn-primary"><?= icon('save') ?> Сохранить</button>
            <button type="button" class="btn btn-ghost" onclick="toggleUserForm()">Отмена</button>
        </div>
    </form>
</div>

<div class="dg-toolbar">
    <button type="button" class="btn btn-primary" onclick="toggleUserForm()"><?= icon('add') ?> Добавить пользователя</button>
</div>

<?php
$statusBadges = [
    'active' => 'badge-success',
    'inactive' => 'badge-neutral',
    'banned' => 'badge-error',
];
$statusLabels = [
    'active' => 'Активен',
    'inactive' => 'Неактивен',
    'banned' => 'Заблокирован',
];

echo DataGrid::render([
    'columns' => [
        ['key' => 'id', 'label' => 'ID', 'sortable' => true],
        ['key' => 'login', 'label' => 'Логин', 'html' => function ($row) {
            $name = $row['display_name'] ?: $row['login'];
            return '<strong>' . TemplateEngine::e($name) . '</strong>';
        }],
        ['key' => 'email', 'label' => 'Email', 'html' => function ($row) {
            return TemplateEngine::e($row['email']);
        }],
        ['key' => 'role', 'label' => 'Роль', 'html' => function ($row) {
            $labels = ['admin' => 'Администратор', 'editor' => 'Редактор', 'author' => 'Автор'];
            $classes = ['admin' => 'badge-info', 'editor' => 'badge-neutral', 'author' => 'badge-neutral'];
            $role = $row['role'] ?? 'author';
            return '<span class="badge ' . ($classes[$role] ?? 'badge-neutral') . '">' . ($labels[$role] ?? $role) . '</span>';
        }],
        ['key' => 'status', 'label' => 'Статус', 'html' => function ($row) use ($statusBadges, $statusLabels) {
            $status = $row['status'] ?? 'active';
            return '<span class="badge ' . ($statusBadges[$status] ?? 'badge-neutral') . '">' . ($statusLabels[$status] ?? $status) . '</span>';
        }],
        ['key' => 'posts_count', 'label' => 'Постов', 'sortable' => true],
        ['key' => 'comments_count', 'label' => 'Коммент.'],
        ['key' => '_actions', 'label' => 'Действия', 'html' => function ($row) {
            $self = ($row['id'] ?? 0) == Auth::id();
            if ($self) {
                return '<a href="/admin/users/edit/' . $row['id'] . '" class="btn btn-ghost btn-sm" title="Редактировать">' . icon('edit') . '</a> <span class="text-muted" style="opacity:0.5">Вы</span>';
            }
            return '<a href="/admin/users/edit/' . $row['id'] . '" class="btn btn-ghost btn-sm" title="Редактировать">' . icon('edit') . '</a>'
                  . '<a href="/admin/users/delete/' . $row['id'] . '" class="btn btn-ghost btn-sm" style="color:var(--color-danger)" title="Удалить" data-confirm="Удалить пользователя?">' . icon('trash-2') . '</a>';
        }],
    ],
    'rows' => $users ?? [],
    'empty' => [
        'title' => 'Пользователей пока нет',
        'text' => 'Пригласите первого пользователя или создайте вручную',
        'icon' => 'users',
    ],
]);
?>

<script>
function toggleUserForm() {
    const form = document.getElementById('user-form');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}
</script>