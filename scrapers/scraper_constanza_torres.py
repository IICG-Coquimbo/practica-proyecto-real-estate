import os
import time
import re
import base64  
import random # <-- NUEVO: Para simular comportamiento humano
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def ejecutar_extraccion():
    """
    Ejecuta la extracción del portal Mitula.
    Retorna una lista de diccionarios lista para ser unificada en PySpark.
    """
    # --- CONFIGURACIÓN PARA ASIGNACIÓN DE PÁGINAS---
    PAGINA_INICIO = 1  
    PAGINA_FIN = 21
    # ----------------------------------------------

    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome && pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.* && rm -rf /tmp/.org.chromium.Chromium.*")
    print(f"🧹 Entorno virtual listo. Asignación Mitula: Páginas {PAGINA_INICIO} a la {PAGINA_FIN}.")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
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

        url_base = "https://casas.mitula.cl/find?operationType=rent&propertyType=apartment&geoId=R231672"

        # ==============================================================================
        # FASE 1: RECOLECCIÓN
        # ==============================================================================
        for pagina_actual in range(PAGINA_INICIO, PAGINA_FIN + 1):
            print(f"\n--- [FASE 1] Procesando Página {pagina_actual} ---")
            url_pagina = f"{url_base}&page={pagina_actual}"
            driver.get(url_pagina)
            
            # 🛡️ INTERVENCIÓN HUMANA SOLO EN LA PÁGINA 1
            if pagina_actual == 1:
                print("👀 ¡VE A TU PESTAÑA DE noVNC AHORA!")
                print("🛑 Tienes 20 segundos... Si ves un CAPTCHA o botón de 'Soy Humano', haz clic en él manualmente.")
                time.sleep(20)
            else:
                # Pausa normal para el resto de páginas
                time.sleep(random.uniform(3.5, 6.0))

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.listing-card"))
                )

                for _ in range(4):
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(random.uniform(0.5, 1.2))

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
                        if match_m2: m2 = int(match_m2.group(1))

                        match_dorm = re.search(r'(\d+)\s*dormitorio', texto_tarjeta)
                        if match_dorm: dormitorios = int(match_dorm.group(1))

                        match_bano = re.search(r'(\d+)\s*baño', texto_tarjeta)
                        if match_bano: banos = int(match_bano.group(1))

                        # DICCIONARIO ESTANDARIZADO
                        catalogo_urls.append({
                            "responsable": "Constanza Torres",
                            "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "titulo": "Departamento Mitula",
                            "ubicacion": ubicacion,
                            "m2": m2,
                            "precio": precio,
                            "dormitorios": dormitorios,
                            "banos": banos, 
                            "estacionamiento": 0, 
                            "piscina": 0,
                            "quincho": 0,
                            "terraza": 0,
                            "gimnasio": 0,
                            "lavanderia": 0,
                            "enlace": url 
                        })
                    except:
                        continue

            except TimeoutException:
                print(f"⚠️ Alerta: No se encontraron tarjetas en la página {pagina_actual}.")
                continue

        print(f"\n✅ Catálogo listo: {len(catalogo_urls)} propiedades encontradas.")

        # ==============================================================================
        # FASE 2: MINERÍA PROFUNDA
        # ==============================================================================
        print("\n🤿 Iniciando Fase 2: Extracción profunda de amenidades...")
        for i, propiedad in enumerate(catalogo_urls):
            try:
                driver.get(propiedad["enlace"])
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                texto_total = driver.find_element(By.TAG_NAME, "body").text.lower()

                if "estacionamiento" in texto_total: propiedad["estacionamiento"] = 1
                if "piscina" in texto_total: propiedad["piscina"] = 1
                if "quincho" in texto_total: propiedad["quincho"] = 1
                if "terraza" in texto_total: propiedad["terraza"] = 1
                if "gimnasio" in texto_total: propiedad["gimnasio"] = 1
                if "lavander" in texto_total: propiedad["lavanderia"] = 1

            except:
                pass

            # Acumulamos en la lista final que será retornada a PySpark
            datos_finales.append(propiedad)
            print(f"Propiedad procesada ({i+1}/{len(catalogo_urls)})")
            
            # Pausa humana para no saturar el servidor
            time.sleep(random.uniform(1.5, 3.0))

    except Exception as e:
        print(f"🚨 Error crítico en Selenium: {e}")

    finally:
        if driver:
            driver.quit()
            print("🔒 Navegador cerrado correctamente.")

    print(f"\n🎉 Extracción Mitula finalizada. Total: {len(datos_finales)} propiedades listas para PySpark.")
    return datos_finales

# =======================================================
if __name__ == "__main__":
    print("Iniciando script de scraping desde terminal...")
    registros = ejecutar_extraccion()