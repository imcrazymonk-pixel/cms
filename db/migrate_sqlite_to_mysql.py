#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Перенос финансовых транзакций из SQLite (Fin) в MySQL (CMS).

Запуск (Python 3.12+, требуется pymysql):
    python db/migrate_sqlite_to_mysql.py            # импорт без очистки (пропуск дубликатов)
    python db/migrate_sqlite_to_mysql.py --reset    # очистить fin_transactions перед импортом

Поведение:
  - создаёт резервную копию текущих fin_transactions в db/backups/ (JSON)
  - --reset: TRUNCATE fin_transactions
  - читает таблицу transactions из Fin/data/finance.db
  - маппит тип: 'Доход'/'Приход' -> income, 'Расход'/'Отток' -> expense
  - вставляет ВСЕ строки без потерь (в исходнике есть корректные операции
    с одинаковыми (date, type, participant, amount), но разными описаниями;
    дедупликацию при переносе не применяем)
"""
import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pymysql

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(ROOT, 'db', 'backups', 'fin-source', 'finance.db')
BACKUP_DIR = os.path.join(ROOT, 'db', 'backups')

DB_HOST = '127.127.126.26'
DB_NAME = 'cms'
DB_USER = 'root'
DB_PASS = ''
DB_CHARSET = 'utf8mb4'


def backup_table(cur):
    cur.execute("SELECT id, date, type, category, participant, amount, description, created_at FROM fin_transactions ORDER BY id")
    rows = cur.fetchall()
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(BACKUP_DIR, f'fin_transactions_backup_{stamp}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
    print(f'Резервная копия ({len(rows)} строк): {path}')
    return path


def map_type(t):
    t = (t or '').strip().lower()
    if t in ('доход', 'income', 'приход', 'плюс', 'прибыль'):
        return 'income'
    if t in ('расход', 'expense', 'отток', 'минус'):
        return 'expense'
    return ''


def parse_created_at(v):
    if not v:
        return None
    try:
        d = dt.datetime.fromisoformat(str(v).replace('Z', '+00:00'))
        return d.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reset', action='store_true', help='очистить fin_transactions перед импортом')
    args = ap.parse_args()

    if not os.path.exists(SQLITE_PATH):
        print(f'ОШИБКА: не найден источник {SQLITE_PATH}')
        sys.exit(1)

    # --- SQLite: читаем источник ---
    lite = sqlite3.connect(SQLITE_PATH)
    lite.row_factory = sqlite3.Row
    src = lite.execute(
        'SELECT date, type, participant, category, amount, description, created_at '
        'FROM transactions ORDER BY date ASC, id ASC'
    ).fetchall()
    lite.close()
    print(f'Источник FIN: {len(src)} строк')

    # --- MySQL ---
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS,
                           database=DB_NAME, charset=DB_CHARSET, autocommit=True)
    cur = conn.cursor()

    backup_path = backup_table(cur)

    if args.reset:
        cur.execute('TRUNCATE TABLE fin_transactions')
        print('fin_transactions ОЧИЩЕНА (--reset)')

    # ВАЖНО: дедупликацию НЕ применяем — в исходной базе FIN есть корректные
    # операции с одинаковыми (date, type, participant, amount), но разными
    # описаниями. Переносим все строки без потерь (как db/migrate_sqlite_to_mysql.php).

    inserted = 0
    invalid = 0
    rows = []
    for r in src:
        date = (r['date'] or '').strip()
        typ = map_type(r['type'])
        participant = (r['participant'] or '').strip()
        category = (r['category'] or '').strip() or 'Другое'
        desc = (r['description'] or '').strip()
        if desc == '-':
            desc = ''
        try:
            amount = round(float(r['amount']), 2)
        except (TypeError, ValueError):
            invalid += 1
            continue
        if not date or not typ or amount <= 0:
            invalid += 1
            continue
        try:
            dt.date.fromisoformat(date)
        except ValueError:
            invalid += 1
            continue

        created = parse_created_at(r['created_at'])
        rows.append((date, typ, category, participant or None, amount, desc, created))
        inserted += 1

    if rows:
        with_created = [r for r in rows if r[6] is not None]
        without_created = [r[:6] for r in rows if r[6] is None]
        if with_created:
            cur.executemany(
                'INSERT INTO fin_transactions (date, type, category, participant, amount, description, created_at) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                with_created
            )
        if without_created:
            # created_at NOT NULL DEFAULT CURRENT_TIMESTAMP — пропускаем колонку,
            # чтобы MySQL проставил время создания автоматически
            cur.executemany(
                'INSERT INTO fin_transactions (date, type, category, participant, amount, description) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                without_created
            )

    cur.execute('SELECT COUNT(*) FROM fin_transactions')
    total = cur.fetchone()[0]
    conn.close()

    print(f'Импортировано: {inserted}')
    print(f'Пропущено битых: {invalid}')
    print(f'Итого в fin_transactions: {total}')
    print(f'Резервная копия: {backup_path}')


if __name__ == '__main__':
    main()
