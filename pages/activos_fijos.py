import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
import traceback

st.set_page_config(
    page_title="Activos Fijos",
    page_icon="💻",
    layout="wide"
)

conn = st.connection("gsheets", type=GSheetsConnection)

if 'df' not in st.session_state:
    try:
        # Initial read only happens once
        df = conn.read(worksheet="Activos Fijos", ttl=0)
        
        # Data preparation
        df['Valor Comprado'] = df['Valor Comprado'].fillna(0).astype(float)
        df['Solicitud Pedido'] = df['Solicitud Pedido'].astype(bool)
        df['Cotizado'] = df['Cotizado'].astype(bool)
        df['Aprobado'] = df['Aprobado'].astype(bool)
        df['Comprado'] = df['Comprado'].astype(bool)
        
        st.session_state.df = df
        st.toast("Datos cargados desde Google Sheets", icon="✅")
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {str(e)}")
        st.error(f"Traceback: {traceback.format_exc()}")
        st.stop()

st.markdown("# Activos Fijos")

st.markdown("🔎 Filtros")

filtro1, filtro2, filtro3 = st.columns(3)
# Use st.session_state.df for options to ensure they are always available
responsable = filtro1.multiselect("Centro de costos", options=st.session_state.df['AREA'].unique(), key="responsable")
activo_fijo = filtro2.multiselect("Activo fijo", options=st.session_state.df['EQUIPO / ITEM'].unique(), key="activo_fijo")
prioridad = filtro3.multiselect("Prioridad", options=st.session_state.df['PRIORIZACION'].unique(), key="prioridad")

# Create a filtered copy for display, keeping the original intact in session_state
filtered_df = st.session_state.df.copy()

if responsable:
    filtered_df = filtered_df[filtered_df['AREA'].isin(responsable)]
if activo_fijo:
    filtered_df = filtered_df[filtered_df['EQUIPO / ITEM'].isin(activo_fijo)]
if prioridad:
    filtered_df = filtered_df[filtered_df['PRIORIZACION'].isin(prioridad)]

if not filtered_df.empty:
    with st.form("editor_activos"):
        st.markdown("📝 Seguimiento de Activos Fijos")
        # Capture edited dataframe
        edited_df = st.data_editor(
            filtered_df, 
            column_config={
                'Solicitud Pedido': st.column_config.CheckboxColumn('Solicitud Pedido', help="Indica si se ha recibido la solicitud del pedido", default=False),
                'Cotizado': st.column_config.CheckboxColumn('Cotizado', help="Indica si se ha realizado la cotización", default=False),
                'Aprobado': st.column_config.CheckboxColumn('Aprobado', help="Indica si se ha aprobado la cotización", default=False),
                'Comprado': st.column_config.CheckboxColumn('Comprado', help="Indica si se ha comprado el activo fijo", default=False),
                'Valor Comprado': st.column_config.Column("Valor Comprado", help="Indica el valor del activo fijo comprado"),
            },
            num_rows='dynamic', 
            disabled=["AREA", 'CODIGO RUBRO PRESUPUESTAL', 'EQUIPO / ITEM','CANTIDAD','VALOR UNITARIO','VALOR TOTAL','PRIORIZACION'],  
            width='stretch',
            hide_index=True)
        
        submit_local = st.form_submit_button("✅ Aplicar cambios locales", width='stretch')
        
    # Update session state with edited values using index matching ONLY when button is pressed
    if submit_local:
        if not edited_df.equals(filtered_df):
            st.session_state.df.update(edited_df)
            st.success("Cambios aplicados localmente. ¡Recuerda guardar en la nube!", icon="✍️")
            time.sleep(1)
            st.rerun()

# Add save button for persistence to Google Sheets
st.markdown("---")
col1, col2 = st.columns([2, 1])
with col1:
    if st.button("💾 Guardar TODO", width='stretch', type="primary"):
        try:
            with st.spinner("Guardando cambios..."):
                conn.update(worksheet="Activos Fijos", data=st.session_state.df)
                st.success("¡Cambios guardados exitosamente en Google Sheets!")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {str(e)}")
with col2:
    if st.button("🔄 Refrescar Datos", width='stretch'):
        del st.session_state.df
        st.rerun()

st.info("💡 **Instrucciones:** 1. Realiza todos los cambios en la tabla. \n **2.** Presiona 'Aplicar cambios locales'. \n **3.** Finalmente presiona 'Guardar TODO'.")


