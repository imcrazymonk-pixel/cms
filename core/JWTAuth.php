<?php
/**
 * JWT Authentication — zero dependencies, pure PHP 8.1
 * 
 * Uses HMAC-SHA256 for signing. The secret is read from:
 *   1. env JWT_SECRET (highest priority)
 *   2. env APP_ENCRYPTION_KEY (fallback)
 * 
 * Token payload:
 *   - sub  (user ID)
 *   - role (user role)
 *   - iat  (issued at)
 *   - exp  (expiration, default 24h)
 * 
 * Usage:
 *   $token = JWTAuth::generateToken($user);
 *   $decoded = JWTAuth::validateToken($token);  // returns payload or null
 */

class JWTAuth
{
    private const ALGORITHM = 'sha256';
    private const TOKEN_TTL = 86400; // 24 hours

    /**
     * Generate a JWT token for a user
     */
    public static function generateToken(array $user): string
    {
        $now = time();
        $payload = [
            'sub'  => $user['id'],
            'login' => $user['login'] ?? '',
            'role' => $user['role'] ?? 'admin',
            'iat'  => $now,
            'exp'  => $now + self::TOKEN_TTL,
        ];

        $header = self::base64urlEncode(json_encode([
            'alg' => 'HS256',
            'typ' => 'JWT',
        ]));

        $payloadEncoded = self::base64urlEncode(json_encode($payload));
        $signature = self::sign("{$header}.{$payloadEncoded}");

        return "{$header}.{$payloadEncoded}.{$signature}";
    }

    /**
     * Validate a JWT token and return its payload, or null on failure
     */
    public static function validateToken(string $token): ?array
    {
        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            return null;
        }

        [$header, $payload, $signature] = $parts;

        // Verify signature
        $expected = self::sign("{$header}.{$payload}");
        if (!hash_equals($expected, $signature)) {
            return null;
        }

        // Decode payload
        $data = json_decode(self::base64urlDecode($payload), true);
        if (!$data || !isset($data['exp'], $data['sub'])) {
            return null;
        }

        // Check expiration
        if ($data['exp'] < time()) {
            return null;
        }

        return $data;
    }

    /**
     * Refresh a token: generate a new one from a valid token's payload
     */
    public static function refreshToken(string $token): ?string
    {
        $payload = self::validateToken($token);
        if (!$payload) {
            return null;
        }

        return self::generateToken([
            'id'    => $payload['sub'],
            'login' => $payload['login'] ?? '',
            'role'  => $payload['role'] ?? 'admin',
        ]);
    }

    // ─── Private helpers ───────────────────────────────────────────────

    private static function getSecret(): string
    {
        $secret = getenv('JWT_SECRET') ?: (defined('APP_ENCRYPTION_KEY') ? APP_ENCRYPTION_KEY : '');
        if ($secret === '') {
            $secret = 'hexaveil-cms-default-jwt-secret-change-in-production';
        }
        return $secret;
    }

    private static function sign(string $data): string
    {
        return self::base64urlEncode(
            hash_hmac(self::ALGORITHM, $data, self::getSecret(), true)
        );
    }

    private static function base64urlEncode(string $data): string
    {
        return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
    }

    private static function base64urlDecode(string $data): string
    {
        $remainder = strlen($data) % 4;
        if ($remainder) {
            $data .= str_repeat('=', 4 - $remainder);
        }
        return base64_decode(strtr($data, '-_', '+/'));
    }
}