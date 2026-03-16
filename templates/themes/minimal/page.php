<?php
/**
 * Шаблон статической страницы
 */
?>

<article class="static-page">
    <header class="page-header">
        <h1><?= TemplateEngine::e($page['title'] ?? $title) ?></h1>
        <?php if (!empty($page['updated_at'])): ?>
        <p class="page-updated">Обновлено: <?= format_date($page['updated_at'], 'd.m.Y') ?></p>
        <?php endif; ?>
    </header>

    <?php if (!empty($page['image'])): ?>
    <div class="page-featured-image">
        <img src="<?= TemplateEngine::image($page['image']) ?>" alt="<?= TemplateEngine::e($page['title']) ?>">
    </div>
    <?php endif; ?>

    <div class="page-content">
        <?= $page['content'] ?? $content ?? '' ?>
    </div>
    
    <?php if (!empty($page['meta_description'])): ?>
    <aside class="page-meta">
        <p><strong>Описание:</strong> <?= TemplateEngine::e($page['meta_description']) ?></p>
    </aside>
    <?php endif; ?>
</article>

<?php if (!empty($showComments) && isset($comments)): ?>
<section class="comments-section">
    <h2>Комментарии</h2>
    
    <?php if (!empty($comments)): ?>
        <?php foreach ($comments as $comment): ?>
        <div class="comment">
            <div class="comment-header">
                <span class="comment-author"><?= TemplateEngine::e($comment['author_name'] ?? 'Аноним') ?></span>
                <span class="comment-date"><?= format_date($comment['created_at']) ?></span>
            </div>
            <div class="comment-content"><?= TemplateEngine::e($comment['content']) ?></div>
        </div>
        <?php endforeach; ?>
    <?php else: ?>
        <p class="no-comments">Комментариев пока нет. Будьте первыми!</p>
    <?php endif; ?>
    
    <?php if (isset($showCommentForm) && $showCommentForm): ?>
    <div class="comment-form-wrap">
        <h3>Оставить комментарий</h3>
        <form method="POST" action="" class="comment-form">
            <?= csrf_field() ?>
            <div class="form-group">
                <label for="author">Ваше имя</label>
                <input type="text" id="author" name="author" class="form-control" required>
            </div>
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" class="form-control" required>
            </div>
            <div class="form-group">
                <label for="content">Комментарий</label>
                <textarea id="content" name="content" class="form-control" rows="5" required></textarea>
            </div>
            <button type="submit" name="submit_comment" class="btn btn-primary">Отправить</button>
        </form>
    </div>
    <?php endif; ?>
</section>
<?php endif; ?>
