<?php
/**
 * ВРЕМЕННЫЙ скрипт: создаёт страницы-секции темы (B) и
 * заполняет настройки темы hexaveil_* (A) значениями по умолчанию.
 *
 * Запуск в OSP (из корня сайта, т.е. home\HexaCMS\public):
 *     php seed-hexaveil.php
 *
 * После запуска УДАЛИТЕ файл.
 */

$_SERVER['HTTP_HOST'] = $_SERVER['HTTP_HOST'] ?? 'localhost';

define('ROOT_PATH', __DIR__);

require_once ROOT_PATH . '/config/config.php';
require_once CORE_PATH . '/Autoloader.php';
Autoloader::register();
require_once CORE_PATH . '/helpers.php';

$page = new Page();
$setting = new Setting();

// ============================================
// B: страницы-секции (длинный контент)
// ============================================

$howContent = <<<'HTML'
<div class="steps">
  <div class="step glass-card">
    <div class="step-number">1</div>
    <div class="step-content">
      <h3>Скачай клиент</h3>
      <p>Установи приложение для VPN (HAPP, INCY) на смартфон или компьютер. Это займёт всего минуту.</p>
    </div>
  </div>
  <div class="step glass-card">
    <div class="step-number">2</div>
    <div class="step-content">
      <h3>Импортируй конфиг</h3>
      <p>Скопируй ссылку на конфигурацию или отсканируй QR-код, который мы тебе дадим. Нажми «Подключиться» в клиенте.</p>
    </div>
  </div>
  <div class="step glass-card">
    <div class="step-number">3</div>
    <div class="step-content">
      <h3>Пользуйся без ограничений</h3>
      <p>Открывай любые сервисы, общайся в мессенджерах и работай с международными платформами как обычно.</p>
    </div>
  </div>
</div>
HTML;

$reviewsContent = <<<'HTML'
<div class="reviews-grid">
  <div class="review-card glass-card">
    <div class="review-stars">★★★★★</div>
    <p class="review-text">"Пользуюсь уже 8 месяцев. За это время ни разу не было серьёзных сбоев - даже в дни веерных отключений у других сервисов HexaVeil работал стабильно."</p>
    <div class="review-author">
      <div class="review-avatar">А</div>
      <div>
        <div class="review-name">Алексей</div>
        <div class="review-meta">Москва</div>
      </div>
    </div>
  </div>
  <div class="review-card glass-card">
    <div class="review-stars">★★★★★</div>
    <p class="review-text">"Скорость отличная - YouTube в 4K идёт без единой подгрузки, Netflix тоже. Раньше пробовала три других сервис, здесь реально лучше."</p>
    <div class="review-author">
      <div class="review-avatar">М</div>
      <div>
        <div class="review-name">Мария</div>
        <div class="review-meta">Санкт-Петербург</div>
      </div>
    </div>
  </div>
  <div class="review-card glass-card">
    <div class="review-stars">★★★★★</div>
    <p class="review-text">"Поддержка отвечает за 5 минут в любое время дня. Один раз сервер перегрузился - через 10 минут уже прислали новый конфиг. Респект."</p>
    <div class="review-author">
      <div class="review-avatar">Д</div>
      <div>
        <div class="review-name">Дмитрий</div>
        <div class="review-meta">Казань</div>
      </div>
    </div>
  </div>
</div>
HTML;

$faqContent = <<<'HTML'
<div class="faq-list">
  <details class="faq-item">
    <summary>Снижается ли скорость интернета?</summary>
    <p>Благодаря современным протоколам и выделенным серверам снижение скорости минимально - обычно не более 10–15%. При хорошем базовом интернете вы сможете смотреть видео в 4K и работать с международными сервисами без задержек.</p>
  </details>
  <details class="faq-item">
    <summary>Как получить конфигурацию после оплаты?</summary>
    <p>Сразу после оплаты вы получите письмо на почту со ссылкой на личный кабинет. Там будут доступны конфигурации для всех популярных клиентов: V2Ray, Sing-box, Shadowrocket, HAPP, Nekoray и других.</p>
  </details>
  <details class="faq-item">
    <summary>Что делать, если что-то не работает?</summary>
    <p>Напишите нам в Telegram-поддержку (ссылка в футере). Мы помогаем с настройкой 24/7 и всегда оперативно заменяем конфигурацию, если сервер перегружен. Среднее время ответа - 5 минут.</p>
  </details>
  <details class="faq-item">
    <summary>Храните ли вы историю моих посещений?</summary>
    <p>Нет. Мы не ведём журналы подключений и не храним историю вашей активности. На наших серверах технически нет механизмов для сбора таких данных - ваша приватность встроена в архитектуру сервиса.</p>
  </details>
  <details class="faq-item">
    <summary>Можно ли попробовать сервис бесплатно?</summary>
    <p>Да. Мы даём 24 часа полного доступа без ввода карты и автоматических списаний. Подпишитесь на наш Telegram-канал - бот пришлёт готовую конфигурацию. После триала решение о покупке остаётся за вами.</p>
  </details>
