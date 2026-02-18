import os
from auth_system.database import engine, Base, get_db
from auth_system.auth import register_user
from auth_system.models import User

# Asegurar que las tablas existan
Base.metadata.create_all(bind=engine)

def create_admin():
    db = next(get_db())
    email = os.getenv("ADMIN_EMAIL", "admin")
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        print("Error: Define la variable de entorno ADMIN_PASSWORD para crear el usuario admin.")
        print("Ejemplo (PowerShell): $env:ADMIN_PASSWORD = 'tu_contraseña_segura'")
        print("Ejemplo (CMD): set ADMIN_PASSWORD=tu_contraseña_segura")
        return
    try:
        register_user(db, email, password, role="admin")
        print(f"Usuario '{email}' creado exitosamente como admin.")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    create_admin()
