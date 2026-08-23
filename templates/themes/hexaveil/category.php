<?php
/**
 * Шаблон категории (тема hexaveil)
 */
?>
<section class="section">
  <div class="container">
    <h1 class="section-title">Категория: <?= TemplateEngine::e($category['name']) ?></h1>

    <?php if (!empty($category['description'])): ?>
    <p style="color: var(--text-muted, #999); max-width: 720px;"><?= TemplateEngine::e($category['description']) ?></p>
    <?php endif; ?>

    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; margin-top: 32px;">
      <?php if (!empty($posts)): ?>
        <?php foreach ($posts as $post): ?>
        <a
          href="<?= TemplateEngine::url('post/' . $post['slug']) ?>"
          class="glass-card"
          style="text-decoration: none; padding: 24px; border-radius: 16px; color: inherit; display: block;"
        >
          <h3 style="margin: 0 0 8px;"><?= TemplateEngine::e($post['title']) ?></h3>
          <p style="color: var(--text-muted, #999); margin: 0; font-size: 14px;">
            <?= TemplateEngine::e(truncate(strip_tags($post['excerpt'] ?? $post['content']), 150)) ?>
          </p>
        </a>
        <?php endforeach; ?>
      <?php else: ?>
      <p style="color: var(--text-muted, #999);">В этой категории пока нет постов.</p>
      <?php endif; ?>
    </div>
  </div>
</section>
