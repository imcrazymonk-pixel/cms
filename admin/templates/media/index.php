<div class="dg-toolbar">
    <button type="button" class="btn btn-primary" onclick="document.getElementById('upload-input').click()"><?= icon('add') ?> Загрузить</button>
    <input type="file" id="upload-input" style="display: none;" accept="image/*" onchange="uploadFile(this)">
</div>

<div id="upload-progress" class="alert alert-info" style="display: none;">Загрузка...</div>

<?php
echo DataGrid::render([
    'columns' => [
        ['key' => 'url', 'label' => 'Превью', 'html' => function ($row) {
            return '<img src="' . $row['url'] . '" alt="' . TemplateEngine::e($row['name']) . '" loading="lazy" style="width:48px;height:48px;object-fit:cover;border-radius:8px;display:block;">';
        }],
        ['key' => 'name', 'label' => 'Имя файла', 'html' => function ($row) {
            return '<span title="' . TemplateEngine::e($row['path']) . '">' . TemplateEngine::e($row['name']) . '</span>';
        }],
        ['key' => 'size', 'label' => 'Размер', 'format' => function ($v) {
            return round((int)$v / 1024, 1) . ' KB';
        }],
        ['key' => 'modified', 'label' => 'Изменён', 'format' => function ($v) {
            // modified приходит как unix-таймстамп (filemtime), format_date() рассчитан на строки
            return is_numeric($v) ? date('d.m.Y H:i', (int)$v) : format_date($v, 'd.m.Y H:i');
        }],
        ['key' => '_actions', 'label' => 'Действия', 'html' => function ($row) {
            return '<button type="button" class="btn btn-sm btn-danger" title="Удалить" onclick="deleteFile(\'' . TemplateEngine::e($row['path']) . '\')">' . icon('delete') . '</button>';
        }],
    ],
    'rows' => $files ?? [],
    'empty' => [
        'title' => 'Медиафайлов пока нет',
        'text' => 'Загрузите первое изображение, чтобы использовать его в контенте',
        'icon' => 'media',
    ],
]);
?>

<script>
async function uploadFile(input) {
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('image', file);

    const progress = document.getElementById('upload-progress');
    progress.style.display = 'block';

    try {
        const response = await fetch('/admin/media/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success || result.location) {
            location.reload();
        } else {
            alert('Ошибка загрузки: ' + (result.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        alert('Ошибка загрузки: ' + error.message);
    } finally {
        progress.style.display = 'none';
        input.value = '';
    }
}

async function deleteFile(path) {
    if (!confirm('Удалить файл?')) return;

    try {
        const formData = new FormData();
        formData.append('path', path);

        const response = await fetch('/admin/media/delete', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            location.reload();
        } else {
            alert('Ошибка удаления: ' + (result.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        alert('Ошибка удаления: ' + error.message);
    }
}
</script>
