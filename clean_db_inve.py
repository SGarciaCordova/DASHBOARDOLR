import sqlite3
import os

BASE_DIR = r"c:\Users\Usuario1\Desktop\Antigravity SGC"
DB_PATH = os.path.join(BASE_DIR, "data", "wms_data.db")

conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM entradas WHERE docto_id LIKE 'INVE-%'")
conn.commit()
conn.close()

# Force dashboard refresh via file modification time
if os.path.exists(DB_PATH):
    os.utime(DB_PATH, None)
    
print("Base de datos limpia y dashboard notificado.")
