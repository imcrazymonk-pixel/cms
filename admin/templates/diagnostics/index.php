<?php
/**
 * Страница диагностики — мониторинг состояния VPN-нод.
 *
 * Переменные:
 *   $nodes       — массив нод с данными
 *   $summary     — сводка (total, reachable, unreachable, problems, avgLoad)
 *   $collectedAt — время последнего сбора
 *   $hasData     — есть ли данные
 */
$nodes = $nodes ?? [];
$summary = $summary ?? [];
$collectedAt = $collectedAt ?? null;
$hasData = $hasData ?? false;
$isCollecting = $isCollecting ?? false;
$scriptExists = $scriptExists ?? false;

$pingLabels = [
    '77.88.8.8' => 'Яндекс DNS',
    '8.8.8.8' => 'Google DNS',
    'ya.ru' => 'Яндекс (Москва)',
    'vk.com' => 'VK (СПб)',
    '144.31.96.78' => 'DE (files)',
    '144.31.156.172' => 'Панель',
    '31.77.128.251' => 'FI (audio)',
    '150.241.94.61' => 'NL (photo)',
    '159.194.221.84' => 'RU (video)',
    '162.217.248.186' => 'US (data)',
    '155.212.131.4' => 'Yandex',
];
?>
<div class="diagnostics-page" data-controller="diagnostics"
     data-is-collecting="<?= $isCollecting ? '1' : '0' ?>"
     data-script-exists="<?= $scriptExists ? '1' : '0' ?>">
    <!-- Шапка -->
    <div class="diag-header">
        <div class="diag-header-left">
            <h1><?= icon('monitor') ?> Диагностика нод</h1>
            <span class="diag-subtitle" id="diagLastUpd"><?= $collectedAt ? '· обновлено ' . str_replace('T', ' ', str_replace('Z', '', $collectedAt)) : '· данные не загружены' ?></span>
            <span class="diag-subtitle diag-collecting-badge" id="diagCollectingBadge"
                  style="<?= $isCollecting ? '' : 'display:none' ?>">⏳ Идёт сбор...</span>
        </div>
        <div class="diag-header-actions">
            <label class="diag-auto-label">
                <input type="checkbox" id="diagAutoRefresh" checked> ♻️ Авто 30с
            </label>
            <button type="button" class="btn btn-ghost" id="diagRefreshBtn" onclick="diagRefresh()"><?= icon('refresh-cw') ?> Обновить</button>
            <button type="button" class="btn btn-primary" id="diagCollectBtn"
                    onclick="diagCollect()"><?= icon('download') ?> Собрать статистику</button>
        </div>
    </div>

    <!-- Сводка -->
    <?php if ($hasData): ?>
    <div class="stats-grid diag-summary-grid">
        <div class="glass-card stat-card anim-fade-in-up stagger-1">
            <div class="stat-icon"><?= icon('monitor', 'icon-lg') ?></div>
            <div>
                <span class="stat-value"><?= $summary['total'] ?? 0 ?></span>
                <span class="stat-label">Всего нод</span>
            </div>
        </div>
        <div class="glass-card stat-card anim-fade-in-up stagger-2">
            <div class="stat-icon"><?= icon('check', 'icon-lg') ?></div>
            <div>
                <span class="stat-value" style="color:var(--color-ok, #8fecb0)"><?= $summary['reachable'] ?? 0 ?></span>
                <span class="stat-label">Доступны</span>
            </div>
        </div>
        <div class="glass-card stat-card anim-fade-in-up stagger-3">
            <div class="stat-icon"><?= icon('alert-triangle', 'icon-lg') ?></div>
            <div>
                <span class="stat-value" style="color:var(--color-err, #f06060)"><?= $summary['unreachable'] ?? 0 ?></span>
                <span class="stat-label">Недоступны</span>
            </div>
        </div>
        <div class="glass-card stat-card anim-fade-in-up stagger-4">
            <div class="stat-icon"><?= icon('trending-up', 'icon-lg') ?></div>
            <div>
                <span class="stat-value"><?= $summary['problems'] ?? 0 ?></span>
                <span class="stat-label">Проблем</span>
            </div>
        </div>
    </div>
    <?php endif; ?>

    <!-- Сетка карточек нод -->
    <div class="diag-grid" id="diagGrid">
        <?php if (!$hasData): ?>
        <div class="glass-card diag-empty">
            <div class="diag-empty-icon"><?= icon('monitor', 'icon-lg') ?></div>
            <h3>Данные мониторинга не загружены</h3>
            <?php if (!$scriptExists): ?>
            <p>Файл <code>tools/collect_stats.py</code> не найден на сервере.</p>
            <p class="diag-hint">Загрузите скрипт на сервер или запустите сбор вручную:</p>
            <?php else: ?>
            <p>Нажмите «Собрать статистику» — скрипт опросит все 6 нод (занимает ~30 сек).</p>
            <?php endif; ?>
            <div class="diag-empty-actions">
                <button type="button" class="btn btn-primary btn-lg" id="diagCollectBtnEmpty"
                        onclick="diagCollect()"><?= icon('download') ?> Собрать статистику</button>
                <button type="button" class="btn btn-ghost" onclick="diagRefresh()"><?= icon('refresh-cw') ?> Обновить</button>
            </div>
        </div>
        <?php else: ?>
        <?php foreach ($nodes as $n):
            $d = $n['data'] ?? [];
            $tcp = $d['tcp'] ?? [];
            $net = $d['network_errors'] ?? [];
            $pings = $d['pings'] ?? [];
            $load = $d['load'] ?? [];
            $ram = $d['ram'] ?? [];
            $disk = $d['disk'] ?? [];
            $docker = $d['docker'] ?? [];
            $nginx = $d['nginx'] ?? [];
            $certs = $d['certs'] ?? [];

            $isOk = $n['reachable'];
            $retransPct = $tcp['retrans_pct'] ?? null;
            $speed = $d['speed_download_mbps'] ?? null;
            $load1m = $load['1m'] ?? 0;

            $cardClass = $isOk ? 'diag-card' : 'diag-card diag-card--err';
            $statusIcon = $isOk ? 'check' : 'alert-triangle';
            $statusColor = $isOk ? 'var(--color-ok, #8fecb0)' : 'var(--color-err, #f06060)';
            $statusText = $isOk ? 'Доступна' : 'Недоступна';
        ?>
        <div class="glass-card <?= $cardClass ?>" data-node-id="<?= $n['id'] ?>">
            <div class="diag-card-header">
                <h3><?= $n['name'] ?></h3>
                <span class="diag-status-badge" style="color:<?= $statusColor ?>"><?= icon($statusIcon) ?> <?= $statusText ?></span>
            </div>

            <?php if (!$isOk): ?>
            <div class="diag-stat-row">
                <span class="diag-stat-l">Ошибка</span>
                <span class="diag-stat-v diag-v-err"><?= $n['error'] ?? 'таймаут' ?></span>
            </div>
            <?php else: ?>
            <!-- Hostname + uptime -->
            <div class="diag-stat-row">
                <span class="diag-stat-l">Hostname</span>
                <span class="diag-stat-v"><?= $d['hostname'] ?? '—' ?></span>
            </div>
            <div class="diag-stat-row">
                <span class="diag-stat-l">Uptime</span>
                <span class="diag-stat-v"><?= $d['uptime'] ?? '—' ?></span>
            </div>

            <!-- CPU / RAM / Disk -->
            <div class="diag-stat-row">
                <span class="diag-stat-l">CPU</span>
                <span class="diag-stat-v"><?= $d['cpu_cores'] ?? '?' ?> ядра</span>
            </div>
            <div class="diag-stat-row">
                <span class="diag-stat-l">RAM</span>
                <span class="diag-stat-v"><?= $ram['used'] ?? '—' ?> / <?= $ram['total'] ?? '—' ?></span>
            </div>
            <div class="diag-stat-row">
                <span class="diag-stat-l">Диск</span>
                <span class="diag-stat-v"><?= $disk['used'] ?? '—' ?> / <?= $disk['total'] ?? '—' ?> (<?= $disk['pct'] ?? '—' ?>)</span>
            </div>

            <!-- Load -->
            <div class="diag-stat-row">
                <span class="diag-stat-l">Load (1/5/15)</span>
                <span class="diag-stat-v diag-v-<?= $load1m < 0.5 ? 'ok' : ($load1m < 0.8 ? 'warn' : 'err') ?>"><?= $load['1m'] ?? '—' ?> / <?= $load['5m'] ?? '—' ?> / <?= $load['15m'] ?? '—' ?></span>
            </div>

            <!-- Docker -->
            <div class="diag-stat-row">
                <span class="diag-stat-l">Docker</span>
                <span class="diag-stat-v"><?php
                    $dcNames = [];
                    foreach ($docker as $c): $dcNames[] = $c['name']; endforeach;
                    echo !empty($dcNames) ? implode(', ', $dcNames) : '—';
                ?></span>
            </div>

            <!-- Nginx -->
            <div class="diag-stat-row">
                <span class="diag-stat-l">nginx</span>
                <span class="diag-stat-v">
                    <?php if ($nginx['status'] ?? '' === 'ok'): ?>
                    <span class="diag-v-ok">✅ OK</span>
                    <?php elseif ($nginx['status'] ?? '' === 'error'): ?>
                    <span class="diag-v-err">🔴 <?= $nginx['error'] ?? 'error' ?></span>
                    <?php else: ?>
                    <span class="diag-v-warn">⚠️ неизвестно</span>
                    <?php endif; ?>
                </span>
            </div>

            <!-- Скорость -->
            <div class="diag-stat-row">
                <span class="diag-stat-l">Download</span>
                <span class="diag-stat-v diag-v-<?= $speed > 100 ? 'ok' : ($speed > 5 ? 'warn' : 'err') ?>"><?= $speed ? $speed . ' Мбит/с' : '—' ?></span>
            </div>

            <!-- TCP -->
            <div class="diag-stat-row">
                <span class="diag-stat-l">TCP ретрансмиссии</span>
                <span class="diag-stat-v diag-v-<?= $retransPct !== null ? ($retransPct < 0.5 ? 'ok' : ($retransPct < 2 ? 'warn' : 'err')) : '' ?>"><?= $retransPct !== null ? $retransPct . '%' : '—' ?></span>
            </div>
            <div class="diag-stat-row">
                <span class="diag-stat-l">TCP таймауты</span>
                <span class="diag-stat-v diag-v-<?= ($tcp['timeouts'] ?? 0) < 1e6 ? 'ok' : (($tcp['timeouts'] ?? 0) < 1e7 ? 'warn' : 'err') ?>"><?= ($tcp['timeouts'] ?? 0) > 0 ? number_format($tcp['timeouts'], 0, '', ' ') : '0' ?></span>
            </div>
            <div class="diag-stat-row">
                <span class="diag-stat-l">Traffic in/out</span>
                <span class="diag-stat-v"><?= number_format($tcp['in_segs'] ?? 0, 0, '', ' ') ?> / <?= number_format($tcp['out_segs'] ?? 0, 0, '', ' ') ?></span>
            </div>

            <!-- Network errors -->
            <div class="diag-stat-row">
                <span class="diag-stat-l">Ошибки сети (rx/tx)</span>
                <span class="diag-stat-v"><?= $net['rx_err'] ?? 0 ?> / <?= $net['tx_err'] ?? 0 ?></span>
            </div>

            <!-- Certificates -->
            <?php if (!empty($certs)): ?>
            <div class="diag-stat-row">
                <span class="diag-stat-l">Сертификаты</span>
                <span class="diag-stat-v"><?= count($certs) ?> шт</span>
            </div>
            <?php endif; ?>

            <!-- Pings -->
            <?php
            $pingEntries = [];
            foreach ($pings as $ip => $p):
                $label = $pingLabels[$ip] ?? $ip;
                $msCls = $p['ms'] !== null ? ($p['ms'] < 30 ? 'ok' : ($p['ms'] < 80 ? 'warn' : 'err')) : '';
                $pingEntries[] = [$label, $p['ms'], $msCls];
            endforeach;
            ?>
            <?php if (!empty($pingEntries)): ?>
            <div class="diag-pings">
                <?php foreach ($pingEntries as $pe): ?>
                <span class="diag-ping-dst"><?= $pe[0] ?></span>
                <span class="diag-ping-ms diag-v-<?= $pe[2] ?>"><?= $pe[1] !== null ? $pe[1] . 'ms' : '—' ?></span>
                <?php endforeach; ?>
            </div>
            <?php endif; ?>
            <?php endif; ?>
        </div>
        <?php endforeach; ?>
        <?php endif; ?>
    </div>

    <!-- Панель проблем -->
    <?php if ($hasData): ?>
    <div id="diagProblems" class="glass-card diag-problems" style="<?php
        $hasProblems = false;
        foreach ($nodes as $n):
            if (!$n['reachable']): $hasProblems = true; break; endif;
            $d = $n['data'] ?? [];
            $t = $d['tcp'] ?? [];
            if (($t['retrans_pct'] ?? 0) >= 2): $hasProblems = true; break; endif;
            if (($d['speed_download_mbps'] ?? 100) < 3): $hasProblems = true; break; endif;
            if (($d['nginx']['status'] ?? '') === 'error'): $hasProblems = true; break; endif;
            if (($d['load']['1m'] ?? 0) > 0.8): $hasProblems = true; break; endif;
        endforeach;
        echo $hasProblems ? '' : 'display:none';
    ?>">
        <h3><?= icon('alert-triangle') ?> Выявленные проблемы</h3>
        <div id="diagProblemsList">
            <?php foreach ($nodes as $n):
                $d = $n['data'] ?? [];
                $t = $d['tcp'] ?? [];
                $pct = $t['retrans_pct'] ?? null;
                if (!$n['reachable']): ?>
                <div class="diag-problem-item diag-problem--err">
                    <?= icon('x') ?> <b><?= $n['name'] ?>:</b> Недоступна (<?= $n['error'] ?? 'таймаут' ?>)
                </div>
                <?php elseif ($pct !== null && $pct >= 2): ?>
                <div class="diag-problem-item diag-problem--err">
                    <?= icon('trending-down') ?> <b><?= $n['name'] ?>:</b> <?= $pct ?>% ретрансмиссий, <?= number_format($t['timeouts'] ?? 0, 0, '', ' ') ?> таймаутов
                </div>
                <?php elseif (($d['nginx']['status'] ?? '') === 'error'): ?>
                <div class="diag-problem-item diag-problem--warn">
                    <?= icon('alert-triangle') ?> <b><?= $n['name'] ?>:</b> nginx: <?= $d['nginx']['error'] ?? 'ошибка' ?>
                </div>
                <?php elseif (($d['speed_download_mbps'] ?? 100) < 3): ?>
                <div class="diag-problem-item diag-problem--warn">
                    <?= icon('trending-down') ?> <b><?= $n['name'] ?>:</b> скорость <?= $d['speed_download_mbps'] ?> Мбит/с
                </div>
                <?php elseif (($d['load']['1m'] ?? 0) > 0.8): ?>
                <div class="diag-problem-item diag-problem--warn">
                    <?= icon('trending-up') ?> <b><?= $n['name'] ?>:</b> Load <?= $d['load']['1m'] ?>
                </div>
                <?php endif; ?>
            <?php endforeach; ?>
        </div>
    </div>
    <?php endif; ?>

    <!-- Таблица сравнения -->
    <?php if ($hasData):
    $reachableNodes = [];
    foreach ($nodes as $n):
        if ($n['reachable']): $reachableNodes[] = $n; endif;
    endforeach;
    ?>
    <?php if (!empty($reachableNodes)): ?>
    <div class="glass-card diag-comparison">
        <h3><?= icon('bar-chart-2') ?> Сравнение нод</h3>
        <div class="table-wrap">
            <table class="diag-table">
                <thead>
                    <tr>
                        <th>Нода</th>
                        <th class="diag-th-right">Load</th>
                        <th class="diag-th-right">RAM</th>
                        <th class="diag-th-right">Disk</th>
                        <th class="diag-th-right">Speed</th>
                        <th class="diag-th-right">Retrans %</th>
                        <th class="diag-th-right">Timeouts</th>
                        <th class="diag-th-right">→ Москва</th>
                        <th class="diag-th-right">→ DE</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($reachableNodes as $n):
                        $d = $n['data'] ?? [];
                        $t = $d['tcp'] ?? [];
                        $p = $d['pings'] ?? [];
                        $l = $d['load'] ?? [];
                        $r = $d['ram'] ?? [];
                        $dk = $d['disk'] ?? [];
                        $sp = $d['speed_download_mbps'] ?? 0;
                        $rt = $t['retrans_pct'] ?? null;
                        $to = $t['timeouts'] ?? 0;
                        $ya = $p['ya.ru'] ?? [];
                        $de = $p['144.31.96.78'] ?? [];
                        $l1 = $l['1m'] ?? 0;
                        $diskPct = $dk['pct'] ?? '0%';
                        $diskPctNum = (int)$diskPct;
                    ?>
                    <tr>
                        <td><?= $n['name'] ?></td>
                        <td class="diag-td-right" style="color:<?= $l1 < 0.5 ? '#8fecb0' : ($l1 < 0.8 ? '#f5c842' : '#f06060') ?>"><?= $l1 ?></td>
                        <td class="diag-td-right"><?= $r['used'] ?? '—' ?></td>
                        <td class="diag-td-right" style="color:<?= $diskPctNum < 50 ? '#8fecb0' : ($diskPctNum < 80 ? '#f5c842' : '#f06060') ?>"><?= $diskPct ?></td>
                        <td class="diag-td-right" style="color:<?= $sp > 100 ? '#8fecb0' : ($sp > 5 ? '#f5c842' : '#f06060') ?>"><?= $sp ? $sp . 'M' : '—' ?></td>
                        <td class="diag-td-right" style="color:<?= $rt !== null ? ($rt < 0.5 ? '#8fecb0' : ($rt < 2 ? '#f5c842' : '#f06060')) : '#666' ?>"><?= $rt !== null ? $rt . '%' : '—' ?></td>
                        <td class="diag-td-right" style="color:<?= $to < 1e6 ? '#8fecb0' : ($to < 1e7 ? '#f5c842' : '#f06060') ?>"><?= $to > 0 ? number_format($to, 0, '', ' ') : '0' ?></td>
                        <td class="diag-td-right<?= $ya['ms'] ? ($ya['ms'] < 30 ? ' diag-v-ok' : ($ya['ms'] < 80 ? ' diag-v-warn' : ' diag-v-err')) : '' ?>"><?= $ya['ms'] ? $ya['ms'] . 'ms' : '—' ?></td>
                        <td class="diag-td-right<?= $de['ms'] ? ($de['ms'] < 30 ? ' diag-v-ok' : ($de['ms'] < 80 ? ' diag-v-warn' : ' diag-v-err')) : '' ?>"><?= $de['ms'] ? $de['ms'] . 'ms' : '—' ?></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
    <?php endif; ?>
    <?php endif; ?>
