import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
import traceback
import plotly.express as px
import pandas as pd

st.set_page_config(
    page_title="Activos Fijos",
    page_icon="💻",
    layout="wide"
)

conn = st.connection("gsheets", type=GSheetsConnection)

if 'df' not in st.session_state:
    try:
        # Initial read only happens once
        df = conn.read(worksheet="Activos Fijos", ttl=60)
        
        # Data preparation
        df['CODIGO RUBRO PRESUPUESTAL'] = df['CODIGO RUBRO PRESUPUESTAL'].astype(int)
        df['CANTIDAD'] = df['CANTIDAD'].astype(int)
        df['VALOR UNITARIO'] = df['VALOR UNITARIO'].astype(int)
        df['VALOR TOTAL'] = pd.to_numeric(df['VALOR TOTAL'], errors='coerce').fillna(0)
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

st.info("💡 **Instrucciones:** 1. Realiza todos los cambios en la tabla. \n **2.** Presiona 'Aplicar cambios locales'. \n **3.** Finalmente presiona 'Guardar TODO'.")
if not filtered_df.empty:
    with st.form("editor_activos"):
        st.markdown("📝 Seguimiento de Activos Fijos")
        # Capture edited dataframe
        edited_df = st.data_editor(
            filtered_df, 
            column_config={
                'AREA': st.column_config.SelectboxColumn(
                    "Centro de costo", 
                    help="Indica el centro de costo",
                    options=sorted(st.session_state.df['AREA'].unique().tolist()),
                    required=True
                ),
                'CODIGO RUBRO PRESUPUESTAL': st.column_config.SelectboxColumn(
                    "Rubro Presupuestal", 
                    help="Indica el rubro presupuestal",
                    options=sorted(st.session_state.df['CODIGO RUBRO PRESUPUESTAL'].unique().tolist()),
                    required=True
                ),
                'EQUIPO / ITEM': st.column_config.Column("Activo fijo", help="Indica el activo fijo"),
                'CANTIDAD': st.column_config.Column("Cantidad", help="Indica la cantidad del activo fijo"),
                'VALOR UNITARIO': st.column_config.Column("Valor unitario", help="Indica el valor unitario del activo fijo"),
                'VALOR TOTAL': st.column_config.Column("Valor total", help="Indica el valor total del activo fijo"),
                'PRIORIZACION': st.column_config.SelectboxColumn(
                    "Prioridad", 
                    help="Indica la prioridad del activo fijo",
                    options=sorted([opt for opt in st.session_state.df['PRIORIZACION'].unique().tolist() if pd.notna(opt) and opt != '']) + ["Nuevo"],
                    required=True
                ),
                'Solicitud Pedido': st.column_config.CheckboxColumn('Solicitud Pedido', help="Indica si se ha recibido la solicitud del pedido", default=False),
                'Cotizado': st.column_config.CheckboxColumn('Cotizado', help="Indica si se ha realizado la cotización", default=False),
                'Aprobado': st.column_config.CheckboxColumn('Aprobado', help="Indica si se ha aprobado la cotización", default=False),
                'Comprado': st.column_config.CheckboxColumn('Comprado', help="Indica si se ha comprado el activo fijo", default=False),
                'Valor Comprado': st.column_config.Column("Valor Comprado", help="Indica el valor del activo fijo comprado"),
            },
            num_rows='dynamic', 
            #disabled=["AREA", 'CODIGO RUBRO PRESUPUESTAL', 'EQUIPO / ITEM','CANTIDAD','VALOR UNITARIO','VALOR TOTAL','PRIORIZACION'],  
            width='stretch',
            hide_index=True)
        
        submit_local = st.form_submit_button("✅ Aplicar cambios locales", width='stretch')
        
    # Update session state with edited values using index matching ONLY when button is pressed
    if submit_local:
        if not edited_df.equals(filtered_df):
            # Obtener los índices que no están en la vista filtrada (para mantenerlos)
            idx_fuera_filtro = st.session_state.df.index[~st.session_state.df.index.isin(filtered_df.index)]
            df_fuera_filtro = st.session_state.df.loc[idx_fuera_filtro]
            
            # Combinar filas no filtradas con las editadas (que incluyen nuevas y eliminadas)
            new_df = pd.concat([df_fuera_filtro, edited_df], ignore_index=True)
            
            # Asegurar tipos de datos para evitar errores en GSheets o en el Dashboard
            try:
                new_df['CODIGO RUBRO PRESUPUESTAL'] = pd.to_numeric(new_df['CODIGO RUBRO PRESUPUESTAL'], errors='coerce').fillna(0).astype(int)
                new_df['CANTIDAD'] = pd.to_numeric(new_df['CANTIDAD'], errors='coerce').fillna(0).astype(int)
                new_df['VALOR UNITARIO'] = pd.to_numeric(new_df['VALOR UNITARIO'], errors='coerce').fillna(0).astype(int)
                new_df['VALOR TOTAL'] = new_df['CANTIDAD'] * new_df['VALOR UNITARIO']
                new_df['Valor Comprado'] = pd.to_numeric(new_df['Valor Comprado'], errors='coerce').fillna(0).astype(float)
                
                # Asegurar que las columnas de estado sean booleanas
                for col in ['Solicitud Pedido', 'Cotizado', 'Aprobado', 'Comprado']:
                    if col in new_df.columns:
                        new_df[col] = new_df[col].fillna(False).astype(bool)
                
                # Manejar valores vacíos en strings para evitar NaN en GSheets
                new_df['PRIORIZACION'] = new_df['PRIORIZACION'].fillna('Nuevo').replace('', 'Nuevo')
                new_df['AREA'] = new_df['AREA'].fillna('').astype(str)
                new_df['EQUIPO / ITEM'] = new_df['EQUIPO / ITEM'].fillna('').astype(str)
                
            except Exception as e:
                st.error(f"Error al procesar tipos de datos: {str(e)}")
            
            st.session_state.df = new_df
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

