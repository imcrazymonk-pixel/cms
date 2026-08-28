"""Временный экспорт транзакций FIN из SQLite в JSON (для переноса в MySQL CMS).
Запуск: python db/export_sqlite.py [путь_к_finance.db] [выходной_json]
"""
import json
import os
import sqlite3
import sys

_D = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_D, 'backups', 'fin-source', 'finance.db')
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(_D, 'sqlite_export.json')

conn = sqlite3.connect(SRC)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT id, date, type, participant, category, amount, description, created_at "
    "FROM transactions ORDER BY date ASC, id ASC"
).fetchall()
conn.close()

data = [dict(r) for r in rows]
with open(DST, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

print(f"Экспортировано {len(data)} записей -> {DST}")