</div>

<div id="diagToast" class="diag-toast"></div>

<script>
const DIAG_PING_LABELS = {
    '77.88.8.8': 'Яндекс DNS',
    '8.8.8.8': 'Google DNS',
    'ya.ru': 'Яндекс (Москва)',
    'vk.com': 'VK (СПб)',
    '144.31.96.78': 'DE (files)',
    '144.31.156.172': 'Панель',
    '31.77.128.251': 'FI (audio)',
    '150.241.94.61': 'NL (photo)',
    '159.194.221.84': 'RU (video)',
    '162.217.248.186': 'US (data)',
    '155.212.131.4': 'Yandex',
};

function diagToast(msg) {
    const t = document.getElementById('diagToast');
    t.textContent = msg;
    t.style.opacity = '1';
    setTimeout(() => { t.style.opacity = '0'; }, 2500);
}

function diagBuildCard(n) {
    const d = n.data || {};
    const load = d.load ? (d.load['1m'] + ' / ' + d.load['5m'] + ' / ' + d.load['15m']) : '—';
    const ram = d.ram ? (d.ram.used + ' / ' + d.ram.total) : '—';
    const disk = d.disk ? (d.disk.used + ' / ' + d.disk.total + ' (' + d.disk.pct + ')') : '—';
    const speed = d.speed_download_mbps ? d.speed_download_mbps + ' Мбит/с' : '—';
    const retrans = d.tcp && d.tcp.retrans_pct !== null ? d.tcp.retrans_pct : null;
    const tc = d.tcp || {};
    const net = d.network_errors || {};
    const pings = d.pings || {};
    const nginx = d.nginx || {};
    const docker = d.docker || [];
    const certs = d.certs || [];
    const load1m = d.load ? d.load['1m'] : 0;

    let statusIcon = n.reachable ? '✅' : '❌';
    let cardClass = n.reachable ? '' : ' diag-card--err';

    let html = '<div class="glass-card diag-card' + cardClass + '" data-node-id="' + n.id + '">';
    html += '<div class="diag-card-header"><h3>' + n.name + '</h3>';
    html += '<span class="diag-status-badge" style="color:' + (n.reachable ? '#8fecb0' : '#f06060') + '">' + statusIcon + ' ' + (n.reachable ? 'Доступна' : 'Недоступна') + '</span></div>';

    if (!n.reachable) {
        html += '<div class="diag-stat-row"><span class="diag-stat-l">Ошибка</span><span class="diag-stat-v diag-v-err">' + (n.error || 'таймаут') + '</span></div>';
        html += '</div>';
        return html;
    }

    const retransCls = retrans !== null ? (retrans < 0.5 ? 'ok' : (retrans < 2 ? 'warn' : 'err')) : '';
    const toCls = tc.timeouts !== undefined ? (tc.timeouts < 1e6 ? 'ok' : (tc.timeouts < 1e7 ? 'warn' : 'err')) : '';
    const speedCls = speed !== '—' ? (d.speed_download_mbps > 100 ? 'ok' : (d.speed_download_mbps > 5 ? 'warn' : 'err')) : '';
    const loadCls = load1m < 0.5 ? 'ok' : (load1m < 0.8 ? 'warn' : 'err');
    const diskPct = d.disk ? parseInt(d.disk.pct) : 0;
    const diskCls = diskPct < 50 ? 'ok' : (diskPct < 80 ? 'warn' : 'err');

    html += '<div class="diag-stat-row"><span class="diag-stat-l">Hostname</span><span class="diag-stat-v">' + (d.hostname || '—') + '</span></div>';
    html += '<div class="diag-stat-row"><span class="diag-stat-l">Uptime</span><span class="diag-stat-v">' + (d.uptime || d.uptime_raw || '—') + '</span></div>';
    html += '<div class="diag-stat-row"><span class="diag-stat-l">CPU / RAM</span><span class="diag-stat-v">' + (d.cpu_cores || '?') + ' ядра · ' + ram + '</span></div>';
    html += '<div class="diag-stat-row"><span class="diag-stat-l">Диск</span><span class="diag-stat-v diag-v-' + diskCls + '">' + disk + '</span></div>';
    html += '<div class="diag-stat-row"><span class="diag-stat-l">Load (1/5/15)</span><span class="diag-stat-v diag-v-' + loadCls + '">' + load + '</span></div>';
    html += '<div class="diag-stat-row"><span class="diag-stat-l">Docker</span><span class="diag-stat-v">' + (docker.map(c => c.name).join(', ') || '—') + '</span></div>';

    const ngStatus = nginx.status === 'ok' ? '<span class="diag-v-ok">✅ OK</span>' : (nginx.status === 'error' ? '<span class="diag-v-err">🔴 ' + (nginx.error || 'error') + '</span>' : '<span class="diag-v-warn">⚠️ неизвестно</span>');
    html += '<div class="diag-stat-row"><span class="diag-stat-l">nginx</span><span class="diag-stat-v">' + ngStatus + '</span></div>';

    html += '<div class="diag-stat-row"><span class="diag-stat-l">Download</span><span class="diag-stat-v diag-v-' + speedCls + '">' + speed + '</span></div>';
    html += '<div class="diag-stat-row"><span class="diag-stat-l">TCP ретрансмиссии</span><span class="diag-stat-v diag-v-' + retransCls + '">' + (retrans !== null ? retrans + '%' : '—') + '</span></div>';
    html += '<div class="diag-stat-row"><span class="diag-stat-l">TCP таймауты</span><span class="diag-stat-v diag-v-' + toCls + '">' + (tc.timeouts ? tc.timeouts.toLocaleString('ru') : '0') + '</span></div>';
    html += '<div class="diag-stat-row"><span class="diag-stat-l">Traffic in/out</span><span class="diag-stat-v">' + ((tc.in_segs || 0).toLocaleString('ru')) + ' / ' + ((tc.out_segs || 0).toLocaleString('ru')) + '</span></div>';
    html += '<div class="diag-stat-row"><span class="diag-stat-l">Ошибки сети (rx/tx)</span><span class="diag-stat-v">' + (net.rx_err || 0) + ' / ' + (net.tx_err || 0) + '</span></div>';

    if (certs && certs.length) {
        html += '<div class="diag-stat-row"><span class="diag-stat-l">Сертификаты</span><span class="diag-stat-v">' + certs.length + ' шт</span></div>';
    }

    const pingKeys = Object.keys(pings);
    if (pingKeys.length) {
        html += '<div class="diag-pings">';
        for (const ip of pingKeys) {
            const p = pings[ip];
            if (p.ms === null && p.loss === null) continue;
            const label = DIAG_PING_LABELS[ip] || ip;
            const msCls = p.ms !== null ? (p.ms < 30 ? 'ok' : (p.ms < 80 ? 'warn' : 'err')) : '';
            html += '<span class="diag-ping-dst">' + label + '</span><span class="diag-ping-ms diag-v-' + msCls + '">' + (p.ms !== null ? p.ms + 'ms' : '—') + '</span>';
        }
        html += '</div>';
    }

    html += '</div>';
    return html;
}

