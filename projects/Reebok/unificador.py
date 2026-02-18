import pandas as pd
import sqlite3
import glob
import os
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurations
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "data", "wms_data.db")

def clean_numeric(series):
    """Removes commas, quotes, spaces and converts to numeric."""
    if series is None:
        return 0
    return pd.to_numeric(series.astype(str).str.replace(r'[",\s]', '', regex=True), errors='coerce').fillna(0)

def clean_string(series):
    """Trims whitespace from strings."""
    return series.astype(str).str.strip()

def process_inbound():
    logging.info("Processing Inbound Files...")
    files = glob.glob(os.path.join(DOWNLOADS_DIR, "INBOUND-*.csv"))
    if not files:
        logging.warning("No Inbound files found.")
        return

    dfs = []
    for f in files:
        try:
            # Read all as string to keep initial formatting safe
            df = pd.read_csv(f, dtype=str, on_bad_lines='skip')
            dfs.append(df)
        except Exception as e:
            logging.error(f"Error reading {f}: {e}")
            
    if not dfs:
        return

    full_df = pd.concat(dfs, ignore_index=True)
    full_df.drop_duplicates(inplace=True)
    
    # Normalize Columns
    # Map CSV headers to DB columns
    # CSV: documento_id, referencia, fecha, sku:right, desc, cantidad_recibida, tarimas, calidad
    # DB: docto_id, referencia, fecha, sku, descripcion, cantidad, tarimas, calidad
    
    # Handle messy headers possibly
    full_df.columns = [c.strip() for c in full_df.columns]
    
    # Rename original 'cantidad' if exists to avoid collision
    if 'cantidad' in full_df.columns:
        full_df.rename(columns={'cantidad': 'cantidad_esperada'}, inplace=True)

    # Rename
    rename_map = {
        'documento_id': 'docto_id',
        'cantidad_recibida': 'cantidad',
        'sku:right': 'sku',
        'desc': 'descripcion',
        # fecha, referencia, tarimas, calidad usually match
    }
    full_df.rename(columns=rename_map, inplace=True)
    
    # Ensure columns exist
    required_cols = ['docto_id', 'referencia', 'fecha', 'sku', 'descripcion', 'cantidad', 'tarimas', 'calidad']
    for col in required_cols:
        if col not in full_df.columns:
            full_df[col] = ''

    # Clean Data
    full_df['cantidad'] = clean_numeric(full_df['cantidad'])
    full_df['tarimas'] = clean_numeric(full_df['tarimas'])
    full_df['docto_id'] = clean_string(full_df['docto_id'])
    full_df['sku'] = clean_string(full_df['sku'])
    full_df['calidad'] = clean_string(full_df['calidad'])
    
    # Select only relevant columns for DB
    final_df = full_df[required_cols].copy()
    
    # Save to SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        final_df.to_sql("entradas", conn, if_exists="replace", index=False)
        count = len(final_df)
        conn.close()
        logging.info(f"Successfully loaded {count} Inbound rows to 'entradas' table.")
    except Exception as e:
        logging.error(f"Database error (Inbound): {e}")

def process_outbound():
    logging.info("Processing Outbound Files...")
    files = glob.glob(os.path.join(DOWNLOADS_DIR, "OUTBOUND-*.csv"))
    if not files:
        logging.warning("No Outbound files found.")
        return

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, dtype=str, on_bad_lines='skip')
            dfs.append(df)
        except Exception as e:
            logging.error(f"Error reading {f}: {e}")

    if not dfs:
        return

    full_df = pd.concat(dfs, ignore_index=True)
    full_df.drop_duplicates(inplace=True)
    
    full_df.columns = [c.strip() for c in full_df.columns]
    
    # CSV: docto_id, referencia, fecha, cantidad_pedida, cantidad_surtida, tarimas, estado, tasa_de_cumplimiento
    # DB: docto_id, referencia, fecha, hora, cantidad_pedida, cantidad_surtida, tarimas, estado, fill_rate

    rename_map = {
        'tasa_de_cumplimiento': 'fill_rate'
    }
    full_df.rename(columns=rename_map, inplace=True)

    # Clean Data First to handle date parsing
    # Parse Fecha
    if 'fecha' in full_df.columns:
        full_df['fecha_dt'] = pd.to_datetime(full_df['fecha'], errors='coerce', dayfirst=True)
        full_df['fecha_new'] = full_df['fecha_dt'].dt.strftime('%Y-%m-%d')
        full_df['hora'] = full_df['fecha_dt'].dt.strftime('%H:%M:%S')
        # Replace original fecha with date part
        full_df['fecha'] = full_df['fecha_new']
    else:
        full_df['fecha'] = ''
        full_df['hora'] = ''

    required_cols = ['docto_id', 'referencia', 'fecha', 'hora', 'cantidad_pedida', 'cantidad_surtida', 'tarimas', 'estado', 'fill_rate']
    for col in required_cols:
        if col not in full_df.columns:
            full_df[col] = ''
            
    # Clean Data
    full_df['cantidad_pedida'] = clean_numeric(full_df['cantidad_pedida'])
    full_df['cantidad_surtida'] = clean_numeric(full_df['cantidad_surtida'])
    full_df['tarimas'] = clean_numeric(full_df['tarimas'])
    
    # Clean Fill Rate (remove % if present)
    full_df['fill_rate'] = full_df['fill_rate'].astype(str).str.replace('%', '').str.strip()
    full_df['fill_rate'] = pd.to_numeric(full_df['fill_rate'], errors='coerce').fillna(0)
    
    full_df['docto_id'] = clean_string(full_df['docto_id'])
    full_df['estado'] = clean_string(full_df['estado'])

    # Filter out System Generated Orders (INV start)
    if 'referencia' in full_df.columns:
        initial_count = len(full_df)
        full_df = full_df[~full_df['referencia'].astype(str).str.startswith('INV', na=False)]
        filtered_count = len(full_df)
        if initial_count != filtered_count:
            logging.info(f"Filtered out {initial_count - filtered_count} 'INV' system records.")

    final_df = full_df[required_cols].copy()

    try:
        conn = sqlite3.connect(DB_PATH)
        final_df.to_sql("surtido", conn, if_exists="replace", index=False)
        count = len(final_df)
        conn.close()
        logging.info(f"Successfully loaded {count} Outbound rows to 'surtido' table.")
    except Exception as e:
        logging.error(f"Database error (Outbound): {e}")

if __name__ == "__main__":
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    process_inbound()
    process_outbound()
    logging.info("Data consolidation complete.")
