<?php if (Request::get('success') === 'created'): ?>
<div class="alert alert-success">Пользователь создан</div>
<?php elseif (Request::get('success') === 'updated'): ?>
<div class="alert alert-success">Пользователь обновлён</div>
<?php elseif (Request::get('success') === 'deleted'): ?>
<div class="alert alert-info">Пользователь удалён</div>
<?php endif; ?>

<?php if (Request::get('error') === 'cannot_delete_self'): ?>
<div class="alert alert-error">Нельзя удалить самого себя</div>
<?php endif; ?>

<!-- Форма добавления -->
<div id="user-form" class="card" style="display: none; margin-bottom: 16px;">
    <form method="POST" action="/admin/users/store">
        <?= csrf_field() ?>
        <div class="form-row">
            <div class="form-group">
                <input type="text" name="login" placeholder="Логин" required>
            </div>
            <div class="form-group">
                <input type="email" name="email" placeholder="Email" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" placeholder="Пароль" required>
            </div>
            <div class="form-group">
                <select name="role">
                    <option value="author">Автор</option>
                    <option value="editor">Редактор</option>
                    <option value="admin">Администратор</option>
                </select>
            </div>
        </div>
        <div class="form-actions">
            <button type="submit" class="btn btn-primary">Сохранить</button>
            <button type="button" class="btn btn-ghost" onclick="toggleUserForm()">Отмена</button>
        </div>
    </form>
</div>

<div class="dg-toolbar">
    <button type="button" class="btn btn-primary" onclick="toggleUserForm()"><?= icon('add') ?> Добавить пользователя</button>
</div>

<?php
echo DataGrid::render([
    'columns' => [
        ['key' => 'id', 'label' => 'ID', 'sortable' => true],
        ['key' => 'login', 'label' => 'Логин', 'html' => function ($row) {
            return '<strong>' . TemplateEngine::e($row['login']) . '</strong>';
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
        ['key' => 'posts_count', 'label' => 'Постов', 'sortable' => true],
        ['key' => 'comments_count', 'label' => 'Комментариев'],
        ['key' => '_actions', 'label' => 'Действия', 'html' => function ($row) {
            if (($row['id'] ?? 0) == Auth::id()) {
                return '<span class="text-muted">Вы</span>';
            }
            return '<a href="/admin/users/delete/' . $row['id'] . '" class="btn btn-sm btn-danger" title="Удалить" data-confirm="Удалить пользователя?">' . icon('delete') . '</a>';
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
