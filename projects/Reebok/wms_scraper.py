"""
wms_scraper.py  ─ OPCIÓN NUCLEAR (Selenium)
═══════════════════════════════════════════
Reescritura completa con selectores verificados en grabación real del WMS.

Flujo:
  1. Login → seleccionar cliente Reebok
  2. Abrir sidebar ≡ menú → Entradas
  3. Elegir "Reporte detallado de documentos de entrada"
  4. Click lupa (Buscar) → esperar datos
  5. Click CSV → esperar descarga en disco
  6. Procesar CSV → INSERT en SQLite (tabla: entradas)
"""

import os
import sys
import time
import json
import logging
import random
import sqlite3
import glob
from pathlib import Path

import argparse
import pandas as pd
from sqlalchemy import create_engine, text

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager

try:
    from dotenv import load_dotenv
    _root = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    load_dotenv(os.path.join(_root, ".env"))
    
    # Añadir raíz al path para importar src
    if _root not in sys.path:
        sys.path.append(_root)
    from src.database import log_activity
except Exception:
    def log_activity(*args, **kwargs): pass # Fallback if import fails

# ─── Config ─────────────────────────────────────────────────────────────────
WMS_URL  = os.getenv("WMS_URL",  "https://apolo.soft-gator.com/gatorwolr/index.jsp")
WMS_USER = os.getenv("WMS_USER", "")
WMS_PASS = os.getenv("WMS_PASS", "")

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
STATUS_FILE  = os.path.join(BASE_DIR, "scraper_status.json")
LOG_FILE     = os.path.join(BASE_DIR, "sync_reebok.log")
DB_PATH      = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)),
                             "data", "wms_data.db")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# Log triggering user at the start
user_trigger = os.getenv("TRIGGERED_BY", "Unknown")
logging.info(f"═══ INICIANDO SYNC (Fase 1: Entradas) - Activado por: {user_trigger} ═══")



# ─── Utilidades ─────────────────────────────────────────────────────────────

def update_status(message: str, percent: int):
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump({"message": message, "percent": percent,
                       "status": "running"}, f)
    except Exception as e:
        log.error(f"update_status falló: {e}")


def rand_sleep(a=1.5, b=3.5):
    time.sleep(random.uniform(a, b))


def clear_downloads():
    log.info("Limpiando descargas previas...")
    for f in glob.glob(os.path.join(DOWNLOAD_DIR, "*")):
        try:
            os.remove(f)
        except Exception:
            pass


# ─── Driver ─────────────────────────────────────────────────────────────────

def build_driver(headless=False) -> webdriver.Chrome:
    """Chrome con descarga automática al DOWNLOAD_DIR sin popups."""
    opts = webdriver.ChromeOptions()

    # ── Preferencias de descarga ────────────────────────────────────────────
    prefs = {
        "download.default_directory":          DOWNLOAD_DIR,
        "download.prompt_for_download":        False,
        "download.directory_upgrade":          True,
        "safebrowsing.enabled":                True,
        "profile.default_content_setting_values.automatic_downloads": 1,
    }
    opts.add_experimental_option("prefs", prefs)

    if headless:
        opts.add_argument("--headless=new")

    # ── Anti-detección ────────────────────────────────────────────────────────
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # ── Ventana / entorno ─────────────────────────────────────────────────────
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-popup-blocking")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--mute-audio")

    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=opts)

    # Stealth básico
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )
    return driver


# ─── Login ───────────────────────────────────────────────────────────────────

