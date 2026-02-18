
import sqlite3
import os

OUT_FILE = "debug_output_clean.txt"

with open(OUT_FILE, "w", encoding="utf-8") as f:
    try:
        DB_PATH = r"c:\Users\Usuario1\Desktop\Antigravity SGC\data\wms_data.db"
        DOWNLOADS_DIR = r"c:\Users\Usuario1\Desktop\Antigravity SGC\projects\Reebok\downloads"

        f.write(f"Checking DOWNLOADS_DIR: {DOWNLOADS_DIR}\n")
        if os.path.exists(DOWNLOADS_DIR):
            files = [file for file in os.listdir(DOWNLOADS_DIR) if file.startswith("OUTBOUND")]
            f.write(f"Found {len(files)} OUTBOUND files: {files}\n")
        else:
            f.write("DOWNLOADS_DIR not found!\n")

        if not os.path.exists(DB_PATH):
            f.write(f"ERROR: DB not found at {DB_PATH}\n")
        else:
            f.write(f"DB found at {DB_PATH}\n")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            tables = [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            f.write(f"Tables: {tables}\n")
            
            if 'surtido' in tables:
                count = cursor.execute("SELECT count(*) FROM surtido").fetchone()[0]
                f.write(f"Total Rows in 'surtido': {count}\n")
                
                # Check for recent records (DO_TR...)
                do_tr_count = cursor.execute("SELECT count(*) FROM surtido WHERE docto_id LIKE 'DO_TR%'").fetchone()[0]
                f.write(f"Rows with 'DO_TR%' ID in 'surtido': {do_tr_count}\n")
                
                # Show a DO_TR sample
                sample = cursor.execute("SELECT * FROM surtido WHERE docto_id LIKE 'DO_TR%' LIMIT 1").fetchone()
                if sample:
                    f.write(f"Sample DO_TR row: {sample}\n")
                else:
                    f.write("No DO_TR rows found.\n")
                    
                # Show columns
                cols = [d[0] for d in cursor.execute("SELECT * FROM surtido LIMIT 1").description]
                f.write(f"Columns: {cols}\n")

            conn.close()
    except Exception as e:
        f.write(f"Error reading DB: {e}\n")

print(f"Written debug info to {OUT_FILE}")
