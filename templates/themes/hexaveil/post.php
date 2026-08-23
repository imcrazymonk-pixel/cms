<?php
/**
 * Шаблон страницы поста (тема hexaveil)
 */
?>
<section class="section">
  <div class="container">
    <article class="glass-card" style="padding: 40px; border-radius: 20px;">
      <h1 class="section-title" style="text-align: left;"><?= TemplateEngine::e($post['title']) ?></h1>

      <div class="post-meta" style="color: var(--text-muted, #999); margin-bottom: 24px;">
        <?php if (!empty($post['author'])): ?><span>Автор: <?= TemplateEngine::e($post['author']) ?></span><?php endif; ?>
        <?php if (!empty($post['category_name'])): ?><span> • <?= TemplateEngine::e($post['category_name']) ?></span><?php endif; ?>
        <?php if (!empty($post['created_at'])): ?><span> • <?= format_date($post['created_at'], 'd.m.Y') ?></span><?php endif; ?>
        <span> • 👁 <?= $post['views'] ?? 0 ?></span>
      </div>

      <?php if (!empty($post['image'])): ?>
      <img
        src="<?= TemplateEngine::image($post['image']) ?>"
        alt="<?= TemplateEngine::e($post['title']) ?>"
        style="max-width: 100%; border-radius: 12px; margin-bottom: 24px;"
      >
      <?php endif; ?>

      <div class="post-content" style="line-height: 1.7;">
        <?= $post['content'] ?>
      </div>

      <?php if (!empty($tags)): ?>
      <div style="margin-top: 32px; display: flex; flex-wrap: wrap; gap: 8px;">
        <?php foreach ($tags as $tag): ?>
        <span class="tag" style="padding: 6px 14px; border-radius: 999px; background: rgba(168,85,247,0.15); color: #c084fc; font-size: 14px;">
          #<?= TemplateEngine::e($tag['name']) ?>
        </span>
        <?php endforeach; ?>
      </div>
      <?php endif; ?>
    </article>

    <?php if (!empty($comments)): ?>
    <div class="glass-card" style="padding: 32px; border-radius: 20px; margin-top: 24px;">
      <h3 style="margin: 0 0 20px;">Комментарии (<?= count($comments) ?>)</h3>
      <?php foreach ($comments as $comment): ?>
      <div style="padding: 16px 0; border-bottom: 1px solid rgba(255,255,255,0.08);">
        <strong><?= TemplateEngine::e($comment['author_name']) ?></strong>
        <span style="color: var(--text-muted, #999); font-size: 14px;"> • <?= format_date($comment['created_at'], 'd.m.Y') ?></span>
        <p style="margin: 8px 0 0;"><?= TemplateEngine::e($comment['content']) ?></p>
      </div>
      <?php endforeach; ?>
    </div>
    <?php endif; ?>
  </div>
</section>
