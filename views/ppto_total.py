import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
import traceback

conn = st.connection("gsheets", type=GSheetsConnection)

st.markdown("# Seguimiento de Presupuesto")

@st.cache_data(show_spinner="Cargando datos...")
def cargar_datos():
    try:
        df = conn.read(worksheet="Por CC", ttl=0)
        placeholder = st.empty()
        placeholder.success("Conexión exitosa!!")
        time.sleep(2)
        placeholder.empty()
    except Exception as e:
        placeholder = st.empty()
        placeholder.error(f"Error al conectar con Google Sheets: {str(e)}")
        placeholder.error(f"Traceback: {traceback.format_exc()}")
        time.sleep(2)
        placeholder.empty()
    
    return df

df = cargar_datos()

st.write(df)