</div>
<div class="legal-note">
  <strong>Важно:</strong> HexaVeil - инструмент для защищённого соединения и доступа к международным сервисам. Мы не призываем к нарушению законодательства. Ответственность за использование сервиса в рамках закона несёт пользователь.
</div>
HTML;

$sectionPages = [
    'hexaveil-how'     => ['title' => 'Начни пользоваться за 3 шага',   'content' => $howContent],
    'hexaveil-reviews' => ['title' => 'Что говорят пользователи',       'content' => $reviewsContent],
    'hexaveil-faq'     => ['title' => 'Вопросы и ответы',               'content' => $faqContent],
];

foreach ($sectionPages as $slug => $p) {
    if ($page->getBySlug($slug)) {
        echo "Страница уже есть: {$slug}\n";
        continue;
    }
    $page->create([
        'title'            => $p['title'],
        'slug'             => $slug,
        'content'          => $p['content'],
        'meta_description' => '',
        'user_id'          => null,
        'template'         => 'default',
        'is_home'          => 0,
    ]);
    echo "Страница создана: {$slug}\n";
}

// ============================================
// A: настройки темы (заполняем только отсутствующие)
// ============================================

$defaults = [
    'hexaveil_cabinet_url'      => 'https://cabinet.fortf.ru/login',
    'hexaveil_referral_url'     => 'https://cabinet.fortf.ru/referral',
    'hexaveil_telegram_url'     => 'https://t.me/nova_vpn',
    'hexaveil_cta_label'        => 'Личный кабинет',

    'hexaveil_tagline_line1'    => 'Ваш надежный VPN&nbsp;провайдер',
    'hexaveil_tagline_line2'    => 'в мир интернета',
    'hexaveil_tagline_subtitle' => 'Смотрите любимые сериалы, работайте с международными сервисами и общайтесь без ограничений.',
    'hexaveil_tagline_btn1'     => 'Попробовать бесплатно',
    'hexaveil_tagline_btn2'     => 'Как это работает',

    'hexaveil_benefit1' => 'Все мировые сервисы: Instagram, YouTube без рекламы, ChatGPT, Netflix, Discord',
    'hexaveil_benefit2' => 'Российские сервисы работают - VPN не нужно выключать',
    'hexaveil_benefit3' => 'Живая поддержка 24/7 - решает вопросы, а не кормит ответами бота',
    'hexaveil_benefit4' => 'Стабильная работа благодаря распределённым серверам',

    'hexaveil_hero_note' => 'Выберите сервер — планета подлетит к нему',

    'hexaveil_stat1_num'   => '10+',
    'hexaveil_stat1_label' => 'Стран с серверами',
    'hexaveil_stat2_num'   => '99.9%',
    'hexaveil_stat2_label' => 'Время работы (Uptime)',
    'hexaveil_stat3_num'   => '10 Гбит/с',
    'hexaveil_stat3_label' => 'Пропускная способность',
    'hexaveil_stat4_num'   => '10K+',
    'hexaveil_stat4_label' => 'Активных пользователей',

    'hexaveil_trial_badge'    => 'Без оплаты и обязательств',
    'hexaveil_trial_title'    => 'Попробуйте HexaVeil бесплатно',
    'hexaveil_trial_subtitle' => 'Получите 24 часа полного доступа - без ввода карты и автоматических списаний. Убедитесь в скорости и стабильности на реальных сервисах, и только потом решайте.',
    'hexaveil_trial_step1_title' => 'Авторизуйтесь',
    'hexaveil_trial_step1_text'  => 'Авторизуйтесь в личном кабинете удобным для тебя способом',
    'hexaveil_trial_step2_title' => 'Получите конфиг',
    'hexaveil_trial_step2_text'  => 'Бот пришлёт готовую конфигурацию для вашего устройства',
    'hexaveil_trial_step3_title' => 'Подключайтесь',
    'hexaveil_trial_step3_text'  => 'Импортируйте в любой клиент - и пользуйтесь 72 часа',
    'hexaveil_trial_button'      => 'Получить бесплатный доступ',
    'hexaveil_trial_note'        => 'Триал ограничен одним устройством на аккаунт. Без автосписаний - решение за вами.',

    'hexaveil_feature1_title' => 'Доступ к любимым сервисам',
    'hexaveil_feature1_text'  => 'YouTube, ChatGPT, Netflix, Spotify и другие международные платформы - стабильно, быстро и без лишних действий.',
    'hexaveil_feature2_title' => 'Защищённое соединение',
    'hexaveil_feature2_text'  => 'Ваш трафик шифруется и проходит через наши серверы. Провайдер не видит, какие ресурсы вы посещаете.',
    'hexaveil_feature3_title' => '10+ стран мира',
    'hexaveil_feature3_text'  => 'Серверы в Европе, Азии и Америке. Выбирайте локацию для минимальной задержки и максимальной скорости.',
    'hexaveil_feature4_title' => 'Стриминг без буферизации',
    'hexaveil_feature4_text'  => 'Видео в 4K и музыка в высоком качестве - без задержек и прерываний. Выделенные каналы для медиа-трафика.',

    'hexaveil_services_title' => 'Открой любимые сервисы',
    'hexaveil_services_intro' => 'Мы гарантируем стабильное соединение с самыми популярными международными платформами.',
    'hexaveil_services_list'  => "YouTube\nChatGPT\nNetflix\nSpotify\nClaude AI\nX (Twitter)\nDiscord",
    'hexaveil_services_note'  => 'Список сервисов регулярно расширяется. Если нужной платформы нет в списке - напишите в поддержку, добавим.',

    'hexaveil_tech1_title' => 'Современный протокол',
    'hexaveil_tech1_text'  => 'VLESS - для скорости и незаметности трафика.',
    'hexaveil_tech2_title' => 'Без журналов подключений',
    'hexaveil_tech2_text'  => 'Мы не отслеживаем ваши действия и не сохраняем историю посещений. Ваша приватность для нас действительно важна!',
    'hexaveil_tech3_title' => 'Шифрование AES-256',
    'hexaveil_tech3_text'  => 'Ваши данные защищены военным стандартом шифрования. Трафик невозможно перехватить и прочитать.',

    'hexaveil_referral_title'        => 'Приглашайте друзей - получайте бонусы',
    'hexaveil_referral_intro'        => 'Делитесь персональной ссылкой: вы и друг получите по 50 ₽, а вы - ещё 20% с его пополнений. Чем больше друзей - тем выгоднее.',
    'hexaveil_referral_card1_value'  => '+50 ₽',
    'hexaveil_referral_card1_title'  => 'Вам за друга',
    'hexaveil_referral_card1_text'   => 'За каждого друга, который оплатит подписку по вашей ссылке',
    'hexaveil_referral_card2_value'  => '+50 ₽',
    'hexaveil_referral_card2_title'  => 'Другу на старт',
    'hexaveil_referral_card2_text'   => 'Подарок другу к первой оплате по вашей ссылке',
    'hexaveil_referral_card3_value'  => '20%',
    'hexaveil_referral_card3_title'  => 'С пополнений',
    'hexaveil_referral_card3_text'   => 'Процент с пополнений ваших рефералов - навсегда',
    'hexaveil_referral_button'       => 'Получить реферальную ссылку',
    'hexaveil_referral_note'         => 'Бонусы начисляются автоматически в личном кабинете после оплаты минимальной суммы в 150 ₽ рефералом.',

    'hexaveil_footer_copyright' => '© 2026 HexaVeil. Защищённый доступ к мировому интернету.',
];

$added = 0;
foreach ($defaults as $key => $value) {
    if ($setting->get($key) === null) {
        $setting->set($key, $value);
        $added++;
    }
}

echo "Настройки темы добавлены (новых): {$added}\n";
echo "OK: страницы и настройки темы готовы. Удалите seed-hexaveil.php\n";
