<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
    <meta http-equiv="Pragma" content="no-cache" />
    <meta http-equiv="Expires" content="0" />
    <title><?= TemplateEngine::e($seo['title'] ?? ($title ?? 'HexaVeil – Доступ к мировому интернету')) ?></title>
    <?php if (!empty($seo['description'])): ?>
    <meta name="description" content="<?= TemplateEngine::e($seo['description']) ?>" />
    <?php else: ?>
    <meta name="description" content="Обходи блокировки и пользуйся любимыми иностранными сервисами. Современный VPN с киберпанк-эстетикой." />
    <?php endif; ?>
    <meta property="og:title" content="<?= TemplateEngine::e($seo['title'] ?? 'HexaVeil – Интернет без границ') ?>" />
    <meta
      property="og:description"
      content="<?= TemplateEngine::e($seo['description'] ?? 'Доступ к заблокированным сайтам, соцсетям и стримингу в один клик.') ?>"
    />
    <meta property="og:type" content="website" />
    <link rel="canonical" href="<?= SITE_URL . ($_SERVER['REQUEST_URI'] ?? '') ?>">
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Serif:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="<?= TemplateEngine::asset('hexaveil/css/reset.css') ?>" />
    <link rel="stylesheet" href="<?= TemplateEngine::asset('hexaveil/css/variables.css') ?>?v=1" />
    <link rel="stylesheet" href="<?= TemplateEngine::asset('hexaveil/css/global.css') ?>?v=1" />
    <link rel="stylesheet" href="<?= TemplateEngine::asset('hexaveil/css/style.css') ?>?v=1" />
    <link rel="stylesheet" href="<?= TemplateEngine::asset('hexaveil/css/stars.css') ?>" />
    <script>
      window.HV_BASE = '<?= TemplateEngine::asset('hexaveil/') ?>';
    </script>
    <script src="<?= TemplateEngine::asset('hexaveil/js/star.js') ?>?v=1" defer></script>
    <script src="<?= TemplateEngine::asset('hexaveil/js/main.js') ?>?v=1" defer></script>
    <script src="<?= TemplateEngine::asset('hexaveil/js/data.js') ?>?v=1" defer></script>
    <script src="<?= TemplateEngine::asset('hexaveil/js/planet.js') ?>?v=1" defer></script>
    <script src="<?= TemplateEngine::asset('hexaveil/js/server-panel.js') ?>?v=1" defer></script>
    <script src="<?= TemplateEngine::asset('hexaveil/js/telemetry.js') ?>?v=1" defer></script>
    <!-- Встроенная копия servers.json (офлайн/файловый фолбэк). Обновляется
         автоматически скриптом scripts/bust-cache.mjs при билде. -->
    <script type="application/json" id="servers-data">{
  "textureUrl": "assets/earth-night.jpg",
  "textureUrlFallback": "https://unpkg.com/three-globe/example/img/earth-night.jpg",
  "rotationMs": 90000,
  "connectUrl": "https://cabinet.fortf.ru/login",
  "cities": {
    "mow": { "lng": 37.62,   "lat": 55.75 },
    "stp": { "lng": 30.36,   "lat": 59.93 },
    "nvs": { "lng": 82.92,   "lat": 55.03 },
    "ny":  { "lng": -74.01,  "lat": 40.71 },
    "tor": { "lng": -79.38,  "lat": 43.65 },
    "lon": { "lng": -0.13,   "lat": 51.51 },
    "fra": { "lng": 8.68,    "lat": 50.11 },
    "par": { "lng": 2.35,    "lat": 48.86 },
    "ams": { "lng": 4.9,     "lat": 52.37 },
    "bru": { "lng": 4.35,    "lat": 50.85 },
    "hel": { "lng": 24.94,   "lat": 60.17 },
    "tll": { "lng": 24.75,   "lat": 59.44 },
    "stk": { "lng": 18.07,   "lat": 59.33 },
    "osl": { "lng": 10.75,   "lat": 59.91 },
    "cph": { "lng": 12.57,   "lat": 55.68 },
    "waw": { "lng": 21.01,   "lat": 52.23 },
    "prg": { "lng": 14.42,   "lat": 50.09 },
    "mil": { "lng": 9.19,    "lat": 45.46 },
    "zrh": { "lng": 8.54,    "lat": 47.38 },
    "mad": { "lng": -3.7,    "lat": 40.42 },
    "ala": { "lng": 76.89,   "lat": 43.24 },
    "ist": { "lng": 28.98,   "lat": 41.01 },
    "tlv": { "lng": 34.78,   "lat": 32.09 },
    "dxb": { "lng": 55.27,   "lat": 25.2 },
    "bom": { "lng": 72.88,   "lat": 19.08 },
    "sin": { "lng": 103.82,  "lat": 1.35 },
    "hkg": { "lng": 114.17,  "lat": 22.32 },
    "tyo": { "lng": 139.65,  "lat": 35.68 },
    "sel": { "lng": 126.98,  "lat": 37.57 },
    "syd": { "lng": 151.21,  "lat": -33.87 },
    "akl": { "lng": 174.76,  "lat": -36.85 },
    "sao": { "lng": -46.63,  "lat": -23.55 },
    "bue": { "lng": -58.38,  "lat": -34.6 },
    "mex": { "lng": -99.13,  "lat": 19.43 },
    "jnb": { "lng": 28.05,   "lat": -26.2 }
  },
  "cityInfo": {
    "mow": { "ru": "Москва",          "en": "Moscow",            "country": "Россия",        "ping": 1,   "flag": "🇷🇺", "tags": ["игры"] },
    "stp": { "ru": "Санкт-Петербург", "en": "Saint Petersburg",  "country": "Россия",        "ping": 10,  "flag": "🇷🇺", "tags": [] },
    "nvs": { "ru": "Новосибирск",     "en": "Novosibirsk",       "country": "Россия",        "ping": 48,  "flag": "🇷🇺", "tags": [] },
    "ny":  { "ru": "Нью-Йорк",        "en": "New York",          "country": "США",           "ping": 152, "flag": "🇺🇸", "tags": ["стриминг", "игры"] },
    "tor": { "ru": "Торонто",         "en": "Toronto",           "country": "Канада",        "ping": 170, "flag": "🇨🇦", "tags": ["стриминг"], "connected": false },
    "lon": { "ru": "Лондон",          "en": "London",            "country": "Великобритания", "ping": 68,  "flag": "🇬🇧", "tags": ["стриминг"], "connected": false },
    "fra": { "ru": "Франкфурт",       "en": "Frankfurt",         "country": "Германия",      "ping": 52,  "flag": "🇩🇪", "tags": ["стриминг", "игры"] },
    "par": { "ru": "Париж",           "en": "Paris",             "country": "Франция",       "ping": 62,  "flag": "🇫🇷", "tags": ["стриминг", "игры"], "connected": false },
    "ams": { "ru": "Амстердам",       "en": "Amsterdam",         "country": "Нидерланды",    "ping": 57,  "flag": "🇳🇱", "tags": ["стриминг", "игры"] },
    "bru": { "ru": "Брюссель",        "en": "Brussels",          "country": "Бельгия",       "ping": 55,  "flag": "🇧🇪", "tags": ["стриминг"], "connected": false },
    "hel": { "ru": "Хельсинки",       "en": "Helsinki",          "country": "Финляндия",     "ping": 22,  "flag": "🇫🇮", "tags": [] },
    "tll": { "ru": "Таллин",          "en": "Tallinn",           "country": "Эстония",       "ping": 18,  "flag": "🇪🇪", "tags": [], "connected": false },
    "stk": { "ru": "Стокгольм",       "en": "Stockholm",         "country": "Швеция",        "ping": 28,  "flag": "🇸🇪", "tags": [], "connected": false },
    "osl": { "ru": "Осло",            "en": "Oslo",              "country": "Норвегия",      "ping": 42,  "flag": "🇳🇴", "tags": [], "connected": false },
    "cph": { "ru": "Копенгаген",      "en": "Copenhagen",        "country": "Дания",         "ping": 40,  "flag": "🇩🇰", "tags": [], "connected": false },
    "waw": { "ru": "Варшава",         "en": "Warsaw",            "country": "Польша",        "ping": 45,  "flag": "🇵🇱", "tags": [], "connected": false },
    "prg": { "ru": "Прага",           "en": "Prague",            "country": "Чехия",         "ping": 58,  "flag": "🇨🇿", "tags": ["стриминг"], "connected": false },
    "mil": { "ru": "Милан",           "en": "Milan",             "country": "Италия",        "ping": 72,  "flag": "🇮🇹", "tags": ["стриминг", "игры"], "connected": false },
    "zrh": { "ru": "Цюрих",           "en": "Zurich",            "country": "Швейцария",     "ping": 65,  "flag": "🇨🇭", "tags": [], "connected": false },
    "mad": { "ru": "Мадрид",          "en": "Madrid",            "country": "Испания",       "ping": 78,  "flag": "🇪🇸", "tags": ["стриминг"], "connected": false },
    "ala": { "ru": "Алматы",          "en": "Almaty",            "country": "Казахстан",     "ping": 88,  "flag": "🇰🇿", "tags": [], "connected": false },
    "ist": { "ru": "Стамбул",         "en": "Istanbul",          "country": "Турция",        "ping": 95,  "flag": "🇹🇷", "tags": ["стриминг"], "connected": false },
    "tlv": { "ru": "Тель-Авив",       "en": "Tel Aviv",          "country": "Израиль",       "ping": 105, "flag": "🇮🇱", "tags": [], "connected": false },
    "dxb": { "ru": "Дубай",           "en": "Dubai",             "country": "ОАЭ",           "ping": 118, "flag": "🇦🇪", "tags": ["стриминг"], "connected": false },
    "bom": { "ru": "Мумбаи",          "en": "Mumbai",            "country": "Индия",         "ping": 148, "flag": "🇮🇳", "tags": [], "connected": false },
    "sin": { "ru": "Сингапур",        "en": "Singapore",         "country": "Сингапур",      "ping": 186, "flag": "🇸🇬", "tags": ["стриминг"], "connected": false },
    "hkg": { "ru": "Гонконг",         "en": "Hong Kong",         "country": "Китай",         "ping": 212, "flag": "🇭🇰", "tags": ["стриминг"], "connected": false },
    "tyo": { "ru": "Токио",           "en": "Tokyo",             "country": "Япония",        "ping": 236, "flag": "🇯🇵", "tags": ["стриминг"], "connected": false },
    "sel": { "ru": "Сеул",            "en": "Seoul",             "country": "Южная Корея",   "ping": 220, "flag": "🇰🇷", "tags": ["стриминг"], "connected": false },
    "syd": { "ru": "Сидней",          "en": "Sydney",            "country": "Австралия",     "ping": 302, "flag": "🇦🇺", "tags": ["стриминг"], "connected": false },
    "akl": { "ru": "Окленд",          "en": "Auckland",          "country": "Новая Зеландия", "ping": 310, "flag": "🇳🇿", "tags": [], "connected": false },
    "sao": { "ru": "Сан-Паулу",       "en": "São Paulo",         "country": "Бразилия",      "ping": 262, "flag": "🇧🇷", "tags": ["стриминг"], "connected": false },
    "bue": { "ru": "Буэнос-Айрес",    "en": "Buenos Aires",      "country": "Аргентина",     "ping": 275, "flag": "🇦🇷", "tags": [], "connected": false },
    "mex": { "ru": "Мехико",          "en": "Mexico City",       "country": "Мексика",       "ping": 235, "flag": "🇲🇽", "tags": ["стриминг"], "connected": false },
    "jnb": { "ru": "Йоханнесбург",    "en": "Johannesburg",      "country": "ЮАР",           "ping": 290, "flag": "🇿🇦", "tags": [], "connected": false }
  },
  "cables": [
    ["mow", "stp", "hel", "tll", "stk"],
    ["mow", "nvs"],
    ["mow", "ala"],
    ["mow", "ams"],
    ["nvs", "ala"],
    ["ala", "ist"],
    ["hel", "fra"],
    ["stk", "cph"],
    ["cph", "osl"],
    ["cph", "fra"],
    ["lon", "ams"],
    ["lon", "bru"],
    ["bru", "ams"],
    ["ams", "fra"],
    ["fra", "par"],
    ["par", "mad"],
    ["par", "mil"],
    ["mil", "zrh"],
    ["zrh", "fra"],
    ["fra", "waw"],
    ["fra", "prg"],
    ["mil", "ist"],
    ["ist", "tlv"],
    ["ist", "dxb"],
    ["dxb", "bom"],
    ["ny", "lon"],
    ["tor", "ny"],
    ["ny", "mad"],
    ["ny", "sao"],
    ["mex", "ny"],
    ["mex", "sao"],
    ["sao", "bue"],
    ["mad", "jnb"],
    ["bom", "sin"],
    ["sin", "hkg"],
    ["hkg", "tyo"],
    ["tyo", "sel"],
    ["sin", "tyo"],
    ["sin", "syd"],
    ["syd", "akl"]
  ]
}</script>
  </head>
  <body>
    <!-- Звёздный фон
    <canvas class="star-canvas" id="starCanvas"></canvas>-->
    <div id="particle-container"></div>
    <!-- ============ HEADER ============ -->
    <header class="header">
      <div class="container">
        <a href="<?= TemplateEngine::url() ?>" class="logo-link">
          <svg
            class="logo-icon"
            width="32"
            height="32"
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M16 2L4 8v8c0 7.2 5.1 13.9 12 16 6.9-2.1 12-8.8 12-16V8L16 2z"
              stroke="#a855f7"
              stroke-width="2"
              fill="rgba(168,85,247,0.1)"
            />
            <path
              d="M10 16l4 4 8-8"
              stroke="#a855f7"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              fill="none"
            />
          </svg>
          <h1 class="logo">Hexa<span class="logo-accent">Veil VPN</span></h1>
        </a>

        <nav class="nav" id="nav">
          <ul>
            <li><a href="#features">Возможности</a></li>
            <li><a href="#trial">Бесплатно</a></li>
            <li><a href="#services">Сервисы</a></li>
            <!--<li><a href="#pricing">Тарифы</a></li>-->
            <li><a href="#referral">Партнёрам</a></li>
            <li><a href="#faq">FAQ</a></li>
          </ul>
        </nav>

        <a
          href="<?= theme_setting('hexaveil_cabinet_url', 'https://cabinet.fortf.ru/login') ?>"
          class="btn btn-primary header-cta"
          ><?= theme_setting('hexaveil_cta_label', 'Личный кабинет') ?></a
        >

        <div class="burger" id="burger">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </header>

    <!-- Область виджетов «Шапка» -->
    <?= render_widget_area('header') ?>
    <?php do_action('theme_header_end'); ?>

    <!-- ============ ОСНОВНОЙ КОНТЕНТ ============ -->
    <?= $content ?? '' ?>

    <?php do_action('theme_footer_start'); ?>
    <!-- Область виджетов «Подвал» -->
    <?= render_widget_area('footer') ?>

    <!-- ============ FOOTER ============ -->
    <footer class="footer">
      <div class="container">
        <div class="footer-nav">
          <a href="#features">Возможности</a>
          <a href="#pricing">Тарифы</a>
          <a href="#referral">Партнёрам</a>
          <a href="#faq">FAQ</a>
          <a href="#privacy">Политика конфиденциальности</a>
          <a href="#terms">Условия использования</a>
          <a
            href="<?= theme_setting('hexaveil_telegram_url', 'https://t.me/nova_vpn') ?>"
            class="social-link"
            target="_blank"
            rel="noopener"
          >
            <svg class="icon" viewBox="0 0 496 512" fill="currentColor" aria-hidden="true"><path d="M248,8C111.033,8,0,119.033,0,256S111.033,504,248,504,496,392.967,496,256,384.967,8,248,8ZM362.952,176.66c-3.732,39.215-19.881,134.378-28.1,178.3-3.476,18.584-10.322,24.816-16.948,25.425-14.4,1.326-25.338-9.517-39.287-18.661-21.827-14.308-34.158-23.215-55.346-37.177-24.485-16.135-8.612-25,5.342-39.5,3.652-3.793,67.107-61.51,68.335-66.746.153-.655.3-3.1-1.154-4.384s-3.59-.849-5.135-.5q-3.283.746-104.608,69.142-14.845,10.194-26.894,9.934c-8.855-.191-25.888-5.006-38.551-9.123-15.531-5.048-27.875-7.717-26.8-16.291q.84-6.7,18.45-13.7,108.446-47.248,144.628-62.3c68.872-28.647,83.183-33.623,92.511-33.789,2.052-.034,6.639.474,9.61,2.885a10.452,10.452,0,0,1,3.53,6.716A43.765,43.765,0,0,1,362.952,176.66Z"/></svg>
            Telegram
          </a>
        </div>
        <p class="copyright">
          <?= theme_setting('hexaveil_footer_copyright', '© 2026 HexaVeil. Защищённый доступ к мировому интернету.') ?>
        </p>
      </div>
    </footer>
  </body>
</html>
