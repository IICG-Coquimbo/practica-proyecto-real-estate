# ==============================================================================
# PROYECTO BIG DATA - GRUPO REAL ESTATE
# Código Chile Propiedades (Coquimbo) - Anais Araya
# ==============================================================================

import os
import time
import re
import random
import base64
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def ejecutar_extraccion1():
    # --- CONFIGURACIÓN DE PÁGINAS ---
    PAGINA_INICIO = 1
    PAGINA_FIN = 47

    # PREPARACIÓN DEL ENTORNO
    os.environ["DISPLAY"] = ":99"
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.*")
    os.system("rm -rf /tmp/.org.chromium.Chromium.*")
    
    print(f"Entorno listo. ChilePropiedades: Páginas {PAGINA_INICIO} a {PAGINA_FIN}")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless") # Ejecución invisible
    
    # Opciones Anti-Bot
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0")
    options.add_argument("--disable-blink-features=AutomationControlled")

    catalogo_urls = []
    datos_finales = []
    driver = None

    try:
        driver = webdriver.Chrome(options=options)
        
        # Evasión extra de detección
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })

        # ==============================================================================
        # FASE 1: RECOLECCIÓN DE URLs
        # ==============================================================================
        url_base = "https://chilepropiedades.cl/propiedades/arriendo-mensual/departamento/iv-region-de-coquimbo/"

        for pagina_actual in range(PAGINA_INICIO, PAGINA_FIN + 1):
            print(f"\n--- Explorando Catálogo Regional: Página {pagina_actual} ---")
            
            # Paginación Índice 0
            indice_web = pagina_actual - 1 
            url_pagina = f"{url_base}{indice_web}"
            
            driver.get(url_pagina)
            time.sleep(random.uniform(3.5, 5.0))

            # Scroll para asentar el DOM
            for _ in range(random.randint(4, 7)):
                salto = random.randint(400, 600)
                driver.execute_script(f"window.scrollBy(0, {salto});")
                time.sleep(random.uniform(0.2, 0.5))

            print(f"Página cargada correctamente")
            
            tarjetas = driver.find_elements(By.CSS_SELECTOR, "div[id^='publication_']")
            
            for tarjeta in tarjetas:
                try:
                    # Extraemos el texto que contiene el tipo y la comuna
                    detalles_tarjeta = tarjeta.find_element(By.CSS_SELECTOR, "h3.sub-codigo-data").text.lower()
                    
                    # 1. Filtro de arriendo diario
                    if "diario" in detalles_tarjeta and "mensual" not in detalles_tarjeta:
                        continue 
                    
                    # 2. FILTRO DE UBICACIÓN
                    if "la serena" in detalles_tarjeta:
                        ubicacion_detectada = "La Serena"
                    elif "coquimbo" in detalles_tarjeta:
                        ubicacion_detectada = "Coquimbo"
                    else:
                        continue # Si es Ovalle, Vicuña, etc., el bot se salta la tarjeta
                    
                    url = tarjeta.find_element(By.TAG_NAME, "a").get_attribute("href")
                    
                    if not url or "/ver-publicacion/" not in url: 
                        continue

                    # Guardamos la URL y la ubicación específica
                    catalogo_urls.append({
                        "url": url,
                        "ubicacion": ubicacion_detectada 
                    })
                except:
                    continue
                    
            time.sleep(random.uniform(1.2, 2.5)) 

        catalogo_urls = list({v['url']: v for v in catalogo_urls}.values())
        print(f"\nFASE 1 COMPLETADA: {len(catalogo_urls)} propiedades válidas en La Serena y Coquimbo.")

        # ==============================================================================
        # FASE 2: INSPECCIÓN ESTRUCTURAL DE PROPIEDADES
        # ==============================================================================
        
        for i, propiedad in enumerate(catalogo_urls):
            if i == 0 or (i+1)% 10 == 0:
                print(f"[{i+1}/{len(catalogo_urls)}] Inspeccionando propiedades en curso...")

            # Diccionario con TODO en formato texto (String)
            registro = {
                "responsable": "Anais Araya", 
                "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "titulo": "",
                "ubicacion": propiedad["ubicacion"], 
                "m2": "0",              
                "precio": "",          
                "dormitorios": "0",     
                "banos": "0",           
                "estacionamiento": "0", 
                "piscina": "0",
                "quincho": "0",
                "terraza": "0",
                "gimnasio": "0",
                "lavanderia": "0",
                "imagen": "",
                "enlace": propiedad["url"]         
            }

            try:
                driver.get(propiedad["url"])
                time.sleep(random.uniform(2.5, 4.0))

                # --- A. TÍTULO ---
                try:
                    titulo = driver.find_element(By.CSS_SELECTOR, "h1.clp-titulo").text.strip()
                    registro["titulo"] = titulo
                except:
                    registro["titulo"] = "Propiedad ChilePropiedades"

                # --- B. EXTRACCIÓN TABULAR ---
                try:
                    labels = driver.find_elements(By.CSS_SELECTOR, ".clp-description-label")
                    values = driver.find_elements(By.CSS_SELECTOR, ".clp-description-value")

                    for j in range(len(labels)):
                        label_text = labels[j].text.strip().lower()
                        value_text = values[j].text.strip() 

                        if label_text == "valor:": 
                            registro["precio"] = value_text 
                        elif "habitaciones" in label_text:
                            registro["dormitorios"] = value_text
                        elif "baño" in label_text:
                            registro["banos"] = value_text
                        elif "estacionamiento" in label_text:
                            registro["estacionamiento"] = value_text
                        elif "superficie total" in label_text or "superficie útil" in label_text:
                            nums = re.findall(r'\d+', value_text)
                            if nums and registro["m2"] == "0": 
                                registro["m2"] = nums[0] 
                except Exception as e:
                    pass 

                # --- C. EXTRACCIÓN DE IMAGEN ---
                try:
                    imagen_elemento = driver.find_element(By.CSS_SELECTOR, "#publication-images-carousel .carousel-item.active img")
                    registro["imagen"] = imagen_elemento.get_attribute("src")
                except:
                    try:
                        registro["imagen"] = driver.find_element(By.CSS_SELECTOR, "img.d-block.w-100").get_attribute("src")
                    except:
                        registro["imagen"] = "Sin imagen"

                # --- D. AMENIDADES ---
                try:
                    texto_descripcion = driver.find_element(By.CSS_SELECTOR, ".clp-description-box").text.lower()
                except:
                    texto_descripcion = driver.find_element(By.TAG_NAME, "body").text.lower()
                
                if registro["estacionamiento"] == "0" and "estacionamiento" in texto_descripcion: registro["estacionamiento"] = "1"
                if "piscina" in texto_descripcion: registro["piscina"] = "1"
                if "quincho" in texto_descripcion or "asador" in texto_descripcion: registro["quincho"] = "1"
                if "terraza" in texto_descripcion: registro["terraza"] = "1"
                if "gimnasio" in texto_descripcion: registro["gimnasio"] = "1"
                if "lavander" in texto_descripcion: registro["lavanderia"] = "1"

                # --- E. FILTRO INTELIGENTE NLP ---
                banderas_rojas = ["diario", "por noche", "por día", "temporal"]
                banderas_verdes = ["año corrido", "año de corrido", "marzo a diciembre", "mensual"]

                tiene_alerta_diaria = any(palabra in texto_descripcion for palabra in banderas_rojas)
                tiene_salvavidas = any(palabra in texto_descripcion for palabra in banderas_verdes)

                if tiene_alerta_diaria and not tiene_salvavidas:
                    print("  -> Descartado: Arriendo 100% diario detectado.")
                    continue

                precio_crudo = registro["precio"]
                precio_solo_numeros = precio_crudo.replace("$", "").replace(".", "").replace(" ", "").strip()
            
                if precio_solo_numeros.isdigit():
                    if int(precio_solo_numeros) < 100000:
                        print(f"  -> Descartado: Precio muy bajo ({precio_crudo}). Posible arriendo diario.")
                        continue

                datos_finales.append(registro)

            except Exception as e:
                print(f"  -> Error al procesar propiedad: {e}")

            driver.delete_all_cookies()
            time.sleep(random.uniform(1.5, 3.0))

    except Exception as e:
        print(f"Error crítico global en Selenium: {e}")

    finally:
        if driver is not None:
            driver.quit()
            
    return datos_finales


