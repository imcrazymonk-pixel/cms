<?php
/**
 * YooKassaClient — REST API клиент платёжной системы ЮKassa (yookassa.ru).
 *
 * Используется для ПУЛЛА платежей в финансовый модуль (аналогично Platega):
 * - список платежей с фильтром по дате создания
 * - пагинация через cursor
 * - разбор суммы, метода оплаты, описания плательщика
 *
 * API: https://yookassa.ru/developers/using-api/interaction-format
 * Аутентификация: HTTP Basic (shop_id : secret_key)
 */

class YooKassaClient
{
    private const API_BASE = 'https://api.yookassa.ru/v3';
    private const TIMEOUT = 30;

    private $shopId;
    private $secret;

    public function __construct(string $shopId, string $secret)
    {
        $this->shopId = $shopId;
        $this->secret = $secret;
    }

    /**
     * Получить список платежей за период (created_at).
     *
     * @param string      $since  ISO-8601 (например '2026-08-25T00:00:00.000Z')
     * @param string      $until  ISO-8601
     * @param string|null $cursor курсор пагинации (null = первая страница)
     * @return array Ассоциативный массив ответа API: items, next_cursor
     * @throws RuntimeException
     */
    public function listPayments(string $since, string $until, ?string $cursor = null): array
    {
        $params = [
            'created_at.gte' => $this->normalizeDate($since),
            'created_at.lte' => $this->normalizeDate($until),
            'limit' => '100',
        ];
        if ($cursor !== null && $cursor !== '') {
            $params['cursor'] = $cursor;
        }

        $query = http_build_query($params);
        $url = self::API_BASE . '/payments?' . $query;

        $json = $this->httpGet($url);
        $data = json_decode($json, true);
        if (!is_array($data)) {
            throw new RuntimeException('YooKassa: не удалось разобрать ответ API');
        }
        if (!empty($data['type']) && $data['type'] === 'error') {
            throw new RuntimeException('YooKassa API: ' . ($data['message'] ?? '') . (isset($data['description']) ? ' — ' . $data['description'] : ''));
        }
        return $data;
    }

    /**
     * Перебрать ВСЕ платежи за период (с учётом пагинации).
     * @return array[] массив платежей (каждый — ассоц. массив API)
     */
    public function fetchAllPayments(string $since, string $until): array
    {
        $all = [];
        $cursor = null;
        do {
            $data = $this->listPayments($since, $until, $cursor);
            $items = $data['items'] ?? [];
            foreach ($items as $item) {
                $all[] = $item;
            }
            $cursor = $data['next_cursor'] ?? null;
        } while ($cursor !== null && $cursor !== '');

        return $all;
    }

    /**
     * Проверить подключение: делаем один запрос за 1 день.
     * @return bool true если API отвечает без ошибки авторизации
     */
    public function testConnection(): bool
    {
        try {
            $now = gmdate('Y-m-d') . 'T00:00:00.000Z';
            $this->listPayments('2020-01-01T00:00:00.000Z', $now);
            return true;
        } catch (\Throwable $e) {
            return false;
        }
    }

    /**
     * Комиссии ЮKassa по способам оплаты (используются как умолчания).
     * Ключи — payment_method.type, значение — процент комиссии.
     */
    public static function defaultCommissions(): array
    {
        return [
            'bank_card'    => 3.0,  // банковские карты
            'sbp'          => 0.5,  // Система быстрых платежей
            'yoo_money'    => 3.0,  // ЮMoney
            'sberbank'     => 3.0,  // Сбербанк Онлайн / SberPay
            'tinkoff_bank' => 3.0,  // Тинькофф
            'mobile'       => 6.0,  // мобильные платежи
            'cash'         => 3.0,  // наличные
            'qiwi'         => 3.0,  // Qiwi (устар.)
        ];
    }

    /**
     * Человекочитаемые названия способов оплаты.
     */
    public static function methodLabel(string $type): string
    {
        $labels = [
            'bank_card'    => 'Банковская карта',
            'sbp'          => 'СБП',
            'yoo_money'    => 'ЮMoney',
            'sberbank'     => 'Сбербанк',
            'tinkoff_bank' => 'Тинькофф',
            'mobile'       => 'Мобильный платёж',
            'cash'         => 'Наличные',
            'qiwi'         => 'Qiwi',
            'alfa_bank'    => 'Альфа-Банк',
            'b2b_sberbank' => 'СберБизнес',
            'installment'  => 'Рассрочка',
            'wechat'       => 'WeChat',
        ];
        return $labels[$type] ?? $type;
    }

    /**
     * Методы оплаты, показываемые в настройках комиссии.
     */
    public static function supportedMethods(): array
    {
        return array_keys(self::defaultCommissions());
    }

    private function normalizeDate(string $date): string
    {
        $ts = strtotime($date);
        return $ts !== false ? gmdate('Y-m-d\TH:i:s.000\Z', $ts) : $date;
    }

    private function authHeader(): string
    {
        return 'Authorization: Basic ' . base64_encode($this->shopId . ':' . $this->secret);
    }

    private function httpGet(string $url): string
    {
        $headers = [
            $this->authHeader(),
            'Idempotence-Key: ' . bin2hex(random_bytes(16)),
            'User-Agent: HexaVeil-CMS/1.0 (PHP)',
            'Accept: application/json',
        ];

        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt_array($ch, [
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_HTTPHEADER => $headers,
                CURLOPT_TIMEOUT => self::TIMEOUT,
                CURLOPT_SSL_VERIFYPEER => true,
            ]);
            $resp = curl_exec($ch);
            $err = curl_error($ch);
            $code = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
            curl_close($ch);
            if ($resp === false) {
                throw new RuntimeException('YooKassa HTTP: ' . $err);
            }
            $this->assertHttpOk($code, $url, $resp);
            return $resp;
        }

        $ctx = stream_context_create([
            'http' => [
                'method' => 'GET',
                'header' => implode("\r\n", $headers) . "\r\n",
                'timeout' => self::TIMEOUT,
                'ignore_errors' => true,
            ],
            'ssl' => [
                'verify_peer' => true,
                'verify_peer_name' => true,
            ],
        ]);
        $resp = @file_get_contents($url, false, $ctx);
        if ($resp === false) {
            throw new RuntimeException('YooKassa HTTP: unable to fetch ' . $url);
        }
        $code = 200;
        if (isset($http_response_header) && preg_match('/HTTP\/\S+\s+(\d+)/', $http_response_header[0] ?? '', $m)) {
            $code = (int)$m[1];
        }
        $this->assertHttpOk($code, $url, $resp);
        return $resp;
    }

    private function assertHttpOk(int $code, string $url, string $body): void
    {
        if ($code >= 200 && $code < 300) {
            return;
        }
        $apiError = '';
        $decoded = json_decode($body, true);
        if (is_array($decoded)) {
            $apiError = ($decoded['message'] ?? '') . (isset($decoded['description']) ? ' — ' . $decoded['description'] : '');
        }
        if ($code === 401 || $code === 403) {
            throw new RuntimeException('YooKassa: неверные shop_id или secret_key (HTTP ' . $code . ')');
        }
        throw new RuntimeException('YooKassa API HTTP ' . $code . ($apiError ? ': ' . $apiError : ''));
    }
}