-- ============================================
-- Миграция: настройки интеграции ЮKassa + шифрование ключей Platega
-- Добавляет ключи YooKassa в fin_settings (хранение секретов — ЕНКРИПТИРОВАННОЕ, см. core/Crypto.php).
-- Существующие открытые ключи Platega НЕ трогаются — они прозрачно читаются
-- и перешифровываются при следующем сохранении настроек.
-- ============================================

INSERT INTO `fin_settings` (`setting_key`, `setting_value`) VALUES
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
ON DUPLICATE KEY UPDATE `setting_key` = `setting_key`;