def ejecutar_extraccion2():
    PAGINA_INICIO = 20
    PAGINA_FIN = 23
    MAX_REGISTROS = 100
    
    os.environ["DISPLAY"] = ":99"
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.*")
    os.system("rm -rf /tmp/.org.chromium.Chromium.*")
    
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

        for pagina_actual in range(PAGINA_INICIO, PAGINA_FIN + 1):
            if len(catalogo_urls) >= MAX_REGISTROS:
                break
    
            print(f"\n--- [FASE 1] Procesando Página {pagina_actual} ---")
            url_pagina = f"{url_base}&page={pagina_actual}"
            driver.get(url_pagina)
    
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.listing-card")))
                for _ in range(4):
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1)
                time.sleep(1)
    
                bloques = driver.find_elements(By.CSS_SELECTOR, "article.listing-card")
    
                for bloque in bloques:
                    if len(catalogo_urls) >= MAX_REGISTROS:
                        break
                    try:
                        texto_tarjeta = bloque.get_attribute("textContent").lower()
                        if "coquimbo" in texto_tarjeta:
                            ubicacion = "Coquimbo"
                        elif "la serena" in texto_tarjeta:
                            ubicacion = "La Serena"
                        else:
                            continue
    
                        try:
                            codigo_secreto = bloque.get_attribute("data-clickdestination")
                            if codigo_secreto:
                                url_decodificada = base64.b64decode(codigo_secreto).decode("utf-8", errors="ignore")
                                url = "https://casas.mitula.cl" + url_decodificada
                            else:
                                continue
                        except:
                            continue
    
                        if not url or "javascript" in url:
                            continue
    
                        try:
                            precio_texto = bloque.find_element(By.CSS_SELECTOR, ".price__actual").get_attribute("textContent").strip()
                        except:
                            precio_texto = "Sin información"
    
                        m2_texto, dormitorios_texto, banos_texto = "Sin información", "Sin información", "Sin información"
                        
                        match_m2 = re.search(r'(\d+\s*(m2|m²|mts))', texto_tarjeta)
                        if match_m2: m2_texto = match_m2.group(1)
    
                        match_dorm = re.search(r'(\d+\s*dormitorio[s]?)', texto_tarjeta)
                        if match_dorm: dormitorios_texto = match_dorm.group(1)
    
                        match_bano = re.search(r'(\d+\s*baño[s]?)', texto_tarjeta)
                        if match_bano: banos_texto = match_bano.group(1)
    
                        imagen_url = "Sin imagen"
                        try:
                            imagen = bloque.find_element(By.TAG_NAME, "img")
                            imagen_url = imagen.get_attribute("src") or "Sin imagen"
                        except:
                            pass
    
                        catalogo_urls.append({
                            "responsable": "Anais Araya",
                            "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "titulo": "Propiedad Mitula",
                            "ubicacion": ubicacion,
                            "precio": precio_texto,
                            "m2": m2_texto,
                            "dormitorios": dormitorios_texto,
                            "banos": banos_texto,
                            "imagen": imagen_url,
                            "enlace": url
                        })
                    except:
                        continue
            except TimeoutException:
                continue
        
        catalogo_urls = list({v["enlace"]: v for v in catalogo_urls}.values())
        print(f"\nCatálogo final: {len(catalogo_urls)} propiedades encontradas")
    
        for i, propiedad in enumerate(catalogo_urls):
            if (i + 1) % 5 == 0:
                print(f"Progreso FASE 2: {i + 1} de {len(catalogo_urls)}")
    
            propiedad["estacionamiento"] = "0"
            propiedad["piscina"] = "0"
            propiedad["quincho"] = "0"
            propiedad["terraza"] = "0"
            propiedad["gimnasio"] = "0"
            propiedad["lavanderia"] = "0"
    
            try:
                driver.get(propiedad["enlace"])
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(2)
                
                try:
                    propiedad["titulo"] = driver.find_element(By.CSS_SELECTOR, "div.main-title").get_attribute("textContent").strip()
                except:
                    propiedad["titulo"] = "Sin título"   

                texto_total = driver.find_element(By.TAG_NAME, "body").get_attribute("textContent").lower()
    
                if "estacionamiento" in texto_total: propiedad["estacionamiento"] = "1"
                if "piscina" in texto_total: propiedad["piscina"] = "1"
                if "quincho" in texto_total: propiedad["quincho"] = "1"
                if "terraza" in texto_total: propiedad["terraza"] = "1"
                if "gimnasio" in texto_total: propiedad["gimnasio"] = "1"
                if "lavander" in texto_total: propiedad["lavanderia"] = "1"
            except:
                pass
    
            datos_finales.append(propiedad)
    
    except Exception as e:
        print(f"Error crítico en Selenium: {e}")
    finally:
        if driver is not None: driver.quit()
        
    return datos_finales

