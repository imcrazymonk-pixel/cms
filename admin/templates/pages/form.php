<div class="dg-toolbar">
    <a href="/admin/pages" class="btn btn-ghost"><?= icon('back') ?> Назад к списку</a>
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
      class="card form-card form-post" enctype="multipart/form-data">
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
                <label for="template">Шаблон</label>
                <select id="template" name="template" class="form-control">
                    <option value="default" <?= (($page['template'] ?? $old['template'] ?? '') === 'default') ? 'selected' : '' ?>>📄 Стандартный (default)</option>
                    <option value="fullwidth" <?= (($page['template'] ?? $old['template'] ?? '') === 'fullwidth') ? 'selected' : '' ?>>📐 На всю ширину (fullwidth)</option>
                    <option value="landing" <?= (($page['template'] ?? $old['template'] ?? '') === 'landing') ? 'selected' : '' ?>>🎯 Лендинг (landing)</option>
                    <option value="blank" <?= (($page['template'] ?? $old['template'] ?? '') === 'blank') ? 'selected' : '' ?>>📝 Чистый (blank)</option>
                </select>
                <small class="form-hint">Выберите шаблон для отображения</small>
            </div>

            <div class="form-group">
                <label for="meta_description">Meta Description</label>
                <textarea id="meta_description" name="meta_description" class="form-control" rows="3"
                          placeholder="Для поисковых систем"><?= TemplateEngine::e($page['meta_description'] ?? $old['meta_description'] ?? '') ?></textarea>
            </div>

            <div class="form-actions">
                <button type="submit" class="btn btn-primary btn-block">
                    <?= isset($page['id']) ? icon('save') . ' Сохранить' : icon('add') . ' Создать' ?>
                </button>
                <a href="/admin/pages" class="btn btn-secondary btn-block">Отмена</a>
            </div>
        </div>
    </div>
</form>

<script>
// Транслитерация кириллицы в латиницу
function transliterate(word) {
    const transliteration = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch',
        'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
        'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
        'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
        'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
        'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'Ch',
        'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
        'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
        '№': ''
    };
    
    let result = '';
    for (let i = 0; i < word.length; i++) {
        result += transliteration[word[i]] || word[i];
    }
    return result;
}

// Автогенерация slug из заголовка
const titleInput = document.getElementById('title');
const slugInput = document.getElementById('slug');
let userEditedSlug = false;

// Отслеживаем ручное редактирование slug
slugInput?.addEventListener('input', function() {
    userEditedSlug = true;
});

// Генерируем slug только если пользователь не редактировал его вручную
titleInput?.addEventListener('input', function() {
    if (slugInput && !userEditedSlug) {
        let slug = transliterate(this.value)
            .toLowerCase()
            .replace(/[^a-z0-9\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .trim();
        slugInput.value = slug;
    }
});
</script>
