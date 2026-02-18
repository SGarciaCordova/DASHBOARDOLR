import sqlite3
import csv
import io
import os

# Mock DB Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjust strictly to where I am running this: project root or projects/Reebok?
# I will run this in "c:\Users\Usuario1\Desktop\Antigravity SGC\projects\Reebok"
DB_PATH = "../../data/wms_data.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_surtido_csv():
    try:
        conn = get_db()
        cursor = conn.cursor()
        print("Connected to DB.")
        
        # Fetch comprehensive data for the report
        cursor.execute("""
            SELECT docto_id, referencia, fecha, hora, cantidad_pedida, cantidad_surtida, tarimas, estado, fill_rate
            FROM surtido ORDER BY rowid DESC
        """)
        rows = cursor.fetchall()
        print(f"Fetched {len(rows)} rows.")
        
        # Get headers
        if cursor.description:
            headers = [description[0] for description in cursor.description]
        else:
            headers = ["docto_id", "referencia", "fecha", "hora", "cantidad_pedida", "cantidad_surtida", "tarimas", "estado", "fill_rate"]

        conn.close()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        # Convert rows explicitly to check if that's the issue
        # writer.writerows(rows) 
        # Better:
        writer.writerows([tuple(r) for r in rows])
        
        val = output.getvalue()
        print(f"CSV generated. Length: {len(val)}")
        return val
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    print("Testing get_surtido_csv...")
    csv_str = get_surtido_csv()
    if csv_str:
        print("Success.")
        # print("Preview:", csv_str[:100])
    else:
        print("Failed.")