def login(driver: webdriver.Chrome, wait: WebDriverWait, client_name: str = "Reebok"):
    update_status(f"Iniciando sesión para {client_name}...", 10)
    log.info(f"Navegando a {WMS_URL}")
    driver.get(WMS_URL)

    wait.until(EC.visibility_of_element_located((By.ID, "user")))
    driver.find_element(By.ID, "user").clear()
    driver.find_element(By.ID, "user").send_keys(WMS_USER)
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys(WMS_PASS)

    driver.find_element(
        By.XPATH, "//button[contains(text(),'Iniciar Sesión')]"
    ).click()
    time.sleep(1)

    # Buscar label del cliente
    # Mapeo de nombres cortos a labels reales del select
    CLIENT_LABELS = {
        "REEBOK": "Reebok / Reebok",
        "ON": "Monte Rosa / Monte Rosa", 
        "PIARENA": "Piarena / Piarena",
    }
    
    target_label = CLIENT_LABELS.get(client_name.upper(), client_name)

    # Seleccionar cliente si aparece
    try:
        sel = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "indexCta"))
        )
        
        # Intentar seleccionar por texto exacto o parcial
        try:
            Select(sel).select_by_visible_text(target_label)
        except:
            # Fallback a búsqueda parcial si falla
            options = Select(sel).options
            matched = False
            for opt in options:
                if client_name.upper() in opt.text.upper():
                    Select(sel).select_by_visible_text(opt.text)
                    matched = True
                    break
            if not matched:
                log.warning(f"No se encontró el cliente {client_name} en la lista.")

        driver.find_element(By.ID, "chooseServerButton").click()
        time.sleep(1)
        log.info(f"Cliente {client_name} seleccionado.")
    except TimeoutException:
        log.info("Sin selector de cliente (ya estaba seleccionado o no aplica).")

    # Esperar que cargue el dashboard principal
    wait.until(EC.presence_of_element_located(
        (By.XPATH, "//*[contains(text(),'Indicadores') or contains(text(),'menú')]")
    ))
    log.info("✅ Login exitoso.")


# ─── Navegación ──────────────────────────────────────────────────────────────

def abrir_menu(driver: webdriver.Chrome, wait: WebDriverWait):
    """Abre el sidebar ≡ menú (esquina superior derecha)."""
    log.info("Abriendo sidebar '≡ menú'...")
    try:
        # Intentar detectar si el link de Entradas ya es visible (sidebar abierto)
        entradas_exist = driver.find_elements(By.XPATH, "//a[contains(.,'Entradas')]")
        if entradas_exist and entradas_exist[0].is_displayed():
            log.info("Sidebar ya se ve abierto.")
            return
    except Exception:
        pass

    try:
        btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'menú') or contains(@class,'navbar-toggler')] | "
                       "//a[contains(.,'menú')] | "
                       "//*[@id='menu-toggle']")
        ))
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(0.5)
        log.info("Sidebar abierto con click JS.")
    except Exception as e:
        log.warning(f"No se pudo abrir menú: {e}")

def click_entradas(driver: webdriver.Chrome, wait: WebDriverWait):
    """Click en la sección 'Entradas' del sidebar."""
    log.info("Click en 'Entradas' del sidebar...")
    try:
        # En GatorWMS, a veces hay que clickear el texto o el icono
        entradas_link = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//a[contains(.,'Entradas') and not(contains(@class,'dropdown-item'))]")
        ))
        driver.execute_script("arguments[0].scrollIntoView(true);", entradas_link)
        driver.execute_script("arguments[0].click();", entradas_link)
        time.sleep(1)
        log.info("Sección Entradas clicada.")
    except Exception as e:
        log.error(f"Error al clickear Entradas: {e}")

def click_reporte_detallado(driver: webdriver.Chrome, wait: WebDriverWait):
    """Click en 'Reporte detallado de documentos de entrada' (ítem 2 del submenú)."""
    log.info("Seleccionando reporte detallado...")
    try:
        # El submenú en GatorWMS a menudo muestra una lista numerada en un modal.
        # Buscamos específicamente el que dice "2. Entradas" o similar.
        reporte = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//a[contains(.,'2. Entradas')] | //li[contains(.,'Reporte detallado')] | //a[contains(.,'Reporte detallado')]")
        ))
        driver.execute_script("arguments[0].scrollIntoView(true);", reporte)
        rand_sleep(1, 2)
        driver.execute_script("arguments[0].click();", reporte)
        time.sleep(1.5)
        log.info("Modal de reporte abierto.")
    except Exception as e:
        log.error(f"Error al abrir reporte detallado: {e}")
        # Intentar fallback por texto exacto si falla el anterior
        try:
            fallback = driver.find_element(By.LINK_TEXT, "2. Entradas")
            driver.execute_script("arguments[0].click();", fallback)
            log.info("Abierto via fallback LINK_TEXT '2. Entradas'.")
        except:
            pass


# ─── Búsqueda y Descarga ─────────────────────────────────────────────────────

