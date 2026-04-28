
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

# CONFIGURACIÓN

def ejecutar_extracción():
    PAGINA_INICIO = 1
    PAGINA_FIN = 1
    MAX_REGISTROS = 500
    

    # PREPARACIÓN DEL ENTORNO

    os.environ["DISPLAY"] = ":99"
    
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.*")
    os.system("rm -rf /tmp/.org.chromium.Chromium.*")
    
    print(f"Entorno virtual listo. Páginas asignadas: {PAGINA_INICIO} a {PAGINA_FIN}")
    print(f"Límite máximo de registros: {MAX_REGISTROS}")
    
    options = Options()
    # options.add_argument("--headless=new")  # descomentar si quieres ocultar navegador
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
    )
    
    catalogo_urls = []
    datos_finales = []
    driver = None
    
    
    try:
        driver = webdriver.Chrome(options=options)
    
        url_base = (
            "https://casas.mitula.cl/find?"
            "operationType=rent&propertyType=apartment&geoId=R231672"
        )

        # FASE 1: RECOLECCIÓN EN CATÁLOGO (DATOS CRUDOS)
 
        for pagina_actual in range(PAGINA_INICIO, PAGINA_FIN + 1):
    
            if len(catalogo_urls) >= MAX_REGISTROS:
                break
    
            print(f"\n--- [FASE 1] Procesando Página {pagina_actual} ---")
    
            url_pagina = f"{url_base}&page={pagina_actual}"
            driver.get(url_pagina)
    
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "article.listing-card")
                    )
                )
    
                for _ in range(4):
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1)
    
                time.sleep(1)
    
                bloques = driver.find_elements(
                    By.CSS_SELECTOR,
                    "article.listing-card"
                )
    
                for bloque in bloques:
    
                    if len(catalogo_urls) >= MAX_REGISTROS:
                        print(f"\nSe alcanzó el límite de {MAX_REGISTROS} registros.")
                        break
    
                    try:
                        texto_tarjeta = bloque.get_attribute(
                            "textContent"
                        ).lower()
    
                        # UBICACIÓN
        
                        if "coquimbo" in texto_tarjeta:
                            ubicacion = "Coquimbo"
    
                        elif "la serena" in texto_tarjeta:
                            ubicacion = "La Serena"
    
                        else:
                            continue
    

                        # URL REAL
    
                        try:
                            codigo_secreto = bloque.get_attribute(
                                "data-clickdestination"
                            )
    
                            if codigo_secreto:
                                url_decodificada = base64.b64decode(
                                    codigo_secreto
                                ).decode(
                                    "utf-8",
                                    errors="ignore"
                                )
    
                                url = "https://casas.mitula.cl" + url_decodificada
    
                            else:
                                continue
    
                        except:
                            continue
    
                        if not url or "javascript" in url:
                            continue
    
                        # PRECIO (EN BRUTO - SIN LIMPIAR)

                        try:
                            precio_texto = bloque.find_element(
                                By.CSS_SELECTOR,
                                ".price__actual"
                            ).get_attribute("textContent").strip()
    
                        except:
                            precio_texto = "Sin información"
    
                        # M2 / DORMITORIOS / BAÑOS (EN BRUTO)
       
                        m2_texto = "Sin información"
                        dormitorios_texto = "Sin información"
                        banos_texto = "Sin información"
    
                        match_m2 = re.search(
                            r'(\d+\s*(m2|m²|mts))',
                            texto_tarjeta
                        )
                        if match_m2:
                            m2_texto = match_m2.group(1)
    
                        match_dorm = re.search(
                            r'(\d+\s*dormitorio[s]?)',
                            texto_tarjeta
                        )
                        if match_dorm:
                            dormitorios_texto = match_dorm.group(1)
    
                        match_bano = re.search(
                            r'(\d+\s*baño[s]?)',
                            texto_tarjeta
                        )
                        if match_bano:
                            banos_texto = match_bano.group(1)
    
                        # IMAGEN 
    
                        imagen_url = "Sin imagen"
    
                        try:
                            imagen = bloque.find_element(By.TAG_NAME, "img")
                            imagen_url = imagen.get_attribute("src")
    
                            if not imagen_url:
                                imagen_url = "Sin imagen"
    
                        except:
                            pass
    
                        # GUARDADO BASE (DATOS CRUDOS)

                        catalogo_urls.append({
                            "responsable": "Constanza Torres",
                            "fecha_extraccion": time.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
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
    
                print(f"Registros acumulados: {len(catalogo_urls)}")
    
            except TimeoutException:
                print("Advertencia: Mitula tardó en cargar")
                continue

        
        # ELIMINAR DUPLICADOS POR URL

    
        catalogo_urls = list(
            {v["enlace"]: v for v in catalogo_urls}.values()
        )
    
        print(f"\nCatálogo final: {len(catalogo_urls)} propiedades encontradas")
    

        # FASE 2: INSPECCIÓN PROFUNDA

    
        for i, propiedad in enumerate(catalogo_urls):
    
            if (i + 1) % 5 == 0:
                print(
                    f"Progreso FASE 2: {i + 1} de {len(catalogo_urls)}"
                )
    
            propiedad["estacionamiento"] = 0
            propiedad["piscina"] = 0
            propiedad["quincho"] = 0
            propiedad["terraza"] = 0
            propiedad["gimnasio"] = 0
            propiedad["lavanderia"] = 0
    
            try:
                driver.get(propiedad["enlace"])
    
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.TAG_NAME, "body")
                    )
                )
    
                time.sleep(2)
                try:
                    titulo_real = driver.find_element(
                        By.CSS_SELECTOR,
                        "div.main-title"
                    ).get_attribute("textContent").strip()

                    propiedad["titulo"] = titulo_real

                except:
                    propiedad["titulo"] = "Sin título"   

                
                texto_total = driver.find_element(
                    By.TAG_NAME,
                    "body"
                ).get_attribute(
                    "textContent"
                ).lower()
    
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
        if driver is not None:
            driver.quit()
    
    print(
        f"\nExtracción finalizada. "
        f"Total final: {len(datos_finales)} propiedades."
    )
    
    print("\nPrimeros 3 registros extraídos:\n")
    
    for i, d in enumerate(datos_finales[:3], 1):
        print(f"--- Propiedad {i} ---")
        print(d)
        print()
        
    return datos_finales

datosfinales=ejecutar_extracción()