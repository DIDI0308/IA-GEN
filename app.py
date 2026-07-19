import pandas as pd
import streamlit as st
from openai import OpenAI

# Configuración de la página visual para un look corporativo
st.set_page_config(page_title="Revenue AI Assistant", layout="wide")

# Estilos CSS para colores corporativos y formales
st.markdown("""
    <style>
    /* Colores y tipografía corporativa */
    .stApp {
        background-color: #F4F6F9;
    }
    h1, h2, h3 {
        color: #1A365D !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    /* Estilo formal para métricas */
    [data-testid="stMetricValue"] {
        color: #2B6CB0;
        font-weight: 600;
    }
    /* Líneas separadoras */
    hr {
        border-top: 2px solid #E2E8F0;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Sistema de Asistencia Analítica en Revenue Management")

# 1. Configuración de API Key
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("Atención: Configuración de API Key incompleta. Proceda a 'Manage app' > 'Settings' > 'Secrets' y registre el parámetro OPENAI_API_KEY.")
    st.stop()

client = OpenAI(api_key=API_KEY)

def limpiar_columna_numerica(df, columna):
    """Limpia los valores monetarios para cálculos matemáticos."""
    if columna in df.columns:
        df[columna] = df[columna].astype(str).str.replace('$', '', regex=False)
        df[columna] = df[columna].str.replace(',', '', regex=False).str.strip()
        df[columna] = pd.to_numeric(df[columna], errors='coerce').fillna(0)
    return df

# Carga optimizada
@st.cache_data(show_spinner=False)
def cargar_datos(url):
    try:
        df = pd.read_csv(url)
        df = limpiar_columna_numerica(df, 'Rental Revenue')
        df = limpiar_columna_numerica(df, 'Rental Revenue STLY')
        df = limpiar_columna_numerica(df, 'Unit Goal+')
        return df
    except Exception as e:
        st.error(f"Error de sistema al procesar los datos: {e}")
        return None

# ID del archivo CSV
FILE_ID_CSV = "1AvYuNhj9OyLDkAiYsssmjXO62VyKy0Do"
link_drive_csv = f"https://drive.google.com/uc?id={FILE_ID_CSV}"

with st.spinner("Inicializando carga de datos en el sistema..."):
    df_original = cargar_datos(link_drive_csv)

if df_original is None:
    st.error("Error de conexión: No se pudo acceder al repositorio de datos. Verifique los permisos.")
else:
    # --- BARRA LATERAL CONTROLES ---
    st.sidebar.header("Parámetros de Análisis")
    
    meses_disponibles = df_original['Year & Month'].dropna().unique().tolist()
    idx_mes = meses_disponibles.index("2026-04 (Apr)") if "2026-04 (Apr)" in meses_disponibles else 0
    mes_filtro = st.sidebar.selectbox("Seleccione el Período:", meses_disponibles, index=idx_mes)
    
    df_mes = df_original[df_original['Year & Month'] == mes_filtro].copy()
    
    clientes_disponibles = sorted(df_mes['Client'].dropna().unique().tolist())
    cliente_seleccionado = st.sidebar.selectbox("Seleccione la Cartera/Propietario:", ["TODOS"] + clientes_disponibles)
    
    if cliente_seleccionado != "TODOS":
        df_filtrado = df_mes[df_mes['Client'] == cliente_seleccionado].copy()
    else:
        df_filtrado = df_mes.copy()
        
    st.sidebar.metric(label="Total de propiedades seleccionadas", value=len(df_filtrado))

    # --- VENTANA PRINCIPAL Y KPIs ---
    st.subheader(f"Reporte de Rendimiento: {cliente_seleccionado} ({mes_filtro})")
    
    # 1. PANEL DE KPIs ESTRATÉGICOS
    total_revenue = df_filtrado['Rental Revenue'].sum()
    total_goal = df_filtrado['Unit Goal+'].sum()
    total_stly = df_filtrado['Rental Revenue STLY'].sum()
    
    pct_cumplimiento = (total_revenue / total_goal * 100) if total_goal > 0 else 0
    var_stly = ((total_revenue - total_stly) / total_stly * 100) if total_stly > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingreso Real", f"${total_revenue:,.2f}")
    col2.metric("Meta Establecida", f"${total_goal:,.2f}")
    col3.metric("Cumplimiento de Meta", f"{pct_cumplimiento:.1f}%")
    col4.metric("Variación vs Año Anterior", f"{var_stly:+.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. OCULTAR BASE DE DATOS PARA LIMPIAR LA PANTALLA
    with st.expander("Desplegar Base de Datos Detallada"):
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # 3. INTERFAZ DE CHAT CON MEMORIA (Look SaaS Profesional)
    st.write("**Módulo de Consultas Estratégicas Asistidas por IA:**")

    # Inicializar el historial de conversación en la memoria temporal
    if "mensajes_chat" not in st.session_state:
        st.session_state.mensajes_chat = []

    # Mostrar mensajes anteriores
    for mensaje in st.session_state.mensajes_chat:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    # Cuadro de entrada de chat nativo
    if consulta_usuario := st.chat_input("Ingrese su consulta analítica (Ej: Identificar propiedades bajo meta y sugerir acciones)..."):
        
        # Mostrar el mensaje del usuario inmediatamente
        st.session_state.mensajes_chat.append({"role": "user", "content": consulta_usuario})
        with st.chat_message("user"):
            st.markdown(consulta_usuario)

        # Preparar contexto de datos para la IA (Formato CSV para mayor precisión matemática)
        resumen_df = df_filtrado[['Listing Name', 'Rental Revenue', 'Unit Goal+', 'Rental Revenue STLY']].copy()
        datos_comprimidos = resumen_df.to_csv(index=False)
        
        prompt_sistema = f"""
        Usted es un sistema experto en Revenue Management corporativo y visualización de datos de rendimiento.
        Actualmente está asistiendo a un ejecutivo analizando la siguiente base de datos filtrada:
        
        {datos_comprimidos}
        
        Instrucciones estrictas:
        - Responda siempre con un tono formal, profesional y objetivo.
        - Utilice la información provista en los datos para argumentar sus análisis.
        """
        
        # Construir el historial para enviarlo a la API
        mensajes_api = [{"role": "system", "content": prompt_sistema}]
        for m in st.session_state.mensajes_chat:
            mensajes_api.append({"role": m["role"], "content": m["content"]})

        # Generar respuesta con efecto "Streaming" (Máquina de escribir)
        with st.chat_message("assistant"):
            try:
                stream = client.chat.completions.create(
                    model="gpt-4o", 
                    messages=mensajes_api,
                    stream=True # Esto activa el efecto en tiempo real
                )
                # Escribir la respuesta fluida en la pantalla
                respuesta_completa = st.write_stream(stream)
                
                # Guardar en memoria
                st.session_state.mensajes_chat.append({"role": "assistant", "content": respuesta_completa})
                
            except Exception as e:
                st.error(f"Falla de conexión con el servidor de IA: {e}")
