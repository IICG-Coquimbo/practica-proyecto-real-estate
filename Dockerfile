FROM jupyter/pyspark-notebook:latest

USER root

# 1. Herramientas de Red, SSL y Entorno Gráfico (Xvfb para el scraper)
RUN apt-get update && apt-get install -y \
    ca-certificates \
    openssl \
    curl \
    wget \
    gnupg2 \
    xvfb \
    fluxbox \
    x11vnc \
    supervisor \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Instalamos Brave Browser (o Chromium) para el scraping
RUN curl -fsSLo /usr/share/keyrings/brave-browser-archive-keyring.gpg https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/brave-browser-archive-keyring.gpg] https://brave-browser-apt-release.s3.brave.com/ stable main" | tee /etc/apt/sources.list.d/brave-browser-release.list \
    && apt-get update && apt-get install -y brave-browser

# 3. Librerías de Python para todo el curso (Scraping + Atlas + Spark)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "pymongo[srv]" dnspython certifi selenium webdriver-manager pandas

# 4. Instalación de JARs: Versión 10.3.0 (Compatible con Spark 3.5)
# Limpiamos la carpeta primero para que no queden versiones viejas chocando
RUN rm -f /usr/local/spark/jars/mongo-spark-connector* && \
    rm -f /usr/local/spark/jars/mongodb-driver* && \
    rm -f /usr/local/spark/jars/bson* && \
    wget https://repo1.maven.org/maven2/org/mongodb/spark/mongo-spark-connector_2.12/10.3.0/mongo-spark-connector_2.12-10.3.0.jar -P /usr/local/spark/jars/ \
    && wget https://repo1.maven.org/maven2/org/mongodb/mongodb-driver-sync/4.11.1/mongodb-driver-sync-4.11.1.jar -P /usr/local/spark/jars/

# 5. Configuración de visualización (noVNC)
COPY start-vnc.sh /usr/local/bin/start-vnc.sh
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN sed -i 's/\r$//' /usr/local/bin/start-vnc.sh \
    && chmod +x /usr/local/bin/start-vnc.sh && \
    chown -R jovyan:users /home/jovyan/work

EXPOSE 8888 5900 6080 4040
ENV DISPLAY=:99

# Iniciamos como root para evitar el error de setuid y lanzamos Supervisor
USER root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]