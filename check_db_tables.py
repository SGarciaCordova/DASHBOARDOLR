
import sqlite3
import os

DB_PATH = r"c:\Users\Usuario1\Desktop\Antigravity SGC\data\wms_data.db"

if not os.path.exists(DB_PATH):
    print(f"DATABASE FILE NOT FOUND AT: {DB_PATH}")
else:
    print(f"Database found at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables found:")
        for t in tables:
            print(f"- {t[0]}")
        conn.close()
    except Exception as e:
        print(f"Error reading database: {e}")
