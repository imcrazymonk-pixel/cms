<?php
/**
 * Шаблон поста
 */
?>

<article class="single-post">
    <header class="post-header">
        <div class="post-meta-top">
            <?php if (!empty($post['category_name'])): ?>
            <a href="<?= TemplateEngine::url('category/' . $post['category']) ?>" class="post-category-badge">
                📁 <?= TemplateEngine::e($post['category_name']) ?>
            </a>
            <?php endif; ?>
        </div>
        
        <h1 class="post-title"><?= TemplateEngine::e($post['title']) ?></h1>
        
        <div class="post-meta">
            <span class="post-date">📅 <?= format_date($post['created_at'], 'd.m.Y H:i') ?></span>
            <?php if (!empty($post['author'])): ?>
            <span class="post-author">✍️ <?= TemplateEngine::e($post['author']) ?></span>
            <?php endif; ?>
            <span class="post-views">👁️ <?= $post['views'] ?? 0 ?> просмотров</span>
        </div>
    </header>

    <?php if (!empty($post['image'])): ?>
    <figure class="post-featured-image">
        <img src="<?= TemplateEngine::image($post['image']) ?>" alt="<?= TemplateEngine::e($post['title']) ?>">
        <?php if (!empty($post['image_caption'])): ?>
        <figcaption><?= TemplateEngine::e($post['image_caption']) ?></figcaption>
        <?php endif; ?>
    </figure>
    <?php endif; ?>

    <div class="post-content">
        <?= $post['content'] ?? '' ?>
    </div>

    <?php if (!empty($tags)): ?>
    <div class="post-tags">
        <span class="tags-label">🏷️ Теги:</span>
        <div class="tags-list">
            <?php foreach ($tags as $tag): ?>
            <a href="<?= TemplateEngine::url('tag/' . $tag['slug']) ?>" class="tag"><?= TemplateEngine::e($tag['name']) ?></a>
            <?php endforeach; ?>
        </div>
    </div>
    <?php endif; ?>
    
    <div class="post-share">
        <span>Поделиться:</span>
        <a href="https://vk.com/share.php?url=<?= urlencode(SITE_URL . '/post/' . ($post['slug'] ?? '')) ?>" target="_blank" class="share-link vk">ВК</a>
        <a href="https://t.me/share/url?url=<?= urlencode(SITE_URL . '/post/' . ($post['slug'] ?? '')) ?>" target="_blank" class="share-link tg">Telegram</a>
    </div>
</article>

<?php if (!empty($relatedPosts)): ?>
<section class="related-posts">
    <h2>Читайте также</h2>
    <div class="posts-grid">
        <?php foreach ($relatedPosts as $related): ?>
        <article class="post-card">
            <a href="<?= TemplateEngine::url('post/' . $related['slug']) ?>">
                <?php if (!empty($related['image'])): ?>
                <img src="<?= TemplateEngine::image($related['image']) ?>" alt="<?= TemplateEngine::e($related['title']) ?>" loading="lazy">
                <?php endif; ?>
                <h3><?= TemplateEngine::e($related['title']) ?></h3>
            </a>
        </article>
        <?php endforeach; ?>
    </div>
</section>
<?php endif; ?>

<section class="comments-section" id="comments">
    <h2>Комментарии (<?= count($comments ?? []) ?>)</h2>
    
    <?php if (!empty($comments)): ?>
    <div class="comments-list">
        <?php foreach ($comments as $comment): ?>
        <div class="comment">
            <div class="comment-avatar">
                <?= mb_strtoupper(mb_substr($comment['author_name'] ?? 'А', 0, 1)) ?>
            </div>
            <div class="comment-body">
                <div class="comment-header">
                    <span class="comment-author"><?= TemplateEngine::e($comment['author_name'] ?? 'Аноним') ?></span>
                    <span class="comment-date"><?= format_date($comment['created_at']) ?></span>
                </div>
                <div class="comment-content"><?= TemplateEngine::e($comment['content']) ?></div>
            </div>
        </div>
        <?php endforeach; ?>
    </div>
    <?php else: ?>
    <p class="no-comments">Комментариев пока нет. Будьте первыми!</p>
    <?php endif; ?>
    
    <div class="comment-form-wrap">
        <h3>Оставить комментарий</h3>
        <form method="POST" action="" class="comment-form">
            <?= csrf_field() ?>
            <div class="form-row">
                <div class="form-group">
                    <label for="author">Ваше имя *</label>
                    <input type="text" id="author" name="author" class="form-control" required>
                </div>
                <div class="form-group">
                    <label for="email">Email *</label>
                    <input type="email" id="email" name="email" class="form-control" required>
                </div>
            </div>
            <div class="form-group">
                <label for="content">Комментарий *</label>
                <textarea id="content" name="content" class="form-control" rows="5" required></textarea>
            </div>
            <button type="submit" name="submit_comment" class="btn btn-primary">Отправить комментарий</button>
        </form>
    </div>
</section>
