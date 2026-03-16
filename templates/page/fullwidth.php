<?php
/**
 * Шаблон страницы на всю ширину
 * Без боковых отступов, контент занимает всю ширину контейнера
 */
?>

<article class="static-page fullwidth-page">
    <header class="page-header fullwidth-header">
        <h1><?= TemplateEngine::e($page['title'] ?? $title) ?></h1>
        <?php if (!empty($page['updated_at'])): ?>
        <p class="page-updated">Обновлено: <?= format_date($page['updated_at'], 'd.m.Y') ?></p>
        <?php endif; ?>
    </header>

    <?php if (!empty($page['image'])): ?>
    <div class="page-featured-image fullwidth-image">
        <img src="<?= TemplateEngine::image($page['image']) ?>" alt="<?= TemplateEngine::e($page['title']) ?>">
    </div>
    <?php endif; ?>

    <div class="page-content fullwidth-content">
        <?= $page['content'] ?? $content ?? '' ?>
    </div>

    <?php if (!empty($page['meta_description'])): ?>
    <aside class="page-meta">
        <p><strong>Описание:</strong> <?= TemplateEngine::e($page['meta_description']) ?></p>
    </aside>
    <?php endif; ?>
</article>

<style>
.fullwidth-page {
    max-width: 100%;
    margin: 0;
    padding: 0;
}

.fullwidth-header {
    padding: 40px 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    text-align: center;
}

.fullwidth-header h1 {
    font-size: 3rem;
    margin-bottom: 10px;
}

.fullwidth-header .page-updated {
    opacity: 0.9;
}

.fullwidth-image img {
    width: 100%;
    height: 400px;
    object-fit: cover;
}

.fullwidth-content {
    padding: 60px 20px;
    max-width: 1200px;
    margin: 0 auto;
    font-size: 1.1rem;
    line-height: 1.8;
}

.fullwidth-content img {
    max-width: 100%;
    height: auto;
}
</style>
