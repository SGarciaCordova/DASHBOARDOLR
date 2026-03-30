import os
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import sys

# Cargar .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if "[TU-PASSWORD]" in DATABASE_URL:
    print("❌ ERROR: No has configurado la contraseña de Supabase en el archivo .env")
    sys.exit(1)

def migrate():
    # 1. Conectar a SQLite Local
    sqlite_path = 'auth_system/auth.db'
    if not os.path.exists(sqlite_path):
        print("❌ ERROR: No se encontró la base de datos local auth.db")
        return

    print("🔄 Leyendo usuarios locales...")
    conn_sqlite = sqlite3.connect(sqlite_path)
    cursor = conn_sqlite.cursor()
    
    try:
        cursor.execute("SELECT email, password_hash, role, failed_attempts, account_locked FROM users")
        local_users = cursor.fetchall()
    except Exception as e:
        print(f"❌ ERROR al leer SQLite: {e}")
        return
    finally:
        conn_sqlite.close()

    if not local_users:
        print("ℹ️ No hay usuarios para migrar.")
        return

    # 2. Conectar a Supabase (Postgres)
    print(f"🔗 Conectando a Supabase...")
    try:
        # Usamos pooling para evitar problemas de conexión
        engine = create_engine(DATABASE_URL)
        # Intentar conectar
        with engine.connect() as conn:
            print("✅ Conexión a Supabase exitosa.")
            
            # 3. Insertar usuarios
            print(f"🚀 Migrando {len(local_users)} usuarios...")
            from sqlalchemy import text
            for user in local_users:
                email, pwd_hash, role, attempts, locked = user
                
                # Convertir explícitamente tipos para Postgres
                attempts_val = int(attempts) if attempts is not None else 0
                locked_val = bool(locked) if locked is not None else False
                
                insert_query = text("""
                INSERT INTO users (email, password_hash, role, failed_attempts, account_locked)
                VALUES (:email, :pwd_hash, :role, :attempts, :locked)
                ON CONFLICT (email) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role;
                """)
                conn.execute(insert_query, {
                    "email": email, 
                    "pwd_hash": pwd_hash, 
                    "role": role, 
                    "attempts": attempts_val, 
                    "locked": locked_val
                })
                conn.commit()
            
            print("🎉 ¡Migración completada con éxito!")

    except Exception as e:
        print(f"❌ ERROR durante la migración a Supabase: {e}")
        print("\nNota: Asegúrate de haber ejecutado el SQL de creación de tabla en el Dashboard de Supabase primero.")

if __name__ == "__main__":
    migrate()
