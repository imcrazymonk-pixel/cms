<div class="dg-toolbar">
    <a href="/admin/posts" class="btn btn-ghost"><?= icon('back') ?> Назад к списку</a>
</div>

<form method="POST" action="<?= isset($post['id']) ? '/admin/posts/update/' . $post['id'] : '/admin/posts/store' ?>" 
      class="card form-card form-post" enctype="multipart/form-data">
    <?= csrf_field() ?>
    
    <div class="form-row">
        <div class="form-col-main">
            <div class="form-group">
                <label for="title">Заголовок *</label>
                <input type="text" id="title" name="title" class="form-control" 
                       value="<?= TemplateEngine::e($post['title'] ?? '') ?>" required>
            </div>
            
            <div class="form-group">
                <label for="slug">Slug (URL)</label>
                <input type="text" id="slug" name="slug" class="form-control" 
                       value="<?= TemplateEngine::e($post['slug'] ?? '') ?>" 
                       placeholder="avtomaticheski">
                <small class="form-hint">Оставьте пустым для автогенерации</small>
            </div>
            
            <div class="form-group">
                <label for="content">Содержимое *</label>
                <textarea id="content" name="content" class="editor"><?= TemplateEngine::e($post['content'] ?? '') ?></textarea>
            </div>
        </div>
        
        <div class="form-col-sidebar">
            <div class="form-group">
                <label for="category_id">Категория</label>
                <select id="category_id" name="category_id" class="form-control">
                    <option value="">Без категории</option>
                    <?php foreach ($categories ?? [] as $cat): ?>
                    <option value="<?= $cat['id'] ?>" <?= (($post['category_id'] ?? 0) == $cat['id']) ? 'selected' : '' ?>>
                        <?= TemplateEngine::e($cat['name']) ?>
                    </option>
                    <?php endforeach; ?>
                </select>
            </div>
            
            <div class="form-group">
                <label for="status">Статус</label>
                <select id="status" name="status" class="form-control">
                    <option value="draft" <?= (($post['status'] ?? 'draft') === 'draft') ? 'selected' : '' ?>>Черновик</option>
                    <option value="published" <?= (($post['status'] ?? '') === 'published') ? 'selected' : '' ?>>Опубликован</option>
                    <option value="archived" <?= (($post['status'] ?? '') === 'archived') ? 'selected' : '' ?>>Архив</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="image">Изображение</label>
                <input type="file" id="image" name="image" class="form-control" accept="image/*">
                <?php if (!empty($post['image'])): ?>
                <div class="image-preview">
                    <img src="<?= $post['image'] ?>" alt="Текущее изображение">
                </div>
                <?php endif; ?>
            </div>
            
            <div class="form-group">
                <label for="excerpt">Краткое описание</label>
                <textarea id="excerpt" name="excerpt" class="form-control" rows="3" 
                          placeholder="Для анонса в списке постов"><?= TemplateEngine::e($post['excerpt'] ?? '') ?></textarea>
            </div>
            
            <div class="form-actions">
                <button type="submit" class="btn btn-primary btn-block">
                    <?= isset($post['id']) ? icon('save') . ' Сохранить' : icon('add') . ' Создать' ?>
                </button>
                <a href="/admin/posts" class="btn btn-secondary btn-block">Отмена</a>
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
