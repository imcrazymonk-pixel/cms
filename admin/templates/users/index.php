<div class="page-header-actions">
    <h2>Пользователи</h2>
    <button type="button" class="btn btn-primary" onclick="toggleUserForm()">➕ Добавить пользователя</button>
</div>

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
<div id="user-form" class="form-container" style="display: none;">
    <form method="POST" action="/admin/users/store" class="form-inline">
        <?= csrf_field() ?>
        <input type="text" name="login" class="form-control" placeholder="Логин" required>
        <input type="email" name="email" class="form-control" placeholder="Email" required>
        <input type="password" name="password" class="form-control" placeholder="Пароль" required>
        <select name="role" class="form-control">
            <option value="author">Автор</option>
            <option value="editor">Редактор</option>
            <option value="admin">Администратор</option>
        </select>
        <button type="submit" class="btn btn-success">Сохранить</button>
        <button type="button" class="btn btn-secondary" onclick="toggleUserForm()">Отмена</button>
    </form>
</div>

<table class="data-table">
    <thead>
        <tr>
            <th>ID</th>
            <th>Логин</th>
            <th>Email</th>
            <th>Роль</th>
            <th>Постов</th>
            <th>Комментариев</th>
            <th>Действия</th>
        </tr>
    </thead>
    <tbody>
        <?php if (!empty($users)): ?>
            <?php foreach ($users as $userItem): ?>
            <tr>
                <td><?= $userItem['id'] ?></td>
                <td><?= TemplateEngine::e($userItem['login']) ?></td>
                <td><?= TemplateEngine::e($userItem['email']) ?></td>
                <td>
                    <span class="badge badge-<?= $userItem['role'] ?>">
                        <?= $userItem['role'] === 'admin' ? '👑 Администратор' : ($userItem['role'] === 'editor' ? '✏️ Редактор' : '📝 Автор') ?>
                    </span>
                </td>
                <td><?= $userItem['posts_count'] ?></td>
                <td><?= $userItem['comments_count'] ?></td>
                <td class="actions">
                    <?php if ($userItem['id'] != Auth::id()): ?>
                    <a href="/admin/users/delete/<?= $userItem['id'] ?>" class="btn btn-sm btn-danger"
                       onclick="return confirm('Удалить пользователя?')" title="Удалить">🗑️</a>
                    <?php else: ?>
                    <span class="text-muted">Вы</span>
                    <?php endif; ?>
                </td>
            </tr>
            <?php endforeach; ?>
        <?php else: ?>
            <tr>
                <td colspan="7" class="text-center">Пользователей не найдено</td>
            </tr>
        <?php endif; ?>
    </tbody>
</table>

<script>
function toggleUserForm() {
    const form = document.getElementById('user-form');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}
</script>
