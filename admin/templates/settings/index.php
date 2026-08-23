<div class="page-header-actions">
    <h2>Настройки</h2>
    <button type="button" class="btn btn-primary" onclick="document.getElementById('settings-form').submit()">💾 Сохранить</button>
</div>

<?php if (Request::get('success') === 'updated'): ?>
<div class="alert alert-success">Настройки сохранены</div>
<?php endif; ?>

<form id="settings-form" method="POST" action="/admin/settings/update">
    <?= csrf_field() ?>

    <div class="settings-section">
        <h3>📌 Основные настройки</h3>

        <div class="form-group">
            <label for="site_name">Название сайта</label>
            <input type="text" id="site_name" name="settings[site_name]" class="form-control"
                   value="<?= TemplateEngine::e($settings['site_name'] ?? '') ?>">
        </div>

        <div class="form-group">
            <label for="site_url">URL сайта</label>
            <input type="url" id="site_url" name="settings[site_url]" class="form-control"
                   value="<?= TemplateEngine::e($settings['site_url'] ?? '') ?>">
        </div>

        <div class="form-group">
            <label for="admin_email">Email администратора</label>
            <input type="email" id="admin_email" name="settings[admin_email]" class="form-control"
                   value="<?= TemplateEngine::e($settings['admin_email'] ?? '') ?>">
        </div>

        <div class="form-group">
            <label for="posts_per_page">Постов на страницу</label>
            <input type="number" id="posts_per_page" name="settings[posts_per_page]" class="form-control"
                   value="<?= (int)($settings['posts_per_page'] ?? 10) ?>" min="1" max="100">
        </div>
    </div>

    <div class="settings-section">
        <h3>🎨 Внешний вид</h3>

        <div class="form-group">
            <label for="active_theme">Тема оформления</label>
            <select id="active_theme" name="settings[active_theme]" class="form-control">
                <?php
                // Список тем формируется автоматически из папки templates/themes
                $themesDir = TEMPLATES_PATH . '/themes';
                $themes = [];
                if (is_dir($themesDir)) {
                    $themes = array_values(array_filter(scandir($themesDir), function ($d) use ($themesDir) {
                        return $d !== '.' && $d !== '..' && is_dir($themesDir . '/' . $d);
                    }));
                }
                $themeLabels = [
                    'default'  => '📄 Классическая (Default)',
                    'modern'   => '🚀 Современная (Modern)',
                    'minimal'  => '📝 Минимализм (Minimal)',
                    'hexaveil' => '🌐 HexaVeil (лендинг)',
                ];
                foreach ($themes as $themeName):
                    $themeLabel = $themeLabels[$themeName] ?? $themeName;
                ?>
                <option value="<?= TemplateEngine::e($themeName) ?>" <?= (($settings['active_theme'] ?? '') === $themeName) ? 'selected' : '' ?>><?= TemplateEngine::e($themeLabel) ?></option>
                <?php endforeach; ?>
            </select>
            <small class="form-hint">Выберите тему для всего сайта</small>
        </div>
    </div>

    <div class="settings-section">
        <h3>🔧 Дополнительные настройки</h3>

        <div class="form-group">
            <label for="meta_description">Описание сайта (Meta Description)</label>
            <textarea id="meta_description" name="settings[meta_description]" class="form-control" rows="3"><?= TemplateEngine::e($settings['meta_description'] ?? '') ?></textarea>
        </div>

        <div class="form-group">
            <label for="meta_keywords">Ключевые слова (Meta Keywords)</label>
            <input type="text" id="meta_keywords" name="settings[meta_keywords]" class="form-control"
                   value="<?= TemplateEngine::e($settings['meta_keywords'] ?? '') ?>">
        </div>
    </div>
</form>

<style>
.settings-section {
    background: var(--gray-100);
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
}
.settings-section h3 {
    margin-top: 0;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 2px solid var(--gray-300);
}
</style>
