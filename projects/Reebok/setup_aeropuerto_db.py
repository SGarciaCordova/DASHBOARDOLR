import sqlite3
import os

# Path to the database
# Assumes this script is in projects/Reebok/
# DB is in data/wms_data.db (3 levels up)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "wms_data.db")

def setup_db():
    print(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. wms_aeropuerto_raw
    # Table for active orders (Airport Mode - Active/Delays/Etc)
    print("Creating table wms_aeropuerto_raw...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wms_aeropuerto_raw (
            docto_id TEXT,
            referencia TEXT,
            fecha TEXT,
            cliente TEXT,
            cantidad_pedida INTEGER,
            cantidad_surtida INTEGER,
            tarimas INTEGER,
            tasa_de_cumplimiento REAL,
            UNIQUE(docto_id, fecha)
        )
    """)

    # 2. inbound_scord_despachados_raw
    # Table for shipped/dispatched orders (Recent Departures)
    print("Creating table inbound_scord_despachados_raw...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inbound_scord_despachados_raw (
            docto_id TEXT PRIMARY KEY,
            referencia TEXT,
            fecha TEXT,
            cliente TEXT,
            cantidad_pedida INTEGER,
            cantidad_surtida INTEGER,
            tarimas INTEGER,
            estado TEXT
        )
    """)

    # 3. View wms_aeropuerto
    # Separates date and time
    print("Creating view wms_aeropuerto...")
    cursor.execute("DROP VIEW IF EXISTS wms_aeropuerto")
    cursor.execute("""
        CREATE VIEW wms_aeropuerto AS
        SELECT
            docto_id,
            referencia,
            DATE(fecha) AS fecha,
            TIME(fecha) AS hora,
            cliente,
            cantidad_pedida,
            cantidad_surtida,
            tarimas,
            tasa_de_cumplimiento
        FROM wms_aeropuerto_raw
        WHERE referencia NOT LIKE 'INV%'
    """)

    conn.commit()
    conn.close()
    print("Database setup complete.")

if __name__ == "__main__":
    setup_db()
