import os
import time
import json
import logging
import sys
import random
import pandas as pd
from datetime import datetime
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright

# Add project root to sys.path for relative imports
_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from src.database import log_activity
except Exception:
    def log_activity(*args, **kwargs): pass # Fallback if import fails

# === CONFIGURATION ===
try:
    from dotenv import load_dotenv
    _root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    load_dotenv(os.path.join(_root, ".env"))
except Exception:
    pass

WMS_URL = os.getenv("WMS_URL", "https://apolo.soft-gator.com/gatorwolr/index.jsp")
USER = os.getenv("WMS_USER", "")
PASS = os.getenv("WMS_PASS", "")

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_status.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_reebok.log")

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Log start of process
user_trigger = os.getenv("TRIGGERED_BY", "Unknown")
logging.info(f"═══ INICIANDO SYNC AEROPUERTO - Activado por: {user_trigger} ═══")


# === HELPERS ===
def update_status(message, percent):
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump({"message": message, "percent": percent, "status": "running"}, f)
    except Exception as e:
        logging.error(f"Failed to update status: {e}")

def random_sleep(min_s=2, max_s=5):
    time.sleep(random.uniform(min_s, max_s))

def process_csv(file_path, table_name, unused_mapping):
    logging.info(f"Processing {file_path} into {table_name}...")
    try:
        if not file_path or not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return

        df = pd.read_csv(file_path, encoding='latin-1', on_bad_lines='skip')
        
        # Normalize columns: lower, clean spaces/dots for SQL safety
        df.columns = [c.strip().lower().replace(' ', '_').replace('.', '').replace('/', '_') for c in df.columns]

        # RE-MAPPING IMPORTANT COLUMNS (Ensures Supabase core fields are populated correctly)
        mapping_dict = {
            'documento_id': 'docto_id', 'pedido': 'docto_id', 'documento': 'docto_id', 'docto': 'docto_id', 'orden': 'docto_id',
            'ref': 'referencia', 'caja': 'referencia',
            'fecha_creacion': 'fecha', 'f_alta': 'fecha',
            'entrega': 'fecha_entrega', 'deadline': 'fecha_entrega', 'entregar': 'fecha_entrega',
            'cancelacion': 'fecha_cancelacion', 'cancelado': 'fecha_cancelacion',
            'items': 'partidas', 'lineas': 'partidas',
            'locacion': 'ubicacion', 'location': 'ubicacion', 'pasillo': 'ubicacion',
            'nombre_cliente': 'cliente', 'account': 'cliente', 'customer': 'cliente',
            'cantidad': 'cantidad_pedida', 'piezas': 'cantidad_pedida', 'pedida': 'cantidad_pedida',
            'surtida': 'cantidad_surtida', 'atendida': 'cantidad_surtida', 'surtido': 'cantidad_surtida',
            'pallets': 'tarimas', 'huella': 'tarimas',
            'fill_rate': 'tasa_de_cumplimiento', '%_avance': 'tasa_de_cumplimiento', 'avance': 'tasa_de_cumplimiento',
            'status': 'estado'
        }
        
        # Rename only if the target name doesn't exist yet and the source does
        for src, target in mapping_dict.items():
            if src in df.columns and target not in df.columns:
                df.rename(columns={src: target}, inplace=True)

        from sqlalchemy import create_engine, text
        DATABASE_URL = os.getenv("DATABASE_URL")
        engine = create_engine(DATABASE_URL)
        
        logging.info(f"Clearing table {table_name} and updating schema if needed...")
        with engine.connect() as conn:
            # 1. Get current columns from DB
            res = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '{table_name}'"))
            existing_cols = [r[0] for r in res]
            
            # 2. Add missing columns to Supabase
            for col in df.columns:
                if col not in existing_cols:
                    logging.info(f"Adding new column '{col}' to {table_name}...")
                    try:
                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN \"{col}\" TEXT"))
                        conn.commit()
                    except Exception as e:
                        logging.warning(f"Failed to add column {col}: {e}")
            
            # 3. Clear data (Fresh import)
            conn.execute(text(f"DELETE FROM {table_name}"))
            conn.commit()
        
        # Clean numeric columns before inserting
        numeric_cols = ['cantidad_pedida', 'cantidad_surtida', 'tarimas', 'tasa_de_cumplimiento']
        for col in numeric_cols:
            if col in df.columns:
                try:
                    df[col] = df[col].astype(str).str.replace(',', '').str.strip().apply(pd.to_numeric, errors='coerce').fillna(0)
                except:
                    pass

        # Bulk Insert EVERYTHING
        if not df.empty:
            df.to_sql(table_name, engine, if_exists='append', index=False)
            logging.info(f"Bulk inserted {len(df)} rows into {table_name}")
        
        try:
            os.remove(file_path)
        except:
            pass
            
    except Exception as e:
        logging.error(f"Failed to process CSV: {e}")

