def ejecutar_extraccion():

    import os
    import time
    import re
    import base64  
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException

    # --- CONFIGURACIÓN PARA ASIGNACIÓN DE PÁGINAS---
    PAGINA_INICIO = 1  
    PAGINA_FIN = 21
    # ----------------------------------------------

    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.* && rm -rf /tmp/.org.chromium.Chromium.*")
    print(f"Entorno virtual listo. Asignación Mitula: Páginas {PAGINA_INICIO} a la {PAGINA_FIN}.")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0")

    catalogo_urls = []
    datos_finales = []

    driver = None

    try:
        driver = webdriver.Chrome(options=options)
        url_base = "https://casas.mitula.cl/find?operationType=rent&propertyType=apartment&geoId=R231672"

        # ==============================================================================
        # FASE 1: RECOLECCIÓN
        # ==============================================================================
        for pagina_actual in range(PAGINA_INICIO, PAGINA_FIN + 1):
            print(f"\n--- [FASE 1] Procesando Página {pagina_actual} ---")

            url_pagina = f"{url_base}&page={pagina_actual}"
            driver.get(url_pagina)

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.listing-card"))
                )

                for _ in range(4):
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1)

                bloques = driver.find_elements(By.CSS_SELECTOR, "article.listing-card")

                for bloque in bloques:
                    try:
                        listing_id = bloque.get_attribute("data-listingid")
                        if not listing_id:
                            continue

                        texto_tarjeta = bloque.get_attribute("textContent").lower()

                        if "coquimbo" in texto_tarjeta:
                            ubicacion = "Coquimbo"
                        elif "la serena" in texto_tarjeta:
                            ubicacion = "La Serena"
                        else:
                            continue

                        url = "Sin URL"
                        try:
                            codigo_secreto = bloque.get_attribute("data-clickdestination")
                            if codigo_secreto:
                                url_decodificada = base64.b64decode(codigo_secreto).decode('utf-8', errors='ignore')
                                url = "https://casas.mitula.cl" + url_decodificada
                            else:
                                url = f"https://casas.mitula.cl/propiedad_id_{listing_id}"
                        except:
                            pass

                        if url == "Sin URL" or "javascript" in url:
                            continue

                        try:
                            precio_texto = bloque.find_element(By.CSS_SELECTOR, ".price__actual").text
                            v_limpio = precio_texto.replace("$", "").replace("/mes", "").replace(".", "").replace(",", "").strip()
                            precio = float(v_limpio) if v_limpio.isdigit() else 0.0
                        except:
                            precio = 0.0

                        if precio == 0.0:
                            continue

                        m2, dormitorios, banos = 0, 0, 0

                        match_m2 = re.search(r'(\d+)\s*(m2|m²|mts)', texto_tarjeta)
                        if match_m2:
                            m2 = int(match_m2.group(1))

                        match_dorm = re.search(r'(\d+)\s*dormitorio', texto_tarjeta)
                        if match_dorm:
                            dormitorios = int(match_dorm.group(1))

                        match_bano = re.search(r'(\d+)\s*baño', texto_tarjeta)
                        if match_bano:
                            banos = int(match_bano.group(1))

                        catalogo_urls.append({
                            "responsable": "Constanza Torres",
                            "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "listing_id": listing_id,
                            "titulo": "Departamento Mit",
                            "ubicacion": ubicacion,
                            "m2": m2,
                            "precio": precio,
                            "dormitorios": dormitorios,
                            "baños": banos,
                            "url": url
                        })

                    except:
                        continue

            except TimeoutException:
                continue

        print(f"\nCatálogo listo: {len(catalogo_urls)} propiedades encontradas.")

        # ==============================================================================
        # FASE 2
        # ==============================================================================
        for propiedad in catalogo_urls:

            propiedad["estacionamiento"] = 0
            propiedad["piscina"] = 0
            propiedad["quincho"] = 0
            propiedad["terraza"] = 0
            propiedad["gimnasio"] = 0
            propiedad["lavanderia"] = 0

            try:
                driver.get(propiedad["url"])
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                texto_total = driver.find_element(By.TAG_NAME, "body").text.lower()

                if "estacionamiento" in texto_total:
                    propiedad["estacionamiento"] = 1
                if "piscina" in texto_total:
                    propiedad["piscina"] = 1
                if "quincho" in texto_total:
                    propiedad["quincho"] = 1
                if "terraza" in texto_total:
                    propiedad["terraza"] = 1
                if "gimnasio" in texto_total:
                    propiedad["gimnasio"] = 1
                if "lavander" in texto_total:
                    propiedad["lavanderia"] = 1

            except:
                pass

            datos_finales.append(propiedad)

    except Exception as e:
        print(f"Error crítico en Selenium: {e}")

    finally:
        if driver:
            driver.quit()

    print(f"\nExtracción finalizada. Total: {len(datos_finales)} propiedades.")

    return datos_finales