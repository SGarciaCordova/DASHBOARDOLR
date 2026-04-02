import os
import sys

# Ensure the project root is in the path for imports
sys.path.append(os.getcwd())

from auth_system.database import get_db
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

def list_users():
    db = next(get_db())
    # Note: Using SQLAlchemy's `text` for raw SQL on a session/connection.
    # The table is likely `users` based on common patterns.
    try:
        result = db.execute(text("SELECT email, role FROM users WHERE email LIKE 'moderador_on%'"))
        users = result.fetchall()
        print("👤 Usuarios Moderadores ON encontrados:")
        for user in users:
            print(f"   - Email: {user[0]} | Rol: {user[1]}")
    except Exception as e:
        print(f"❌ Error al listar usuarios: {e}")

if __name__ == "__main__":
    list_users()