def login(page):
    update_status("Iniciando sesión...", 10)
    logging.info("Navigating to Login Page...")
    page.goto(WMS_URL)
    
    try:
        page.locator("#user").wait_for(state="visible", timeout=15000)
        page.locator("#user").fill(USER)
        page.locator("#password").fill(PASS)
        
        page.locator("xpath=//button[contains(text(), 'Iniciar Sesión')]").click()
        
        try:
            client_select = page.locator("#indexCta")
            client_select.wait_for(state="visible", timeout=10000)
            client_select.select_option(label="Reebok / Reebok")
            page.locator("#chooseServerButton").click()
        except Exception:
            pass
        
        page.locator("#menu").wait_for(state="attached", timeout=30000)
        logging.info("Login Successful.")
        
    except Exception as e:
        logging.error(f"Login failed: {e}")
        raise
def main():
    update_status("Iniciando ambiente de automatización...", 2)
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    with sync_playwright() as p:
        headless_mode = False
        if os.getenv("DOCKER_ENV") == "1":
            headless_mode = True
            logging.info("Playwright: modo headless activado (Docker/sin display)")
            
        try:
            ua = UserAgent()
            user_agent = ua.random
        except:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            
        update_status("Lanzando navegador (Chromium)...", 5)
        browser = p.chromium.launch(
            headless=headless_mode,
            args=["--start-maximized", "--disable-gpu", "--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        update_status("Navegador listo. Abriendo portal WMS...", 8)
        # Permite descargas sin confirmación
        context = browser.new_context(
            user_agent=user_agent,
            accept_downloads=True,
            no_viewport=True  # Para start-maximized
        )
        # Evitar deteccion webdriver
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()
        
        try:
            user_trigger = os.getenv("TRIGGERED_BY", "REEBOK_SCRAPER_AIRPORT")
            # log_activity(user_trigger, "SCRAPER_RUN", "Iniciando scraper de Airport Mode (Activos)")
            login(page)
            POOL_ID_SURTIDO = "e352a00c-66df-438e-b1bc-55ff8610918d"
            
            # === 1. ACTIVOS (Aeropuerto Raw) ===
            update_status("Sincronizando órdenes activas (Airport)...", 30)
            
            # Asegurar que el pool esté abierto
            page.evaluate(f"getPool({{screen:'{POOL_ID_SURTIDO}'}});")
            time.sleep(1)
            
            # A) ESPERAR LIMPIEZA DE OVERLAY (GatorWMS a veces muestra #processing al cambiar de pantalla)
            try:
                page.wait_for_selector("#processing", state="hidden", timeout=15000)
                logging.info("Overlay #processing is hidden.")
            except: 
                pass # Si no existe o ya está oculto, ignoramos el error

            # B) CLICK ROBUSTO EN LUPA (BÚSQUEDA)
            search_btn_xpath = f"xpath=//div[contains(@id, '{POOL_ID_SURTIDO}')]//button[.//i[contains(@class, 'fa-search')]]"
            try:
                btn = page.locator(search_btn_xpath).first
                btn.wait_for(state="visible", timeout=10000)
                btn.click(force=True)
                logging.info("Magnifying glass (Search) clicked.")
            except Exception as e:
                logging.warning(f"Manual click failed ({e}), trying JavaScript fallback search...")
                page.evaluate(f"searchMe({{cancelBubble:true, stopPropagation:function(){{}}}}, '{POOL_ID_SURTIDO}');")
            
            # El WMS suele mostrar datos al instante tras el click, usamos un timeout mínimo de seguridad
            try:
                page.wait_for_selector(f"div#{POOL_ID_SURTIDO} table tbody tr", timeout=2000)
                logging.info("Rows detected in the table.")
            except:
                pass

            # Eliminamos pausa extra, ya validamos que hay datos arriba
            
            # === DESCARGAR CSV ===
            update_status("Descargando reporte de Surtido Activo...", 70)
            js_download_active = f"""
            accioname(
                {{"icono": "fa fa-file-excel-o ", "accion": "obtenMiCSV", "nombre": "CSV"}},
                "{POOL_ID_SURTIDO}"
            );
            """
            
            # Esperamos activamente la descarga proveniente del click o evaluate
            with page.expect_download(timeout=60000) as download_info:
                page.evaluate(js_download_active)
            
            download = download_info.value
            file_active = os.path.join(DOWNLOAD_DIR, f"activos_{int(time.time())}.csv")
            download.save_as(file_active)
            
            if os.path.exists(file_active):
                process_csv(file_active, "wms_aeropuerto_raw", None)
            else:
                logging.error("Failed to save Activos CSV")


            update_status("Proceso Completado", 100)
            # log_activity(user_trigger, "SCRAPER_RUN", "Sincronización de Airport Mode (Activos) Completada")
            with open(STATUS_FILE, "w") as f:
                json.dump({"message": "Actualización Airport Mode Completada", "percent": 100, "status": "complete"}, f)

        except Exception as e:
            logging.error(f"Process failed: {e}")
            log_activity(user_trigger, "SCRAPER_ERROR", f"Error en scraper de Airport Mode: {str(e)}", status="ERROR")
            with open(STATUS_FILE, "w") as f:
                json.dump({"message": "Error en proceso", "percent": 0, "status": "error"}, f)
            try:
                page.screenshot(path="scraper_aeropuerto_error.png")
            except:
                pass
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()