function diagBuildComparison(nodes) {
    const reachable = nodes.filter(n => n.reachable);
    if (!reachable.length) return '';

    let html = '<h3 style="margin-top:0">' + /* icon */ '📋 Сравнение нод</h3>';
    html += '<div class="table-wrap"><table class="diag-table"><thead><tr>';
    html += '<th>Нода</th><th class="diag-th-right">Load</th><th class="diag-th-right">RAM</th>';
    html += '<th class="diag-th-right">Disk</th><th class="diag-th-right">Speed</th>';
    html += '<th class="diag-th-right">Retrans %</th><th class="diag-th-right">Timeouts</th>';
    html += '<th class="diag-th-right">→ Москва</th><th class="diag-th-right">→ DE</th>';
    html += '</tr></thead><tbody>';

    for (const n of reachable) {
        const d = n.data || {};
        const tcp = d.tcp || {};
        const pings = d.pings || {};
        const ya = pings['ya.ru'] || {};
        const de = pings['144.31.96.78'] || {};
        const load = d.load ? d.load['1m'] : 0;
        const ram = d.ram ? d.ram.used : '—';
        const diskVal = d.disk ? d.disk.pct : '—';
        const speed = d.speed_download_mbps || 0;
        const retrans = tcp.retrans_pct !== null ? tcp.retrans_pct : null;
        const timeouts = tcp.timeouts || 0;
        const diskPct = d.disk ? parseInt(d.disk.pct) : 0;

        const loadCls = load < 0.5 ? '#8fecb0' : (load < 0.8 ? '#f5c842' : '#f06060');
        const diskCls = diskPct < 50 ? '#8fecb0' : (diskPct < 80 ? '#f5c842' : '#f06060');
        const speedCls = speed > 100 ? '#8fecb0' : (speed > 5 ? '#f5c842' : '#f06060');
        const retransCls = retrans !== null ? (retrans < 0.5 ? '#8fecb0' : (retrans < 2 ? '#f5c842' : '#f06060')) : '#666';
        const toCls = timeouts < 1e6 ? '#8fecb0' : (timeouts < 1e7 ? '#f5c842' : '#f06060');

        html += '<tr>';
        html += '<td>' + n.name + '</td>';
        html += '<td class="diag-td-right" style="color:' + loadCls + '">' + load + '</td>';
        html += '<td class="diag-td-right">' + ram + '</td>';
        html += '<td class="diag-td-right" style="color:' + diskCls + '">' + diskVal + '</td>';
        html += '<td class="diag-td-right" style="color:' + speedCls + '">' + (speed ? speed + 'M' : '—') + '</td>';
        html += '<td class="diag-td-right" style="color:' + retransCls + '">' + (retrans !== null ? retrans + '%' : '—') + '</td>';
        html += '<td class="diag-td-right" style="color:' + toCls + '">' + (timeouts ? timeouts.toLocaleString('ru') : '0') + '</td>';
        html += '<td class="diag-td-right" style="color:' + (ya.ms < 30 ? '#8fecb0' : (ya.ms < 80 ? '#f5c842' : '#f06060')) + '">' + (ya.ms ? ya.ms + 'ms' : '—') + '</td>';
        html += '<td class="diag-td-right" style="color:' + (de.ms < 30 ? '#8fecb0' : (de.ms < 80 ? '#f5c842' : '#f06060')) + '">' + (de.ms ? de.ms + 'ms' : '—') + '</td>';
        html += '</tr>';
    }
    html += '</tbody></table></div>';
    return html;
}

