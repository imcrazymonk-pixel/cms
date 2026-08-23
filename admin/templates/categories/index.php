<div class="page-header-actions">
    <h2>Категории</h2>
    <button type="button" class="btn btn-primary" onclick="toggleCategoryForm()"><?= icon('add') ?> Добавить категорию</button>
</div>

<?php if (Request::get('success') === 'created'): ?>
<div class="alert alert-success">Категория создана</div>
<?php elseif (Request::get('success') === 'updated'): ?>
<div class="alert alert-success">Категория обновлена</div>
<?php elseif (Request::get('success') === 'deleted'): ?>
<div class="alert alert-info">Категория удалена</div>
<?php endif; ?>

<!-- Форма добавления -->
<div id="category-form" class="form-container" style="display: none;">
    <form method="POST" action="/admin/categories/store" class="form-inline">
        <?= csrf_field() ?>
        <input type="text" name="name" class="form-control" placeholder="Название категории" required>
        <input type="text" name="slug" class="form-control" placeholder="Slug (URL)">
        <input type="text" name="description" class="form-control" placeholder="Описание">
        <button type="submit" class="btn btn-success">Сохранить</button>
        <button type="button" class="btn btn-secondary" onclick="toggleCategoryForm()">Отмена</button>
    </form>
</div>

<table class="data-table">
    <thead>
        <tr>
            <th>ID</th>
            <th>Название</th>
            <th>Slug</th>
            <th>Описание</th>
            <th>Постов</th>
            <th>Действия</th>
        </tr>
    </thead>
    <tbody>
        <?php if (!empty($categories)): ?>
            <?php foreach ($categories as $cat): ?>
            <tr>
                <td><?= $cat['id'] ?></td>
                <td>
                    <form method="POST" action="/admin/categories/update/<?= $cat['id'] ?>" class="form-inline">
                        <?= csrf_field() ?>
                        <input type="text" name="name" class="form-control" value="<?= TemplateEngine::e($cat['name']) ?>" required>
                    </form>
                </td>
                <td><?= TemplateEngine::e($cat['slug']) ?></td>
                <td><?= TemplateEngine::e($cat['description']) ?></td>
                <td><?= $cat['posts_count'] ?></td>
                <td class="actions">
                    <button type="submit" form="update-cat-<?= $cat['id'] ?>" class="btn btn-sm btn-primary" title="Сохранить"><?= icon('edit') ?></button>
                    <a href="/admin/categories/delete/<?= $cat['id'] ?>" class="btn btn-sm btn-danger"
                       onclick="return confirm('Удалить категорию?')" title="Удалить">🗑️</a>
                </td>
            </tr>
            <?php endforeach; ?>
        <?php else: ?>
            <tr>
                <td colspan="6" class="text-center">
                    <div class="empty-state">
                        <div class="empty-icon"><?= icon('categories') ?></div>
                        <h3>Категорий пока нет</h3>
                        <p>Создайте первую категорию, чтобы упорядочить контент</p>
                        <a href="/admin/categories/create" class="btn btn-primary"><?= icon('add') ?> Создать категорию</a>
                    </div>
                </td>
            </tr>
        <?php endif; ?>
    </tbody>
</table>

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

function toggleCategoryForm() {
    const form = document.getElementById('category-form');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

// Автогенерация slug из названия категории
let userEditedSlug = false;

document.addEventListener('DOMContentLoaded', function() {
    const nameInput = document.querySelector('#category-form input[name="name"]');
    const slugInput = document.querySelector('#category-form input[name="slug"]');
    
    if (nameInput && slugInput) {
        // Отслеживаем ручное редактирование slug
        slugInput.addEventListener('input', function() {
            userEditedSlug = true;
        });
        
        // Генерируем slug только если пользователь не редактировал его вручную
        nameInput.addEventListener('input', function() {
            if (!userEditedSlug) {
                let slug = transliterate(this.value)
                    .toLowerCase()
                    .replace(/[^a-z0-9\s-]/g, '')
                    .replace(/\s+/g, '-')
                    .replace(/-+/g, '-')
                    .trim();
                slugInput.value = slug;
            }
        });
    }
});
</script>
