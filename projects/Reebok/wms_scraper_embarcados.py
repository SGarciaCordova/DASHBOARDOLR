import os
import time
import json
import logging
import sys
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent

# === CONFIGURATION ===
# Cargar .env desde la raíz del proyecto
try:
    from dotenv import load_dotenv
    _root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    load_dotenv(os.path.join(_root, ".env"))
except Exception:
    pass

WMS_URL = os.getenv("WMS_URL", "https://apolo.soft-gator.com/gatorwolr/index.jsp")
USER = os.getenv("WMS_USER", "")
PASS = os.getenv("WMS_PASS", "")

if not USER or not PASS:
    logging.error("Credenciales no encontradas en .env")
    
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_status.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_finalizados.log")

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
def random_sleep(min_s=2, max_s=5):
    time.sleep(random.uniform(min_s, max_s))

def update_status(message, percent):
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump({"message": message, "percent": percent, "status": "running"}, f)
    except Exception as e:
        logging.error(f"Failed to update status: {e}")

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
    update_status("Iniciando sesión (Finalizados)...", 10)
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
        
        # Client Selection
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

def trigger_download(driver, report_name):
    logging.info(f"Triggering download for {report_name}...")
    try:
        pool_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[id^='currentPool']"))
        )
        pool_id = pool_input.get_attribute("id").replace("currentPool", "")
        
        js_script = f"""
        accioname(
            {{"icono": "fa fa-file-excel-o ", "accion": "obtenMiCSV", "nombre": "CSV"}},
            "{pool_id}"
        );
        """
        driver.execute_script(js_script)
        
    except Exception as e:
        logging.error(f"Failed to trigger download: {e}")
        raise

def wait_for_download(folder, timeout=60):
    logging.info("Waiting for download...")
    start_time = time.time()
    initial_files = set(os.listdir(folder))
    
    while time.time() - start_time < timeout:
        current_files = set(os.listdir(folder))
        new_files = current_files - initial_files
        
        # Check for confirmed CSVs (not .crdownload)
        valid_new_files = [f for f in new_files if f.endswith('.csv') and not f.endswith('.crdownload')]
        
        if valid_new_files:
            logging.info(f"Download detected: {valid_new_files}")
            return True
            
        time.sleep(1)
        
    logging.warning("Download timed out.")
    return False

def close_all_floating_windows(driver):
    try:
        close_btns = driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-close')]")
        for btn in close_btns:
            try:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(0.5)
            except:
                pass
    except:
        pass

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    driver = setup_driver()
    try:
        login(driver)
        
        # Pool ID for Surtido provided in HTML
        POOL_ID_SURTIDO = "e352a00c-66df-438e-b1bc-55ff8610918d"
        
        update_status("Navegando al menú Surtido...", 20)
        
        # Step 1: Open Surtido Screen directly
        logging.info(f"Opening 'Surtido' screen ({POOL_ID_SURTIDO})...")
        driver.execute_script(f"getPool({{screen:'{POOL_ID_SURTIDO}'}});")
        random_sleep(4, 6)
        
        # Wait for Surtido container
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, f"//div[contains(@id, '{POOL_ID_SURTIDO}')]"))
            )
            logging.info("Surtido Container found.")
        except:
             logging.warning("Surtido container not found explicitly, proceeding with hope...")

        # Step 1.5: Download SURTIDO (Active Orders) - Moved from Phase 1
        update_status("Descargando Surtido (Activos)...", 30)
        logging.info("Triggering Search for Surtido (Active)...")
        try:
             driver.execute_script(f"searchMe(null, '{POOL_ID_SURTIDO}');")
             random_sleep(4, 6)
             
             # Wait for data or no records
             logging.info("Waiting for data table...")
             WebDriverWait(driver, 15).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//table[starts-with(@id, 'reporte')]//tbody/tr")),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'No se encontraron registros')]")) 
                )
             )
             random_sleep(2, 4)
             
             logging.info("Downloading Surtido (Active)...")
             js_download_active = f"""
             accioname(
                 {{"icono": "fa fa-file-excel-o ", "accion": "obtenMiCSV", "nombre": "CSV"}},
                 "{POOL_ID_SURTIDO}"
             );
             """
             driver.execute_script(js_download_active)
             
             if wait_for_download(DOWNLOAD_DIR, timeout=60):
                 logging.info("Surtido (Active) download successful.")
             else:
                 logging.warning("Surtido (Active) download timed out or no new file.")
                 
        except Exception as e:
             logging.error(f"Error processing Surtido (Active): {e}")
             # Don't stop, proceed to Embarcados
        
        # Step 2: Switch to "Embarcados" View
        # User says: Dropdown -> Embarcados
        update_status("Cambiando vista a Embarcados...", 40)
        
        logging.info("Executing JS to switch to 'Embarcados'...")
        # Dictionary from HTML: {"icono":"fas fa-shipping-fast","accion":"muestrame","nombre":"Shipped","pagina":"1","accionId":"embarque","condiciones":["surtido.por.sesion","salida.enc.embarcados"]}
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
        
        # Step 3: Trigger Search (Update view) - Optional but good practice
        # User mentioned "lupa". It might be needed to refresh the list after switching views.
        update_status("Actualizando lista...", 60)
        try:
             driver.execute_script(f"searchMe(null, '{POOL_ID_SURTIDO}');")
             logging.info("Search triggered to refresh list.")
             random_sleep(5, 8)
        except:
             pass

        # Step 4: Download CSV
        update_status("Descargando Reporte Embarcados...", 80)
        
        # Trigger Download via JS
        # Action from HTML: {"icono": "fa fa-file-excel-o ", "accion": "obtenMiCSV", "nombre": "CSV"}
        js_download = f"""
        accioname(
            {{"icono": "fa fa-file-excel-o ", "accion": "obtenMiCSV", "nombre": "CSV"}},
            "{POOL_ID_SURTIDO}"
        );
        """
        logging.info("Executing Download Script...")
        driver.execute_script(js_download)
        
        if wait_for_download(DOWNLOAD_DIR, timeout=300):
            logging.info("Download successful.")
            update_status("Descarga Embarcados completada", 100)
            
            # Additional cleanup: Rename the most recent file to something meaningful (optional, but good)
            # For now, we trust the wait_for_download to identify it.
            
            with open(STATUS_FILE, "w") as f:
                json.dump({"message": "Descarga Embarcados completada", "percent": 100, "status": "complete"}, f)
        else:
            logging.error("Download failed or timed out.")
            with open(STATUS_FILE, "w") as f:
                json.dump({"message": "Error en descarga Embarcados", "percent": 0, "status": "error"}, f)
            raise Exception("Download timeout")
            
        random_sleep(3, 5)

    except Exception as e:
        logging.error(f"Script failed: {e}")
        driver.save_screenshot("scraper_finalizados_error.png")
        sys.exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
