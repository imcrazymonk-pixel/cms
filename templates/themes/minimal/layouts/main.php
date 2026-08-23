<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- SEO Meta Tags -->
    <title><?= $seo['title'] ?? ($title ?? SITE_NAME) ?></title>
    <?php if (!empty($seo['description'])): ?>
    <meta name="description" content="<?= TemplateEngine::e($seo['description']) ?>">
    <?php endif; ?>

    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

    <!-- Styles -->
    <link rel="stylesheet" href="<?= TemplateEngine::asset('css/style.css') ?>">
    <?php if (!empty($extraCss)): ?>
    <?php foreach ($extraCss as $css): ?>
    <link rel="stylesheet" href="<?= $css ?>">
    <?php endforeach; ?>
    <?php endif; ?>
</head>
<body class="<?= $bodyClass ?? '' ?> minimal-theme">
    <!-- Простой header -->
    <header class="minimal-header">
        <div class="minimal-container">
            <a href="<?= TemplateEngine::url() ?>" class="minimal-logo">
                <?= $siteLogo ?? SITE_NAME ?>
            </a>

            <nav class="minimal-navigation">
                <ul class="minimal-nav-menu">
                    <?php if (!empty($menuItems)): ?>
                        <?php foreach ($menuItems as $item): ?>
                        <li>
                            <a href="<?= TemplateEngine::e($item['url']) ?>"
                               class="<?= !empty($item['active']) ? 'active' : '' ?>">
                                <?= TemplateEngine::e($item['label']) ?>
                            </a>
                        </li>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </ul>
            </nav>
        </div>
    </header>

    <!-- Основной контент -->
    <main class="minimal-main">
        <div class="minimal-container">
            <?= $content ?? '' ?>
        </div>
    </main>

    <!-- Простой footer -->
    <footer class="minimal-footer">
        <div class="minimal-container">
            <p>&copy; <?= date('Y') ?> <?= SITE_NAME ?></p>
            <?php if (!empty($footerMenu)): ?>
            <nav class="minimal-footer-nav">
                <?php foreach ($footerMenu as $item): ?>
                <a href="<?= TemplateEngine::e($item['url']) ?>"><?= TemplateEngine::e($item['label']) ?></a>
                <?php endforeach; ?>
            </nav>
            <?php endif; ?>
        </div>
    </footer>

    <style>
    /* Minimal Theme Styles */
    :root {
        --text-color: #1a1a1a;
        --text-light: #666;
        --bg-color: #fff;
        --bg-secondary: #fafafa;
        --accent-color: #333;
    }

    .minimal-theme {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
        color: var(--text-color);
        background: var(--bg-color);
    }

    .minimal-container {
        max-width: 960px;
        margin: 0 auto;
        padding: 0 20px;
    }

    /* Header */
    .minimal-header {
        padding: 30px 0;
        border-bottom: 1px solid #eee;
    }

    .minimal-header-inner {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .minimal-logo {
        font-size: 1.5rem;
        font-weight: 600;
        text-decoration: none;
        color: var(--text-color);
        letter-spacing: -0.5px;
    }

    .minimal-navigation {
        flex: 1;
        margin-left: 40px;
    }

    .minimal-nav-menu {
        display: flex;
        list-style: none;
        margin: 0;
        padding: 0;
        gap: 30px;
    }

    .minimal-nav-menu a {
        text-decoration: none;
        color: var(--text-light);
        font-size: 0.95rem;
        transition: color 0.2s;
    }

    .minimal-nav-menu a:hover,
    .minimal-nav-menu a.active {
        color: var(--text-color);
    }

    /* Main */
    .minimal-main {
        padding: 60px 0;
        min-height: 60vh;
    }

    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-weight: 600;
        line-height: 1.3;
        margin-top: 0;
    }

    h1 { font-size: 2.5rem; margin-bottom: 20px; }
    h2 { font-size: 2rem; margin-bottom: 16px; }
    h3 { font-size: 1.5rem; margin-bottom: 12px; }

    p {
        margin-bottom: 1.5em;
    }

    a {
        color: var(--accent-color);
        text-decoration: underline;
    }

    a:hover {
        text-decoration: none;
    }

    /* Footer */
    .minimal-footer {
        padding: 40px 0;
        border-top: 1px solid #eee;
        text-align: center;
    }

    .minimal-footer p {
        margin: 0 0 15px 0;
        color: var(--text-light);
        font-size: 0.9rem;
    }

    .minimal-footer-nav {
        display: flex;
        justify-content: center;
        gap: 20px;
        flex-wrap: wrap;
    }

    .minimal-footer-nav a {
        color: var(--text-light);
        text-decoration: none;
        font-size: 0.9rem;
    }

    .minimal-footer-nav a:hover {
        color: var(--text-color);
    }

    /* Posts */
    .post-card {
        margin-bottom: 40px;
        padding-bottom: 40px;
        border-bottom: 1px solid #eee;
    }

    .post-card:last-child {
        border-bottom: none;
    }

    .post-card h2 {
        margin-bottom: 10px;
    }

    .post-card h2 a {
        text-decoration: none;
        color: var(--text-color);
    }

    .post-card h2 a:hover {
        color: var(--accent-color);
    }

    .post-meta {
        color: var(--text-light);
        font-size: 0.9rem;
        margin-bottom: 15px;
    }

    .post-excerpt {
        color: var(--text-light);
    }

    .read-more {
        display: inline-block;
        margin-top: 15px;
        text-decoration: none;
        color: var(--accent-color);
        font-weight: 500;
    }

    .read-more:hover {
        text-decoration: underline;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .minimal-header-inner {
            flex-direction: column;
            gap: 20px;
        }

        .minimal-navigation {
            margin-left: 0;
            width: 100%;
        }

        .minimal-nav-menu {
            flex-wrap: wrap;
            gap: 15px;
            justify-content: center;
        }

        .minimal-main {
            padding: 40px 0;
        }

        h1 { font-size: 2rem; }
        h2 { font-size: 1.5rem; }
    }
    </style>
</body>
</html>
