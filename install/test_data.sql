-- Тестовые данные для CMS
-- Запустить после установки

-- Тестовый пользователь (если нужно)
-- INSERT INTO users (login, email, password, role) VALUES
-- ('test', 'test@localhost', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'author');

-- Тестовые посты
INSERT INTO posts (title, slug, content, excerpt, status, user_id, category_id) VALUES
('Первый пост', 'first-post', 
 '<p>Это содержимое первого поста. Добро пожаловать в вашу новую CMS!</p>
  <p>Здесь вы можете публиковать статьи, новости и другой контент.</p>',
 'Добро пожаловать в вашу новую CMS!',
 'published', 1, 1),

('Второй пост', 'second-post',
 '<p>Второй тестовый пост демонстрирует работу системы.</p>
  <p>Шаблонизатор поддерживает HTML, стили и структуру.</p>',
 'Второй тестовый пост',
 'published', 1, 2),

('Черновик', 'draft-post',
 '<p>Этот пост не виден на сайте - он в статусе черновика.</p>',
 'Черновик',
 'draft', 1, 1);

-- Теги
INSERT INTO tags (name, slug) VALUES
('CMS', 'cms'),
('Тест', 'test'),
('Новости', 'news');

-- Связь постов и тегов
INSERT INTO post_tags (post_id, tag_id) VALUES
(1, 1), (1, 2),
(2, 1), (2, 3);

-- Комментарии
INSERT INTO comments (post_id, author_name, author_email, content, status) VALUES
(1, 'Иван', 'ivan@test.com', 'Отличная статья!', 'approved'),
(1, 'Петр', 'petr@test.com', 'Спасибо за информацию', 'approved'),
(2, 'Анна', 'anna@test.com', 'Жду продолжения!', 'approved');

-- Тестовая страница
INSERT INTO pages (title, slug, content, template) VALUES
('О нас', 'about', 
 '<p>Это страница "О нас". Здесь вы можете рассказать о вашем проекте.</p>
  <p>Наша CMS создана с любовью и вниманием к деталям.</p>',
 'default'),

('Контакты', 'contacts',
 '<p>Свяжитесь с нами:</p>
  <ul>
    <li>Email: info@mysite.com</li>
    <li>Телефон: +7 (999) 000-00-00</li>
  </ul>',
 'default');
