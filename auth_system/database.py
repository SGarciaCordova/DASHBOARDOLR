import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener URL de la base de datos desde .env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth_system/auth.db")
print(f"[DB] Sistema conectado a: {DATABASE_URL[:40]}...")

# Configurar argumentos de conexión
# check_same_thread es necesario solo para SQLite en aplicaciones multi-hilo como Streamlit
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False

# Crear el motor de la base de datos
engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args,
    pool_pre_ping=True # Recomendado para MySQL para evitar desconexiones
)

# Crear la sesión de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos declarativos
Base = declarative_base()

# Dependencia para obtener la sesión de BD en cada petición
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_config_warnings():
    """
    Revisa variables de entorno críticas y devuelve una lista de advertencias
    (no bloquea la ejecución). Útil para mostrar al arranque del Dashboard.
    """
    warnings = []
    if not os.getenv("DATABASE_URL"):
        warnings.append(
            "DATABASE_URL no está definida en .env; se usa SQLite por defecto. "
            "En producción, define DATABASE_URL en tu archivo .env."
        )
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.isfile(env_path):
        warnings.append(
            "No se encontró archivo .env en la raíz del proyecto. "
            "Copia .env.example a .env y configura las variables necesarias."
        )
    return warnings
