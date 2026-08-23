<div class="stats-grid">
    <div class="stat-card stat-card-posts">
        <div class="stat-icon"><?= icon('posts', 'icon-lg') ?></div>
        <div class="stat-body">
            <span class="stat-value"><?= $stats['posts'] ?? 0 ?></span>
            <span class="stat-label">Постов</span>
        </div>
    </div>

    <div class="stat-card stat-card-comments">
        <div class="stat-icon"><?= icon('message', 'icon-lg') ?></div>
        <div class="stat-body">
            <span class="stat-value"><?= $stats['comments'] ?? 0 ?></span>
            <span class="stat-label">Комментариев</span>
        </div>
    </div>

    <div class="stat-card stat-card-users">
        <div class="stat-icon"><?= icon('users', 'icon-lg') ?></div>
        <div class="stat-body">
            <span class="stat-value"><?= $stats['users'] ?? 0 ?></span>
            <span class="stat-label">Пользователей</span>
        </div>
    </div>

    <div class="stat-card stat-card-categories">
        <div class="stat-icon"><?= icon('categories', 'icon-lg') ?></div>
        <div class="stat-body">
            <span class="stat-value"><?= $stats['categories'] ?? 0 ?></span>
            <span class="stat-label">Категорий</span>
        </div>
    </div>
</div>

<div class="dashboard-sections">
    <div class="dashboard-section">
        <h2><?= icon('posts') ?> Последние посты</h2>
        <table class="data-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Заголовок</th>
                    <th>Статус</th>
                    <th>Дата</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                <?php if (!empty($recentPosts)): ?>
                    <?php foreach ($recentPosts as $post): ?>
                    <tr>
                        <td><?= $post['id'] ?></td>
                        <td>
                            <a href="/admin/posts/edit/<?= $post['id'] ?>">
                                <?= TemplateEngine::e($post['title']) ?>
                            </a>
                        </td>
                        <td>
                            <span class="badge badge-<?= $post['status'] ?>">
                                <?= $post['status'] === 'published' ? 'Опубликован' : ($post['status'] === 'draft' ? 'Черновик' : 'Архив') ?>
                            </span>
                        </td>
                        <td><?= format_date($post['created_at'], 'd.m.Y') ?></td>
                        <td class="actions">
                            <a href="/admin/posts/edit/<?= $post['id'] ?>" class="btn btn-sm btn-primary" title="Редактировать"><?= icon('edit') ?></a>
                            <?php if (!empty($post['slug'])): ?>
                            <a href="/post/<?= $post['slug'] ?>" class="btn btn-sm btn-info" target="_blank" title="Просмотр"><?= icon('eye') ?></a>
                            <?php endif; ?>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                <?php else: ?>
                    <tr>
                        <td colspan="5" class="text-center">
                            <div class="empty-state">
                                <div class="empty-icon"><?= icon('posts') ?></div>
                                <h3>Постов пока нет</h3>
                                <p>Создайте первый пост в разделе &laquo;Посты&raquo;</p>
                                <a href="/admin/posts/create" class="btn btn-primary"><?= icon('add') ?> Создать пост</a>
                            </div>
                        </td>
                    </tr>
                <?php endif; ?>
            </tbody>
        </table>
        <div class="table-footer">
            <a href="/admin/posts" class="btn btn-secondary">Все посты →</a>
        </div>
    </div>
    
    <div class="dashboard-section">
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
