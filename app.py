import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# 1. Configuración de página (Obligatorio como primera instrucción)
st.set_page_config(page_title="Dashboard Inmobiliario Profesional", page_icon="🏢", layout="wide")

# 2. Inyección CSS Avanzada para control absoluto de contraste y colores
st.markdown("""
    <style>
        /* Fondo de la app blanco */
        .stApp {
            background-color: #FFFFFF;
        }
        /* Texto general en negro */
        p, span, div, label, li {
            color: #000000 !important;
        }
        /* Títulos en rojo */
        h1, h2, h3, h4, h5, h6 {
            color: #C62828 !important; 
            font-family: 'Segoe UI', sans-serif;
        }
        /* Barra lateral gris claro limpio */
        [data-testid="stSidebar"] {
            background-color: #F8F9FA;
            border-right: 1px solid #E0E0E0;
        }
        /* Personalización de los radio buttons en la barra lateral */
        div[data-testid="stRadio"] label {
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 5px;
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
        }

        /* ======================================================= */
        /* DISEÑO DE BOTONES [1] [2] [3] [4] [5] CON ALTO CONTRASTE   */
        /* ======================================================= */
        
        /* BOTÓN NO SELECCIONADO: Blanco, borde negro, texto negro */
        div.stButton > button[kind="secondary"], 
        div.stButton > button:not([kind="primary"]) {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 2px solid #000000 !important;
            border-radius: 6px !important;
            font-weight: bold !important;
            transition: all 0.2s ease-in-out;
        }
        
        /* BOTÓN SELECCIONADO: Rojo, borde blanco, texto blanco */
        div.stButton > button[kind="primary"] {
            background-color: #C62828 !important;
            color: #FFFFFF !important;
            border: 2px solid #FFFFFF !important;
            border-radius: 6px !important;
            font-weight: bold !important;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.15) !important;
        }

        /* EFECTO HOVER (Pasar el mouse por encima de los no seleccionados) */
        div.stButton > button[kind="secondary"]:hover {
            background-color: #F5F5F5 !important;
            border-color: #C62828 !important;
            color: #C62828 !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Inicializar el estado de la sesión para el filtro de dormitorios
if 'dormitorios_sel' not in st.session_state:
    st.session_state.dormitorios_sel = 1 # Valor inicial por defecto

# ==========================================
# SECCIÓN LATERAL: Lista de Indicadores
# ==========================================
st.sidebar.title("📋 Menú de Indicadores")
st.sidebar.markdown("Selecciona el KPI macro que deseas analizar en el panel principal:")

kpi_seleccionado = st.sidebar.radio(
    "Indicadores Disponibles:",
    options=[
        "Precio Promedio por Metro Cuadrado",
        "Precio de Arriendo Promedio Total",
        "Volumen Absoluto de Propiedades"
    ]
)

st.sidebar.divider()
st.sidebar.write(f"**KPI Activo:** \n{kpi_seleccionado}")

# ==========================================
# SECCIÓN PRINCIPAL: Título y Filtro por Botones
# ==========================================
st.title("🏢 Panel de Control Estratégico")
st.markdown("### Análisis Dinámico por Tipología Estructural")
st.divider()

# Carga de Datos (con caché para optimizar memoria en Docker)
@st.cache_data 
def cargar_datos():
    return pd.read_csv("semanas/Semana 15/datos_kpi_real_estate.csv")

try:
    df = cargar_datos()
    
    st.markdown("#### 🚪 Seleccione la cantidad de Dormitorios:")
    
    # Fila de 5 columnas para alojar los botones [1] [2] [3] [4] [5]
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # El truco aquí es alternar dinámicamente entre "primary" (rojo) y "secondary" (blanco)
    with col1:
        if st.button(" [ 1 ] ", key="btn_1", use_container_width=True, type="primary" if st.session_state.dormitorios_sel == 1 else "secondary"):
            st.session_state.dormitorios_sel = 1
    with col2:
        if st.button(" [ 2 ] ", key="btn_2", use_container_width=True, type="primary" if st.session_state.dormitorios_sel == 2 else "secondary"):
            st.session_state.dormitorios_sel = 2
    with col3:
        if st.button(" [ 3 ] ", key="btn_3", use_container_width=True, type="primary" if st.session_state.dormitorios_sel == 3 else "secondary"):
            st.session_state.dormitorios_sel = 3
    with col4:
        if st.button(" [ 4 ] ", key="btn_4", use_container_width=True, type="primary" if st.session_state.dormitorios_sel == 4 else "secondary"):
            st.session_state.dormitorios_sel = 4
    with col5:
        if st.button(" [ 5 ] ", key="btn_5", use_container_width=True, type="primary" if st.session_state.dormitorios_sel == 5 else "secondary"):
            st.session_state.dormitorios_sel = 5

    # Filtrado final usando la variable de sesión
    df_filtrado = df[df["dormitorios"] == st.session_state.dormitorios_sel]

    st.markdown(f"### Análisis para propiedades de **{st.session_state.dormitorios_sel}** Dormitorio(s)")
    
    if not df_filtrado.empty:
        
        # Definición de variables dependiendo de la selección de la barra lateral
        if kpi_seleccionado == "Precio Promedio por Metro Cuadrado":
            columna_y = "kpi_promedio_precio_m2"
            label_y = "Precio Promedio por m² ($)"
            valor_kpi = df_filtrado[columna_y].mean()
            formato_kpi = f"${valor_kpi:,.2f} / m²"
            
        elif kpi_seleccionado == "Precio de Arriendo Promedio Total":
            columna_y = "precio_promedio"
            label_y = "Precio de Arriendo ($)"
            valor_kpi = df_filtrado[columna_y].mean()
            formato_kpi = f"${valor_kpi:,.0f}"
            
        else:
            columna_y = "volumen_propiedades"
            label_y = "Cantidad de Propiedades"
            valor_kpi = df_filtrado[columna_y].sum()
            formato_kpi = f"{int(valor_kpi)} unids."

        # Tarjeta de métrica destacada
        st.metric(label=f"Métrica Consolidada del KPI Seleccionado", value=formato_kpi)

        # Configuración del gráfico con Matplotlib + Seaborn
        fig, ax = plt.subplots(figsize=(11, 4.5))
        fig.patch.set_facecolor('#FFFFFF')
        ax.set_facecolor('#FFFFFF')
        
        # Paleta armónica basada en tonos rojos
        paleta_rojos = sns.color_palette("Reds", len(df_filtrado["banos"].unique()))
        
        sns.barplot(
            data=df_filtrado, 
            x="banos", 
            y=columna_y, 
            ax=ax, 
            palette=paleta_rojos,
            edgecolor="#333333"
        )
        
        # Títulos y limpieza de ejes
        ax.set_title(f"Evolución de '{kpi_seleccionado}' según cantidad de Baños", fontsize=12, fontweight='bold', color="#C62828")
        ax.set_xlabel("Número de Baños (Confort)", fontsize=10, color="#000000")
        ax.set_ylabel(label_y, fontsize=10, color="#000000")
        sns.despine()
        
        st.pyplot(fig)
        
    else:
        st.warning(f"⚠️ No se encontraron registros cargados para la tipología de {st.session_state.dormitorios_sel} dormitorios.")

    # Acordeón inferior para revisar datos crudos de PySpark
    with st.expander("📂 Ver matriz de datos agregados (PySpark)"):
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

except FileNotFoundError:
    st.error("❌ Archivo 'datos_kpi_real_estate.csv' no detectado en la raíz. Por favor corre primero la celda de Spark.")