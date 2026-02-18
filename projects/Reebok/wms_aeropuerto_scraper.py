import os
import time
import json
import logging
import sys
import random
import sqlite3
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent

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
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_aeropuerto.log")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "wms_data.db")

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

# === HELPERS ===
def update_status(message, percent):
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump({"message": message, "percent": percent, "status": "running"}, f)
    except Exception as e:
        logging.error(f"Failed to update status: {e}")

def random_sleep(min_s=2, max_s=5):
    time.sleep(random.uniform(min_s, max_s))

def setup_driver():
    options = Options()
    # Headless automático en Docker (DOCKER_ENV=1) o si no hay display
    if os.getenv("DOCKER_ENV") == "1" or not os.getenv("DISPLAY", ""):
        options.add_argument("--headless=new")
        options.add_argument("--disable-dev-shm-usage")
        logging.info("Chrome: modo headless activado (Docker/sin display)")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        ua = UserAgent()
        user_agent = ua.random
        options.add_argument(f"user-agent={user_agent}")
    except:
        pass

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def login(driver):
    update_status("Iniciando sesión...", 10)
    logging.info("Navigating to Login Page...")
    driver.get(WMS_URL)
    
    try:
        user_field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "user")))
        pass_field = driver.find_element(By.ID, "password")
        
        user_field.clear()
        user_field.send_keys(USER)
        pass_field.clear()
        pass_field.send_keys(PASS)
        
        driver.find_element(By.XPATH, "//button[contains(text(), 'Iniciar Sesión')]").click()
        
        try:
            client_select = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "indexCta"))
            )
            from selenium.webdriver.support.ui import Select
            Select(client_select).select_by_visible_text("Reebok / Reebok")
            driver.find_element(By.ID, "chooseServerButton").click()
        except:
            pass
        
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "menu")))
        logging.info("Login Successful.")
        
    except Exception as e:
        logging.error(f"Login failed: {e}")
        driver.quit()
        raise

def wait_for_download(folder, timeout=60):
    logging.info("Waiting for download...")
    start_time = time.time()
    initial_files = set(os.listdir(folder))
    
    while time.time() - start_time < timeout:
        current_files = set(os.listdir(folder))
        new_files = current_files - initial_files
        
        valid_new_files = [f for f in new_files if f.endswith('.csv') and not f.endswith('.crdownload')]
        
        if valid_new_files:
            logging.info(f"Download detected: {valid_new_files}")
            return os.path.join(folder, valid_new_files[0])
            
        time.sleep(1)
        
    logging.warning("Download timed out.")
    return None

