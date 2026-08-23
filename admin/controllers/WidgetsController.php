<?php
/**
 * Контроллер виджетов в админке
 */

class AdminWidgetsController
{
    private $widget;

    public function __construct()
    {
        $this->widget = new Widget();
    }

    /**
     * Список виджетов по областям + форма добавления/редактирования
     */
    public function index()
    {
        Auth::requireAdmin();

        $widgets = $this->widget->getAll();
        $areas = $this->themeWidgetAreas();
        $editWidget = null;

        if (Request::get('edit')) {
            $editWidget = $this->widget->getById((int)Request::get('edit'));
        }

        $template = new TemplateEngine(ADMIN_PATH . '/templates');
        $template->set('title', 'Виджеты');
        $template->set('user', Auth::user());
        $template->set('widgets', $widgets);
        $template->set('areas', $areas);
        $template->set('editWidget', $editWidget);
        $template->setLayout('layouts/main');
        $template->display('widgets/index');
    }

    /**
     * Создать виджет
     */
    public function store()
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $data = $this->collectData();
        $this->widget->create($data);

        redirect('/admin/widgets?success=created');
    }

    /**
     * Обновить виджет
     */
    public function update($id)
    {
        Auth::requireAdmin();

        if (!verify_csrf()) {
            die('CSRF token invalid');
        }

        $data = $this->collectData();
        $this->widget->update((int)$id, $data);

        redirect('/admin/widgets?success=updated');
    }

    /**
     * Удалить виджет
     */
    public function delete($id)
    {
        Auth::requireAdmin();

        $this->widget->delete((int)$id);

        redirect('/admin/widgets?success=deleted');
    }

    /**
     * Собрать данные виджета из POST
     */
    private function collectData(): array
    {
        return [
            'area'       => (string)Request::post('area', 'footer'),
            'title'      => (string)Request::post('title', ''),
            'content'    => (string)Request::post('content', ''),
            'sort_order' => (int)Request::post('sort_order', 0),
        ];
    }

    /**
     * Области виджетов активной темы
     */
    private function themeWidgetAreas(): array
    {
        $config = get_theme_config();
        return $config['widget_areas'] ?? ['footer' => 'Подвал'];
    }
}
