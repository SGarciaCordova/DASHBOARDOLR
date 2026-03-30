import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import sys

# Cargar .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SQLITE_DB_PATH = r"c:\Users\Usuario1\Desktop\Antigravity SGC\data\wms_data.db"

if not DATABASE_URL or "[TU-PASSWORD]" in DATABASE_URL:
    print("❌ ERROR: No has configurado la DATABASE_URL de Supabase en el archivo .env")
    sys.exit(1)

if not os.path.exists(SQLITE_DB_PATH):
    print(f"❌ ERROR: No se encontró la base de datos local en {SQLITE_DB_PATH}")
    sys.exit(1)

def migrate_tables():
    print(f"🔗 Conectando a Supabase...")
    try:
        # Usar postgresql:// para SQLAlchemy con psycopg2-binary
        engine = create_engine(DATABASE_URL)
        
        # Conectar a SQLite
        conn_sqlite = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn_sqlite.cursor()
        
        # Obtener todas las tablas existentes en el SQLite
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        available_tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Tablas encontradas en SQLite: {available_tables}")
        
        # Tablas que queremos migrar si existen
        tables_to_migrate = [t for t in ['entradas', 'surtido', 'surtido_raw', 'wms_aeropuerto_raw', 'inbound_scord_despachados_raw'] if t in available_tables]
        
        if not tables_to_migrate:
            print("⚠️ No hay tablas relevantes para migrar.")
            return

        for table in tables_to_migrate:
            print(f"\n🔄 Migrando tabla: {table}...")
            try:
                # Leer datos de SQLite
                df = pd.read_sql_query(f"SELECT * FROM {table}", conn_sqlite)
                
                if df.empty:
                    print(f"ℹ️ La tabla {table} está vacía. Saltando...")
                    continue
                
                print(f"   - Filas encontradas: {len(df)}")
                
                # Subir a Supabase
                # index=False para no subir el índice de pandas como columna
                # if_exists='replace' para crear la tabla o sobrescribirla con el esquema correcto
                df.to_sql(table, engine, if_exists='replace', index=False)
                print(f"✅ Tabla {table} migrada correctamente.")
                
            except Exception as e:
                print(f"❌ ERROR en tabla {table}: {e}")
        
        conn_sqlite.close()
        print("\n🎉 ¡Fase 2 completada con éxito!")

    except Exception as e:
        print(f"❌ ERROR general durante la migración: {e}")

if __name__ == "__main__":
    migrate_tables()
