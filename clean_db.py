import sqlite3
import os

DB_PATH = "data/wms_data.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("--- CLEANING UP INV REFERENCES ---")
cursor.execute("DELETE FROM wms_aeropuerto_raw WHERE referencia LIKE 'INV%'")
deleted_raw = cursor.rowcount
print(f"Deleted {deleted_raw} rows from wms_aeropuerto_raw")

cursor.execute("DELETE FROM inbound_scord_despachados_raw WHERE referencia LIKE 'INV%'")
deleted_shipped = cursor.rowcount
print(f"Deleted {deleted_shipped} rows from inbound_scord_despachados_raw")

conn.commit()

print("\n--- VERIFYING ---")
cursor.execute("SELECT count(*) FROM wms_aeropuerto_raw WHERE referencia LIKE 'INV%'")
count_raw = cursor.fetchone()[0]
print(f"Remaining INV rows in wms_aeropuerto_raw: {count_raw}")

cursor.execute("SELECT count(*) FROM inbound_scord_despachados_raw WHERE referencia LIKE 'INV%'")
count_shipped = cursor.fetchone()[0]
print(f"Remaining INV rows in inbound_scord_despachados_raw: {count_shipped}")

conn.close()
