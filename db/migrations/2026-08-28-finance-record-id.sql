-- ============================================
-- Миграция: уникальный идентификатор платежа Platega
-- Добавляет колонку record_id (RecordId из Platega API —
-- уникален для КАЖДОГО платежа, в отличие от
-- (date, type, participant, amount), где participant
-- всегда 'Platega пополнение' и два платежа с одинаковой
-- датой/суммой от разных людей неразличимы).
-- ============================================

ALTER TABLE `fin_transactions`
  ADD COLUMN `record_id` VARCHAR(64) DEFAULT NULL AFTER `description`;

CREATE INDEX `idx_fin_record_id` ON `fin_transactions` (`record_id`);
