from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, trim
# 1. Importamos TODOS los scrapers del equipo
from scrapers import (
    scraper_jalil_ahure, 
    scraper_constanza_torres, 
    scraper_millaray_zalazar1, 
    scraper_millaray_zalazar2, 
    scraper_millaray_zalazar3
)

print("⏳ Iniciando la extracción web MASIVA. ¡Ve por un café, esto tomará tiempo!...")

# 2. Ejecución secuencial de los scrapers
print("\n--- INICIANDO EXTRACCIÓN JALIL (YAPO) ---")
data_jalil = scraper_jalil_ahure.ejecutar_extraccion()

print("\n--- INICIANDO EXTRACCIÓN CONSTANZA (MITULA) ---")
data_constanza = scraper_constanza_torres.ejecutar_extraccion()

print("\n--- INICIANDO EXTRACCIÓN MILLARAY - PARTE 1 (PORTAL INMOBILIARIO) ---")
data_millaray_1 = scraper_millaray_zalazar1.ejecutar_extraccion()

print("\n--- INICIANDO EXTRACCIÓN MILLARAY - PARTE 2 (PORTAL INMOBILIARIO) ---")
data_millaray_2 = scraper_millaray_zalazar2.ejecutar_extraccion()

print("\n--- INICIANDO EXTRACCIÓN MILLARAY - PARTE 3 (PORTAL INMOBILIARIO) ---")
data_millaray_3 = scraper_millaray_zalazar3.ejecutar_extraccion()

print(f"\n✅ Extracciones finalizadas.")
print(f"Resultados -> Jalil: {len(data_jalil)} | Constanza: {len(data_constanza)} | Millaray: {len(data_millaray_1) + len(data_millaray_2) + len(data_millaray_3)}")

# ==============================================================================
# PUNTO DE CONTROL FLEXIBLE (AVISA PERO CONTINÚA)
# ==============================================================================
fallos = []
if not data_jalil: fallos.append("Jalil (Yapo)")
if not data_constanza: fallos.append("Constanza (Mitula)")
if not data_millaray_1: fallos.append("Millaray Parte 1")
if not data_millaray_2: fallos.append("Millaray Parte 2")
if not data_millaray_3: fallos.append("Millaray Parte 3")

if fallos:
    print(f"\n⚠️ ADVERTENCIA: La extracción está incompleta. Los siguientes scrapers devolvieron 0 registros:")
    for f in fallos:
        print(f"   - {f}")
    print("⏭️ Continuando de todas formas. Se unificarán y guardarán los datos de los scrapers exitosos.")
# ==============================================================================

# 3. Iniciamos PySpark 
URI_MONGO = "mongodb+srv://bd_realestate:abc123456@c-realestate.xyfip8o.mongodb.net/RealEstate.Consolidado?retryWrites=true&w=majority"

spark = SparkSession.builder \
    .appName("IntegradoraBigData_Inmobiliaria") \
    .config("spark.mongodb.output.uri", URI_MONGO) \
    .getOrCreate()

# 4. Convertimos a DataFrames de Spark (A prueba de listas vacías)
print("\n⚙️ PySpark: Transformando listas a DataFrames...")
df_jalil = spark.createDataFrame(data_jalil) if data_jalil else None
df_constanza = spark.createDataFrame(data_constanza) if data_constanza else None
df_m1 = spark.createDataFrame(data_millaray_1) if data_millaray_1 else None
df_m2 = spark.createDataFrame(data_millaray_2) if data_millaray_2 else None
df_m3 = spark.createDataFrame(data_millaray_3) if data_millaray_3 else None

# 5. Unimos todos los DataFrames que SÍ tengan datos
lista_dfs = [df for df in [df_jalil, df_constanza, df_m1, df_m2, df_m3] if df is not None]

# Solo se detendrá si ABSOLUTAMENTE TODOS fallaron
if not lista_dfs:
    print("❌ Error Crítico: Ningún scraper devolvió datos. No hay nada que procesar o guardar. Abortando.")
    spark.stop()
    exit()

df_final = lista_dfs[0]
for df in lista_dfs[1:]:
    df_final = df_final.unionByName(df, allowMissingColumns=True)

# 6. Limpieza y Transformación en Spark
print("🧹 PySpark: Iniciando limpieza y eliminación de duplicados...")
df_limpio = df_final \
    .dropDuplicates(["enlace"]) \
    .filter(col("precio") > 1000) \
    .withColumn("ubicacion", trim(lower(col("ubicacion"))))

total_limpios = df_limpio.count()
print(f"📊 Registros unificados, limpios y sin duplicados listos para BD: {total_limpios}")

# 7. Subida a MongoDB
print("☁️ Subiendo datos consolidados a MongoDB Atlas...")
# Modo "overwrite" para reemplazar toda la base y mantener solo lo fresco
df_limpio.write.format("mongodb").mode("overwrite").save()

print("🎉 ¡INTEGRACIÓN EXITOSA DEL GRUPO 2! Los datos están en la nube.")
spark.stop()