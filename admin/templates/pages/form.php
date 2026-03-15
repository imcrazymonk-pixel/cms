<div class="page-header-actions">
    <h2><?= isset($page['id']) ? 'Редактировать страницу' : 'Новая страница' ?></h2>
    <a href="/admin/pages" class="btn btn-secondary">← Назад к списку</a>
</div>

<?php
$errors = Session::get('page_errors', []);
$old = Session::get('page_old', []);
Session::remove('page_errors');
Session::remove('page_old');
?>

<?php if (!empty($errors)): ?>
<div class="alert alert-error">
    <ul>
        <?php foreach ($errors as $error): ?>
        <li><?= TemplateEngine::e($error) ?></li>
        <?php endforeach; ?>
    </ul>
</div>
<?php endif; ?>

<form method="POST" action="<?= isset($page['id']) ? '/admin/pages/update/' . $page['id'] : '/admin/pages/store' ?>"
      class="form-post" enctype="multipart/form-data">
    <?= csrf_field() ?>

    <div class="form-row">
        <div class="form-col-main">
            <div class="form-group">
                <label for="title">Заголовок *</label>
                <input type="text" id="title" name="title" class="form-control"
                       value="<?= TemplateEngine::e($page['title'] ?? $old['title'] ?? '') ?>" required>
            </div>

            <div class="form-group">
                <label for="slug">Slug (URL)</label>
                <input type="text" id="slug" name="slug" class="form-control"
                       value="<?= TemplateEngine::e($page['slug'] ?? $old['slug'] ?? '') ?>"
                       placeholder="avtomaticheski">
                <small class="form-hint">Оставьте пустым для автогенерации</small>
            </div>

            <div class="form-group">
                <label for="content">Содержимое *</label>
                <textarea id="content" name="content" class="editor"><?= TemplateEngine::e($page['content'] ?? $old['content'] ?? '') ?></textarea>
            </div>
        </div>

        <div class="form-col-sidebar">
            <div class="form-group">
                <label for="meta_description">Meta Description</label>
                <textarea id="meta_description" name="meta_description" class="form-control" rows="3"
                          placeholder="Для поисковых систем"><?= TemplateEngine::e($page['meta_description'] ?? $old['meta_description'] ?? '') ?></textarea>
            </div>

            <div class="form-actions">
                <button type="submit" class="btn btn-primary btn-block">
                    <?= isset($page['id']) ? '💾 Сохранить' : '➕ Создать' ?>
                </button>
                <a href="/admin/pages" class="btn btn-secondary btn-block">Отмена</a>
            </div>
        </div>
    </div>
</form>

<script>
// Автогенерация slug из заголовка
document.getElementById('title')?.addEventListener('input', function() {
    const slugInput = document.getElementById('slug');
    if (slugInput && !slugInput.value) {
        let slug = this.value.toLowerCase()
            .replace(/[^a-zа-яё0-9\s-]/gi, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .trim();
        slugInput.value = slug;
    }
});
</script>