# ==============================================================
# ESTA ES LA FUNCIÓN MAESTRA QUE LLAMARÁ EL main.py
# ==============================================================
def ejecutar_extraccion():
    datos_finales = []
    
    print("\n[ANAIS] Iniciando extracción de ChilePropiedades...")
    datos_scraper1 = ejecutar_extraccion1()
    if datos_scraper1:
        datos_finales.extend(datos_scraper1)

    print("\n[ANAIS] Iniciando extracción de Mitula...")
    datos_scraper2 = ejecutar_extraccion2()
    if datos_scraper2:
        datos_finales.extend(datos_scraper2)

    # --- IMPRESIÓN DOS 3 PRIMEIROS REXISTROS ---
    print(f"\nExtracción finalizada. Total de propiedades extraídas: {len(datos_finales)}")
    
    if datos_finales:
        print("\n" + "="*80)
        print(" MUESTRA DE RESULTADOS FINALES (Primeros 3 registros)")
        print("="*80)

        for idx, dato in enumerate(datos_finales[:3]):
            print(f"\n--- REXISTRO {idx + 1} ---")
            for clave, valor in dato.items():
                mostrar_valor = valor if valor != "" else "[Vacío / No encontrado]"
                print(f" • {clave.capitalize():<18}: {mostrar_valor}")
        
        print("\n" + "="*80)

    return datos_finales

# =======================================================
# BLOQUE DE PROBA LOCAL 
# =======================================================
if __name__ == "__main__":
    print("Iniciando script de scraping de manera local...")
    registros = ejecutar_extraccion()