function diagRenderProblems(nodes) {
    const problems = [];
    for (const n of nodes) {
        if (!n.reachable) {
            problems.push({ type: 'err', text: '🔴 <b>' + n.name + ':</b> Недоступна (' + (n.error || 'таймаут') + ')' });
            continue;
        }
        const d = n.data || {};
        const tcp = d.tcp || {};
        if (tcp.retrans_pct !== null && tcp.retrans_pct >= 2) {
            problems.push({ type: 'err', text: '🔴 <b>' + n.name + ':</b> ' + tcp.retrans_pct + '% ретрансмиссий, ' + (tcp.timeouts || 0).toLocaleString('ru') + ' таймаутов' });
        }
        if (d.nginx && d.nginx.status === 'error') {
            problems.push({ type: 'warn', text: '⚠️ <b>' + n.name + ':</b> nginx: ' + (d.nginx.error || 'ошибка') });
        }
        if (d.speed_download_mbps !== null && d.speed_download_mbps < 3) {
            problems.push({ type: 'warn', text: '🐌 <b>' + n.name + ':</b> скорость ' + d.speed_download_mbps + ' Мбит/с' });
        }
        if (d.load && d.load['1m'] > 0.8) {
            problems.push({ type: 'warn', text: '🔺 <b>' + n.name + ':</b> Load ' + d.load['1m'] });
        }
    }
    return problems;
}

