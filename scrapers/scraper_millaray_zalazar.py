# ==============================================================================
# PROYECTO BIG DATA - GRUPO REAL ESTATE
# Código Portal Inmobiliario (Coquimbo) - Millaray Zalazar
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

def scraper1():

    # --- CONFIGURACIÓN PARA ASIGNACIÓN DE PÁGINAS ---
    PAGINA_INICIO = 1
    PAGINA_FIN = 6
    
    # ----------------------------------------------
    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.* && rm -rf /tmp/.org.chromium.Chromium.*")

    print(f"Entorno virtual listo. Asignación: Páginas {PAGINA_INICIO} a la {PAGINA_FIN}.")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0")

    # ANTI-BOT Nivel 1
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    catalogo_urls = []
    datos_1 = []
    driver = None

    try:
        driver = webdriver.Chrome(options=options)
        
        # ANTI-BOT Nivel 2
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        url_base = "https://www.portalinmobiliario.com/arriendo/departamento/coquimbo-coquimbo"

        # ==============================================================================
        # FASE 1: RECOLECCIÓN EN EL CATÁLOGO
        # ==============================================================================
        for pagina_actual in range(PAGINA_INICIO, PAGINA_FIN + 1):
            print(f"\n--- [FASE 1] Recolectando enlaces de la Página {pagina_actual} ---")
            
            if pagina_actual == 1:
                url_pagina = url_base
            else:
                desde = ((pagina_actual - 1) * 48) + 1
                url_pagina = f"{url_base}_Desde_{desde}_NoIndex_True"
                
            driver.get(url_pagina)

            try:
                WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ui-search-layout__item")))
                
                # Scroll
                for _ in range(random.randint(7, 11)): 
                    salto = random.randint(350,500)
                    driver.execute_script(f"window.scrollBy(0, {salto});") 
                    time.sleep(random.uniform(0.1, 0.4)) 
                    
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(0.7, 1.2)) 

                bloques = driver.find_elements(By.CSS_SELECTOR, ".ui-search-layout__item")
                
                for bloque in bloques:
                    try:
                        url = bloque.find_element(By.TAG_NAME, "a").get_attribute("href").split("#")[0].split("?")[0]
                        titulo = bloque.find_element(By.CSS_SELECTOR, ".poly-component__title").get_attribute("textContent").strip()
                        
                        ubicacion_cruda = bloque.find_element(By.CSS_SELECTOR, ".poly-component__location").get_attribute("textContent").strip()
                        ubi_minuscula = ubicacion_cruda.lower()
                        
                        if "coquimbo" in ubi_minuscula: ubicacion = "Coquimbo"       
                        elif "la serena" in ubi_minuscula: ubicacion = "La Serena"     
                        else: continue 

                        try:
                            imagen_url = bloque.find_element(By.CSS_SELECTOR, "img.poly-component__picture").get_attribute("src")
                        except:
                            imagen_url = "Sin Imagen"
                
                        try:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-price__current").get_attribute("textContent")
                        except:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-component__price").get_attribute("textContent")
                        
                        precio = p_text.strip()

                        if url != "Sin URL" and precio != "":
                            catalogo_urls.append({
                                "url": url,
                                "identificador": titulo, 
                                "ubicacion": ubicacion,
                                "precio": precio,
                                "imagen": imagen_url 
                            })
                    except: continue
                    
            except Exception as e:
                print(f"Advertencia en página {pagina_actual}: {e}")
                
            time.sleep(random.uniform(1.2, 2.5))

        print(f"\nCatálogo listo: {len(catalogo_urls)} propiedades encontradas. Recolectando amenidades...")

        # ==============================================================================
        # FASE 2: INSPECCIÓN PROFUNDA POR PROPIEDAD
        # ==============================================================================
        for i, propiedad in enumerate(catalogo_urls):
            
            if i == 0 or (i+1) % 10 == 0:
                print(f"[{i+1}/{len(catalogo_urls)}] Inspeccionando propiedades en curso...")
            
            # TODO INICIA COMO TEXTO (String)
            registro = {
                "responsable": "Millaray Zalazar", 
                "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"), 
                "titulo": propiedad["identificador"],
                "ubicacion": propiedad["ubicacion"],
                "m2": "0",
                "precio": propiedad["precio"], 
                "dormitorios": "0",
                "banos": "0",
                "estacionamiento": "0",
                "piscina": "0",
                "quincho": "0",
                "terraza": "0",
                "gimnasio": "0",
                "lavanderia": "0",
                "imagen": propiedad["imagen"],
                "enlace": propiedad["url"]
            }

            try:
                driver.get(propiedad["url"])
                
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                texto_pagina = driver.find_element(By.TAG_NAME, "body").get_attribute("textContent").lower()
                
                if "publicación pausada" in texto_pagina or "publicación finaliz" in texto_pagina:
                    print("   -> Publicación inactiva. Marcando precio como 'Inactiva'")
                    registro["precio"] = "0" 
                else:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-pdp-collapsable__container")))
                    filas_tabla = driver.find_elements(By.CSS_SELECTOR, ".andes-table__row")
                    
                    for fila in filas_tabla:
                        texto_fila = fila.get_attribute("textContent").lower()
                        
                        # EXTRACCIÓN SIN CONVERTIR A INT()
                        if "superficie total" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["m2"] = nums[0]
                        elif "dormitorios" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["dormitorios"] = nums[0]
                        elif "baños" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["banos"] = nums[0]
                        elif "estacionamiento" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
    
                            # Si encuentra número, guarda el número como texto (ej: "2")
                            if nums and int(nums[0]) > 0:
                                registro["estacionamiento"] = nums[0]
                                
                            # Si dice "sí", lo marca con "1" en texto
                            elif "sí" in texto_fila or "si" in texto_fila:
                                registro["estacionamiento"] = "1"
                        
                        # AMENIDADES 
                        elif "piscina" in texto_fila and "sí" in texto_fila: registro["piscina"] = "1"
                        elif ("quincho" in texto_fila or "parrilla" in texto_fila) and "sí" in texto_fila: registro["quincho"] = "1"
                        elif "terraza" in texto_fila and "sí" in texto_fila: registro["terraza"] = "1"
                        elif "gimnasio" in texto_fila and "sí" in texto_fila: registro["gimnasio"] = "1"
                        elif "lavander" in texto_fila and "sí" in texto_fila: registro["lavanderia"] = "1"

                datos_1.append(registro)

            except Exception as e:
                print(f"   -> Página caída o tabla no encontrada. Marcando precio como 'Error'")
                registro["precio"] = "0" 
                datos_1.append(registro)
                
            driver.delete_all_cookies() 
            time.sleep(random.uniform(1.4, 2.7)) 

    except Exception as e:
        print(f"Error crítico en Selenium: {e}")
    finally:
        if driver is not None:
            driver.quit()
            print("\nNavegador cerrado.")

    
    return datos_1


