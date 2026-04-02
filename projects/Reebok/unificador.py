import os
import sys
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Setup logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_reebok.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
# Log start of unification
user_trigger = os.getenv("TRIGGERED_BY", "Unknown")
log = logging.getLogger("Unificador")
log.info(f"═══ FINALIZANDO SYNC (Fase 3: Unificación) - Activado por: {user_trigger} ═══")


def unify_data():
    log.info("═══ INICIANDO UNIFICACIÓN DE DATOS (REEBOK) ═══")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        log.error("DATABASE_URL no configurada en .env")
        return False
        
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # 1. Asegurar integridad en 'entradas' (Deduplicación)
            log.info("Optimizando tabla 'entradas'...")
            conn.execute(text("""
                DELETE FROM entradas 
                WHERE ctid NOT IN (
                    SELECT MIN(ctid) 
                    FROM entradas 
                    GROUP BY docto_id, sku, fecha, cliente
                )
            """))
            log.info("✓ Tabla 'entradas' deduplicada.")
            
            # 2. Asegurar integridad en 'surtido' (Deduplicación)
            # Nota: 'surtido' usa un esquema ligeramente diferente (con 'hora')
            log.info("Optimizando tabla 'surtido'...")
            conn.execute(text("""
                DELETE FROM surtido 
                WHERE ctid NOT IN (
                    SELECT MIN(ctid) 
                    FROM surtido 
                    GROUP BY docto_id, fecha, hora, cliente
                )
            """))
            log.info("✓ Tabla 'surtido' deduplicada.")
            
            # 3. Log de Actividad Final
            from src.database import log_activity
            user_trigger = os.getenv("TRIGGERED_BY", "SISTEMA_UNIFICADOR_REEBOK")
            log_activity(user_trigger, "SYNC", "Sincronización de Datos Completa")
            
            conn.commit()
            
        log.info("═══ UNIFICACIÓN COMPLETADA EXITOSAMENTE ═══")
        return True
        
    except Exception as e:
        log.error(f"Error durante la unificación: {e}")
        return False

if __name__ == "__main__":
    success = unify_data()
    if not success:
        sys.exit(1)
    sys.exit(0)