# --- DASHBOARD SECTION ---
st.markdown("## 📊 Dashboard de Seguimiento")

# Metrics Calculation
total_budget = filtered_df['VALOR TOTAL'].sum()
total_executed = filtered_df['Valor Comprado'].sum()
balance = total_budget - total_executed
execution_pct = (total_executed / total_budget * 100) if total_budget > 0 else 0

# Minimalist Metrics Row
m1, m2, m3, m4 = st.columns(4)
m1.metric("Presupuesto Total", f"${total_budget:,.1f}", help="Suma de VALOR TOTAL")
m2.metric("Ejecutado Total", f"${total_executed:,.1f}", help="Suma de Valor Comprado")
m3.metric("Saldo Pendiente", f"${balance:,.1f}", delta=f"{(100-execution_pct):.1f}% restante", delta_color="inverse")
m4.metric("% Ejecución", f"{execution_pct:.1f}%")

st.markdown("---")

# Visual Charts
if not filtered_df.empty:
    chart_col1, chart_col2 = st.columns([2, 1])

    with chart_col1:
        st.markdown("#### 🏢 Ejecución por Área")
        # Prepare data for budget vs executed by Area
        area_stats = filtered_df.groupby('AREA').agg({
            'VALOR TOTAL': 'sum',
            'Valor Comprado': 'sum'
        }).reset_index()
        
        # Melt for easier plotting with Plotly
        area_stats_melted = area_stats.melt(id_vars='AREA', value_vars=['VALOR TOTAL', 'Valor Comprado'], 
                                             var_name='Tipo', value_name='Monto')
        
        fig_area = px.bar(
            area_stats_melted, 
            x='AREA', 
            y='Monto', 
            color='Tipo',
            barmode='group',
            color_discrete_map={'VALOR TOTAL': '#203c62', 'Valor Comprado': '#00d2ff'},
            template="plotly_white"
        )
        fig_area.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=350,
            xaxis_title="",
            yaxis_title="Monto ($)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_area, use_container_width=True)

    with chart_col2:
        st.markdown("#### 🔄 Proceso de Gestión")
        # Status counts
        status_counts = {
            'Solicitud': filtered_df['Solicitud Pedido'].sum(),
            'Cotizado': filtered_df['Cotizado'].sum(),
            'Aprobado': filtered_df['Aprobado'].sum(),
            'Comprado': filtered_df['Comprado'].sum()
        }
        status_df = pd.DataFrame(status_counts.items(), columns=['Estado', 'Cantidad'])
        
        fig_status = px.funnel(
            status_df, 
            y='Estado', 
            x='Cantidad',
            color_discrete_sequence=['#203c62'],
            template="plotly_white"
        )
        fig_status.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=350
        )
        st.plotly_chart(fig_status, use_container_width=True)

    # New Section: Breakdown by Rubro Presupuestal
    st.markdown("#### 📖 Ejecución por Rubro Presupuestal")
    
    rubro_stats = filtered_df.groupby('CODIGO RUBRO PRESUPUESTAL').agg({
        'VALOR TOTAL': 'sum',
        'Valor Comprado': 'sum'
    }).reset_index()

    rubro_stats['CODIGO RUBRO PRESUPUESTAL'] = rubro_stats['CODIGO RUBRO PRESUPUESTAL'].astype(str)   
    
    # Sort by budget to make it easier to read
    rubro_stats = rubro_stats.sort_values(by='VALOR TOTAL', ascending=True)
    
    rubro_stats_melted = rubro_stats.melt(id_vars='CODIGO RUBRO PRESUPUESTAL', 
                                         value_vars=['VALOR TOTAL', 'Valor Comprado'], 
                                         var_name='Tipo', value_name='Monto')
    
    fig_rubro = px.bar(
        rubro_stats_melted, 
        y='CODIGO RUBRO PRESUPUESTAL', 
        x='Monto', 
        color='Tipo',
        orientation='h',
        barmode='group',
        text='Monto', # Add text labels to bars
        color_discrete_map={'VALOR TOTAL': '#203c62', 'Valor Comprado': '#00d2ff'},
        template="plotly_white",
        labels={'CODIGO RUBRO PRESUPUESTAL': 'Rubro', 'Monto': 'Monto ($)'}
    )
    
    # Format text labels for readability
    fig_rubro.update_traces(texttemplate='%{text:$,.0f}', textposition='outside')
    
    fig_rubro.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        height=max(400, 100 + len(rubro_stats) * 50), # INCREASED height per item
        xaxis_title="Monto ($)",
        yaxis_title="",
        uniformtext_mode='hide', # Hide labels if bars are too small
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=14) # INCREASED font size
    )
    st.plotly_chart(fig_rubro, use_container_width=True)
else:
    st.info("No hay datos para mostrar en el dashboard.")



