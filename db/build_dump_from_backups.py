#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Формирование SQL-дампа финансовых таблиц (fin_transactions, fin_settings)
НЕПОСРЕДСТВЕННО из резервных копий — без обращения к локальной MySQL.

Источники:
  - db/backups/fin_transactions_after_import_20260828_011746.json  (72 не-Platega строки)
  - db/backups/fin-source/platega_export.csv                        (115 CONFIRMED платежей Platega)

Результат: db/backups/finance_data.sql — готов к импорту в phpMyAdmin на хостинге.
"""
import csv
import json
import os
import sys
import io
from decimal import Decimal, ROUND_HALF_UP

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

JSON = r'db/backups/fin_transactions_after_import_20260828_011746.json'
CSV = r'db/backups/fin-source/platega_export.csv'
OUT = r'db/backups/finance_data.sql'

SETTINGS = [
    ('currency', '₽'), ('decimals', '2'), ('auto_refresh', '0'), ('avg_period', 'day'),
    ('avg_exclude_categories', '[]'), ('avg_exclude_income_keywords', '[]'),
    ('avg_exclude_expense_keywords', '[]'), ('quick_categories', '[]'), ('quick_participants', '[]'),
    ('platega_merchant_id', 'c66751a9-2c2e-4eba-a3f6-e7b11a777bb6'),
    ('platega_secret', 'hDB1Wew553iSBFUNBp389bVPLsXraZMhHD6bcDgPU23MXwvMULMXGec2dU5O3kndXpHmBo0Sf8Ky3dDKpRYdOStrUHr9BntG2z8V'),
    ('platega_days_back', '150'), ('platega_auto_sync', '1'),
    ('platega_last_sync', '2026-08-28T02:27:19+03:00'),
    ('platega_cron_token', '576126c9050ebd6fb1d89026edc4922c1eb1cdf7c8da4312'),
]

CREATE_TX = """CREATE TABLE IF NOT EXISTS `fin_transactions` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `date` DATE NOT NULL,
  `type` ENUM('income','expense') NOT NULL,
  `category` VARCHAR(100) NOT NULL,
  `participant` VARCHAR(100) DEFAULT NULL,
  `amount` DECIMAL(15,2) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `record_id` VARCHAR(64) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_date` (`date`),
  INDEX `idx_type` (`type`),
  INDEX `idx_category` (`category`),
  INDEX `idx_participant` (`participant`),
  INDEX `idx_date_type` (`date`, `type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"""

CREATE_ST = """CREATE TABLE IF NOT EXISTS `fin_settings` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `setting_key` VARCHAR(100) NOT NULL UNIQUE,
  `setting_value` TEXT DEFAULT NULL,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_key` (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"""


def q(v):
    if v is None:
        return 'NULL'
    if isinstance(v, Decimal):
        return str(v)
    s = str(v).replace('\\', '\\\\').replace("'", "''")
    return "'" + s + "'"


def build():
    out = []
    out.append("-- Дамп финансовых таблиц (сформирован из резервных копий)")
    out.append("-- Дата формирования: (из бэкапов)")
    out.append("SET NAMES utf8mb4;")
    out.append("SET FOREIGN_KEY_CHECKS = 0;")
    out.append("")
    out.append("-- ============ fin_transactions ============")
    out.append("DROP TABLE IF EXISTS `fin_transactions`;")
    out.append(CREATE_TX)
    out.append("")

    # Собираем строки
    rows = json.load(open(JSON, encoding='utf-8'))
    non_platega = [r for r in rows if r[4] != 'Platega пополнение']

    with open(CSV, encoding='utf-8-sig') as f:
        crows = [r for r in csv.DictReader(f, delimiter=';')
                 if r.get('Status') == 'CONFIRMED' and r.get('RecordId') and (r.get('CreatedAt') or '')[:19]]

    # Вывод: сначала не-Platega (с исходными id), затем Platega (авто-id)
    inserts = []
    # не-Platega
    for r in non_platega:
        rid, date, typ, cat, part, amt, desc, created = r
        vals = [str(rid), q(date), q(typ), q(cat), q(part or None), q(Decimal(str(amt))),
                q(desc or None), 'NULL', q((created or '')[:19] or None)]
        inserts.append("(%s)" % ", ".join(vals))
    n1 = len(inserts)
    # Platega из CSV
    for r in crows:
        created = (r.get('CreatedAt') or '')[:19]
        gross = abs(Decimal(r.get('Amount') or 0))
        net = (gross * Decimal('0.9')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        desc = 'Пополнение на %d ₽' % int(gross)
        vals = ["NULL", q(created[:10]), q('income'), q('Прибыль'), q('Platega пополнение'),
                q(net), q(desc), q(r.get('RecordId')), q(created)]
        inserts.append("(%s)" % ", ".join(vals))
    n2 = len(inserts) - n1

    out.append("INSERT INTO `fin_transactions` (`id`, `date`, `type`, `category`, `participant`, `amount`, `description`, `record_id`, `created_at`) VALUES")
    for i, ins in enumerate(inserts):
        out.append(ins + ('' if i == len(inserts) - 1 else ','))
    out.append("")
    out.append("-- ============ fin_settings ============")
    out.append("DROP TABLE IF EXISTS `fin_settings`;")
    out.append(CREATE_ST)
    out.append("")
    out.append("INSERT INTO `fin_settings` (`setting_key`, `setting_value`) VALUES")
    for i, (k, v) in enumerate(SETTINGS):
        out.append("(%s, %s)%s" % (q(k), q(v), '' if i == len(SETTINGS) - 1 else ','))
    out.append("")
    out.append("SET FOREIGN_KEY_CHECKS = 1;")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write("\n".join(out))

    print('Готово: %s' % OUT)
    print('  строк fin_transactions: %d (не-Platega: %d, Platega: %d)' % (len(inserts), n1, n2))
    print('  строк fin_settings: %d' % len(SETTINGS))


if __name__ == '__main__':
    build()
