# ==============================================================================
# PROYECTO BIG DATA - GRUPO 2 (REAL ESTATE)
# Script Integrador y Estandarizador Principal (main.py)
# ==============================================================================

import json
import re
import certifi
from pymongo import MongoClient

# Importamos las funciones de cada integrante
from scrapers.scraper_constanza_torres import ejecutar_extracción as scraper_constanza
from scrapers.scraper_millaray_zalazar import scraper_prueba as scraper_millaray
from scrapers.scraper_prueba import ejecutar_extraccion as scraper_jalil
from scrapers.scraper_melany_torres import ejecutar_extraccion as scraper_melany

def limpiar_numero(valor):
    """
    Purificador Universal: Toma cualquier texto (ej. '$ 450.000', '2 m2', 'Sí')
    y devuelve estrictamente el número entero.
    """
    if isinstance(valor, bool): return 1 if valor else 0
    if isinstance(valor, (int, float)): return int(valor)
    if not valor: return 0
    
    texto = str(valor).lower().strip()
    if texto in ["sin información", "error", "inactiva", "sin miniatura", "none", "sin imagen"]:
        return 0
    if texto in ["sí", "si", "true", "yes"]:
        return 1
        
    # Reemplazamos puntos y comas de miles antes de extraer
    texto_sin_separadores = texto.replace('.', '').replace(',', '')
    nums = re.findall(r'\d+', texto_sin_separadores)
    return int(nums[0]) if nums else 0

def estandarizar_registro(reg):
    """
    Mapea el diccionario original de cualquier integrante a un esquema ÚNICO.
    Garantiza que la base de datos sea perfecta.
    """
    # Identificar si la llave se llamaba 'banos' o 'baños'
    banos_raw = reg.get("baños", reg.get("banos", 0))
    # Identificar URL vs Enlace
    url_raw = reg.get("url", reg.get("enlace", "Sin URL"))
    
    return {
        "responsable": reg.get("responsable", "Desconocido"),
        "fecha_extraccion": reg.get("fecha_extraccion", reg.get("fecha_captura", "")),
        "titulo": str(reg.get("titulo", "")).strip(),
        "ubicacion": str(reg.get("ubicacion", "")).strip(),
        
        # Numéricos limpios (int)
        "precio": limpiar_numero(reg.get("precio", 0)),
        "m2": limpiar_numero(reg.get("m2", 0)),
        "dormitorios": limpiar_numero(reg.get("dormitorios", 0)),
        "baños": limpiar_numero(banos_raw),
        
        # Booleanos numéricos (1 o 0)
        "estacionamiento": 1 if limpiar_numero(reg.get("estacionamiento", 0)) > 0 else 0,
        "piscina": 1 if limpiar_numero(reg.get("piscina", 0)) > 0 else 0,
        "quincho": 1 if limpiar_numero(reg.get("quincho", 0)) > 0 else 0,
        "terraza": 1 if limpiar_numero(reg.get("terraza", 0)) > 0 else 0,
        "gimnasio": 1 if limpiar_numero(reg.get("gimnasio", 0)) > 0 else 0,
        "lavanderia": 1 if limpiar_numero(reg.get("lavanderia", 0)) > 0 else 0,
        
        # Textos finales
        "imagen": str(reg.get("imagen", "Sin imagen")),
        "url": str(url_raw)
    }

def ejecutar_pipeline_integrado():
    print("============================================================")
    print(" 🚀 INICIANDO PIPELINE INTEGRADOR BIG DATA - GRUPO 2")
    print("============================================================")
    
    datos_crudos = []

    # --- 1. SCRAPER DE CONSTANZA ---
    print("\n▶️ [1/3] Extrayendo datos: Constanza (Mitula)...")
    try:
        data = scraper_constanza()
        if data: datos_crudos.extend(data)
    except Exception as e: print(f"❌ Error en Constanza: {e}")

    # --- 2. SCRAPER DE MILLARAY ---
    print("\n▶️ [2/3] Extrayendo datos: Millaray (Portal Inmobiliario)...")
    try:
        data = scraper_millaray()
        if data: datos_crudos.extend(data)
    except Exception as e: print(f"❌ Error en Millaray: {e}")

    # --- 3. SCRAPER DE JALIL ---
    print("\n▶️ [3/3] Extrayendo datos: Jalil (Yapo)...")
    try:
        data = scraper_jalil()
        if data: datos_crudos.extend(data)
    except Exception as e: print(f"❌ Error en Jalil: {e}")

    # --- 4. SCRAPER DE MELANY ---
    print("\n▶️ [4/4] Extrayendo datos: Melany (Portal Inmobiliario)...")
    try:
        data = scraper_melany()
        if data: datos_crudos.extend(data)
    except Exception as e: print(f"❌ Error en Melany: {e}")

    # --- 5. LIMPIEZA UNIVERSAL ---
    print("\n" + "="*60)
    print(" 🧼 PURIFICANDO Y ESTANDARIZANDO DATOS...")
    datos_limpios = [estandarizar_registro(reg) for reg in datos_crudos]
    print(f" ✅ {len(datos_limpios)} registros fueron formateados exitosamente.")

    # --- 6. SUBIDA A MONGODB ---
    if datos_limpios:
        URI_ATLAS = "mongodb+srv://bd_realestate:abc123456@c-realestate.xyfip8o.mongodb.net/?retryWrites=true&w=majority&appName=C-RealEstate"
        try:
            print(" 🔌 Conectando a MongoDB Atlas...")
            client = MongoClient(URI_ATLAS, tlsCAFile=certifi.where())
            coleccion = client["Proyecto_RealEstate"]["Integracion_Prueba_Grupo2"]
            coleccion.insert_many(datos_limpios)
            
            print(f" 🎉 ¡ÉXITO! {len(datos_limpios)} registros impecables guardados en Atlas.")
            
            # Imprimimos 1 registro como evidencia en consola
            print("\n 🔍 Evidencia de limpieza (Primer registro en la Nube):")
            ejemplo = datos_limpios[0]
            if "_id" in ejemplo: ejemplo["_id"] = str(ejemplo["_id"])
            print(json.dumps(ejemplo, indent=4, ensure_ascii=False))
            
        except Exception as e:
            print(f" ❌ Error conectando a Atlas: {e}")
    else:
        print(" ⚠️ No se recolectaron datos para subir.")

if __name__ == "__main__":
    ejecutar_pipeline_integrado()