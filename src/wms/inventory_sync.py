import os
import sys
import time
import logging
import argparse
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
 
# ─── Configuración Global ────────────────────────────────────────────────────
 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
load_dotenv()
 
WMS_URL  = os.getenv("WMS_URL")
WMS_USER = os.getenv("WMS_USER")
WMS_PASS = os.getenv("WMS_PASS")
DB_URL   = os.getenv("DATABASE_URL")
 
DOWNLOAD_DIR = os.path.join(os.getcwd(), "temp_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
 
# Logger global — inicializado al arrancar el módulo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("inventory_sync.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("InventorySync")
 
# ─── Mapeo de clientes → texto exacto en el menú del WMS ────────────────────
CLIENT_MAP = {
    "REEBOK":    "Reebok / Reebok",
    "ON":        "Monte Rosa / Monte Rosa",
    "PIARENA":   "Piarena / Piarena",
    "LUSUS":     "Lusus / Lusus",
    "MINI GRIP": "Mini Grip / Mini Grip",
}
 
# ─── Driver ──────────────────────────────────────────────────────────────────
 
def build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory":                             DOWNLOAD_DIR,
        "download.prompt_for_download":                           False,
        "profile.default_content_setting_values.automatic_downloads": 1,
    }
    opts.add_experimental_option("prefs", prefs)
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=2560,1440")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
 
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)
 
# ─── Login + Selección de Bodega ─────────────────────────────────────────────
 
def login(driver: webdriver.Chrome, wait: WebDriverWait, client_name: str) -> bool:
    log.info(f"[{client_name}] Navegando a {WMS_URL}")
    driver.get(WMS_URL)
 
    try:
        wait.until(EC.presence_of_element_located((By.ID, "user"))).send_keys(WMS_USER)
        driver.find_element(By.ID, "password").send_keys(WMS_PASS)
        driver.find_element(By.XPATH, "//button[contains(text(),'Iniciar Sesión')]").click()
    except TimeoutException:
        log.error(f"[{client_name}] Tiempo de espera de login agotado.")
        return False
 
    try:
        sel_elem = wait.until(EC.presence_of_element_located((By.ID, "indexCta")))
        select   = Select(sel_elem)
 
        target_text = CLIENT_MAP.get(client_name.upper())
        selected    = False
 
        if target_text:
            try:
                select.select_by_visible_text(target_text)
                log.info(f"[{client_name}] Bodega seleccionada (exacta): '{target_text}'")
                selected = True
            except Exception:
                log.warning(f"[{client_name}] No se encontró '{target_text}', intentando parcial...")
 
        if not selected:
            keyword = client_name.upper()
            matches = [opt for opt in select.options if keyword in opt.text.upper()]
            if matches:
                select.select_by_visible_text(matches[0].text)
                log.info(f"[{client_name}] Bodega seleccionada (parcial): '{matches[0].text}'")
                selected = True
            else:
                log.error(f"[{client_name}] ❌ No se encontró bodega. Opciones: {[o.text for o in select.options]}")
                return False
 
        ingresar = wait.until(EC.element_to_be_clickable((By.ID, "chooseServerButton")))
        driver.execute_script("arguments[0].click();", ingresar)
        return True
    except TimeoutException:
        log.warning(f"[{client_name}] No apareció selector (ya logueado).")
        return True
 
# ─── Flujo de Inventario ──────────────────────────────────────────────────────
 
def _limpiar_descargas():
    for f in os.listdir(DOWNLOAD_DIR):
        try: os.remove(os.path.join(DOWNLOAD_DIR, f))
        except: pass
 
def _esperar_descarga(timeout: int = 60) -> str | None:
    for _ in range(timeout):
        files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith(".csv") and not f.endswith(".crdownload")]
        if files: return os.path.join(DOWNLOAD_DIR, files[0])
        time.sleep(1)
    return None
 
