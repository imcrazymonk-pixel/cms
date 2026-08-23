<?php
/**
 * Шаблон статической страницы (тема hexaveil)
 */
?>
<section class="section">
  <div class="container">
    <article class="glass-card" style="padding: 40px; border-radius: 20px;">
      <h1 class="section-title" style="text-align: left;"><?= TemplateEngine::e($page['title']) ?></h1>
      <div class="page-content" style="line-height: 1.7;">
        <?= $page['content'] ?>
      </div>
    </article>
  </div>
</section>
