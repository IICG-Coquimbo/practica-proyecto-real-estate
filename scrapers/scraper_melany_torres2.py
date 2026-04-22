# ==============================================================================
# PROYECTO BIG DATA - GRUPO 2 (REAL ESTATE)
# Módulo Estandarizado: scraper_millaray.py (Capítulo 8)
# Estandarización para integración con Spark y MongoDB Atlas
# ==============================================================================

import os
import time
import re
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def ejecutar_extraccion():

    # --- CONFIGURACIÓN PÁGINAS A SCRAPEAR ---
    PAGINA_INICIO = 12
    PAGINA_FIN = 12
    CANTIDAD_A_EXTRAER = 20
    INVERTIR_ORDEN = False  

    # --- LIMPIEZA Y ENTORNO ---
    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.* && rm -rf /tmp/.org.chromium.Chromium.*")

    print(f"Entorno listo. Procesando Pág {PAGINA_INICIO} | Segmento: Primeras {CANTIDAD_A_EXTRAER} tarjetas.")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    # ANTI-BOT Nivel 1:
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.experimental_options["excludeSwitches"] = ["enable-automation"]
    options.experimental_options["useAutomationExtension"] = False

    catalogo_urls = []
    datos_finales = []
    driver = None

    try:
        driver = webdriver.Chrome(options=options)
       
        # ANTI-BOT Nivel 2:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
       
        url_base = "https://www.portalinmobiliario.com/arriendo/departamento/la-serena-coquimbo"

        # ==============================================================================
        # FASE 1: RECOLECCIÓN EN EL CATÁLOGO (CON SEGMENTACIÓN)
        # ==============================================================================
        for pagina_actual in range(PAGINA_INICIO, PAGINA_FIN + 1):
            print(f"\n--- [FASE 1] Navegando a Página {pagina_actual} ---")
           
            url_pagina = url_base if pagina_actual == 1 else f"{url_base}_Desde_{((pagina_actual - 1) * 48) + 1}_NoIndex_True"
            driver.get(url_pagina)

            try:
                WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ui-search-layout__item")))
               
                for _ in range(random.randint(10, 15)):
                    driver.execute_script("window.scrollBy(0, 300);")
                    time.sleep(random.uniform(0.3, 0.6))
               
                bloques_totales = driver.find_elements(By.CSS_SELECTOR, ".ui-search-layout__item")
                bloques_a_procesar = bloques_totales[:CANTIDAD_A_EXTRAER] # De arriba hacia abajo
               
                if INVERTIR_ORDEN:
                    bloques_a_procesar = bloques_a_procesar[::-1]
               
                print(f"Página cargada ({len(bloques_totales)} total). Extrayendo {len(bloques_a_procesar)} tarjetas asignadas.")

                for bloque in bloques_a_procesar:
                    try:
                        url = bloque.find_element(By.TAG_NAME, "a").get_attribute("href").split("#")[0].split("?")[0]
                        titulo = bloque.find_element(By.CSS_SELECTOR, ".poly-component__title").get_attribute("textContent").strip()
                        ubicacion_cruda = bloque.find_element(By.CSS_SELECTOR, ".poly-component__location").get_attribute("textContent").strip()
                       
                        try:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-price__current").get_attribute("textContent")
                        except:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-component__price").get_attribute("textContent")
                       
                        # Guardamos el valor como texto para limpieza masiva en Spark
                        v_limpio = p_text.replace("$", "").replace(".", "").replace(",", "").replace("\n", "").strip()
                        precio = float(v_limpio) if v_limpio.isdigit() else 0.0

                        if url != "Sin URL" and precio > 0:
                            catalogo_urls.append({
                                "url": url,
                                "identificador": titulo,
                                "ubicacion": ubicacion_cruda,
                                "precio": precio        
                            })
                    except: continue
               
            except Exception as e:
                print(f"Error en carga de catálogo: {e}")
           
            time.sleep(random.uniform(3.0, 5.5))

        # ==============================================================================
        # FASE 2: INSPECCIÓN PROFUNDA POR PROPIEDAD
        # ==============================================================================
        print(f"\n--- [FASE 2] Iniciando buceo profundo en {len(catalogo_urls)} publicaciones ---")
        for i, propiedad in enumerate(catalogo_urls):
            print(f"[{i+1}/{len(catalogo_urls)}] Analizando: {propiedad['identificador'][:35]}...")
           
            registro = {
                "integrante": "Melany Torres",
                "fecha_captura": time.strftime("%Y-%m-%d %H:%M:%S"),
                "titulo": propiedad["identificador"],
                "ubicacion": propiedad["ubicacion"],
                "m2": 0,
                "precio": propiedad["precio"],
                "dormitorios": 0,
                "baños": 0,
                "estacionamiento": 0,
                "piscina": 0,
                "quincho": 0,
                "terraza": 0,
                "gimnasio": 0,
                "lavanderia": 0,
                "url": propiedad["url"]
            }

            try:
                driver.get(propiedad["url"])
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                texto_pagina = driver.find_element(By.TAG_NAME, "body").get_attribute("textContent").lower()
               
                # Lector de disponibilidad
                if "publicación pausada" in texto_pagina or "publicación finaliz" in texto_pagina:
                    print("   -> Publicación inactiva. Valor seteado a 0.0")
                    registro["precio"] = 0.0
                else:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-pdp-collapsable__container")))
                    filas_tabla = driver.find_elements(By.CSS_SELECTOR, ".andes-table__row")
                   
                    for fila in filas_tabla:
                        texto_fila = fila.get_attribute("textContent").lower()
                       
                        if "superficie total" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["m2"] = int(nums[0])
                        elif "dormitorios" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["dormitorios"] = int(nums[0])
                        elif "baños" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["baños"] = int(nums[0])
                        elif "estacionamiento" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums and int(nums[0]) > 0: registro["estacionamiento"] = int(nums[0])
                            elif any(x in texto_fila for x in ["sí", "si"]): registro["estacionamiento"] = 1
                       
                        # Captura de amenidades
                        elif "piscina" in texto_fila and any(x in texto_fila for x in ["sí", "si"]): registro["piscina"] = 1
                        elif "quincho" in texto_fila and any(x in texto_fila for x in ["sí", "si"]): registro["quincho"] = 1
                        elif "terraza" in texto_fila and any(x in texto_fila for x in ["sí", "si"]): registro["terraza"] = 1
                        elif "gimnasio" in texto_fila and any(x in texto_fila for x in ["sí", "si"]): registro["gimnasio"] = 1
                        elif "lavander" in texto_fila and any(x in texto_fila for x in ["sí", "si"]): registro["lavanderia"] = 1

                datos_finales.append(registro)

            except Exception:
                print(f"   -> No se pudo leer la tabla. Valor a 0.0")
                registro["precio"] = 0.0
                datos_finales.append(registro)
               
            driver.delete_all_cookies()
            time.sleep(random.uniform(2.5, 4.5))

    except Exception as e:
        print(f"Error crítico en el módulo: {e}")
    finally:
        if driver is not None:
            driver.quit()
            print("\nNavegador Selenium cerrado.")
           
    return datos_finales