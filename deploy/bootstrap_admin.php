<?php
/**
 * HexaVeil CMS — idempotent admin bootstrap (installer helper, not a route).
 *
 * Usage (inside the `app` container):
 *   docker compose exec -T app php deploy/bootstrap_admin.php
 *
 * Env:
 *   ADMIN_LOGIN    — default "admin"
 *   ADMIN_PASSWORD — required to create a user or replace a placeholder hash
 *   ADMIN_EMAIL    — optional, used only when creating a new user
 *   FORCE_RESET=1  — rotate the password of an existing non-placeholder admin
 *
 * Exit codes:
 *   0 — user ensured / nothing to do
 *   1 — database or hashing error
 *   2 — password required but missing (placeholder hash / new user)
 */
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    fwrite(STDERR, "ERROR: bootstrap_admin.php must be run from the command line.\n");
    exit(1);
}

$env = static function (string $key, string $default = ''): string {
    $value = getenv($key);
    if ($value === false) {
        return $default;
    }
    return $value;
};

$login = trim($env('ADMIN_LOGIN', 'admin'));
$password = $env('ADMIN_PASSWORD', '');
$email = trim($env('ADMIN_EMAIL', ''));
$forceReset = in_array(strtolower($env('FORCE_RESET', '0')), ['1', 'true', 'yes', 'on'], true);

// Exact placeholder shipped in db/postgres/init/01-schema.sql.
$placeholder = '$2y$10$change_this_to_a_real_bcrypt_hash';

if ($login === '') {
    fwrite(STDERR, "ERROR: ADMIN_LOGIN is empty.\n");
    exit(2);
}

$dsn = sprintf(
    'pgsql:host=%s;port=%s;dbname=%s',
    $env('DB_HOST', 'db'),
    $env('DB_PORT', '5432'),
    $env('DB_NAME', 'cms')
);

try {
    $pdo = new PDO($dsn, $env('DB_USER', 'cms'), $env('DB_PASS', 'cms'), [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (PDOException $e) {
    fwrite(STDERR, "ERROR: cannot connect to PostgreSQL: " . $e->getMessage() . "\n");
    exit(1);
}

$setPassword = static function (PDO $pdo, string $login, string $password): void {
    $hash = password_hash($password, PASSWORD_DEFAULT);
    $stmt = $pdo->prepare('UPDATE users SET password = :password WHERE login = :login');
    $stmt->execute([':password' => $hash, ':login' => $login]);
};

try {
    $stmt = $pdo->prepare('SELECT id, password FROM users WHERE login = :login LIMIT 1');
    $stmt->execute([':login' => $login]);
    $row = $stmt->fetch();

    if ($row === false) {
        if ($password === '') {
            fwrite(STDERR, "ERROR: user '{$login}' does not exist and ADMIN_PASSWORD is not set.\n");
            fwrite(STDERR, "       Pass ADMIN_PASSWORD (optionally ADMIN_EMAIL) to create the admin.\n");
            exit(2);
        }

        $hash = password_hash($password, PASSWORD_DEFAULT);
        $insert = $pdo->prepare(
            'INSERT INTO users (login, email, password, role) VALUES (:login, :email, :password, :role)'
        );
        $insert->bindValue(':login', $login);
        if ($email === '') {
            $insert->bindValue(':email', null, PDO::PARAM_NULL);
        } else {
            $insert->bindValue(':email', $email);
        }
        $insert->bindValue(':password', $hash);
        $insert->bindValue(':role', 'admin');
        $insert->execute();

        fwrite(STDOUT, "Created admin user '{$login}'.\n");
        exit(0);
    }

    $current = (string) ($row['password'] ?? '');
    $isPlaceholder = ($current === '' || $current === $placeholder);

    if ($isPlaceholder) {
        if ($password === '') {
            fwrite(STDERR, "ERROR: admin user '{$login}' still has the placeholder password.\n");
            fwrite(STDERR, "       Pass ADMIN_PASSWORD to set a real password (exit code 2).\n");
            exit(2);
        }
        $setPassword($pdo, $login, $password);
        fwrite(STDOUT, "Set password for admin user '{$login}'.\n");
        exit(0);
    }

    if ($forceReset && $password !== '') {
        $setPassword($pdo, $login, $password);
        fwrite(STDOUT, "Reset password for admin user '{$login}' (FORCE_RESET=1).\n");
        exit(0);
    }

    if ($forceReset && $password === '') {
        fwrite(STDOUT, "FORCE_RESET=1 but ADMIN_PASSWORD is empty; password unchanged.\n");
        exit(0);
    }

    fwrite(STDOUT, "Admin user '{$login}' exists, password unchanged.\n");
    exit(0);
} catch (PDOException $e) {
    fwrite(STDERR, "ERROR: database operation failed: " . $e->getMessage() . "\n");
    exit(1);
}
