pg_dump: warning: there are circular foreign-key constraints on this table:
pg_dump: detail: categories
pg_dump: hint: You might not be able to restore the dump without using --disable-triggers or temporarily dropping the constraints.
pg_dump: hint: Consider using a full dump instead of a --data-only dump to avoid this problem.
pg_dump: warning: there are circular foreign-key constraints on this table:
pg_dump: detail: menu_items
pg_dump: hint: You might not be able to restore the dump without using --disable-triggers or temporarily dropping the constraints.
pg_dump: hint: Consider using a full dump instead of a --data-only dump to avoid this problem.
--
-- PostgreSQL database dump
--

\restrict hi64xdlDKrBdPmx19WK7U6Q8fpINaaW4PFexfTca6rctZkRbSfTzw1zG9GbiqM0

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: cms
--

SET SESSION AUTHORIZATION DEFAULT;

ALTER TABLE public.categories DISABLE TRIGGER ALL;

INSERT INTO public.categories (id, name, slug, description, parent_id) VALUES (2, 'Статьи', 'articles', 'Полезные статьи', NULL);
INSERT INTO public.categories (id, name, slug, description, parent_id) VALUES (1, 'Новости', 'novosti', '', NULL);


ALTER TABLE public.categories ENABLE TRIGGER ALL;

--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.users DISABLE TRIGGER ALL;

INSERT INTO public.users (id, login, email, password, role, created_at) VALUES (1, 'admn', 'imcrazymonk@gmail.com', '$2y$10$I7B5DdT2UsBOPrgcyG5YZuaUvlSZ5FeY/n97ITYbypMgiTHgiqQ3G', 'admin', '2026-09-26 01:02:53.170796');


ALTER TABLE public.users ENABLE TRIGGER ALL;

--
-- Data for Name: posts; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.posts DISABLE TRIGGER ALL;

