
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'auth.db')

def migrate():
    print(f"Migrating database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'locked_until' in columns:
            print("Column 'locked_until' already exists. Skipping.")
        else:
            print("Adding 'locked_until' column...")
            # SQLite doesn't strictly support datetime types in the same way, usually TEXT or REAL/INTEGER.
            # SQLAlchemy DateTime uses TEXT or NUMERIC by default in SQLite. 
            # We will use DATETIME type which SQLite accepts as a valid affinity.
            cursor.execute("ALTER TABLE users ADD COLUMN locked_until DATETIME")
            conn.commit()
            print("Migration successful: Added 'locked_until' column.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