def switch_to_reporte_frame(driver: webdriver.Chrome, wait: WebDriverWait):
    """Hace switch al iframe donde carga el modal del reporte de entradas."""
    log.info("Buscando iframe del reporte (con reintentos)...")
    for intento in range(3):
        try:
            time.sleep(1)
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            log.info(f"Intento {intento+1}: Iframes encontrados: {len(iframes)}")

            if len(iframes) == 0:
                # Si no hay iframes, quizás todavía no carga el modal
                continue

            for frame in reversed(iframes):
                try:
                    src = (frame.get_attribute("src") or "").lower()
                    # Apolo Soft-Gator usa full_screen.jsp o reportes en modales
                    if "reporte" in src or "forms" in src or "full_screen" in src:
                        driver.switch_to.frame(frame)
                        log.info(f"✅ Switch a iframe: {src[:60]}")
                        return
                except Exception:
                    continue
        except Exception as e:
            log.warning(f"Error en switch_to_reporte_frame, reintentando: {e}")
            
    log.info("No se encontró iframe específico — operando en contexto principal.")


def ejecutar_busqueda(driver: webdriver.Chrome, wait: WebDriverWait):
    """Click en el botón lupa (Buscar) y espera que carguen los datos."""
    update_status("Seleccionando fecha y buscando...", 30)

    # 0. Esperar a que el overlay de "processing" desaparezca
    log.info("Esperando que desaparezca cualquier overlay blocking...")
    try:
        WebDriverWait(driver, 15).until(
            EC.invisibility_of_element_located((By.ID, "processing"))
        )
    except Exception:
        pass

    # 1. Intentar filtrar por "Semana" (triggers search automatically)
    log.info("Intentando configurar el filtro a 'Semana'...")
    try:
        # Localizar botón de fecha y extraer UUID
        btn_fecha = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//button[starts-with(@id, 'fecha')] | //*[contains(normalize-space(), 'Seleccionar Fecha')]")
        ))
        
        full_id = btn_fecha.get_attribute("id") or ""
        uuid = full_id.replace("fecha", "")
        log.info(f"Botón fecha encontrado. UUID: {uuid}")

        driver.execute_script("arguments[0].scrollIntoView(true);", btn_fecha)
        rand_sleep(1, 2)
        
        # Click para abrir dropdown
        driver.execute_script("arguments[0].click();", btn_fecha)
        log.info("Click en 'Seleccionar Fecha'. Esperando dropdown...")
        rand_sleep(2, 3)
        
        # Seleccionar "Semana" (ID empieza con 'week')
        xpath_semana = f"//a[@id='week{uuid}']" if uuid else "//a[contains(.,'Semana')] | //*[normalize-space()='Semana']"
        
        btn_semana = wait.until(EC.presence_of_element_located((By.XPATH, xpath_semana)))
        driver.execute_script("arguments[0].click();", btn_semana)
        log.info(f"✅ Filtro de fecha configurado en 'Semana'.")
        time.sleep(1.5)
        
    except Exception as e:
        log.warning(f"No se pudo ajustar el filtro de fecha: {e}. Seguimos con el default.")

    # La lupa ya no es necesaria si el WMS dispara al clickear 'Semana'.
    # Si hiciera falta en algún caso, se dejaría como fallback, pero el usuario pide quitarla.
    # log.info("Omitiendo click en lupa (disparado por fecha)...")

    log.info("Esperando resultados...")
    # Esperar a que la tabla o el indicador de carga muestren que hay algo
    try:
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@id, 'pagination')] | //td[contains(@class, 'data')] | //*[contains(@class, 'badge')]")
            )
        )
        log.info("✅ Datos cargados en pantalla.")
    except Exception:
        log.warning("No se detectó cambio claro en el DOM, procedemos a intentar descarga.")

    time.sleep(1)

