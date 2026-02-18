from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

WMS_URL = "https://apolo.soft-gator.com/gatorwolr/index.jsp"

def capture_login():
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(WMS_URL)
        time.sleep(5)
        with open("login_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Login page captured.")
    finally:
        driver.quit()

if __name__ == "__main__":
    capture_login()
