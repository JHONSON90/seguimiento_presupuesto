from narwhals.dtypes import Int64
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
import traceback
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Gastos Generales",
    page_icon="💰",
    layout="wide"
)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(show_spinner="Cargando datos...")
def cargar_datos():
    try:
        df = conn.read(worksheet="Gastos Generales", ttl=0)
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
        df2 = conn.read(worksheet="Control GG", ttl=0)
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
    
    return df, df2

df, df2 = cargar_datos()

@st.dialog("🛒 Agregar Gasto")
def agregar_consumo():
    Fecha_formulario = st.date_input("🗓️ Fecha de la Compra")
    Rubro_Presupuestal_form = st.selectbox("🏷️ Rubro Presupuestal", ['50101 - GASTOS DE PERSONAL','50102 - CAPACITACIONES','50103 - PLAN DE BIENESTAR','50104 - HONORARIOS','50105 - IMPUESTOS','50106 - ARRENDAMIENTOS','50107 - AFILIACIONES Y CONTRIBUCIONES','50108 - SEGUROS','50109 - SERVICIOS','50110 - GASTOS LEGALES','50111 - MANTENIMIENTO Y REPARACIONES','50112 - DEPRECIACION','50113 - AMORTIZACIONES','50114 - OTROS GASTOS','50115 - DETERIORO','50116 - GASTOS FINANCIEROS','50117 - AJUSTES AL INVENTARIO','50118 - GASTOS JURIDICOS','50119 - GASTOS DIVERSOS','50120 - MATERIALES Y SUMINISTROS','50121 - GASTOS DE VIAJE'])
    Bodega_form = st.selectbox("🏠 Centro de Costo", ['ADMISIONES','ALERGOLOGIA','ALMACEN','AMBULANCIA','ANESTESIOLOGIA','ATENCION AL USUARIO','AUDIOLOGIA','AUDITORIA INTERNA','AUDITORIA MEDICA','CAMILLEROS','CARDIOLOGIA','CARTERA','CENTRAL DE MEZCLAS','CIRUGIA DE COLUMNA','CIRUGIA GENERAL','CIRUGIA MAXILOFACIAL','CIRUGIA ONCOLOGICA','CIRUGIA PEDIATRICA','CIRUGIA PLASTICA','CIRUGIA VASCULAR','CITAS MEDICAS','COMPRAS','CONSTRUCCIÓN','CONTABILIDAD','CONTRATACION','COORDINACION DE MUNICIPIOS','COSTOS','CRONICOS','CUENTAS MEDICAS','CUMBAL','DERMATOLOGIA','DIRECCIÓN CLINICA','DIRECCION CONTRATO MAGISTERIO','EL TAMBO','ENDOCRINOLOGIA','ENDOSCOPIA','EPIDEMIOLOGIA','EPIDEMIOLOGIA ESP','ESPECIALIZADA SIN ESPECIFICAR','ESTADISTICA','FACTURACION','FISIATRIA','FONOAUDIOLOGIA','GASTROENTEROLOGIA','GERENCIA GENERAL','GERENCIAMIENTO DE SGC','GESTION AMBIENTAL','GESTION DOCUMENTAL','GINECOLOGIA','HEMATOLOGIA','HISTORIAS CLINICAS','HOSPITALIZACION PISOS','HUMANIZACION','IMAGENOLOGIA','INVESTIGACION DESARROLLO E INOVACION','IPIALES','JURIDICA','LA CRUZ','LA UNION','LABORATORIO CLINICO','LAVANDERIA','MANTENIMIENTO','MEDICINA FAMILIAR','MEDICINA GENERAL','MEDICINA INTERNA','MEDICINA LABORAL','NEFROLOGIA','NEUMOLOGIA','NEUROCIRUGIA','NEUROLOGIA','NUTRICION','ODONTOLOGIA','ODONTOPEDIATRIA','OFTALMOLOGIA','ONCOLOGIA','OPTOMETRIA','ORIENTACIÓN Y VIGILANCIA','ORTOPEDIA Y TRAUMATOLOGIA','OTORRINOLARINGOLOGIA','OTRAS TERAPIAS','PAGADURIA','PASTO','PATOLOGIA','PEDIATRIA','PROGRAMA IAMI - AIEPI','PROMOCION Y PREVENCION','PSICOLOGIA','PSIQUIATRIA','QUIROFANO','RECURSOS HUMANOS','REFERENCIA Y CONTRAREFERE','REGISTRO Y CONTROL','REUMATOLOGIA','SALUD MENTAL','SALUD OCUPACIONAL','SAN PABLO','SANDONA','SEGURIDAD DEL PACIENTE','SEGURIDAD Y SALUD EN EL TRABAJO (INTERNO)','SERVICIO FARMACÉUTICO','SERVICIOS GENERALES- ASEO','SISTEMAS','SUBGERENCIA ADMINISTRATIVA','TERAPIA FISICA','TERAPIA OCUPACIONAL','TERAPIA ONCOLOGICA','TERAPIA RESPIRATORIA','TUMACO','TUQUERRES','UCI ADULTOS','UCI NEONATOS','URGENCIAS','UROLOGIA'])
    Valor_form = st.number_input("💰 Valor", min_value=0.0, format="%.2f")
    if st.button('Agregar Gasto'):
        df2 = conn.read(worksheet="Control GG", ttl=0)
        df2['Rubro Presupuestal'] = df2['Rubro Presupuestal'].astype(str)
        new_row = pd.DataFrame({
            'Fecha':[Fecha_formulario],
            'Centro de costo':[Bodega_form],
            "Rubro Presupuestal":[Rubro_Presupuestal_form],
            'Valor': [Valor_form]
        })
        df2 = pd.concat([df2, new_row], ignore_index=True)
        conn.update(worksheet='Control GG', data=df2)
        st.success("Gasto agregado exitosamente!!")
        time.sleep(2)
        st.rerun()
    