def descargar_csv(driver: webdriver.Chrome, wait: WebDriverWait) -> list:
    """
    Click en botón CSV → espera a que el archivo aparezca en DOWNLOAD_DIR.
    Usa JS directo porque el overlay #processing bloquea el click() normal.
    """
    update_status("Iniciando descarga CSV...", 50)

    # 1) Esperar a que el overlay #processing desaparezca
    log.info("Esperando que desaparezca el overlay 'processing'...")
    try:
        WebDriverWait(driver, 120).until(
            EC.invisibility_of_element_located((By.ID, "processing"))
        )
        log.info("✅ Overlay desaparecido.")
    except TimeoutException:
        log.warning("Timeout esperando overlay — intentando de todas formas.")

    time.sleep(0.5)

    # 2) Snapshot de archivos antes de la descarga
    antes = set(os.listdir(DOWNLOAD_DIR))

    # 3) Localizar el botón CSV 
    log.info("Localizando botón CSV...")
    try:
        # Intentar localizar CSV con texto exacto o dentro de span
        csv_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//a[normalize-space(.)='CSV' or contains(.,'CSV')] | //button[contains(.,'CSV')]")
        ))
    except Exception:
        log.warning("No se encontró botón CSV por texto, intentando selector genérico...")
        csv_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//*[@id='exportCsv'] | //a[contains(@onclick, 'csv')]")
        ))

    # 4) Ejecutar via JavaScript para evitar el bloqueo del overlay
    log.info("Ejecutando descarga CSV via JavaScript...")
    driver.execute_script("arguments[0].click();", csv_btn)
    log.info("CSV solicitado. Esperando descarga en disco...")

    # Monitorear archivos en disco
    inicio   = time.time()
    timeout  = 600  # 10 minutos máx
    estable  = 0

    while time.time() - inicio < timeout:
        ahora    = set(os.listdir(DOWNLOAD_DIR))
        nuevos   = ahora - antes
        en_curso = [f for f in nuevos if f.endswith(".crdownload") or f.endswith(".tmp")]
        listos   = [f for f in nuevos if not f.endswith(".crdownload") and not f.endswith(".tmp")]

        if listos:
            log.info(f"  Listos: {len(listos)} | En curso: {len(en_curso)}")

        if listos and not en_curso:
            estable += 1
            if estable >= 5:   # 15 s estable sin actividad
                log.info("✅ Descarga estable.")
                break
        else:
            estable = 0

        time.sleep(1)

    archivos = [
        os.path.join(DOWNLOAD_DIR, f)
        for f in (set(os.listdir(DOWNLOAD_DIR)) - antes)
        if not f.endswith(".crdownload") and not f.endswith(".tmp")
    ]
    log.info(f"Archivos descargados: {[os.path.basename(p) for p in archivos]}")
    return archivos


# ─── Procesamiento CSV → Supabase ───────────────────────────────────────────────

def find_col(df, candidates: list):
    """Busca la primera columna que contenga alguno de los nombres candidatos."""
    for name in candidates:
        matches = [c for c in df.columns if name in c]
        if matches:
            return matches[0]
    return None


