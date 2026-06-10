import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as ticker

# 1. Configuración de la interfaz web
st.set_page_config(page_title="Dashboard Operacional Especializado", layout="wide")

st.title("Cuadro de Mando Integral — Gestión de Cartera")
st.markdown("---")

# 2. Carga optimizada del archivo CSV 
@st.cache_data
def cargar_datos():
    return pd.read_csv("/home/jovyan/work/semanas/Semana 15/datos_inmobiliaria_dashboard.csv")

df = cargar_datos()

# 3. Estructura de navegación por niveles organizacionales de la corredora
tab_est, tab_tac, tab_op = st.tabs([
    "Nivel Estratégico (CEO)", 
    "Nivel Táctico (Gerente)", 
    "Nivel Operacional (Agente Inmobiliario)"
])

# ==========================================
# PESTAÑAS RESERVADAS PARA OTROS HITOS
# ==========================================
with tab_est:
    st.info("Módulo estratégico en reserva para indicadores macro de la dirección general.")

with tab_tac:
    st.info("Módulo táctico en reserva para el control de bandas de precios e inventarios.")

# ==========================================
# PESTAÑA 3: NIVEL OPERACIONAL (DESARROLLO EXCLUSIVO)
# ==========================================
with tab_op:
    st.header("Matriz de Alertas Operacionales — Mitigación de 'Huesos'")
    st.caption("Frecuencia: Diario / Tiempo Real | Objetivo: Evitar la incorporación de inmuebles estancados mediante negociación de tarifas.")
    
    st.markdown(
        "El mercado inmobiliario local penaliza severamente el déficit de infraestructura vial. "
        "Esta alerta identifica las captaciones de gran escala que, al no poseer estacionamiento, "
        "corren el riesgo de convertirse en un activo estancado dentro de la cartera de arriendos."
    )
    
    # Control interactivo dinámico para ajustar el umbral de metros cuadrados en vivo
    umbral_m2 = st.slider("Ajustar Umbral Crítico de Formato Familiar (m²):", min_value=60, max_value=100, value=75, step=5)
    
    # --- PROCESAMIENTO OPERATIVO (FILTRO DE ALERTA ACV) ---
    df_universo_m2 = df[df['m2'] > umbral_m2].copy()
    zona_peligro_acv = df_universo_m2[df_universo_m2['estacionamiento'] == 0]
    total_alerta_acv = len(zona_peligro_acv)
    
    # Diseño en columnas (Métricas de acción e instrucciones comerciales a la izquierda)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.metric(
            label="Alerta de Castigo Vehicular (ACV)", 
            value=f"{total_alerta_acv} Propiedades",
            delta="Requieren Ajuste de Precio",
            delta_color="inverse"
        )
        
        st.error(
            " **Instrucción de Cierre:** Utiliza el gráfico de bandas de la derecha para "
            "demostrarle empíricamente al propietario que las viviendas de estas dimensiones sin "
            "aparcamiento se devalúan. No aceptes el ingreso del inmueble sin una rebaja inicial."
        )
        
    with col2:
        # Generación del gráfico de distribución adaptado con cálculo dinámico de medianas
        orden_cajas = ['Con Estacionamiento\n(Saludable)', 'Sin Estacionamiento\n(ALERTA ACV)']
        df_universo_m2['Infraestructura'] = df_universo_m2['estacionamiento'].apply(
            lambda x: orden_cajas[0] if x == 1 else orden_cajas[1]
        )
        
        # Agrupación por medianas de la muestra segmentada por el slider
        medianas = df_universo_m2.groupby('Infraestructura')['precio'].median()
        
        fig, ax = plt.subplots(figsize=(8, 4.5))
        sns.boxplot(
            data=df_universo_m2, 
            x='Infraestructura', 
            y='precio', 
            order=orden_cajas,
            palette=['#2ca02c', '#d62728'], 
            width=0.4, 
            linewidth=2, 
            ax=ax
        )
        
        # medianas al costado de las cajas
        for i, categoria in enumerate(orden_cajas):
            if categoria in medianas:
                valor_mediana = medianas[categoria]
                ax.text(
                    i + 0.23, valor_mediana, f"Mediana:\n${valor_mediana:,.0f}", 
                    ha='left', va='center', color='black', weight='bold', fontsize=10,
                    bbox=dict(facecolor='#F0F2F6', edgecolor='none', alpha=0.8, boxstyle='round,pad=0.2')
                )
        
        ax.set_title(f'Brecha Histórica de Precios para Inmuebles > {umbral_m2}m²', fontsize=11, pad=10)
        ax.set_ylabel("Precio del Arriendo Mensual ($)")
        ax.set_xlabel("")
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x:,.0f}'))
        sns.despine(left=True)
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        st.pyplot(fig)
        
    # Despliegue de la lista de acción con enlaces limpios
    if total_alerta_acv > 0:
        st.subheader("Lista de Control Diario para Agentes de Captación:")
        st.dataframe(
            zona_peligro_acv[['precio', 'm2', 'dormitorios', 'banos', 'enlace']], 
            hide_index=True,
            use_container_width=True,
            column_config={
                "precio": st.column_config.NumberColumn("Precio Ofertado ($)", format="$%d"),
                "m2": st.column_config.NumberColumn("Superficie", format="%d m²"),
                "url": st.column_config.LinkColumn("Enlace al Anuncio")
            }
        )
    else:
        st.success("Cartera operativa óptima. Ninguna propiedad familiar se encuentra en situación de riesgo vehicular.")