<?php if (Request::get('success') === 'created'): ?>
<div class="alert alert-success">Пункт меню добавлен</div>
<?php elseif (Request::get('success') === 'deleted'): ?>
<div class="alert alert-info">Пункт меню удалён</div>
<?php elseif (Request::get('success') === 'updated'): ?>
<div class="alert alert-success">Пункт меню обновлён</div>
<?php endif; ?>

<?php if (Session::get('menu_error')): ?>
<div class="alert alert-error"><?= Session::flash('menu_error') ?></div>
<?php endif; ?>

<!-- Форма добавления -->
<div id="menu-form" class="card" style="display: none; margin-bottom: 16px;">
    <form method="POST" action="/admin/menus/store">
        <?= csrf_field() ?>
        <div class="form-row">
            <div class="form-group">
                <input type="text" name="name" placeholder="Название" required>
            </div>
            <div class="form-group">
                <input type="text" name="url" placeholder="URL (например, /about)" required>
            </div>
            <div class="form-group">
                <select name="location">
                    <option value="main">Главное меню</option>
                    <option value="footer">Футер</option>
                </select>
            </div>
        </div>
        <div class="form-actions">
            <button type="submit" class="btn btn-primary"><?= icon('add') ?> Добавить</button>
            <button type="button" class="btn btn-ghost" onclick="toggleMenuForm()">Отмена</button>
        </div>
    </form>
</div>

<div class="dg-toolbar">
    <button type="button" class="btn btn-primary" onclick="toggleMenuForm()"><?= icon('add') ?> Добавить пункт</button>
</div>

<?php
echo DataGrid::render([
    'columns' => [
        ['key' => 'id', 'label' => 'ID', 'sortable' => true],
        ['key' => 'name', 'label' => 'Название', 'html' => function ($row) {
            return '<strong>' . TemplateEngine::e($row['name']) . '</strong>';
        }],
        ['key' => 'url', 'label' => 'URL', 'html' => function ($row) {
            return '<code>' . TemplateEngine::e($row['url']) . '</code>';
        }],
        ['key' => 'location', 'label' => 'Расположение', 'html' => function ($row) {
            $loc = $row['location'] ?? 'main';
            $cls = $loc === 'main' ? 'badge-success' : 'badge-neutral';
            $label = $loc === 'main' ? 'Главное' : 'Футер';
            return '<span class="badge ' . $cls . '">' . $label . '</span>';
        }],
    ],
    'rows' => $menus ?? [],
    'actions' => [
        ['label' => 'edit', 'url' => '/admin/menus/edit/{id}', 'icon' => 'edit'],
        ['label' => 'delete', 'url' => '/admin/menus/delete/{id}', 'icon' => 'delete', 'confirm' => 'Удалить пункт меню?'],
    ],
    'empty' => [
        'title' => 'Пунктов меню пока нет',
        'text' => 'Добавьте первый пункт меню для навигации по сайту',
        'icon' => 'menus',
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

function toggleMenuForm() {
    const form = document.getElementById('menu-form');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

// Автогенерация URL из названия пункта меню
let userEditedUrl = false;

document.addEventListener('DOMContentLoaded', function() {
    const nameInput = document.querySelector('#menu-form input[name="name"]');
    const urlInput = document.querySelector('#menu-form input[name="url"]');

    if (nameInput && urlInput) {
        // Отслеживаем ручное редактирование URL
        urlInput.addEventListener('input', function() {
            userEditedUrl = true;
        });

        // Генерируем URL только если пользователь не редактировал его вручную
        nameInput.addEventListener('input', function() {
            if (!userEditedUrl) {
                let slug = transliterate(this.value)
                    .toLowerCase()
                    .replace(/[^a-z0-9\s-]/g, '')
                    .replace(/\s+/g, '-')
                    .replace(/-+/g, '-')
                    .trim();
                urlInput.value = '/' + slug;
            }
        });
    }
});
</script>
