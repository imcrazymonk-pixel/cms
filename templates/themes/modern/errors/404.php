<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Страница не найдена</title>
    <meta name="robots" content="noindex">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/public/css/cms-tokens.css">
    <style>
        body {
            font-family: 'Outfit', system-ui, sans-serif;
            background: #1e1e2e;
            color: #f5f5f7;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            text-align: center;
            padding: 20px;
            -webkit-font-smoothing: antialiased;
        }
        .error-page { max-width: 480px; }
        .error-code {
            font-size: 96px;
            font-weight: 700;
            color: #6366f1;
            line-height: 1;
            margin-bottom: 8px;
        }
        .error-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .error-text {
            color: rgba(255, 255, 255, 0.55);
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 32px;
        }
        .error-actions {
            display: flex;
            gap: 12px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 24px;
            border-radius: 6px;
            font-size: 15px;
            font-weight: 500;
            font-family: inherit;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
        }
        .btn-primary {
            background: #6366f1;
            color: white;
        }
        .btn-primary:hover {
            background: #4f46e5;
        }
        .btn-outline {
            background: transparent;
            border: 2px solid rgba(255, 255, 255, 0.15);
            color: rgba(255, 255, 255, 0.65);
        }
        .btn-outline:hover {
            border-color: #6366f1;
            color: #6366f1;
        }
    </style>
</head>
<body>
    <div class="error-page">
        <div class="error-code">404</div>
        <h1 class="error-title">Страница не найдена</h1>
        <p class="error-text">
            Страница, которую вы ищете, не существует или была перемещена.<br>
            Возможно, вы перешли по устаревшей ссылке.
        </p>
        <div class="error-actions">
            <a href="/" class="btn btn-primary">← На главную</a>
            <a href="javascript:history.back()" class="btn btn-outline">Вернуться назад</a>
        </div>
    </div>
</body>
</html>