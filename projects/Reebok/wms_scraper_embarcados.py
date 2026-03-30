import os
import time
import json
import logging
import sys
import random
import sqlite3
import pandas as pd
from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent

try:
    from dotenv import load_dotenv
    _root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    load_dotenv(os.path.join(_root, ".env"))
    
    # Añadir raíz al path para importar src
    if _root not in sys.path:
        sys.path.append(_root)
    from src.database import log_activity
except Exception:
    def log_activity(*args, **kwargs): pass # Fallback if import fails

WMS_URL = os.getenv("WMS_URL", "https://apolo.soft-gator.com/gatorwolr/index.jsp")
USER = os.getenv("WMS_USER", "")
PASS = os.getenv("WMS_PASS", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
STATUS_FILE = os.path.join(BASE_DIR, "scraper_status.json")
LOG_FILE = os.path.join(BASE_DIR, "sync_reebok.log")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "data", "wms_data.db")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'), logging.StreamHandler(sys.stdout)])

# Log start of phase
user_trigger = os.getenv("TRIGGERED_BY", "Unknown")
logging.info(f"═══ CONTINUANDO SYNC (Fase 2: Embarcados) - Activado por: {user_trigger} ═══")


def update_status(message, percent):
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump({"message": message, "percent": percent, "status": "running"}, f)
    except Exception as e:
        logging.error(f"Failed to update status: {e}")

def random_sleep(min_s=2, max_s=5):
    time.sleep(random.uniform(min_s, max_s))

def clear_downloads(prefix=""):
    logging.info(f"Clearing download directory for prefix {prefix}...")
    if not os.path.exists(DOWNLOAD_DIR): return
    for f in os.listdir(DOWNLOAD_DIR):
        if prefix and not f.startswith(prefix):
            continue
        file_path = os.path.join(DOWNLOAD_DIR, f)
        try:
            if os.path.isfile(file_path): os.unlink(file_path)
        except Exception:
            pass

