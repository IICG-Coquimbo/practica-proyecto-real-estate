import os
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def ejecutar_extraccion():
    PAGINA_INICIO = 2
    PAGINA_FIN = 2

    catalogo_urls = []
    datos_finales = []
    driver = None

    try:
        os.environ["DISPLAY"] = ":99"
        os.system("pkill -9 chrome")
        os.system("pkill -9 chromedriver")
        os.system("rm -rf /tmp/.com.google.Chrome.*")
        os.system("rm -rf /tmp/.org.chromium.Chromium.*")
        print(f"🧹 Entorno virtual listo. Asignación: Páginas {PAGINA_INICIO} a la {PAGINA_FIN}.")

        options = Options()
        options.binary_location = "/usr/bin/google-chrome"
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        )

        driver = webdriver.Chrome(options=options)

        url_base = "https://www.portalinmobiliario.com/arriendo/departamento/la-serena-coquimbo"

        for pagina_actual in range(PAGINA_INICIO, PAGINA_FIN + 1):
            print(f"\n--- [FASE 1] Recolectando enlaces de la Página {pagina_actual} ---")

            if pagina_actual == 1:
                url_pagina = url_base
            else:
                desde = ((pagina_actual - 1) * 48) + 1
                url_pagina = f"{url_base}_Desde_{desde}_NoIndex_True"

            driver.get(url_pagina)

            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ui-search-layout__item"))
            )

            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1)

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            bloques = driver.find_elements(By.CSS_SELECTOR, ".ui-search-layout__item")

            for bloque in bloques:
                try:
                    url = bloque.find_element(By.TAG_NAME, "a").get_attribute("href").split("#")[0].split("?")[0]
                    titulo = bloque.find_element(
                        By.CSS_SELECTOR, ".poly-component__title"
                    ).get_attribute("textContent").strip()

                    ubicacion_cruda = bloque.find_element(
                        By.CSS_SELECTOR, ".poly-component__location"
                    ).get_attribute("textContent").strip()
                    ubi_minuscula = ubicacion_cruda.lower()

                    if "la serena" in ubi_minuscula:
                        ubicacion = "La Serena"
                    else:
                        continue

                    try:
                        p_text = bloque.find_element(
                            By.CSS_SELECTOR, ".poly-price__current"
                        ).get_attribute("textContent")
                    except:
                        p_text = bloque.find_element(
                            By.CSS_SELECTOR, ".poly-component__price"
                        ).get_attribute("textContent")

                    v_limpio = (
                        p_text.replace("$", "")
                        .replace(".", "")
                        .replace(",", "")
                        .replace("\n", "")
                        .strip()
                    )

                    precio = float(v_limpio) if v_limpio.isdigit() else 0.0

                    if url and precio > 0:
                        catalogo_urls.append({
                            "url": url,
                            "titulo": titulo,
                            "ubicacion": ubicacion,
                            "precio": precio
                        })
                except:
                    continue

        print(f"Catálogo listo: {len(catalogo_urls)} propiedades encontradas.")

        for i, propiedad in enumerate(catalogo_urls):
            print(f"[{i+1}/{len(catalogo_urls)}] Inspeccionando: {propiedad['titulo'][:30]}...")

            registro = {
                "identificador": propiedad["titulo"],
                "valor": propiedad["precio"],
                "ubicacion": propiedad["ubicacion"],
                "m2": 0,
                "dormitorios": 0,
                "banos": 0,
                "estacionamiento": 0,
                "piscina": 0,
                "quincho": 0,
                "terraza": 0,
                "gimnasio": 0,
                "lavanderia": 0,
                "url": propiedad["url"],
                "grupo": "RealEstate",
                "integrante": "melany-torres",
                "fecha_captura": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            try:
                driver.get(propiedad["url"])

                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-pdp-collapsable__container"))
                )

                filas_tabla = driver.find_elements(By.CSS_SELECTOR, ".andes-table__row")

                for fila in filas_tabla:
                    texto_fila = fila.get_attribute("textContent").lower()

                    if "superficie total" in texto_fila:
                        nums = re.findall(r"\d+", texto_fila)
                        if nums:
                            registro["m2"] = int(nums[0])

                    elif "dormitorios" in texto_fila:
                        nums = re.findall(r"\d+", texto_fila)
                        if nums:
                            registro["dormitorios"] = int(nums[0])

                    elif "baños" in texto_fila:
                        nums = re.findall(r"\d+", texto_fila)
                        if nums:
                            registro["banos"] = int(nums[0])

                    elif "estacionamiento" in texto_fila:
                        nums = re.findall(r"\d+", texto_fila)
                        if nums and int(nums[0]) > 0:
                            registro["estacionamiento"] = int(nums[0])
                        elif "sí" in texto_fila or "si" in texto_fila:
                            registro["estacionamiento"] = 1

                    elif "piscina" in texto_fila and "sí" in texto_fila:
                        registro["piscina"] = 1
                    elif "quincho" in texto_fila and "sí" in texto_fila:
                        registro["quincho"] = 1
                    elif "terraza" in texto_fila and "sí" in texto_fila:
                        registro["terraza"] = 1
                    elif "gimnasio" in texto_fila and "sí" in texto_fila:
                        registro["gimnasio"] = 1
                    elif "lavander" in texto_fila and "sí" in texto_fila:
                        registro["lavanderia"] = 1

                datos_finales.append(registro)

            except Exception:
                datos_finales.append(registro)

            time.sleep(2)

    except Exception as e:
        print(f"Error crítico en Selenium: {e}")

    finally:
        if driver is not None:
            try:
                driver.quit()
                print("\nNavegador cerrado.")
            except:
                pass

    return datos_finales