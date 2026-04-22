from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from scrapers.scraper_melany import ejecutar_extraccion

print("🚀 INICIANDO MAIN")

# 1. Ejecutar scraper
data_melany = ejecutar_extraccion()

# 2. Iniciar Spark con conector MongoDB
spark = SparkSession.builder \
    .appName("IntegradoraRealEstate") \
    .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1") \
    .config("spark.mongodb.output.uri", "mongodb+srv://bd_realestate:abc123456@c-realestate.xyfip8o.mongodb.net/BigData_RealEstate?retryWrites=true&w=majority") \
    .config("spark.mongodb.output.database", "BigData_RealEstate") \
    .config("spark.mongodb.output.collection", "propiedades_melany") \
    .getOrCreate()


# 3. Convertir lista a DataFrame
df = spark.createDataFrame(data_melany)

# 4. Limpieza básica
df_limpio = df.filter(col("valor").isNotNull()) \
              .filter(col("valor") > 0)

# 5. Mostrar resultados
print("Datos originales:", df.count())
print("Datos limpios:", df_limpio.count())
df_limpio.show(10, truncate=False)

# 6. Guardar en MongoDB Atlas
df_limpio.write \
    .format("mongo") \
    .mode("append") \
    .save()

print("✅ Proceso finalizado: datos enviados a MongoDB Atlas.")