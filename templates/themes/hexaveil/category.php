<?php
/**
 * Шаблон категории (тема hexaveil)
 */
?>
<section class="section">
  <div class="container">
    <h1 class="section-title">Категория: <?= TemplateEngine::e($category['name']) ?></h1>

    <?php if (!empty($category['description'])): ?>
    <p style="color: var(--text-muted, #999); max-width: 720px; text-align: center; margin: -1.5rem auto 2rem;"><?= TemplateEngine::e($category['description']) ?></p>
    <?php endif; ?>

    <?php if (!empty($categories)): ?>
    <div class="blog-categories">
      <a href="<?= TemplateEngine::url('blog') ?>" class="blog-cat-link">Все записи</a>
      <?php foreach ($categories as $cat): ?>
      <a
        href="<?= TemplateEngine::url('category/' . TemplateEngine::e($cat['slug'])) ?>"
        class="blog-cat-link<?= ($currentCategory ?? '') === $cat['slug'] ? ' active' : '' ?>"
      ><?= TemplateEngine::e($cat['name']) ?></a>
      <?php endforeach; ?>
    </div>
    <?php endif; ?>

    <div class="blog-grid">
      <?php if (!empty($posts)): ?>
        <?php foreach ($posts as $post): ?>
        <article class="blog-card glass-card">
          <a href="<?= TemplateEngine::url('post/' . $post['slug']) ?>" class="blog-card-link">
            <?php if (!empty($post['image'])): ?>
            <div class="blog-card-img-wrap">
              <img src="<?= TemplateEngine::image($post['image']) ?>" alt="<?= TemplateEngine::e($post['title']) ?>" loading="lazy" />
            </div>
            <?php endif; ?>
            <div class="blog-card-body">
              <h3 class="blog-card-title"><?= TemplateEngine::e($post['title']) ?></h3>
              <p class="blog-card-excerpt"><?= TemplateEngine::e(truncate(strip_tags($post['excerpt'] ?? $post['content']), 150)) ?></p>
              <div class="blog-card-meta">
                <span class="blog-card-date"><?= format_date($post['created_at'], 'd.m.Y') ?></span>
                <span class="blog-card-views"><?= $post['views'] ?? 0 ?> просмотров</span>
              </div>
            </div>
          </a>
        </article>
        <?php endforeach; ?>
      <?php else: ?>
      <p class="blog-empty">В этой категории пока нет постов.</p>
      <?php endif; ?>
    </div>
  </div>
</section>
