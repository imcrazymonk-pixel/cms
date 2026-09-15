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
        $selectable = !empty($config['selectable']);
        $bulkActions = $config['bulk_actions'] ?? [];
        $kebab = !empty($config['kebab']); // wrap actions in kebab dropdown
        $rowId = $config['row_id'] ?? 'id'; // primary key field

        if (!$columns) return '';

        $colCount = count($columns);
        if ($selectable) $colCount++;
        if ($actions) $colCount++;

        $html = '<div class="dg-wrapper">';

        // Mass actions bar (Remnawave-style)
        if ($selectable && $bulkActions) {
            $html .= '<div class="dg-bulk-bar" id="dgBulkBar" style="display:none;">';
            $html .= '<span class="dg-bulk-count" id="dgBulkCount">Выбрано: 0</span>';
            foreach ($bulkActions as $ba) {
                $cls = 'btn btn-sm ' . ($ba['variant'] ?? 'btn-secondary');
                $html .= '<button type="button" class="' . $cls . '" data-bulk-action="' . TemplateEngine::e($ba['action'] ?? '') . '">';
                if (!empty($ba['icon'])) $html .= icon($ba['icon']) . ' ';
                $html .= TemplateEngine::e($ba['label'] ?? '') . '</button>';
            }
            $html .= '<button type="button" class="btn btn-sm btn-ghost" data-bulk-cancel id="dgBulkCancel">✕ Отмена</button>';
            $html .= '</div>';
        }

        $html .= '<table class="dg-table"><thead><tr>';
        if ($selectable) {
            $html .= '<th class="dg-check-col"><input type="checkbox" id="dgSelectAll" class="dg-checkbox"></th>';
        }
        foreach ($columns as $col) {
            $label = TemplateEngine::e($col['label'] ?? $col['key']);
            if (!empty($col['sortable'])) {
                $html .= '<th class="sortable" data-sort="' . TemplateEngine::e($col['key']) . '">' . $label . '<span class="sort-indicator">↕</span></th>';
            } else {
                $html .= '<th>' . $label . '</th>';
            }
        }
        if ($actions) $html .= '<th class="dg-actions-col">' . ($kebab ? '' : 'Действия') . '</th>';
        $html .= '</tr></thead><tbody>';

        if (empty($rows) && !empty($empty)) {
            $html .= '<tr><td colspan="' . $colCount . '">';
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
            $rid = $row[$rowId] ?? '';
            $html .= '<tr data-row-id="' . TemplateEngine::e((string)$rid) . '">';
            if ($selectable) {
                $html .= '<td class="dg-check-col"><input type="checkbox" class="dg-checkbox dg-row-cb" value="' . TemplateEngine::e((string)$rid) . '"></td>';
            }
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
                if ($kebab) {
                    // Kebab dropdown menu
                    $html .= '<td class="dg-actions-col"><div class="dropdown dg-kebab">';
                    $html .= '<button type="button" class="btn-icon-action" data-dropdown-toggle><span class="dg-kebab-dots">⋮</span></button>';
                    $html .= '<div class="dropdown-menu dg-kebab-menu">';
                    foreach ($actions as $act) {
                        $url = $act['url'] ?? '#';
                        $url = preg_replace_callback('/\{(\w+)\}/', function ($m) use ($row) {
                            return (string)($row[$m[1]] ?? $m[0]);
                        }, $url);
                        $target = !empty($act['target']) ? ' target="' . $act['target'] . '"' : '';
                        $title = $act['label'] ?? '';
                        $confirm = !empty($act['confirm']) ? ' data-confirm="' . TemplateEngine::e($act['confirm']) . '"' : '';
                        $colorClass = ($act['label'] ?? '') === 'delete' ? ' dg-kebab-danger' : '';
                        $html .= '<a href="' . $url . '" class="dg-kebab-item' . $colorClass . '"' . $target . $confirm . '>';
                        if (!empty($act['icon'])) $html .= icon($act['icon']) . ' ';
                        $html .= TemplateEngine::e($title) . '</a>';
                        if (($act['label'] ?? '') === 'delete' && $act !== end($actions)) {
                            $html .= '<div class="dg-kebab-sep"></div>';
                        }
                    }
                    $html .= '</div></div></td>';
                } else {
                    // Inline ghost buttons
                    $html .= '<td class="dg-actions-cell">';
                    foreach ($actions as $act) {
                        $url = $act['url'] ?? '#';
                        $url = preg_replace_callback('/\{(\w+)\}/', function ($m) use ($row) {
                            return (string)($row[$m[1]] ?? $m[0]);
                        }, $url);
                        $target = !empty($act['target']) ? ' target="' . $act['target'] . '"' : '';
                        $title = $act['label'] ?? '';
                        $confirm = !empty($act['confirm']) ? ' data-confirm="' . TemplateEngine::e($act['confirm']) . '"' : '';
                        $html .= '<a href="' . $url . '" class="btn-icon-action' . (($act['label'] ?? '') === 'delete' ? ' danger' : '') . '" title="' . TemplateEngine::e($title) . '"' . $target . $confirm . '>';
                        if (!empty($act['icon'])) $html .= icon($act['icon']);
                        elseif ($act['label'] ?? '') $html .= TemplateEngine::e($act['label']);
                        $html .= '</a>';
                    }
                    $html .= '</td>';
                }
            }
            $html .= '</tr>';
        }

        $html .= '</tbody></table>';

        if ($pagination) {
            $html .= self::renderPagination($pagination);
        }

        $html .= '</div>';

        // Output mass-actions JS once (singleton guard via request counter)
        if ($selectable && $bulkActions && !defined('DATAGRID_BULK_JS')) {
            define('DATAGRID_BULK_JS', true);
            $html .= self::bulkJs();
        }

        return $html;
    }

    private static function bulkJs(): string
    {
        return '<script>
(function() {
    var selectAll = document.getElementById("dgSelectAll");
    var bulkBar = document.getElementById("dgBulkBar");
    var bulkCount = document.getElementById("dgBulkCount");
    var cancelBtn = document.getElementById("dgBulkCancel");

    function updateBulkBar() {
        var cbs = document.querySelectorAll(".dg-row-cb:checked");
        var count = cbs.length;
        if (count > 0) {
            bulkBar.style.display = "flex";
            bulkCount.textContent = "Выбрано: " + count;
        } else {
            bulkBar.style.display = "none";
            if (selectAll) selectAll.checked = false;
        }
    }

    if (selectAll) {
        selectAll.addEventListener("change", function() {
            var checked = this.checked;
            document.querySelectorAll(".dg-row-cb").forEach(function(cb) { cb.checked = checked; });
            updateBulkBar();
        });
    }

    document.querySelectorAll(".dg-row-cb").forEach(function(cb) {
        cb.addEventListener("change", updateBulkBar);
    });

    if (cancelBtn) {
        cancelBtn.addEventListener("click", function() {
            document.querySelectorAll(".dg-row-cb").forEach(function(cb) { cb.checked = false; });
            if (selectAll) selectAll.checked = false;
            updateBulkBar();
        });
    }

    // Bulk action buttons dispatch custom events
    document.querySelectorAll("[data-bulk-action]").forEach(function(btn) {
        btn.addEventListener("click", function() {
            var action = this.getAttribute("data-bulk-action");
            var selected = [];
            document.querySelectorAll(".dg-row-cb:checked").forEach(function(cb) {
                selected.push(cb.value);
            });
            if (selected.length === 0) return;
            var evt = new CustomEvent("dg-bulk-action", {
                detail: { action: action, ids: selected }
            });
            document.querySelector(".dg-wrapper").dispatchEvent(evt);
        });
    });
})();
</script>';
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
