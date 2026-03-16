<?php
/**
 * Шаблон лендинга
 * Одностраничный шаблон с ярким дизайном
 */
?>

<article class="landing-page">
    <!-- Hero секция -->
    <header class="landing-hero">
        <div class="hero-content">
            <h1><?= TemplateEngine::e($page['title'] ?? $title) ?></h1>
            <?php if (!empty($page['meta_description'])): ?>
            <p class="hero-subtitle"><?= TemplateEngine::e($page['meta_description']) ?></p>
            <?php endif; ?>
            <?php if (!empty($page['content'])): ?>
                <?php
                $firstParagraph = preg_match('/<p[^>]*>(.*?)<\/p>/s', $page['content'], $matches);
                if ($firstParagraph && !empty($matches[1])):
                ?>
                <div class="hero-description"><?= strip_tags($matches[1]) ?></div>
                <?php endif; ?>
            <?php endif; ?>
            <a href="#content" class="btn btn-hero">Узнать больше ↓</a>
        </div>
    </header>

    <!-- Основной контент -->
    <section id="content" class="landing-content">
        <div class="container">
            <div class="content-wrapper">
                <?= $page['content'] ?? $content ?? '' ?>
            </div>
        </div>
    </section>

    <!-- Footer секция -->
    <footer class="landing-footer">
        <div class="container">
            <p>&copy; <?= date('Y') ?> <?= SITE_NAME ?>. Все права защищены.</p>
        </div>
    </footer>
</article>

<style>
.landing-page {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Hero секция */
.landing-hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 120px 20px;
    text-align: center;
    min-height: 80vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.hero-content h1 {
    font-size: 3.5rem;
    margin-bottom: 20px;
    font-weight: 700;
}

.hero-subtitle {
    font-size: 1.5rem;
    opacity: 0.95;
    margin-bottom: 30px;
}

.hero-description {
    font-size: 1.2rem;
    max-width: 600px;
    margin: 0 auto 40px;
    opacity: 0.9;
}

.btn-hero {
    display: inline-block;
    padding: 18px 40px;
    background: white;
    color: #667eea;
    text-decoration: none;
    border-radius: 50px;
    font-weight: 600;
    font-size: 1.1rem;
    transition: transform 0.3s, box-shadow 0.3s;
}

.btn-hero:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

/* Контент */
.landing-content {
    padding: 80px 20px;
    background: #f8f9fa;
}

.landing-content .container {
    max-width: 1200px;
    margin: 0 auto;
}

.content-wrapper {
    background: white;
    padding: 60px;
    border-radius: 20px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    font-size: 1.1rem;
    line-height: 1.8;
}

.content-wrapper h2 {
    color: #667eea;
    font-size: 2rem;
    margin-top: 40px;
    margin-bottom: 20px;
}

.content-wrapper h3 {
    color: #764ba2;
    font-size: 1.5rem;
    margin-top: 30px;
    margin-bottom: 15px;
}

.content-wrapper img {
    max-width: 100%;
    height: auto;
    border-radius: 10px;
    margin: 20px 0;
}

.content-wrapper ul,
.content-wrapper ol {
    margin: 20px 0;
    padding-left: 30px;
}

.content-wrapper li {
    margin-bottom: 10px;
}

/* Footer */
.landing-footer {
    background: #2d3748;
    color: white;
    padding: 40px 20px;
    text-align: center;
}

.landing-footer p {
    margin: 0;
    opacity: 0.8;
}

/* Адаптивность */
@media (max-width: 768px) {
    .hero-content h1 {
        font-size: 2.5rem;
    }
    
    .hero-subtitle {
        font-size: 1.2rem;
    }
    
    .content-wrapper {
        padding: 30px;
    }
}
</style>
