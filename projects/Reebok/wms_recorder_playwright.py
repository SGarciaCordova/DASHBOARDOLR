"""
wms_recorder_playwright.py
─────────────────────────
Graba una sesión manual en el WMS de Reebok usando Playwright.
- Abre un navegador en modo VISIBLE para que tú navegues manualmente.
- Graba VIDEO de toda la sesión.
- Toma screenshots automáticos cada 10 segundos.
- Captura HTML source cuando presionas ENTER en la consola.
- Guarda todo en: projects/Reebok/recordings/

Uso:
    python wms_recorder_playwright.py

Controles en consola:
    ENTER       → Captura screenshot + HTML manualmente
    q + ENTER   → Termina la grabación y guarda el video
"""

import os
import sys
import time
import threading
import json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

try:
    from dotenv import load_dotenv
    _root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    load_dotenv(os.path.join(_root, ".env"))
except Exception:
    pass

WMS_URL  = os.getenv("WMS_URL",  "https://apolo.soft-gator.com/gatorwolr/index.jsp")
WMS_USER = os.getenv("WMS_USER", "")
WMS_PASS = os.getenv("WMS_PASS", "")

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
RECORDING_DIR = os.path.join(BASE_DIR, "recordings")
os.makedirs(RECORDING_DIR, exist_ok=True)

SESSION_ID  = datetime.now().strftime("%Y%m%d_%H%M%S")
SESSION_DIR = os.path.join(RECORDING_DIR, SESSION_ID)
os.makedirs(SESSION_DIR, exist_ok=True)

# Carpeta de descargas → Windows Downloads para que el usuario las vea directamente
WINDOWS_DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")

# ─────────────────────────────────────────────────────────────────────────────

should_exit   = False
capture_count = 0
page_ref      = None

def capture_state(label="manual"):
    """Captura screenshot + HTML source de la página actual."""
    global capture_count, page_ref
    if page_ref is None:
        return
    capture_count += 1
    ts   = datetime.now().strftime("%H%M%S")
    name = f"{capture_count:03d}_{ts}_{label}"

    # Screenshot
    scr_path = os.path.join(SESSION_DIR, f"{name}.png")
    try:
        page_ref.screenshot(path=scr_path, full_page=True)
        print(f"  📸 Screenshot: {os.path.basename(scr_path)}")
    except Exception as e:
        print(f"  ⚠️  Screenshot falló: {e}")

    # HTML source
    html_path = os.path.join(SESSION_DIR, f"{name}.html")
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page_ref.content())
        print(f"  📄 HTML:       {os.path.basename(html_path)}")
    except Exception as e:
        print(f"  ⚠️  HTML falló: {e}")

    # URL actual
    try:
        print(f"  🔗 URL:        {page_ref.url}")
    except:
        pass

def auto_capture_loop():
    """Captura automática cada 15 segundos."""
    while not should_exit:
        time.sleep(15)
        if not should_exit:
            capture_state("auto")

def input_loop():
    """Maneja la entrada del usuario en la consola."""
    global should_exit
    print("\n" + "═"*60)
    print("  CONTROLES:")
    print("  ENTER     → Captura manual de screenshot + HTML")
    print("  q + ENTER → Terminar grabación")
    print("═"*60 + "\n")

    while not should_exit:
        try:
            cmd = input().strip().lower()
            if cmd == "q":
                should_exit = True
                print("\n⏹️  Finalizando grabación...")
                break
            else:
                print(f"\n{'─'*40}")
                print(f"📸 Captura #{capture_count + 1}...")
                capture_state("manual")
                print(f"{'─'*40}\n")
        except (EOFError, KeyboardInterrupt):
            should_exit = True
            break

# ─────────────────────────────────────────────────────────────────────────────

