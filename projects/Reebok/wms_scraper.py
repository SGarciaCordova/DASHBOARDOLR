import os
import time
import json
import logging
# Cargar .env desde la raíz del proyecto (para WMS_USER, WMS_PASS, WMS_URL)
try:
    from dotenv import load_dotenv
    _root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    load_dotenv(os.path.join(_root, ".env"))
except Exception:
    pass
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import random

def random_sleep(min_s=2, max_s=5):
    """Sleeps for a random amount of time to mimic human behavior."""
    sleep_time = random.uniform(min_s, max_s)
    # logging.info(f"Sleeping for {sleep_time:.2f}s...")
    time.sleep(sleep_time)

import sys

# Setup logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_status.json")

def update_status(message, percent):
    """Writes status to a JSON file for the dashboard to read."""
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump({"message": message, "percent": percent, "status": "running"}, f)
    except Exception as e:
        logging.error(f"Failed to update status: {e}")

# Configuration - credenciales desde variables de entorno (no hardcodear)
WMS_URL = os.getenv("WMS_URL", "https://apolo.soft-gator.com/gatorwolr/index.jsp")
USER = os.getenv("WMS_USER", "")
PASS = os.getenv("WMS_PASS", "")
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

# Ensure download directory exists
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

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
    
    # Anti-Detection: Disable automation flags
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Anti-Detection: Random User-Agent
    try:
        ua = UserAgent()
        user_agent = ua.random
        logging.info(f"User-Agent: {user_agent}")
        options.add_argument(f"user-agent={user_agent}")
    except Exception as e:
        logging.warning(f"Failed to generate random User-Agent: {e}")

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
    
    # Anti-Detection: Overwrite navigator.webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def login(driver):
    if not USER or not PASS:
        raise ValueError(
            "WMS_USER y WMS_PASS deben estar definidos en .env o variables de entorno. "
            "No hardcodear credenciales en el código."
        )
    update_status("Iniciando sesión...", 10)
    logging.info("Navigating to Login Page...")
    driver.get(WMS_URL)
    
    try:
        logging.info("Entering credentials...")
        user_field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "user")))
        pass_field = driver.find_element(By.ID, "password")
        
        user_field.clear()
        user_field.send_keys(USER)
        pass_field.clear()
        pass_field.send_keys(PASS)
        
        logging.info("Clicking Login Button...")
        login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Iniciar Sesión')]")
        login_btn.click()
             
        # Handle Client Selection (Choose Server)
        logging.info("Waiting for Client Selection...")
        try:
            # Wait for the select element
            client_select = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "indexCta"))
            )
            # Select Reebok (Value 2 based on analysis)
            from selenium.webdriver.support.ui import Select
            select = Select(client_select)
            select.select_by_visible_text("Reebok / Reebok")
            logging.info("Selected 'Reebok / Reebok'")
            
            # Click Enter
            enter_btn = driver.find_element(By.ID, "chooseServerButton")
            enter_btn.click()
            
        except Exception as e:
            logging.warning(f"Client selection step skipped or failed: {e}")
            # If it's already logged in or skipped, we might proceed.
        
        # Wait for login to complete (check for user profile or menu to confirm login)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "menu")))
        logging.info("Login & Selection Successful.")
        
    except Exception as e:
        logging.error(f"Login failed: {e}")
        driver.quit()
        raise

def trigger_download(driver, report_name):
    logging.info(f"Processing {report_name}...")
    
    # Wait for the Pool Input to be present. This contains the config and PoolID.
    # The ID starts with 'currentPool'.
    try:
        pool_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[id^='currentPool']"))
        )
        pool_input_id = pool_input.get_attribute("id")
        pool_id = pool_input_id.replace("currentPool", "")
        logging.info(f"Found Pool ID: {pool_id}")
        
        # Execute the download JS
        # Action config for CSV: {"icono": "fa fa-file-excel-o ", "accion": "obtenMiCSV", "nombre": "CSV"}
        js_script = f"""
        accioname(
            {{"icono": "fa fa-file-excel-o ", "accion": "obtenMiCSV", "nombre": "CSV"}},
            "{pool_id}"
        );
        """
        logging.info("Executing Download Script...")
        driver.execute_script(js_script)
        
        # Wait for file to appear
        wait_for_download(DOWNLOAD_DIR)
        
    except Exception as e:
        logging.error(f"Failed to trigger download for {report_name}: {e}")

