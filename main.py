# ==============================================================================
# PROYECTO BIG DATA - GRUPO (REAL ESTATE)
# Script Maestro de Integración y Limpieza (main.py)
# ==============================================================================

import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, trim, regexp_replace

# ==============================================================================
# 1. IMPORTACIONES BLINDADAS (Si un archivo falla, los demás se salvan)
# ==============================================================================
try:
    from scrapers import scraper_anais_araya
except Exception as e:
    print(f"⚠️ Error importando Anaís: {e}")
    scraper_anais_araya = None

try:
    from scrapers import scraper_constanza_torres
except Exception as e:
    print(f"⚠️ Error importando Constanza: {e}")
    scraper_constanza_torres = None

try:
    from scrapers import scraper_jalil_ahure
except Exception as e:
    print(f"⚠️ Error importando Jalil: {e}")
    scraper_jalil_ahure = None

try:
    from scrapers import scraper_marco_torres
except Exception as e:
    print(f"⚠️ Error importando Marco: {e}")
    scraper_marco_torres = None

try:
    from scrapers import scraper_melany_torres
except Exception as e:
    print(f"⚠️ Error importando Melany: {e}")
    scraper_melany_torres = None

try:
    from scrapers import scraper_millaray_zalazar
except Exception as e:
    print(f"⚠️ Error importando Millaray: {e}")
    scraper_millaray_zalazar = None


