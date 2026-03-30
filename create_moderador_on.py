import os
import sys
sys.path.append(os.getcwd())

from auth_system.database import get_db
from auth_system.auth import register_user
from dotenv import load_dotenv

load_dotenv()

def create_moderator_on():
    db = next(get_db())
    email = "moderador_on"
    password = "moderadoron123"
    role = "moderador_on"
    
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
    create_moderator_on()
