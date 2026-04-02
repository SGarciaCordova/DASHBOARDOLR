import os
import sys

# Ensure the project root is in the path for imports
sys.path.append(os.getcwd())

from auth_system.database import get_db
from auth_system.auth import register_user
from dotenv import load_dotenv

load_dotenv()

def create_moderators():
    db = next(get_db())
    users_to_create = [
        {"email": "moderador_on2", "password": "moderadoron123", "role": "moderador_on"},
        {"email": "moderador_on3", "password": "moderadoron123", "role": "moderador_on"}
    ]
    
    for user in users_to_create:
        email = user["email"]
        password = user["password"]
        role = user["role"]
        
        print(f"🚀 Creando usuario '{email}' en la base de datos...")
        try:
            register_user(db, email, password, role=role)
            print(f"✅ Usuario '{email}' creado exitosamente con el rol '{role}'.")
        except ValueError as e:
            # Check if user already exists
            if "already exists" in str(e).lower():
                print(f"⚠️ El usuario '{email}' ya existe.")
            else:
                print(f"❌ Error al crear '{email}': {e}")
        except Exception as e:
            print(f"❌ Ocurrió un error inesperado al crear '{email}': {e}")

if __name__ == "__main__":
    create_moderators()
