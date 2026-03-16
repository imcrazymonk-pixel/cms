<?php
/**
 * Шаблон категории
 */
?>

<section class="category-page">
    <header class="category-header">
        <div class="category-badge">📁 Категория</div>
        <h1><?= TemplateEngine::e($category['name'] ?? $category ?? 'Без названия') ?></h1>
        <?php if (!empty($category['description'])): ?>
        <p class="category-description"><?= TemplateEngine::e($category['description']) ?></p>
        <?php endif; ?>
        <div class="category-stats">
            <span>Публикаций: <?= count($posts ?? []) ?></span>
        </div>
    </header>

    <div class="posts-grid">
        <?php if (!empty($posts)): ?>
            <?php foreach ($posts as $post): ?>
            <article class="post-card">
                <a href="<?= TemplateEngine::url('post/' . $post['slug']) ?>" class="post-link">
                    <?php if (!empty($post['image'])): ?>
                    <div class="post-image-wrap">
                        <img src="<?= TemplateEngine::image($post['image']) ?>" alt="<?= TemplateEngine::e($post['title']) ?>" loading="lazy">
                    </div>
                    <?php endif; ?>
                    <div class="post-content">
                        <h3 class="post-title"><?= TemplateEngine::e($post['title']) ?></h3>
                        <p class="post-excerpt"><?= TemplateEngine::e(truncate(strip_tags($post['excerpt'] ?? $post['content']), 150)) ?></p>
                        <div class="post-card-meta">
                            <span class="post-date">📅 <?= format_date($post['created_at'], 'd.m.Y') ?></span>
                            <span class="post-views">👁️ <?= $post['views'] ?? 0 ?></span>
                        </div>
                    </div>
                </a>
            </article>
            <?php endforeach; ?>
        <?php else: ?>
            <div class="no-posts">
                <p>В этой категории пока нет публикаций</p>
            </div>
        <?php endif; ?>
    </div>
    
    <?php if (!empty($pagination)): ?>
    <div class="pagination">
        <?= $pagination ?>
    </div>
    <?php endif; ?>
</section>
