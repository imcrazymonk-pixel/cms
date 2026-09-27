<?php
/**
 * Контроллер настроек в админке
 */

class AdminSettingsController
{
    private $setting;

    public function __construct()
    {
        $this->setting = new Setting();
    }

    /**
     * Просмотр и редактирование настроек
     */
    public function index()
    {
        Auth::requireAdmin();

        $settings = $this->setting->getAll();
        $finSettings = (new FinSetting())->getAll();
        $dockerConfig = $this->loadJsonSetting('docker_config', [
            'docker_ssh_host' => 'localhost',
            'docker_ssh_user' => 'kilo',
            'docker_ssh_port' => 356,
            'docker_containers' => '',
            'docker_lines' => 100,
        ]);
        $lokiConfig = $this->loadJsonSetting('loki_config', [
            'loki_url' => '',
            'loki_user' => '',
            'loki_password' => '',
            'loki_query' => '{job="varlog"}',
            'loki_limit' => 100,
        ]);

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Настройки');
        $template->set('user', Auth::user());
        $template->set('settings', $settings);
        $template->set('finSettings', $finSettings);
        $template->set('dockerConfig', $dockerConfig);
        $template->set('lokiConfig', $lokiConfig);
        $template->setLayout('layouts/main');
        $template->display('settings/index');
    }

    /**
     * Сохранение настроек
     */
    public function update()
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $settingsData = Request::post('settings', []);
        if (is_array($settingsData)) {
            $this->setting->setMultiple($settingsData);
        }

        $finData = Request::post('fin_settings', []);
        if (is_array($finData) && count($finData) > 0) {
            $this->saveFinSettings($finData);
        }

        // Docker / Loki config (JSON blobs)
        $dockerRaw = Request::post('docker_config', []);
        if (is_array($dockerRaw)) {
            $this->setting->set('docker_config', json_encode($dockerRaw, JSON_UNESCAPED_UNICODE));
        }
        $lokiRaw = Request::post('loki_config', []);
        if (is_array($lokiRaw)) {
            // Не перезаписываем пароль пустым значением
            if (empty($lokiRaw['loki_password'])) {
                unset($lokiRaw['loki_password']);
            }
            $this->setting->set('loki_config', json_encode($lokiRaw, JSON_UNESCAPED_UNICODE));
        }

        $tab = Request::post('tab', 'basic');
        if (!in_array($tab, ['basic', 'appearance', 'finance', 'integrations', 'logs'], true)) {
            $tab = 'basic';
        }
        redirect('/admin/settings?tab=' . urlencode($tab) . '&success=updated');
    }

    /**
     * Загрузить JSON-настройку из таблицы settings.
     */
    private function loadJsonSetting(string $key, array $defaults): array
    {
        try {
            $row = $this->setting->get($key);
            if ($row) {
                $decoded = json_decode($row, true);
                if (is_array($decoded)) {
                    return array_merge($defaults, $decoded);
                }
            }
        } catch (\Throwable $e) {
            // defaults
        }
        return $defaults;
    }

    /**
     * Сохранение настроек платёжных интеграций (таблица fin_settings).
     * Секреты шифруются через Crypto::encrypt(), пустое значение — НЕ перезаписывает
     * существующий ключ. Комиссии ЮKassa собираются в JSON-объект из ограниченного
     * набора методов (YooKassaClient::supportedMethods()).
     *
     * @param array $finData массив ключ => значение из POST
     */
    private function saveFinSettings(array $finData): void
    {
        $fin = new FinSetting();
        $existing = $fin->getAll();

        $secretKeys = ['platega_secret', 'yookassa_secret_key'];
        $stringKeys = [
            // Общие настройки финансов
            'currency',
            'auto_refresh',
            'avg_period',
            // Platega
            'platega_merchant_id',
            'platega_days_back',
            'platega_auto_sync',
            // YooKassa
            'yookassa_shop_id',
            'yookassa_days_back',
            'yookassa_auto_sync',
        ];

        // Ключи, хранящиеся как JSON-массивы (из формы приходит строка через запятую → JSON)
        $jsonArrayKeys = [
            'avg_exclude_categories',
            'avg_exclude_income_keywords',
            'avg_exclude_expense_keywords',
            'quick_categories',
            'quick_participants',
        ];

        // Целочисленные настройки
        $intKeys = ['decimals'];

        foreach ($finData as $key => $value) {
            // Секретные ключи: пустое значение не трогаем, непустое шифруем
            if (in_array($key, $secretKeys, true)) {
                $val = trim((string)$value);
                if ($val === '') {
                    continue;
                }
                $fin->set($key, Crypto::encrypt($val));
                continue;
            }

            // Комиссии ЮKassa: массив методов → JSON-объект
            if ($key === 'yookassa_commissions') {
                if (!is_array($value)) {
                    continue;
                }
                $oldRaw = isset($existing[$key]) ? (string)$existing[$key] : '';
                $oldDecoded = ($oldRaw !== '') ? json_decode($oldRaw, true) : null;
                if (!is_array($oldDecoded)) {
                    $oldDecoded = YooKassaClient::defaultCommissions();
                }
                $commissions = [];
                foreach (YooKassaClient::supportedMethods() as $method) {
                    if (isset($value[$method]) && $value[$method] !== '') {
                        $num = max(0.0, min(50.0, (float)$value[$method]));
                        $commissions[$method] = round($num, 2);
                    } else {
                        $commissions[$method] = isset($oldDecoded[$method]) ? (float)$oldDecoded[$method] : 0.0;
                    }
                }
                $fin->set($key, json_encode($commissions, JSON_UNESCAPED_UNICODE));
                continue;
            }

            // JSON-массивы (строка через запятую из textarea/input → JSON array)
            if (in_array($key, $jsonArrayKeys, true)) {
                $arr = array_values(array_filter(array_map('trim', explode(',', (string)$value)), function ($s) {
                    return $s !== '';
                }));
                $fin->set($key, json_encode($arr, JSON_UNESCAPED_UNICODE));
                continue;
            }

            // Целочисленные
            if (in_array($key, $intKeys, true)) {
                $fin->set($key, (string)(int)$value);
                continue;
            }

            // Обычные строковые настройки
            if (in_array($key, $stringKeys, true)) {
                $fin->set($key, (string)$value);
            }
        }
    }
}