def scraper2():

    # --- CONFIGURACIÓN PARA ASIGNACIÓN DE PÁGINAS ---
    PAGINA_INICIO = 13
    PAGINA_FIN = 17
    
    # ----------------------------------------------
    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.* && rm -rf /tmp/.org.chromium.Chromium.*")

    print(f"Entorno virtual listo. Asignación: Páginas {PAGINA_INICIO} a la {PAGINA_FIN}.")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless") 
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0")

    # ANTI-BOT Nivel 1
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    catalogo_urls = []
    datos_2 = []
    driver = None

    try:
        driver = webdriver.Chrome(options=options)
        
        # ANTI-BOT Nivel 2
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        url_base = "https://www.portalinmobiliario.com/arriendo/departamento/la-serena-coquimbo"

        # ==============================================================================
        # FASE 1: RECOLECCIÓN EN EL CATÁLOGO
        # ==============================================================================
        for pagina_actual in range(PAGINA_INICIO, PAGINA_FIN + 1):
            print(f"\n--- [FASE 1] Recolectando enlaces de la Página {pagina_actual} ---")
            
            if pagina_actual == 1:
                url_pagina = url_base
            else:
                desde = ((pagina_actual - 1) * 48) + 1
                url_pagina = f"{url_base}_Desde_{desde}_NoIndex_True"
                
            driver.get(url_pagina)

            try:
                WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ui-search-layout__item")))
                
                # Scroll Ultra Lento y Suave
                for _ in range(random.randint(12, 18)): 
                    driver.execute_script("window.scrollBy(0, 250);") 
                    time.sleep(random.uniform(0.2, 0.5)) 
                    
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(0.9, 1.7)) 

                bloques = driver.find_elements(By.CSS_SELECTOR, ".ui-search-layout__item")
                
                for bloque in bloques:
                    try:
                        url = bloque.find_element(By.TAG_NAME, "a").get_attribute("href").split("#")[0].split("?")[0]
                        titulo = bloque.find_element(By.CSS_SELECTOR, ".poly-component__title").get_attribute("textContent").strip()
                        
                        ubicacion_cruda = bloque.find_element(By.CSS_SELECTOR, ".poly-component__location").get_attribute("textContent").strip()
                        ubi_minuscula = ubicacion_cruda.lower()
                        
                        if "la serena" in ubi_minuscula: ubicacion = "La Serena"       
                        elif "coquimbo" in ubi_minuscula: ubicacion = "Coquimbo"     
                        else: continue 

                        try:
                            imagen_url = bloque.find_element(By.CSS_SELECTOR, "img.poly-component__picture").get_attribute("src")
                        except:
                            imagen_url = "Sin Imagen"
                            
                        try:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-price__current").get_attribute("textContent")
                        except:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-component__price").get_attribute("textContent")
                        
                        precio = p_text.strip()

                        if url != "Sin URL" and precio != "":
                            catalogo_urls.append({
                                "url": url,
                                "identificador": titulo, 
                                "ubicacion": ubicacion,
                                "precio": precio,
                                "imagen": imagen_url
                            })
                    except: continue
                    
            except Exception as e:
                print(f"Advertencia en página {pagina_actual}: {e}")
                
            time.sleep(random.uniform(1.1, 2.6))

        print(f"\nCatálogo listo: {len(catalogo_urls)} propiedades encontradas. Recolectando amenidades...")

        # ==============================================================================
        # FASE 2: INSPECCIÓN PROFUNDA POR PROPIEDAD
        # ==============================================================================
        for i, propiedad in enumerate(catalogo_urls):
            
            if i == 0 or (i+1) % 10 == 0:
                print(f"[{i+1}/{len(catalogo_urls)}] Inspeccionando propiedades en curso...")
            
            # --- DICCIONARIO ---
            registro = {
                "responsable": "Millaray Zalazar", 
                "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"), 
                "titulo": propiedad["identificador"],
                "ubicacion": propiedad["ubicacion"],
                "m2": "0",
                "precio": propiedad["precio"], 
                "dormitorios": "0",
                "banos": "0",          
                "estacionamiento": "0",
                "piscina": "0",
                "quincho": "0",
                "terraza": "0",
                "gimnasio": "0",
                "lavanderia": "0",
                "imagen": propiedad["imagen"],
                "enlace": propiedad["url"] 
            }

            try:
                driver.get(propiedad["url"])
                
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                texto_pagina = driver.find_element(By.TAG_NAME, "body").get_attribute("textContent").lower()
                
                if "publicación pausada" in texto_pagina or "publicación finaliz" in texto_pagina:
                    print("   -> Publicación inactiva.")
                    registro["precio"] = "0"
                else:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-pdp-collapsable__container")))
                    filas_tabla = driver.find_elements(By.CSS_SELECTOR, ".andes-table__row")
                    
                    for fila in filas_tabla:
                        texto_fila = fila.get_attribute("textContent").lower()
                        
                        # --- EXTRACCIÓN  ---
                        if "superficie total" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["m2"] = nums[0]
                        elif "dormitorios" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["dormitorios"] = nums[0]
                        elif "baños" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["banos"] = nums[0]
                        elif "estacionamiento" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            
                            # Si encuentra número, guarda el número como texto (ej: "2")
                            if nums and int(nums[0]) > 0:
                                registro["estacionamiento"] = nums[0]
                            # Si dice "sí", lo marca con "1" 
                            elif "sí" in texto_fila or "si" in texto_fila:
                                registro["estacionamiento"] = "1"
                        
                        # --- AMENIDADES  ---
                        elif "piscina" in texto_fila and "sí" in texto_fila: registro["piscina"] = "1"
                        elif ("quincho" in texto_fila or "parrilla" in texto_fila) and "sí" in texto_fila: registro["quincho"] = "1"
                        elif "terraza" in texto_fila and "sí" in texto_fila: registro["terraza"] = "1"
                        elif "gimnasio" in texto_fila and "sí" in texto_fila: registro["gimnasio"] = "1"
                        elif "lavander" in texto_fila and "sí" in texto_fila: registro["lavanderia"] = "1"

                datos_2.append(registro)

            except Exception as e:
                print(f"   -> Página caída o tabla no encontrada. Anulando valor")
                registro["precio"] = "0"
                datos_2.append(registro)
                
            driver.delete_all_cookies() 
            time.sleep(random.uniform(1.5, 2.9)) 

    except Exception as e:
        print(f"Error crítico en Selenium: {e}")
    finally:
        if driver is not None:
            driver.quit()
            print("\nNavegador cerrado.")
    
    return datos_2


