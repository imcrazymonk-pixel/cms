<?php
/**
 * Crypto — шифрование чувствительных настроек (API-ключи платёжных систем).
 *
 * AES-256-CBC через OpenSSL. Формат значения:
 *   enc:v1:<base64(iv)>.<base64(ciphertext)>
 *
 * Особенности:
 * - При пустой строке возвращается '' (ключ не задан).
 * - decrypt() прозрачно возвращает значения, НЕ имеющие префикса `enc:v1:`
 *   (легаси-данные, сохранённые до введения шифрования).
 * - Ключ берётся из APP_ENCRYPTION_KEY (config/config.php).
 */

class Crypto
{
    private const PREFIX = 'enc:v1:';

    /** Ключ шифрования: sha256 от APP_ENCRYPTION_KEY */
    private static function keyBytes(): string
    {
        static $key = null;
        if ($key === null) {
            $base = defined('APP_ENCRYPTION_KEY') ? (string)APP_ENCRYPTION_KEY : '';
            $key = hash('sha256', $base ?: 'hexacms-default-key-change-me', true);
        }
        return $key;
    }

    /**
     * Зашифровать строку.
     * @return string '' если вход пустой, иначе 'enc:v1:<iv>.<data>'
     */
    public static function encrypt(string $plain): string
    {
        if ($plain === '') {
            return '';
        }
        $iv = random_bytes(16);
        $cipher = openssl_encrypt($plain, 'AES-256-CBC', self::keyBytes(), OPENSSL_RAW_DATA, $iv);
        if ($cipher === false) {
            return '';
        }
        return self::PREFIX . base64_encode($iv) . '.' . base64_encode($cipher);
    }

    /**
     * Расшифровать строку.
     * @param string $value 'enc:v1:...' или легаси-значение без префикса
     * @return string расшифрованное значение (легаси возвращается как есть)
     */
    public static function decrypt(string $value): string
    {
        if ($value === '') {
            return '';
        }
        if (strpos($value, self::PREFIX) !== 0) {
            return $value;
        }
        $body = substr($value, strlen(self::PREFIX));
        [$ivB64, $dataB64] = array_pad(explode('.', $body, 2), 2, '');
        $iv = base64_decode($ivB64, true);
        $data = base64_decode($dataB64, true);
        if ($iv === false || $data === false || strlen($iv) !== 16) {
            return '';
        }
        $plain = openssl_decrypt($data, 'AES-256-CBC', self::keyBytes(), OPENSSL_RAW_DATA, $iv);
        return $plain === false ? '' : $plain;
    }

    /** Является ли значение зашифрованным */
    public static function isEncrypted(string $value): bool
    {
        return strpos($value, self::PREFIX) === 0;
    }

    /** Маска для отображения в UI: '••••' + последние 4 символа (не расшифровывая) */
    public static function mask(string $value): string
    {
        if ($value === '') {
            return '';
        }
        $tail = substr($value, -4);
        return '••••••••••••' . $tail;
    }
}