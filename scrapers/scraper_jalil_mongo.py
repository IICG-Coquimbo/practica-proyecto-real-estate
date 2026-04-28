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
    """
    Ejecuta el pipeline completo de extracción de Yapo.cl:
    1. Recolección de 500 enlaces base e imagen miniatura.
    2. Minería profunda por propiedad (extrayendo foto de alta calidad e indicadores).
    3. Retorno de lista conservando etiquetas originales con datos en bruto (sin descripción larga).
    """
    # --- PASO 0: LIMPIEZA TOTAL Y REPARACIÓN ---
    # FORZAR LA PANTALLA PARA noVNC
    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome")
    os.system("pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.*")
    os.system("rm -rf /tmp/.org.chromium.Chromium.*")
    print("🧹 Limpieza completada. Pantalla virtual configurada.")

    # --- VARIABLES GENERALES ---
    RESPONSABLE_EXTRACCION = "Jalil" 
    META_REGISTROS = 500
    TAMANO_TANDA = 100

    propiedades_basicas = [] 
    driver = None        
    total_guardados = 0
    
    # Lista maestra que acumulará todos los registros para enviarlos a PySpark
    datos_totales_jalil = [] 

    # --- PASO 1: CONFIGURACIÓN DEL NAVEGADOR ---
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        # Se agrega webdriver_manager para garantizar compatibilidad de versiones
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        print(f"🚀 Navegador iniciado. Fase 1: Buscando {META_REGISTROS} enlaces...")

        url_yapo = "https://www.yapo.cl/bienes-raices-alquiler-apartamentos/chile-es-coquimbo?_gl=1*xrdyl5*_gcl_au*MjQxMDY4NDMuMTc3NjU1NTI1MQ.."
        driver.get(url_yapo)
        
        nivel_pagina = 1

        # Bucle WHILE: Sigue buscando páginas hasta llegar a 500 enlaces
        while len(propiedades_basicas) < META_REGISTROS:
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
                if len(propiedades_basicas) >= META_REGISTROS:
                    break # Rompe si ya llegó a la meta en medio de una página

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

                    # Extracción de la miniatura para respaldo
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

            # Si aún faltan registros, pasamos a la siguiente página
            if len(propiedades_basicas) < META_REGISTROS:
                try:
                    btn_sig = driver.find_element(By.XPATH, "//a[contains(@class, 'pagination') and contains(text(), 'Siguiente')] | //a[contains(@class, 'next')]")
                    driver.execute_script("arguments[0].click();", btn_sig)
                    time.sleep(5)
                    nivel_pagina += 1
                except:
                    print("⚠️ No hay más páginas disponibles. Extracción detenida.")
                    break

        print(f"\n✅ Fase 1 completada. Se capturaron {len(propiedades_basicas)} enlaces exactos.")

        # --- PASO 2 Y 3 COMBINADOS: INMERSIÓN, MINERÍA EN BRUTO Y GUARDADO EN TANDAS ---
        print("\n🤿 Iniciando Fase 2 y 3: Extracción profunda y Guardado por Lotes...")

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
                    
                    # Leemos la descripción para sacar las banderas, pero NO la guardamos en el diccionario final
                    desc_larga = driver.find_element(By.CSS_SELECTOR, ".d3-property-about__text").get_attribute("textContent").strip()
                    texto_busqueda = (prop["titulo"] + " " + desc_larga).lower()
                    
                    # --- Captura de Imagen ---
                    imagen_final = "Sin imagen"
                    try:
                        img_element = driver.find_element(By.CSS_SELECTOR, "img.d3-hero-carousel__photo")
                        src = img_element.get_attribute("src")
                        if src and "data:image" not in src:
                            imagen_final = src
                        else:
                            data_src = img_element.get_attribute("data-src")
                            if data_src:
                                imagen_final = data_src
                            else:
                                imagen_final = prop["imagen_fallback"]
                    except:
                        imagen_final = prop["imagen_fallback"]

                    # --- EXTRACCIÓN MÍNIMA (PARA MANTENER ETIQUETAS, PERO VALORES EN BRUTO) ---
                    m2_match = re.search(r'(\d+)\s*(?:m2|mts|metros)', texto_busqueda)
                    m2_crudo = m2_match.group(0) if m2_match else "0"

                    registro_limpio_pero_crudo = {
                        "responsable": RESPONSABLE_EXTRACCION,
                        "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "titulo": prop["titulo"],
                        "ubicacion": prop["ubicacion"],
                        
                        # ETIQUETAS ORIGINALES PRESERVADAS
                        "m2": m2_crudo, 
                        "precio": prop["precio_crudo"], 
                        "dormitorios": prop["dormitorios_crudo"], 
                        "banos": prop["banos_crudo"], 
                        "estacionamiento": prop["estac_crudo"], 
                        
                        # Banderas en texto
                        "piscina": "1" if "piscina" in texto_busqueda else "0",
                        "quincho": "1" if "quincho" in texto_busqueda or "asador" in texto_busqueda else "0",
                        "terraza": "1" if "terraza" in texto_busqueda or "balcon" in texto_busqueda or "balcón" in texto_busqueda else "0",
                        "gimnasio": "1" if "gimnasio" in texto_busqueda or "gym" in texto_busqueda else "0",
                        "lavanderia": "1" if "lavanderia" in texto_busqueda or "lavandería" in texto_busqueda or "logia" in texto_busqueda else "0",
                        
                        # Adiciones
                        "imagen": imagen_final,
                        "enlace": prop["enlace"]
                    }

                    datos_tanda.append(registro_limpio_pero_crudo)
                    time.sleep(2) # Pausa normal entre páginas
                    
                except Exception as e:
                    continue

            # Al terminar la tanda
            if datos_tanda:
                datos_totales_jalil.extend(datos_tanda) # Acumulamos en la lista maestra
                total_guardados += len(datos_tanda)
                print(f"💾 ¡Tanda guardada exitosamente! Respaldos actuales: {total_guardados}.")
            
            # Pausa larga anti-bot (solo si no es la última tanda)
            if i + TAMANO_TANDA < len(propiedades_basicas):
                print("⏱️ Iniciando pausa de 60 segundos para evitar bloqueos por parte del servidor...")
                time.sleep(60)

        print(f"\n🎉 EXTRACCIÓN MAESTRA COMPLETADA: {total_guardados} propiedades listas.")

    except Exception as e:
        print(f"🚨 Error crítico en la ejecución: {e}")

    finally:
        if driver is not None:
            try:
                driver.quit()
                print("🔒 Navegador cerrado correctamente.")
            except:
                pass
                
    # Retornamos la LISTA MAESTRA
    return datos_totales_jalil

# =======================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# =======================================================
if __name__ == "__main__":
    print("Iniciando script de scraping desde terminal...")
    registros = ejecutar_extraccion()
    print(f"Proceso finalizado. Total guardado: {len(registros)}")
    
    # Opcional: Imprimir un registro para confirmar cómo queda
    if registros:
        print("\n🔍 MUESTRA DEL PRIMER REGISTRO EXTRAÍDO:")
        print(json.dumps(registros[0], indent=4, ensure_ascii=False))