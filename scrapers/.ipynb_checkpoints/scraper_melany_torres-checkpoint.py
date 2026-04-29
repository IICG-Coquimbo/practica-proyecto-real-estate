# ==============================================================================
# PROYECTO BIG DATA - GRUPO 2 (REAL ESTATE)
# Código Portal Inmobiliario (Coquimbo) - Melany Torres
# ==============================================================================

import os
import time
import re
import random
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def ejecutar_extraccion():

    # --- CONFIGURACIÓN PARA EXTRACCIÓN MASIVA (Aprox 500 registros) ---
    PAGINA_INICIO = 1
    PAGINA_FIN = 11 # 11 páginas * 48 tarjetas = 528 registros potenciales
    
    # ----------------------------------------------
    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.* && rm -rf /tmp/.org.chromium.Chromium.*")

    print(f"🧹 Entorno virtual listo. Asignación: Páginas {PAGINA_INICIO} a la {PAGINA_FIN}.")
    print("🚀 Iniciando extracción masiva de Portal Inmobiliario (Responsable: Melany Torres)")

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
    datos_finales = []
    driver = None

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
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

        print(f"\n✅ Catálogo listo: {len(catalogo_urls)} propiedades encontradas. Pasando a inspección profunda...")

        # ==============================================================================
        # FASE 2: INSPECCIÓN PROFUNDA POR PROPIEDAD
        # ==============================================================================
        for i, propiedad in enumerate(catalogo_urls):
            if (i + 1) % 50 == 0:
                print(f"Progreso FASE 2: Inspeccionadas {i + 1} de {len(catalogo_urls)} propiedades...")
                
            # ETIQUETAS HOMOLOGADAS IDENTICAS A LAS DE YAPO (JALIL)
            # Todos los valores numéricos inicializan como string "0"
            registro = {
                "responsable": "Melany Torres", 
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
                    registro["precio"] = "Inactiva" 
                else:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-pdp-collapsable__container")))
                    filas_tabla = driver.find_elements(By.CSS_SELECTOR, ".andes-table__row")
                    
                    for fila in filas_tabla:
                        texto_fila = fila.get_attribute("textContent").lower()
                        
                        # Guardamos todos los resultados como texto (strings) para homologar con Yapo
                        if "superficie total" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["m2"] = str(nums[0])
                        elif "dormitorios" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["dormitorios"] = str(nums[0])
                        elif "baños" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums: registro["banos"] = str(nums[0])
                        elif "estacionamiento" in texto_fila:
                            nums = re.findall(r'\d+', texto_fila)
                            if nums and int(nums[0]) > 0:
                                registro["estacionamiento"] = str(nums[0])
                            elif "sí" in texto_fila or "si" in texto_fila:
                                registro["estacionamiento"] = "1"
                        
                        elif "piscina" in texto_fila and "sí" in texto_fila: registro["piscina"] = "1"
                        elif ("quincho" in texto_fila or "parrilla" in texto_fila) and "sí" in texto_fila: registro["quincho"] = "1"
                        elif "terraza" in texto_fila and "sí" in texto_fila: registro["terraza"] = "1"
                        elif "gimnasio" in texto_fila and "sí" in texto_fila: registro["gimnasio"] = "1"
                        elif "lavander" in texto_fila and "sí" in texto_fila: registro["lavanderia"] = "1"

                datos_finales.append(registro)

            except Exception as e:
                registro["precio"] = "Error" 
                datos_finales.append(registro)
                
            driver.delete_all_cookies() 
            time.sleep(random.uniform(1.4, 2.7)) 

        print(f"\n🎉 EXTRACCIÓN MAESTRA COMPLETADA: {len(datos_finales)} propiedades listas.")

    except Exception as e:
        print(f"🚨 Error crítico en Selenium: {e}")
    finally:
        if driver is not None:
            driver.quit()
            print("🔒 Navegador cerrado.")
            
    return datos_finales

# =======================================================
# BLOQUE DE PRUEBA LOCAL (Solo se ejecuta si corres este archivo directamente)
# =======================================================
if __name__ == "__main__":
    print("Iniciando script de scraping de manera local...")
    registros = ejecutar_extraccion()
    print(f"Proceso finalizado. Total retornado en la lista: {len(registros)}")