async function diagRefresh() {
    const btn = document.getElementById('diagRefreshBtn');
    btn.disabled = true;
    btn.textContent = '⏳';

    try {
        const r = await fetch('/admin/diagnostics/api/data');
        if (!r.ok) { diagToast('❌ Ошибка загрузки'); btn.disabled = false; btn.innerHTML = '⟳ Обновить'; return; }
        const json = await r.json();
        if (!json.success) { diagToast('❌ ' + (json.error || 'Ошибка')); btn.disabled = false; btn.innerHTML = '⟳ Обновить'; return; }

        const data = json;

        // Update timestamp
        document.getElementById('diagLastUpd').textContent = '· обновлено ' + (data.collected_at || '—').replace('T', ' ').replace('Z', '');

        // Update cards
        const grid = document.getElementById('diagGrid');
        if (!data.nodes || !data.nodes.length) {
            grid.innerHTML = '<div class="glass-card diag-empty"><h3>Нет данных</h3><p>Запустите сбор статистики</p></div>';
        } else {
            grid.innerHTML = data.nodes.map(n => diagBuildCard(n)).join('');
        }

        // Update problems panel
        const problemsEl = document.getElementById('diagProblems');
        const problemsList = document.getElementById('diagProblemsList');
        if (problemsEl && problemsList) {
            const problems = diagRenderProblems(data.nodes);
            if (problems.length) {
                problemsEl.style.display = '';
                problemsList.innerHTML = problems.map(p => '<div class="diag-problem-item diag-problem--' + p.type + '">' + p.text + '</div>').join('');
            } else {
                problemsEl.style.display = 'none';
            }
        }

        // Update comparison table
        const comparisonSection = document.querySelector('.diag-comparison');
        if (comparisonSection) {
            const tableWrap = comparisonSection.querySelector('.table-wrap');
            if (tableWrap) {
                const newHtml = diagBuildComparison(data.nodes);
                if (newHtml) {
                    tableWrap.innerHTML = newHtml;
                }
            }
        }

        // Update summary stats
        if (json.summary) {
            const summaryCards = document.querySelectorAll('.diag-summary-grid .stat-card .stat-value');
            if (summaryCards.length >= 4) {
                summaryCards[0].textContent = json.summary.total || 0;
                summaryCards[1].textContent = json.summary.reachable || 0;
                summaryCards[2].textContent = json.summary.unreachable || 0;
                summaryCards[3].textContent = json.summary.problems || 0;
            }
        }

        diagToast('✅ Обновлено');
    } catch(e) {
        diagToast('❌ Ошибка: ' + e.message);
    }
    btn.disabled = false;
    btn.innerHTML = '⟳ Обновить';
}

