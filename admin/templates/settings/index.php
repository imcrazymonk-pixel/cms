<?php
/**
 * Настройки сайта — табы: Основные / Внешний вид / API Интеграции
 */

$activeTab = Request::get('tab', 'basic');
if (!in_array($activeTab, ['basic', 'appearance', 'integrations'], true)) {
    $activeTab = 'basic';
}

// Список тем формируется автоматически из папки templates/themes
$themesDir = TEMPLATES_PATH . '/themes';
$themes = [];
if (is_dir($themesDir)) {
    $themes = array_values(array_filter(scandir($themesDir), function ($d) use ($themesDir) {
        return $d !== '.' && $d !== '..' && is_dir($themesDir . '/' . $d);
    }));
}
$themeLabels = [
    'default'  => '📄 Классическая (Default)',
    'modern'   => '🚀 Современная (Modern)',
    'minimal'  => '📝 Минимализм (Minimal)',
    'hexaveil' => '🌐 HexaVeil (лендинг)',
];

// Статус интеграции: [class бейджа, иконка, подпись]
$statusFor = function ($syncOk, $error) {
    $error = trim((string)$error);
    if ($syncOk === '1' && $error === '') {
        return ['badge-success', 'check-circle-2', 'Синхронизировано'];
    }
    if ($error !== '') {
        return ['badge-danger', 'alert-triangle', 'Ошибка синхронизации'];
    }
    return ['badge-neutral', 'x', 'Не настроено'];
};

// Маски секретов (не расшифровывая)
$plategaSecretMask = !empty($finSettings['platega_secret']) ? Crypto::mask($finSettings['platega_secret']) : '';
$yookassaSecretMask = !empty($finSettings['yookassa_secret_key']) ? Crypto::mask($finSettings['yookassa_secret_key']) : '';

// Комиссии ЮKassa: умолчания, перекрытые сохранённым JSON
$yooCommissions = YooKassaClient::defaultCommissions();
if (!empty($finSettings['yookassa_commissions'])) {
    $decodedComms = json_decode($finSettings['yookassa_commissions'], true);
    if (is_array($decodedComms)) {
        $yooCommissions = array_merge($yooCommissions, $decodedComms);
    }
}
$commissionEmojis = [
    'bank_card'    => '💳',
    'sbp'          => '⚡',
    'yoo_money'    => '💰',
    'sberbank'     => '🏦',
    'tinkoff_bank' => '🏧',
    'mobile'       => '📱',
    'cash'         => '💵',
    'qiwi'         => '🟣',
];

// Форматирование процента: 3 / 0.5 / 2.25
$formatPercent = function ($v) {
    $v = (float)$v;
    if ($v == (int)$v) {
        return (string)(int)$v;
    }
    return rtrim(rtrim(number_format($v, 2, '.', ''), '0'), '.');
};

// Cron-команды
$baseUrl = rtrim(SITE_URL, '/');
$plategaCron = '';
if (!empty($finSettings['platega_cron_token'])) {
    $plategaCron = '*/5 * * * * curl -s "' . $baseUrl . '/admin/finance/api/platega/cron-sync?token=' . rawurlencode($finSettings['platega_cron_token']) . '" > /dev/null';
}
$yookassaCron = '';
if (!empty($finSettings['yookassa_cron_token'])) {
    $yookassaCron = '*/5 * * * * curl -s "' . $baseUrl . '/admin/finance/api/yookassa/cron-sync?token=' . rawurlencode($finSettings['yookassa_cron_token']) . '" > /dev/null';
}
?>

<div class="dg-toolbar">
    <button type="button" class="btn btn-primary" onclick="document.getElementById('settings-form').submit()"><?= icon('save') ?> Сохранить</button>
</div>

<?php if (Request::get('success') === 'updated'): ?>
<div class="alert alert-success"><?= icon('check') ?> Настройки сохранены</div>
<?php endif; ?>