INSERT INTO public.posts (id, title, slug, content, excerpt, image, status, views, user_id, category_id, created_at, updated_at) VALUES (1, 'Выживание» в 2026: что происходит с VPN в России и как выбрать работающий сервис', 'vyzhivanie-v-2026-chto-proishodit-s-vpn-v-rossii-i-kak-vybrat-rabotayuschiy-servis', '<p class="MsoNormal">&nbsp;</p>
<p class="MsoNormal">&nbsp;</p>
<p class="MsoNormal">За последние полтора года рынок VPN в России пережил тектонические сдвиги. То, что ещё вчера работало без проблем, сегодня либо недоступно, либо требует принципиально иного подхода. Блокировки ужесточаются, привычные сервисы один за другим уходят в тень, а пользователи массово ищут рабочие альтернативы. Разберёмся, что реально происходит и на что теперь ориентироваться.</p>
<p class="MsoNormal">&nbsp;</p>
<h2 class="MsoNormal">Цифры, которые говорят сами за себя</h2>
<p>&nbsp;</p>
<p class="MsoNormal">Спрос на VPN-сервисы в России вырос настолько стремительно, что статистика выглядит почти фантастической. В марте 2026 года российские пользователи скачали VPN-приложения 9,2 миллиона раз &mdash; это в 14 раз больше, чем в марте 2025 года. А всего за год, с марта 2025 по март 2026, зафиксировано 35,7 миллиона скачиваний. Пик пришёлся на первый квартал 2026 года &mdash; 21,27 миллиона загрузок.</p>
<p class="MsoNormal">&nbsp;</p>
<p class="MsoNormal">Активная аудитория пяти крупнейших VPN-сервисов достигла 7,3 миллиона человек. По некоторым оценкам, 39% россиян пользуются VPN &mdash; рост на 8 процентных пунктов с начала 2026 года.</p>
<p class="MsoNormal">&nbsp;</p>
<p class="MsoNormal">При этом количество заблокированных сервисов растёт не менее впечатляющими темпами. В 2025 году Роскомнадзор ограничил доступ к 258 VPN-сервисам &mdash; на 31% больше, чем в 2024-м. К середине января 2026 года чёрный список вырос до 439 позиций. А к концу февраля &mdash; уже до 469. И это только официально подтверждённые цифры.</p>
<p class="MsoNormal">&nbsp;</p>
<h1>Как именно блокируют: ТСПУ, DPI и охота на протоколы</h1>
<p>&nbsp;</p>
<p class="MsoNormal">Технически блокировки реализуются через ТСПУ (технические средства противодействия угрозам) &mdash; оборудование, которое устанавливается у провайдеров и фильтрует трафик. Системы глубокой инспекции пакетов (DPI) анализируют не просто IP-адреса, а сигнатуры протоколов, порты, объёмы трафика и даже цифровые &laquo;отпечатки&raquo; соединений.</p>
<p class="MsoNormal">&nbsp;</p>
<p class="MsoNormal">С декабря 2025 года РКН начал активно блокировать дополнительные протоколы &mdash; SOCKS5, VLESS и L2TP. Классические протоколы вроде OpenVPN, L2TP и PPTP уже давно детектируются практически мгновенно &mdash; их сигнатуры хорошо известны. Даже WireGuard, считавшийся современным и надёжным, имеет характерные метаданные, которые DPI научились распознавать.</p>
<p class="MsoNormal">&nbsp;</p>
<p class="MsoNormal">Более того, блокировки теперь применяются не только к конкретным IP-адресам, но и к целым классам подключений. Роскомнадзор отслеживает аномальные объёмы трафика &mdash; например, сервер могут заблокировать при 100 Гб трафика в день на один IP-адрес, даже если данные замаскированы под обычный сёрфинг.</p>
<p class="MsoNormal">&nbsp;</p>
<h1>Что изменилось с 1 мая 2026 года</h1>
<p>&nbsp;</p>
<p class="MsoNormal">Весной 2026 года произошёл ряд событий, которые кардинально изменили правила игры:</p>
<p class="MsoNormal">Первое. Apple удалила из российского App Store ряд популярных VPN- и proxy-клиентов по требованию, связанному с российским регулированием.</p>
<p class="MsoNormal">Второе. Минцифры провело совещания с операторами связи и крупнейшими цифровыми платформами &mdash; VK, Ozon, Wildberries, Яндексом и другими. Бизнесу предложили ввести меры, которые фактически делают использование VPN платным и труднодоступным. Операторам предложено ввести плату за использование более 15 ГБ &laquo;международного трафика&raquo; в месяц &mdash; а любой трафик на VPN-сервер за границей считается международным. За каждый лишний гигабайт придётся платить от 100 до 150 рублей.</p>
<p class="MsoNormal">Третье. Крупнейшие российские онлайн-платформы с 15 апреля 2026 года начали блокировать доступ пользователям с включённым VPN. Им раздали методичку с тремя сигналами для определения VPN: несовпадение IP с российским, попадание в чёрный список РКН, частая смена стран. Wildberries и Ozon уже активно блокируют VPN-подключения.</p>
<p class="MsoNormal">&nbsp;</p>
<h2>Какие протоколы ещё работают</h2>
<p>&nbsp;</p>
<p class="MsoNormal">В условиях тотальной фильтрации трафика обычные VPN-приложения без глубокой маскировки перестали работать. Коммерческие сервисы вроде NordVPN или Surfshark в России либо недоступны, либо работают крайне нестабильно.</p>
<p class="MsoNormal">Эксперты рекомендуют переходить на решения, спроектированные с защитой от DPI. Главные альтернативы сегодня &mdash; протокол VLESS и транспорт Reality.</p>
<p class="MsoNormal">Reality &mdash; это надстройка над VLESS, которая делает подключение неотличимым от соединения с легитимным сайтом. Сервер &laquo;притворяется&raquo; реальным ресурсом, и DPI не находит признаков VPN. Это единственный известный протокол, который эмпирически обходит ТСПУ на российских операторах без использования сторонних приложений. Проблема в том, что даже VLESS+Reality не даёт вечной гарантии &mdash; системы DPI постоянно эволюционируют, и то, что работает сегодня, завтра может быть распознано.</p>
<p class="MsoNormal">&nbsp;</p>
<h2>Как выбрать работающий VPN в 2026 году</h2>
<p>&nbsp;</p>
<p class="MsoNormal">Исходя из текущей ситуации, вот ключевые критерии выбора VPN-сервиса, который реально будет работать:</p>
<p class="MsoNormal">1. Современные протоколы с маскировкой. Забудьте про OpenVPN, L2TP и PPTP &mdash; они не работают. WireGuard тоже под вопросом. Ищите сервисы, которые используют VLESS, Reality, XTLS или другие протоколы с обфускацией трафика.</p>
<p class="MsoNormal">2. Устойчивость к DPI. Сервис должен постоянно обновлять методы маскировки, менять IP-адреса и адаптироваться к новым сигнатурам блокировок. Статичные решения &laquo;поставил и забыл&raquo; больше не работают.</p>
<p class="MsoNormal">3. Отсутствие логов. В условиях, когда использование VPN становится всё более заметным, политика zero-log &mdash; не просто маркетинг, а вопрос безопасности.</p>
<p class="MsoNormal">4. Надёжная инфраструктура. Серверы должны быть размещены так, чтобы минимизировать риск коллатеральных блокировок (а такие случаи уже были &mdash; борьба с VPN обрушила крупные российские хостинги).</p>
<p class="MsoNormal">5. Техническая поддержка, понимающая контекст. В 2026 году недостаточно просто &laquo;поднять сервер&raquo;. Нужна команда, которая мониторит ситуацию с блокировками и оперативно реагирует на изменения.</p>
<p class="MsoNormal">&nbsp;</p>
<h1>Вместо заключения</h1>
<p>&nbsp;</p>
<p class="MsoNormal">Рынок VPN в России 2026 года &mdash; это поле боя, где каждую неделю меняются правила. Те сервисы, которые не инвестируют в защиту от DPI и не следят за эволюцией блокировок, обречены. Пользователи, в свою очередь, вынуждены выбирать между дорогими и сложными решениями или полной потерей доступа к заблокированным ресурсам.</p>
<p class="MsoNormal">&nbsp;</p>
<p class="MsoNormal">Если вы ищете сервис, который учитывает все эти реалии, обратите внимание на HexaVeil. Проект построен с использованием современных протоколов, устойчивых к DPI, и постоянно адаптируется к изменениям в методах блокировки &mdash; именно то, что нужно, чтобы оставаться на связи в 2026 году.</p>
<p class="MsoNormal">&nbsp;</p>
<p class="MsoNormal">Статья подготовлена на основе открытых данных и материалов СМИ по состоянию на август 2026 года. Ситуация с блокировками динамична, информация может меняться.</p>', 'За последние полтора года рынок VPN в России пережил тектонические сдвиги. То, что ещё вчера работало без проблем, сегодня либо недоступно, либо требует принципиально иного подхода. Блокировки ужесточаются, привычные сервисы один за другим уходят в тень, а пользователи массово ищут рабочие альтернативы. Разберёмся, что реально происходит и на что теперь ориентироваться.', '', 'published', 70, 1, 2, '2026-09-14 12:32:55', '2026-09-27 09:06:21.785363');
INSERT INTO public.posts (id, title, slug, content, excerpt, image, status, views, user_id, category_id, created_at, updated_at) VALUES (2, 'VPN для ChatGPT, Claude, Gemini и других нейросетей в 2026 году: какой выбрать и почему обычный VPN не подходит', 'vpn-dlya-chatgpt-claude-gemini-i-drugih-neyrosetey-v-2026-godu-kakoy-vybrat-i-pochemu-obychnyy-vpn-ne-podhodit', '<p class="w6asjq_TextBase _85PZeG_Text PDq2pG_selectionAnchorContainer" data-d-component="text">В 2026 году VPN перестал быть просто способом открыть заблокированный сайт. Если вы пользуетесь <span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">ChatGPT, Claude, Gemini, Midjourney, Perplexity AI, Cursor или GitHub Copilot</span>, то уже наверняка сталкивались с ошибками вроде <span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">"This service is not available in your country"</span>, <span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">"Connection blocked"</span> или бесконечной загрузкой страницы.</p>
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text">Проблема в том, что большинство популярных нейросетей ограничивают доступ пользователям из России по IP-адресу, а часть VPN-сервисов уже блокируется российскими провайдерами или попадает в списки подозрительных IP самих AI-сервисов. Поэтому далеко не каждый VPN подойдет для работы с искусственным интеллектом. OpenAI, Anthropic и Google используют географические ограничения, а также дополнительные механизмы защиты от подозрительных VPN-адресов.</p>
<p>В этой статье разберем:</p>
<ul>
<li>какой VPN действительно подходит для ChatGPT, Claude и Gemini;</li>
<li>почему бесплатные VPN часто не работают;</li>
<li>какие страны выбирать для подключения;</li>
<li>как получить стабильный доступ к AI-сервисам в России.</li>
</ul>
<h2>Почему ChatGPT, Claude и Gemini не работают без VPN</h2>
<p class="w6asjq_TextBase _85PZeG_Text PDq2pG_selectionAnchorContainer" data-d-component="text">Причин сразу две.</p>
<h3 class="w6asjq_TextBase GgxHUa_Title" data-d-component="title" data-d-size="md" data-d-weight="semibold">1. Ограничения со стороны самих сервисов</h3>
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text">OpenAI официально не поддерживает доступ к ChatGPT и API из России. Аналогичные ограничения действуют у Anthropic для Claude, а Google ограничивает работу Gemini в неподдерживаемых регионах. При попытке открыть сервис с российским IP пользователь получает сообщение о недоступности региона.</p>
<h3 class="w6asjq_TextBase GgxHUa_Title" data-d-component="title" data-d-size="md" data-d-weight="semibold">2. Ограничения со стороны интернет-провайдеров</h3>
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text">Даже если сервис готов работать через иностранный IP, соединение может прерываться из-за фильтрации VPN-трафика российскими провайдерами. Многие классические VPN-протоколы распознаются и работают нестабильно.</p>
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Вывод:</span> хороший VPN должен одновременно менять ваш IP и использовать технологии, которые позволяют соединению оставаться стабильным.</p>
<h2 class="w6asjq_TextBase GgxHUa_Title PDq2pG_selectionAnchorContainer" data-d-component="title" data-d-size="lg" data-d-weight="semibold">Каким должен быть VPN для нейросетей</h2>
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text">Не каждый VPN одинаково хорошо подходит для AI.</p>
<div class="_6IUVGW_TableFrame" data-d-column-sizing="auto" data-d-component="table">
<table class="_6IUVGW_Table" style="width: 60.5004%; border-collapse: collapse; height: 405.812px; border-width: 1px;" border="1" data-d-column-sizing="auto" data-d-dividers="">
<thead data-d-component="table-section">
<tr style="height: 40.9688px;" data-d-component="table-row">
<th style="width: 33.0785%;" scope="col" data-d-component="table-cell" data-d-valign="start">Критерий</th>
<th style="width: 66.9117%;" scope="col" data-d-component="table-cell" data-d-valign="start">Почему это важно</th>
</tr>
</thead>
<tbody>
<tr style="height: 72.9688px;" data-d-component="table-row">
<td style="width: 33.0785%;" data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Чистые зарубежные IP</span></p>
</td>
<td style="width: 66.9117%;" data-d-component="table-cell" data-d-valign="start">OpenAI и Claude могут ограничивать доступ с известных VPN-адресов.</td>
</tr>
<tr style="height: 72.9688px;" data-d-component="table-row">
<td style="width: 33.0785%;" data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Высокая скорость</span></p>
</td>
<td style="width: 66.9117%;" data-d-component="table-cell" data-d-valign="start">Gemini и ChatGPT активно работают с голосом, файлами и изображениями.</td>
</tr>
<tr style="height: 72.9688px;" data-d-component="table-row">
<td style="width: 33.0785%;" data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Современные протоколы</span></p>
</td>
<td style="width: 66.9117%;" data-d-component="table-cell" data-d-valign="start">Лучше обходят ограничения и работают стабильнее.</td>
</tr>
<tr style="height: 72.9688px;" data-d-component="table-row">
<td style="width: 33.0785%;" data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Стабильные европейские серверы</span></p>
</td>
<td style="width: 66.9117%;" data-d-component="table-cell" data-d-valign="start">Минимальная задержка и меньше вероятность блокировок.</td>
</tr>
<tr style="height: 72.9688px;" data-d-component="table-row">
<td style="width: 33.0785%;" data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Работа на телефоне, ПК и телевизоре</span></p>
</td>
<td style="width: 66.9117%;" data-d-component="table-cell" data-d-valign="start">Один VPN можно использовать сразу на нескольких устройствах.</td>
</tr>
</tbody>
</table>
</div>
<h2 class="w6asjq_TextBase _85PZeG_Text" data-d-component="text">Лучшие страны для подключения к нейросетям<br><br></h2>
<div class="_6IUVGW_TableFrame" data-d-column-sizing="auto" data-d-component="table">
<table class="_6IUVGW_Table" data-d-column-sizing="auto" data-d-dividers="">
<thead data-d-component="table-section">
<tr data-d-component="table-row">
<th scope="col" data-d-component="table-cell" data-d-valign="start">Страна VPN</th>
<th scope="col" data-d-component="table-cell" data-d-valign="start">Для чего подходит</th>
</tr>
</thead>
<tbody>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">Нидерланды</td>
<td data-d-component="table-cell" data-d-valign="start">Лучший вариант для ChatGPT, Claude и Gemini.</td>
</tr>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">Швеция</td>
<td data-d-component="table-cell" data-d-valign="start">Очень стабильная работа AI и высокая скорость.</td>
</tr>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">Германия</td>
<td data-d-component="table-cell" data-d-valign="start">Подходит для большинства сервисов Google.</td>
</tr>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">Бельгия</td>
<td data-d-component="table-cell" data-d-valign="start">Хорошая альтернатива европейским серверам.</td>
</tr>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">Финляндия</td>
<td data-d-component="table-cell" data-d-valign="start">Минимальная задержка для пользователей из России.</td>
</tr>
</tbody>
</table>
</div>
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Совет:</span> не используйте США без необходимости &mdash; задержка выше.<br><br></p>
<h2 class="w6asjq_TextBase GgxHUa_Title PDq2pG_selectionAnchorContainer" data-d-component="title" data-d-size="lg" data-d-weight="semibold">Какой сервер выбрать для каждой нейросети</h2>
<div class="_6IUVGW_TableFrame" data-d-column-sizing="auto" data-d-component="table">
<table class="_6IUVGW_Table" data-d-column-sizing="auto" data-d-dividers="">
<thead data-d-component="table-section">
<tr data-d-component="table-row">
<th scope="col" data-d-component="table-cell" data-d-valign="start">Нейросеть</th>
<th scope="col" data-d-component="table-cell" data-d-valign="start">Нужен VPN?</th>
<th scope="col" data-d-component="table-cell" data-d-valign="start">Лучший регион</th>
</tr>
</thead>
<tbody>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">ChatGPT</span></p>
</td>
<td data-d-component="table-cell" data-d-valign="start">✅ Да</td>
<td data-d-component="table-cell" data-d-valign="start">Нидерланды / Швеция</td>
</tr>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Claude</span></p>
</td>
<td data-d-component="table-cell" data-d-valign="start">✅ Да</td>
<td data-d-component="table-cell" data-d-valign="start">Нидерланды / Швеция</td>
</tr>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Gemini</span></p>
</td>
<td data-d-component="table-cell" data-d-valign="start">✅ Да</td>
<td data-d-component="table-cell" data-d-valign="start">Германия / Нидерланды</td>
</tr>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Perplexity AI</span></p>
</td>
<td data-d-component="table-cell" data-d-valign="start">Желательно</td>
<td data-d-component="table-cell" data-d-valign="start">Швеция / Германия</td>
</tr>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Midjourney</span></p>
</td>
<td data-d-component="table-cell" data-d-valign="start">✅ Да</td>
<td data-d-component="table-cell" data-d-valign="start">Швеция</td>
</tr>
<tr data-d-component="table-row">
<td data-d-component="table-cell" data-d-valign="start">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">Cursor AI / GitHub Copilot</span></p>
</td>
<td data-d-component="table-cell" data-d-valign="start">Часто нужен</td>
<td data-d-component="table-cell" data-d-valign="start">Нидерланды / Германия</td>
</tr>
</tbody>
</table>
</div>
<h2 class="w6asjq_TextBase _85PZeG_Text" data-d-component="text">Почему пользователи AI выбирают HexaVeil VPN</h2>
<p class="w6asjq_TextBase _85PZeG_Text PDq2pG_selectionAnchorContainer" data-d-component="text">Если вам нужен VPN именно для <span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">ChatGPT, Claude, Gemini, Midjourney, Perplexity и других нейросетей</span>, стоит обратить внимание на <span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">HexaVeil VPN</span> &mdash; сервис, который изначально оптимизирован для стабильной работы AI-сервисов.</p>
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">HexaVeil</span> сочетает в себе все ключевые требования для комфортной работы с нейросетями в 2026 году:</p>
<ul>
<li>Стабильное подключение без постоянных обрывов и переподключений.</li>
<li>Все необходимые серверы для нейросетей &mdash; Нидерланды, Швеция, Германия, Финляндия и другие регионы, которые подходят для ChatGPT, Claude и Gemini.</li>
<li>Современные VPN-протоколы, которые обеспечивают высокую скорость и помогают поддерживать стабильное соединение даже при высокой нагрузке сети.</li>
<li>Бесперебойная работа на телефонах, компьютерах, планшетах и Smart TV.</li>
<li>Высокая скорость для генерации текста, изображений, загрузки файлов и голосового режима AI.</li>
</ul>
<p class="w6asjq_TextBase _85PZeG_Text PDq2pG_selectionAnchorContainer" data-d-component="text">И самое приятное &mdash; <span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">HexaVeil стоит всего 75 рублей за одно устройство</span>. Это один из самых доступных вариантов для тех, кто регулярно пользуется нейросетями и хочет, чтобы ChatGPT, Claude и Gemini работали быстро и без ошибок.</p>
<blockquote class="HmKZva_Blockquote" data-d-component="blockquote">
<p class="w6asjq_TextBase _85PZeG_Text" data-d-component="text"><span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">HexaVeil VPN &mdash; это VPN, созданный для нейросетей:</span> стабильное соединение, современные технологии и доступ ко всем популярным AI-сервисам по цене всего <span class="w6asjq_TextBase _85PZeG_Text" data-d-component="text" data-d-default-strong="" data-d-inline="">75 ₽ за устройство</span>.</p>
</blockquote>', 'В 2026 году VPN перестал быть просто способом открыть заблокированный сайт. Если вы пользуетесь ChatGPT, Claude, Gemini, Midjourney, Perplexity AI, Cursor или GitHub Copilot, то уже наверняка сталкивались с ошибками вроде "This service is not available in your country", "Connection blocked" или бесконечной загрузкой страницы.', '', 'published', 74, 1, 2, '2026-09-16 19:16:00', '2026-09-27 09:06:22.127787');


ALTER TABLE public.posts ENABLE TRIGGER ALL;

--
-- Data for Name: comments; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.comments DISABLE TRIGGER ALL;



ALTER TABLE public.comments ENABLE TRIGGER ALL;

--
-- Data for Name: fin_settings; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.fin_settings DISABLE TRIGGER ALL;

INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (29, 'currency', '₽', '2026-09-13 14:31:46');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (30, 'decimals', '2', '2026-09-13 14:31:46');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (31, 'auto_refresh', '0', '2026-09-13 14:31:46');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (32, 'avg_period', 'day', '2026-09-13 14:31:46');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (33, 'avg_exclude_categories', '[]', '2026-09-13 14:31:46');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (34, 'avg_exclude_income_keywords', '[]', '2026-09-13 14:31:46');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (35, 'avg_exclude_expense_keywords', '[]', '2026-09-13 14:31:46');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (36, 'quick_categories', '[]', '2026-09-13 14:31:46');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (37, 'quick_participants', '[]', '2026-09-13 14:31:46');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (39, 'platega_secret', 'hDB1Wew553iSBFUNBp389bVPLsXraZMhHD6bcDgPU23MXwvMULMXGec2dU5O3kndXpHmBo0Sf8Ky3dDKpRYdOStrUHr9BntG2z8V', '2026-09-13 14:46:31');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (45, 'platega_cron_token', '160e118cc8d9410b687ce00fb448a0cc46a4e1e5356d127d', '2026-09-13 14:31:53');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (47, 'yookassa_cron_token', '4f53f903db002b57896e31be4f2ecdd713cd6c62e8461fc9', '2026-09-25 19:02:49');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (48, 'yookassa_shop_id', '1470788', '2026-09-26 10:29:56.130418');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (49, 'yookassa_secret_key', 'enc:v1:wr+3rgnD0QQe7SAyUA6uxQ==.wE+mMh1t1fhjf7fjt/aLLhGeJ27cbBj+mFPVdAPOhC/15jIjJslIVSTCPmcrKt5DzxHGdmrskpPqZsgIkP3dfA==', '2026-09-26 10:29:56.133305');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (50, 'yookassa_days_back', '5', '2026-09-26 10:29:56.133955');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (38, 'platega_merchant_id', 'c66751a9-2c2e-4eba-a3f6-e7b11a777bb6', '2026-09-26 10:25:01.390391');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (53, 'yookassa_last_sync', '2026-09-27T08:19:14+00:00', '2026-09-27 08:19:14.327516');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (55, 'yookassa_last_error', '', '2026-09-27 08:19:14.328503');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (54, 'yookassa_last_sync_ok', '1', '2026-09-27 08:19:14.329204');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (56, 'yookassa_sync_lock', '', '2026-09-27 08:19:14.329833');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (40, 'platega_days_back', '5', '2026-09-26 10:25:01.395486');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (41, 'platega_auto_sync', '1', '2026-09-26 10:25:01.396392');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (42, 'platega_last_sync', '2026-09-27T08:19:14+00:00', '2026-09-27 08:19:14.955036');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (44, 'platega_last_error', '', '2026-09-27 08:19:14.956245');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (51, 'yookassa_auto_sync', '1', '2026-09-26 10:25:01.399686');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (52, 'yookassa_commissions', '{"bank_card":3.5,"sbp":3.5,"yoo_money":3.5,"sberbank":3.5,"tinkoff_bank":3.5,"mobile":3.5,"cash":3.5,"qiwi":3.5}', '2026-09-26 10:25:01.400565');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (43, 'platega_last_sync_ok', '1', '2026-09-27 08:19:14.956916');
INSERT INTO public.fin_settings (id, setting_key, setting_value, updated_at) VALUES (46, 'platega_sync_lock', '', '2026-09-27 08:19:14.957576');


ALTER TABLE public.fin_settings ENABLE TRIGGER ALL;

--
-- Data for Name: fin_transactions; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.fin_transactions DISABLE TRIGGER ALL;

INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (1, '2026-01-10', 'expense', 'Сервер', 'Timeweb.Cloud', 790.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (2, '2026-02-20', 'expense', 'Сервер', 'Timeweb.Cloud', 690.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (3, '2026-02-28', 'income', 'Взнос участника', 'Храпков И.', 150.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (4, '2026-02-28', 'income', 'Взнос участника', 'Максимов Ю.', 150.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (5, '2026-02-28', 'income', 'Взнос участника', 'Григорьев В.', 1500.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (6, '2026-02-28', 'income', 'Взнос участника', 'Майоров З.', 150.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (7, '2026-02-28', 'income', 'Взнос участника', 'Ивлев Т.', 150.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (8, '2026-02-28', 'income', 'Взнос участника', 'Алимов Д.', 150.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (9, '2026-03-01', 'expense', 'Домен', 'LuxHost', 640.00, 'Проебаны в пустую, регистратор хуета', NULL, '2026-09-13 14:32:58', '2026-09-24 12:42:15');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (10, '2026-03-02', 'income', 'Взнос участника', 'Старовойтов С.', 450.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (11, '2026-03-02', 'income', 'Взнос участника', 'Конюхов А.', 300.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (12, '2026-03-06', 'income', 'Взнос участника', 'Ковалева Е.', 150.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (13, '2026-03-06', 'income', 'Взнос участника', 'Хамзин А.', 150.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (14, '2026-03-17', 'expense', 'Сервер', 'NuxtCloud', 340.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (15, '2026-03-20', 'expense', 'Сервер', 'Play2go', 826.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (16, '2026-03-23', 'expense', 'Сервер', 'Timeweb.Cloud', 690.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (17, '2026-03-28', 'income', 'Взнос участника', 'Юля (Подруга кати)', 350.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (18, '2026-03-28', 'income', 'Взнос участника', 'Майоров З.', 270.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (19, '2026-03-28', 'income', 'Взнос участника', 'Храпков И.', 135.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (20, '2026-03-28', 'income', 'Взнос участника', 'Сергей (От свяжина)', 135.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (21, '2026-03-30', 'income', 'Взнос участника', 'Алимов Д.', 300.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (22, '2026-03-30', 'income', 'Взнос участника', 'Олейник Д.', 270.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (23, '2026-03-30', 'income', 'Взнос участника', 'Елена Шерстенева', 450.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (24, '2026-03-31', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '6f96ded9-d94b-4c1d-8ad5-eb14442564d1', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (25, '2026-04-02', 'income', 'Взнос участника', 'Хамзин А.', 300.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (26, '2026-04-05', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '910c4af6-c78f-4b5f-8128-1704df349610', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (27, '2026-04-05', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'e1856f8a-f8ff-48a9-b09a-859ef788c05d', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (28, '2026-04-05', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'e1bf198a-7fbd-475d-a79c-b79331972fa1', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (29, '2026-04-07', 'income', 'Взнос участника', 'Конюхов А.', 1200.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (30, '2026-04-07', 'expense', 'Сервер', 'Sweb', 478.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (31, '2026-04-12', 'expense', 'Сервер', 'Play2go', 800.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (32, '2026-04-12', 'expense', 'Сервер', 'NuxtCloud', 341.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (33, '2026-04-23', 'income', 'Прибыль', 'Platega пополнение', 108.00, 'Пополнение на 120 ₽', 'f41c65ae-c934-408f-9f8e-4af225a8c34c', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (34, '2026-04-23', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'fae16477-842f-4839-ad90-6ac878c338ba', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (35, '2026-04-24', 'expense', 'Сервер', 'Sweb', 478.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (36, '2026-04-25', 'expense', 'Сервер', 'EternityCloud', 270.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (37, '2026-04-26', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'd1eb7c58-33d1-464a-a05a-bc7d1cad0f9b', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (38, '2026-04-27', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '2379c3fd-e1ab-45c1-8dc8-2d8527f313f8', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (39, '2026-04-27', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '739990a0-1ed8-4ae2-91aa-2656f6288af4', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (40, '2026-04-27', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'a805cd1b-3a20-4043-842e-8b1cf0c5187a', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (41, '2026-04-30', 'income', 'Прибыль', 'Platega пополнение', 450.00, 'Пополнение на 500 ₽', '78f3de56-898e-4201-b79a-8c082be6594b', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (42, '2026-05-02', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'ec9083b2-be03-4003-aced-56efa6ecbefd', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (43, '2026-05-04', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'c9bd77ad-da08-4cb5-9851-6f1b9b2cb7cb', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (44, '2026-05-07', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '46161b14-93aa-4b63-aab1-42f55f78a8c0', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (45, '2026-05-10', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'a0ac71fe-7dbb-4612-b6e1-c70128335be1', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (46, '2026-05-15', 'expense', 'Сервер', 'NuxtCloud', 341.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (47, '2026-05-15', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'c479137b-a880-4c3c-a79d-e97e5fb84d03', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (48, '2026-05-15', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'bb036739-bc91-4d24-a0e4-a79cebb3b479', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (49, '2026-05-20', 'expense', 'Сервер', 'Play2go', 800.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (50, '2026-05-21', 'income', 'Прибыль', 'Platega пополнение', 180.00, 'Пополнение на 200 ₽', 'b674a7f8-b17a-4cbd-a49b-10f8b2e044bc', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (51, '2026-05-23', 'expense', 'Сервер', 'EternityCloud', 270.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (52, '2026-05-23', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '49d9cb85-a341-436f-a2d8-22f6ad4b70f2', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (53, '2026-05-24', 'expense', 'Сервер', 'EternityCloud', 270.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (54, '2026-05-25', 'expense', 'Сервер', 'Sweb', 274.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (55, '2026-05-26', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '2378ff79-ebd6-40e6-ba92-11d352ec5323', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (56, '2026-05-26', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'd5e6a99d-e582-4fde-b22a-6aa4ddbc922c', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (57, '2026-05-26', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '8f99b9a4-ba96-4eb0-9768-c3e362bda143', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (111, '2026-07-08', 'expense', 'Сервер', 'Play2go', 340.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (58, '2026-05-27', 'income', 'Прибыль', 'Platega пополнение', 45.00, 'Пополнение на 50 ₽', 'd02c756c-76eb-47df-9cac-39e8fbe06f52', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (59, '2026-05-27', 'income', 'Прибыль', 'Platega пополнение', 90.00, 'Пополнение на 100 ₽', '528790f8-5828-43b3-a242-1fcb3e73f6ab', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (60, '2026-05-27', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'd3e0afe3-e8c5-4540-aba8-0b81fcc4701f', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (61, '2026-05-28', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'd2acefdc-f66c-4662-81fe-4eda3b3d2250', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (62, '2026-05-29', 'income', 'Прибыль', 'Platega пополнение', 450.00, 'Пополнение на 500 ₽', 'b4fab7bd-9f4b-4604-9361-d62e6833d445', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (63, '2026-05-30', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'c3511e05-0972-4e0e-8876-850839bcbba1', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (64, '2026-06-01', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '5390ba20-5d02-4ab2-a185-b9da7e6f4a08', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (65, '2026-06-02', 'income', 'Прибыль', 'Platega пополнение', 405.00, 'Пополнение на 450 ₽', '36823607-8de6-4fa4-936d-601a40fe82eb', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (66, '2026-06-04', 'expense', 'Сервер', 'Beget', 50.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (67, '2026-06-04', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'ea0b9912-95c6-4a60-a9c9-8aca1e9ce9f0', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (68, '2026-06-04', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '3f531579-5c9e-4088-b91d-489cb0baf2a1', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (69, '2026-06-06', 'expense', 'Сервер', 'Beget', 50.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (70, '2026-06-06', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'a0e3d062-9582-43a3-996d-dd42d8d6a6e2', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (71, '2026-06-08', 'income', 'Прибыль', 'Platega пополнение', 189.00, 'Пополнение на 210 ₽', 'a408cd68-1a35-45b0-b942-f7d72d9211e8', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (72, '2026-06-09', 'expense', 'Сервер', 'Sweb', 206.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (73, '2026-06-09', 'expense', 'Сервер', 'NuxtCloud', 234.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (74, '2026-06-09', 'expense', 'Сервер', 'Beget', 500.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (75, '2026-06-09', 'expense', 'Сервер', 'Play2go', 330.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (76, '2026-06-10', 'expense', 'INCY', 'INCY_Prem', 486.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (77, '2026-06-12', 'expense', 'Другое', 'Platega комиссия вывода', 240.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (78, '2026-06-12', 'expense', 'Хостинг', 'Play2go', 250.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (79, '2026-06-12', 'expense', 'Сервер', 'Play2go', 150.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (80, '2026-06-13', 'expense', 'Домен', 'reg.ru', 170.00, 'Оплата услуг Регистрация домена zaqxs1.ru / zaqxs1.online', NULL, '2026-09-13 14:32:58', '2026-09-24 12:41:47');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (81, '2026-06-13', 'expense', 'Другое', 'INFO GHOST OS', 4000.00, 'Гайды по конфигам и настройкам', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (82, '2026-06-13', 'expense', 'Сервер', 'Sweb', 478.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (83, '2026-06-19', 'expense', 'Сервер', 'Play2go', 728.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (84, '2026-06-20', 'expense', 'Сервер', 'NuxtCloud', 133.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (85, '2026-06-20', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '92f1e2ac-ea1f-4431-8a59-7517282a038c', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (86, '2026-06-21', 'income', 'Прибыль', 'Platega пополнение', 450.00, 'Пополнение на 500 ₽', 'f731aa1e-abbc-4cd0-9430-e9a45c35f314', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (87, '2026-06-24', 'expense', 'Сервер', 'Beget', 500.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (88, '2026-06-24', 'expense', 'Сервер', 'Play2go', 340.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (89, '2026-06-24', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '87729f37-d1c4-419f-9abf-7ea3aeaf3d96', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (90, '2026-06-24', 'income', 'Прибыль', 'Platega пополнение', 126.00, 'Пополнение на 140 ₽', 'dc7eddbb-cc93-4b97-9f0f-4d75a42757bb', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (91, '2026-06-24', 'income', 'Прибыль', 'Platega пополнение', 9.00, 'Пополнение на 10 ₽', '66e388fc-c9a2-4dc3-9870-05dfaee490e8', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (92, '2026-06-24', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '944afc83-ab95-4b8e-abd9-63777b7e3f95', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (93, '2026-06-25', 'income', 'Прибыль', 'Sweb', 656.00, 'Возврат', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (94, '2026-06-25', 'income', 'Прибыль', 'Platega пополнение', 90.00, 'Пополнение на 100 ₽', '2a5535ff-0971-4b6f-aa83-90ffba7034bb', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (95, '2026-06-25', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'e705fb2e-9cac-49c0-a088-7b1286f45137', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (96, '2026-06-25', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'c29041cc-c5a0-4fe6-b261-8c310c21810c', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (97, '2026-06-27', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'fcabde73-9eee-4fdd-9a48-77196385b738', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (98, '2026-06-28', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '8bb4f6d4-2619-465d-bf69-87f732919e76', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (99, '2026-06-29', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'a66e3fcc-5a16-4a9e-99b6-78eeef3f4127', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (100, '2026-06-29', 'income', 'Прибыль', 'Platega пополнение', 450.00, 'Пополнение на 500 ₽', '74a88eb0-af92-4fe9-a82a-e4ddb64bfd5c', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (101, '2026-06-29', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '664edd1f-fca3-4f81-a04d-886ea55d0f9a', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (102, '2026-07-01', 'income', 'Прибыль', 'Platega пополнение', 189.00, 'Пополнение на 210 ₽', 'e05d7392-07ee-4816-b2b9-277046905b73', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (103, '2026-07-03', 'expense', 'Сервер', 'Beget', 500.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (104, '2026-07-03', 'income', 'Прибыль', 'Platega пополнение', 378.00, 'Пополнение на 420 ₽', 'dd625b48-c927-4cf5-923a-e24ba7a4473a', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (105, '2026-07-05', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '738d32a0-085d-48d6-ab58-12c48bdf3c56', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (106, '2026-07-05', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '16a9e2d3-c7ba-4f3b-b274-7c9a995ae79f', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (107, '2026-07-05', 'income', 'Прибыль', 'Platega пополнение', 189.00, 'Пополнение на 210 ₽', 'c47bb442-58a5-494c-8799-18f1594e3361', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (108, '2026-07-06', 'income', 'Прибыль', 'Platega пополнение', 288.00, 'Пополнение на 320 ₽', '0727bfdb-5bc3-4b06-8087-5b28fe897074', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (109, '2026-07-07', 'expense', 'Другое', 'Platega комиссия вывода', 240.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (110, '2026-07-07', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '5d7fdcce-cf8a-45d3-8917-ac28889e6666', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (112, '2026-07-08', 'expense', 'Сервер', 'Beget', 500.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (113, '2026-07-09', 'expense', 'INCY', 'INCY_Prem', 518.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (114, '2026-07-10', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '030db6d3-544f-4622-b022-6d88a101ef1c', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (115, '2026-07-10', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '1b73fec8-4df5-4b91-a60a-2c5dcc0ff45b', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (116, '2026-07-11', 'income', 'Прибыль', 'Platega пополнение', 405.00, 'Пополнение на 450 ₽', 'b580fefb-8428-4781-83cd-adf86fa91be4', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (117, '2026-07-17', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'b36c3435-8869-4db1-96f6-bcce84dca4b7', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (118, '2026-07-19', 'expense', 'Сервер', 'NuxtCloud', 362.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (119, '2026-07-20', 'expense', 'Сервер', 'Beget', 100.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (120, '2026-07-21', 'expense', 'Сервер', 'Beget', 500.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (121, '2026-07-21', 'expense', 'Сервер', 'Play2go', 850.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (122, '2026-07-25', 'expense', 'Сервер', 'YottaSrc', 500.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (123, '2026-07-25', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '9ea1edb3-29be-4a2e-9867-e479b6a94d31', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (124, '2026-07-26', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'f2cd1b2b-0dc7-4056-9648-f300cd924f7e', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (125, '2026-07-26', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '7a2f58b6-dd66-462e-b542-2592a0c1273a', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (126, '2026-07-26', 'income', 'Прибыль', 'Platega пополнение', 247.50, 'Пополнение на 275 ₽', '00f3ee97-9be4-4994-a2d8-17732631bd82', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (127, '2026-07-26', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '57003660-b64f-4dac-a646-b95c6a1d4098', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (128, '2026-07-27', 'income', 'Прибыль', 'Platega пополнение', 9.00, 'Пополнение на 10 ₽', '8b972214-9cb8-4adc-b2d2-80fd4e91be75', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (129, '2026-07-27', 'income', 'Прибыль', 'Platega пополнение', 45.00, 'Пополнение на 50 ₽', '945d18b1-d744-46d0-bce5-2fa7a967e0f0', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (130, '2026-07-27', 'income', 'Прибыль', 'Platega пополнение', 450.00, 'Пополнение на 500 ₽', '0469a669-4d60-4d11-bbaa-6ab89d565559', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (131, '2026-07-27', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'dda4d731-5cbc-4c4c-ba9b-d7407aeff815', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (132, '2026-07-27', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '531e745d-b1d7-402d-936e-7aeafa7c579c', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (133, '2026-07-28', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '58cf76dc-e05b-4659-a5f2-3f06d82aec4b', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (134, '2026-07-29', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '4f564d86-f60a-4946-a447-dca83455257d', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (135, '2026-07-29', 'income', 'Прибыль', 'Platega пополнение', 189.00, 'Пополнение на 210 ₽', '26d6c303-6a3c-4437-96f9-aab616edc527', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (136, '2026-07-29', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'e22de179-6015-4263-a59d-a1003069d9b5', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (137, '2026-07-29', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'facfbf09-6b75-49e5-b397-75560f623713', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (138, '2026-07-31', 'expense', 'Сервер', 'Beget', 500.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (139, '2026-07-31', 'expense', 'Другое', 'Platega комиссия вывода', 240.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (140, '2026-07-31', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '80143797-cf80-43d5-b667-e234439b54b5', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (141, '2026-07-31', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'ea9a7b2b-4796-4b8d-a832-81cdb879de28', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (142, '2026-07-31', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'da9e208b-61d6-4623-99a1-54e98e3b6424', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (143, '2026-07-31', 'income', 'Прибыль', 'Platega пополнение', 450.00, 'Пополнение на 500 ₽', 'b489c5c0-d50d-4cef-850f-6d492fcf006f', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (144, '2026-07-31', 'expense', 'ИИ', 'RouterAI', 600.00, 'Андрей', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (145, '2026-08-01', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '04079457-7053-40b5-b2a0-258bf5fbecf4', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (146, '2026-08-01', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'dacaa2be-99b6-4b9c-9f2d-5380cc1d7e42', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (147, '2026-08-01', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '8626d50a-6c81-4d2d-86d7-adb6256ecd45', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (148, '2026-08-01', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '1ad5fce6-86df-459b-b536-1995b86f3dca', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (149, '2026-08-02', 'income', 'Прибыль', 'Platega пополнение', 405.00, 'Пополнение на 450 ₽', 'f796bddd-709d-462f-b337-44d2804d6b1d', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (150, '2026-08-03', 'income', 'Прибыль', 'Platega пополнение', 315.00, 'Пополнение на 350 ₽', '7987cdac-9f47-4833-be13-1b1c021df208', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (151, '2026-08-03', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '40ab089c-c03d-4b69-ac7b-ee4c0384129f', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (152, '2026-08-05', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'fb99951c-b329-48ee-961e-f6f9df7bbc5a', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (153, '2026-08-05', 'income', 'Прибыль', 'Platega пополнение', 19.80, 'Пополнение на 22 ₽', '66785f50-36f5-4d00-a43c-853faead979a', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (154, '2026-08-06', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'de0d3629-85cb-44fe-9b19-996b7a9e438e', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (155, '2026-08-07', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '2633a137-5eb7-45e3-b491-043eb062a031', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (156, '2026-08-08', 'expense', 'Сервер', 'Beget', 500.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (157, '2026-08-08', 'expense', 'Другое', 'INCY_Prem', 575.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (158, '2026-08-08', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '1fb4fcac-b2d9-444e-b8f2-a1945b917c66', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (159, '2026-08-09', 'expense', 'Сервер', 'Play2go', 340.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (160, '2026-08-10', 'income', 'Прибыль', 'Platega пополнение', 15.75, 'Пополнение на 17 ₽', '7030b75a-0b03-4975-a141-4c110f9ee4c8', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (161, '2026-08-10', 'income', 'Прибыль', 'Platega пополнение', 15.75, 'Пополнение на 17 ₽', 'd90b9bd6-863e-4e8c-b2c5-819c87c59f0d', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (162, '2026-08-14', 'income', 'Прибыль', 'Platega пополнение', 540.00, 'Пополнение на 600 ₽', '5b4917c0-bbbf-48b5-9752-82ed3c432433', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (163, '2026-08-15', 'expense', 'Сервер', 'Beget', 542.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (164, '2026-08-15', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '5f6ea4e5-ec95-45f8-983f-5c55c057777e', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (165, '2026-08-17', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '5d1b8297-26a3-4b5f-b15c-7fc19db539af', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (166, '2026-08-17', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '6f35cff2-e060-4220-af6d-499b7fc0ed26', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (167, '2026-08-18', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '53481ce2-ea3c-4524-b96f-7923150ffa09', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (168, '2026-08-18', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'cdcec01e-0537-4035-bbf8-249a185f9421', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (169, '2026-08-19', 'expense', 'Сервер', 'NuxtCloud', 362.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (170, '2026-08-19', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', 'c68ca0ae-475e-4804-aa2b-b70cffcda8be', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (171, '2026-08-21', 'income', 'Прибыль', 'Platega пополнение', 31.50, 'Пополнение на 35 ₽', '5c26c659-e3bd-4025-905d-662d30e1b5af', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (172, '2026-08-21', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '877e0a27-fe03-47d1-bce8-85cef948c7ba', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (173, '2026-08-21', 'income', 'Прибыль', 'Platega пополнение', 51.30, 'Пополнение на 57 ₽', 'f5c2d826-dc13-4f37-824d-4be66782338d', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (174, '2026-08-22', 'expense', 'Сервер', 'Play2go', 850.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (175, '2026-08-22', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'f126a238-f4d6-4b16-a920-5ead1d990376', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (176, '2026-08-23', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'cbc0dcbf-becc-408f-bbbf-9757e8197730', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (177, '2026-08-23', 'income', 'Прибыль', 'Platega пополнение', 630.00, 'Пополнение на 700 ₽', '5e167e58-de45-4d36-a6ec-aa5a3ddc3ba2', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (178, '2026-08-24', 'expense', 'Сервер', 'Beget', 360.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (179, '2026-08-24', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'd0cb2848-0871-48fa-9fd6-542c0e25aaee', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (180, '2026-08-24', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '9db5e46b-c257-45d9-9b4f-b06ef5b48f40', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (181, '2026-08-24', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '37cdbcf9-31cc-4b89-8605-c04eb4a41742', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (182, '2026-08-24', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '5e361969-1079-4541-ba76-a3bd2b29303f', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (183, '2026-08-25', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', 'c84a1482-d306-485d-86f2-6d5843a0de13', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (184, '2026-08-25', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'f1a484a8-d589-4ea2-acfa-69c2af456620', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (185, '2026-08-25', 'income', 'Прибыль', 'Platega пополнение', 90.00, 'Пополнение на 100 ₽', '4735ac1b-d448-438e-a008-7a3ee81e191b', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (186, '2026-08-26', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'dc6ef137-aef9-4edb-98a3-c31f5902ff09', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (187, '2026-08-26', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '2ae03336-20bf-4b9e-9716-d1b9518a7bc9', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (188, '2026-08-26', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '2617f924-2bf3-4df2-9c6c-9b1060998354', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (189, '2026-08-28', 'expense', 'Сервер', 'YottaSrc', 512.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (190, '2026-08-28', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'fc039c82-ca92-42c7-9e39-ea9b186678cf', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (191, '2026-08-28', 'income', 'Прибыль', 'Platega пополнение', 450.00, 'Пополнение на 500 ₽', 'f30e6ae5-cf18-45ff-b830-eabc18e354bf', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (192, '2026-08-29', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'd1464474-4753-4504-a7b5-ce57c48efb4e', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (193, '2026-08-29', 'income', 'Прибыль', 'Platega пополнение', 202.50, 'Пополнение на 225 ₽', '2731d8b3-8eb6-4f39-b271-2dd189a63cb9', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (194, '2026-08-29', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '0c0a88bf-68c0-431a-964a-de6779c081ee', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (195, '2026-08-29', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'a0211f50-86e3-439e-a13b-6e208a328533', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (196, '2026-08-29', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '412c5d3c-77df-4921-9723-25520d00bf53', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (197, '2026-08-30', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', 'ea22df02-2d5e-4f79-96c5-21c9a17d264a', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (198, '2026-08-30', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '0d5100b4-e127-403c-bd29-277fc4c7f9e3', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (199, '2026-08-30', 'income', 'Прибыль', 'Platega пополнение', 1125.00, 'Пополнение на 1250 ₽', '1e1f7918-73a8-4a0f-8bf4-423a7d2558c7', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (200, '2026-08-30', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '2ad5410c-e9ca-4694-8e4d-18ef373a12f6', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (201, '2026-08-30', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'ada562da-801c-4eac-8eec-1141f53b7263', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (202, '2026-08-31', 'expense', 'ИИ', 'RouterAI', 1200.00, 'Андрей', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (203, '2026-08-31', 'income', 'Прибыль', 'Platega пополнение', 202.50, 'Пополнение на 225 ₽', 'e50ff547-b9b1-4f3c-9fdc-c3fdbc6ccc7b', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (204, '2026-08-31', 'income', 'Прибыль', 'Platega пополнение', 450.00, 'Пополнение на 500 ₽', '8f643d10-9691-4816-83a6-5ccb608761de', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (205, '2026-09-01', 'expense', 'Сервер', 'Beget', 1860.00, 'Ру сервера за месяц', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (206, '2026-09-01', 'expense', 'INCY', 'INCY_Prem', 867.00, '150 устройств', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (207, '2026-09-01', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'c51c106f-fb5b-4b58-9bb7-69072e7aa1f3', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (208, '2026-09-01', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '67b47c8a-4420-4377-b84e-d3f4c2cfea22', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (209, '2026-09-02', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '14e1fa66-4cf0-41a5-b8bd-ddf187cd726b', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (210, '2026-09-02', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', 'b18e66ad-8491-480b-9c45-bb77fb333625', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (211, '2026-09-02', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '1373f4ec-b05d-4728-a792-491a43f3e1c8', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (212, '2026-09-03', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '82034bcd-b242-47a9-a145-7911d99e70ab', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (213, '2026-09-04', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '48528f95-343d-4541-9f5a-03ffd1fb9543', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (214, '2026-09-05', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'baabc7af-b2fe-4a41-a478-64d394107669', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (215, '2026-09-06', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '64369261-5a18-4634-9dd8-c94445973415', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (216, '2026-09-06', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '32c577d8-30d2-46a7-9497-c11ef0e7dcdc', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (217, '2026-09-06', 'income', 'Прибыль', 'Platega пополнение', 202.50, 'Пополнение на 225 ₽', '895d13a6-ceaa-4fb1-b9e8-7b4387d46143', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (218, '2026-09-08', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'bb46af91-1fa2-411b-abb9-65d041dd3dbe', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (219, '2026-09-09', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'd85e65d8-bf98-4411-9a17-0c9f59ccf17a', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (220, '2026-09-09', 'income', 'Прибыль', 'Platega пополнение', 540.00, 'Пополнение на 600 ₽', '150d619b-9856-4b73-a274-2b1a7085dfcf', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (221, '2026-09-09', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'b5416d02-e8e8-4ae9-a292-041e6fe0743d', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (222, '2026-09-09', 'expense', 'Сервер', 'Play2go', 300.00, '', NULL, '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (223, '2026-09-10', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '7e23d17f-f756-414d-ba03-d18ad726622d', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (224, '2026-09-10', 'income', 'Прибыль', 'Platega пополнение', 202.50, 'Пополнение на 225 ₽', 'efa31740-6a55-45fb-bec7-70faf9ab3a04', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (225, '2026-09-11', 'income', 'Прибыль', 'Platega пополнение', 202.50, 'Пополнение на 225 ₽', 'a2e7775f-68de-42d7-b7e1-ffd3b531c845', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (226, '2026-09-25', 'expense', 'ИИ', 'RouterAI', 1800.00, 'Андрей', NULL, '2026-09-13 14:32:58', '2026-09-26 02:11:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (227, '2026-09-11', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', 'd8d64276-5bfc-4ff1-bcbc-98eb7c7da230', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (228, '2026-09-11', 'income', 'Прибыль', 'Platega пополнение', 202.50, 'Пополнение на 225 ₽', '22ca22cb-0dfc-42a2-be2d-d7dde04a1b56', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (229, '2026-09-12', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '5738d0cd-a61a-42af-a5a0-bb48d3e7511a', '2026-09-13 14:32:58', '2026-09-13 14:32:58');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (230, '2026-09-13', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '78413158-4f38-43df-80c0-08a5b8f2a3af', '2026-09-13 18:30:05', '2026-09-13 18:30:05');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (231, '2026-09-13', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', 'db8c1aad-2eef-447e-bf16-4e66cc925067', '2026-09-13 19:15:05', '2026-09-13 19:15:05');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (232, '2026-09-15', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '938e737f-63f5-41db-a1cf-bae3c46c3454', '2026-09-15 10:01:45', '2026-09-15 10:01:45');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (233, '2026-09-15', 'income', 'Прибыль', 'Platega пополнение', 202.50, 'Пополнение на 225 ₽', '366c6e09-e954-48b3-95f2-01c8e2d61ec0', '2026-09-15 18:37:35', '2026-09-15 18:37:35');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (234, '2026-09-16', 'income', 'Прибыль', 'Platega пополнение', 202.50, 'Пополнение на 225 ₽', 'e562ba6b-8ec1-4dc6-b560-b124b8067478', '2026-09-16 16:22:46', '2026-09-16 16:22:46');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (235, '2026-09-17', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '650e7546-d909-48f4-8897-6199139502a9', '2026-09-19 08:21:55', '2026-09-19 08:21:55');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (236, '2026-09-17', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '5e735efc-a792-461f-9d3c-1fa0036130da', '2026-09-19 08:21:55', '2026-09-19 08:21:55');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (237, '2026-09-19', 'expense', 'Сервер', 'NuxtCloud', 363.00, 'Германия01', NULL, '2026-09-19 08:23:29', '2026-09-19 08:23:29');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (239, '2026-09-19', 'income', 'Прибыль', 'Platega пополнение', 292.50, 'Пополнение на 325 ₽', '12991132-684a-438e-8be6-9ce04aba88f9', '2026-09-20 13:42:10', '2026-09-20 13:42:10');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (240, '2026-09-20', 'expense', 'Сервер', 'Play2go', 850.00, 'Панель', NULL, '2026-09-20 13:47:21', '2026-09-20 13:47:21');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (241, '2026-09-20', 'income', 'Прибыль', 'Platega пополнение', 540.00, 'Пополнение на 600 ₽', 'a28b909b-dd54-4896-b7b5-2de0a503d0e7', '2026-09-20 14:35:33', '2026-09-20 14:35:33');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (242, '2026-09-20', 'income', 'Прибыль', 'Platega пополнение', 189.00, 'Пополнение на 210 ₽', '4aab8866-f9f3-443d-958a-c0a96d1732a4', '2026-09-20 17:00:34', '2026-09-20 17:00:34');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (243, '2026-09-21', 'income', 'Прибыль', 'Platega пополнение', 67.50, 'Пополнение на 75 ₽', '723fdcc6-1aa6-456d-b423-3e0081353a00', '2026-09-21 17:05:53', '2026-09-21 17:05:53');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (244, '2026-09-21', 'income', 'Прибыль', 'Platega пополнение', 450.00, 'Пополнение на 500 ₽', '9c5049af-1955-4482-b4a2-2c8b5c39c8a7', '2026-09-21 17:05:53', '2026-09-21 17:05:53');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (245, '2026-09-20', 'income', 'Прибыль', 'Platega пополнение', 270.00, 'Пополнение на 300 ₽', '7b8f449d-8ddc-4570-8b1c-7d1991d475f2', '2026-09-21 17:05:53', '2026-09-21 17:05:53');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (246, '2026-09-20', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'ad2448bb-ecae-4527-947b-b97e9f246d4b', '2026-09-21 17:05:53', '2026-09-21 17:05:53');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (247, '2026-09-22', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', 'ae7a0dc7-1e1f-47d0-befb-db10a55da773', '2026-09-22 23:12:01', '2026-09-22 23:12:01');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (248, '2026-09-22', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '8f34e641-cf08-4c38-89d1-400598b5d03b', '2026-09-22 23:12:01', '2026-09-22 23:12:01');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (249, '2026-09-24', 'income', 'Прибыль', 'Platega пополнение', 135.00, 'Пополнение на 150 ₽', '6d0b6a3b-e2e2-4e8d-96ad-6c2bd5d6d0e8', '2026-09-24 11:32:50', '2026-09-24 11:32:50');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (250, '2026-09-24', 'expense', 'Сервер', 'Play2go', 450.00, 'смена IP + продление Нидерланд', NULL, '2026-09-24 11:48:29', '2026-09-24 11:48:29');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (251, '2026-03-08', 'expense', 'Домен', 'reg.ru', 129.00, 'Оплата услуг Регистрация домена fortf.ru', NULL, '2026-09-24 12:40:47', '2026-09-24 12:46:30');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (252, '2026-07-05', 'expense', 'Домен', 'reg.ru', 305.00, 'Оплата услуг Регистрация домена hexaveil.xyz', NULL, '2026-09-24 12:43:34', '2026-09-24 12:43:34');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (253, '2026-09-02', 'expense', 'Домен', 'reg.ru', 509.00, 'Оплата услуг Регистрация домена monolist.art', NULL, '2026-09-24 12:45:15', '2026-09-24 12:45:15');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (254, '2026-09-18', 'expense', 'Домен', 'reg.ru', 249.00, 'Оплата услуг Регистрация домена qazws.online', NULL, '2026-09-24 12:45:49', '2026-09-24 12:45:49');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (255, '2026-09-25', 'income', 'Прибыль', 'Platega пополнение', 280.80, 'Пополнение на 300 ₽', '14e15c7d-5c29-4eb9-945e-4caeaa2159e9', '2026-09-25 13:49:56', '2026-09-25 13:49:56');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (256, '2026-09-25', 'income', 'Прибыль', 'YooKassa', 482.50, 'HexaVeil - Пополнение баланса на 500 ₽ (U189)', 'yk_3248e12c-000f-5000-b000-1f2dfdad2544', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (257, '2026-09-25', 'income', 'Прибыль', 'YooKassa', 579.00, 'HexaVeil - Пополнение баланса на 600 ₽ (U189)', 'yk_3248e0e9-000f-5000-b000-161ec8833e7e', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (258, '2026-09-25', 'income', 'Прибыль', 'YooKassa', 265.38, 'HexaVeil - Пополнение баланса на 275 ₽ (ID 515449275)', 'yk_3248c04f-000f-5000-b000-1fc8f60e1908', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (259, '2026-09-25', 'income', 'Прибыль', 'YooKassa', 265.38, 'HexaVeil - Пополнение баланса на 275 ₽ (ID 515449275)', 'yk_3248bf9f-000f-5001-8000-134ca7e2c771', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (260, '2026-09-25', 'income', 'Прибыль', 'YooKassa', 173.70, 'HexaVeil - Пополнение баланса на 180 ₽ (ID 7893753552)', 'yk_3248b280-000f-5000-b000-19d6432e8edc', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (261, '2026-09-25', 'income', 'Прибыль', 'YooKassa', 270.20, 'HexaVeil - Пополнение баланса на 280 ₽ (U305)', 'yk_3248a99f-000f-5001-9000-15f1f3fd1484', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (262, '2026-09-25', 'income', 'Прибыль', 'YooKassa', 579.00, 'HexaVeil - Пополнение баланса на 600 ₽ (U305)', 'yk_324896dd-000f-5001-8000-1a3804348089', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (263, '2026-09-25', 'income', 'Прибыль', 'YooKassa', 144.75, 'HexaVeil - Пополнение баланса на 150 ₽ (ID 985412154)', 'yk_3248524c-000f-5001-8000-16190de2ca6f', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (264, '2026-09-25', 'income', 'Прибыль', 'YooKassa', 579.00, 'HexaVeil - Пополнение баланса на 600 ₽ (U269)', 'yk_324828d5-000f-5001-a000-196fdc9422b2', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (265, '2026-09-24', 'income', 'Прибыль', 'YooKassa', 144.75, 'HexaVeil - Пополнение баланса на 150 ₽ (ID 543871882)', 'yk_32478f93-000f-5000-b000-15ca40f10be3', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (266, '2026-09-24', 'income', 'Прибыль', 'YooKassa', 1189.85, 'HexaVeil - Пополнение баланса на 1233 ₽ (ID 464624186)', 'yk_32475f4e-000f-5001-9000-12357eedd949', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (267, '2026-09-24', 'income', 'Прибыль', 'YooKassa', 72.38, 'HexaVeil - Пополнение баланса на 75 ₽ (ID 461538917)', 'yk_3247417d-000f-5001-9000-10ad48578633', '2026-09-26 01:59:51', '2026-09-26 01:59:51');
INSERT INTO public.fin_transactions (id, date, type, category, participant, amount, description, record_id, created_at, updated_at) VALUES (268, '2026-09-26', 'income', 'Прибыль', 'YooKassa', 144.75, 'HexaVeil - Пополнение баланса на 150 ₽ (ID 5181407388)', 'yk_32496c57-000f-5001-9000-12ed103909fa', '2026-09-26 10:27:55', '2026-09-26 10:27:55');


ALTER TABLE public.fin_transactions ENABLE TRIGGER ALL;

--
-- Data for Name: media; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.media DISABLE TRIGGER ALL;



ALTER TABLE public.media ENABLE TRIGGER ALL;

--
-- Data for Name: menus; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.menus DISABLE TRIGGER ALL;



ALTER TABLE public.menus ENABLE TRIGGER ALL;

--
-- Data for Name: menu_items; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.menu_items DISABLE TRIGGER ALL;



ALTER TABLE public.menu_items ENABLE TRIGGER ALL;

--
-- Data for Name: pages; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.pages DISABLE TRIGGER ALL;



ALTER TABLE public.pages ENABLE TRIGGER ALL;

--
-- Data for Name: tags; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.tags DISABLE TRIGGER ALL;



ALTER TABLE public.tags ENABLE TRIGGER ALL;

--
-- Data for Name: post_tags; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.post_tags DISABLE TRIGGER ALL;



ALTER TABLE public.post_tags ENABLE TRIGGER ALL;

--
-- Data for Name: settings; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.settings DISABLE TRIGGER ALL;

INSERT INTO public.settings (id, setting_key, setting_value) VALUES (2, 'site_url', 'https://test.hexaveil.xyz');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (9, 'hexaveil_cabinet_url', 'https://cabinet.fortf.ru/login');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (10, 'hexaveil_referral_url', 'https://cabinet.fortf.ru/referral');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (11, 'hexaveil_telegram_url', 'https://t.me/HexaVeil_bot');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (12, 'hexaveil_cta_label', 'Личный кабинет');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (13, 'hexaveil_tagline_line1', 'Ваш надежный VPN&nbsp;провайдер');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (14, 'hexaveil_tagline_line2', 'в мир интернета');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (15, 'hexaveil_tagline_subtitle', 'Смотрите любимые сериалы, работайте с международными сервисами и общайтесь без ограничений.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (16, 'hexaveil_tagline_btn1', 'Попробовать бесплатно');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (17, 'hexaveil_tagline_btn2', 'Как это работает');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (18, 'hexaveil_benefit1', 'Все мировые сервисы: Instagram, YouTube без рекламы, ChatGPT, Netflix, Discord');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (19, 'hexaveil_benefit2', 'Российские сервисы работают - VPN не нужно выключать');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (20, 'hexaveil_benefit3', 'Живая поддержка 24/7 - решает вопросы, а не кормит ответами бота');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (21, 'hexaveil_benefit4', 'Стабильная работа благодаря распределённым серверам');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (22, 'hexaveil_hero_note', 'Выберите сервер — планета подлетит к нему');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (23, 'hexaveil_stat1_num', '10+');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (24, 'hexaveil_stat1_label', 'Стран с серверами');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (25, 'hexaveil_stat2_num', '99.9%');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (26, 'hexaveil_stat2_label', 'Время работы (Uptime)');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (27, 'hexaveil_stat3_num', '10 Гбит/с');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (28, 'hexaveil_stat3_label', 'Пропускная способность');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (29, 'hexaveil_stat4_num', '10K+');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (30, 'hexaveil_stat4_label', 'Активных пользователей');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (31, 'hexaveil_trial_badge', 'Без оплаты и обязательств');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (32, 'hexaveil_trial_title', 'Попробуйте HexaVeil бесплатно');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (33, 'hexaveil_trial_subtitle', 'Получите 24 часа полного доступа - без ввода карты и автоматических списаний. Убедитесь в скорости и стабильности на реальных сервисах, и только потом решайте.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (34, 'hexaveil_trial_step1_title', 'Авторизуйтесь');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (35, 'hexaveil_trial_step1_text', 'Авторизуйтесь в личном кабинете удобным для тебя способом');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (36, 'hexaveil_trial_step2_title', 'Получите конфиг');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (37, 'hexaveil_trial_step2_text', 'Бот пришлёт готовую конфигурацию для вашего устройства');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (38, 'hexaveil_trial_step3_title', 'Подключайтесь');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (39, 'hexaveil_trial_step3_text', 'Импортируйте в любой клиент - и пользуйтесь 72 часа');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (40, 'hexaveil_trial_button', 'Получить бесплатный доступ');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (41, 'hexaveil_trial_note', 'Триал ограничен одним устройством на аккаунт. Без автосписаний - решение за вами.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (42, 'hexaveil_feature1_title', 'Доступ к любимым сервисам');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (43, 'hexaveil_feature1_text', 'YouTube, ChatGPT, Netflix, Spotify и другие международные платформы - стабильно, быстро и без лишних действий.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (44, 'hexaveil_feature2_title', 'Защищённое соединение');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (45, 'hexaveil_feature2_text', 'Ваш трафик шифруется и проходит через наши серверы. Провайдер не видит, какие ресурсы вы посещаете.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (46, 'hexaveil_feature3_title', '10+ стран мира');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (47, 'hexaveil_feature3_text', 'Серверы в Европе, Азии и Америке. Выбирайте локацию для минимальной задержки и максимальной скорости.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (48, 'hexaveil_feature4_title', 'Стриминг без буферизации');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (49, 'hexaveil_feature4_text', 'Видео в 4K и музыка в высоком качестве - без задержек и прерываний. Выделенные каналы для медиа-трафика.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (50, 'hexaveil_services_title', 'Открой любимые сервисы');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (51, 'hexaveil_services_intro', 'Мы гарантируем стабильное соединение с самыми популярными международными платформами.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (52, 'hexaveil_services_list', 'YouTube
ChatGPT
Netflix
Spotify
Claude AI
X (Twitter)
Discord');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (53, 'hexaveil_services_note', 'Список сервисов регулярно расширяется. Если нужной платформы нет в списке - напишите в поддержку, добавим.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (54, 'hexaveil_tech1_title', 'Современный протокол');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (55, 'hexaveil_tech1_text', 'VLESS - для скорости и незаметности трафика.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (56, 'hexaveil_tech2_title', 'Без журналов подключений');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (57, 'hexaveil_tech2_text', 'Мы не отслеживаем ваши действия и не сохраняем историю посещений. Ваша приватность для нас действительно важна!');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (58, 'hexaveil_tech3_title', 'Шифрование AES-256');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (59, 'hexaveil_tech3_text', 'Ваши данные защищены военным стандартом шифрования. Трафик невозможно перехватить и прочитать.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (60, 'hexaveil_referral_title', 'Приглашайте друзей - получайте бонусы');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (61, 'hexaveil_referral_intro', 'Делитесь персональной ссылкой: вы и друг получите по 50 ₽, а вы - ещё 20% с его пополнений. Чем больше друзей - тем выгоднее.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (62, 'hexaveil_referral_card1_value', '+50 ₽');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (63, 'hexaveil_referral_card1_title', 'Вам за друга');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (64, 'hexaveil_referral_card1_text', 'За каждого друга, который оплатит подписку по вашей ссылке');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (65, 'hexaveil_referral_card2_value', '+50 ₽');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (66, 'hexaveil_referral_card2_title', 'Другу на старт');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (67, 'hexaveil_referral_card2_text', 'Подарок другу к первой оплате по вашей ссылке');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (68, 'hexaveil_referral_card3_value', '20%');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (69, 'hexaveil_referral_card3_title', 'С пополнений');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (70, 'hexaveil_referral_card3_text', 'Процент с пополнений ваших рефералов - навсегда');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (71, 'hexaveil_referral_button', 'Получить реферальную ссылку');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (72, 'hexaveil_referral_note', 'Бонусы начисляются автоматически в личном кабинете после оплаты минимальной суммы в 150 ₽ рефералом.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (73, 'hexaveil_footer_copyright', '© 2026 HexaVeil. Защищённый доступ к мировому интернету.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (5, 'site_description', 'Сайт на собственной CMS');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (1, 'site_name', 'HexaVeil – Доступ к мировому интернету');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (3, 'admin_email', 'imcrazymonk@gmail.com');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (4, 'posts_per_page', '10');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (6, 'meta_description', 'Обходи блокировки и пользуйся любимыми иностранными сервисами. Современный VPN с киберпанк-эстетикой.');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (7, 'meta_keywords', '');
INSERT INTO public.settings (id, setting_key, setting_value) VALUES (8, 'active_theme', 'hexaveil');


ALTER TABLE public.settings ENABLE TRIGGER ALL;

--
-- Data for Name: user_preferences; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.user_preferences DISABLE TRIGGER ALL;

INSERT INTO public.user_preferences (user_id, pref_key, pref_value) VALUES (1, 'panel_ui_state', '{"theme":"obsidian","mode":"dark","test":true}');
INSERT INTO public.user_preferences (user_id, pref_key, pref_value) VALUES (1, 'theme', 'ember');


ALTER TABLE public.user_preferences ENABLE TRIGGER ALL;

--
-- Data for Name: widgets; Type: TABLE DATA; Schema: public; Owner: cms
--

ALTER TABLE public.widgets DISABLE TRIGGER ALL;



ALTER TABLE public.widgets ENABLE TRIGGER ALL;

--
-- Name: app_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.app_logs_id_seq', 573, true);


--
-- Name: categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.categories_id_seq', 2, true);


--
-- Name: comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.comments_id_seq', 1, false);


--
-- Name: fin_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.fin_settings_id_seq', 419, true);


--
-- Name: fin_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.fin_transactions_id_seq', 76, true);


--
-- Name: media_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.media_id_seq', 1, false);


--
-- Name: menu_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.menu_items_id_seq', 1, false);


--
-- Name: menus_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.menus_id_seq', 1, false);


--
-- Name: pages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.pages_id_seq', 1, false);


--
-- Name: posts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.posts_id_seq', 1, false);


--
-- Name: settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.settings_id_seq', 8, true);


--
-- Name: tags_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.tags_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.users_id_seq', 1, true);


--
-- Name: widgets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: cms
--

SELECT pg_catalog.setval('public.widgets_id_seq', 1, false);


--
-- PostgreSQL database dump complete
--

\unrestrict hi64xdlDKrBdPmx19WK7U6Q8fpINaaW4PFexfTca6rctZkRbSfTzw1zG9GbiqM0