def main():
    global page_ref, should_exit

    print("═"*60)
    print("  🎥 WMS Reebok — Grabador de Sesión (Playwright)")
    print(f"  📁 Guardando en: {SESSION_DIR}")
    print("═"*60)
    print(f"\n  URL WMS : {WMS_URL}")
    if WMS_USER:
        print(f"  Usuario : {WMS_USER}")
    print(f"  📥 Descargas → {WINDOWS_DOWNLOADS}")
    print("\n  Abriendo navegador...")

    with sync_playwright() as p:
        # ── Perfil Chrome: forzar descargas a Windows Downloads ──────────────
        profile_dir = os.path.join(SESSION_DIR, "profile")
        profile_default = os.path.join(profile_dir, "Default")
        os.makedirs(profile_default, exist_ok=True)
        prefs = {
            "download": {
                "default_directory": WINDOWS_DOWNLOADS,
                "prompt_for_download": False,
                "directory_upgrade": True,
            },
            "savefile": {"default_directory": WINDOWS_DOWNLOADS},
            "profile": {
                "default_content_setting_values": {"automatic_downloads": 1},
                "default_content_settings": {"multiple-automatic-downloads": 1},
            }
        }
        import json as _json
        with open(os.path.join(profile_default, "Preferences"), "w") as pf:
            pf.write(_json.dumps(prefs))

        # Contexto con grabación de video
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            record_video_dir=SESSION_DIR,
            record_video_size={"width": 1400, "height": 900},
            viewport={"width": 1400, "height": 900},
            args=[
                "--start-maximized",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-popup-blocking",
                "--disable-notifications",
            ],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page_ref = page

        # Ir al WMS
        print(f"  🌐 Navegando a {WMS_URL} ...")
        page.goto(WMS_URL, wait_until="domcontentloaded")

        # Auto-login si hay credenciales
        if WMS_USER and WMS_PASS:
            print("  🔑 Aplicando credenciales del .env...")
            try:
                page.locator("#user").wait_for(state="visible", timeout=10000)
                page.locator("#user").fill(WMS_USER)
                page.locator("#password").fill(WMS_PASS)
                page.locator("xpath=//button[contains(text(), 'Iniciar Sesión')]").click()
                print("  ✅ Login ejecutado — revisa el navegador")
                time.sleep(3)
                # Seleccionar cliente Reebok si aparece
                try:
                    client_select = page.locator("#indexCta")
                    client_select.wait_for(state="visible", timeout=8000)
                    client_select.select_option(label="Reebok / Reebok")
                    page.locator("#chooseServerButton").click()
                    print("  ✅ Cliente Reebok seleccionado")
                except:
                    pass
            except Exception as e:
                print(f"  ⚠️  Login automático falló ({e}) — inicia sesión manualmente")
        else:
            print("  ⚠️  No hay credenciales en .env — inicia sesión manualmente en el navegador")

        # Captura inicial
        time.sleep(3)
        capture_state("inicio")

        print("\n  ✅ ¡Navegador listo! Realiza tu flujo en el browser.")
        print("  Graba el proceso de descarga de Entradas como lo haces normalmente.\n")

        # Hilos de background
        auto_thread  = threading.Thread(target=auto_capture_loop,  daemon=True)
        input_thread = threading.Thread(target=input_loop,          daemon=False)
        auto_thread.start()
        input_thread.start()

        # Esperar a que el usuario termine
        input_thread.join()

        # Captura final antes de cerrar
        print("\n  📸 Captura final...")
        capture_state("final")
        time.sleep(1)

        context.close()

    # Generar resumen de sesión
    summary = {
        "session_id":  SESSION_ID,
        "session_dir": SESSION_DIR,
        "captures":    capture_count,
        "wms_url":     WMS_URL,
        "timestamp":   datetime.now().isoformat(),
    }
    summary_path = os.path.join(SESSION_DIR, "session_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'═'*60}")
    print(f"  🎬 Grabación finalizada")
    print(f"  📁 Sesión guardada en: {SESSION_DIR}")
    print(f"  📸 Capturas totales: {capture_count}")
    print(f"  🎥 Video: busca el archivo .webm dentro de la carpeta")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
