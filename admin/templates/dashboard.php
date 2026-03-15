<div class="dashboard-stats">
    <div class="stat-card">
        <div class="stat-icon">📝</div>
        <div class="stat-info">
            <span class="stat-value"><?= $stats['posts'] ?? 0 ?></span>
            <span class="stat-label">Постов</span>
        </div>
    </div>
    
    <div class="stat-card">
        <div class="stat-icon">💬</div>
        <div class="stat-info">
            <span class="stat-value"><?= $stats['comments'] ?? 0 ?></span>
            <span class="stat-label">Комментариев</span>
        </div>
    </div>
    
    <div class="stat-card">
        <div class="stat-icon">👥</div>
        <div class="stat-info">
            <span class="stat-value"><?= $stats['users'] ?? 0 ?></span>
            <span class="stat-label">Пользователей</span>
        </div>
    </div>
    
    <div class="stat-card">
        <div class="stat-icon">📁</div>
        <div class="stat-info">
            <span class="stat-value"><?= $stats['categories'] ?? 0 ?></span>
            <span class="stat-label">Категорий</span>
        </div>
    </div>
</div>

<div class="dashboard-sections">
    <div class="dashboard-section">
        <h2>📋 Последние посты</h2>
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
                            <a href="/admin/posts/edit/<?= $post['id'] ?>" class="btn btn-sm btn-primary" title="Редактировать">✏️</a>
                            <?php if (!empty($post['slug'])): ?>
                            <a href="/post/<?= $post['slug'] ?>" class="btn btn-sm btn-info" target="_blank" title="Просмотр">👁️</a>
                            <?php endif; ?>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                <?php else: ?>
                    <tr>
                        <td colspan="5" class="text-center">Постов пока нет</td>
                    </tr>
                <?php endif; ?>
            </tbody>
        </table>
        <div class="table-footer">
            <a href="/admin/posts" class="btn btn-secondary">Все посты →</a>
        </div>
    </div>
    
    <div class="dashboard-section">
        <h2>⚡ Быстрые действия</h2>
        <div class="quick-actions">
            <a href="/admin/posts/create" class="btn btn-primary">
                <span>📝</span> Новый пост
            </a>
            <a href="/admin/categories" class="btn btn-secondary">
                <span>📁</span> Категории
            </a>
            <a href="/admin/media" class="btn btn-secondary">
                <span>🖼️</span> Медиафайлы
            </a>
            <a href="/admin/settings" class="btn btn-secondary">
                <span>⚙️</span> Настройки
            </a>
        </div>
    </div>
</div>
