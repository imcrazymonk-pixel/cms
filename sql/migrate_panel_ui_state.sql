-- ============================================
-- SQL Migration: Перенос настроек вида панели
-- в единый JSON-блоб panel_ui_state (Variant C)
-- ============================================
-- Запускать на хостинге один раз.
-- Пример:
--   mysql -h your_host -u your_user -p your_db < sql/migrate_panel_ui_state.sql
-- ============================================

-- Собираем существующие настройки каждого пользователя в JSON-строку
-- и записываем в panel_ui_state (если ещё нет такой записи).
-- Если у пользователя не было настроек — создаётся с дефолтами.
-- Используем CONCAT для совместимости с MySQL 5.7+ (JSON_OBJECT необязателен).

INSERT INTO user_preferences (user_id, pref_key, pref_value)
SELECT
  u.id,
  'panel_ui_state',
  CONCAT(
    '{"theme":"', COALESCE(p.theme, 'obsidian'), '","mode":"', COALESCE(p.mode, 'dark'),
    '","density":"', COALESCE(p.density, 'comfortable'), '","radius":"', COALESCE(p.radius, 'default'),
    '","fontSize":"', COALESCE(p.fontSize, 'default'),
    '","animations":', CASE WHEN p.animations IS NULL OR p.animations = '' OR p.animations = 'true' THEN 'true' ELSE 'false' END,
    ',"sidebarCollapsed":false}'
  )
FROM users u
LEFT JOIN (
  SELECT
    user_id,
    MAX(CASE WHEN pref_key = 'theme' THEN pref_value END) AS theme,
    MAX(CASE WHEN pref_key = 'mode' THEN pref_value END) AS mode,
    MAX(CASE WHEN pref_key = 'density' THEN pref_value END) AS density,
    MAX(CASE WHEN pref_key = 'radius' THEN pref_value END) AS radius,
    MAX(CASE WHEN pref_key = 'fontSize' THEN pref_value END) AS fontSize,
    MAX(CASE WHEN pref_key = 'animations' THEN pref_value END) AS animations
  FROM user_preferences
  WHERE pref_key IN ('theme', 'mode', 'density', 'radius', 'fontSize', 'animations')
  GROUP BY user_id
) p ON u.id = p.user_id
WHERE NOT EXISTS (
  SELECT 1 FROM user_preferences up
  WHERE up.user_id = u.id AND up.pref_key = 'panel_ui_state'
);

-- ============================================
-- ВАЖНО: Старые ключи (theme, mode, density, radius, fontSize)
-- остаются в таблице для обратной совместимости со старым
-- эндпоинтом save-preference. Новый код читает только panel_ui_state.
-- Если старые записи мешают — их можно удалить позже:
--   DELETE FROM user_preferences WHERE pref_key IN ('theme','mode','density','radius','fontSize','animations');
-- Но рекомендую оставить до полной проверки.
-- ============================================