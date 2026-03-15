<?php
/**
 * Мастер установки CMS
 * Проверка окружения, создание БД, генерация конфигурации
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

$step = isset($_GET['step']) ? (int) $_GET['step'] : 1;
$errors = [];
$success = false;

// Проверка блокировки установки
if (file_exists(__DIR__ . '/../install.lock')) {
    die('CMS уже установлена. Удалите файл install.lock для повторной установки.');
}

// Проверка наличия config.php (значит система уже настроена)
if (file_exists(__DIR__ . '/../config/config.php')) {
    die('Файл config.php уже существует. Удалите его для повторной установки.');
}

// ============================================
// Проверка требований
// ============================================
function checkRequirements(): array
{
    return [
        'php_version' => [
            'name' => 'PHP версия >= 7.4',
            'passed' => version_compare(PHP_VERSION, '7.4.0', '>='),
            'current' => PHP_VERSION,
        ],
        'pdo' => [
            'name' => 'Расширение PDO',
            'passed' => extension_loaded('pdo'),
            'current' => extension_loaded('pdo') ? 'Да' : 'Нет',
        ],
        'pdo_mysql' => [
            'name' => 'PDO MySQL',
            'passed' => extension_loaded('pdo_mysql'),
            'current' => extension_loaded('pdo_mysql') ? 'Да' : 'Нет',
        ],
        'mbstring' => [
            'name' => 'MBString',
            'passed' => extension_loaded('mbstring'),
            'current' => extension_loaded('mbstring') ? 'Да' : 'Нет',
        ],
        'json' => [
            'name' => 'JSON',
            'passed' => extension_loaded('json'),
            'current' => extension_loaded('json') ? 'Да' : 'Нет',
        ],
        'config_writable' => [
            'name' => 'Папка /config доступна для записи',
            'passed' => is_writable(__DIR__ . '/../config'),
            'current' => is_writable(__DIR__ . '/../config') ? 'Да' : 'Нет',
        ],
    ];
}

// ============================================
// Генерация config.php
// ============================================
function generateConfig(array $data, string $adminEmail): string
{
    $date = date('Y-m-d H:i:s');
    return "<?php
/**
 * Конфигурационный файл CMS
 * Сгенерирован установщиком {$date}
 */

// Доступ к базе данных
define('DB_HOST', '" . addslashes($data['db_host']) . "');
define('DB_NAME', '" . addslashes($data['db_name']) . "');
define('DB_USER', '" . addslashes($data['db_user']) . "');
define('DB_PASS', '" . addslashes($data['db_pass']) . "');
define('DB_CHARSET', 'utf8mb4');

// Настройки сайта
define('SITE_NAME', 'Моя CMS');
define('SITE_URL', 'http://' . \$_SERVER['HTTP_HOST']);
define('ADMIN_EMAIL', '" . addslashes($adminEmail) . "');

// Пути к директориям
define('ROOT_PATH', dirname(dirname(__DIR__)));
define('PUBLIC_PATH', ROOT_PATH . '/public');
define('ADMIN_PATH', ROOT_PATH . '/admin');
define('CORE_PATH', ROOT_PATH . '/core');
define('TEMPLATES_PATH', ROOT_PATH . '/templates');

// Настройки сессии
define('SESSION_LIFETIME', 3600);

// Настройки безопасности
define('HASH_ALGO', PASSWORD_BCRYPT);
define('HASH_COST', 10);

// Отладка (false в production)
define('DEBUG', true);

// Постов на страницу
define('POSTS_PER_PAGE', 10);
";
}