def process_entradas_csv(file_path: str, client_key: str):
    log.info(f"Procesando {os.path.basename(file_path)}...")
    try:
        df = pd.read_csv(
            file_path,
            encoding="latin-1",
            on_bad_lines="skip",
            dtype=str,
        )
        df.columns = [
            str(c).strip().lower()
                  .replace(" ", "_").replace(":", "").replace(".", "")
            for c in df.columns
        ]

        DATABASE_URL = os.getenv("DATABASE_URL")
        engine = create_engine(DATABASE_URL)
        
        rows_to_insert = []
        count = 0

        for _, row in df.iterrows():
            docto_id = row.get(find_col(df, ["documento_id", "docto_id",
                                               "pedido", "documento", "docto"]), "")

            if str(docto_id).upper().startswith("INVE-"):
                continue

            referencia  = row.get(find_col(df, ["referencia", "ref", "caja"]), "")
            fecha       = row.get(find_col(df, ["fecha", "fecha_creacion",
                                                 "f_alta", "date"]), "")
            sku         = row.get(find_col(df, ["skuright", "sku", "articulo",
                                                 "item", "codigo"]), "")
            descripcion = row.get(find_col(df, ["desc", "descripcion",
                                                 "description", "nombre"]), "")
            cantidad    = row.get(find_col(df, ["cantidad_recibida", "cantidad",
                                                 "piezas", "recibida",
                                                 "cant_recibida", "qty"]), 0)
            tarimas     = row.get(find_col(df, ["tarimas", "pallets",
                                                 "huella", "tarima"]), 0)
            calidad     = row.get(find_col(df, ["calidad", "quality",
                                                 "condicion", "estado_calidad"]), "")

            try:
                cantidad = float(str(cantidad).replace(",", "").replace('"', "").strip())
            except Exception:
                cantidad = 0
            try:
                tarimas = float(str(tarimas).replace(",", "").replace('"', "").strip())
            except Exception:
                tarimas = 0

            rows_to_insert.append({
                "docto_id": str(docto_id),
                "referencia": str(referencia),
                "fecha": str(fecha),
                "sku": str(sku),
                "descripcion": str(descripcion),
                "cantidad": cantidad,
                "tarimas": tarimas,
                "calidad": str(calidad),
                "cliente": client_key.upper()
            })
            count += 1

        if rows_to_insert:
            temp_df = pd.DataFrame(rows_to_insert)
            
            # Lógica de Deduplicación en Supabase (UPSERT)
            # 1. Crear tabla temporal
            with engine.connect() as conn:
                temp_df.to_sql("entradas_temp", engine, if_exists="replace", index=False)
                
                # 2. Upsert: Eliminar si ya existe y luego insertar
                conn.execute(text("""
                    DELETE FROM entradas 
                    WHERE (docto_id, sku, fecha, cliente) IN (
                        SELECT docto_id, sku, fecha, cliente FROM entradas_temp
                    )
                """))
                conn.execute(text("""
                    INSERT INTO entradas (docto_id, referencia, fecha, sku, descripcion, cantidad, tarimas, calidad, cliente)
                    SELECT docto_id, referencia, fecha, sku, descripcion, cantidad, tarimas, calidad, cliente FROM entradas_temp
                """))
                conn.execute(text("DROP TABLE entradas_temp"))
                conn.commit()
                
            log.info(f"  → {count} filas procesadas/sincronizadas para {client_key}.")

    except Exception as e:
        log.error(f"Error procesando CSV {file_path}: {e}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="WMS Entradas Scraper")
    parser.add_argument("--client", default="REEBOK", help="Cliente a procesar (REEBOK, ON, PIARENA, etc.)")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en modo invisible")
    args = parser.parse_args()

    client_key = args.client.upper()

    log.info("═" * 60)
    log.info(f"  WMS Scraper — Modo {'HEADLESS' if args.headless else 'VISIBLE'}")
    log.info(f"  CLIENTE: {client_key}")
    log.info("═" * 60)

    clear_downloads()
    driver = build_driver(headless=args.headless)
    wait   = WebDriverWait(driver, 60)

    user_trigger = os.getenv("TRIGGERED_BY", f"{client_key}_SCRAPER")
    try:
    # log_activity(user_trigger, "SCRAPER_RUN", f"Iniciando scraper de Entradas - {client_key}")
        # ── FASE 1: Login ────────────────────────────────────────────────────
        login(driver, wait, client_key)

        # ── FASE 2: Navegar a Reporte de Entradas ────────────────────────────
        update_status(f"Navegando a Entradas ({client_key})...", 20)
        abrir_menu(driver, wait)
        click_entradas(driver, wait)
        click_reporte_detallado(driver, wait)

        # ── FASE 3: Buscar y Descargar CSV ───────────────────────────────────
        switch_to_reporte_frame(driver, wait)
        ejecutar_busqueda(driver, wait)
        archivos = descargar_csv(driver, wait)

        # ── FASE 4: Procesar y guardar en DB ─────────────────────────────────
        if archivos:
            update_status(f"Procesando {len(archivos)} archivo(s)...", 70)
            log.info(f"✅ {len(archivos)} archivo(s) descargados.")

            for path in archivos:
                process_entradas_csv(path, client_key)

            update_status("Sincronización Completa", 100)
            # log_activity(user_trigger, "SCRAPER_RUN", f"Sincronización Completa ({client_key}): {len(archivos)} archivos.")
            log.info("✅ Todo listo.")
        else:
            log.warning("⚠️ No se descargaron archivos.")
            update_status("Sin archivos — revisa el WMS", 0)
            sys.exit(1)

    except Exception as e:
        log.error(f"Error fatal: {e}", exc_info=True)
        update_status(f"Error: {e}", 0)
        log_activity(user_trigger, "SCRAPER_ERROR", f"Error fatal en {client_key}: {str(e)}", status="ERROR")

        # Screenshot de emergencia (solo si no es headless o depurando)
        try:
            ts  = int(time.time())
            scr = os.path.join(BASE_DIR, f"error_{client_key}_{ts}.png")
            driver.save_screenshot(scr)
            log.info(f"Screenshot de error: {scr}")
        except Exception:
            pass

        sys.exit(1)

    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