if st.button("➕ Agregar Gasto"):
    agregar_consumo()

st.markdown("# Gastos")

df2['Fecha'] = pd.to_datetime(df2['Fecha'])
df2['Mes'] = df2['Fecha'].dt.month_name()
df2['Valor'] = df2['Valor'].astype(int)
seguimiento = df2.pivot_table(
    index='Rubro Presupuestal',
    columns='Mes',
    values='Valor',
    aggfunc='sum'
)

ppto_consumos = df.merge(seguimiento, right_on='Rubro Presupuestal', left_on='Cod Rubro Pptal', how='left').fillna(0)

ppto_consumos['Valor 2026'] = ppto_consumos['Valor 2026'].astype(int)
ppto_consumos['Valor mensual'] = ppto_consumos['Valor mensual'].astype(int)



col1, col2 = st.columns([0.80, 0.20])

with col1:
    st.write(ppto_consumos)

with col2:
    st.metric('Presupuesto Total', f"${ppto_consumos['Valor 2026'].sum():,.0f}")
    st.metric('Ejecutado Total', f"${df2['Valor'].sum():,.0f}", delta=f"{df2['Valor'].count()} ordenes")
    st.metric('Saldo Pendiente', f"${ppto_consumos['Valor 2026'].sum() - df2['Valor'].sum():,.0f}")
    st.metric('% Ejecución', f"{(df2['Valor'].sum() / ppto_consumos['Valor 2026'].sum() * 100):.1f}%")    
    
st.markdown("## 📊 Dashboard de Seguimiento")

chart_col1, chart_col2 = st.columns([2, 1])

with chart_col1:
    st.markdown("#### 🏢 Ejecución por Área")
    # Prepare data for budget vs executed by Area
    area_stats = df2.groupby('Centro de costo').agg({
        'Valor': 'sum',
    }).reset_index()
    
    # Melt for easier plotting with Plotly
    area_stats_melted = area_stats.melt(id_vars='Centro de costo', value_vars=['Valor'], 
                                         var_name='Tipo', value_name='Monto')
    
    fig_area = px.bar(
        area_stats_melted, 
        x='Centro de costo', 
        y='Monto', 
        color='Tipo', 
        barmode='group',
        title='Presupuesto vs Ejecutado por Área',
        color_discrete_map={
            'Valor': '#1f77b4',  # Blue for Budget
        },
        labels={'Centro de costo': 'Centro de Costos', 'Monto': 'Monto (COP)'}
    )
    st.plotly_chart(fig_area, width='stretch')

with chart_col2:
    st.markdown("#### 🎯 Rubro Presupuestal")
    # Prepare data for count by Prioritization
    prioridad_counts = df2.groupby('Rubro Presupuestal').agg({
        'Valor': 'sum',
    }).reset_index()
    prioridad_counts.columns = ['Rubro Presupuestal', 'Valor']
    
    fig_prioridad = px.pie(
        prioridad_counts, 
        values='Valor', 
        names='Rubro Presupuestal',
        title='Distribución por Rubro Presupuestal',
        hole=0.3
    )
    st.plotly_chart(fig_prioridad, width='stretch')

# Additional Chart: Execution by Type
st.markdown("#### 📋 Ejecución por Rubro presupuestal")
# Prepare data for budget vs executed by Type
type_stats = df2.groupby('Rubro Presupuestal').agg({
    'Valor': 'sum',
}).reset_index()

seguimiento_total = df.merge(type_stats, right_on='Rubro Presupuestal', left_on='Cod Rubro Pptal', how='left').fillna(0)

fig_type = px.bar(
    seguimiento_total, 
    x='Cod Rubro Pptal', 
    y=['Valor', 'Valor 2026'], 
    barmode='group',
    title='Presupuesto vs Valor 2026 por Rubro Presupuestal',
    color_discrete_map={
        'Valor': '#1f77b4',
        'Valor 2026': '#ff7f0e'
    },
    labels={'value': 'Monto (COP)', 'variable': 'Tipo', 'Rubro Presupuestal': 'Rubro Presupuestal'}
)
st.plotly_chart(fig_type, width='stretch')

