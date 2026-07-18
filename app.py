import pandas as pd
import streamlit as st
from openai import OpenAI

# Configuración de la página visual para un look ejecutivo
st.set_page_config(page_title="Revenue AI Assistant", layout="wide")
st.title("🤖 Asistente de Revenue Management con IA")

# 1. Tu clave de acceso de OpenAI API (Manejo seguro de Secrets)
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("⚠️ Falta configurar la API Key. Ve a 'Manage app' (abajo a la derecha) > 'Settings' > 'Secrets' y añade tu OPENAI_API_KEY.")
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
        st.error(f"Error técnico al leer datos: {e}")
        return None

# ID del archivo Analisis Abril - Copy.csv extraído de tu carpeta compartida
FILE_ID_CSV = "1AvYuNhj9OyLDkAiYsssmjXO62VyKy0Do"
link_drive_csv = f"https://drive.google.com/uc?id={FILE_ID_CSV}"

with st.spinner("Cargando base de datos a alta velocidad..."):
    df_original = cargar_datos(link_drive_csv)

if df_original is None:
    st.error("❌ No se pudo descargar el archivo. Verifica que los permisos del CSV en Drive estén en 'Cualquier persona con el enlace'.")
else:
    # --- BARRA LATERAL CONTROLES ---
    st.sidebar.header("Filtros de Análisis")
    
    # Selector de Mes
    meses_disponibles = df_original['Year & Month'].dropna().unique().tolist()
    # Pre-seleccionar Abril si existe, si no, el primer mes
    idx_mes = meses_disponibles.index("2026-04 (Apr)") if "2026-04 (Apr)" in meses_disponibles else 0
    mes_filtro = st.sidebar.selectbox("Selecciona el Mes:", meses_disponibles, index=idx_mes)
    
    # Filtrar por mes seleccionado
    df_mes = df_original[df_original['Year & Month'] == mes_filtro].copy()
    
    # Selector de Cliente Interactivo
    clientes_disponibles = sorted(df_mes['Client'].dropna().unique().tolist())
    cliente_seleccionado = st.sidebar.selectbox("Selecciona el Cliente/Propietario:", ["TODOS"] + clientes_disponibles)
    
    if cliente_seleccionado != "TODOS":
        df_filtrado = df_mes[df_mes['Client'] == cliente_seleccionado].copy()
    else:
        df_filtrado = df_mes.copy()
        
    st.sidebar.metric(label="Propiedades seleccionadas", value=len(df_filtrado))

    # --- VENTANA DE DIÁLOGO E INTERACCIÓN ---
    st.subheader(f"📊 Análisis de Datos para: {cliente_seleccionado} ({mes_filtro})")
    
    # Mostrar tabla interactiva (ajustada para diseño ejecutivo, sin índice)
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.write("💬 **Hazle preguntas a la IA sobre las propiedades filtradas de este cliente:**")

    # Cuadro de texto interactivo
    consulta_usuario = st.text_input(
        "Escribe aquí (Ej: '¿Cuáles propiedades están más lejos de su meta y qué estrategia recomiendas?'):",
        key="query_input"
    )

    if st.button("Consultar a la IA") and consulta_usuario:
        with st.spinner("Pensando estrategia de revenue... 🧠"):
            
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
                st.success("¡Análisis completado!")
                st.write(respuesta.choices[0].message.content)
            
            except Exception as e:
                st.error(f"Hubo un error al conectar con OpenAI: {e}")
