from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

WMS_URL = "https://apolo.soft-gator.com/gatorwolr/index.jsp"
USER = "scordova"
PASS = "scordova123"

def capture_client_select():
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(WMS_URL)
        
        # Login
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "user"))).send_keys(USER)
        driver.find_element(By.ID, "password").send_keys(PASS)
        driver.find_element(By.XPATH, "//button[contains(text(), 'Iniciar Sesión')]").click()
        
        # Wait for login processing
        time.sleep(5) 
        
        # Check if we are redirected to choose_server, or navigate manually
        current_url = driver.current_url
        print(f"URL after login: {current_url}")
        
        # Explicitly go to choose_server if not there
        if "choose_server.jsp" not in current_url:
            driver.get("https://apolo.soft-gator.com/gatorwolr/forms/choose_server.jsp")
            time.sleep(3)
            
        with open("choose_server.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("choose_server.html captured.")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    capture_client_select()