def wait_for_download(folder, timeout=60, previous_count=0):
    logging.info("Waiting for download to complete...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        files = os.listdir(folder)
        
        # Check if any .crdownload or .tmp files exist
        downloading_files = [f for f in files if f.endswith('.crdownload') or f.endswith('.tmp')]
        
        # Check for confirmed CSVs
        current_csvs = [f for f in files if not f.endswith('.crdownload') and f.endswith('.csv')]
        
        # If we have new CSVs AND no active downloads, we are good.
        if len(current_csvs) > previous_count and not downloading_files:
            logging.info(f"Download detected! Total CSVs: {len(current_csvs)}")
            # Wait a bit more to be sure
            time.sleep(2)
            return len(current_csvs)
            
        # If we see .crdownload files, log it
        if downloading_files:
           logging.info(f"Downloading in progress... ({len(downloading_files)} files)")
           
        time.sleep(2)
        
    logging.warning("Download timed out or no NEW file found.")
    return previous_count

def navigate_menu(driver, menu_name):
    logging.info(f"Navigating to {menu_name}...")
    try:
        # OPEN SIDEBAR IF NEEDED
        try:
            sidebar = driver.find_element(By.ID, "menu")
            if "show" not in sidebar.get_attribute("class"):
                logging.info("Opening sidebar menu...")
                try:
                    toggle = driver.find_element(By.XPATH, "//button[@data-bs-target='#menu']")
                    toggle.click()
                    random_sleep(2, 3)
                    time.sleep(1)
                except:
                    # Fallback: maybe just click the icon?
                    driver.find_element(By.XPATH, "//i[contains(@class, 'fa-bars')]").click()
                    random_sleep(1, 2)
        except:
             pass

        # Find menu link containing the text.
        menu_item = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[.//span[contains(text(), '{menu_name}')]]"))
        )
        menu_item.click()
        random_sleep(4, 7) # Allow page load / dynamic content load
    except Exception as e:
        logging.error(f"Failed to navigate to {menu_name}: {e}")
        try:
            driver.save_screenshot(f"nav_error_{menu_name}.png")
        except:
            pass
        raise # Re-raise to stop execution if navigation fails

def clear_downloads():
    logging.info("Clearing download directory...")
    for f in os.listdir(DOWNLOAD_DIR):
        file_path = os.path.join(DOWNLOAD_DIR, f)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            logging.error(f"Failed to delete {file_path}: {e}")

def close_all_floating_windows(driver):
    logging.info("Closing all floating windows...")
    try:
        # Find all close buttons (Boostrap style)
        close_btns = driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-close')]")
        logging.info(f"Found {len(close_btns)} close buttons.")
        for btn in close_btns:
            try:
                if btn.is_displayed():
                    btn.click()
                    random_sleep(1, 1.5)
            except:
                 pass
                 
        # Additional safety: Press ESC
        from selenium.webdriver.common.keys import Keys
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except:
            pass
            
    except Exception as e:
        logging.warning(f"Error closing windows: {e}")

def main():
    driver = setup_driver()
    try:
        clear_downloads()
        login(driver)
        
        success = False
        current_count = 0
        
        update_status("Navegando a Entradas...", 20)
        # Inbound (Entradas)
        navigate_menu(driver, "Entradas")
        
        # Click the "2. Entradas" submenu option
        logging.info("Clicking Submenu '2. Entradas'...")
        try:
            submenu = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Reporte detallado de documentos de entrada')]"))
            )
            submenu.click()
            random_sleep(3, 6)
            
            # Click Search Button (Lupa) to load data
            logging.info("Clicking Search Button (Lupa)...")
            search_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//i[contains(@class, 'fa-search')]]"))
            )
            search_btn.click()
            
            # Wait for Data Rows to ensure data is ACTUALLY loaded
            # Wait for Data Rows OR "No records" message
            logging.info("Waiting for Data Rows...")
            try:
                WebDriverWait(driver, 90).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//table[starts-with(@id, 'reporte')]//tbody/tr")),
                        EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'No se encontraron registros')]")) # Hypothetical
                    )
                )
            except:
                logging.warning("Timeout waiting for data rows (Entradas). Proceeding anyway...")

            # Optional: Wait for at least 1 row? specific row count?
            rows = driver.find_elements(By.XPATH, "//table[starts-with(@id, 'reporte')]//tbody/tr")
            logging.info(f"Data Loaded: {len(rows)} rows found.")
            random_sleep(2, 4) # Extra buffer for rendering
            
        except Exception as e:
            logging.error(f"Failed to navigate/search Entradas: {e}")
            raise

        update_status("Descargando Entradas...", 30)
        trigger_download(driver, "Entradas")
        
        # Wait for Inbound Download
        # We might get multiple files. Wait until at least one new one appears.
        # But wait a bit longer to ensure multiple files (if any) start downloading?
        random_sleep(8, 12)
        current_count = wait_for_download(DOWNLOAD_DIR, timeout=300, previous_count=current_count) # Increased timeout
        
        
        # Validate downloads for Inbound (optional, we already waited)
        
        # Close any open windows/modals from Inbound phase
        close_all_floating_windows(driver)
        random_sleep(2, 3)

        logging.info("Surtido section removed from Phase 1 (Moved to Phase 2).")
        
        logging.info("All downloads completed. Waiting 5s before closing...")
        random_sleep(4, 6)

        # ====== DATA UNIFICATION ======
        # ====== DATA UNIFICATION (DISABLED - Handled by Dashboard Phase 3) ======
        # update_status("Procesando datos...", 90)
        # logging.info("Starting Data Unification...")
        # try:
        #     import unificador
        #     unificador.process_inbound()
        #     unificador.process_outbound()
        #     logging.info("Data Unification completed successfully.")
        #     update_status("Completado", 100)
        #     # Final success status write
        #     with open(STATUS_FILE, "w") as f:
        #         json.dump({"message": "Actualización completada", "percent": 100, "status": "complete"}, f)
        #     success = True
        # except ImportError:
        #     # Try importing if running from root
        #     try:
        #         from projects.Reebok import unificador
        #         unificador.process_inbound()
        #         unificador.process_outbound()
        #         logging.info("Data Unification completed successfully (module import).")
        #     except Exception as e:
        #         logging.error(f"Failed to import unificador: {e}")
        # except Exception as e:
        #     logging.error(f"Data Unification failed: {e}")
        
        logging.info("Skipping Unification (Handled by Phase 3)...")
        update_status("Fase 1 Completada", 100)
        with open(STATUS_FILE, "w") as f:
                json.dump({"message": "Fase 1 completada", "percent": 100, "status": "complete"}, f)
        success = True

        
    except Exception as e:
        logging.error(f"Scraper failed: {e}")
        try:
            driver.save_screenshot("scraper_error.png")
            logging.info("Saved scraper_error.png")
        except:
            pass
        driver.quit()
        raise
        
    try:
        if driver:
            driver.quit()
    except Exception as e:
        logging.warning(f"Error closing driver: {e}")

    if success:
        logging.info("Exiting script with code 0")
        sys.exit(0)
    else:
        logging.error("Exiting script with code 1")
        sys.exit(1)

if __name__ == "__main__":
    main()
