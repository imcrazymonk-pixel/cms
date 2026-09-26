-- PostgreSQL Schema for NewWeb CMS
-- Converted from MySQL. Generated: 2026-09-25

-- ============================================
-- Trigger function for updated_at columns
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================
-- Пользователи
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    login VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) CHECK (role IN ('admin', 'editor', 'author')) DEFAULT 'author',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Категории
-- ============================================
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(191) UNIQUE NOT NULL,
    description TEXT,
    parent_id INTEGER DEFAULT NULL
);

-- ============================================
-- Посты
-- ============================================
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(191) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    excerpt TEXT,
    image VARCHAR(255),
    status VARCHAR(50) CHECK (status IN ('draft', 'published', 'archived')) DEFAULT 'draft',
    views INTEGER DEFAULT 0,
    user_id INTEGER NOT NULL,
    category_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category_id);
CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);

CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Настройки сайта
-- ============================================
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT
);

-- ============================================
-- Страницы
-- ============================================
CREATE TABLE IF NOT EXISTS pages (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(191) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    meta_description VARCHAR(255) DEFAULT NULL,
    user_id INTEGER DEFAULT NULL,
    template VARCHAR(100) DEFAULT 'default',
    is_home SMALLINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pages_is_home ON pages(is_home);

-- ============================================
-- Теги
-- ============================================
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    slug VARCHAR(191) UNIQUE NOT NULL
);

-- ============================================
-- Связь постов и тегов
-- ============================================
CREATE TABLE IF NOT EXISTS post_tags (
    post_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (post_id, tag_id)
);

-- ============================================
-- Комментарии
-- ============================================
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL,
    user_id INTEGER,
    author_name VARCHAR(100),
    author_email VARCHAR(100),
    content TEXT NOT NULL,
    status VARCHAR(50) CHECK (status IN ('pending', 'approved', 'spam')) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_status ON comments(status);

-- ============================================
-- Меню
-- ============================================
CREATE TABLE IF NOT EXISTS menus (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(255) NOT NULL,
    location VARCHAR(50) DEFAULT 'main'
);

-- ============================================
-- Элементы меню
-- ============================================
CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    menu_id INTEGER NOT NULL,
    title VARCHAR(100) NOT NULL,
    url VARCHAR(255) NOT NULL,
    parent_id INTEGER DEFAULT NULL,
    "order" INTEGER DEFAULT 0
);