def scraper3():

    # --- CONFIGURACIÓN PÁGINAS A SCRAPEAR ---
    PAGINA_INICIO = 12
    PAGINA_FIN = 12
    CANTIDAD_A_EXTRAER = 20  
    INVERTIR_ORDEN = True     

    # --- LIMPIEZA Y ENTORNO ---
    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.* && rm -rf /tmp/.org.chromium.Chromium.*")

    print(f"Entorno listo. Procesando Pág {PAGINA_INICIO} | Segmento: Últimas {CANTIDAD_A_EXTRAER} tarjetas.")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless") # Requerido para ejecución profesional en contenedores
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    # ANTI-BOT Nivel 1
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    catalogo_urls = []
    datos_3 = []
    driver = None

    try:
        driver = webdriver.Chrome(options=options)
        
        # ANTI-BOT Nivel 2
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        url_base = "https://www.portalinmobiliario.com/arriendo/departamento/la-serena-coquimbo"

        # FASE 1: RECOLECCIÓN EN EL CATÁLOGO
        for pagina_actual in range(PAGINA_INICIO, PAGINA_FIN + 1):
            print(f"\n--- [FASE 1] Navegando a Página {pagina_actual} ---")
            
            url_pagina = url_base if pagina_actual == 1 else f"{url_base}_Desde_{((pagina_actual - 1) * 48) + 1}_NoIndex_True"
            driver.get(url_pagina)

            try:
                WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ui-search-layout__item")))
                
                for _ in range(random.randint(12, 18)): 
                    driver.execute_script("window.scrollBy(0, 250);") 
                    time.sleep(random.uniform(0.3, 0.7)) 
                
                bloques_totales = driver.find_elements(By.CSS_SELECTOR, ".ui-search-layout__item")
                
                # Segmentación asignada
                bloques_a_procesar = bloques_totales[-CANTIDAD_A_EXTRAER:]
                if INVERTIR_ORDEN:
                    bloques_a_procesar = bloques_a_procesar[::-1]
                
                print(f"Página cargada ({len(bloques_totales)} total). Extrayendo {len(bloques_a_procesar)} tarjetas.")

                for bloque in bloques_a_procesar:
                    try:
                        url = bloque.find_element(By.TAG_NAME, "a").get_attribute("href").split("#")[0].split("?")[0]
                        titulo = bloque.find_element(By.CSS_SELECTOR, ".poly-component__title").get_attribute("textContent").strip()
                        
                        ubicacion_cruda = bloque.find_element(By.CSS_SELECTOR, ".poly-component__location").get_attribute("textContent").strip()
                        ubi_minuscula = ubicacion_cruda.lower()
                        
                        if "la serena" in ubi_minuscula: ubicacion = "La Serena"       
                        elif "coquimbo" in ubi_minuscula: ubicacion = "Coquimbo"     
                        else: continue 

                        try:
                            imagen_url = bloque.find_element(By.CSS_SELECTOR, "img.poly-component__picture").get_attribute("src")
                        except:
                            imagen_url = "Sin Imagen"
                            
                        try:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-price__current").get_attribute("textContent")
                        except:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-component__price").get_attribute("textContent")
                        
                        precio = p_text.strip()

                        if url != "Sin URL" and precio != "":
                            catalogo_urls.append({
                                "url": url,
                                "identificador": titulo, 
                                "ubicacion": ubicacion,
                                "precio": precio,
                                "imagen": imagen_url
                            })
                    except: continue
            except Exception as e:
                print(f"Error en carga de catálogo: {e}")
            
            time.sleep(random.uniform(1.3, 2.9))

        # FASE 2: INSPECCIÓN PROFUNDA
        print(f"\n--- [FASE 2] Iniciando buceo profundo en {len(catalogo_urls)} publicaciones ---")
        for i, propiedad in enumerate(catalogo_urls):
            
            if i == 0 or (i+1) % 10 == 0:
                print(f"[{i+1}/{len(catalogo_urls)}] Analizando propiedades en curso...")
            
            # DICCIONARIO TEXTUAL
            registro = {
                "responsable": "Millaray Zalazar", 
                "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "titulo": propiedad["identificador"],
                "ubicacion": propiedad["ubicacion"],
                "m2": "0",
                "precio": propiedad["precio"], 
                "dormitorios": "0",
                "banos": "0",          
                "estacionamiento": "0",
                "piscina": "0",
                "quincho": "0",
                "terraza": "0",
                "gimnasio": "0",
                "lavanderia": "0",
                "imagen": propiedad["imagen"],
                "enlace": propiedad["url"] 
            }

            try:
                driver.get(propiedad["url"])
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                texto_pagina = driver.find_element(By.TAG_NAME, "body").get_attribute("textContent").lower()
                
                if "publicación pausada" in texto_pagina or "publicación finaliz" in texto_pagina:
                    print("   -> Publicación ya no disponible")
                    registro["precio"] = "0"
                else:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-pdp-collapsable__container")))
                    filas_tabla = driver.find_elements(By.CSS_SELECTOR, ".andes-table__row")
                    
                    for fila in filas_tabla:
                        texto_fila = fila.get_attribute("textContent").lower()
                        
                        # EXTRACCIÓN
                        if "superficie total" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["m2"] = nums[0]
                        elif "dormitorios" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["dormitorios"] = nums[0]
                        elif "baños" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["banos"] = nums[0]
                        elif "estacionamiento" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums and int(nums[0]) > 0: registro["estacionamiento"] = nums[0]
                            elif any(x in texto_fila for x in ["sí", "si"]): registro["estacionamiento"] = "1"
                        
                        # AMENIDADES
                        elif "piscina" in texto_fila and any(x in texto_fila for x in ["sí", "si"]): registro["piscina"] = "1"
                        elif ("quincho" in texto_fila or "parrilla" in texto_fila) and "sí" in texto_fila: registro["quincho"] = "1"
                        elif "terraza" in texto_fila and any(x in texto_fila for x in ["sí", "si"]): registro["terraza"] = "1"
                        elif "gimnasio" in texto_fila and any(x in texto_fila for x in ["sí", "si"]): registro["gimnasio"] = "1"
                        elif "lavander" in texto_fila and any(x in texto_fila for x in ["sí", "si"]): registro["lavanderia"] = "1"
            
            except Exception:
                print(f"   -> No se pudo leer la tabla detallada.")
                registro["precio"] = "0"
            
            datos_3.append(registro)
            driver.delete_all_cookies() 
            time.sleep(random.uniform(1.4, 2.9))

    except Exception as e:
        print(f"Error crítico: {e}")
    finally:
        if driver:
            driver.quit()
            print("\nNavegador cerrado.")
    
    return datos_3 

