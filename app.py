import pandas as pd
import streamlit as st
from openai import OpenAI

# Configuración de la página visual para un look ejecutivo
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
    /* Estilo formal para botones */
    .stButton>button {
        background-color: #1A365D;
        color: #FFFFFF;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #2A4365;
        color: #FFFFFF;
    }
    /* Líneas separadoras */
    hr {
        border-top: 2px solid #E2E8F0;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Sistema de Asistencia Analítica en Revenue Management")

# 1. Tu clave de acceso de OpenAI API (Manejo seguro de Secrets)
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("Atención: Configuración de API Key incompleta. Proceda a 'Manage app' > 'Settings' > 'Secrets' y registre el parámetro OPENAI_API_KEY.")
    st.stop() # Detiene la app limpiamente hasta que pongas la clave

client = OpenAI(api_key=API_KEY)

def limpiar_columna_numerica(df, columna):
    """Limpia los valores monetarios para poder hacer cálculos matemáticos."""
    if columna in df.columns:
        df[columna] = df[columna].astype(str).str.replace('$', '', regex=False)
        df[columna] = df[columna].str.replace(',', '', regex=False).str.strip()
        df[columna] = pd.to_numeric(df[columna], errors='coerce').fillna(0)
    return df

# Carga optimizada: Usamos el CSV de tu carpeta para máxima velocidad
@st.cache_data(show_spinner=False)
def cargar_datos(url):
    try:
        # pd.read_csv es mucho más rápido y ligero en la nube
        df = pd.read_csv(url)
        
        df = limpiar_columna_numerica(df, 'Rental Revenue')
        df = limpiar_columna_numerica(df, 'Rental Revenue STLY')
        df = limpiar_columna_numerica(df, 'Unit Goal+')
        return df
    except Exception as e:
        st.error(f"Error de sistema al procesar los datos: {e}")
        return None

# ID del archivo Analisis Abril - Copy.csv extraído de tu carpeta compartida
FILE_ID_CSV = "1AvYuNhj9OyLDkAiYsssmjXO62VyKy0Do"
link_drive_csv = f"https://drive.google.com/uc?id={FILE_ID_CSV}"

with st.spinner("Inicializando carga de datos en el sistema..."):
    df_original = cargar_datos(link_drive_csv)

if df_original is None:
    st.error("Error de conexión: No se pudo acceder al repositorio de datos. Verifique los permisos de acceso del archivo CSV.")
else:
    # --- BARRA LATERAL CONTROLES ---
    st.sidebar.header("Parámetros de Análisis")
    
    # Selector de Mes
    meses_disponibles = df_original['Year & Month'].dropna().unique().tolist()
    # Pre-seleccionar Abril si existe, si no, el primer mes
    idx_mes = meses_disponibles.index("2026-04 (Apr)") if "2026-04 (Apr)" in meses_disponibles else 0
    mes_filtro = st.sidebar.selectbox("Seleccione el Período:", meses_disponibles, index=idx_mes)
    
    # Filtrar por mes seleccionado
    df_mes = df_original[df_original['Year & Month'] == mes_filtro].copy()
    
    # Selector de Cliente Interactivo
    clientes_disponibles = sorted(df_mes['Client'].dropna().unique().tolist())
    cliente_seleccionado = st.sidebar.selectbox("Seleccione la Cartera/Propietario:", ["TODOS"] + clientes_disponibles)
    
    if cliente_seleccionado != "TODOS":
        df_filtrado = df_mes[df_mes['Client'] == cliente_seleccionado].copy()
    else:
        df_filtrado = df_mes.copy()
        
    st.sidebar.metric(label="Total de propiedades en la selección", value=len(df_filtrado))

    # --- VENTANA DE DIÁLOGO E INTERACCIÓN ---
    st.subheader(f"Reporte de Rendimiento: {cliente_seleccionado} ({mes_filtro})")
    
    # Mostrar tabla interactiva (ajustada para diseño ejecutivo, sin índice)
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.write("**Módulo de Consultas Estratégicas:**")

    # Cuadro de texto interactivo
    consulta_usuario = st.text_input(
        "Ingrese su consulta analítica (Ej: 'Indique las propiedades con mayor desviación respecto a su meta y proponga una estrategia'):",
        key="query_input"
    )

    if st.button("Ejecutar Análisis de IA") and consulta_usuario:
        with st.spinner("Procesando consulta mediante el motor de Inteligencia Artificial..."):
            
            # Construir un resumen compacto protegiendo cálculos de errores nulos
            resumen_propiedades = ""
            for idx, row in df_filtrado.iterrows():
                if pd.isna(row['Unit Goal+']) or row['Unit Goal+'] == 0: 
                    continue
                pct = (row['Rental Revenue'] / row['Unit Goal+'] * 100)
                resumen_propiedades += f"- Propiedad: {row['Listing Name']} | Actual: ${row['Rental Revenue']:,.2f} | Meta: ${row['Unit Goal+']:,.2f} | Avance: {pct:.1f}% | STLY: ${row['Rental Revenue STLY']:,.2f}\n"
            
            prompt_contexto = f"""
            Eres un asistente experto en Revenue Management. Basado en los siguientes datos de propiedades filtradas:
            
            {resumen_propiedades}
            
            Por favor, responde a la siguiente consulta del usuario de manera profesional, clara y analítica:
            "{consulta_usuario}"
            """
            
            try:
                respuesta = client.chat.completions.create(
                    model="gpt-4o", 
                    messages=[
                        {"role": "system", "content": "Eres un experto en Revenue Management y visualización de datos de rendimiento."},
                        {"role": "user", "content": prompt_contexto}
                    ]
                )
                st.success("Análisis estratégico finalizado con éxito.")
                st.write(respuesta.choices[0].message.content)
            
            except Exception as e:
                st.error(f"Falla de conexión con el servidor de OpenAI: {e}")
