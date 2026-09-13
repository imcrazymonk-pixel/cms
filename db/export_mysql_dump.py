#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт таблиц локальной MySQL в SQL-файл для импорта на хостинг.

По умолчанию — только финансовые таблицы (fin_transactions, fin_settings).
Для полной БД: python db/export_mysql_dump.py --all
"""
import argparse
import io
import os
import sys
from datetime import date, datetime
from decimal import Decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pymysql

DB_HOST = '127.127.126.26'
DB_NAME = 'cms'
DB_USER = 'root'
DB_PASS = ''
DEFAULT_TABLES = ['fin_transactions', 'fin_settings']


def sql_str(v):
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return "'" + v.strftime('%Y-%m-%d %H:%M:%S') + "'"
    s = pymysql.converters.escape_string(str(v))
    return "'" + s + "'"


def dump_table(cur, out, table):
    # DROP + CREATE (точная схема из БД)
    cur.execute("DROP TABLE IF EXISTS `%s`" % table)
    out.write("DROP TABLE IF EXISTS `%s`;\n" % table)
    cur.execute("SHOW CREATE TABLE `%s`" % table)
    create = cur.fetchone()[1]
    out.write(create.rstrip() + ";\n\n")

    # INSERT-ы
    cur.execute("SELECT * FROM `%s`" % table)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if not rows:
        out.write("-- (таблица пуста)\n\n")
        return
    col_list = ", ".join("`%s`" % c for c in cols)
    out.write("INSERT INTO `%s` (%s) VALUES\n" % (table, col_list))
    for i, r in enumerate(rows):
        vals = ", ".join(sql_str(v) for v in r)
        out.write("(%s)%s\n" % (vals, ';' if i == len(rows) - 1 else ','))
    out.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true', help='экспортировать ВСЕ таблицы БД')
    ap.add_argument('--out', default=None, help='выходной файл')
    args = ap.parse_args()

    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS,
                           database=DB_NAME, charset='utf8mb4', autocommit=True)
    cur = conn.cursor()

    if args.all:
        cur.execute("SHOW TABLES")
        tables = [r[0] for r in cur.fetchall()]
        default_out = os.path.join('db', 'backups', 'cms_full_dump.sql')
    else:
        tables = DEFAULT_TABLES
        default_out = os.path.join('db', 'backups', 'finance_data.sql')

    out_path = args.out or default_out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as out:
        out.write("-- Дамп локальной БД (CMS)\n-- Таблицы: %s\n-- Дата: %s\n\n"
                  % (', '.join(tables), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        out.write("SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS = 0;\n\n")
        for t in tables:
            try:
                dump_table(cur, out, t)
            except Exception as e:
                print(f'  [!] таблица {t}: {e}')
        out.write("SET FOREIGN_KEY_CHECKS = 1;\n")

    conn.close()

    size = os.path.getsize(out_path) / 1024
    print(f'Готово: {out_path}  ({size:.1f} KB, таблиц: {len(tables)})')


if __name__ == '__main__':
    main()
