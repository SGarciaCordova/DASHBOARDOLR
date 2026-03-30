import os
import sys
sys.path.append(os.getcwd())

from auth_system.database import get_db
from auth_system.auth import register_user
from dotenv import load_dotenv

load_dotenv()

def create_seniormdc():
    db = next(get_db())
    email = "seniormdc"
    password = "seniormdc123"
    role = "gerencia"
    
    print(f"🚀 Creando usuario '{email}' con rol '{role}'...")
    try:
        register_user(db, email, password, role=role)
        print(f"✅ Usuario '{email}' creado exitosamente.")
    except ValueError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    create_seniormdc()
