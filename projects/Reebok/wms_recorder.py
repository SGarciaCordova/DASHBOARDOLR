from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

def record_session():
    print("🚀 Iniciando navegador (Standard Selenium)...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    # options.add_argument("--headless") # Commented out for visibility
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"❌ Error al iniciar Chrome: {e}")
        return

    try:
        url = "https://apolo.soft-gator.com/gatorwolr/index.jsp"
        print(f"🌐 Navegando a: {url}")
        driver.get(url)
        
        print("\n🔑 **Credenciales (Solo referencia)**:")
        print("Usuario: scordova")
        print("Pass:    scordova123")
        
        print("\n🛑 **INSTRUCCIONES**:")
        print("1. Inicia sesión manualmente.")
        print("2. Navega hasta el reporte deseado.")
        print("3. Cuando quieras una captura, avísame (crearé el archivo 'CAPTURE').")
        print("4. Para terminar la sesión, crearé el archivo 'EXIT'.")
        
        capture_count = 1
        trigger_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CAPTURE")
        exit_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "EXIT")
        
        if os.path.exists(trigger_file): os.remove(trigger_file)
        if os.path.exists(exit_file): os.remove(exit_file)
            
        print(f"⏳ Esperando acciones (CAPTURE para foto, EXIT para salir)...")
        
        while not os.path.exists(exit_file):
            if os.path.exists(trigger_file):
                print(f"\n📸 Capturando estado #{capture_count}...")
                timestamp = int(time.time())
                
                # Capture Screenshot
                scr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"wms_debug_{capture_count}_{timestamp}.png")
                driver.save_screenshot(scr_path)
                print(f"✅ Screenshot guardado: {scr_path}")
                
                # Capture HTML
                html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"wms_source_{capture_count}_{timestamp}.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f"✅ Código fuente guardado: {html_path}")
                
                print(f"🔗 URL Actual: {driver.current_url}")
                
                # Clean up trigger
                os.remove(trigger_file)
                capture_count += 1
                print(f"⏳ Esperando siguiente acción...")
            
            time.sleep(1)
            
        if os.path.exists(exit_file):
            os.remove(exit_file)
        print("\nCerrando navegador...")
        
    except Exception as e:
        print(f"Error durante la sesión: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    record_session()