async function diagCollect() {
    const btn = document.getElementById('diagCollectBtn');
    const btnEmpty = document.getElementById('diagCollectBtnEmpty');
    const badge = document.getElementById('diagCollectingBadge');

    // Disable both buttons
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Сбор...'; }
    if (btnEmpty) { btnEmpty.disabled = true; btnEmpty.textContent = '⏳ Сбор...'; }
    if (badge) { badge.style.display = ''; badge.textContent = '⏳ Сбор запущен...'; }
    diagToast('⏳ Запуск сбора статистики...');

    try {
        const r = await fetch('/admin/diagnostics/api/collect', { method: 'POST' });
        const json = await r.json();
        if (json.success) {
            diagToast('⏳ Сбор запущен. Ожидайте ~30 сек...');
            // Start polling for completion: check every 5 seconds
            let attempts = 0;
            const maxAttempts = 20; // 100 seconds max
            const poll = () => {
                attempts++;
                fetch('/admin/diagnostics/api/data')
                    .then(r => r.json())
                    .then(d => {
                        if (badge) badge.textContent = '⏳ Сбор... ' + (attempts * 5) + 'с';
                        if (!d.is_collecting && d.collected_at) {
                            // Collection done
                            if (badge) badge.style.display = 'none';
                            diagToast('✅ Сбор завершён');
                            diagRefresh();
                            return;
                        }
                        if (attempts < maxAttempts) {
                            setTimeout(poll, 5000);
                        } else {
                            if (badge) badge.style.display = 'none';
                            diagToast('⚠️ Сбор не завершился за ' + (maxAttempts * 5) + 'с. Проверьте сервер.');
                            if (btn) { btn.disabled = false; btn.textContent = '⟳ Собрать статистику'; }
                            if (btnEmpty) { btnEmpty.disabled = false; btnEmpty.textContent = '⟳ Собрать статистику'; }
                        }
                    })
                    .catch(() => {
                        if (attempts < maxAttempts) {
                            setTimeout(poll, 5000);
                        }
                    });
            };
            setTimeout(poll, 3000);
        } else {
            diagToast('❌ ' + (json.error || 'Ошибка запуска'));
            if (badge) badge.style.display = 'none';
            if (btn) { btn.disabled = false; btn.textContent = '⟳ Собрать статистику'; }
            if (btnEmpty) { btnEmpty.disabled = false; btnEmpty.textContent = '⟳ Собрать статистику'; }
        }
    } catch(e) {
        diagToast('❌ Ошибка: ' + e.message);
        if (badge) badge.style.display = 'none';
        if (btn) { btn.disabled = false; btn.textContent = '⟳ Собрать статистику'; }
        if (btnEmpty) { btnEmpty.disabled = false; btnEmpty.textContent = '⟳ Собрать статистику'; }
    }
}