def process_surtido_csvs(file_paths):
    logging.info("Intelligently processing Outbound (Surtido) files...")
    all_data = []
    
    for file_path in file_paths:
        if not os.path.exists(file_path): continue
        df = pd.read_csv(file_path, encoding='latin-1', on_bad_lines='skip', dtype=str)
        df.columns = [str(c).strip().lower().replace(' ', '_').replace(':', '').replace('.', '') for c in df.columns]

        # --- VOLCADO RAW DIRECTO A SUPABASE ---
        try:
            from sqlalchemy import create_engine, text
            db_url = os.getenv("DATABASE_URL")
            if db_url:
                tmp_engine = create_engine(db_url)
                with tmp_engine.begin() as conn:
                    df.to_sql("inbound_scord_despachados_raw", conn, if_exists="replace", index=False)
                logging.info(f"Volcado RAW a inbound_scord_despachados_raw completado ({len(df)} filas).")
        except Exception as e:
            logging.error(f"Error volcando RAW a inbound_scord_despachados_raw: {e}")
        # --------------------------------------

        def find_col(possible_names):
            # Prioritize exact match to avoid picking up 'fecha_cancelacion' when looking for 'fecha'
            for name in possible_names:
                if name in df.columns:
                    return name
            # Only if no exact match, look for partial match (carefully)
            for name in possible_names:
                matches = [c for c in df.columns if name in c and 'cancelacion' not in c]
                if matches: return matches[0]
            return None

        # Procesar filas
        for index, row in df.iterrows():
            docto_id = row.get(find_col(['documento_id', 'docto_id', 'pedido', 'documento', 'orden', 'docto']), '')
            referencia = row.get(find_col(['referencia', 'ref']), '')
            fecha_raw = str(row.get(find_col(['fecha', 'f_alta', 'date']), ''))
            fecha_entrega_raw = str(row.get(find_col(['fecha_entrega', 'entrega', 'deadline', 'entregar']), ''))
            
            # EXTRAER RAW COLUMNA H (0-indexed pos 7) - No importa si hay espacios
            try: 
                val_h = row.iloc[7]
                cliente = str(val_h) if not pd.isna(val_h) else ""
            except: 
                cliente = ""
                
            cant_pedida = row.get(find_col(['cantidad_pedida', 'qty', 'pedida', 'piezas', 'cantidad']), 0)
            cant_surtida = row.get(find_col(['cantidad_surtida', 'surtida', 'atendida']), 0)
            tarimas = row.get(find_col(['tarimas', 'pallets', 'huella', 'tarima']), 0)
            estado = row.get(find_col(['estado', 'status']), '')
            fill_rate = row.get(find_col(['tasa_de_cumplimiento', 'avance', 'fill_rate', 'progreso']), 0)

            # Skip dummy records
            if str(referencia).upper().startswith('INV'):
                continue

            try: cant_pedida = float(str(cant_pedida).replace(',', '').replace('"', '').strip())
            except: cant_pedida = 0
            try: cant_surtida = float(str(cant_surtida).replace(',', '').replace('"', '').strip())
            except: cant_surtida = 0
            try: tarimas = float(str(tarimas).replace(',', '').replace('"', '').strip())
            except: tarimas = 0
            # Calculate Fill Rate: (surtida / pedida) * 100
            if cant_pedida > 0:
                fill_rate = round((cant_surtida / cant_pedida) * 100, 1)
            else:
                fill_rate = 0.0

            # Date formatting (como lo hacia unificador.py pero robusto)
            fecha = ''
            hora = ''
            if fecha_raw and fecha_raw.lower() != 'nan' and fecha_raw != 'None':
                try:
                    fecha_dt = pd.to_datetime(fecha_raw, errors='coerce')
                    if not pd.isna(fecha_dt):
                        fecha = fecha_dt.strftime('%Y-%m-%d')
                        hora = fecha_dt.strftime('%H:%M:%S')
                    else:
                        fecha = fecha_raw
                except:
                    fecha = fecha_raw
            
            fecha_entrega = ''
            if fecha_entrega_raw and fecha_entrega_raw.lower() != 'nan' and fecha_entrega_raw != 'None':
                try:
                    fe_dt = pd.to_datetime(fecha_entrega_raw, errors='coerce')
                    if not pd.isna(fe_dt):
                        fecha_entrega = fe_dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        fecha_entrega = fecha_entrega_raw
                except:
                    fecha_entrega = fecha_entrega_raw

            all_data.append({
                'docto_id': str(docto_id).replace('nan',''),
                'referencia': str(referencia).replace('nan',''),
                'cliente': str(cliente).replace('nan','').upper(),
                'fecha': fecha,
                'hora': hora,
                'fecha_entrega': fecha_entrega,
                'cantidad_pedida': cant_pedida,
                'cantidad_surtida': cant_surtida,
                'tarimas': tarimas,
                'estado': str(estado).replace('nan',''),
                'fill_rate': fill_rate
            })

    if all_data:
        final_df = pd.DataFrame(all_data)
        final_df.drop_duplicates(inplace=True)
        try:
            from sqlalchemy import create_engine, text
            DATABASE_URL = os.getenv("DATABASE_URL")
            engine = create_engine(DATABASE_URL)
            
            # if_exists="replace" for temporary table, then UPSERT into final 'surtido'
            with engine.connect() as conn:
                final_df.to_sql("surtido_temp", engine, if_exists="replace", index=False)
                
                # Deduplicación basada en docto_id, fecha y hora (para permitir múltiples actualizaciones del mismo día)
                conn.execute(text("""
                    DELETE FROM surtido 
                    WHERE (docto_id, fecha, hora, cliente) IN (
                        SELECT docto_id, fecha, hora, cliente FROM surtido_temp
                    )
                """))
                
                # Insertar nuevos/actualizados
                conn.execute(text("""
                    INSERT INTO surtido (docto_id, referencia, cliente, fecha, hora, fecha_entrega, cantidad_pedida, cantidad_surtida, tarimas, estado, fill_rate)
                    SELECT docto_id, referencia, cliente, fecha, hora, fecha_entrega, cantidad_pedida, cantidad_surtida, tarimas, estado, fill_rate FROM surtido_temp
                """))
                
                conn.execute(text("DROP TABLE surtido_temp"))
                conn.commit()
                
            logging.info(f"Loaded/Merged {len(final_df)} rows to 'surtido' in Supabase.")
        except Exception as e:
            logging.error(f"Database error: {e}")

