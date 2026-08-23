<div class="page-header-actions">
    <h2>Меню</h2>
    <button type="button" class="btn btn-primary" onclick="toggleMenuForm()"><?= icon('add') ?> Добавить пункт</button>
</div>

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
<div id="menu-form" class="form-container" style="display: none;">
    <form method="POST" action="/admin/menus/store" class="form-inline">
        <?= csrf_field() ?>
        <input type="text" name="name" class="form-control" placeholder="Название" required>
        <input type="text" name="url" class="form-control" placeholder="URL (например, /about)" required>
        <select name="location" class="form-control">
            <option value="main">Главное меню</option>
            <option value="footer">Футер</option>
        </select>
        <button type="submit" class="btn btn-success">Добавить</button>
        <button type="button" class="btn btn-secondary" onclick="toggleMenuForm()">Отмена</button>
    </form>
</div>

<table class="data-table">
    <thead>
        <tr>
            <th>ID</th>
            <th>Название</th>
            <th>URL</th>
            <th>Расположение</th>
            <th>Действия</th>
        </tr>
    </thead>
    <tbody>
        <?php if (!empty($menus)): ?>
            <?php foreach ($menus as $menuItem): ?>
            <tr>
                <td><?= $menuItem['id'] ?></td>
                <td><?= TemplateEngine::e($menuItem['name']) ?></td>
                <td><?= TemplateEngine::e($menuItem['url']) ?></td>
                <td>
                    <span class="badge badge-<?= $menuItem['location'] ?>">
                        <?= $menuItem['location'] === 'main' ? 'Главное' : 'Футер' ?>
                    </span>
                </td>
                <td class="actions">
                    <a href="/admin/menus/edit/<?= $menuItem['id'] ?>" class="btn btn-sm btn-primary" title="Редактировать"><?= icon('edit') ?></a>
                    <a href="/admin/menus/delete/<?= $menuItem['id'] ?>" class="btn btn-sm btn-danger"
                       onclick="return confirm('Удалить пункт меню?')" title="Удалить">🗑️</a>
                </td>
            </tr>
            <?php endforeach; ?>
        <?php else: ?>
            <tr>
                <td colspan="5" class="text-center">Пунктов меню пока нет</td>
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