def _switch_to_modal_frame(driver: webdriver.Chrome) -> bool:
    """
    Las ventanas de GatorWMS son iframes dinámicos.
    """
    driver.switch_to.default_content()
    time.sleep(2)
    # Buscamos el iframe que sea visible y no sea del menú lateral
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for frame in reversed(iframes):
        try:
            if not frame.is_displayed(): continue
            driver.switch_to.frame(frame)
            # Si vemos el botón de buscar o el enlace CSV, estamos en el correcto
            if driver.find_elements(By.XPATH, "//button[contains(@onclick,'searchMe')] | //a[contains(.,'CSV')] | //i[contains(@class,'fa-search')]"):
                log.info("Iframe de reporte localizado.")
                return True
            driver.switch_to.default_content()
        except:
            driver.switch_to.default_content()
    return False

def abrir_menu(driver, wait):
    """Intenta abrir el menú pero no bloquea si falla la detección."""
    try:
        # Si ya es visible algún enlace de la barra lateral, no hacemos nada
        elements = driver.find_elements(By.XPATH, "//a[contains(.,'Inventario')] | //a[contains(.,'Configuración')]")
        if any(e.is_displayed() for e in elements):
            return

        log.info("Menú no detectado como visible, intentando abrir...")
        btn = driver.find_element(By.XPATH, "//button[contains(.,'menú')] | //*[@id='menu-toggle'] | //*[contains(@class,'fa-bars')]")
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)
    except:
        pass

def get_inventory_data(driver: webdriver.Chrome, wait: WebDriverWait, client_name: str) -> str | None:
    log.info(f"[{client_name}] ── Iniciando flujo ──")
    try:
        driver.switch_to.default_content()
        
        # Paso 1: Abrir el menú de la derecha (Corección: forzar por JS)
        log.info("Paso 1: Forzando apertura de menú hamburguesa...")
        abrir_menu(driver, wait)
        time.sleep(3) # Pausa vital para animaciones de GatorWMS
        
        # Paso 2: Click en "Inventario" (Buscando el icono fa-boxes o el texto)
        log.info("Paso 2: Movimiento de mouse a 'Inventario'...")
        btn_inv = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//i[contains(@class,'fa-boxes')]/ancestor::a | //a[contains(.,'Inventario')] | //li[contains(.,'Inventario')]/a"
        )))
        actions = ActionChains(driver)
        actions.move_to_element(btn_inv).click().perform()
        log.info("Paso 2 ✓: Click físico en Inventario (Derecha)")
        time.sleep(2)
        
        # Paso 3: Click en "4. Inventario" (Ventana izquierda - Imagen 3)
        driver.switch_to.default_content() 
        _switch_to_modal_frame(driver)
        log.info("Paso 3: Localizando '4. Inventario' (div.fw-bold)...")
        # Selector exacto de tu nueva captura: div.fw-bold con texto Inventario
        opcion_4 = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//div[@class='fw-bold' and contains(., 'Inventario')] | //a[contains(@onclick, 'getForm')]//div[contains(., 'Inventario')]"
        )))
        actions = ActionChains(driver)
        actions.move_to_element(opcion_4).click().perform()
        log.info("Paso 3 ✓: Click físico en 4. Inventario (Izquierda)")
        time.sleep(3)
 
        # Paso 4: Click en la LUPA (Nueva ventana flotante - Imagen 4)
        _switch_to_modal_frame(driver)
        log.info("Paso 4: Localizando Lupa (i.fa-search)...")
        lupa = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, "i.fa-search, button.btn-info"
        )))
        actions = ActionChains(driver)
        actions.move_to_element(lupa).click().perform()
        log.info("Paso 4 ✓: Click físico en Lupa (Búsqueda iniciada)")
        
        # Paso 5: Click en CSV y descargar (Imagen 5)
        _switch_to_modal_frame(driver)
        log.info("Paso 5: Localizando enlace CSV (span CSV)...")
        csv_link = WebDriverWait(driver, 120).until(EC.element_to_be_clickable((
            By.XPATH, "//a[.//span[text()='CSV']] | //*[text()='CSV']/parent::a"
        )))
        
        log.info("Paso 5 ✓: Enlace CSV localizado. Iniciando descarga...")
        _limpiar_descargas()
        driver.execute_script("arguments[0].click();", csv_link)
        
        # Darle tiempo extra a la descarga física del archivo
        # Subimos a 5 minutos (300s) por lentitud del WMS confirmada por el usuario
        res = _esperar_descarga(300) 
        return res
    except Exception as e:
        ss_path = f"error_{client_name}.png"
        driver.save_screenshot(ss_path)
        log.error(f"[{client_name}] Falló flujo en paso actual. Captura: {ss_path}. Error: {e}")
        return None
 
