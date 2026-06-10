import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Configuración de la página web (Identidad corporativa de Real Estate)
st.set_page_config(page_title="Dashboard Inmobiliario Ejecutivo", layout="wide")

st.title("Cuadro de Mando Integral - Real Estate Coquimbo & La Serena")
st.markdown("---")

# 2. Carga de datos optimizada (Con la ruta exacta de la Semana 15)
@st.cache_data
def cargar_datos():

    return pd.read_csv("/home/jovyan/work/semanas/Semana 15/datos_riesgo_inmobiliario_dashboard.csv")

df = cargar_datos()

# 3. Creación de las Pestañas (Tabs) manteniendo la estructura de la asignatura
tab_est, tab_tac, tab_op = st.tabs([
    "Nivel Estratégico (Gerente de Riesgo)", 
    "Nivel Táctico (Planificación)", 
    "Nivel Operacional (Supervisor de Cartera)"
])

# ==============================================================================
# PESTAÑA 1: NIVEL ESTRATÉGICO 
# ==============================================================================
with tab_est:
    st.header(" Mitigación de Cartera Estancada")
    st.caption("Frecuencia: Semestral | Objetivo: Medir el riesgo financiero general de tener propiedades con hacinamiento sanitario.")
    
    # Procesamiento matemático exacto del KPI BCH
    resumen_kpi = df.groupby(['ciudad_limpia', 'Categoria_Riesgo'])['precio'].mean().unstack()
    resumen_kpi['Brecha_BCH'] = resumen_kpi['Hacinado (IDH >= 2.0)'] - resumen_kpi['Óptimo (IDH 1.0)']
    
    total_propiedades = len(df)
    
    # Diseño en columnas (Métricas clave arriba con los datos reales)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric(label="Total Propiedades Auditadas", value=total_propiedades)
        
        # Extraemos las brechas exactas calculadas en tu EDA
        brecha_ls = resumen_kpi.loc['La Serena', 'Brecha_BCH']
        brecha_coq = resumen_kpi.loc['Coquimbo', 'Brecha_BCH']
        
        st.metric(label="Brecha BCH La Serena", value=f"${brecha_ls:,.0f}", delta="Castigo Mensual", delta_color="inverse")
        st.metric(label="Brecha BCH Coquimbo", value=f"${brecha_coq:,.0f}", delta="Castigo Mensual", delta_color="inverse")
        
        # Formateamos la tabla resumen para mostrarla en el dashboard
        resumen_show = resumen_kpi.copy()
        for col in resumen_show.columns:
            resumen_show[col] = resumen_show[col].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "$0")
        st.dataframe(resumen_show.reset_index(), hide_index=True)
        
    with col2:
        # Desplegamos el mismo gráfico de tu celda D
        fig, ax = plt.subplots(figsize=(8, 5.2))
        sns.barplot(
            data=df, 
            x='ciudad_limpia', 
            y='precio', 
            hue='Categoria_Riesgo', 
            palette=['#2ca02c', '#d62728'], # Verde (Óptimo) vs Rojo (Peligro)
            errorbar=None,
            ax=ax
        )
        ax.set_title("Castigo del Mercado por Hacinamiento (BCH)")
        ax.set_ylabel("Precio Promedio de Arriendo ($)")
        ax.set_xlabel("Comuna Analizada")
        sns.despine(left=True, bottom=False)
        st.pyplot(fig)

# ==============================================================================
# PESTAÑA 2: NIVEL TÁCTICO (Bandas de Precios por IDH)
# ==============================================================================
with tab_tac:
    st.header(" Bandas de Competitividad por Índice de Confort")
    st.caption("Frecuencia: Mensual | Objetivo: Diseñar estrategias de precios según la relación pieza/baño.")
    
    # Filtro interactivo por ciudad (El poder de Streamlit adaptado a tu caso)
    ciudades_seleccionadas = st.multiselect("Filtrar Ciudades para Análisis:", options=df['ciudad_limpia'].unique(), default=df['ciudad_limpia'].unique())
    df_filtrado = df[df['ciudad_limpia'].isin(ciudades_seleccionadas)]
    
    # Gráfico de distribución de precios por IDH
    fig, ax = plt.subplots(figsize=(10, 4.5))
    sns.boxplot(data=df_filtrado, x='IDH', y='precio', palette="Purples", ax=ax)
    ax.set_ylabel("Precio de Arriendo ($)")
    ax.set_xlabel("Índice de Confort Higiénico (IDH = Dormitorios / Baños)")
    ax.ticklabel_format(style='plain', axis='y')
    sns.despine(left=True)
    st.pyplot(fig)

# ==============================================================================
# PESTAÑA 3: NIVEL OPERACIONAL (Matriz de Alertas de Propiedades Críticas)
# ==============================================================================
with tab_op:
    st.header(" Matriz de Alertas de Activos de Alto Riesgo")
    st.caption("Frecuencia: Diario / Tiempo Real | Objetivo: Detectar propiedades en riesgo sanitario de baja rentabilidad.")
    
    # Control interactivo: Slider para mover el umbral de riesgo en vivo
    umbral_idh = st.slider("Ajustar Umbral Crítico de IDH:", min_value=1.0, max_value=3.0, value=2.0, step=0.5)
    
    zona_peligro = df[df['IDH'] >= umbral_idh]
    
    # Alerta visual dinámica según el slider
    st.error(f" Se han detectado {len(zona_peligro)} propiedades en la cartera que igualan o superan el umbral de riesgo sanitario.")
    
    # Tabla detallada con los activos en peligro para que el supervisor actúe
    if len(zona_peligro) > 0:
        st.subheader(" Lista de Propiedades en Riesgo para Revisión Inmediata:")
        st.dataframe(zona_peligro[['ciudad_limpia', 'precio', 'IDH', 'Categoria_Riesgo']].sort_values(by='precio'), hide_index=True)