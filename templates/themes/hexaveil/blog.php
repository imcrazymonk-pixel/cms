<?php
/**
 * Шаблон ленты блога (тема HexaVeil).
 * Стилистика: glass-карточки, акцент purple, тёмный фон.
 * Переменные: $posts, $categories, $currentCategory
 */
?>
<section class="section">
  <div class="container">
    <h1 class="section-title">Блог</h1>

    <?php if (!empty($categories)): ?>
    <div class="blog-categories">
      <a href="<?= TemplateEngine::url('blog') ?>" class="blog-cat-link<?= empty($currentCategory) ? ' active' : '' ?>">Все</a>
      <?php foreach ($categories as $cat): ?>
      <a
        href="<?= TemplateEngine::url('category/' . TemplateEngine::e($cat['slug'])) ?>"
        class="blog-cat-link<?= ($currentCategory ?? '') === $cat['slug'] ? ' active' : '' ?>"
      ><?= TemplateEngine::e($cat['name']) ?></a>
      <?php endforeach; ?>
    </div>
    <?php endif; ?>

    <?php if (!empty($posts)): ?>
    <div class="blog-grid">
      <?php foreach ($posts as $post): ?>
      <article class="blog-card glass-card">
        <a href="<?= TemplateEngine::url('post/' . $post['slug']) ?>" class="blog-card-link">
          <?php if (!empty($post['image'])): ?>
          <div class="blog-card-img-wrap">
            <img
              src="<?= TemplateEngine::image($post['image']) ?>"
              alt="<?= TemplateEngine::e($post['title']) ?>"
              loading="lazy"
            />
          </div>
          <?php endif; ?>
          <div class="blog-card-body">
            <h3 class="blog-card-title"><?= TemplateEngine::e($post['title']) ?></h3>
            <p class="blog-card-excerpt">
              <?= TemplateEngine::e(truncate(strip_tags($post['excerpt'] ?? $post['content']), 160)) ?>
            </p>
            <div class="blog-card-meta">
              <?php if (!empty($post['category_name'])): ?>
              <span class="blog-card-cat"><?= TemplateEngine::e($post['category_name']) ?></span>
              <?php endif; ?>
              <span class="blog-card-date"><?= format_date($post['created_at'], 'd.m.Y') ?></span>
              <span class="blog-card-views"><?= $post['views'] ?? 0 ?> просмотров</span>
            </div>
          </div>
        </a>
      </article>
      <?php endforeach; ?>
    </div>
    <?php else: ?>
    <p class="blog-empty">Публикаций пока нет. Загляните позже!</p>
    <?php endif; ?>
  </div>
</section>