# ==============================================================
# ESTA ES LA FUNCIÓN MAESTRA QUE LLAMARÁ EL main.py
# ==============================================================
def extraccion_datos():
    datos_finales = []
    
    print("\n[MILLARAY] Iniciando extracción de Portal Inmobiliario (Coquimbo)...")
    datos1 = scraper1()
    if datos1:
        datos_finales.extend(datos1)
        
    print("\n[MILLARAY] Iniciando extracción de Portal Inmobiliario (La Serena - Parte 1)...")
    datos2 = scraper2()
    if datos2:
        datos_finales.extend(datos2)

    print("\n[MILLARAY] Iniciando extracción de Portal Inmobiliario (La Serena - Parte 2)...")
    datos3 = scraper3()
    if datos3:
        datos_finales.extend(datos3)

    # --- IMPRESIÓN DE LOS 3 PRIMEROS REGISTROS ---
    print(f"\nExtracción finalizada. Total de propiedades extraídas: {len(datos_finales)}")
    
    if datos_finales:
        print("\n" + "="*80)
        print(" MUESTRA DE RESULTADOS FINALES (Primeros 3 registros)")
        print("="*80)

        for idx, dato in enumerate(datos_finales[:3]):
            print(f"\n--- REGISTRO {idx + 1} ---")
            for clave, valor in dato.items():
                mostrar_valor = valor if valor != "" else "[Vacío / No encontrado]"
                print(f" • {clave.capitalize():<18}: {mostrar_valor}")
        
        print("\n" + "="*80)

    return datos_finales

# =======================================================
# BLOQUE DE PRUEBA LOCAL 
# =======================================================
if __name__ == "__main__":
    print("Iniciando script de scraping de manera local...")
    registros = extraccion_datos()