# ─── Sincronización a Supabase ────────────────────────────────────────────────
 
COLUMN_CANDIDATES = {
    "ubicacion_nombre": ["ubicacion_nombre", "ubicacion", "location", "bin"],
    "ubicacion_id":     ["ubicacion_id", "bin_id", "loc_id"],
    "sku":              ["sku", "articulo", "item", "codigo"],
    "descripcion":      ["sku_descripcion", "descripcion", "desc", "nombre"],
    "cantidad":         ["cantidad", "existencia", "qty"],
}
 
def _resolver_columna(df_cols, candidates):
    cols_lower = {c.lower(): c for c in df_cols}
    for cand in candidates:
        for cl, co in cols_lower.items():
            if cand in cl: return co
    return None
 
def sync_to_supabase(file_path: str, client_name: str) -> None:
    if not file_path: return
    try:
        df = pd.read_csv(file_path, encoding="latin-1", dtype=str)
        clean_rows = []
        for _, row in df.iterrows():
            item = {"cliente": client_name.upper()}
            for target, candidates in COLUMN_CANDIDATES.items():
                col = _resolver_columna(list(df.columns), candidates)
                val = row[col] if col else ""
                if target == "cantidad":
                    try: val = float(str(val).replace(",", "").strip())
                    except: val = 0.0
                elif target == "ubicacion_id":
                    try: val = int(float(str(val).strip()))
                    except: val = None
                item[target] = val
            clean_rows.append(item)
 
        final_df = pd.DataFrame(clean_rows)
        # Añadir marca de tiempo de la sincronización real del robot
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        final_df['fecha_actualizacion'] = now
        
        engine   = create_engine(DB_URL)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM inventario_ubicaciones WHERE UPPER(cliente) = :c"), {"c": client_name.upper()})
            final_df.to_sql("inventario_ubicaciones", conn, if_exists="append", index=False)
        log.info(f"[{client_name}] ✅ Supabase actualizado con marca de tiempo {now}.")
    except Exception as e:
        log.error(f"[{client_name}] Error en sync: {e}")
 
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", default="REEBOK,ON,PIARENA", help="Clientes separados por coma")
    parser.add_argument("--no-headless", action="store_true", help="Muestra el navegador")
    args = parser.parse_args()
 
    client_list = [c.strip().upper() for c in args.clients.split(",") if c.strip()]
    headless    = not args.no_headless
 
    resultados = {}
    for client in client_list:
        log.info(f"\n{'='*45}\n  PROCESANDO: {client}\n{'='*45}")
        driver = build_driver(headless=headless)
        wait   = WebDriverWait(driver, 45)
        try:
            if login(driver, wait, client):
                path = get_inventory_data(driver, wait, client)
                if path:
                    sync_to_supabase(path, client)
                    resultados[client] = "OK"
                else: resultados[client] = "FALLÓ_DESCARGA"
            else: resultados[client] = "FALLÓ_LOGIN"
        except Exception as e:
            log.error(f"Error en {client}: {e}")
            resultados[client] = f"ERROR: {str(e)}"
        finally:
            driver.quit()
 
    log.info("\n" + "="*45 + "\n  RESUMEN FINAL\n" + "="*45)
    for c, s in resultados.items():
        log.info(f"  {'✅' if s=='OK' else '❌'} {c}: {s}")
    log.info("="*45)
 
if __name__ == "__main__":
    main()
