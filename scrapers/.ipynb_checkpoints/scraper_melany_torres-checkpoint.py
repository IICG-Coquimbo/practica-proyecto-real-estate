# ==============================================================================
# PROYECTO BIG DATA - GRUPO REAL ESTATE
# Código Portal Inmobiliario (La Serena) Melany Torres
# ==============================================================================

import os
import time
import re
import random
import json # Agregado para imprimir bonito
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def ejecutar_extraccion():

    PAGINA_INICIO = 1
    PAGINA_FIN = 11
    
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

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    catalogo_urls = []
    datos_finales = []
    driver = None

    try:
        driver = webdriver.Chrome(options=options)
        
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
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
                WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, ".ui-search-layout__item")
                    )
                )
                
                for _ in range(random.randint(12, 18)):
                    driver.execute_script("window.scrollBy(0, 250);")
                    time.sleep(random.uniform(0.3, 0.7))
                    
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(1.5, 3.0))

                bloques = driver.find_elements(By.CSS_SELECTOR, ".ui-search-layout__item")
                print(f"Tarjetas detectadas: {len(bloques)}")
                
                for bloque in bloques:
                    try:
                        url = bloque.find_element(By.TAG_NAME, "a").get_attribute("href").split("#")[0].split("?")[0]
                        titulo = bloque.find_element(By.CSS_SELECTOR, ".poly-component__title").get_attribute("textContent").strip()
                        
                        ubicacion_cruda = bloque.find_element(By.CSS_SELECTOR, ".poly-component__location").get_attribute("textContent").strip()
                        ubi_minuscula = ubicacion_cruda.lower()
                        
                        if "la serena" in ubi_minuscula or "coquimbo" in ubi_minuscula:
                            ubicacion = ubicacion_cruda     
                        else:
                            continue

                        try:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-price__current").get_attribute("textContent").strip()
                        except:
                            p_text = bloque.find_element(By.CSS_SELECTOR, ".poly-component__price").get_attribute("textContent").strip()
                        
                        precio_crudo = p_text

                        # =========================
                        # IMAGEN DESDE CATÁLOGO
                        # =========================
                        try:
                            imagen = bloque.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
                        except:
                            try:
                                imagen = bloque.find_element(By.CSS_SELECTOR, "img").get_attribute("data-src")
                            except:
                                imagen = "Sin imagen"

                        if url != "Sin URL" and precio_crudo:
                            catalogo_urls.append({
                                "url": url,
                                "identificador": titulo,
                                "ubicacion": ubicacion,
                                "precio": precio_crudo,
                                "imagen": imagen
                            })

                    except:
                        continue
                    
            except Exception as e:
                print(f"Advertencia en página {pagina_actual}: {e}")
                
            time.sleep(random.uniform(3.0, 5.5))

        print(f"\nCatálogo listo: {len(catalogo_urls)} propiedades encontradas. Recolectando amenidades...")

        # ==============================================================================
        # FASE 2: INSPECCIÓN PROFUNDA POR PROPIEDAD
        # ==============================================================================
        for i, propiedad in enumerate(catalogo_urls):
            
            if i == 0 or (i+1) % 10 == 0:
                print(f"[{i+1}/{len(catalogo_urls)}] Inspeccionando propiedades en curso...")
            
            registro = {
                "responsable": "Melany Torres",
                "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "titulo": propiedad["identificador"],
                "ubicacion": propiedad["ubicacion"],
                "m2": "",
                "precio": propiedad["precio"],
                "dormitorios": "",
                "banos": "",
                "estacionamiento": "",
                "piscina": "",
                "quincho": "",
                "terraza": "",
                "gimnasio": "",
                "lavanderia": "",
                "imagen": propiedad.get("imagen", "Sin imagen"),
                "enlace": propiedad["url"]
            }

            try:
                driver.get(propiedad["url"])
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                texto_pagina = driver.find_element(By.TAG_NAME, "body").get_attribute("textContent").lower()
                
                if "publicación pausada" in texto_pagina or "publicación finaliz" in texto_pagina:
                    registro["precio"] = "0"

                else:
                    # =========================
                    # IMAGEN DESDE DETALLE
                    # =========================
                    try:
                        imagen_detalle = driver.find_element(
                            By.CSS_SELECTOR,
                            ".ui-pdp-gallery__figure img"
                        ).get_attribute("src")

                        if imagen_detalle:
                            registro["imagen"] = imagen_detalle

                    except:
                        pass

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, ".ui-pdp-collapsable__container")
                        )
                    )

                    filas_tabla = driver.find_elements(By.CSS_SELECTOR, ".andes-table__row")
                    
                    for fila in filas_tabla:
                        texto_fila = fila.get_attribute("textContent").strip()
                        texto_fila_lower = texto_fila.lower()
                        
                        if "superficie total" in texto_fila_lower:
                            registro["m2"] = texto_fila

                        elif "dormitorios" in texto_fila_lower:
                            registro["dormitorios"] = texto_fila

                        elif "baños" in texto_fila_lower:
                            registro["banos"] = texto_fila

                        elif "estacionamiento" in texto_fila_lower:
                            registro["estacionamiento"] = texto_fila

                        elif "piscina" in texto_fila_lower:
                            registro["piscina"] = texto_fila

                        elif "quincho" in texto_fila_lower:
                            registro["quincho"] = texto_fila

                        elif "terraza" in texto_fila_lower:
                            registro["terraza"] = texto_fila

                        elif "gimnasio" in texto_fila_lower:
                            registro["gimnasio"] = texto_fila

                        elif "lavander" in texto_fila_lower:
                            registro["lavanderia"] = texto_fila

                datos_finales.append(registro)

            except Exception as e:
                registro["precio"] = "0"
                datos_finales.append(registro)
                
            driver.delete_all_cookies()
            time.sleep(random.uniform(2.8, 5.2))

    except Exception as e:
        print(f"Error crítico en Selenium: {e}")
        
    finally:
        if driver is not None:
            driver.quit()

    # ==============================================================================
    # FASE 3: MOSTRAR LISTA FINAL DE DATOS
    # ==============================================================================
    print(f"\nExtracción finalizada. Total de propiedades extraídas: {len(datos_finales)}")
    
    # IMPORTANTE: Aquí se limita la impresión solo a los primeros 3 registros
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


# ==============================================================================
# EJECUCIÓN DIRECTA PROTEGIDA
# (Esto asegura que no choque con el main.py)
# ==============================================================================
if __name__ == "__main__":
    datos_de_prueba = ejecutar_extraccion()