<?php
/**
 * Страница «Темы»: менеджер тем + настройки активной темы.
 * Доступны переменные: $themes, $themeName, $themeConfig, $settings.
 */

// Хелпер для рендера одного поля настроек темы
function __theme_field(string $key, array $field, string $prefix, array $settings): void
{
    $esc = function ($v) { return TemplateEngine::e((string)$v); };
    $type = $field['type'] ?? 'text';
    $name = 'settings[' . $key . ']';
    $value = $settings[$prefix . $key] ?? ($field['default'] ?? '');
    $label = $field['label'] ?? $key;

    echo '<div class="form-group">';
    echo '<label for="' . $esc($key) . '">' . $esc($label) . '</label>';

    if ($type === 'textarea') {
        echo '<textarea id="' . $esc($key) . '" name="' . $esc($name) . '" class="form-control" rows="' . (int)($field['rows'] ?? 3) . '">' . $esc($value) . '</textarea>';
    } elseif ($type === 'select') {
        echo '<select id="' . $esc($key) . '" name="' . $esc($name) . '" class="form-control">';
        foreach (($field['options'] ?? []) as $optValue => $optLabel) {
            $selected = ((string)$value === (string)$optValue) ? ' selected' : '';
            echo '<option value="' . $esc($optValue) . '"' . $selected . '>' . $esc($optLabel) . '</option>';
        }
        echo '</select>';
    } else {
        $inputType = in_array($type, ['text', 'url', 'number', 'email', 'color'], true) ? $type : 'text';
        echo '<input type="' . $esc($inputType) . '" id="' . $esc($key) . '" name="' . $esc($name) . '" class="form-control" value="' . $esc($value) . '">';
    }

    if (!empty($field['hint'])) {
        echo '<small class="form-hint">' . $esc($field['hint']) . '</small>';
    }
    echo '</div>';
}
?>

<?php if (Request::get('success') === 'updated'): ?>
<div class="alert alert-success">Настройки темы сохранены</div>
<?php elseif (Request::get('success') === 'activated'): ?>
<div class="alert alert-success">Тема активирована</div>
<?php elseif (Request::get('success') === 'uploaded'): ?>
<div class="alert alert-success">Тема загружена</div>
<?php elseif (Request::get('error') === 'badtheme'): ?>
<div class="alert alert-error">Не удалось активировать тему</div>
<?php elseif (Request::get('error') === 'upload' || Request::get('error') === 'zip' || Request::get('error') === 'emptyzip'): ?>
<div class="alert alert-error">Не удалось загрузить тему из архива</div>
<?php elseif (Request::get('error') === 'nozip'): ?>
<div class="alert alert-error">На сервере недоступно расширение ZipArchive</div>
<?php endif; ?>

<!-- ================= Менеджер тем ================= -->
<div class="card form-card">
    <h3>Установленные темы</h3>

    <div class="themes-grid">
        <?php foreach ($themes as $theme): ?>
        <div class="theme-card <?= $theme['active'] ? 'theme-active' : '' ?>">
            <div class="theme-card-header">
                <strong><?= TemplateEngine::e($theme['label']) ?></strong>
                <?php if ($theme['active']): ?>
                <span class="badge badge-success">Активна</span>
                <?php endif; ?>
            </div>
            <div class="theme-card-name">slug: <code><?= TemplateEngine::e($theme['name']) ?></code></div>
            <p class="theme-card-desc"><?= TemplateEngine::e($theme['description']) ?></p>
            <?php if (!$theme['active']): ?>
            <form method="POST" action="/admin/theme/activate">
                <?= csrf_field() ?>
                <input type="hidden" name="theme" value="<?= TemplateEngine::e($theme['name']) ?>">
                <button type="submit" class="btn btn-primary btn-sm">Активировать</button>
            </form>
            <?php endif; ?>
        </div>
        <?php endforeach; ?>
    </div>
</div>

<!-- ================= Загрузка темы ================= -->
<div class="card form-card">
    <h3>Установить тему из .zip</h3>
    <form method="POST" action="/admin/theme/upload" enctype="multipart/form-data">
        <?= csrf_field() ?>
        <div class="form-group">
            <label for="theme_zip">Архив темы (.zip)</label>
            <input type="file" id="theme_zip" name="theme_zip" class="form-control" accept=".zip,application/zip">
            <small class="form-hint">
                Структура архива: файлы темы (layouts/, index.php, theme.php…) и необязательно папка
                <code>public/</code> со статикой. Распакуется в <code>templates/themes/</code> и <code>public/</code>.
            </small>
        </div>
        <button type="submit" class="btn btn-primary"><?= icon('add') ?> Загрузить и установить</button>
    </form>
</div>

<!-- ================= Настройки активной темы ================= -->
<div class="card form-card">
    <h3>Настройки активной темы: <?= TemplateEngine::e($themeConfig['name'] ?? $themeName) ?></h3>

    <?php if (empty($themeConfig['options'])): ?>
    <p class="form-hint">
        У этой темы нет настраиваемых полей. Чтобы они появились, добавьте файл
        <code>theme.php</code> в папку темы (см. тему hexaveil как пример).
    </p>
    <?php else: ?>
    <form id="theme-options-form" method="POST" action="/admin/theme/update">
        <?= csrf_field() ?>
        <?php foreach ($themeConfig['options'] as $sectionName => $fields): ?>
        <h4 style="margin: 20px 0 10px;">
            <?= TemplateEngine::e($sectionName) ?>
        </h4>
        <?php foreach ($fields as $fieldKey => $field): ?>
        <?php __theme_field((string)$fieldKey, is_array($field) ? $field : ['label' => $fieldKey, 'type' => 'text', 'default' => ''], $themeName . '_', $settings); ?>
        <?php endforeach; ?>
        <?php endforeach; ?>

        <div class="form-actions">
            <button type="submit" class="btn btn-primary"><?= icon('save') ?> Сохранить настройки</button>
        </div>
    </form>
    <?php endif; ?>
</div>

