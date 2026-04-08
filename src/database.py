import sqlite3
import pandas as pd
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

DB_NAME = 'sgc_system.db'

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db():
    """Initializes the database table structure if it doesn't exist."""
    conn = get_connection()
    c = conn.cursor()
    
    # We will store data as JSON text or just rely on pandas to create tables dynamically
    # For flexibility in this prototype phase, letting pandas handle table creation
    # via to_sql is often safer and easier when columns might change in the Sheet.
    # However, creating a metadata table is good practice.
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_dataframe_to_db(df, table_name):
    """Saves a pandas DataFrame to SQLite, replacing existing table."""
    conn = get_connection()
    try:
        # if_exists='replace' drops the table and recreates it. 
        # Ideally we would do incremental, but for this size (Sheets), full replace is safer to ensure sync.
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Update timestamp
        c = conn.cursor()
        from datetime import datetime
        c.execute("INSERT OR REPLACE INTO metadata (key, value, updated_at) VALUES (?, ?, ?)", 
                  (f"{table_name}_last_sync", datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving {table_name}: {e}")
        return False
    finally:
        conn.close()

def load_dataframe_from_db(table_name):
    """Loads a table from SQLite into a DataFrame."""
    conn = get_connection()
    try:
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        # Table might not exist yet
        print(f"Error loading {table_name}: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_last_sync_time(table_name="entradas"):
    """Returns the last sync timestamp string or None."""
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT value FROM metadata WHERE key = ?", (f"{table_name}_last_sync",))
        result = c.fetchone()
        return result[0] if result else None
    except:
        return None
    finally:
        conn.close()

def get_supabase_engine():
    """Returns an SQLAlchemy engine for Supabase."""
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    return create_engine(db_url, connect_args={"connect_timeout": 10})

def log_activity(user_email, event_type, detail, status="OK", ip=None):
    """
    Centralized function to log activity to Supabase audit_logs table.
    event_type values: LOGIN, LOGOUT, SCRAPER_RUN, SCRAPER_ERROR, SYNC, PERMISSION_CHANGE, EXPORT
    """
    engine = get_supabase_engine()
    if not engine:
        print("❌ Skip activity log: DATABASE_URL not set")
        return False
    
    try:
        with engine.connect() as conn:
            sql = text("""
                INSERT INTO audit_logs (user_email, event_type, detail, status, ip_address)
                VALUES (:email, :type, :detail, :status, :ip)
            """)
            conn.execute(sql, {
                "email": user_email,
                "type": event_type,
                "detail": detail,
                "status": status,
                "ip": ip
            })
            conn.commit()
            return True
    except Exception as e:
        print(f"[ERROR] Error logging activity: {e}")
        return False


def upsert_desempeno_csv(df_csv, progress_callback=None):
    """
    Inserts new operator performance records from a CSV DataFrame into Desempeno_Op_.
    Uses batch INSERT ... ON CONFLICT DO NOTHING to skip duplicates automatically.
    
    Args:
        df_csv: DataFrame from the uploaded CSV.
        progress_callback: Optional callable(batch_num, total_batches) for UI progress.
    
    Returns dict: {total_csv, inserted, duplicates, errors, error_msg}
    """
    BATCH_SIZE = 5000

    engine = get_supabase_engine()
    if not engine:
        return {"total_csv": 0, "inserted": 0, "duplicates": 0, "errors": 1, "error_msg": "DATABASE_URL no configurado"}
    

    # --- Column Mapping (flexible, case-insensitive) ---
    col_map = {}
    target_cols = {
        'transaccion': ['transaccion', 'transaction', 'tipo'],
        'detalle': ['detalle', 'detail', 'descripcion_transaccion'],
        'usuario': ['usuario', 'user', 'operador', 'user_name'],
        'fecha': ['fecha', 'date', 'fecha_hora', 'datetime', 'timestamp'],
        'referencia': ['referencia', 'reference', 'pedido', 'order'],
        'sku': ['sku', 'codigo', 'product_code', 'item'],
        'cantidad': ['cantidad', 'quantity', 'qty', 'piezas'],
    }
    
    csv_cols_lower = {c.lower().strip(): c for c in df_csv.columns}
    
    for db_col, aliases in target_cols.items():
        for alias in aliases:
            if alias in csv_cols_lower:
                col_map[db_col] = csv_cols_lower[alias]
                break
    
    # Validate required columns found
    required = ['transaccion', 'usuario', 'fecha', 'sku', 'referencia', 'cantidad']
    missing = [r for r in required if r not in col_map]
    if missing:
        return {
            "total_csv": len(df_csv), "inserted": 0, "duplicates": 0, "errors": 1,
            "error_msg": f"Columnas faltantes en CSV: {missing}. Columnas encontradas: {list(df_csv.columns)}"
        }
    
    # --- Build clean DataFrame ---
    df_clean = pd.DataFrame()
    for db_col, csv_col in col_map.items():
        df_clean[db_col] = df_csv[csv_col]
    
    # Parse fecha to timestamp — handle DD/MM/YYYY vs MM/DD/YYYY ambiguity
    from datetime import datetime as dt_cls, timezone
    import numpy as np
    
    df_clean['fecha'] = pd.to_datetime(df_clean['fecha'], dayfirst=True, errors='coerce')
    now_utc = pd.Timestamp.now(tz='UTC').tz_localize(None)
    future_threshold = now_utc + pd.Timedelta(days=7)
    
    # Check if dayfirst=True produced suspicious future dates (month/day swap symptom)
    valid_dates = df_clean['fecha'].dropna()
    if len(valid_dates) > 0 and (valid_dates > future_threshold).any():
        df_clean['fecha'] = pd.to_datetime(df_csv[col_map['fecha']], dayfirst=False, errors='coerce')
    
    df_clean = df_clean.dropna(subset=['fecha', 'usuario', 'sku'])
    
    # Filter by 'Salida por Defecto' as per user request
    if 'detalle' in df_clean.columns:
        df_clean = df_clean[df_clean['detalle'] == 'Salida por Defecto']
    
    # Clean cantidad to numeric
    df_clean['cantidad'] = pd.to_numeric(df_clean['cantidad'], errors='coerce').fillna(0)
    
    # Fill detalle if missing
    if 'detalle' not in col_map:
        df_clean['detalle'] = ''
    
    total_csv = len(df_clean)
    if total_csv == 0:
        return {"total_csv": 0, "inserted": 0, "duplicates": 0, "errors": 1, "error_msg": "CSV vacío o sin columnas válidas después del parseo"}
    
    # --- Prepare all records as list of dicts (vectorized, no iterrows) ---
    df_clean['transaccion'] = df_clean['transaccion'].astype(str)
    df_clean['detalle'] = df_clean['detalle'].astype(str)
    df_clean['usuario'] = df_clean['usuario'].astype(str)
    df_clean['referencia'] = df_clean['referencia'].astype(str)
    df_clean['sku'] = df_clean['sku'].astype(str)
    df_clean['cantidad'] = pd.to_numeric(df_clean['cantidad'], errors='coerce').fillna(0).astype(float)
    
    # Vectorized isoformat
    df_clean['fecha'] = pd.to_datetime(df_clean['fecha']).dt.strftime('%Y-%m-%dT%H:%M:%S')
    
    records = df_clean.to_dict('records')
    
    # --- BULK INSERT with ON CONFLICT DO NOTHING ---
    # Build a single INSERT ... VALUES (...), (...), ... statement
    # This is MUCH faster than executemany over a network connection
    
    inserted = 0
    total_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE
    
    try:
        with engine.connect() as conn:
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i : i + BATCH_SIZE]
                
                # Build VALUES clause with placeholders
                value_placeholders = []
                params = {}
                for j, rec in enumerate(batch):
                    ph = f"(:t{j}, :d{j}, :u{j}, :f{j}, :r{j}, :s{j}, :c{j})"
                    value_placeholders.append(ph)
                    params[f"t{j}"] = rec['transaccion']
                    params[f"d{j}"] = rec['detalle']
                    params[f"u{j}"] = rec['usuario']
                    params[f"f{j}"] = rec['fecha']
                    params[f"r{j}"] = rec['referencia']
                    params[f"s{j}"] = rec['sku']
                    params[f"c{j}"] = rec['cantidad']
                
                sql = text(f"""
                    INSERT INTO "Desempeno_Op_" (transaccion, detalle, usuario, fecha, referencia, sku, cantidad)
                    VALUES {', '.join(value_placeholders)}
                    ON CONFLICT (transaccion, usuario, fecha, sku, referencia) DO NOTHING
                """)
                result = conn.execute(sql, params)
                inserted += result.rowcount
                
                batch_num = (i // BATCH_SIZE) + 1
                if progress_callback:
                    progress_callback(batch_num, total_batches)
            
            conn.commit()
        
        duplicates = total_csv - inserted
        return {"total_csv": total_csv, "inserted": inserted, "duplicates": duplicates, "errors": 0, "error_msg": None}
    except Exception as e:
        return {"total_csv": total_csv, "inserted": inserted, "duplicates": 0, "errors": 1, "error_msg": str(e)}
