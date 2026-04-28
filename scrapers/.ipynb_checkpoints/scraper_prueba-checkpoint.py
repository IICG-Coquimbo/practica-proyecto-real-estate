import os
import time
import re  
import json 
import certifi # Para los certificados de seguridad de Atlas
from pymongo import MongoClient # Para la conexión a la base de datos
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def ejecutar_extraccion():
    """
    Ejecuta el pipeline de PRUEBA de extracción de Yapo.cl y lo guarda en ATLAS:
    1. Recolección de 5 enlaces base e imagen miniatura.
    2. Minería profunda por propiedad.
    3. Guardado directo de la lista resultante en MongoDB Atlas.
    """
    # --- PASO 0: LIMPIEZA TOTAL Y REPARACIÓN ---
    os.environ["DISPLAY"] = ":99"  
    os.system("pkill -9 chrome")
    os.system("pkill -9 chromedriver")
    os.system("rm -rf /tmp/.com.google.Chrome.*")
    os.system("rm -rf /tmp/.org.chromium.Chromium.*")
    print("🧹 Limpieza completada. Pantalla virtual configurada.")

    # --- NUEVO: CONFIGURACIÓN MONGODB ATLAS ---
    URI_ATLAS = "mongodb+srv://bd_realestate:abc123456@c-realestate.xyfip8o.mongodb.net/?retryWrites=true&w=majority&appName=C-RealEstate"
    
    try:
        print("🔌 Conectando a MongoDB Atlas...")
        client = MongoClient(URI_ATLAS, tlsCAFile=certifi.where())
        db = client["Proyecto_RealEstate"] 
        coleccion = db["Prueba_Yapo"]
        print("✅ Conexión exitosa a la base de datos en la nube.")
    except Exception as e:
        print(f"❌ Error conectando a Atlas: {e}")
        return []

    # --- VARIABLES GENERALES (PARA PRUEBA) ---
    RESPONSABLE_EXTRACCION = "Jalil" 
    META_REGISTROS = 5  # Solo 5 para la prueba
    TAMANO_TANDA = 5    # Procesa los 5 de una vez

    propiedades_basicas = [] 
    driver = None        
    total_guardados = 0
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
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        print(f"🚀 Navegador iniciado. Fase 1: Buscando {META_REGISTROS} enlaces de prueba...")

        url_yapo = "https://www.yapo.cl/bienes-raices-alquiler-apartamentos/chile-es-coquimbo?_gl=1*xrdyl5*_gcl_au*MjQxMDY4NDMuMTc3NjU1NTI1MQ.."
        driver.get(url_yapo)
        
        nivel_pagina = 1

        while len(propiedades_basicas) < META_REGISTROS:
            print(f"\n--- 📄 Extrayendo tarjetas - Página {nivel_pagina} (Llevamos {len(propiedades_basicas)} enlaces) ---")

            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".d3-ad-tile__content"))
            )
            
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3) 

            bloques = driver.find_elements(By.CSS_SELECTOR, ".d3-ad-tile__content")

            for bloque in bloques:
                if len(propiedades_basicas) >= META_REGISTROS:
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

            if len(propiedades_basicas) < META_REGISTROS:
                try:
                    btn_sig = driver.find_element(By.XPATH, "//a[contains(@class, 'pagination') and contains(text(), 'Siguiente')] | //a[contains(@class, 'next')]")
                    driver.execute_script("arguments[0].click();", btn_sig)
                    time.sleep(5)
                    nivel_pagina += 1
                except:
                    print("⚠️ No hay más páginas disponibles.")
                    break

        print(f"\n✅ Fase 1 completada. Se capturaron {len(propiedades_basicas)} enlaces exactos.")

        # --- PASO 2: INMERSIÓN Y MINERÍA EN BRUTO ---
        print("\n🤿 Iniciando Fase 2: Extracción profunda e Imagen...")

        for i in range(0, len(propiedades_basicas), TAMANO_TANDA):
            lote_enlaces = propiedades_basicas[i : i + TAMANO_TANDA]
            datos_tanda = []
            
            print(f"\n📦 Procesando tanda de prueba (Registros {i+1} al {i + len(lote_enlaces)})...")

            for prop in lote_enlaces:
                try:
                    driver.get(prop["enlace"])
                    
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".d3-property-about__text"))
                    )
                    
                    desc_larga = driver.find_element(By.CSS_SELECTOR, ".d3-property-about__text").get_attribute("textContent").strip()
                    texto_busqueda = (prop["titulo"] + " " + desc_larga).lower()
                    
                    # Captura de Imagen
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

                    # EXTRACCIÓN MÍNIMA (MANTIENE ETIQUETAS ORIGINALES, VALORES EN BRUTO)
                    m2_match = re.search(r'(\d+)\s*(?:m2|mts|metros)', texto_busqueda)
                    m2_crudo = m2_match.group(0) if m2_match else "0"

                    registro_limpio_pero_crudo = {
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
                        "quincho": "1" if "quincho" in texto_busqueda or "asador" in texto_busqueda else "0",
                        "terraza": "1" if "terraza" in texto_busqueda or "balcon" in texto_busqueda or "balcón" in texto_busqueda else "0",
                        "gimnasio": "1" if "gimnasio" in texto_busqueda or "gym" in texto_busqueda else "0",
                        "lavanderia": "1" if "lavanderia" in texto_busqueda or "lavandería" in texto_busqueda or "logia" in texto_busqueda else "0",
                        
                        "imagen": imagen_final,
                        "enlace": prop["enlace"]
                    }

                    datos_tanda.append(registro_limpio_pero_crudo)
                    time.sleep(2) 
                    
                except Exception as e:
                    continue

            if datos_tanda:
                datos_totales_jalil.extend(datos_tanda) 
                total_guardados += len(datos_tanda)

        print(f"\n🎉 EXTRACCIÓN DE PRUEBA COMPLETADA: {total_guardados} propiedades preparadas.")

        # --- NUEVO PASO 3: GUARDADO EN MONGO ATLAS ---
        if datos_totales_jalil:
            print(f"\n☁️ Subiendo {len(datos_totales_jalil)} registros a MongoDB Atlas...")
            try:
                coleccion.insert_many(datos_totales_jalil)
                print("✅ ¡Carga exitosa! Tus datos ya están en la nube.")
            except Exception as e:
                print(f"❌ Error al guardar los datos en Atlas: {e}")

    except Exception as e:
        print(f"🚨 Error crítico en la ejecución: {e}")

    finally:
        if driver is not None:
            try:
                driver.quit()
                print("🔒 Navegador cerrado correctamente.")
            except:
                pass
                
    return datos_totales_jalil

# =======================================================
# BLOQUE DE EJECUCIÓN DIRECTA E IMPRESIÓN
# =======================================================
if __name__ == "__main__":
    print("Iniciando script de scraping de PRUEBA hacia ATLAS...\n")
    
    registros_extraidos = ejecutar_extraccion()
    
    print("\n" + "="*60)
    print("🖨️  IMPRIMIENDO LOS 5 REGISTROS ENVIADOS A ATLAS")
    print("="*60)
    
    if registros_extraidos:
        for index, registro in enumerate(registros_extraidos):
            print(f"\n--- PROPIEDAD N° {index + 1} ---")
            
            # Eliminamos el _id de Mongo solo para la impresión visual
            registro_visual = registro.copy()
            if "_id" in registro_visual:
                registro_visual["_id"] = str(registro_visual["_id"])
                
            print(json.dumps(registro_visual, indent=4, ensure_ascii=False))
            
        print("\n" + "="*60)
        print("🎯 Proceso finalizado. Verifica los datos en tu Base de Datos.")
    else:
        print("⚠️ No se extrajo ningún registro.")