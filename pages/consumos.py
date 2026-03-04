import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
import traceback
import pandas as pd
import polars as pl


conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(worksheet="Consumos", ttl=0)
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

try:
    df2 = conn.read(worksheet="Control Consumos", ttl=0)
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

@st.dialog("🛒 Agregar Consumo")
def agregar_consumo():
    Fecha_formulario = st.date_input("🗓️ Fecha de la Compra")
    Rubro_Presupuestal_form = st.selectbox("🏠 Bodega", ['60101 - Laboratorio Clinico',   '60102 - Mantenimiento', '60103 - Osteosintesis', '60104 - Servicio Farmaceutico', '60105 - Sistemas', '60106 - Suministros'])
    Valor_form = st.number_input("💰 Valor", min_value=0.0, format="%.2f")
    if st.button('Agregar Consumo'):
        df2 = conn.read(worksheet="Control Consumos", ttl=0)
        new_row = pd.DataFrame({
            'Fecha':[Fecha_formulario],
            "Rubro Presupuestal":[Rubro_Presupuestal_form],
            #'Bodega':[Bodega_form],
            'Valor': [Valor_form]
        })
        df2 = pd.concat([df2, new_row], ignore_index=True)
        conn.update(worksheet='Control Consumos', data=df2)
        st.success("Gasto agregado exitosamente!!")
        time.sleep(2)
        st.rerun()

if st.button("Agregar Consumo"):
    agregar_consumo()

st.markdown("# Consumos por bodega")

df2['Fecha'] = pd.to_datetime(df2['Fecha'])
df2['Mes'] = df2['Fecha'].dt.month_name()
seguimiento = df2.pivot_table(
    index='Rubro Presupuestal',
    columns='Mes',
    values='Valor',
    aggfunc='sum'
)

ppto_consumos = df.join(seguimiento, on='Rubro Presupuestal', how='left').fillna(0)
# ppto_consumos[]

st.write(df)

st.write(ppto_consumos)