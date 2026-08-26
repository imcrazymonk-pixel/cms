-- ============================================
-- Миграция: таблица пользовательских настроек панели (тема/режим и т.д.)
-- Дата: 2026-08-26
-- Применять один раз: mysql -h 127.127.126.26 -u root cms < этот файл
-- ============================================

CREATE TABLE IF NOT EXISTS user_preferences (
  user_id INT NOT NULL,
  pref_key VARCHAR(50) NOT NULL,
  pref_value VARCHAR(100) NOT NULL,
  PRIMARY KEY (user_id, pref_key),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