<form id="settings-form" method="POST" action="/admin/settings/update">
    <?= csrf_field() ?>

    <div class="settings-tabs" role="tablist">
        <button type="button" class="settings-tab <?= $activeTab === 'basic' ? 'active' : '' ?>" data-tab="basic" role="tab"><?= icon('settings') ?> Основные</button>
        <button type="button" class="settings-tab <?= $activeTab === 'appearance' ? 'active' : '' ?>" data-tab="appearance" role="tab"><?= icon('palette') ?> Внешний вид</button>
        <button type="button" class="settings-tab <?= $activeTab === 'integrations' ? 'active' : '' ?>" data-tab="integrations" role="tab"><?= icon('wallet') ?> API Интеграции</button>
    </div>

    <!-- ==================== Основные ==================== -->
    <div class="settings-panel <?= $activeTab === 'basic' ? 'active' : '' ?>" data-panel="basic">
        <div class="card form-card">
            <h3><?= icon('settings') ?> Основные настройки</h3>

            <div class="form-row">
                <div class="form-group">
                    <label for="site_name">Название сайта</label>
                    <input type="text" id="site_name" name="settings[site_name]" class="form-control"
                           value="<?= TemplateEngine::e($settings['site_name'] ?? '') ?>">
                    <div class="help-text">Отображается в заголовке вкладки браузера и в шапке сайта</div>
                </div>

                <div class="form-group">
                    <label for="site_url">URL сайта</label>
                    <input type="url" id="site_url" name="settings[site_url]" class="form-control"
                           value="<?= TemplateEngine::e($settings['site_url'] ?? '') ?>">
                    <div class="help-text">Базовый адрес сайта без завершающего слэша</div>
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label for="admin_email">Email администратора</label>
                    <input type="email" id="admin_email" name="settings[admin_email]" class="form-control"
                           value="<?= TemplateEngine::e($settings['admin_email'] ?? '') ?>">
                    <div class="help-text">Служебные уведомления направляются на этот адрес</div>
                </div>

                <div class="form-group">
                    <label for="posts_per_page">Постов на страницу</label>
                    <input type="number" id="posts_per_page" name="settings[posts_per_page]" class="form-control"
                           value="<?= (int)($settings['posts_per_page'] ?? 10) ?>" min="1" max="100">
                    <div class="help-text">Количество записей в списке блога на одной странице</div>
                </div>
            </div>
        </div>

        <div class="card form-card">
            <h3><?= icon('file-text') ?> Дополнительные настройки</h3>

            <div class="form-group">
                <label for="meta_description">Описание сайта (Meta Description)</label>
                <textarea id="meta_description" name="settings[meta_description]" class="form-control" rows="3"><?= TemplateEngine::e($settings['meta_description'] ?? '') ?></textarea>
                <div class="help-text">Краткое описание сайта для поисковых систем и соцсетей</div>
            </div>

            <div class="form-group">
                <label for="meta_keywords">Ключевые слова (Meta Keywords)</label>
                <input type="text" id="meta_keywords" name="settings[meta_keywords]" class="form-control"
                       value="<?= TemplateEngine::e($settings['meta_keywords'] ?? '') ?>">
                <div class="help-text">Через запятую, например: vpn, proxy, безопасность</div>
            </div>
        </div>
    </div>

    <!-- ==================== Внешний вид ==================== -->
    <div class="settings-panel <?= $activeTab === 'appearance' ? 'active' : '' ?>" data-panel="appearance">
        <div class="card form-card">
            <h3><?= icon('palette') ?> Внешний вид</h3>

            <div class="form-group">
                <label for="active_theme">Тема оформления</label>
                <select id="active_theme" name="settings[active_theme]" class="form-control">
                    <?php foreach ($themes as $themeName): ?>
                        <?php $themeLabel = $themeLabels[$themeName] ?? $themeName; ?>
                        <option value="<?= TemplateEngine::e($themeName) ?>" <?= (($settings['active_theme'] ?? '') === $themeName) ? 'selected' : '' ?>><?= TemplateEngine::e($themeLabel) ?></option>
                    <?php endforeach; ?>
                </select>
                <div class="help-text">Выберите тему для всего сайта. Шаблоны берутся из папки templates/themes</div>
            </div>
        </div>
    </div>

    <!-- ==================== API Интеграции ==================== -->
    <div class="settings-panel <?= $activeTab === 'integrations' ? 'active' : '' ?>" data-panel="integrations">
        <?php $plategaStatus = $statusFor($finSettings['platega_last_sync_ok'] ?? '0', $finSettings['platega_last_error'] ?? ''); ?>

        <div class="integration-card integration-card-platega">
            <div class="integration-card-header">
                <div class="integration-card-title">
                    <span class="integration-logo"><?= icon('credit-card') ?></span>
                    <span>
                        <span>Platega</span>
                        <span class="integration-subtitle">Платёжный агрегатор</span>
                    </span>
                </div>
                <span class="badge <?= $plategaStatus[0] ?> integration-status"><?= icon($plategaStatus[1]) ?><?= TemplateEngine::e($plategaStatus[2]) ?></span>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label for="platega_merchant_id">Merchant ID</label>
                    <input type="text" id="platega_merchant_id" name="fin_settings[platega_merchant_id]" class="form-control"
                           value="<?= TemplateEngine::e($finSettings['platega_merchant_id'] ?? '') ?>" autocomplete="off">
                    <div class="help-text">Идентификатор мерчанта из личного кабинета Platega</div>
                </div>

                <div class="form-group">
                    <label for="platega_secret">Secret Key</label>
                    <input type="password" id="platega_secret" name="fin_settings[platega_secret]" class="form-control"
                           placeholder="<?= TemplateEngine::e($plategaSecretMask !== '' ? $plategaSecretMask : 'Введите секретный ключ') ?>" autocomplete="new-password">
                    <div class="help-text">Если оставить пустым — текущий ключ сохранится</div>
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label for="platega_days_back">Дней назад</label>
                    <input type="number" id="platega_days_back" name="fin_settings[platega_days_back]" class="form-control"
                           value="<?= (int)($finSettings['platega_days_back'] ?? 30) ?>" min="1" max="365">
                    <div class="help-text">Глубина выгрузки платежей при синхронизации</div>
                </div>

                <div class="form-group">
                    <label for="platega_auto_sync">Автоимпорт</label>
                    <select id="platega_auto_sync" name="fin_settings[platega_auto_sync]" class="form-control">
                        <option value="0" <?= (($finSettings['platega_auto_sync'] ?? '0') == 1 ? '' : 'selected') ?>>Выключен</option>
                        <option value="1" <?= (($finSettings['platega_auto_sync'] ?? '0') == 1 ? 'selected' : '') ?>>Включён</option>
                    </select>
                    <div class="help-text">Автоматическое добавление платежей по cron</div>
                </div>
            </div>

            <div class="integration-footer">
                <?php if (!empty($finSettings['platega_last_sync'])): ?>
                    <div>Последняя синхронизация: <strong><?= TemplateEngine::e($finSettings['platega_last_sync']) ?></strong></div>
                <?php endif; ?>
                <?php if (!empty($finSettings['platega_last_error'])): ?>
                    <div class="text-error">Ошибка: <?= TemplateEngine::e($finSettings['platega_last_error']) ?></div>
                <?php endif; ?>
                <?php if ($plategaCron !== ''): ?>
                    <div>Cron: <code><?= TemplateEngine::e($plategaCron) ?></code></div>
                <?php endif; ?>
                <small>Секретные ключи хранятся в зашифрованном виде (AES-256).</small>
            </div>
        </div>

        <?php $yookassaStatus = $statusFor($finSettings['yookassa_last_sync_ok'] ?? '0', $finSettings['yookassa_last_error'] ?? ''); ?>

        <div class="integration-card integration-card-yookassa">
            <div class="integration-card-header">
                <div class="integration-card-title">
                    <span class="integration-logo"><?= icon('wallet') ?></span>
                    <span>
                        <span>ЮKassa</span>
                        <span class="integration-subtitle">Приём платежей от YooMoney</span>
                    </span>
                </div>
                <span class="badge <?= $yookassaStatus[0] ?> integration-status"><?= icon($yookassaStatus[1]) ?><?= TemplateEngine::e($yookassaStatus[2]) ?></span>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label for="yookassa_shop_id">Shop ID</label>
                    <input type="text" id="yookassa_shop_id" name="fin_settings[yookassa_shop_id]" class="form-control"
                           value="<?= TemplateEngine::e($finSettings['yookassa_shop_id'] ?? '') ?>" autocomplete="off">
                    <div class="help-text">Идентификатор магазина (shopId) из кабинета ЮKassa</div>
                </div>

                <div class="form-group">
                    <label for="yookassa_secret_key">Secret Key</label>
                    <input type="password" id="yookassa_secret_key" name="fin_settings[yookassa_secret_key]" class="form-control"
                           placeholder="<?= TemplateEngine::e($yookassaSecretMask !== '' ? $yookassaSecretMask : 'Введите секретный ключ') ?>" autocomplete="new-password">
                    <div class="help-text">Если оставить пустым — текущий ключ сохранится</div>
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label for="yookassa_days_back">Дней назад</label>
                    <input type="number" id="yookassa_days_back" name="fin_settings[yookassa_days_back]" class="form-control"
                           value="<?= (int)($finSettings['yookassa_days_back'] ?? 150) ?>" min="1" max="365">
                    <div class="help-text">Глубина выгрузки платежей при синхронизации</div>
                </div>

                <div class="form-group">
                    <label for="yookassa_auto_sync">Автоимпорт</label>
                    <select id="yookassa_auto_sync" name="fin_settings[yookassa_auto_sync]" class="form-control">
                        <option value="0" <?= (($finSettings['yookassa_auto_sync'] ?? '0') == 1 ? '' : 'selected') ?>>Выключен</option>
                        <option value="1" <?= (($finSettings['yookassa_auto_sync'] ?? '0') == 1 ? 'selected' : '') ?>>Включён</option>
                    </select>
                    <div class="help-text">Автоматическое добавление платежей по cron</div>
                </div>
            </div>

            <div class="form-group commission-section">
                <label>Комиссии по способам оплаты</label>
                <div class="help-text">Процент комиссии для расчёта чистого дохода по каждому методу</div>
            </div>

            <div class="commission-grid">
                <?php foreach (YooKassaClient::supportedMethods() as $method): ?>
                    <div class="commission-item">
                        <label for="yoo_commission_<?= TemplateEngine::e($method) ?>">
                            <?= $commissionEmojis[$method] ?? '💳' ?> <?= TemplateEngine::e(YooKassaClient::methodLabel($method)) ?>
                        </label>
                        <input type="number" id="yoo_commission_<?= TemplateEngine::e($method) ?>" class="form-control"
                               name="fin_settings[yookassa_commissions][<?= TemplateEngine::e($method) ?>]"
                               value="<?= TemplateEngine::e($formatPercent($yooCommissions[$method] ?? 0)) ?>"
                               step="0.1" min="0" max="50">
                    </div>
                <?php endforeach; ?>
            </div>

            <div class="integration-footer">
                <?php if (!empty($finSettings['yookassa_last_sync'])): ?>
                    <div>Последняя синхронизация: <strong><?= TemplateEngine::e($finSettings['yookassa_last_sync']) ?></strong></div>
                <?php endif; ?>
                <?php if (!empty($finSettings['yookassa_last_error'])): ?>
                    <div class="text-error">Ошибка: <?= TemplateEngine::e($finSettings['yookassa_last_error']) ?></div>
                <?php endif; ?>
                <?php if ($yookassaCron !== ''): ?>
                    <div>Cron: <code><?= TemplateEngine::e($yookassaCron) ?></code></div>
                <?php endif; ?>
                <small>Секретные ключи хранятся в зашифрованном виде (AES-256).</small>
            </div>
        </div>
    </div>

    <div class="form-actions">
        <button type="submit" class="btn btn-primary"><?= icon('save') ?> Сохранить настройки</button>
    </div>
</form>

<script>
(function () {
    var tabs = document.querySelectorAll('.settings-tab');
    var panels = document.querySelectorAll('.settings-panel');
    tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            var name = tab.getAttribute('data-tab');
            tabs.forEach(function (t) {
                t.classList.toggle('active', t === tab);
            });
            panels.forEach(function (p) {
                p.classList.toggle('active', p.getAttribute('data-panel') === name);
            });
        });
    });
})();
</script>