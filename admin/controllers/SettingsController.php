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

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Настройки');
        $template->set('user', Auth::user());
        $template->set('settings', $settings);
        $template->set('finSettings', $finSettings);
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

        redirect('/admin/settings?tab=integrations&success=updated');
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
            'platega_merchant_id',
            'platega_days_back',
            'platega_auto_sync',
            'yookassa_shop_id',
            'yookassa_days_back',
            'yookassa_auto_sync',
        ];

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

            // Обычные строковые настройки
            if (in_array($key, $stringKeys, true)) {
                $fin->set($key, (string)$value);
            }
        }
    }
}