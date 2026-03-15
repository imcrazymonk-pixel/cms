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

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Настройки');
        $template->set('user', Auth::user());
        $template->set('settings', $settings);
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

        $this->setting->setMultiple($settingsData);

        redirect('/admin/settings?success=updated');
    }
}
