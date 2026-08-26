<!DOCTYPE html>
<html lang="ru" data-theme="obsidian" data-mode="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход в админку — <?= SITE_NAME ?></title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Unbounded:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/tokens.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/tokens.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/themes.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/themes.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/base.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/base.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/effects.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/effects.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/components.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/components.css') ?>">
    <link rel="stylesheet" href="<?= SITE_URL ?>/public/css/panel/layout.css?v=<?= filemtime(PUBLIC_PATH . '/css/panel/layout.css') ?>">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%236366f1'/%3E%3Ctext x='50' y='72' font-size='56' font-family='Arial' font-weight='bold' text-anchor='middle' fill='white'%3EC%3C/text%3E%3C/svg%3E">
</head>
<body class="login-page">
    <!-- Mesh-фон -->
    <div class="mesh-bg" aria-hidden="true">
        <div class="mesh-layer mesh-layer--1"></div>
        <div class="mesh-layer mesh-layer--2"></div>
        <div class="mesh-layer mesh-layer--3"></div>
        <div class="mesh-layer mesh-layer--4"></div>
        <div class="mesh-layer mesh-layer--5"></div>
    </div>

    <div class="login-container">
        <div class="login-box glass-card anim-scale-in">
            <div class="login-logo login-logo-glow"><?= icon('hexa', 'icon-lg') ?></div>
            <h1 class="login-title">Вход в админку</h1>

            <?php if (isset($error)): ?>
            <div class="alert alert-error">
                <?= TemplateEngine::e($error) ?>
            </div>
            <?php endif; ?>

            <form method="POST" action="/admin/login" class="login-form">
                <?= csrf_field() ?>

                <div class="form-group">
                    <label for="login">Логин или Email</label>
                    <input type="text" id="login" name="login" required autofocus
                           placeholder="Введите логин или email">
                </div>

                <div class="form-group">
                    <label for="password">Пароль</label>
                    <input type="password" id="password" name="password" required
                           placeholder="Введите пароль">
                </div>

                <button type="submit" class="btn btn-primary btn-lg btn-block">
                    <?= icon('logout', 'icon-sm') ?> Войти
                </button>
            </form>

            <p class="login-footer">
                <a href="/"><?= icon('back') ?> Вернуться на сайт</a>
            </p>
        </div>
    </div>
</body>
</html>