// ============================================
// Обработка форм
// ============================================
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['step'])) {
    $postStep = (int) $_POST['step'];

    if ($postStep === 2) {
        $host = $_POST['db_host'] ?? 'localhost';
        $name = $_POST['db_name'] ?? 'cms';
        $user = $_POST['db_user'] ?? 'root';
        $pass = $_POST['db_pass'] ?? '';

        try {
            $dsn = "mysql:host={$host};charset=utf8mb4";
            $pdo = new PDO($dsn, $user, $pass, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);

            $stmt = $pdo->query("SHOW DATABASES LIKE '{$name}'");
            $dbExists = $stmt->rowCount() > 0;

            if (!$dbExists) {
                $pdo->exec("CREATE DATABASE `{$name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
            }

            $dsn = "mysql:host={$host};dbname={$name};charset=utf8mb4";
            $pdo = new PDO($dsn, $user, $pass, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);

            $_SESSION['install_data'] = [
                'db_host' => $host,
                'db_name' => $name,
                'db_user' => $user,
                'db_pass' => $pass,
            ];

            header('Location: ?step=3');
            exit;
        } catch (PDOException $e) {
            $errors[] = 'Ошибка подключения к БД: ' . $e->getMessage();
            $step = 2;
        }
    }

    if ($postStep === 4) {
        // Берём данные БД из сессии или из POST (скрытые поля)
        $data = $_SESSION['install_data'] ?? [
            'db_host' => $_POST['db_host'] ?? 'localhost',
            'db_name' => $_POST['db_name'] ?? 'cms',
            'db_user' => $_POST['db_user'] ?? 'root',
            'db_pass' => $_POST['db_pass'] ?? '',
        ];

        $adminLogin = trim($_POST['admin_login'] ?? '');
        $adminEmail = trim($_POST['admin_email'] ?? '');
        $adminPass = $_POST['admin_pass'] ?? '';
        $adminPassConfirm = $_POST['admin_pass_confirm'] ?? '';

        if (strlen($adminLogin) < 3) {
            $errors[] = 'Логин должен быть не менее 3 символов';
        }
        if (!filter_var($adminEmail, FILTER_VALIDATE_EMAIL)) {
            $errors[] = 'Некорректный email';
        }
        if (strlen($adminPass) < 6) {
            $errors[] = 'Пароль должен быть не менее 6 символов';
        }
        if ($adminPass !== $adminPassConfirm) {
            $errors[] = 'Пароли не совпадают';
        }

        if (empty($errors) && !empty($data)) {
            try {
                $dsn = "mysql:host={$data['db_host']};dbname={$data['db_name']};charset=utf8mb4";
                $pdo = new PDO($dsn, $data['db_user'], $data['db_pass'], [
                    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                ]);

                // Проверяем путь к SQL файлу
                $sqlFile = dirname(__DIR__) . '/database.sql';
                if (!file_exists($sqlFile)) {
                    // Пробуем альтернативный путь (файл в корне)
                    $sqlFile = dirname(dirname(__DIR__)) . '/database.sql';
                }
                if (!file_exists($sqlFile)) {
                    throw new Exception('Файл database.sql не найден. Путь: ' . $sqlFile);
                }

                $sql = file_get_contents($sqlFile);
                if ($sql === false) {
                    throw new Exception('Не удалось прочитать файл database.sql');
                }

                // Используем multiQuery для выполнения всего SQL за раз
                $pdo->exec($sql);

                $hashedPass = password_hash($adminPass, PASSWORD_BCRYPT);
                $stmt = $pdo->prepare("INSERT INTO users (login, email, password, role) VALUES (:login, :email, :password, 'admin')");
                $stmt->execute([
                    'login' => $adminLogin,
                    'email' => $adminEmail,
                    'password' => $hashedPass,
                ]);

                $stmt = $pdo->prepare("UPDATE settings SET setting_value = :value WHERE setting_key = 'admin_email'");
                $stmt->execute(['value' => $adminEmail]);

                file_put_contents(__DIR__ . '/../config/config.php', generateConfig($data, $adminEmail));
                file_put_contents(__DIR__ . '/../install.lock', date('Y-m-d H:i:s'));

                unset($_SESSION['install_data']);

                $success = true;
                $step = 5;
            } catch (Exception $e) {
                $errors[] = 'Ошибка установки: ' . $e->getMessage();
            }
        } else {
            $step = 3;
        }
    }
}
?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Установка CMS</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 700px;
            width: 100%;
            overflow: hidden;
        }
        .header {
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            border-bottom: 1px solid #e9ecef;
        }
        .header h1 { color: #333; font-size: 28px; margin-bottom: 10px; }
        .header p { color: #666; }
        .progress {
            display: flex;
            background: #f8f9fa;
            padding: 20px 30px;
            border-bottom: 1px solid #e9ecef;
        }
        .progress-step {
            flex: 1;
            text-align: center;
            position: relative;
            font-size: 14px;
            color: #999;
            z-index: 1;
        }
        .progress-step-inner {
            display: inline-block;
            background: #f8f9fa;
            padding: 0 10px;
            position: relative;
            z-index: 2;
        }
        .progress-step.active { color: #667eea; font-weight: 600; }
        .progress-step.completed { color: #28a745; }
        .progress-step:not(:last-child) .progress-line {
            content: '';
            position: absolute;
            top: 10px;
            left: 50%;
            width: 100%;
            height: 2px;
            background: #e9ecef;
            z-index: 0;
        }
        .progress-step.completed:not(:last-child) .progress-line { background: #28a745; }
        .content { padding: 40px; }
        .step-content { display: none; }
        .step-content.active { display: block; }
        .requirements { list-style: none; }
        .requirements li {
            padding: 12px 15px;
            margin-bottom: 8px;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .requirements li.passed { background: #d4edda; color: #155724; }
        .requirements li.failed { background: #f8d7da; color: #721c24; }
        .badge { 
            padding: 4px 12px; 
            border-radius: 20px; 
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success { background: #28a745; color: white; }
        .badge-danger { background: #dc3545; color: white; }
        .form-group { margin-bottom: 20px; }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #333;
        }
        .form-group input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e9ecef;
            border-radius: 6px;
            font-size: 15px;
            transition: border-color 0.2s;
        }
        .form-group input:focus { outline: none; border-color: #667eea; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .btn {
            display: inline-block;
            padding: 14px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            text-decoration: none;
            transition: background 0.2s;
        }
        .btn:hover { background: #5a6fd6; }
        .btn-secondary { background: #6c757d; }
        .btn-secondary:hover { background: #5a6268; }
        .btn-block { width: 100%; }
        .errors {
            background: #f8d7da;
            color: #721c24;
            padding: 15px 20px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        .errors ul { margin: 0; padding-left: 20px; }
        .success-box {
            background: #d4edda;
            color: #155724;
            padding: 30px;
            border-radius: 6px;
            text-align: center;
        }
        .success-box h2 { margin-bottom: 15px; }
        .info-box {
            background: #e7f3ff;
            border-left: 4px solid #667eea;
            padding: 15px 20px;
            margin-bottom: 20px;
            border-radius: 0 6px 6px 0;
        }
        .small { font-size: 13px; color: #666; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Установка CMS</h1>
            <p>Мастер установки поможет настроить вашу CMS</p>
        </div>

        <div class="progress">
            <div class="progress-step <?= $step >= 1 ? 'active' : '' ?> <?= $step > 1 ? 'completed' : '' ?>">
                <span class="progress-line"></span>
                <span class="progress-step-inner">1. Требования</span>
            </div>
            <div class="progress-step <?= $step >= 2 ? 'active' : '' ?> <?= $step > 2 ? 'completed' : '' ?>">
                <span class="progress-line"></span>
                <span class="progress-step-inner">2. База данных</span>
            </div>
            <div class="progress-step <?= $step >= 3 ? 'active' : '' ?> <?= $step > 3 ? 'completed' : '' ?>">
                <span class="progress-line"></span>
                <span class="progress-step-inner">3. Администратор</span>
            </div>
            <div class="progress-step <?= $step >= 4 ? 'active' : '' ?> <?= $step > 4 ? 'completed' : '' ?>">
                <span class="progress-step-inner">4. Установка</span>
            </div>
        </div>

        <div class="content">
            <?php if (!empty($errors)): ?>
            <div class="errors">
                <strong>Ошибки:</strong>
                <ul>
                    <?php foreach ($errors as $error): ?>
                        <li><?= htmlspecialchars($error) ?></li>
                    <?php endforeach; ?>
                </ul>
            </div>
            <?php endif; ?>

            <!-- Шаг 1: Требования -->
            <div class="step-content <?= $step === 1 ? 'active' : '' ?>">
                <h2 style="margin-bottom: 20px;">Проверка требований</h2>
                <ul class="requirements">
                    <?php foreach (checkRequirements() as $req): ?>
                    <li class="<?= $req['passed'] ? 'passed' : 'failed' ?>">
                        <span><?= $req['name'] ?></span>
                        <span class="badge <?= $req['passed'] ? 'badge-success' : 'badge-danger' ?>">
                            <?= $req['current'] ?>
                        </span>
                    </li>
                    <?php endforeach; ?>
                </ul>

                <?php
                $allPassed = !array_filter(checkRequirements(), fn($r) => !$r['passed']);
                if ($allPassed):
                ?>
                <div style="margin-top: 25px; text-align: center;">
                    <a href="?step=2" class="btn btn-block">Продолжить →</a>
                </div>
                <?php else: ?>
                <div class="info-box" style="margin-top: 20px;">
                    ⚠️ Устраните ошибки выше и обновите страницу
                </div>
                <?php endif; ?>
            </div>

            <!-- Шаг 2: База данных -->
            <div class="step-content <?= $step === 2 ? 'active' : '' ?>">
                <h2 style="margin-bottom: 20px;">Настройка базы данных</h2>

                <div class="info-box">
                    База данных будет создана автоматически, если не существует
                </div>

                <form method="POST">
                    <input type="hidden" name="step" value="2">

                    <div class="form-row">
                        <div class="form-group">
                            <label>Host</label>
                            <input type="text" name="db_host" value="localhost" required>
                        </div>
                        <div class="form-group">
                            <label>Имя базы</label>
                            <input type="text" name="db_name" value="cms" required>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label>Пользователь БД</label>
                            <input type="text" name="db_user" value="root" required>
                        </div>
                        <div class="form-group">
                            <label>Пароль БД</label>
                            <input type="password" name="db_pass" value="">
                        </div>
                    </div>

                    <div style="display: flex; gap: 15px; margin-top: 25px;">
                        <a href="?step=1" class="btn btn-secondary">← Назад</a>
                        <button type="submit" class="btn" style="flex: 1;">Проверить подключение →</button>
                    </div>
                </form>
            </div>

            <!-- Шаг 3: Администратор -->
            <div class="step-content <?= $step === 3 ? 'active' : '' ?>">
                <h2 style="margin-bottom: 20px;">Учётная запись администратора</h2>

                <?php
                // Проверяем, есть ли данные БД в сессии
                $dbData = $_SESSION['install_data'] ?? [];
                ?>

                <form method="POST">
                    <input type="hidden" name="step" value="4">
                    <!-- Сохраняем данные БД в скрытые поля -->
                    <input type="hidden" name="db_host" value="<?= htmlspecialchars($dbData['db_host'] ?? '') ?>">
                    <input type="hidden" name="db_name" value="<?= htmlspecialchars($dbData['db_name'] ?? '') ?>">
                    <input type="hidden" name="db_user" value="<?= htmlspecialchars($dbData['db_user'] ?? '') ?>">
                    <input type="hidden" name="db_pass" value="<?= htmlspecialchars($dbData['db_pass'] ?? '') ?>">

                    <div class="form-group">
                        <label>Логин</label>
                        <input type="text" name="admin_login" required minlength="3">
                    </div>

                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" name="admin_email" required>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label>Пароль</label>
                            <input type="password" name="admin_pass" required minlength="6">
                            <div class="small">Минимум 6 символов</div>
                        </div>
                        <div class="form-group">
                            <label>Подтверждение пароля</label>
                            <input type="password" name="admin_pass_confirm" required>
                        </div>
                    </div>

                    <div style="display: flex; gap: 15px; margin-top: 25px;">
                        <a href="?step=2" class="btn btn-secondary">← Назад</a>
                        <button type="submit" class="btn" style="flex: 1;">Установить CMS 🚀</button>
                    </div>
                </form>
            </div>

            <!-- Шаг 4: Установка -->
            <div class="step-content <?= $step === 4 ? 'active' : '' ?>">
                <div style="text-align: center; padding: 40px 0;">
                    <div style="font-size: 60px; margin-bottom: 20px;">⚙️</div>
                    <h2>Установка...</h2>
                    <p style="color: #666; margin-top: 10px;">Пожалуйста, подождите</p>
                </div>
            </div>

            <!-- Шаг 5: Готово -->
            <div class="step-content <?= $step === 5 ? 'active' : '' ?>">
                <div class="success-box">
                    <h2>✅ Установка завершена!</h2>
                    <p style="margin-bottom: 25px;">
                        CMS успешно установлена. Теперь вы можете войти в панель администратора.
                    </p>
                    <div style="display: flex; gap: 15px; justify-content: center;">
                        <a href="/public/" class="btn btn-secondary">На сайт</a>
                        <a href="/admin/login" class="btn">Войти в админку</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
