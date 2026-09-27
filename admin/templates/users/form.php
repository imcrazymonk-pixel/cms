<?php
/**
 * Форма редактирования пользователя
 */
$editUser = $editUser ?? [];
$errors = $errors ?? [];
$old = $old ?? [];
$success = $success ?? '';
?>

<?php if ($success === 'updated'): ?>
<div class="alert alert-success"><?= icon('check') ?> Пользователь обновлён</div>
<?php endif; ?>

<?php if (!empty($errors)): ?>
<div class="alert alert-error">
    <ul style="margin:0;padding-left:20px">
    <?php foreach ($errors as $e): ?>
        <li><?= TemplateEngine::e($e) ?></li>
    <?php endforeach; ?>
    </ul>
</div>
<?php endif; ?>

<div class="dg-toolbar">
    <a href="/admin/users" class="btn btn-ghost btn-sm"><?= icon('arrow-left') ?> Назад к списку</a>
    <button type="button" class="btn btn-primary btn-sm" onclick="document.getElementById('user-edit-form').submit()"><?= icon('save') ?> Сохранить</button>
</div>

<form id="user-edit-form" method="POST" action="/admin/users/update/<?= (int)$editUser['id'] ?>">
    <?= csrf_field() ?>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start">

        <!-- Основная информация -->
        <div class="card form-card">
            <h3><?= icon('user') ?> Основная информация</h3>

            <div class="form-group">
                <label for="login">Логин</label>
                <input type="text" id="login" name="login" class="form-control"
                       value="<?= TemplateEngine::e($old['login'] ?? $editUser['login'] ?? '') ?>" required>
                <div class="help-text">Уникальное имя пользователя для входа</div>
            </div>

            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" class="form-control"
                       value="<?= TemplateEngine::e($old['email'] ?? $editUser['email'] ?? '') ?>" required>
                <div class="help-text">Электронная почта пользователя</div>
            </div>

            <div class="form-group">
                <label for="display_name">Отображаемое имя</label>
                <input type="text" id="display_name" name="display_name" class="form-control"
                       value="<?= TemplateEngine::e($old['display_name'] ?? $editUser['display_name'] ?? '') ?>"
                       placeholder="Например: Иван Иванов">
                <div class="help-text">Имя, которое будет отображаться в системе (необязательно)</div>
            </div>
        </div>

        <!-- Роль и статус -->
        <div class="card form-card">
            <h3><?= icon('shield') ?> Роль и статус</h3>

            <div class="form-group">
                <label for="role">Роль</label>
                <select id="role" name="role" class="form-control">
                    <option value="author" <?= (($old['role'] ?? $editUser['role'] ?? '') === 'author') ? 'selected' : '' ?>>Автор</option>
                    <option value="editor" <?= (($old['role'] ?? $editUser['role'] ?? '') === 'editor') ? 'selected' : '' ?>>Редактор</option>
                    <option value="admin" <?= (($old['role'] ?? $editUser['role'] ?? '') === 'admin') ? 'selected' : '' ?>>Администратор</option>
                </select>
                <div class="help-text">Определяет права доступа в системе</div>
            </div>

            <div class="form-group">
                <label for="status">Статус</label>
                <select id="status" name="status" class="form-control">
                    <option value="active" <?= (($old['status'] ?? $editUser['status'] ?? 'active') === 'active') ? 'selected' : '' ?>>Активен</option>
                    <option value="inactive" <?= (($old['status'] ?? $editUser['status'] ?? '') === 'inactive') ? 'selected' : '' ?>>Неактивен</option>
                    <option value="banned" <?= (($old['status'] ?? $editUser['status'] ?? '') === 'banned') ? 'selected' : '' ?>>Заблокирован</option>
                </select>
                <div class="help-text">Активен — полный доступ, Неактивен — без доступа, Заблокирован — без возможности входа</div>
            </div>

            <div class="form-group">
                <label for="password">Новый пароль</label>
                <input type="password" id="password" name="password" class="form-control"
                       placeholder="Оставьте пустым, чтобы не менять" autocomplete="new-password">
                <div class="help-text">Минимум 6 символов. Если не менять — оставьте пустым</div>
            </div>
        </div>
    </div>

    <!-- Информация о пользователе -->
    <div class="card form-card" style="margin-top:16px">
        <h3><?= icon('info') ?> Информация об учётной записи</h3>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px">
            <div>
                <label class="form-label" style="display:block;margin-bottom:4px;color:var(--text-muted);font-size:0.857rem">ID</label>
                <span style="font-weight:600">#<?= (int)$editUser['id'] ?></span>
            </div>
            <div>
                <label class="form-label" style="display:block;margin-bottom:4px;color:var(--text-muted);font-size:0.857rem">Создан</label>
                <span><?= TemplateEngine::e($editUser['created_at'] ?? '—') ?></span>
            </div>
            <div>
                <label class="form-label" style="display:block;margin-bottom:4px;color:var(--text-muted);font-size:0.857rem">Обновлён</label>
                <span><?= TemplateEngine::e($editUser['updated_at'] ?? '—') ?></span>
            </div>
        </div>
    </div>

    <div class="form-actions" style="margin-top:16px">
        <button type="submit" class="btn btn-primary"><?= icon('save') ?> Сохранить изменения</button>
        <a href="/admin/users" class="btn btn-ghost">Отмена</a>
    </div>
</form>