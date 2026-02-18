
import sqlite3
import os

DB_PATH = "/app/data/wms_data.db"

if not os.path.exists(DB_PATH):
    print(f"❌ DATABASE FILE NOT FOUND AT: {DB_PATH}")
    # List dir to see what is there
    print(f"Contents of /app/data: {os.listdir('/app/data')}")
else:
    print(f"✅ Database found at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]
        print(f"📊 Tables found ({len(tables)}):")
        for t in table_names:
            print(f"- {t}")
            
        if 'entradas' in table_names:
            print("✅ Table 'entradas' exists.")
        else:
            print("❌ Table 'entradas' MISSING.")
            
        conn.close()
    except Exception as e:
        print(f"❌ Error reading database: {e}")
