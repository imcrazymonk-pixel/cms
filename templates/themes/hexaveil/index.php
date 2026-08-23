<?php
/**
 * Шаблон главной страницы (лендинг HexaVeil).
 * Тексты и ссылки берутся из настроек темы (раздел «Тема HexaVeil» в админке),
 * блоки «Как это работает», «Отзывы» и «FAQ» — из страниц CMS
 * (slug hexaveil-how / hexaveil-reviews / hexaveil-faq).
 */
$__hexaPageModel = new Page();
$__hexaHow = $__hexaPageModel->getBySlug('hexaveil-how');
$__hexaReviews = $__hexaPageModel->getBySlug('hexaveil-reviews');
$__hexaFaq = $__hexaPageModel->getBySlug('hexaveil-faq');
?>
    <!-- ============ TAGLINE (заголовок + выгоды над hero) ============ -->
    <section class="tagline">
      <div class="container">
        <h2 class="tagline-title">
          <?= theme_setting('hexaveil_tagline_line1', 'Ваш надежный VPN&nbsp;провайдер') ?><br />
          <span class="tagline-accent"><?= theme_setting('hexaveil_tagline_line2', 'в мир интернета') ?></span>
        </h2>

        <p class="tagline-subtitle sub-desktop"><span class="sub-line"><?= theme_setting('hexaveil_tagline_subtitle', 'Смотрите любимые сериалы, работайте с международными сервисами и общайтесь без ограничений.') ?></span></p>
        <p class="tagline-subtitle sub-mobile"><span class="sub-line"><?= theme_setting('hexaveil_tagline_subtitle', 'Смотрите любимые сериалы, работайте с международными сервисами и общайтесь без ограничений.') ?></span></p>

        <div class="tagline-actions">
          <a href="#trial" class="btn btn-primary"><?= theme_setting('hexaveil_tagline_btn1', 'Попробовать бесплатно') ?></a>
          <a href="#features" class="btn btn-outline"><?= theme_setting('hexaveil_tagline_btn2', 'Как это работает') ?></a>
        </div>

        <div class="hero-benefits">
          <div class="hero-benefit">
            <svg class="icon" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true"><path d="M80.3 44C69.8 69.9 64 98.2 64 128s5.8 58.1 16.3 84c6.6 16.4-1.3 35-17.7 41.7s-35-1.3-41.7-17.7C7.4 202.6 0 166.1 0 128S7.4 53.4 20.9 20C27.6 3.6 46.2-4.3 62.6 2.3S86.9 27.6 80.3 44zM555.1 20C568.6 53.4 576 89.9 576 128s-7.4 74.6-20.9 108c-6.6 16.4-25.3 24.3-41.7 17.7S489.1 228.4 495.7 212c10.5-25.9 16.3-54.2 16.3-84s-5.8-58.1-16.3-84C489.1 27.6 497 9 513.4 2.3s35 1.3 41.7 17.7zM352 128c0 23.7-12.9 44.4-32 55.4V480c0 17.7-14.3 32-32 32s-32-14.3-32-32V183.4c-19.1-11.1-32-31.7-32-55.4c0-35.3 28.7-64 64-64s64 28.7 64 64zM170.6 76.8C163.8 92.4 160 109.7 160 128s3.8 35.6 10.6 51.2c7.1 16.2-.3 35.1-16.5 42.1s-35.1-.3-42.1-16.5c-10.3-23.6-16-49.6-16-76.8s5.7-53.2 16-76.8c7.1-16.2 25.9-23.6 42.1-16.5s23.6 25.9 16.5 42.1zM464 51.2c10.3 23.6 16 49.6 16 76.8s-5.7 53.2-16 76.8c-7.1 16.2-25.9 23.6-42.1 16.5s-23.6-25.9-16.5-42.1c6.8-15.6 10.6-32.9 10.6-51.2s-3.8-35.6-10.6-51.2c-7.1-16.2 .3-35.1 16.5-42.1s35.1 .3 42.1 16.5z"/></svg>
            <span>
              <?= theme_setting('hexaveil_benefit1', 'Все мировые сервисы: Instagram, YouTube без рекламы, ChatGPT, Netflix, Discord') ?>
            </span>
          </div>
          <div class="hero-benefit">
            <svg class="icon" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true"><path d="M243.4 2.6l-224 96c-14 6-21.8 21-18.7 35.8S16.8 160 32 160v8c0 13.3 10.7 24 24 24H456c13.3 0 24-10.7 24-24v-8c15.2 0 28.3-10.7 31.3-25.6s-4.8-29.9-18.7-35.8l-224-96c-8-3.4-17.2-3.4-25.2 0zM128 224H64V420.3c-.6 .3-1.2 .7-1.8 1.1l-48 32c-11.7 7.8-17 22.4-12.9 35.9S17.9 512 32 512H480c14.1 0 26.5-9.2 30.6-22.7s-1.1-28.1-12.9-35.9l-48-32c-.6-.4-1.2-.7-1.8-1.1V224H384V416H344V224H280V416H232V224H168V416H128V224zM256 64a32 32 0 1 1 0 64 32 32 0 1 1 0-64z"/></svg>
            <span>
              <?= theme_setting('hexaveil_benefit2', 'Российские сервисы работают - VPN не нужно выключать') ?>
            </span>
          </div>
          <div class="hero-benefit">
            <svg class="icon" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true"><path d="M256 48C141.1 48 48 141.1 48 256v40c0 13.3-10.7 24-24 24s-24-10.7-24-24V256C0 114.6 114.6 0 256 0S512 114.6 512 256V400.1c0 48.6-39.4 88-88.1 88L313.6 488c-8.3 14.3-23.8 24-41.6 24H240c-26.5 0-48-21.5-48-48s21.5-48 48-48h32c17.8 0 33.3 9.7 41.6 24l110.4 .1c22.1 0 40-17.9 40-40V256c0-114.9-93.1-208-208-208zM144 208h16c17.7 0 32 14.3 32 32V352c0 17.7-14.3 32-32 32H144c-35.3 0-64-28.7-64-64V272c0-35.3 28.7-64 64-64zm224 0c35.3 0 64 28.7 64 64v48c0 35.3-28.7 64-64 64H352c-17.7 0-32-14.3-32-32V240c0-17.7 14.3-32 32-32h16z"/></svg>
            <span>
              <?= theme_setting('hexaveil_benefit3', 'Живая поддержка 24/7 - решает вопросы, а не кормит ответами бота') ?>
            </span>
          </div>
          <div class="hero-benefit">
            <svg class="icon" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true"><path d="M64 32C28.7 32 0 60.7 0 96v64c0 35.3 28.7 64 64 64H448c35.3 0 64-28.7 64-64V96c0-35.3-28.7-64-64-64H64zm280 72a24 24 0 1 1 0 48 24 24 0 1 1 0-48zm48 24a24 24 0 1 1 48 0 24 24 0 1 1 -48 0zM64 288c-35.3 0-64 28.7-64 64v64c0 35.3 28.7 64 64 64H448c35.3 0 64-28.7 64-64V352c0-35.3-28.7-64-64-64H64zm280 72a24 24 0 1 1 0 48 24 24 0 1 1 0-48zm56 24a24 24 0 1 1 48 0 24 24 0 1 1 -48 0z"/></svg>
            <span><?= theme_setting('hexaveil_benefit4', 'Стабильная работа благодаря распределённым серверам') ?></span>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ HERO ============ -->
    <section class="hero">
      <div class="container">
        <div class="hero-left">
          <div class="hero-server-panel">
            <div class="server-panel-head">
              <h3>Серверы</h3>
              <span class="server-count" id="serverCount">0</span>
            </div>

            <div class="server-search-wrap">
              <input
                type="text"
                class="server-search"
                id="serverSearch"
                placeholder="Поиск сервера…"
                aria-label="Поиск сервера"
              />
              <button
                type="button"
                class="server-search-clear"
                id="serverSearchClear"
                aria-label="Очистить поиск"
                tabindex="-1"
              >
                <svg class="icon" viewBox="0 0 384 512" fill="currentColor" aria-hidden="true"><path d="M342.6 150.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L192 210.7 86.6 105.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L146.7 256 41.4 361.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L192 301.3 297.4 406.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L237.3 256 342.6 150.6z"/></svg>
              </button>
            </div>

            <div class="server-list" id="serverList"></div>

            <!-- Телеметрия (сворачивается на мобильных) -->
            <details class="panel-block" open>
              <summary class="panel-block-title">Телеметрия</summary>
              <div class="telemetry-row">
                <span>Загрузка магистрали</span>
                <span class="setting-value" id="telemetryPct">0%</span>
              </div>
              <div class="telemetry-bar">
                <div class="telemetry-fill" id="telemetryBar"></div>
              </div>
              <div class="telemetry-meta">
                <span>Маршрутов: <b id="telemetryRoutes">0</b></span>
                <span>Активных: <b id="telemetrySpeed">0</b></span>
              </div>
            </details>

            <!-- Терминал-лог (сворачивается на мобильных) -->
            <details class="panel-block" open>
              <summary class="panel-block-title">
                <span>Монитор сети</span>
                <span class="live-dot"></span>
              </summary>
              <div class="net-log" id="netLog"></div>
            </details>

            <div class="server-panel-note">
              <?= theme_setting('hexaveil_hero_note', 'Выберите сервер — планета подлетит к нему') ?>
            </div>
          </div>
        </div>

        <div class="hero-visual">
          <div class="globe">
            <canvas id="planetCanvas" aria-hidden="true"></canvas>
            <div class="planet-labels" id="planetLabels"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ STATS ============ -->
    <section class="section stats-section">
      <div class="container">
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-number"><?= theme_setting('hexaveil_stat1_num', '10+') ?></div>
            <div class="stat-label"><?= theme_setting('hexaveil_stat1_label', 'Стран с серверами') ?></div>
          </div>
          <div class="stat-item">
            <div class="stat-number"><?= theme_setting('hexaveil_stat2_num', '99.9%') ?></div>
            <div class="stat-label"><?= theme_setting('hexaveil_stat2_label', 'Время работы (Uptime)') ?></div>
          </div>
          <div class="stat-item">
            <div class="stat-number"><?= theme_setting('hexaveil_stat3_num', '10 Гбит/с') ?></div>
            <div class="stat-label"><?= theme_setting('hexaveil_stat3_label', 'Пропускная способность') ?></div>
          </div>
          <div class="stat-item">
            <div class="stat-number"><?= theme_setting('hexaveil_stat4_num', '10K+') ?></div>
            <div class="stat-label"><?= theme_setting('hexaveil_stat4_label', 'Активных пользователей') ?></div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ TRIAL (Бесплатный вход в воронку) ============ -->
    <section class="section" id="trial">
      <div class="container">
        <div class="trial-card glass-card">
          <span class="trial-badge">
            <svg class="icon" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true"><path d="M190.5 68.8L225.3 128H224 152c-22.1 0-40-17.9-40-40s17.9-40 40-40h2.2c14.9 0 28.8 7.9 36.3 20.8zM64 88c0 14.4 3.5 28 9.6 40H32c-17.7 0-32 14.3-32 32v64c0 17.7 14.3 32 32 32H480c17.7 0 32-14.3 32-32V160c0-17.7-14.3-32-32-32H438.4c6.1-12 9.6-25.6 9.6-40c0-48.6-39.4-88-88-88h-2.2c-31.9 0-61.5 16.9-77.7 44.4L256 85.5l-24.1-41C215.7 16.9 186.1 0 154.2 0H152C103.4 0 64 39.4 64 88zm336 0c0 22.1-17.9 40-40 40H288h-1.3l34.8-59.2C329.1 55.9 342.9 48 357.8 48H360c22.1 0 40 17.9 40 40zM32 288V464c0 26.5 21.5 48 48 48H224V288H32zM288 512H432c26.5 0 48-21.5 48-48V288H288V512z"/></svg>
            <?= theme_setting('hexaveil_trial_badge', 'Без оплаты и обязательств') ?>
          </span>

          <h2 class="trial-title"><?= theme_setting('hexaveil_trial_title', 'Попробуйте HexaVeil бесплатно') ?></h2>
          <p class="trial-subtitle">
            <?= theme_setting('hexaveil_trial_subtitle', 'Получите 24 часа полного доступа - без ввода карты и автоматических списаний. Убедитесь в скорости и стабильности на реальных сервисах, и только потом решайте.') ?>
          </p>

          <div class="trial-steps">
            <div class="trial-step">
              <div class="trial-step-num">1</div>
              <h4><?= theme_setting('hexaveil_trial_step1_title', 'Авторизуйтесь') ?></h4>
              <p><?= theme_setting('hexaveil_trial_step1_text', 'Авторизуйтесь в личном кабинете удобным для тебя способом') ?></p>
            </div>
            <div class="trial-step">
              <div class="trial-step-num">2</div>
              <h4><?= theme_setting('hexaveil_trial_step2_title', 'Получите конфиг') ?></h4>
              <p><?= theme_setting('hexaveil_trial_step2_text', 'Бот пришлёт готовую конфигурацию для вашего устройства') ?></p>
            </div>
            <div class="trial-step">
              <div class="trial-step-num">3</div>
              <h4><?= theme_setting('hexaveil_trial_step3_title', 'Подключайтесь') ?></h4>
              <p><?= theme_setting('hexaveil_trial_step3_text', 'Импортируйте в любой клиент - и пользуйтесь 72 часа') ?></p>
            </div>
          </div>

          <a
            href="<?= theme_setting('hexaveil_cabinet_url', 'https://cabinet.fortf.ru/login') ?>"
            class="btn btn-primary"
            target="_blank"
            rel="noopener"
          >
            <svg class="icon" viewBox="0 0 496 512" fill="currentColor" aria-hidden="true"><path d="M248,8C111.033,8,0,119.033,0,256S111.033,504,248,504,496,392.967,496,256,384.967,8,248,8ZM362.952,176.66c-3.732,39.215-19.881,134.378-28.1,178.3-3.476,18.584-10.322,24.816-16.948,25.425-14.4,1.326-25.338-9.517-39.287-18.661-21.827-14.308-34.158-23.215-55.346-37.177-24.485-16.135-8.612-25,5.342-39.5,3.652-3.793,67.107-61.51,68.335-66.746.153-.655.3-3.1-1.154-4.384s-3.59-.849-5.135-.5q-3.283.746-104.608,69.142-14.845,10.194-26.894,9.934c-8.855-.191-25.888-5.006-38.551-9.123-15.531-5.048-27.875-7.717-26.8-16.291q.84-6.7,18.45-13.7,108.446-47.248,144.628-62.3c68.872-28.647,83.183-33.623,92.511-33.789,2.052-.034,6.639.474,9.61,2.885a10.452,10.452,0,0,1,3.53,6.716A43.765,43.765,0,0,1,362.952,176.66Z"/></svg>
            <?= theme_setting('hexaveil_trial_button', 'Получить бесплатный доступ') ?>
          </a>

          <p class="trial-note">
            <?= theme_setting('hexaveil_trial_note', 'Триал ограничен одним устройством на аккаунт. Без автосписаний - решение за вами.') ?>
          </p>
          <p class="trial-note">ВИДЕОИНСТРУКЦИЯ</p>
        </div>
      </div>
    </section>

    <!-- ============ FEATURES ============ -->
    <section class="section features" id="features">
      <div class="container">
        <h2 class="section-title">Почему выбирают HexaVeil</h2>

        <div class="grid">
          <div class="feature-card glass-card">
            <div class="feature-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 48 48"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <circle
                  cx="24"
                  cy="24"
                  r="20"
                  stroke="#a855f7"
                  stroke-width="2"
                  fill="rgba(168,85,247,0.1)"
                />
                <path
                  d="M16 24l6 6 10-12"
                  stroke="#a855f7"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
            <h3><?= theme_setting('hexaveil_feature1_title', 'Доступ к любимым сервисам') ?></h3>
            <p>
              <?= theme_setting('hexaveil_feature1_text', 'YouTube, ChatGPT, Netflix, Spotify и другие международные платформы - стабильно, быстро и без лишних действий.') ?>
            </p>
          </div>

          <div class="feature-card glass-card">
            <div class="feature-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 48 48"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <rect
                  x="10"
                  y="20"
                  width="28"
                  height="20"
                  rx="3"
                  stroke="#a855f7"
                  stroke-width="2"
                  fill="rgba(168,85,247,0.1)"
                />
                <path
                  d="M16 20v-4a8 8 0 0116 0v4"
                  stroke="#a855f7"
                  stroke-width="2"
                  stroke-linecap="round"
                />
                <circle cx="24" cy="30" r="2" fill="#a855f7" />
              </svg>
            </div>
            <h3><?= theme_setting('hexaveil_feature2_title', 'Защищённое соединение') ?></h3>
            <p>
              <?= theme_setting('hexaveil_feature2_text', 'Ваш трафик шифруется и проходит через наши серверы. Провайдер не видит, какие ресурсы вы посещаете.') ?>
            </p>
          </div>

          <div class="feature-card glass-card">
            <div class="feature-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 48 48"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <circle
                  cx="24"
                  cy="24"
                  r="18"
                  stroke="#a855f7"
                  stroke-width="2"
                  fill="rgba(168,85,247,0.1)"
                />
                <path
                  d="M6 24h36M24 6c6 6 6 30 0 36M24 6c-6 6-6 30 0 36"
                  stroke="#a855f7"
                  stroke-width="1.5"
                  fill="none"
                />
              </svg>
            </div>
            <h3><?= theme_setting('hexaveil_feature3_title', '10+ стран мира') ?></h3>
            <p>
              <?= theme_setting('hexaveil_feature3_text', 'Серверы в Европе, Азии и Америке. Выбирайте локацию для минимальной задержки и максимальной скорости.') ?>
            </p>
          </div>

          <div class="feature-card glass-card">
            <div class="feature-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 48 48"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M14 34V22l10-8 10 8v12H14z"
                  stroke="#a855f7"
                  stroke-width="2"
                  fill="rgba(168,85,247,0.1)"
                />
                <path d="M20 34v-8h8v8" stroke="#a855f7" stroke-width="2" />
                <path
                  d="M10 22l14-11 14 11"
                  stroke="#a855f7"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  fill="none"
                />
              </svg>
            </div>
            <h3><?= theme_setting('hexaveil_feature4_title', 'Стриминг без буферизации') ?></h3>
            <p>
              <?= theme_setting('hexaveil_feature4_text', 'Видео в 4K и музыка в высоком качестве - без задержек и прерываний. Выделенные каналы для медиа-трафика.') ?>
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ SERVICES ============ -->
    <section class="section" id="services">
      <div class="container">
        <h2 class="section-title"><?= theme_setting('hexaveil_services_title', 'Открой любимые сервисы') ?></h2>
        <p>
          <?= theme_setting('hexaveil_services_intro', 'Мы гарантируем стабильное соединение с самыми популярными международными платформами.') ?>
        </p>

        <div class="services-grid">
          <?php
          $__services = preg_split('/\r\n|\r|\n/', theme_setting('hexaveil_services_list', "YouTube\nChatGPT\nNetflix\nSpotify\nClaude AI\nX (Twitter)\nDiscord"), -1, PREG_SPLIT_NO_EMPTY);
          foreach ($__services as $__serviceName):
          ?>
          <div class="service-item">
            <span class="service-name"><?= TemplateEngine::e($__serviceName) ?></span>
            <span class="service-status available">Доступен</span>
          </div>
          <?php endforeach; ?>
        </div>

        <p class="services-note">
          <?= theme_setting('hexaveil_services_note', 'Список сервисов регулярно расширяется. Если нужной платформы нет в списке - напишите в поддержку, добавим.') ?>
        </p>
      </div>
    </section>

    <!-- ============ TECH ============ -->
    <section class="section">
      <div class="container">
        <h2 class="section-title">Технологии, которым можно доверять</h2>

        <div class="tech-grid">
          <div class="tech-block glass-card">
            <div class="tech-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 48 48"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M8 16l16-8 16 8-16 8-16-8z"
                  stroke="#a855f7"
                  stroke-width="2"
                  fill="rgba(168,85,247,0.1)"
                />
                <path
                  d="M8 24l16 8 16-8M8 32l16 8 16-8"
                  stroke="#a855f7"
                  stroke-width="2"
                  stroke-linejoin="round"
                  fill="none"
                />
              </svg>
            </div>
            <h3><?= theme_setting('hexaveil_tech1_title', 'Современный протокол') ?></h3>
            <p><?= theme_setting('hexaveil_tech1_text', 'VLESS - для скорости и незаметности трафика.') ?></p>
          </div>

          <div class="tech-block glass-card">
            <div class="tech-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 48 48"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M24 6L8 14v10c0 10 6.8 19.3 16 22 9.2-2.7 16-12 16-22V14L24 6z"
                  stroke="#a855f7"
                  stroke-width="2"
                  fill="rgba(168,85,247,0.1)"
                />
                <path
                  d="M18 24l4 4 8-8"
                  stroke="#a855f7"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  fill="none"
                />
              </svg>
            </div>
            <h3><?= theme_setting('hexaveil_tech2_title', 'Без журналов подключений') ?></h3>
            <p>
              <?= theme_setting('hexaveil_tech2_text', 'Мы не отслеживаем ваши действия и не сохраняем историю посещений. Ваша приватность для нас действительно важна!') ?>
            </p>
          </div>

          <div class="tech-block glass-card">
            <div class="tech-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 48 48"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <rect
                  x="10"
                  y="22"
                  width="28"
                  height="18"
                  rx="3"
                  stroke="#a855f7"
                  stroke-width="2"
                  fill="rgba(168,85,247,0.1)"
                />
                <path
                  d="M16 22v-6a8 8 0 0116 0v6"
                  stroke="#a855f7"
                  stroke-width="2"
                  stroke-linecap="round"
                />
                <circle cx="24" cy="31" r="2.5" fill="#a855f7" />
                <path
                  d="M24 33.5v3"
                  stroke="#a855f7"
                  stroke-width="2"
                  stroke-linecap="round"
                />
              </svg>
            </div>
            <h3><?= theme_setting('hexaveil_tech3_title', 'Шифрование AES-256') ?></h3>
            <p>
              <?= theme_setting('hexaveil_tech3_text', 'Ваши данные защищены военным стандартом шифрования. Трафик невозможно перехватить и прочитать.') ?>
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ HOW IT WORKS (страница hexaveil-how) ============ -->
    <section class="section how-it-works">
      <div class="container">
        <h2 class="section-title"><?= $__hexaHow ? TemplateEngine::e($__hexaHow['title']) : 'Начни пользоваться за 3 шага' ?></h2>

        <?php if ($__hexaHow && !empty($__hexaHow['content'])): ?>
        <?= $__hexaHow['content'] ?>
        <?php else: ?>
        <div class="steps">
          <div class="step glass-card">
            <div class="step-number">1</div>
            <div class="step-content">
              <h3>Скачай клиент</h3>
              <p>
                Установи приложение для VPN (HAPP, INCY) на смартфон или
                компьютер. Это займёт всего минуту.
              </p>
            </div>
          </div>

          <div class="step glass-card">
            <div class="step-number">2</div>
            <div class="step-content">
              <h3>Импортируй конфиг</h3>
              <p>
                Скопируй ссылку на конфигурацию или отсканируй QR-код, который
                мы тебе дадим. Нажми «Подключиться» в клиенте.
              </p>
            </div>
          </div>

          <div class="step glass-card">
            <div class="step-number">3</div>
            <div class="step-content">
              <h3>Пользуйся без ограничений</h3>
              <p>
                Открывай любые сервисы, общайся в мессенджерах и работай с
                международными платформами как обычно.
              </p>
            </div>
          </div>
        </div>
        <?php endif; ?>
      </div>
    </section>

    <!-- ============ REFERRAL ============ -->
    <section class="section" id="referral">
      <div class="container">
        <h2 class="section-title"><?= theme_setting('hexaveil_referral_title', 'Приглашайте друзей - получайте бонусы') ?></h2>
        <p class="referral-intro">
          <?= theme_setting('hexaveil_referral_intro', 'Делитесь персональной ссылкой: вы и друг получите по 50 ₽, а вы - ещё 20% с его пополнений. Чем больше друзей - тем выгоднее.') ?>
        </p>

        <div class="referral-grid">
          <div class="referral-card glass-card">
            <div class="referral-value"><?= theme_setting('hexaveil_referral_card1_value', '+50 ₽') ?></div>
            <h3><?= theme_setting('hexaveil_referral_card1_title', 'Вам за друга') ?></h3>
            <p><?= theme_setting('hexaveil_referral_card1_text', 'За каждого друга, который оплатит подписку по вашей ссылке') ?></p>
          </div>

          <div class="referral-card glass-card">
            <div class="referral-value"><?= theme_setting('hexaveil_referral_card2_value', '+50 ₽') ?></div>
            <h3><?= theme_setting('hexaveil_referral_card2_title', 'Другу на старт') ?></h3>
            <p><?= theme_setting('hexaveil_referral_card2_text', 'Подарок другу к первой оплате по вашей ссылке') ?></p>
          </div>

          <div class="referral-card glass-card">
            <div class="referral-value"><?= theme_setting('hexaveil_referral_card3_value', '20%') ?></div>
            <h3><?= theme_setting('hexaveil_referral_card3_title', 'С пополнений') ?></h3>
            <p><?= theme_setting('hexaveil_referral_card3_text', 'Процент с пополнений ваших рефералов - навсегда') ?></p>
          </div>
        </div>

        <div class="referral-cta">
          <a href="<?= theme_setting('hexaveil_referral_url', 'https://cabinet.fortf.ru/referral') ?>" class="btn btn-primary">
            <svg class="icon" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true"><path d="M579.8 267.7c56.5-56.5 56.5-148 0-204.5c-50-50-128.8-56.5-186.3-15.4l-1.6 1.1c-14.4 10.3-17.7 30.3-7.4 44.6s30.3 17.7 44.6 7.4l1.6-1.1c32.1-22.9 76-19.3 103.8 8.6c31.5 31.5 31.5 82.5 0 114L422.3 334.8c-31.5 31.5-82.5 31.5-114 0c-27.9-27.9-31.5-71.8-8.6-103.8l1.1-1.6c10.3-14.4 6.9-34.4-7.4-44.6s-34.4-6.9-44.6 7.4l-1.1 1.6C206.5 251.2 213 330 263 380c56.5 56.5 148 56.5 204.5 0L579.8 267.7zM60.2 244.3c-56.5 56.5-56.5 148 0 204.5c50 50 128.8 56.5 186.3 15.4l1.6-1.1c14.4-10.3 17.7-30.3 7.4-44.6s-30.3-17.7-44.6-7.4l-1.6 1.1c-32.1 22.9-76 19.3-103.8-8.6C74 372 74 321 105.5 289.5L217.7 177.2c31.5-31.5 82.5-31.5 114 0c27.9 27.9 31.5 71.8 8.6 103.9l-1.1 1.6c-10.3 14.4-6.9 34.4 7.4 44.6s34.4 6.9 44.6-7.4l1.1-1.6C433.5 260.8 427 182 377 132c-56.5-56.5-148-56.5-204.5 0L60.2 244.3z"/></svg>
            <?= theme_setting('hexaveil_referral_button', 'Получить реферальную ссылку') ?>
          </a>
          <p class="trial-note">
            <?= theme_setting('hexaveil_referral_note', 'Бонусы начисляются автоматически в личном кабинете после оплаты минимальной суммы в 150 ₽ рефералом.') ?>
          </p>
        </div>
      </div>
    </section>

    <!-- ============ PRICING (выключен) ============ -->
    <!--<section class="section pricing" id="pricing">
      <div class="container">
        <h2 class="section-title">Выбери свой план</h2>
        <div class="pricing-grid">
          <div class="pricing-card glass-card">
            <h3>Trial</h3>
            <div class="price">0 ₽</div>
            <ul class="price-features">
              <li>24 часа полного доступа</li>
              <li>Без ввода карты</li>
              <li>1 устройство</li>
              <li>3 страны на выбор</li>
              <li>Скорость до 1000 Мбит/с</li>
            </ul>
            <a href="#trial" class="btn btn-outline">Попробовать бесплатно</a>
          </div>
        </div>
      </div>
    </section>-->

    <!-- ============ REVIEWS (страница hexaveil-reviews) ============ -->
    <section class="section">
      <div class="container">
        <h2 class="section-title"><?= $__hexaReviews ? TemplateEngine::e($__hexaReviews['title']) : 'Что говорят пользователи' ?></h2>

        <?php if ($__hexaReviews && !empty($__hexaReviews['content'])): ?>
        <?= $__hexaReviews['content'] ?>
        <?php else: ?>
        <div class="reviews-grid">
          <div class="review-card glass-card">
            <div class="review-stars">★★★★★</div>
            <p class="review-text">
              "Пользуюсь уже 8 месяцев. За это время ни разу не было серьёзных
              сбоев - даже в дни веерных отключений у других сервисов HexaVeil
              работал стабильно."
            </p>
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
            <p class="review-text">
              "Скорость отличная - YouTube в 4K идёт без единой подгрузки,
              Netflix тоже. Раньше пробовала три других сервис, здесь реально
              лучше."
            </p>
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
            <p class="review-text">
              "Поддержка отвечает за 5 минут в любое время дня. Один раз сервер
              перегрузился - через 10 минут уже прислали новый конфиг. Респект."
            </p>
            <div class="review-author">
              <div class="review-avatar">Д</div>
              <div>
                <div class="review-name">Дмитрий</div>
                <div class="review-meta">Казань</div>
              </div>
            </div>
          </div>
        </div>
        <?php endif; ?>
      </div>
    </section>

    <!-- ============ FAQ (страница hexaveil-faq) ============ -->
    <section class="section" id="faq">
      <div class="container">
        <h2 class="section-title"><?= $__hexaFaq ? TemplateEngine::e($__hexaFaq['title']) : 'Вопросы и ответы' ?></h2>

        <?php if ($__hexaFaq && !empty($__hexaFaq['content'])): ?>
        <?= $__hexaFaq['content'] ?>
        <?php else: ?>
        <div class="faq-list">
          <details class="faq-item">
            <summary>Снижается ли скорость интернета?</summary>
            <p>
              Благодаря современным протоколам и выделенным серверам снижение
              скорости минимально - обычно не более 10–15%. При хорошем базовом
              интернете вы сможете смотреть видео в 4K и работать с
              международными сервисами без задержек.
            </p>
          </details>

          <details class="faq-item">
            <summary>Как получить конфигурацию после оплаты?</summary>
            <p>
              Сразу после оплаты вы получите письмо на почту со ссылкой на
              личный кабинет. Там будут доступны конфигурации для всех
              популярных клиентов: V2Ray, Sing-box, Shadowrocket, HAPP, Nekoray
              и других.
            </p>
          </details>

          <details class="faq-item">
            <summary>Что делать, если что-то не работает?</summary>
            <p>
              Напишите нам в Telegram-поддержку (ссылка в футере). Мы помогаем с
              настройкой 24/7 и всегда оперативно заменяем конфигурацию, если
              сервер перегружен. Среднее время ответа - 5 минут.
            </p>
          </details>

          <details class="faq-item">
            <summary>Храните ли вы историю моих посещений?</summary>
            <p>
              Нет. Мы не ведём журналы подключений и не храним историю вашей
              активности. На наших серверах технически нет механизмов для сбора
              таких данных - ваша приватность встроена в архитектуру сервиса.
            </p>
          </details>

          <details class="faq-item">
            <summary>Можно ли попробовать сервис бесплатно?</summary>
            <p>
              Да. Мы даём 24 часа полного доступа без ввода карты и
              автоматических списаний. Подпишитесь на наш Telegram-канал - бот
              пришлёт готовую конфигурацию. После триала решение о покупке
              остаётся за вами.
            </p>
          </details>
        </div>

        <div class="legal-note">
          <strong>Важно:</strong> HexaVeil - инструмент для защищённого
          соединения и доступа к международным сервисам. Мы не призываем к
          нарушению законодательства. Ответственность за использование сервиса в
          рамках закона несёт пользователь.
        </div>
        <?php endif; ?>
      </div>
    </section>
