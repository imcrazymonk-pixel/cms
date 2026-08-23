<div class="page-header-actions">
    <h2>Медиафайлы</h2>
    <button type="button" class="btn btn-primary" onclick="document.getElementById('upload-input').click()"><?= icon('add') ?> Загрузить</button>
    <input type="file" id="upload-input" style="display: none;" accept="image/*" onchange="uploadFile(this)">
</div>

<div id="upload-progress" class="alert alert-info" style="display: none;">Загрузка...</div>

<?php if (!empty($files)): ?>
<div class="media-grid">
    <?php foreach ($files as $file): ?>
    <div class="media-item" data-path="<?= TemplateEngine::e($file['path']) ?>">
        <img src="<?= $file['url'] ?>" alt="<?= TemplateEngine::e($file['name']) ?>" loading="lazy">
        <div class="media-info">
            <span class="media-name"><?= TemplateEngine::e($file['name']) ?></span>
            <span class="media-size"><?= round($file['size'] / 1024, 1) ?> KB</span>
        </div>
        <button type="button" class="btn btn-sm btn-danger" onclick="deleteFile('<?= TemplateEngine::e($file['path']) ?>')"><?= icon('delete') ?></button>
    </div>
    <?php endforeach; ?>
</div>
<?php else: ?>
<div class="empty-state">
    <div class="empty-icon"><?= icon('media') ?></div>
    <h3>Медиафайлов пока нет</h3>
    <p>Загрузите первое изображение, чтобы использовать его в контенте</p>
    <button class="btn btn-primary" onclick="document.getElementById('upload-form').style.display='block'"><?= icon('add') ?> Загрузить файл</button>
</div>
<?php endif; ?>

<style>
.media-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 20px;
    margin-top: 20px;
}
.media-item {
    position: relative;
    border: 1px solid var(--gray-200);
    border-radius: 8px;
    overflow: hidden;
    transition: box-shadow 0.2s;
}
.media-item:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.media-item img {
    width: 100%;
    height: 150px;
    object-fit: cover;
}
.media-info {
    padding: 10px;
    background: var(--gray-100);
}
.media-name {
    display: block;
    font-size: 13px;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.media-size {
    font-size: 12px;
    color: var(--gray-600);
}
.media-item .btn {
    position: absolute;
    top: 10px;
    right: 10px;
    opacity: 0;
    transition: opacity 0.2s;
}
.media-item:hover .btn {
    opacity: 1;
}
</style>

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
