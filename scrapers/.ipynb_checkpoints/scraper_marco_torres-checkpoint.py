# ==============================================================================
# PROYECTO BIG DATA - GRUPO 2 (REAL ESTATE)
# Código Yapo.cl (Coquimbo) - Marco Torres
# ==============================================================================

import os
import time
import re  
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def ejecutar_extraccion():
    # --- PASO 0: LIMPIEZA TOTAL Y REPARACIÓN ---
    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome")
    os.system("pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.*")
    os.system("rm -rf /tmp/.org.chromium.Chromium.*")
    print("🧹 Limpieza completada. Pantalla virtual configurada.")

    # --- VARIABLES GENERALES ---
    RESPONSABLE_EXTRACCION = "Marco Torres"
    META_REGISTROS = 500
    REGISTROS_A_SALTAR = 500 
    TAMANO_TANDA = 100

    propiedades_basicas = [] 
    driver = None        
    total_guardados = 0
    
    datos_totales_marco = []

    # --- PASO 1: CONFIGURACIÓN DEL NAVEGADOR ---
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        print(f"🚀 Navegador iniciado. Fase 1: Buscando {META_REGISTROS + REGISTROS_A_SALTAR} enlaces...")

        url_yapo = "https://www.yapo.cl/bienes-raices-alquiler-apartamentos/chile-es-coquimbo?_gl=1*xrdyl5*_gcl_au*MjQxMDY4NDMuMTc3NjU1NTI1MQ.."
        driver.get(url_yapo)
        
        nivel_pagina = 1

        while len(propiedades_basicas) < (META_REGISTROS + REGISTROS_A_SALTAR):
            print(f"\n--- 📄 Extrayendo tarjetas - Página {nivel_pagina} (Llevamos {len(propiedades_basicas)} enlaces) ---")

            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".d3-ad-tile__content"))
            )
            
            # Scroll Humano
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3) 

            bloques = driver.find_elements(By.CSS_SELECTOR, ".d3-ad-tile__content")

            for bloque in bloques:
                if len(propiedades_basicas) >= (META_REGISTROS + REGISTROS_A_SALTAR):
                    break 

                try:
                    nombre = bloque.find_element(By.CSS_SELECTOR, ".d3-ad-tile__title").get_attribute("textContent")
                    precio_texto = bloque.find_element(By.CSS_SELECTOR, ".d3-ad-tile__price").get_attribute("textContent")
                    
                    if not nombre or not precio_texto or not nombre.strip() or not precio_texto.strip():
                        continue

                    try:
                        direccion = bloque.find_element(By.CSS_SELECTOR, ".d3-ad-tile__location").get_attribute("textContent")
                    except:
                        direccion = "Sin ubicación"

                    enlace = bloque.find_element(By.CSS_SELECTOR, "a.d3-ad-tile__description").get_attribute("href")

                    # Recoger miniatura como respaldo (imagen_fallback)
                    try:
                        imagen_miniatura = bloque.find_element(By.TAG_NAME, "img").get_attribute("src")
                    except:
                        imagen_miniatura = "Sin miniatura"

                    detalles = bloque.find_elements(By.CSS_SELECTOR, ".d3-ad-tile__details-item")
                    dormitorios_txt = "0"
                    banos_txt = "0"
                    estacionamientos_txt = "0"
                    
                    for det in detalles:
                        html_interno = det.get_attribute("innerHTML")
                        texto = det.get_attribute("textContent").strip()
                        if "#bed" in html_interno: dormitorios_txt = texto
                        elif "#bath" in html_interno: banos_txt = texto
                        elif "#parking" in html_interno: estacionamientos_txt = texto

                    propiedades_basicas.append({
                        "titulo": nombre.strip(),
                        "ubicacion": direccion.strip(),
                        "precio_crudo": precio_texto.strip(),
                        "dormitorios_crudo": dormitorios_txt,
                        "banos_crudo": banos_txt,
                        "estac_crudo": estacionamientos_txt,
                        "enlace": enlace,
                        "imagen_fallback": imagen_miniatura
                    })
                except Exception:
                    continue

            if len(propiedades_basicas) < (META_REGISTROS + REGISTROS_A_SALTAR):
                try:
                    btn_sig = driver.find_element(By.XPATH, "//a[contains(@class, 'pagination') and contains(text(), 'Siguiente')] | //a[contains(@class, 'next')]")
                    driver.execute_script("arguments[0].click();", btn_sig)
                    time.sleep(5)
                    nivel_pagina += 1
                except:
                    print("⚠️ No hay más páginas disponibles. Extracción detenida.")
                    break

        # --- RECORTE DE ENLACES SEGÚN OFFSET ---
        print(f"\n✂️ Recortando los primeros {REGISTROS_A_SALTAR} registros...")
        propiedades_basicas = propiedades_basicas[REGISTROS_A_SALTAR : REGISTROS_A_SALTAR + META_REGISTROS]
        print(f"✅ Fase 1 completada. {len(propiedades_basicas)} enlaces listos para inmersión.")

        # --- PASO 2 Y 3: INMERSIÓN Y EXTRACCIÓN EN BRUTO ---
        print("\n🤿 Iniciando Fase 2 y 3: Extracción de datos en bruto e imágenes...")

        for i in range(0, len(propiedades_basicas), TAMANO_TANDA):
            lote_enlaces = propiedades_basicas[i : i + TAMANO_TANDA]
            datos_tanda = []
            
            print(f"\n📦 Procesando tanda {i//TAMANO_TANDA + 1} (Registros {i+1} al {i + len(lote_enlaces)})...")

            for prop in lote_enlaces:
                try:
                    driver.get(prop["enlace"])
                    
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".d3-property-about__text"))
                    )
                    
                    desc_larga = driver.find_element(By.CSS_SELECTOR, ".d3-property-about__text").get_attribute("textContent").strip()
                    texto_busqueda = (prop["titulo"] + " " + desc_larga).lower()
                    
                    # --- EXTRAER IMAGEN PRINCIPAL ---
                    imagen_final = "Sin imagen"
                    try:
                        img_element = driver.find_element(By.CSS_SELECTOR, "img.d3-hero-carousel__photo")
                        src = img_element.get_attribute("src")
                        if src and "data:image" not in src:
                            imagen_final = src
                        else:
                            data_src = img_element.get_attribute("data-src")
                            imagen_final = data_src if data_src else prop["imagen_fallback"]
                    except:
                        imagen_final = prop["imagen_fallback"]

                    # Buscamos metros cuadrados pero mantenemos el texto tal cual
                    m2_match = re.search(r'(\d+)\s*(?:m2|mts|metros)', texto_busqueda)
                    m2_crudo = m2_match.group(0) if m2_match else "Sin especificar"

                    # REGISTRO SIN LIMPIEZA NUMÉRICA (Todo como viene del sitio)
                    registro_crudo = {
                        "responsable": RESPONSABLE_EXTRACCION,
                        "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "titulo": prop["titulo"],
                        "ubicacion": prop["ubicacion"],
                        "m2": m2_crudo,
                        "precio": prop["precio_crudo"],
                        "dormitorios": prop["dormitorios_crudo"],
                        "banos": prop["banos_crudo"], 
                        "estacionamiento": prop["estac_crudo"],
                        "piscina": "1" if "piscina" in texto_busqueda else "0",
                        "quincho": "1" if any(x in texto_busqueda for x in ["quincho", "asador"]) else "0",
                        "terraza": "1" if any(x in texto_busqueda for x in ["terraza", "balcon", "balcón"]) else "0",
                        "gimnasio": "1" if any(x in texto_busqueda for x in ["gimnasio", "gym"]) else "0",
                        "lavanderia": "1" if any(x in texto_busqueda for x in ["lavanderia", "lavandería", "logia"]) else "0",
                        "imagen": imagen_final,
                        "enlace": prop["enlace"] 
                    }

                    datos_tanda.append(registro_crudo)
                    time.sleep(2) 
                    
                except Exception:
                    continue

            if datos_tanda:
                datos_totales_marco.extend(datos_tanda) 
                total_guardados += len(datos_tanda)
                print(f"💾 Tanda finalizada. Registros acumulados: {total_guardados}.")
            
            if i + TAMANO_TANDA < len(propiedades_basicas):
                print("⏱️ Pausa anti-bloqueo (60s)...")
                time.sleep(60)

    except Exception as e:
        print(f"🚨 Error crítico: {e}")

    finally:
        if driver:
            driver.quit()

    # ==============================================================================
    # FASE 3: MOSTRAR LISTA FINAL DE DATOS 
    # ==============================================================================
    print(f"\nExtracción finalizada. Total de propiedades extraídas: {len(datos_totales_marco)}")
    
    # IMPORTANTE: Aquí se limita la impresión solo a los primeros 3 registros
    if datos_totales_marco:
        print("\n" + "="*80)
        print(" MUESTRA DE RESULTADOS FINALES (Primeros 3 registros)")
        print("="*80)

        for idx, dato in enumerate(datos_totales_marco[:3]):
            print(f"\n--- REGISTRO {idx + 1} ---")
            for clave, valor in dato.items():
                mostrar_valor = valor if valor != "" else "[Vacío / No encontrado]"
                print(f" • {clave.capitalize():<18}: {mostrar_valor}")
        
        print("\n" + "="*80)
                
    return datos_totales_marco


# ==============================================================================
# EJECUCIÓN DIRECTA PROTEGIDA
# (Esto asegura que no choque con el main.py)
# ==============================================================================
if __name__ == "__main__":
    datos_de_prueba = ejecutar_extraccion()