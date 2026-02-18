import sqlite3
import pandas as pd
import os

DB_PATH = r"c:\Users\Usuario1\Desktop\Antigravity SGC\data\wms_data.db"

if not os.path.exists(DB_PATH):
    print("Database not found!")
else:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM surtido WHERE referencia LIKE 'INVE%'", conn)
        print(f"Found {len(df)} records with reference starting with INVE.")
        if len(df) > 0:
            print(df[['docto_id', 'referencia']].head())
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        conn.close()