-- ============================================
-- Медиафайлы
-- ============================================
CREATE TABLE IF NOT EXISTS media (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL,
    alt VARCHAR(255),
    size INTEGER,
    mime_type VARCHAR(50),
    uploaded_by INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Виджеты
-- ============================================
CREATE TABLE IF NOT EXISTS widgets (
    id SERIAL PRIMARY KEY,
    area VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_widgets_area ON widgets(area);

-- ============================================
-- Финансовый модуль: транзакции
-- ============================================
CREATE TABLE IF NOT EXISTS fin_transactions (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    type VARCHAR(10) CHECK (type IN ('income', 'expense')) NOT NULL,
    category VARCHAR(100) NOT NULL,
    participant VARCHAR(100) DEFAULT NULL,
    amount DECIMAL(15,2) NOT NULL,
    description TEXT DEFAULT NULL,
    record_id VARCHAR(64) DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fin_transactions_date ON fin_transactions(date);
CREATE INDEX IF NOT EXISTS idx_fin_transactions_type ON fin_transactions(type);
CREATE INDEX IF NOT EXISTS idx_fin_transactions_category ON fin_transactions(category);
CREATE INDEX IF NOT EXISTS idx_fin_transactions_participant ON fin_transactions(participant);
CREATE INDEX IF NOT EXISTS idx_fin_transactions_date_type ON fin_transactions(date, type);
CREATE INDEX IF NOT EXISTS idx_fin_record_id ON fin_transactions(record_id);

CREATE TRIGGER update_fin_transactions_updated_at BEFORE UPDATE ON fin_transactions
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Финансовый модуль: настройки
-- ============================================
CREATE TABLE IF NOT EXISTS fin_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT DEFAULT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fin_settings_key ON fin_settings(setting_key);

CREATE TRIGGER update_fin_settings_updated_at BEFORE UPDATE ON fin_settings
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Логи приложения
-- ============================================
CREATE TABLE IF NOT EXISTS app_logs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL DEFAULT 'info',
    channel VARCHAR(50) NOT NULL DEFAULT 'system',
    message TEXT NOT NULL,
    context TEXT DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_app_logs_created_at ON app_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_app_logs_level_channel ON app_logs(level, channel);

-- ============================================
-- Пользовательские настройки панели
-- ============================================
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER NOT NULL,
    pref_key VARCHAR(50) NOT NULL,
    pref_value VARCHAR(100) NOT NULL,
    PRIMARY KEY (user_id, pref_key),
    UNIQUE (user_id, pref_key)
);

-- ============================================
-- Внешние ключи
-- ============================================

ALTER TABLE categories ADD FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL;
ALTER TABLE posts ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE posts ADD FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL;
ALTER TABLE post_tags ADD FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE;
ALTER TABLE post_tags ADD FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE;
ALTER TABLE comments ADD FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE;
ALTER TABLE comments ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE pages ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE menu_items ADD FOREIGN KEY (menu_id) REFERENCES menus(id) ON DELETE CASCADE;
ALTER TABLE menu_items ADD FOREIGN KEY (parent_id) REFERENCES menu_items(id) ON DELETE SET NULL;
ALTER TABLE media ADD FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE user_preferences ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- ============================================
-- Начальные данные
-- ============================================

-- Категории по умолчанию
INSERT INTO categories (name, slug, description) VALUES
('Новости', 'news', 'Последние новости сайта'),
('Статьи', 'articles', 'Полезные статьи');

-- Настройки по умолчанию
INSERT INTO settings (setting_key, setting_value) VALUES
('site_name', 'Моя CMS'),
('site_url', 'http://localhost'),
('admin_email', 'admin@localhost'),
('posts_per_page', '10'),
('site_description', 'Сайт на собственной CMS'),
('meta_description', ''),
('meta_keywords', ''),
('active_theme', 'default');

-- Администратор по умолчанию
INSERT INTO users (login, email, password, role) VALUES
('admin', 'admin@localhost', '$2y$10$change_this_to_a_real_bcrypt_hash', 'admin');

-- Настройки финансового модуля (Platega)
INSERT INTO fin_settings (setting_key, setting_value) VALUES
('currency', '₽'),
('decimals', '2'),
('auto_refresh', '0'),
('avg_period', 'day'),
('avg_exclude_categories', '[]'),
('avg_exclude_income_keywords', '[]'),
('avg_exclude_expense_keywords', '[]'),
('quick_categories', '[]'),
('quick_participants', '[]'),
('platega_merchant_id', ''),
('platega_secret', ''),
('platega_days_back', '150'),
('platega_auto_sync', '0'),
('platega_last_sync', ''),
('platega_last_sync_ok', '0'),
('platega_last_error', '')
ON CONFLICT (setting_key) DO NOTHING;

-- Настройки ЮKassa
INSERT INTO fin_settings (setting_key, setting_value) VALUES
('yookassa_shop_id', ''),
('yookassa_secret_key', ''),
('yookassa_days_back', '150'),
('yookassa_auto_sync', '0'),
('yookassa_commissions', '{"bank_card":3,"sbp":0.5,"yoo_money":3,"sberbank":3,"tinkoff_bank":3,"mobile":6,"cash":3,"qiwi":3}'),
('yookassa_last_sync', ''),
('yookassa_last_sync_ok', '0'),
('yookassa_last_error', ''),
('yookassa_sync_lock', ''),
('yookassa_cron_token', '')
ON CONFLICT (setting_key) DO NOTHING;