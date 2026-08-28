#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Бэкафилл record_id (уникальный идентификатор платежа Platega)
для уже существующих транзакций в fin_transactions.

Источник данных: Fin/data/platega_export.csv (копия выгрузки Platega,
которую сохранял FIN при последней синхронизации).

Матчинг: по (date, net) где net = round(gross * 0.9, 2);
при нескольких кандидатах — по совпадению created_at (время платежа).

Запуск:  python db/backfill_record_ids.py   [--dry-run]
"""
import argparse
import csv
import sys
import io
from collections import defaultdict
from decimal import Decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pymysql

ROOT = 'db'
DB_HOST = '127.127.126.26'
DB_NAME = 'cms'
DB_USER = 'root'
DB_PASS = ''
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups', 'fin-source', 'platega_export.csv')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='показать план без записи')
    args = ap.parse_args()

    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS,
                           database=DB_NAME, charset='utf8mb4', autocommit=True)
    cur = conn.cursor()

    # --- CSV Platega ---
    confirmed = []
    with open(CSV_PATH, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for r in reader:
            if r.get('Status') == 'CONFIRMED':
                rid = (r.get('RecordId') or '').strip()
                created = (r.get('CreatedAt') or '').strip()[:19]
                gross = float(r.get('Amount') or 0)
                if rid and created:
                    confirmed.append({
                        'record_id': rid,
                        'created_at': created,
                        'date': created[:10],
                        'net': round(gross * 0.9, 2),
                    })
    confirmed.sort(key=lambda r: r['created_at'])
    print(f'CONFIRMED строк из CSV: {len(confirmed)}')

    # --- DB: кандидаты ---
    cur.execute("SELECT id, date, amount, created_at, record_id FROM fin_transactions WHERE participant='Platega пополнение' ORDER BY date, id")
    db_rows = cur.fetchall()
    print(f'Platega-строк в БД: {len(db_rows)}')

    db_by_key = defaultdict(list)
    for rid, date, amount, created, rec in db_rows:
        if rec:
            continue  # уже имеет record_id
        db_by_key[(str(date), float(amount))].append({
            'id': rid, 'created_at': created, 'used': False,
        })

    # --- Матчинг ---
    def _parse_dt(s):
        from datetime import datetime
        try:
            return datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return datetime(1970, 1, 1)

    updated = 0
    skipped_csv = 0   # строки CSV без кандидата в БД
    for c in confirmed:
        key = (c['date'], c['net'])
        cands = [x for x in db_by_key.get(key, []) if not x['used']]
        if not cands:
            skipped_csv += 1
            continue
        target = _parse_dt(c['created_at'])
        exact = [x for x in cands if x['created_at'] is not None and x['created_at'] == target]
        best = exact[0] if exact else min(
            cands,
            key=lambda x: abs((x['created_at'] - target).total_seconds()) if x['created_at'] else 1e18
        )
        best['used'] = True
        if not args.dry_run:
            cur.execute("UPDATE fin_transactions SET record_id=%s WHERE id=%s", (c['record_id'], best['id']))
        updated += 1

    cur.execute("SELECT COUNT(*) FROM fin_transactions WHERE participant='Platega пополнение' AND (record_id IS NULL OR record_id='')")
    unmatched_db = cur.fetchone()[0]
    conn.close()

    print(f'Обновлено record_id: {updated}')
    print(f'Строк CSV без кандидата в БД: {skipped_csv}')
    print(f'Осталось в БД без record_id: {unmatched_db}')
    if args.dry_run:
        print('(--dry-run: запись не производилась)')


if __name__ == '__main__':
    main()
