import os
import sys
# Agregar el directorio actual al path para poder importar auth_system
sys.path.append(os.getcwd())

from auth_system.database import engine, Base, get_db
from auth_system.auth import register_user
from dotenv import load_dotenv

load_dotenv()

def create_moderator():
    db = next(get_db())
    email = "moderador"
    password = "moderador123"
    role = "moderador"
    
    print(f"🚀 Creando usuario '{email}' en Supabase...")
    try:
        register_user(db, email, password, role=role)
        print(f"✅ Usuario '{email}' creado exitosamente con el rol '{role}'.")
        print(f"🔑 Credenciales:\n   - Usuario: {email}\n   - Contraseña: {password}")
    except ValueError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    create_moderator()
