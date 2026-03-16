<?php
/**
 * Шаблон главной страницы
 */
?>

<section class="hero">
    <div class="hero-content">
        <h1><?= TemplateEngine::e($heroTitle ?? 'Добро пожаловать на ' . SITE_NAME) ?></h1>
        <p class="hero-subtitle"><?= TemplateEngine::e($heroSubtitle ?? 'Наш блог о самом интересном') ?></p>
    </div>
</section>

<section class="posts-section">
    <div class="section-header">
        <h2>Последние публикации</h2>
        <?php if (!empty($categories)): ?>
        <div class="category-filter">
            <a href="<?= TemplateEngine::url() ?>" class="<?= empty($currentCategory) ? 'active' : '' ?>">Все</a>
            <?php foreach ($categories as $cat): ?>
            <a href="<?= TemplateEngine::url('category/' . $cat['slug']) ?>" 
               class="<?= ($currentCategory ?? '') === $cat['slug'] ? 'active' : '' ?>">
                <?= TemplateEngine::e($cat['name']) ?>
            </a>
            <?php endforeach; ?>
        </div>
        <?php endif; ?>
    </div>
    
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
                            <?php if (!empty($post['category_name'])): ?>
                            <span class="post-category">📁 <?= TemplateEngine::e($post['category_name']) ?></span>
                            <?php endif; ?>
                            <span class="post-views">👁️ <?= $post['views'] ?? 0 ?></span>
                        </div>
                    </div>
                </a>
            </article>
            <?php endforeach; ?>
        <?php else: ?>
            <div class="no-posts">
                <p>Публикаций пока нет. Загляните позже!</p>
            </div>
        <?php endif; ?>
    </div>
    
    <?php if (!empty($pagination)): ?>
    <div class="pagination">
        <?= $pagination ?>
    </div>
    <?php endif; ?>
</section>
