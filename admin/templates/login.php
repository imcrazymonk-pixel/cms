<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход в админку — <?= SITE_NAME ?></title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/public/css/cms-tokens.css">
    <link rel="stylesheet" href="/admin/css/admin.css?v=<?= filemtime(ADMIN_PATH . '/css/admin.css') ?>">
</head>
<body class="login-page">
    <div class="login-container">
        <div class="login-box">
            <div class="login-logo"><?= icon('dashboard', 'icon-lg') ?></div>
            <h1 class="login-title">Вход в админку</h1>

            <?php if (isset($error)): ?>
            <div class="alert alert-error">
                <?= icon('error') ?>
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

                <button type="submit" class="btn btn-primary btn-block">
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
