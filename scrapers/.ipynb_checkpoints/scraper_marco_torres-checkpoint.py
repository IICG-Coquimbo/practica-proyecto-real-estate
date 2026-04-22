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
    RESPONSABLE_EXTRACCION = "Marco"
    META_REGISTROS = 500
    REGISTROS_A_SALTAR = 500 #Cantidad de registros que debe ignorar
    TAMANO_TANDA = 100

    propiedades_basicas = [] 
    driver = None        
    total_guardados = 0
    
    datos_totales_companero = [] # MODIFICADO: Lista maestra

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
        # MODIFICADO: Ahora el mensaje refleja la suma
        print(f"🚀 Navegador iniciado. Fase 1: Buscando {META_REGISTROS + REGISTROS_A_SALTAR} enlaces...")

        url_yapo = "https://www.yapo.cl/bienes-raices-alquiler-apartamentos/chile-es-coquimbo?_gl=1*xrdyl5*_gcl_au*MjQxMDY4NDMuMTc3NjU1NTI1MQ.."
        driver.get(url_yapo)
        
        nivel_pagina = 1

        # MODIFICADO: Bucle WHILE ahora busca hasta la suma (ej. 1000 enlaces)
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
                # MODIFICADO: Rompe si ya llegó a 1000
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
                        "enlace": enlace
                    })
                except Exception:
                    continue

            # Si aún faltan registros, pasamos a la siguiente página
            if len(propiedades_basicas) < (META_REGISTROS + REGISTROS_A_SALTAR):
                try:
                    btn_sig = driver.find_element(By.XPATH, "//a[contains(@class, 'pagination') and contains(text(), 'Siguiente')] | //a[contains(@class, 'next')]")
                    driver.execute_script("arguments[0].click();", btn_sig)
                    time.sleep(5)
                    nivel_pagina += 1
                except:
                    print("⚠️ No hay más páginas disponibles. Extracción detenida.")
                    break

        # ====================================================================
        # NUEVO: Recorte de enlaces. Esto es lo que separa ambas partes.
        # ====================================================================
        print(f"\n✂️ Recortando los primeros {REGISTROS_A_SALTAR} registros que ya extrajiste tú...")
        propiedades_basicas = propiedades_basicas[REGISTROS_A_SALTAR : REGISTROS_A_SALTAR + META_REGISTROS]
        
        print(f"✅ Fase 1 completada. Se dejaron {len(propiedades_basicas)} enlaces exactos listos para minería profunda.")

        # --- PASO 2 Y 3 COMBINADOS: INMERSIÓN, MINERÍA Y GUARDADO EN TANDAS ---
        print("\n🤿 Iniciando Fase 2 y 3: Extracción profunda, Minería y Guardado por Lotes...")

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
                    
                    # Limpieza estructural
                    precio_solo_num = re.sub(r"\D", "", prop["precio_crudo"]) 
                    precio_final = float(precio_solo_num) if precio_solo_num else 0.0
                    
                    dorm_final = int(''.join(filter(str.isdigit, str(prop["dormitorios_crudo"]))) or 0)
                    banos_final = int(''.join(filter(str.isdigit, str(prop["banos_crudo"]))) or 0)
                    
                    estac_num = int(''.join(filter(str.isdigit, str(prop["estac_crudo"]))) or 0)
                    estac_final = 1 if estac_num > 0 else 0

                    m2_match = re.search(r'(\d+)\s*(?:m2|mts|metros)', texto_busqueda)
                    m2_final = int(m2_match.group(1)) if m2_match else 0

                    registro_limpio = {
                        "responsable": RESPONSABLE_EXTRACCION,
                        "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "titulo": prop["titulo"],
                        "ubicacion": prop["ubicacion"],
                        "m2": m2_final,
                        "precio": precio_final,
                        "dormitorios": dorm_final,
                        "banos": banos_final, 
                        "estacionamiento": estac_final,
                        "piscina": 1 if "piscina" in texto_busqueda else 0,
                        "quincho": 1 if "quincho" in texto_busqueda or "asador" in texto_busqueda else 0,
                        "terraza": 1 if "terraza" in texto_busqueda or "balcon" in texto_busqueda or "balcón" in texto_busqueda else 0,
                        "gimnasio": 1 if "gimnasio" in texto_busqueda or "gym" in texto_busqueda else 0,
                        "lavanderia": 1 if "lavanderia" in texto_busqueda or "lavandería" in texto_busqueda or "logia" in texto_busqueda else 0,
                        "enlace": prop["enlace"] 
                    }

                    datos_tanda.append(registro_limpio)
                    time.sleep(2) 
                    
                except Exception as e:
                    continue

            # Al terminar la tanda de 100
            if datos_tanda:
                datos_totales_companero.extend(datos_tanda) 
                total_guardados += len(datos_tanda)
                print(f"💾 ¡Tanda guardada exitosamente! Respaldos actuales: {total_guardados}.")
            
            # Pausa larga anti-bot (solo si no es la última tanda)
            if i + TAMANO_TANDA < len(propiedades_basicas):
                print("⏱️ Iniciando pausa de 60 segundos para evitar bloqueos por parte del servidor...")
                time.sleep(60)

        print(f"\n🎉 EXTRACCIÓN MAESTRA COMPLETADA: {total_guardados} propiedades listas para PySpark.")

    except Exception as e:
        print(f"🚨 Error crítico en la ejecución: {e}")

    finally:
        if driver is not None:
            try:
                driver.quit()
                print("🔒 Navegador cerrado correctamente.")
            except:
                pass
                
    return datos_totales_marco

if __name__ == "__main__":
    print("🧪 Iniciando prueba en seco (Sin base de datos)...")
    
    # Llamamos a la función y guardamos la lista que retorna en una variable
    datos_obtenidos = ejecutar_extraccion()
    
    # Imprimimos un resumen
    print("\n" + "="*50)
    print(f"✅ PRUEBA FINALIZADA. SE OBTUVIERON {len(datos_obtenidos)} REGISTROS.")
    print("="*50 + "\n")
    
    # Para no inundar la consola si extraes 500, imprimimos solo los 3 primeros registros
    # Usamos json.dumps para que se imprima con un formato bonito y legible
    if datos_obtenidos:
        print("👀 Mostrando una muestra de los primeros 3 registros extraídos:\n")
        muestra = datos_obtenidos[:3] 
        print(json.dumps(muestra, indent=4, ensure_ascii=False))
    else:
        print("⚠️ La lista está vacía. Revisa si hubo algún error en la extracción.")