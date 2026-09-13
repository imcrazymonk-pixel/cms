#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Восстановление финансовых таблиц (fin_transactions, fin_settings) локальной CMS
из резервных копий после их пропажи из MySQL.

Источники:
  - db/backups/fin_transactions_after_import_20260828_011746.json  (178 строк после миграции)
  - db/backups/fin-source/platega_export.csv                        (все CONFIRMED платежи Platega)
"""
import csv
import json
import sys
import io
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pymysql

DB_HOST = '127.127.126.26'
DB_NAME = 'cms'
DB_USER = 'root'
DB_PASS = ''
JSON = r'db/backups/fin_transactions_after_import_20260828_011746.json'
CSV = r'db/backups/fin-source/platega_export.csv'

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


def main():
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS,
                           database=DB_NAME, charset='utf8mb4', autocommit=True)
    cur = conn.cursor()

    # 1) Создаём таблицы (миграции)
    for m in [r'db/migrations/2026-08-27-finance.sql', r'db/migrations/2026-08-28-finance-record-id.sql']:
        with open(m, encoding='utf-8') as f:
            sql = f.read()
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)
    print('Таблицы созданы (миграции применены).')

    # 2) fin_settings
    cur.execute("DELETE FROM fin_settings")
    for k, v in SETTINGS:
        cur.execute("INSERT INTO fin_settings (setting_key, setting_value) VALUES (%s, %s)", (k, v))
    print('fin_settings: %d строк' % len(SETTINGS))

    # 3) fin_transactions: не-Platega из JSON
    rows = json.load(open(JSON, encoding='utf-8'))
    non_platega = [r for r in rows if r[4] != 'Platega пополнение']
    cur.execute("DELETE FROM fin_transactions")
    for r in non_platega:
        rid, date, typ, cat, part, amt, desc, created = r
        if created:
            cur.execute(
                "INSERT INTO fin_transactions (id, date, type, category, participant, amount, description, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (rid, date, typ, cat, part or None, Decimal(str(amt)), desc, created[:19]))
        else:
            cur.execute(
                "INSERT INTO fin_transactions (id, date, type, category, participant, amount, description) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (rid, date, typ, cat, part or None, Decimal(str(amt)), desc))
    print('Не-Platega строк восстановлено: %d' % len(non_platega))

    # 4) Platega из CSV (полный набор CONFIRMED)
    with open(CSV, encoding='utf-8-sig') as f:
        crows = list(csv.DictReader(f, delimiter=';'))
    confirmed = [r for r in crows if r.get('Status') == 'CONFIRMED' and r.get('RecordId')]
    inserted = 0
    for r in confirmed:
        created = (r.get('CreatedAt') or '')[:19]
        if not created:
            continue
        gross = abs(Decimal(r.get('Amount') or 0))
        net = (gross * Decimal('0.9')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        desc = 'Пополнение на %d ₽' % int(gross)
        cur.execute(
            "INSERT INTO fin_transactions (date, type, category, participant, amount, description, record_id, created_at) "
            "VALUES (%s, 'income', 'Прибыль', 'Platega пополнение', %s, %s, %s, %s)",
            (created[:10], net, desc, r.get('RecordId'), created))
        inserted += 1
    print('Platega строк восстановлено: %d' % inserted)

    # 5) Проверка
    cur.execute("SELECT COUNT(*), COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END),0), "
                "COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),0) FROM fin_transactions")
    total, inc, exp = cur.fetchone()
    print('\nИтого: %d строк | доход: %s | расход: %s' % (total, inc, exp))
    cur.execute("SELECT COUNT(*), COUNT(record_id) FROM fin_transactions WHERE participant='Platega пополнение'")
    print('Platega строк / с record_id:', cur.fetchone())
    cur.execute("SELECT COUNT(*) FROM (SELECT record_id FROM fin_transactions WHERE record_id IS NOT NULL GROUP BY record_id HAVING COUNT(*)>1) x")
    print('Дубли record_id (0 = ок):', cur.fetchone()[0])
    conn.close()


if __name__ == '__main__':
    main()
