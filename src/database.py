import sqlite3
import pandas as pd
import os

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
