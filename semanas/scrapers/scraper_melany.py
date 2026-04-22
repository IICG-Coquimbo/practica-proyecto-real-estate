import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def ejecutar_extraccion():
    datos_finales = []
    driver = None

    try:
        # LIMPIEZA
        os.system("pkill -9 chrome")
        os.system("pkill -9 chromedriver")

        # CONFIGURACIÓN
        options = Options()
        options.binary_location = "/usr/bin/google-chrome"
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0")

        driver = webdriver.Chrome(options=options)

        # URL
        url = "https://www.portalinmobiliario.com/arriendo/departamento/coquimbo-coquimbo"
        driver.get(url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ui-search-layout__item"))
        )

        # Scroll
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        bloques = driver.find_elements(By.CSS_SELECTOR, ".ui-search-layout__item")

        # SCRAPING
        for b in bloques:
            try:
                titulo = b.find_element(By.CSS_SELECTOR, ".poly-component__title").text
                precio_texto = b.find_element(By.CSS_SELECTOR, ".poly-component__price").text

                if not titulo or not precio_texto:
                    continue

                precio_limpio = precio_texto.replace("$", "").replace(".", "").strip()
                valor = float(precio_limpio) if precio_limpio.isdigit() else 0.0

                registro = {
                    "identificador": titulo.strip(),
                    "valor": valor,
                    "grupo": "RealEstate",
                    "integrante": "Melany"
                }

                datos_finales.append(registro)

            except:
                continue

    except Exception as e:
        print("Error:", e)

    finally:
        if driver:
            driver.quit()

    return datos_finales