def login(page):
    update_status("Iniciando sesión (Finalizados)...", 10)
    logging.info("Navigating to Login Page...")
    page.goto(WMS_URL)
    page.locator("#user").wait_for(state="visible", timeout=15000)
    page.locator("#user").fill(USER)
    page.locator("#password").fill(PASS)
    page.locator("xpath=//button[contains(text(), 'Iniciar Sesión')]").click()
    try:
        client_select = page.locator("#indexCta")
        client_select.wait_for(state="visible", timeout=10000)
        client_select.select_option(label="Reebok / Reebok")
        page.locator("#chooseServerButton").click()
    except:
        pass
    page.locator("#menu").wait_for(state="attached", timeout=30000)
    logging.info("Login Successful.")

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    with sync_playwright() as p:
        headless_mode = os.getenv("DOCKER_ENV") == "1"
        try:
            ua = UserAgent()
            user_agent = ua.random
        except:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        browser = p.chromium.launch(
            headless=headless_mode,
            args=["--start-maximized", "--disable-gpu", "--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(user_agent=user_agent, accept_downloads=True, no_viewport=True)
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        page = context.new_page()

        try:
            user_trigger = os.getenv("TRIGGERED_BY", "REEBOK_SCRAPER")
            log_activity(user_trigger, "SCRAPER_RUN", "Iniciando scraper de Embarcados Reebok")
            clear_downloads("OUTBOUND-")
            login(page)

            POOL_ID_SURTIDO = "e352a00c-66df-438e-b1bc-55ff8610918d"

            # ── Paso 1: Abrir la pantalla de Surtido ──
            update_status("Navegando al menú Surtido...", 15)
            logging.info(f"Opening 'Surtido' screen ({POOL_ID_SURTIDO})...")
            # ── Paso 2: Ir a Embarcados (Navegación robusta) ──
            update_status("Cambiando vista a Embarcados...", 30)
            logging.info("Attempting to switch to 'Embarcados' view...")

            # 1. Asegurar que el pool esté abierto
            page.evaluate(f"getPool({{screen:'{POOL_ID_SURTIDO}'}});")
            random_sleep(3, 5)

            nav_success = False
            for attempt in range(2):
                try:
                    logging.info(f"Navigation attempt {attempt+1}...")
                    
                    # Clic manual en el dropdown
                    page.locator(f"#btnAction{POOL_ID_SURTIDO}").click(force=True)
                    random_sleep(1, 2)
                    
                    # Estrategia 1: Clic manual si el link es visible
                    embarque_link = page.locator(f'a.dropdown-item[id^="embarque"]').first
                    if embarque_link.is_visible():
                        embarque_link.click(force=True)
                        logging.info("Clicked Embarcados link manually.")
                    else:
                        # Estrategia 2: Fallback JS directo si no es visible
                        logging.info("Link not visible, trying direct JS navigation...")
                        page.evaluate(f"""
                            accioname({{
                                "icono": "fas fa-shipping-fast",
                                "accion": "muestrame",
                                "nombre": "Shipped",
                                "pagina": "1",
                                "accionId": "embarque",
                                "condiciones": ["surtido.por.cuenta", "salida.enc.embarcados"]
                            }}, "{POOL_ID_SURTIDO}");
                        """)
                    
                    random_sleep(5, 8)
                    btn_text = page.locator(f"#btnAction{POOL_ID_SURTIDO}").inner_text()
                    if any(x in btn_text for x in ["Embarcados", "Shipped", "Enviado", "Embarque"]):
                        logging.info("Navigation to Embarcados confirmed.")
                        nav_success = True
                        break
                        
                except Exception as e:
                    logging.error(f"Navigation attempt {attempt+1} error: {e}")
                    random_sleep(2, 4)

            # Clic en la Lupa (Search) para asegurar que carguen los datos
            search_btn_xpath = f"xpath=//button[contains(@onclick, 'searchMe') and contains(@onclick, '{POOL_ID_SURTIDO}')]"
            try:
                # Intentamos buscar el botón de búsqueda que tenga el icono de lupa
                search_btn = page.locator(f"div#{POOL_ID_SURTIDO} button i.fa-search").locator("..")
                if search_btn.is_visible():
                    search_btn.click(force=True)
                    logging.info("Search button clicked (Lupa).")
                    random_sleep(5, 7)
            except:
                pass

            # ── Paso 3: Esperar a que la tabla de Embarcados cargue ──
            update_status("Esperando datos de Embarcados...", 50)
            try:
                page.wait_for_selector(f"div#{POOL_ID_SURTIDO} table tbody tr", timeout=30000)
                logging.info("Embarcados table rows detected.")
            except:
                logging.warning("Table rows not detected, but will try download anyway.")

            # ── Paso 4: Descargar CSV de Embarcados ──
            update_status("Descargando CSV de Embarcados...", 70)
            embarcados_path = None
            download_done = False
            
            for dl_attempt in range(2):
                try:
                    logging.info(f"Download attempt {dl_attempt+1}...")
                    
                    # Selectores combinados para el botón CSV
                    target_btn = page.locator(f"a.nav-link[onclick*='obtenMiCSV'][onclick*='{POOL_ID_SURTIDO}']").first
                    
                    if target_btn.is_visible():
                        with page.expect_download(timeout=90000) as download_info:
                            target_btn.click(force=True)
                        download = download_info.value
                        embarcados_path = os.path.join(DOWNLOAD_DIR, f"OUTBOUND-embarcados-{int(time.time())}.csv")
                        download.save_as(embarcados_path)
                        logging.info(f"CSV saved via click: {embarcados_path}")
                        download_done = True
                        break
                    else:
                        logging.info("CSV button not found or invisible, trying JS download...")
                        with page.expect_download(timeout=60000) as download_info:
                            page.evaluate(f"""
                                accioname({{"icono": "fa fa-file-excel-o ", "accion": "obtenMiCSV", "nombre": "CSV"}}, "{POOL_ID_SURTIDO}");
                            """)
                        download = download_info.value
                        embarcados_path = os.path.join(DOWNLOAD_DIR, f"OUTBOUND-JS-{int(time.time())}.csv")
                        download.save_as(embarcados_path)
                        logging.info(f"CSV saved via JS: {embarcados_path}")
                        download_done = True
                        break
                        
                except Exception as e:
                    logging.error(f"Download attempt {dl_attempt+1} failed: {e}")
                    random_sleep(3, 5)

            # ── Paso 5: Procesar y guardar en BD ──
            update_status("Procesando datos...", 90)
            if download_done and embarcados_path and os.path.exists(embarcados_path):
                process_surtido_csvs([embarcados_path])
            else:
                logging.error("Failed to acquire Embarcados file.")

            update_status("Fase 2 completada", 100)
            log_activity(user_trigger, "SCRAPER_RUN", "Sincronización Completa de Embarcados Reebok")
            logging.info("Phase 2 finished.")

        except Exception as e:
            logging.error(f"Script failed: {e}")
            update_status("Error en Fase 2", 0)
            log_activity(user_trigger, "SCRAPER_ERROR", f"Error fatal en Embarcados Reebok: {str(e)}", status="ERROR")
            sys.exit(1)
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()

