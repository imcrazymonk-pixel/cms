<?php
/**
 * Чистый шаблон (blank)
 * Минимальный шаблон без layout
 * Используется для специальных страниц
 */
?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $seo['title'] ?? ($page['title'] ?? $title ?? SITE_NAME) ?></title>
    <?php if (!empty($seo['description'])): ?>
    <meta name="description" content="<?= TemplateEngine::e($seo['description']) ?>">
    <?php endif; ?>
    <link rel="stylesheet" href="<?= TemplateEngine::asset('css/style.css') ?>">
</head>
<body class="blank-page-body">
    <article class="blank-page">
        <header class="blank-header">
            <h1><?= TemplateEngine::e($page['title'] ?? $title) ?></h1>
        </header>

        <div class="blank-content">
            <?= $page['content'] ?? $content ?? '' ?>
        </div>
    </article>

    <style>
    .blank-page-body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
        color: #333;
        background: #f5f5f5;
        margin: 0;
        padding: 0;
    }

    .blank-page {
        max-width: 800px;
        margin: 40px auto;
        background: white;
        padding: 40px;
        border-radius: 10px;
        box-shadow: 0 2px 20px rgba(0,0,0,0.1);
    }

    .blank-header {
        border-bottom: 2px solid #667eea;
        padding-bottom: 20px;
        margin-bottom: 30px;
    }

    .blank-header h1 {
        margin: 0;
        color: #667eea;
        font-size: 2rem;
    }

    .blank-content {
        font-size: 1rem;
        line-height: 1.8;
    }

    .blank-content h2 {
        color: #333;
        margin-top: 30px;
    }

    .blank-content h3 {
        color: #666;
        margin-top: 25px;
    }

    .blank-content img {
        max-width: 100%;
        height: auto;
        border-radius: 5px;
    }

    .blank-content a {
        color: #667eea;
        text-decoration: none;
    }

    .blank-content a:hover {
        text-decoration: underline;
    }

    .blank-content ul,
    .blank-content ol {
        padding-left: 25px;
    }

    .blank-content blockquote {
        border-left: 4px solid #667eea;
        padding-left: 20px;
        margin: 20px 0;
        font-style: italic;
        color: #666;
    }

    .blank-content pre {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        overflow-x: auto;
    }

    .blank-content code {
        background: #f8f9fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
    }
    </style>
</body>
</html>
