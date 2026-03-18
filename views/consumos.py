import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
import traceback
import pandas as pd
import polars as pl
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Consumos por Bodega",
    page_icon="🔥",
    layout="wide"
)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(show_spinner="Cargando datos...")
def cargar_datos():
    try:
        df = conn.read(worksheet="Consumos", ttl=60)
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
        df2 = conn.read(worksheet="Control Consumos", ttl=60)
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
        df3 = conn.read(worksheet="Control Compras", ttl=60)
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

    return df, df2, df3

df, df2, df3 = cargar_datos()

@st.dialog("🛒 Agregar Consumo")
def agregar_consumo():
    Fecha_formulario = st.date_input("🗓️ Fecha de la Compra")
    Rubro_Presupuestal_form = st.selectbox("🏠 Bodega", ['60101 - Laboratorio Clinico',   '60102 - Mantenimiento', '60103 - Osteosintesis', '60104 - Servicio Farmaceutico', '60105 - Sistemas', '60106 - Suministros'])
    Valor_form = st.number_input("💰 Valor", min_value=0.0, format="%.2f")
    if st.button('Agregar Consumo'):
        df2 = conn.read(worksheet="Control Consumos", ttl=60)
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

@st.dialog("📋 Listado de solicitudes de compra")
def listado_solicitudes():
    st.write(df2)

col1, col2 = st.columns(2)
with col1:
    if st.button("➕ Agregar Consumo"):
        agregar_consumo()
with col2:
    if st.button("Listado de solicitudes de compra"):
        listado_solicitudes()

st.markdown("# Consumos autorizados por bodega")

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

st.write(ppto_consumos)

data1, data2, data3, data4 = st.columns(4)

with data1:
    st.metric("Total", f"${ppto_consumos['Valor Año'].sum():,.0f}")
with data2:
    st.metric("Total Mensual", f"${ppto_consumos['Valor Mensual'].sum():,.0f}")
with data3:
    st.metric("Total Autorizado", f"${df2['Valor'].sum():,.0f}", delta=f"{df2['Rubro Presupuestal'].count()} Solicitudes de compra", delta_color="inverse")
with data4:
    st.metric("Saldo Autorizado", f"${ppto_consumos['Valor Año'].sum() - df2['Valor'].sum():,.0f}")


#region compras

df3['FECHA'] = pd.to_datetime(df3['FECHA'], format='%d/%m/%Y')
df3['Mes'] = df3['FECHA'].dt.month_name()
df3['N_Mes'] = df3['FECHA'].dt.month

para_grafico_compras = df3.groupby(['RUBRO', 'N_Mes', 'Mes']).agg({
    'Valor': 'sum'
}).reset_index()

seguimiento_compras = df3.pivot_table(
    index='RUBRO',
    columns='Mes',
    values='Valor',
    aggfunc='sum'
)

sin_index = df.reset_index()

para_grafico_compras = para_grafico_compras.merge(sin_index, right_on='Rubro Presupuestal', left_on='RUBRO', how='left').fillna(0)

# cols_to_drop = [c for c in ['index', 'Rubro Presupuestal', 'Valor Año'] if c in para_grafico_compras.columns]
para_grafico_compras = para_grafico_compras.drop(columns=['index', 'Rubro Presupuestal'])
#st.write(para_grafico_compras)
st.divider()
seguimiento_compras_unido = sin_index.merge(seguimiento_compras, right_on='RUBRO', left_on='Rubro Presupuestal', how='left').fillna(0)

st.markdown("# Seguimiento con Compras")

filtro1, filtro2 = st.columns(2)
por_rubro = filtro1.multiselect("Rubro Presupuestal", options=para_grafico_compras['RUBRO'].unique(), key="rubro")
por_mes = filtro2.multiselect("Mes", options=para_grafico_compras['Mes'].unique(), key="mes")

if por_rubro:
    para_grafico_compras = para_grafico_compras[para_grafico_compras['RUBRO'].isin(por_rubro)]
if por_mes:
    para_grafico_compras = para_grafico_compras[para_grafico_compras['Mes'].isin(por_mes)]

if not para_grafico_compras.empty:
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total", f"${para_grafico_compras['Valor Año'].sum():,.0f}", border=True)
    with m2:
        st.metric("Total Mensual", f"${para_grafico_compras['Valor Mensual'].sum():,.0f}", border=True)
    with m3:
        st.metric("Total Autorizado", f"${para_grafico_compras['Valor'].sum():,.0f}", border=True)
    with m4:
        st.metric("Saldo Autorizado", f"${ppto_consumos['Valor Año'].sum() - para_grafico_compras['Valor'].sum():,.0f}", border=True)
    fig_compras = px.bar(para_grafico_compras, 
                        y='RUBRO', 
                        x=['Valor', 'Valor Mensual'], 
                        #color='RUBRO',
                    facet_col='Mes',
                    facet_col_wrap=3,
                    #text_auto=True,
                    barmode='overlay', #'stack', 'group', 'overlay', 'relative']
                    labels={'value': 'Monto', 'variable': 'Tipo', 'Valor': 'Ejecutado', 'Valor Mensual': 'Presupuestado'})

    st.plotly_chart(fig_compras)

seguimiento_compras_unido.drop(columns=['index', 'Valor Año'], inplace=True)


with st.expander("Seguimiento con Compras"):
    st.write(seguimiento_compras_unido)
#st.write(df)

st.divider()
