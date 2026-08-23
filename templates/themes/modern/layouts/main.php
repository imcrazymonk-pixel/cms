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

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <?php if (!empty($ogImage)): ?>
    <meta name="twitter:image" content="<?= SITE_URL . $ogImage ?>">
    <?php endif; ?>

    <!-- Canonical URL -->
    <link rel="canonical" href="<?= SITE_URL . ($_SERVER['REQUEST_URI'] ?? '') ?>">

    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

    <!-- Styles -->
    <link rel="stylesheet" href="<?= TemplateEngine::asset('css/cms-tokens.css') ?>">
    <link rel="stylesheet" href="<?= TemplateEngine::asset('css/style.css') ?>">
    <?php if (!empty($extraCss)): ?>
    <?php foreach ($extraCss as $css): ?>
    <link rel="stylesheet" href="<?= $css ?>">
    <?php endforeach; ?>
    <?php endif; ?>
</head>
<body class="<?= $bodyClass ?? '' ?> modern-theme">
    <!-- Header с навигацией -->
    <header class="modern-header">
        <div class="modern-container">
            <div class="modern-header-inner">
                <a href="<?= TemplateEngine::url() ?>" class="modern-logo">
                    <span class="logo-icon">🚀</span>
                    <span class="logo-text"><?= $siteLogo ?? SITE_NAME ?></span>
                </a>

                <button class="modern-menu-toggle" aria-label="Меню">
                    <span></span>
                    <span></span>
                    <span></span>
                </button>

                <nav class="modern-navigation">
                    <ul class="modern-nav-menu">
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

                <div class="header-cta">
                    <a href="#contact" class="btn btn-primary">Связаться</a>
                </div>
            </div>
        </div>
    </header>

    <!-- Hero секция для главной -->
    <?php if (!empty($showHero) && $showHero): ?>
    <section class="modern-hero">
        <div class="modern-container">
            <div class="hero-content">
                <h1 class="hero-title"><?= $heroTitle ?? 'Добро пожаловать' ?></h1>
                <p class="hero-subtitle"><?= $heroSubtitle ?? '' ?></p>
                <div class="hero-buttons">
                    <a href="/blog" class="btn btn-primary btn-lg">Наш блог</a>
                    <a href="/about" class="btn btn-outline btn-lg">О нас</a>
                </div>
            </div>
        </div>
    </section>
    <?php endif; ?>

    <!-- Основной контент -->
    <main class="modern-main">
        <div class="modern-container">
            <?= $content ?? '' ?>
        </div>
    </main>

    <!-- Footer -->
    <footer class="modern-footer">
        <div class="modern-container">
            <div class="footer-grid">
                <div class="footer-col">
                    <h4><?= SITE_NAME ?></h4>
                    <p class="footer-description">Современная CMS для ваших проектов</p>
                    <div class="social-links">
                        <?php if (!empty($socialLinks)): ?>
                            <?php foreach ($socialLinks as $social): ?>
                            <a href="<?= TemplateEngine::e($social['url']) ?>" class="social-link" target="_blank" rel="noopener">
                                <?= $social['icon'] ?? '🔗' ?>
                            </a>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </div>
                </div>

                <div class="footer-col">
                    <h4>Навигация</h4>
                    <?php if (!empty($footerMenu)): ?>
                    <ul class="footer-links">
                        <?php foreach ($footerMenu as $item): ?>
                        <li><a href="<?= TemplateEngine::e($item['url']) ?>"><?= TemplateEngine::e($item['label']) ?></a></li>
                        <?php endforeach; ?>
                    </ul>
                    <?php endif; ?>
                </div>

                <div class="footer-col">
                    <h4>Контакты</h4>
                    <ul class="contact-list">
                        <li>📧 <?= ADMIN_EMAIL ?></li>
                        <li>📍 <?= SITE_NAME ?></li>
                    </ul>
                </div>
            </div>

            <div class="footer-bottom">
                <p>&copy; <?= date('Y') ?> <?= SITE_NAME ?>. Все права защищены.</p>
            </div>
        </div>
    </footer>

    <script>
        // Мобильное меню
        document.querySelector('.modern-menu-toggle')?.addEventListener('click', function() {
            document.querySelector('.modern-navigation')?.classList.toggle('active');
            this.classList.toggle('active');
        });
    </script>

    <?php if (!empty($extraJs)): ?>
    <?php foreach ($extraJs as $js): ?>
    <script src="<?= $js ?>"></script>
    <?php endforeach; ?>
    <?php endif; ?>

    <style>
    /* Modern Theme Styles */
    :root {
        --primary-color: #6366f1;
        --secondary-color: #8b5cf6;
        --accent-color: #f59e0b;
        --text-color: #1f2937;
        --text-light: #6b7280;
        --bg-color: #ffffff;
        --bg-secondary: #f9fafb;
        --border-color: #e5e7eb;
    }

    .modern-theme {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--bg-color);
        color: var(--text-color);
    }

    .modern-container {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 24px;
    }

    /* Header */
    .modern-header {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--border-color);
        position: sticky;
        top: 0;
        z-index: 1000;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .modern-header-inner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 0;
        gap: 24px;
    }

    .modern-logo {
        display: flex;
        align-items: center;
        gap: 12px;
        text-decoration: none;
        color: var(--text-color);
        font-weight: 700;
        font-size: 1.5rem;
    }

    .logo-icon {
        font-size: 2rem;
    }

    .modern-navigation {
        flex: 1;
    }

    .modern-nav-menu {
        display: flex;
        list-style: none;
        gap: 8px;
        margin: 0;
        padding: 0;
    }

    .modern-nav-menu a {
        display: block;
        padding: 10px 16px;
        text-decoration: none;
        color: var(--text-light);
        font-weight: 500;
        border-radius: 8px;
        transition: all 0.2s;
    }

    .modern-nav-menu a:hover,
    .modern-nav-menu a.active {
        color: var(--primary-color);
        background: rgba(99, 102, 241, 0.1);
    }

    .header-cta .btn {
        padding: 10px 24px;
    }

    .modern-menu-toggle {
        display: none;
        flex-direction: column;
        gap: 5px;
        background: none;
        border: none;
        cursor: pointer;
        padding: 8px;
    }

    .modern-menu-toggle span {
        width: 24px;
        height: 2px;
        background: var(--text-color);
        transition: all 0.3s;
    }

    /* Hero */
    .modern-hero {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
        padding: 100px 24px;
        text-align: center;
        color: white;
    }

    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 20px;
        line-height: 1.1;
    }

    .hero-subtitle {
        font-size: 1.25rem;
        opacity: 0.9;
        max-width: 600px;
        margin: 0 auto 40px;
    }

    .hero-buttons {
        display: flex;
        gap: 16px;
        justify-content: center;
        flex-wrap: wrap;
    }

    /* Main */
    .modern-main {
        padding: 60px 0;
        min-height: 60vh;
    }

    /* Footer */
    .modern-footer {
        background: var(--bg-secondary);
        padding: 60px 0 30px;
        border-top: 1px solid var(--border-color);
    }

    .footer-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 40px;
        margin-bottom: 40px;
    }

    .footer-col h4 {
        margin-bottom: 16px;
        color: var(--text-color);
        font-weight: 600;
    }

    .footer-description {
        color: var(--text-light);
        line-height: 1.6;
    }

    .footer-links,
    .contact-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .footer-links li,
    .contact-list li {
        margin-bottom: 12px;
    }

    .footer-links a {
        color: var(--text-light);
        text-decoration: none;
        transition: color 0.2s;
    }

    .footer-links a:hover {
        color: var(--primary-color);
    }

    .social-links {
        display: flex;
        gap: 12px;
        margin-top: 16px;
    }

    .social-link {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        background: var(--bg-secondary);
        border-radius: 50%;
        text-decoration: none;
        font-size: 1.2rem;
        transition: all 0.2s;
    }

    .social-link:hover {
        background: var(--primary-color);
        transform: translateY(-2px);
    }

    .footer-bottom {
        text-align: center;
        padding-top: 30px;
        border-top: 1px solid var(--border-color);
        color: var(--text-light);
    }

    /* Buttons */
    .btn {
        display: inline-block;
        padding: 12px 24px;
        border-radius: 10px;
        font-weight: 600;
        text-decoration: none;
        transition: all 0.2s;
        cursor: pointer;
        border: none;
    }

    .btn-primary {
        background: var(--primary-color);
        color: white;
    }

    .btn-primary:hover {
        background: #4f46e5;
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(99, 102, 241, 0.3);
    }

    .btn-outline {
        background: transparent;
        color: white;
        border: 2px solid white;
    }

    .btn-outline:hover {
        background: white;
        color: var(--primary-color);
    }

    .btn-lg {
        padding: 16px 32px;
        font-size: 1.1rem;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .modern-menu-toggle {
            display: flex;
        }

        .modern-navigation {
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }

        .modern-navigation.active {
            display: block;
        }

        .modern-nav-menu {
            flex-direction: column;
        }

        .header-cta {
            display: none;
        }

        .hero-title {
            font-size: 2.5rem;
        }

        .footer-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
</body>
</html>
