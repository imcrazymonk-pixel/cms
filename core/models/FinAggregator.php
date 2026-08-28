<?php
/**
 * FinAggregator — статические помощники агрегаций финансового модуля.
 * Вынесено из FinTransaction, чтобы файлы оставались в пределах 500 строк.
 * Порт группировок из FIN (aggregator.py): monthly/daily/weekly/yearly + исключения.
 */

class FinAggregator
{
    /**
     * Распарсить JSON-массив ключевых слов исключений
     */
    public static function keywordsFrom($json): array
    {
        $data = json_decode((string)$json, true);
        if (!is_array($data)) {
            return [];
        }
        $out = [];
        foreach ($data as $kw) {
            $kw = mb_strtolower(trim((string)$kw));
            if ($kw !== '') {
                $out[] = $kw;
            }
        }
        return $out;
    }

    /**
     * Проверить, исключена ли транзакция (по category/participant/description, регистронезависимо)
     */
    public static function isExcluded(array $row, array $keywords): bool
    {
        if (!$keywords) {
            return false;
        }
        $vals = [
            mb_strtolower((string)($row['category'] ?? '')),
            mb_strtolower((string)($row['participant'] ?? '')),
            mb_strtolower((string)($row['description'] ?? '')),
        ];
        foreach ($keywords as $kw) {
            foreach ($vals as $v) {
                if ($v !== '' && mb_strpos($v, $kw) !== false) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * Количество уникальных префиксов дат (месяцев/лет)
     */
    public static function uniquePrefixes(array $dates, int $len): int
    {
        $set = [];
        foreach ($dates as $d) {
            $set[substr($d, 0, $len)] = true;
        }
        return count($set);
    }

    /**
     * Группировка по месяцам. Строки: date, type, amount.
     * @return array [['label'=>, 'income'=>, 'expense'=>], ...]
     */
    public static function groupMonthly(array $rows): array
    {
        $bm = [];
        foreach ($rows as $r) {
            $m = substr($r['date'], 0, 7);
            if (!isset($bm[$m])) {
                $bm[$m] = ['income' => 0.0, 'expense' => 0.0];
            }
            $bm[$m][$r['type'] === 'income' ? 'income' : 'expense'] += (float)$r['amount'];
        }
        ksort($bm);
        $out = [];
        foreach ($bm as $m => $v) {
            $out[] = [
                'key' => $m,
                'label' => substr($m, 5, 2) . '.' . substr($m, 0, 4),
                'income' => round($v['income'], 2),
                'expense' => round($v['expense'], 2),
            ];
        }
        return $out;
    }

    /**
     * Группировка по дням
     */
    public static function groupDaily(array $rows): array
    {
        $bd = [];
        foreach ($rows as $r) {
            $d = $r['date'];
            if (!isset($bd[$d])) {
                $bd[$d] = ['income' => 0.0, 'expense' => 0.0];
            }
            $bd[$d][$r['type'] === 'income' ? 'income' : 'expense'] += (float)$r['amount'];
        }
        ksort($bd);
        $out = [];
        foreach ($bd as $d => $v) {
            $out[] = [
                'key' => $d,
                'label' => date('d.m.Y', strtotime($d)),
                'income' => round($v['income'], 2),
                'expense' => round($v['expense'], 2),
            ];
        }
        return $out;
    }

    /**
     * Группировка по неделям (ISO, подпись — понедельник недели)
     */
    public static function groupWeekly(array $rows): array
    {
        $bw = [];
        $monday = [];
        foreach ($rows as $r) {
            $dt = new DateTime($r['date']);
            $key = $dt->format('o-\WW');
            if (!isset($monday[$key])) {
                $monday[$key] = (clone $dt)->modify('-' . ($dt->format('N') - 1) . ' days');
            }
            if (!isset($bw[$key])) {
                $bw[$key] = ['income' => 0.0, 'expense' => 0.0];
            }
            $bw[$key][$r['type'] === 'income' ? 'income' : 'expense'] += (float)$r['amount'];
        }
        ksort($bw);
        $out = [];
        foreach ($bw as $key => $v) {
            $m = $monday[$key];
            $out[] = [
                'key' => $key,
                'label' => $m->format('d.m') . ' w' . substr($key, strpos($key, 'W') + 1),
                'income' => round($v['income'], 2),
                'expense' => round($v['expense'], 2),
            ];
        }
        return $out;
    }

    /**
     * Группировка по годам
     */
    public static function groupYearly(array $rows): array
    {
        $by = [];
        foreach ($rows as $r) {
            $y = substr($r['date'], 0, 4);
            if (!isset($by[$y])) {
                $by[$y] = ['income' => 0.0, 'expense' => 0.0];
            }
            $by[$y][$r['type'] === 'income' ? 'income' : 'expense'] += (float)$r['amount'];
        }
        ksort($by);
        $out = [];
        foreach ($by as $y => $v) {
            $out[] = [
                'key' => $y,
                'label' => $y,
                'income' => round($v['income'], 2),
                'expense' => round($v['expense'], 2),
            ];
        }
        return $out;
    }
}
