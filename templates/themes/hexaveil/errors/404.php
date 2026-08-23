<?php
/**
 * Шаблон страницы 404 (тема hexaveil)
 */
?>
<section class="section" style="text-align: center; padding: 120px 24px;">
  <h1 style="font-size: 6rem; margin: 0; background: linear-gradient(135deg, #a855f7, #6366f1); -webkit-background-clip: text; background-clip: text; color: transparent;">
    404
  </h1>
  <h2>Страница не найдена</h2>
  <p style="color: var(--text-muted, #999); margin-bottom: 32px;">К сожалению, запрашиваемая страница не существует.</p>
  <a
    href="<?= TemplateEngine::url() ?>"
    class="btn btn-primary"
    style="display: inline-block; padding: 14px 28px; border-radius: 10px; background: #a855f7; color: #fff; text-decoration: none;"
  >
    Вернуться на главную
  </a>
</section>
