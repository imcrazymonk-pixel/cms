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
    <?php if (!empty($seo['keywords'])): ?>
    <meta name="keywords" content="<?= TemplateEngine::e($seo['keywords']) ?>">
    <?php endif; ?>
    
    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="<?= $seo['title'] ?? ($title ?? SITE_NAME) ?>">
    <meta property="og:url" content="<?= SITE_URL . ($_SERVER['REQUEST_URI'] ?? '') ?>">
    <?php if (!empty($seo['description'])): ?>
    <meta property="og:description" content="<?= TemplateEngine::e($seo['description']) ?>">
    <?php endif; ?>
    <?php if (!empty($ogImage)): ?>
    <meta property="og:image" content="<?= SITE_URL . $ogImage ?>">
    <?php endif; ?>
    
    <!-- Canonical URL -->
    <link rel="canonical" href="<?= SITE_URL . ($_SERVER['REQUEST_URI'] ?? '') ?>">

    <!-- Styles -->
    <link rel="stylesheet" href="<?= TemplateEngine::asset('css/style.css') ?>">
    <?php if (!empty($extraCss)): ?>
    <?php foreach ($extraCss as $css): ?>
    <link rel="stylesheet" href="<?= $css ?>">
    <?php endforeach; ?>
    <?php endif; ?>
</head>
<body class="<?= $bodyClass ?? '' ?>">
    <header class="site-header">
        <div class="container">
            <div class="header-inner">
                <a href="<?= TemplateEngine::url() ?>" class="logo">
                    <?= $siteLogo ?? SITE_NAME ?>
                </a>
                
                <button class="mobile-menu-toggle" aria-label="Меню">
                    <span></span>
                    <span></span>
                    <span></span>
                </button>
                
                <nav class="main-navigation">
                    <ul class="nav-menu">
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
        </div>
    </header>

    <main class="site-main">
        <div class="container">
            <?= $content ?? '' ?>
        </div>
    </main>

    <footer class="site-footer">
        <div class="container">
            <div class="footer-inner">
                <div class="footer-info">
                    <p>&copy; <?= date('Y') ?> <?= SITE_NAME ?>.</p>
                    <p>Все права защищены.</p>
                </div>
                
                <?php if (!empty($footerMenu)): ?>
                <nav class="footer-navigation">
                    <ul class="footer-menu">
                        <?php foreach ($footerMenu as $item): ?>
                        <li><a href="<?= TemplateEngine::e($item['url']) ?>"><?= TemplateEngine::e($item['label']) ?></a></li>
                        <?php endforeach; ?>
                    </ul>
                </nav>
                <?php endif; ?>
                
                <div class="footer-social">
                    <?php if (!empty($socialLinks)): ?>
                        <?php foreach ($socialLinks as $social): ?>
                        <a href="<?= TemplateEngine::e($social['url']) ?>" class="social-link" target="_blank" rel="noopener">
                            <?= $social['icon'] ?? '🔗' ?>
                        </a>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </div>
            </div>
        </div>
    </footer>

    <script>
        // Мобильное меню
        document.querySelector('.mobile-menu-toggle')?.addEventListener('click', function() {
            document.querySelector('.main-navigation')?.classList.toggle('active');
            this.classList.toggle('active');
        });
    </script>
    
    <?php if (!empty($extraJs)): ?>
    <?php foreach ($extraJs as $js): ?>
    <script src="<?= $js ?>"></script>
    <?php endforeach; ?>
    <?php endif; ?>
</body>
</html>