def ejecutar_pipeline_maestro():
    print("\n⏳ Iniciando la extracción web MASIVA. ¡Ve por un café, esto tomará tiempo!...")
    
    data_anais, data_constanza, data_jalil = [], [], []
    data_marco, data_melany, data_millaray = [], [], []

    # ==============================================================================
    # 2. EJECUCIÓN SECUENCIAL ROBUSTA (EN EL ORDEN SOLICITADO)
    # ==============================================================================
    
    # 1. CONSTANZA
    if scraper_constanza_torres:
        print("\n--- INICIANDO EXTRACCIÓN CONSTANZA (MITULA) ---")
        try:
            data_constanza = scraper_constanza_torres.ejecutar_extraccion()
        except Exception as e:
            print(f"❌ Error durante ejecución de Constanza: {e}")

    # 2. ANAÍS
    if scraper_anais_araya:
        print("\n--- INICIANDO EXTRACCIÓN ANAÍS (CHILEPROPIEDADES) ---")
        try:
            data_anais = scraper_anais_araya.ejecutar_extraccion()
        except Exception as e:
            print(f"❌ Error durante ejecución de Anaís: {e}")

    # 3. MILLARAY
    if scraper_millaray_zalazar:
        print("\n--- INICIANDO EXTRACCIÓN MILLARAY (PORTAL INMOBILIARIO - CQ) ---")
        try:
            data_millaray = scraper_millaray_zalazar.extraccion_datos()
        except Exception as e:
            print(f"❌ Error durante ejecución de Millaray: {e}")

    # 4. MELANY
    if scraper_melany_torres:
        print("\n--- INICIANDO EXTRACCIÓN MELANY (PORTAL INMOBILIARIO - LS) ---")
        try:
            data_melany = scraper_melany_torres.ejecutar_extraccion()
        except Exception as e:
            print(f"❌ Error durante ejecución de Melany: {e}")

    # 5. JALIL
    if scraper_jalil_ahure:
        print("\n--- INICIANDO EXTRACCIÓN JALIL (YAPO) ---")
        try:
            data_jalil = scraper_jalil_ahure.ejecutar_extraccion()
        except Exception as e:
            print(f"❌ Error durante ejecución de Jalil: {e}")

    # 6. MARCO
    if scraper_marco_torres:
        print("\n--- INICIANDO EXTRACCIÓN MARCO (YAPO) ---")
        try:
            data_marco = scraper_marco_torres.ejecutar_extraccion()
        except Exception as e:
            print(f"❌ Error durante ejecución de Marco: {e}")


    print(f"\n✅ Extracciones finalizadas.")
    print(f"Resultados -> Constanza: {len(data_constanza)} | Anaís: {len(data_anais)} | Millaray: {len(data_millaray)} | Melany: {len(data_melany)} | Jalil: {len(data_jalil)} | Marco: {len(data_marco)}")

    # ==============================================================================
    # 3. PUNTO DE CONTROL FLEXIBLE (AVISA PERO CONTINÚA)
    # ==============================================================================
    fallos = []
    if not data_constanza: fallos.append("Constanza (Mitula)")
    if not data_anais: fallos.append("Anaís (ChilePropiedades)")
    if not data_millaray: fallos.append("Millaray (PortalInmobiliario - CQ)")
    if not data_melany: fallos.append("Melany (PortalInmobiliario - LS)")
    if not data_jalil: fallos.append("Jalil (Yapo)")
    if not data_marco: fallos.append("Marco (Yapo)")

    if fallos:
        print(f"\n⚠️ ADVERTENCIA: La extracción está incompleta. Los siguientes scrapers devolvieron 0 registros:")
        for f in fallos:
            print(f"   - {f}")
        print("⏭️ Continuando de todas formas. Se unificarán y guardarán los datos de los scrapers exitosos.")

    # ==============================================================================
    # 4. INICIAMOS PYSPARK Y CONVERTIMOS A DATAFRAMES
    # ==============================================================================
    # URI base, le quitamos la BD al final para configurarlo explícitamente abajo
    URI_MONGO = "mongodb+srv://bd_realestate:abc123456@c-realestate.xyfip8o.mongodb.net/"

    spark = SparkSession.builder \
        .appName("IntegradoraBigData_Inmobiliaria") \
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1") \
        .getOrCreate()

    print("\n⚙️ PySpark: Transformando listas a DataFrames...")
    df_anais = spark.createDataFrame(data_anais) if data_anais else None
    df_constanza = spark.createDataFrame(data_constanza) if data_constanza else None
    df_jalil = spark.createDataFrame(data_jalil) if data_jalil else None
    df_marco = spark.createDataFrame(data_marco) if data_marco else None
    df_melany = spark.createDataFrame(data_melany) if data_melany else None
    df_millaray = spark.createDataFrame(data_millaray) if data_millaray else None

    # Unimos todos los DataFrames que SÍ tengan datos
    lista_dfs = [df for df in [df_constanza, df_anais, df_millaray, df_melany, df_jalil, df_marco] if df is not None]

    if not lista_dfs:
        print("❌ Error Crítico: Ningún scraper devolvió datos. No hay nada que procesar o guardar. Abortando.")
        spark.stop()
        return

    df_final = lista_dfs[0]
    for df in lista_dfs[1:]:
        df_final = df_final.unionByName(df, allowMissingColumns=True)

    # ==============================================================================
    # 5. LIMPIEZA Y TRANSFORMACIÓN EN SPARK (Casteos a Entero)
    # ==============================================================================
    print("🧹 PySpark: Iniciando limpieza, estandarización numérica y Upsert ID...")
    
    df_limpio = df_final \
        .dropDuplicates(["enlace"]) \
        .withColumn("precio", regexp_replace(col("precio"), "[^0-9]", "").cast("int")) \
        .withColumn("m2", regexp_replace(col("m2"), "[^0-9]", "").cast("int")) \
        .withColumn("dormitorios", regexp_replace(col("dormitorios"), "[^0-9]", "").cast("int")) \
        .withColumn("banos", regexp_replace(col("banos"), "[^0-9]", "").cast("int")) \
        .withColumn("estacionamiento", regexp_replace(col("estacionamiento"), "[^0-9]", "").cast("int")) \
        .withColumn("piscina", col("piscina").cast("int")) \
        .withColumn("quincho", col("quincho").cast("int")) \
        .withColumn("terraza", col("terraza").cast("int")) \
        .withColumn("gimnasio", col("gimnasio").cast("int")) \
        .withColumn("lavanderia", col("lavanderia").cast("int")) \
        .withColumn("ubicacion", trim(lower(col("ubicacion")))) \
        .filter(col("precio") > 1000) \
        .withColumn("_id", col("enlace")) 

    total_limpios = df_limpio.count()
    print(f"📊 Registros unificados, convertidos a enteros y listos para BD: {total_limpios}")

    # ==============================================================================
    # 6. SUBIDA A MONGODB (Modo Upsert) -> [Sintaxis actualizada v3.0+]
    # ==============================================================================
    print("☁️ Subiendo datos a MongoDB Atlas (Actualizando existentes, insertando nuevos)...")
    
    try:
        df_limpio.write \
            .format("mongodb") \
            .option("spark.mongodb.connection.uri", URI_MONGO) \
            .option("spark.mongodb.database", "BD_RealEstate") \
            .option("spark.mongodb.collection", "Propiedades") \
            .mode("append") \
            .save()
        print("🎉 ¡INTEGRACIÓN EXITOSA DEL GRUPO RealEstate! Datos limpios y estructurados en 'BD_RealEstate'.")
    except Exception as e:
        print(f"❌ Error al guardar en MongoDB: {e}")

    spark.stop()

if __name__ == "__main__":
    ejecutar_pipeline_maestro()