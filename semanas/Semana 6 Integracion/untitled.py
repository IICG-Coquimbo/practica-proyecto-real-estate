# ==============================================================================
# PROYECTO BIG DATA - GRUPO 2 (REAL ESTATE)
# Código para Portal Inmobiliario (La Serena)
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
    """
    Ejecuta el proceso de Web Scraping para La Serena y retorna una lista de 
    diccionarios lista para ser unida en el main.py usando Spark.
    """
    # --- CONFIGURACIÓN PARA ASIGNACIÓN DE PÁGINAS ---
    PAGINA_INICIO = 13
    PAGINA_FIN = 13
    # ----------------------------------------------
    
    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.* && rm -rf /tmp/.org.chromium.Chromium.*")
    print(f"Entorno virtual listo. Asignación: Páginas {PAGINA_INICIO} a la {PAGINA_FIN}.")
    
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0")
    
    # ANTI-BOT Nivel 1: Apagar las banderas de automatización de Chrome
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    catalogo_urls = []
    datos_finales = []
    driver = None
    
    try:
        driver = webdriver.Chrome(options=options)
        
        # ANTI-BOT Nivel 2: Inyectar código en la página antes de que cargue 
        # para borrar la palabra "webdriver" del navegador y parecer un humano.
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
                    time.sleep(random.uniform(0.3, 0.7)) 
                    
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(1.5, 3.0)) 

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
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-price__current").get_attribute("textContent")
                        except:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-component__price").get_attribute("textContent")
                        
                        v_limpio = p_text.replace("$", "").replace(".", "").replace(",", "").replace("\n", "").strip()
                        precio = float(v_limpio) if v_limpio.isdigit() else 0.0

                        if url != "Sin URL" and precio > 0:
                            catalogo_urls.append({
                                "url": url,
                                "titulo": titulo,
                                "ubicacion": ubicacion,
                                "precio": precio
                            })
                    except: continue
                    
            except Exception as e:
                print(f"Advertencia en página {pagina_actual}: {e}")
                
            time.sleep(random.uniform(3.0, 5.5))

        print(f"\nCatálogo listo: {len(catalogo_urls)} propiedades encontradas. Recolectando amenidades...")

        # ==============================================================================
        # FASE 2: INSPECCIÓN PROFUNDA POR PROPIEDAD
        # ==============================================================================
        for i, propiedad in enumerate(catalogo_urls):
            print(f"[{i+1}/{len(catalogo_urls)}] Inspeccionando: {propiedad['titulo'][:30]}...")
            
            registro = {
                "responsable": "Millaray Zalazar", 
                "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "titulo": propiedad["titulo"],
                "ubicacion": propiedad["ubicacion"],
                "m2": 0,
                "precio": propiedad["precio"], # Valor original del catálogo
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
                
                # Lector de Letreros (Detecta publicaciones falsas o arrendadas)
                if "publicación pausada" in texto_pagina or "publicación finaliz" in texto_pagina:
                    print("   -> Publicación inactiva. Anulando precio a 0.0")
                    registro["precio"] = 0.0
                    datos_finales.append(registro)
                else:
                    # Si está activa, leemos la tabla
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
                            if nums and int(nums[0]) > 0:
                                registro["estacionamiento"] = int(nums[0])
                            elif "sí" in texto_fila or "si" in texto_fila:
                                registro["estacionamiento"] = 1
                        
                        elif "piscina" in texto_fila and "sí" in texto_fila: registro["piscina"] = 1
                        elif "quincho" in texto_fila and "sí" in texto_fila: registro["quincho"] = 1
                        elif "terraza" in texto_fila and "sí" in texto_fila: registro["terraza"] = 1
                        elif "gimnasio" in texto_fila and "sí" in texto_fila: registro["gimnasio"] = 1
                        elif "lavander" in texto_fila and "sí" in texto_fila: registro["lavanderia"] = 1

                    datos_finales.append(registro)

            except Exception as e:
                # Si hay Error 404 o falla total de la página, también anulamos el precio
                print(f"   -> Página caída o tabla no encontrada. Anulando precio a 0.0")
                registro["precio"] = 0.0
                datos_finales.append(registro)
                
            driver.delete_all_cookies() 
            time.sleep(random.uniform(2.8, 5.2)) 
            
    except Exception as e:
        print(f"Error crítico en Selenium: {e}")
        
    finally:
        if driver is not None:
            driver.quit()
            print("\nNavegador cerrado.")

    # Retornamos los datos limpios para que Spark (en main.py) los recoja y guarde
    return datos_finales