// Auto-refresh
(function() {
    let timer = null;
    const cb = document.getElementById('diagAutoRefresh');
    if (cb) {
        cb.addEventListener('change', function() {
            if (timer) { clearInterval(timer); timer = null; }
            if (this.checked) {
                diagRefresh();
                timer = setInterval(diagRefresh, 30000);
            }
        });
        // Start auto-refresh by default
        if (cb.checked) {
            timer = setInterval(diagRefresh, 30000);
        }
    }
})();
</script>

<style>
/* ─── Diagnostics Page Styles ─── */
.diagnostics-page {
    padding: 0;
}

/* Header */
.diag-header {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 24px;
}
.diag-header-left {
    display: flex;
    align-items: center;
    gap: 8px;
}
.diag-header-left h1 {
    font-size: 1.286rem;
    font-weight: 700;
    letter-spacing: -0.3px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.diag-subtitle {
    color: var(--text-muted);
    font-size: 0.857rem;
}
.diag-header-actions {
    display: flex;
    gap: 10px;
    margin-left: auto;
    align-items: center;
}
.diag-auto-label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.857rem;
    color: var(--color-ok, #8fecb0);
    cursor: pointer;
}
.diag-auto-label input {
    accent-color: var(--color-ok, #8fecb0);
}

/* Grid */
.diag-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: var(--spacing-md, 16px);
    margin-top: 4px;
}

/* Card */
.diag-card {
    padding: var(--spacing-lg, 20px);
}
.diag-card--err {
    border-color: var(--color-err-border, #5c1a1a);
    background: var(--color-err-bg, rgba(95, 30, 30, 0.15));
}
.diag-card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
}
.diag-card-header h3 {
    font-size: 1rem;
    font-weight: 600;
}
.diag-status-badge {
    font-size: 0.714rem;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

/* Stats */
.diag-stat-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 0.857rem;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
}
.diag-stat-row:last-of-type {
    border-bottom: none;
}
.diag-stat-l {
    color: var(--text-muted);
}
.diag-stat-v {
    font-weight: 600;
}
.diag-v-ok { color: var(--color-ok, #8fecb0) !important; }
.diag-v-warn { color: var(--color-warn, #f5c842) !important; }
.diag-v-err { color: var(--color-err, #f06060) !important; }

/* Pings */
.diag-pings {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 3px 10px;
    font-size: 0.786rem;
    margin-top: 6px;
    padding: 6px 10px;
    background: var(--surface-raised, rgba(255,255,255,0.04));
    border-radius: var(--radius-sm, 6px);
}
.diag-ping-dst {
    color: var(--text-muted, #777);
}
.diag-ping-ms {
    font-weight: 600;
    text-align: right;
}

/* Empty state */
.diag-empty {
    padding: 40px;
    text-align: center;
    grid-column: 1 / -1;
}
.diag-empty-icon {
    font-size: 3rem;
    opacity: 0.4;
    margin-bottom: 8px;
}
.diag-empty h3 {
    font-size: 1.143rem;
    margin-bottom: 8px;
}
.diag-empty p {
    color: var(--text-muted);
    margin-bottom: 8px;
}
.diag-empty-actions {
    display: flex;
    gap: 10px;
    margin-top: 12px;
    justify-content: center;
}
.diag-collecting-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    background: rgba(255, 200, 50, 0.12);
    border-radius: var(--radius-sm, 6px);
    font-size: 0.786rem;
    font-weight: 600;
    color: var(--color-warn, #f5c842);
}
.diag-code {
    background: var(--code-bg, rgba(255,255,255,0.06));
    padding: 10px 14px;
    border-radius: var(--radius-sm, 6px);
    font-family: var(--font-mono);
    font-size: 0.786rem;
    color: var(--text-muted);
    text-align: left;
    overflow-x: auto;
    margin: 8px 0;
}
.diag-hint {
    font-size: 0.857rem;
    color: var(--text-muted);
    opacity: 0.7;
}

/* Problems */
.diag-problems {
    margin-top: 20px;
    padding: var(--spacing-lg, 20px);
}
.diag-problems h3 {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.diag-problem-item {
    padding: 6px 0;
    font-size: 0.857rem;
}
.diag-problem--err {
    color: var(--color-err, #f06060);
}
.diag-problem--warn {
    color: var(--color-warn, #f5c842);
}

/* Comparison table */
.diag-comparison {
    margin-top: 20px;
    padding: var(--spacing-lg, 20px);
}
.diag-comparison h3 {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.diag-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.857rem;
}
.diag-table th {
    padding: 8px 10px;
    text-align: left;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    background: var(--surface-raised, rgba(255,255,255,0.03));
    font-weight: 600;
    color: var(--text-muted);
}
.diag-table td {
    padding: 7px 10px;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.04));
    color: var(--text-primary);
}
.diag-th-right {
    text-align: right !important;
}
.diag-td-right {
    text-align: right;
}
.table-wrap {
    overflow-x: auto;
}

/* Toast */
.diag-toast {
    position: fixed;
    bottom: 30px;
    right: 30px;
    background: var(--toast-bg, rgba(20, 60, 30, 0.9));
    color: var(--color-ok, #8fecb0);
    padding: 12px 24px;
    border-radius: var(--radius-md, 10px);
    font-size: 0.857rem;
    opacity: 0;
    transition: opacity 0.3s;
    z-index: 999;
    backdrop-filter: blur(8px);
    border: 1px solid var(--glass-border, rgba(255,255,255,0.1));
}

/* Summary grid overrides */
.diag-summary-grid .stat-value {
    font-size: 1.714rem;
}
</style>