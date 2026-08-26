<?php if (Request::get('success') === 'created'): ?>
<div class="alert alert-success">Категория создана</div>
<?php elseif (Request::get('success') === 'updated'): ?>
<div class="alert alert-success">Категория обновлена</div>
<?php elseif (Request::get('success') === 'deleted'): ?>
<div class="alert alert-info">Категория удалена</div>
<?php endif; ?>

<!-- Форма добавления -->
<div id="category-form" class="card" style="display: none; margin-bottom: 16px;">
    <form method="POST" action="/admin/categories/store">
        <?= csrf_field() ?>
        <div class="form-row">
            <div class="form-group">
                <input type="text" name="name" placeholder="Название категории" required>
            </div>
            <div class="form-group">
                <input type="text" name="slug" placeholder="Slug (URL)">
            </div>
            <div class="form-group">
                <input type="text" name="description" placeholder="Описание">
            </div>
        </div>
        <div class="form-actions">
            <button type="submit" class="btn btn-primary">Сохранить</button>
            <button type="button" class="btn btn-ghost" onclick="toggleCategoryForm()">Отмена</button>
        </div>
    </form>
</div>

<div class="dg-toolbar">
    <button type="button" class="btn btn-primary" onclick="toggleCategoryForm()"><?= icon('add') ?> Добавить категорию</button>
</div>

<?php
echo DataGrid::render([
    'columns' => [
        ['key' => 'id', 'label' => 'ID', 'sortable' => true],
        ['key' => 'name', 'label' => 'Название', 'html' => function ($row) {
            return '<form method="POST" action="/admin/categories/update/' . $row['id'] . '" class="form-inline">'
                . csrf_field()
                . '<input type="text" name="name" class="form-control" value="' . TemplateEngine::e($row['name']) . '" required>'
                . '<button type="submit" class="btn btn-sm btn-primary" title="Сохранить">' . icon('edit') . '</button>'
                . '</form>';
        }],
        ['key' => 'slug', 'label' => 'Slug'],
        ['key' => 'description', 'label' => 'Описание'],
        ['key' => 'posts_count', 'label' => 'Постов', 'sortable' => true],
    ],
    'rows' => $categories ?? [],
    'actions' => [
        ['label' => 'delete', 'url' => '/admin/categories/delete/{id}', 'icon' => 'delete', 'confirm' => 'Удалить категорию?'],
    ],
    'empty' => [
        'title' => 'Категорий пока нет',
        'text' => 'Создайте первую категорию, чтобы упорядочить контент',
        'icon' => 'categories',
    ],
]);
?>

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