def process_csv(file_path, table_name, mapping):
    logging.info(f"Processing {file_path} into {table_name}...")
    try:
        if not file_path or not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return

        df = pd.read_csv(file_path, encoding='latin-1', on_bad_lines='skip')
        
        # Normalize columns: lower, clean spaces
        df.columns = [c.strip().lower().replace(' ', '_').replace('.', '') for c in df.columns]

        def find_col(possible_names):
            for name in possible_names:
                if name in df.columns:
                    return name
            return None

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        inserted_count = 0
        
        for index, row in df.iterrows():
            if table_name == "wms_aeropuerto_raw":
                 docto_id = row.get(find_col(['docto_id', 'pedido', 'documento', 'docto', 'orden']), '')
                 referencia = row.get(find_col(['referencia', 'ref', 'caja']), '')
                 fecha = row.get(find_col(['fecha', 'fecha_creacion', 'f_alta']), '')
                 cliente = row.get(find_col(['cliente', 'nombre_cte']), 'REEBOK')
                 cant_pedida = row.get(find_col(['cantidad_pedida', 'cantidad', 'piezas', 'pedida']), 0)
                 cant_surtida = row.get(find_col(['cantidad_surtida', 'surtida', 'atendida']), 0)
                 tarimas = row.get(find_col(['tarimas', 'pallets', 'huella']), 0)
                 fill_rate = row.get(find_col(['tasa_de_cumplimiento', '%_avance', 'avance', 'fill_rate']), 0)
                 estado = row.get(find_col(['estado', 'status']), 'SURTIENDOSE')
                 
                 try: cant_pedida = float(str(cant_pedida).replace(',', '').strip())
                 except: cant_pedida = 0
                 try: cant_surtida = float(str(cant_surtida).replace(',', '').strip())
                 except: cant_surtida = 0
                 try: tarimas = float(str(tarimas).replace(',', '').strip())
                 except: tarimas = 0
                 try: fill_rate = float(str(fill_rate).replace(',', '').strip())
                 except: fill_rate = 0

                 # Filter out pseudo-orders (INV)
                 if str(referencia).upper().startswith('INV'):
                     continue

                 cursor.execute("""
                    INSERT OR REPLACE INTO wms_aeropuerto_raw (docto_id, referencia, fecha, cliente, cantidad_pedida, cantidad_surtida, tarimas, tasa_de_cumplimiento, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                 """, (str(docto_id), str(referencia), str(fecha), str(cliente), cant_pedida, cant_surtida, tarimas, fill_rate, str(estado)))
                 inserted_count += 1

            elif table_name == "inbound_scord_despachados_raw":
                 docto_id = row.get(find_col(['docto_id', 'pedido', 'documento']), '')
                 referencia = row.get(find_col(['referencia', 'ref']), '')
                 fecha = row.get(find_col(['fecha', 'f_alta']), '')
                 cliente = row.get(find_col(['cliente']), 'REEBOK')
                 cant_pedida = row.get(find_col(['cantidad_pedida', 'cantidad']), 0)
                 cant_surtida = row.get(find_col(['cantidad_surtida', 'surtida']), 0)
                 tarimas = row.get(find_col(['tarimas']), 0)
                 estado = row.get(find_col(['estado', 'status']), 'Despachado')

                 # Filter out pseudo-orders (INV)
                 if str(referencia).upper().startswith('INV'):
                     continue

                 cursor.execute("""
                    INSERT OR REPLACE INTO inbound_scord_despachados_raw (docto_id, referencia, fecha, cliente, cantidad_pedida, cantidad_surtida, tarimas, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                 """, (str(docto_id), str(referencia), str(fecha), str(cliente), cant_pedida, cant_surtida, tarimas, str(estado)))
                 inserted_count += 1

        conn.commit()
        conn.close()
        logging.info(f"Inserted/Updated {inserted_count} rows into {table_name}")
        
        try:
            os.remove(file_path)
        except:
            pass
            
    except Exception as e:
        logging.error(f"Failed to process CSV: {e}")

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    driver = setup_driver()
    try:
        login(driver)
        POOL_ID_SURTIDO = "e352a00c-66df-438e-b1bc-55ff8610918d"
        
        # === 1. ACTIVOS (Aeropuerto Raw) ===
        update_status("Descargando Reporte Activos...", 30)
        
        # Navigate to Picking/Surtido
        driver.execute_script(f"getPool({{screen:'{POOL_ID_SURTIDO}'}});")
        random_sleep(4, 6)
        
        # Search & Download - Triggering search via button click to avoid JS event error
        try:
            search_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(@onclick, 'searchMe') and contains(@onclick, '{POOL_ID_SURTIDO}')]"))
            )
            driver.execute_script("arguments[0].click();", search_btn)
        except:
            logging.warning("Could not click search button, trying fallback script...")
            driver.execute_script(f"searchMe({{cancelBubble:true, stopPropagation:function(){{}}}}, '{POOL_ID_SURTIDO}');")
        
        random_sleep(5, 8)
        
        js_download_active = f"""
        accioname(
            {{"icono": "fa fa-file-excel-o ", "accion": "obtenMiCSV", "nombre": "CSV"}},
            "{POOL_ID_SURTIDO}"
        );
        """
        driver.execute_script(js_download_active)
        
        file_active = wait_for_download(DOWNLOAD_DIR)
        if file_active:
             process_csv(file_active, "wms_aeropuerto_raw", None)
        else:
             logging.error("Failed to download Activos CSV")

        # === 2. EMBARCADOS (Recent Departures) ===
        update_status("Descargando Reporte Embarcados...", 60)
        
        js_embarcados = f"""
        accioname(
            {{
                "icono": "fas fa-shipping-fast",
                "accion": "muestrame",
                "nombre": "Shipped",
                "pagina": "1",
                "accionId": "embarque",
                "condiciones": ["surtido.por.sesion", "salida.enc.embarcados"]
            }}, 
            "{POOL_ID_SURTIDO}"
        );
        """
        driver.execute_script(js_embarcados)
        random_sleep(5, 8)
        
        # Search & Download again
        try:
            search_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(@onclick, 'searchMe') and contains(@onclick, '{POOL_ID_SURTIDO}')]"))
            )
            driver.execute_script("arguments[0].click();", search_btn)
        except:
            driver.execute_script(f"searchMe({{cancelBubble:true, stopPropagation:function(){{}}}}, '{POOL_ID_SURTIDO}');")
        
        random_sleep(5, 8)
        
        js_download_shipped = f"""
        accioname(
            {{"icono": "fa fa-file-excel-o ", "accion": "obtenMiCSV", "nombre": "CSV"}},
            "{POOL_ID_SURTIDO}"
        );
        """
        driver.execute_script(js_download_shipped)
        
        file_shipped = wait_for_download(DOWNLOAD_DIR)
        if file_shipped:
             process_csv(file_shipped, "inbound_scord_despachados_raw", None)
        else:
             logging.error("Failed to download Embarcados CSV")

        update_status("Proceso Completado", 100)
        with open(STATUS_FILE, "w") as f:
            json.dump({"message": "Actualización Airport Mode Completada", "percent": 100, "status": "complete"}, f)

    except Exception as e:
        logging.error(f"Process failed: {e}")
        with open(STATUS_FILE, "w") as f:
            json.dump({"message": "Error en proceso", "percent": 0, "status": "error"}, f)
        driver.save_screenshot("scraper_aeropuerto_error.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
