
import sqlite3
import os

DB_PATH = r"c:\Users\Usuario1\Desktop\Antigravity SGC\data\wms_data.db"

if not os.path.exists(DB_PATH):
    print(f"ERROR: DB not found at {DB_PATH}")
else:
    print(f"DB found at {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"Tables: {tables}")
        
        if ('entradas',) in tables:
            count = cursor.execute("SELECT count(*) FROM entradas").fetchone()[0]
            print(f"Rows in 'entradas': {count}")
            
        if ('surtido',) in tables:
            count = cursor.execute("SELECT count(*) FROM surtido").fetchone()[0]
            print(f"Rows in 'surtido': {count}")
            
            # Check for fill_rate column
            cols = [d[0] for d in cursor.execute("SELECT * FROM surtido LIMIT 1").description]
            print(f"Columns in 'surtido': {cols}")
            
            # Check a sample row
            sample = cursor.execute("SELECT * FROM surtido LIMIT 1").fetchone()
            print(f"Sample row: {sample}")
            
        conn.close()
    except Exception as e:
        print(f"Error reading DB: {e}")
