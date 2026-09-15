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

    // Switch/boolean — рендерим как toggle row (Remnawave-style)
    if ($type === 'switch' || $type === 'checkbox') {
        $checked = ($value === '1' || $value === 1 || $value === true) ? ' checked' : '';
        echo '<div class="form-switch">';
        echo '<div class="form-switch-body">';
        echo '<label for="' . $esc($key) . '">' . $esc($label) . '</label>';
        if (!empty($field['hint'])) {
            echo '<small class="form-hint">' . $esc($field['hint']) . '</small>';
        }
        echo '</div>';
        echo '<label class="ap-switch">';
        echo '<input type="hidden" name="' . $esc($name) . '" value="0">';
        echo '<input type="checkbox" id="' . $esc($key) . '" name="' . $esc($name) . '" value="1"' . $checked . ' class="theme-auto-save">';
        echo '<span class="ap-switch-slider"></span>';
        echo '</label>';
        echo '</div>';
        return;
    }

    echo '<div class="form-group">';
    echo '<label for="' . $esc($key) . '">' . $esc($label) . '</label>';

    if ($type === 'textarea') {
        echo '<textarea id="' . $esc($key) . '" name="' . $esc($name) . '" class="form-control" rows="' . (int)($field['rows'] ?? 3) . '">' . $esc($value) . '</textarea>';
    } elseif ($type === 'select') {
        echo '<select id="' . $esc($key) . '" name="' . $esc($name) . '" class="form-control theme-auto-save">';
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

<!-- ================= Менеджер тем (Remnawave-style) ================= -->
<div class="card form-card">
    <h3>Установленные темы</h3>

    <div class="themes-grid">
        <?php
        // Палитра градиентов для превью тем (как свотчи в Remnawave Appearance)
        $gradientPalette = [
            'hexaveil' => ['#6366f1', '#818cf8'],
            'default'  => ['#6b7280', '#9ca3af'],
            'modern'   => ['#22d3ee', '#3b82f6'],
            'minimal'  => ['#f59e0b', '#fbbf24'],
        ];
        $fallbackGradients = [
            ['#6366f1','#818cf8'], ['#22d3ee','#3b82f6'], ['#ec4899','#f472b6'],
            ['#8b5cf6','#a78bfa'], ['#f59e0b','#fbbf24'], ['#10b981','#34d399'],
            ['#ef4444','#f87171'], ['#0ea5e9','#38bdf8'], ['#f97316','#fb923c'],
        ];
        foreach ($themes as $idx => $theme):
            // Определяем градиент для превью
            $themeSlug = $theme['name'];
            if (isset($gradientPalette[$themeSlug])) {
                $g = $gradientPalette[$themeSlug];
            } else {
                $g = $fallbackGradients[$idx % count($fallbackGradients)];
            }
        ?>
        <div class="theme-card <?= $theme['active'] ? 'theme-active' : '' ?>">
            <!-- Preview band (градиент-свотч как в Remnawave) -->
            <div class="theme-preview" style="background:linear-gradient(135deg,<?= $g[0] ?>,<?= $g[1] ?>)"></div>
            <div class="theme-card-body">
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

<!-- ================= Настройки активной темы (Remnawave‑style) ================= -->
<div class="card form-card settings-theme-card">
    <div class="settings-theme-header">
        <h3>Настройки активной темы: <?= TemplateEngine::e($themeConfig['name'] ?? $themeName) ?></h3>
        <span class="settings-save-indicator" id="settings-save-indicator" style="display:none;"></span>
    </div>

    <?php if (empty($themeConfig['options'])): ?>
    <p class="form-hint">
        У этой темы нет настраиваемых полей. Чтобы они появились, добавьте файл
        <code>theme.php</code> в папку темы (см. тему hexaveil как пример).
    </p>
    <?php else: ?>
    <!-- Поиск по настройкам (Remnawave‑style) -->
    <div class="settings-search">
        <span class="settings-search-icon"><?= icon('search') ?></span>
        <input type="text" id="settings-search-input" class="form-control" placeholder="Поиск по настройкам..." autocomplete="off">
    </div>

    <form id="theme-options-form" method="POST" action="/admin/theme/update">
        <?= csrf_field() ?>

        <div class="settings-accordion">
        <?php foreach ($themeConfig['options'] as $sectionName => $fields): ?>
            <div class="settings-accordion-item">
                <button type="button" class="settings-accordion-trigger" data-accordion-trigger>
                    <span><?= TemplateEngine::e($sectionName) ?></span>
                    <span class="settings-accordion-chevron"><?= icon('chevron-down') ?></span>
                </button>
                <div class="settings-accordion-content">
                    <?php foreach ($fields as $fieldKey => $field): ?>
                    <?php __theme_field((string)$fieldKey, is_array($field) ? $field : ['label' => $fieldKey, 'type' => 'text', 'default' => ''], $themeName . '_', $settings); ?>
                    <?php endforeach; ?>
                </div>
            </div>
        <?php endforeach; ?>
        </div>

        <div class="form-actions">
            <button type="submit" class="btn btn-primary"><?= icon('save') ?> Сохранить настройки</button>
        </div>
    </form>
    <?php endif; ?>
</div>

<script>
(function() {
    /* ===== Аккордеон ===== */
    document.querySelectorAll('[data-accordion-trigger]').forEach(function(btn) {
        var content = btn.nextElementSibling;
        var chevron = btn.querySelector('.settings-accordion-chevron');
        // Первая секция открыта по умолчанию
        var isFirst = btn.closest('.settings-accordion-item') === document.querySelector('.settings-accordion-item');
        if (isFirst) {
            content.style.maxHeight = content.scrollHeight + 'px';
            content.classList.add('open');
            if (chevron) chevron.classList.add('open');
        }
        btn.addEventListener('click', function() {
            var isOpen = content.classList.contains('open');
            if (isOpen) {
                content.classList.remove('open');
                content.style.maxHeight = '0';
                if (chevron) chevron.classList.remove('open');
            } else {
                content.classList.add('open');
                content.style.maxHeight = content.scrollHeight + 'px';
                if (chevron) chevron.classList.add('open');
            }
        });
    });

    /* ===== Поиск по настройкам (Remnawave‑style) ===== */
    var searchInput = document.getElementById('settings-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            var q = this.value.toLowerCase().trim();
            var allItems = document.querySelectorAll('.settings-accordion-item');
            allItems.forEach(function(item) {
                var text = item.textContent.toLowerCase();
                var match = !q || text.indexOf(q) !== -1;
                item.style.display = match ? '' : 'none';
                // Если поиск активен — открываем все секции с совпадениями
                if (q && match) {
                    var content = item.querySelector('.settings-accordion-content');
                    var chevron = item.querySelector('.settings-accordion-chevron');
                    if (content && !content.classList.contains('open')) {
                        content.classList.add('open');
                        content.style.maxHeight = content.scrollHeight + 'px';
                        if (chevron) chevron.classList.add('open');
                    }
                }
            });
        });
    }

    /* ===== Auto‑save для select/switch (как в Remnawave) ===== */
    var indicator = document.getElementById('settings-save-indicator');
    function showStatus(type) {
        if (!indicator) return;
        if (type === 'saving') {
            indicator.innerHTML = '<?= icon('refresh-cw') ?>';
            indicator.className = 'settings-save-indicator';
            indicator.style.display = 'inline-flex';
        } else if (type === 'success') {
            indicator.innerHTML = '<?= icon('check') ?>';
            indicator.className = 'settings-save-indicator text-success';
            indicator.style.display = 'inline-flex';
            setTimeout(function() { indicator.style.display = 'none'; }, 2000);
        } else if (type === 'error') {
            indicator.innerHTML = '<?= icon('alert-triangle') ?>';
            indicator.className = 'settings-save-indicator text-error';
            indicator.style.display = 'inline-flex';
            setTimeout(function() { indicator.style.display = 'none'; }, 3000);
        }
    }

    document.querySelectorAll('.theme-auto-save').forEach(function(el) {
        el.addEventListener('change', function() {
            var form = document.getElementById('theme-options-form');
            if (!form) return;
            var formData = new FormData(form);
            showStatus('saving');
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: { 'Accept': 'application/json' }
            }).then(function(r) {
                if (r.ok || r.redirected) showStatus('success');
                else showStatus('error');
            }).catch(function() {
                showStatus('error');
            });
        });
    });
})();
</script>

