<?php
/**
 * FinTransaction — модель транзакций финансового модуля (таблица fin_transactions)
 * Порт логики из FIN (Flask/SQLite) на PDO/MySQL CMS.
 * Типы: 'income' | 'expense'.
 */

class FinTransaction
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    /* ─────────────────────────────── CRUD ─────────────────────────────── */

    /**
     * Создать транзакцию. Поля: date, type, category, participant, amount, description, record_id (необязательно).
     * @return int id
     */
    public function create(array $d): int
    {
        $data = [
            'date' => $d['date'],
            'type' => $d['type'],
            'category' => $d['category'],
            'participant' => !empty($d['participant']) ? $d['participant'] : null,
            'amount' => (float)$d['amount'],
            'description' => $d['description'] ?? '',
        ];
        if (!empty($d['record_id'])) {
            $data['record_id'] = $d['record_id'];
        }
        return $this->db->insert('fin_transactions', $data);
    }

    /**
     * Обновить транзакцию
     */
    public function update(int $id, array $d): bool
    {
        $data = [
            'date' => $d['date'],
            'type' => $d['type'],
            'category' => $d['category'],
            'participant' => !empty($d['participant']) ? $d['participant'] : null,
            'amount' => (float)$d['amount'],
            'description' => $d['description'] ?? '',
        ];
        $this->db->update('fin_transactions', $data, 'id = :id', ['id' => $id]);
        return true;
    }

    /**
     * Удалить транзакцию
     */
    public function delete(int $id): bool
    {
        $this->db->delete('fin_transactions', 'id = ?', [$id]);
        return true;
    }

    /**
     * Найти по id
     */
    public function find(int $id): ?array
    {
        return $this->db->fetch('SELECT * FROM fin_transactions WHERE id = ?', [$id]);
    }

    /* ─────────────────────────── Фильтрация/таблица ─────────────────────────── */

    /**
     * Построить WHERE/params из фильтров.
     * Допустимые ключи: month 'YYYY-MM', since 'YYYY-MM-DD', until 'YYYY-MM-DD',
     * type 'income'|'expense', q — поиск по category/participant/description.
     */
    private function buildFilters(array $f): array
    {
        $where = [];
        $params = [];

        if (!empty($f['month']) && preg_match('/^\d{4}-\d{2}$/', (string)$f['month'])) {
            $where[] = 'date LIKE ?';
            $params[] = $f['month'] . '%';
        }
        if (!empty($f['since']) && preg_match('/^\d{4}-\d{2}-\d{2}$/', (string)$f['since'])) {
            $where[] = 'date >= ?';
            $params[] = $f['since'];
        }
        if (!empty($f['until']) && preg_match('/^\d{4}-\d{2}-\d{2}$/', (string)$f['until'])) {
            $where[] = 'date <= ?';
            $params[] = $f['until'];
        }
        if (!empty($f['type']) && in_array($f['type'], ['income', 'expense'], true)) {
            $where[] = 'type = ?';
            $params[] = $f['type'];
        }
        if (!empty($f['q'])) {
            $where[] = '(category LIKE ? OR participant LIKE ? OR description LIKE ?)';
            $like = '%' . $f['q'] . '%';
            array_push($params, $like, $like, $like);
        }

        return [$where ? ' WHERE ' . implode(' AND ', $where) : '', $params];
    }

    /**
     * Страница транзакций.
     * @return array ['rows' => [...], 'total' => int]
     */
    public function getAll(array $filters, int $page = 1, int $perPage = 25, string $sort = 'date', string $order = 'desc'): array
    {
        [$where, $params] = $this->buildFilters($filters);

        $total = (int)$this->db->fetchOne('SELECT COUNT(*) FROM fin_transactions' . $where, $params);

        $sortCols = ['date', 'amount', 'category', 'participant', 'type'];
        if (!in_array($sort, $sortCols, true)) {
            $sort = 'date';
        }
        $orderSql = strtolower($order) === 'asc' ? 'ASC' : 'DESC';
        $sortSql = in_array($sort, ['date', 'amount'], true) ? $sort : '`' . $sort . '`';

        $offset = max(0, ((int)$page - 1) * (int)$perPage);
        $limit = max(1, min(500, (int)$perPage));

        $rows = $this->db->fetchAll(
            "SELECT * FROM fin_transactions{$where} ORDER BY {$sortSql} {$orderSql}, id DESC LIMIT {$offset}, {$limit}",
            $params
        );

        return ['rows' => $rows, 'total' => $total];
    }

    /**
     * Все строки по фильтрам (без лимита) — для экспорта CSV.
     */
    public function getFilteredAll(array $filters): array
    {
        [$where, $params] = $this->buildFilters($filters);
        return $this->db->fetchAll(
            'SELECT * FROM fin_transactions' . $where . ' ORDER BY date ASC, id ASC',
            $params
        );
    }

    /**
     * Проверить существование дубликата (date + type + participant + amount)
     */
    public function findDuplicate(array $d): bool
    {
        $count = (int)$this->db->fetchOne(
            'SELECT COUNT(*) FROM fin_transactions WHERE `date` = ? AND `type` = ? AND COALESCE(`participant`, \'\') = ? AND `amount` = ?',
            [$d['date'], $d['type'], (string)($d['participant'] ?? ''), $d['amount']]
        );
        return $count > 0;
    }

    /* ─────────────────────────── Сводка и средние ─────────────────────────── */

    /**
     * Итоговая сводка по ВСЕМ транзакциям (глобально, как в FIN),
     * с учётом общих исключений avg_exclude_categories.
     */
    public function getSummary(): array
    {
        $settings = (new FinSetting())->getAll();
        $genExcl = $this->keywordsFrom($settings['avg_exclude_categories'] ?? '[]');

        $rows = $this->db->fetchAll('SELECT type, category, participant, description, amount FROM fin_transactions');
        $income = 0.0;
        $expense = 0.0;
        $count = 0;
        foreach ($rows as $r) {
            if ($this->isExcluded($r, $genExcl)) {
                continue;
            }
            $count++;
            if ($r['type'] === 'income') {
                $income += (float)$r['amount'];
            } else {
                $expense += (float)$r['amount'];
            }
        }
        $income = round($income, 2);
        $expense = round($expense, 2);

        return [
            'income' => $income,
            'expense' => $expense,
            'balance' => round($income - $expense, 2),
            'count' => $count,
        ];
    }

    /**
     * Средние значения по периодам (порт build_summary из FIN).
     * Общие исключения применяются к суммам и средним;
     * income/expense-специфичные исключения — только к средним.
     */
    public function getAverages(): array
    {
        $settings = (new FinSetting())->getAll();
        $genExcl = $this->keywordsFrom($settings['avg_exclude_categories'] ?? '[]');
        $incExcl = $this->keywordsFrom($settings['avg_exclude_income_keywords'] ?? '[]');
        $expExcl = $this->keywordsFrom($settings['avg_exclude_expense_keywords'] ?? '[]');

        $rows = $this->db->fetchAll('SELECT date, type, category, participant, description, amount FROM fin_transactions');

        $income = 0.0;
        $expense = 0.0;
        $avgIncome = 0.0;
        $avgExpense = 0.0;
        $dates = [];
        foreach ($rows as $r) {
            $isIncome = $r['type'] === 'income';
            $dates[$r['date']] = true;

            // Суммы — только общие исключения
            if (!$this->isExcluded($r, $genExcl)) {
                if ($isIncome) {
                    $income += (float)$r['amount'];
                } else {
                    $expense += (float)$r['amount'];
                }
            }

            // Средние — дополнительно исключаем по настройкам типа
            if ($isIncome) {
                if (!$this->isExcluded($r, $genExcl) && !$this->isExcluded($r, $incExcl)) {
                    $avgIncome += (float)$r['amount'];
                }
            } else {
                if (!$this->isExcluded($r, $genExcl) && !$this->isExcluded($r, $expExcl)) {
                    $avgExpense += (float)$r['amount'];
                }
            }
        }

        $dateList = array_keys($dates);
        sort($dateList);
        $n = count($dateList);

        $days = 0;
        if ($n > 1) {
            $days = (int)((strtotime($dateList[$n - 1]) - strtotime($dateList[0])) / 86400) + 1;
        } elseif ($n === 1) {
            $days = 1;
        }

        $weeks = $days ? max(1, (int)ceil($days / 7)) : 1;
        $months = $this->uniquePrefixes($dateList, 7) ?: 1;
        $years = $this->uniquePrefixes($dateList, 4) ?: 1;

        return [
            'income' => round($income, 2),
            'expense' => round($expense, 2),
            'balance' => round($income - $expense, 2),
            'total' => count($rows),
            'avg_days' => $days,
            'avg_weeks' => $weeks,
            'avg_months' => $months,
            'avg_years' => $years,
            'avg_income' => [
                'day' => $days ? round($avgIncome / $days, 2) : 0,
                'week' => $weeks ? round($avgIncome / $weeks, 2) : 0,
                'month' => $months ? round($avgIncome / $months, 2) : 0,
                'year' => $years ? round($avgIncome / $years, 2) : 0,
            ],
            'avg_expense' => [
                'day' => $days ? round($avgExpense / $days, 2) : 0,
                'week' => $weeks ? round($avgExpense / $weeks, 2) : 0,
                'month' => $months ? round($avgExpense / $months, 2) : 0,
                'year' => $years ? round($avgExpense / $years, 2) : 0,
            ],
        ];
    }

    /* ─────────────────────────── Графики (порт aggregator.py) ─────────────────────────── */

    /**
     * Серии для графика по шкалам day/week/month/year, с учётом фильтров
     * (month/type/q/since/until — как в FIN: charts строятся по отфильтрованным данным).
     * @return array ['monthly'=>[], 'daily'=>[], 'weekly'=>[], 'yearly'=>[]]
     */
    public function getChartSeries(array $filters): array
    {
        [$where, $params] = $this->buildFilters($filters);
        $rows = $this->db->fetchAll(
            'SELECT date, type, amount FROM fin_transactions' . $where . ' ORDER BY date ASC',
            $params
        );

        $daily = FinAggregator::groupDaily($rows);
        $monthly = FinAggregator::groupMonthly($rows);
        $weekly = FinAggregator::groupWeekly($rows);
        $yearly = FinAggregator::groupYearly($rows);

        $this->attachBalances($daily, $monthly, $weekly, $yearly);

        return [
            'monthly' => $monthly,
            'daily' => $daily,
            'weekly' => $weekly,
            'yearly' => $yearly,
        ];
    }

    /**
     * Кумулятивный баланс (как в FIN): накопительная сумма по всем дням,
     * для периода берётся баланс его последнего дня.
     */
    private function attachBalances(array &$daily, array &$monthly, array &$weekly, array &$yearly): void
    {
        $cum = 0.0;
        $cumByDate = [];
        foreach ($daily as $i => $d) {
            $cum += $d['income'] - $d['expense'];
            $daily[$i]['balance'] = round($cum, 2);
            $cumByDate[$d['key']] = round($cum, 2);
        }

        $this->attachScaleBalance($monthly, 'month', $cumByDate);
        $this->attachScaleBalance($weekly, 'week', $cumByDate);
        $this->attachScaleBalance($yearly, 'year', $cumByDate);
    }

    private function attachScaleBalance(array &$items, string $scale, array $cumByDate): void
    {
        $endBal = [];
        foreach ($cumByDate as $date => $bal) {
            $endBal[$this->periodKey($date, $scale)] = $bal;
        }
        foreach ($items as $i => $item) {
            $items[$i]['balance'] = $endBal[$item['key']] ?? null;
        }
    }

    private function periodKey(string $date, string $scale): string
    {
        if ($scale === 'month') {
            return substr($date, 0, 7);
        }
        if ($scale === 'year') {
            return substr($date, 0, 4);
        }
        if ($scale === 'week') {
            return (new DateTime($date))->format('o-\WW');
        }
        return $date;
    }

    /**
     * Разбивка по категориям (для структуры расходов), с учётом фильтров.
     */
    public function getCategories(array $filters): array
    {
        [$where, $params] = $this->buildFilters($filters);
        $rows = $this->db->fetchAll(
            'SELECT type, category, amount FROM fin_transactions' . $where,
            $params
        );
        $agg = [];
        foreach ($rows as $r) {
            $key = $r['category'] . '|' . $r['type'];
            if (!isset($agg[$key])) {
                $agg[$key] = ['category' => $r['category'], 'type' => $r['type'], 'amount' => 0.0];
            }
            $agg[$key]['amount'] += (float)$r['amount'];
        }
        usort($agg, function ($a, $b) {
            return $b['amount'] <=> $a['amount'];
        });
        foreach ($agg as &$row) {
            $row['amount'] = round($row['amount'], 2);
        }
        return array_values($agg);
    }

    /**
     * Аномальные транзакции: amount > среднего по своему типу * threshold.
     * Возвращает массив id.
     */
    public function getAnomalies(array $filters, float $threshold = 2.0): array
    {
        [$where, $params] = $this->buildFilters($filters);
        $rows = $this->db->fetchAll(
            'SELECT id, type, amount FROM fin_transactions' . $where,
            $params
        );

        $sum = [];
        $cnt = [];
        foreach ($rows as $r) {
            $sum[$r['type']] = ($sum[$r['type']] ?? 0) + (float)$r['amount'];
            $cnt[$r['type']] = ($cnt[$r['type']] ?? 0) + 1;
        }
        $avg = [];
        foreach ($sum as $t => $s) {
            $avg[$t] = $cnt[$t] ? $s / $cnt[$t] : 0.0;
        }

        $out = [];
        foreach ($rows as $r) {
            if ($avg[$r['type']] > 0 && (float)$r['amount'] > $avg[$r['type']] * $threshold) {
                $out[] = (int)$r['id'];
            }
        }
        return $out;
    }

    /**
     * Уникальные значения колонки (для автокомплита). Белый список: category, participant.
     */
    public function distinctValues(string $column): array
    {
        $allowed = ['category', 'participant'];
        if (!in_array($column, $allowed, true)) {
            return [];
        }
        $col = $column === 'participant' ? '`participant`' : '`category`';
        $rows = $this->db->fetchAll(
            "SELECT DISTINCT {$col} AS v FROM fin_transactions WHERE {$col} IS NOT NULL AND {$col} != '' ORDER BY v ASC LIMIT 200"
        );
        return array_map(function ($r) {
            return $r['v'];
        }, $rows);
    }

    /* ─────────────────────────── Приватные помощники ─────────────────────────── */

    private function keywordsFrom($json): array
    {
        return FinAggregator::keywordsFrom($json);
    }

    private function isExcluded(array $row, array $keywords): bool
    {
        return FinAggregator::isExcluded($row, $keywords);
    }

    private function uniquePrefixes(array $dates, int $len): int
    {
        return FinAggregator::uniquePrefixes($dates, $len);
    }
}
