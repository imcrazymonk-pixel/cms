<div class="stats-grid">
    <div class="glass-card stat-card anim-fade-in-up stagger-1">
        <div class="stat-icon"><?= icon('posts', 'icon-lg') ?></div>
        <div>
            <span class="stat-value"><?= $stats['posts'] ?? 0 ?></span>
            <span class="stat-label">Постов</span>
        </div>
    </div>

    <div class="glass-card stat-card anim-fade-in-up stagger-2">
        <div class="stat-icon"><?= icon('message', 'icon-lg') ?></div>
        <div>
            <span class="stat-value"><?= $stats['comments'] ?? 0 ?></span>
            <span class="stat-label">Комментариев</span>
        </div>
    </div>

    <div class="glass-card stat-card anim-fade-in-up stagger-3">
        <div class="stat-icon"><?= icon('users', 'icon-lg') ?></div>
        <div>
            <span class="stat-value"><?= $stats['users'] ?? 0 ?></span>
            <span class="stat-label">Пользователей</span>
        </div>
    </div>

    <div class="glass-card stat-card anim-fade-in-up stagger-4">
        <div class="stat-icon"><?= icon('categories', 'icon-lg') ?></div>
        <div>
            <span class="stat-value"><?= $stats['categories'] ?? 0 ?></span>
            <span class="stat-label">Категорий</span>
        </div>
    </div>
</div>

<div class="dashboard-sections">
    <div class="glass-card dashboard-section">
        <h2><?= icon('posts') ?> Последние посты</h2>
        <?php
        echo DataGrid::render([
            'columns' => [
                ['key' => 'id', 'label' => 'ID'],
                ['key' => 'title', 'label' => 'Заголовок', 'html' => function ($row) {
                    return '<a href="/admin/posts/edit/' . $row['id'] . '">' . TemplateEngine::e($row['title']) . '</a>';
                }],
                ['key' => 'status', 'label' => 'Статус', 'html' => function ($row) {
                    $labels = ['published' => 'Опубликован', 'draft' => 'Черновик', 'archived' => 'Архив'];
                    $st = $row['status'] ?? 'draft';
                    return '<span class="badge badge-' . $st . '">' . ($labels[$st] ?? $st) . '</span>';
                }],
                ['key' => 'created_at', 'label' => 'Дата', 'format' => function ($v) {
                    return format_date($v, 'd.m.Y');
                }],
                ['key' => '_actions', 'label' => 'Действия', 'html' => function ($row) {
                    $html = '<a href="/admin/posts/edit/' . $row['id'] . '" class="btn btn-sm btn-ghost" title="Редактировать">' . icon('edit') . '</a>';
                    if (!empty($row['slug'])) {
                        $html .= '<a href="/post/' . $row['slug'] . '" class="btn btn-sm btn-ghost" target="_blank" title="Просмотр">' . icon('eye') . '</a>';
                    }
                    return $html;
                }],
            ],
            'rows' => $recentPosts ?? [],
            'empty' => [
                'title' => 'Постов пока нет',
                'text' => 'Создайте первый пост в разделе «Посты»',
                'action' => '/admin/posts/create',
                'action_label' => 'Создать пост',
                'icon' => 'posts',
            ],
        ]);
        ?>
        <div class="table-footer">
            <a href="/admin/posts" class="btn btn-secondary">Все посты →</a>
        </div>
    </div>

    <div class="glass-card dashboard-section">
        <h2><?= icon('settings') ?> Быстрые действия</h2>
        <div class="quick-actions">
            <a href="/admin/posts/create" class="btn btn-primary">
                <?= icon('posts') ?> Новый пост
            </a>
            <a href="/admin/categories" class="btn btn-secondary">
                <?= icon('categories') ?> Категории
            </a>
            <a href="/admin/media" class="btn btn-secondary">
                <?= icon('media') ?> Медиафайлы
            </a>
            <a href="/admin/settings" class="btn btn-secondary">
                <?= icon('settings') ?> Настройки
            </a>
        </div>
    </div>
</div>
