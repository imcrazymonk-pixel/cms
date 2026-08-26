<?php
/**
 * DataGrid — универсальный рендерер таблиц админки
 * Принимает готовые данные, НЕ выполняет запросы к БД.
 *
 * Использование:
 * echo DataGrid::render([
 *   'columns' => [
 *       ['key' => 'id', 'label' => 'ID', 'sortable' => true],
 *       ['key' => 'title', 'label' => 'Заголовок', 'sortable' => true],
 *   ],
 *   'rows' => $rows,
 *   'actions' => [
 *       ['label' => 'edit', 'url' => '/admin/posts/edit/{id}', 'icon' => 'edit'],
 *       ['label' => 'view', 'url' => '/post/{slug}', 'icon' => 'eye', 'target' => '_blank'],
 *   ],
 *   'pagination' => ['page' => 1, 'total' => 100, 'per_page' => 25, 'base_url' => '/admin/posts'],
 *   'empty' => ['title' => 'Нет данных', 'text' => 'Создайте первую запись', 'action' => '/admin/posts/create'],
 * ]);
 */
class DataGrid
{
    public static function render(array $config): string
    {
        $columns = $config['columns'] ?? [];
        $rows = $config['rows'] ?? [];
        $actions = $config['actions'] ?? [];
        $empty = $config['empty'] ?? [];
        $pagination = $config['pagination'] ?? null;

        if (!$columns) return '';

        $html = '<div class="dg-wrapper">';
        $html .= '<table class="dg-table"><thead><tr>';
        foreach ($columns as $col) {
            $label = TemplateEngine::e($col['label'] ?? $col['key']);
            if (!empty($col['sortable'])) {
                $html .= '<th class="sortable" data-sort="' . TemplateEngine::e($col['key']) . '">' . $label . '<span class="sort-indicator">↕</span></th>';
            } else {
                $html .= '<th>' . $label . '</th>';
            }
        }
        if ($actions) $html .= '<th class="dg-actions-col">Действия</th>';
        $html .= '</tr></thead><tbody>';

        if (empty($rows) && !empty($empty)) {
            $html .= '<tr><td colspan="' . (count($columns) + ($actions ? 1 : 0)) . '">';
            $html .= '<div class="empty-state">';
            if (!empty($empty['icon'])) $html .= '<div class="empty-icon">' . icon($empty['icon']) . '</div>';
            if (!empty($empty['title'])) $html .= '<h3>' . TemplateEngine::e($empty['title']) . '</h3>';
            if (!empty($empty['text'])) $html .= '<p>' . TemplateEngine::e($empty['text']) . '</p>';
            if (!empty($empty['action']) && !empty($empty['action_label'])) {
                $html .= '<a href="' . $empty['action'] . '" class="btn btn-primary">' . $empty['action_label'] . '</a>';
            }
            $html .= '</div></td></tr>';
        }

        foreach ($rows as $row) {
            $html .= '<tr>';
            foreach ($columns as $col) {
                $value = $row[$col['key']] ?? '';
                if (!empty($col['format']) && is_callable($col['format'])) {
                    $value = $col['format']($value, $row);
                } elseif (!empty($col['html'])) {
                    $value = $col['html']($row);
                } else {
                    $value = TemplateEngine::e((string)$value);
                }
                $html .= '<td>' . $value . '</td>';
            }
            if ($actions) {
                $html .= '<td class="actions">';
                foreach ($actions as $act) {
                    // Заменяем плейсхолдеры {field} значениями из строки (id, slug, ...)
                    $url = $act['url'] ?? '#';
                    $url = preg_replace_callback('/\{(\w+)\}/', function ($m) use ($row) {
                        return (string)($row[$m[1]] ?? $m[0]);
                    }, $url);
                    $target = !empty($act['target']) ? ' target="' . $act['target'] . '"' : '';
                    $title = $act['label'] ?? '';
                    $confirm = !empty($act['confirm']) ? ' data-confirm="' . TemplateEngine::e($act['confirm']) . '"' : '';
                    $html .= '<a href="' . $url . '" class="btn btn-sm btn-ghost" title="' . TemplateEngine::e($title) . '"' . $target . $confirm . '>';
                    if (!empty($act['icon'])) $html .= icon($act['icon']);
                    elseif ($act['label'] ?? '') $html .= TemplateEngine::e($act['label']);
                    $html .= '</a>';
                }
                $html .= '</td>';
            }
            $html .= '</tr>';
        }

        $html .= '</tbody></table>';

        if ($pagination) {
            $html .= self::renderPagination($pagination);
        }

        $html .= '</div>';
        return $html;
    }

    private static function renderPagination(array $p): string
    {
        $page = (int)($p['page'] ?? 1);
        $total = (int)($p['total'] ?? 0);
        $per = (int)($p['per_page'] ?? 25);
        $pages = max(1, (int)ceil($total / $per));
        $base = $p['base_url'] ?? '/admin';

        $html = '<div class="dg-pagination">';
        $html .= '<span>Стр. ' . $page . ' из ' . $pages . ' (всего ' . $total . ')</span>';
        $html .= '<div class="pagination-links">';
        for ($i = 1; $i <= $pages; $i++) {
            if ($pages > 10 && $i > 1 && $i < $pages - 1 && abs($i - $page) > 2) {
                if ($i == 2 || $i == $pages - 2) $html .= '<span>...</span>';
                continue;
            }
            $sep = strpos($base, '?') !== false ? '&' : '?';
            $url = $base . $sep . 'page=' . $i;
            $cls = $i === $page ? 'page-link active' : 'page-link';
            $html .= '<a href="' . $url . '" class="' . $cls . '">' . $i . '</a>';
        }
        $html .= '</div></div>';
        return $html;
    }
}
