import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import plotly.graph_objects as go
import time
import traceback

# Configuration and Styling
st.set_page_config(
    page_title="Seguimiento de Presupuesto 2026",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for a more professional look
# st.markdown("""
# <style>
#     .main {
#         background-color: #f8f9fa;
#     }
#     .stMetric {
#         background-color: #ffffff;
#         padding: 15px;
#         border-radius: 10px;
#         box-shadow: 0 4px 6px rgba(0,0,0,0.1);
#     }
#     .stPlotlyChart {
#         background-color: #ffffff;
#         border-radius: 10px;
#         box-shadow: 0 4px 6px rgba(0,0,0,0.1);
#         padding: 10px;
#     }
# </style>
# """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(show_spinner="Cargando datos del presupuesto...")
def cargar_datos_ppto():
    try:
        # 1. Cargar Presupuesto Aprobado (Por CC)
        df_ppto = conn.read(worksheet="Por CC", ttl=60)
        
        # 2. Cargar Ejecución Real (Control por CC)
        df_real = conn.read(worksheet="Control por CC", ttl=60)
        
        return df_ppto, df_real
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {str(e)}")
        st.error(traceback.format_exc())
        return pd.DataFrame(), pd.DataFrame()


# Meses en español (MAREK)
MESES_ES = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 
            'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']

def procesar_datos(df_ppto, df_real):
    if df_ppto.empty or df_real.empty:
        return pd.DataFrame()
    
    # --- PROCESAR PRESUPUESTO (UNPIVOT) ---
    # Columnas fijas (asumimos CENTRO DE COSTOS y Rubro Presupuestal)
    cols_fijas = [c for c in df_ppto.columns if c not in MESES_ES]
    
    # Melting (Unpivoting) los meses
    df_ppto_long = pd.melt(
        df_ppto, 
        id_vars=cols_fijas, 
        value_vars=[m for m in MESES_ES if m in df_ppto.columns],
        var_name='Mes_Nom', 
        value_name='Presupuesto'
    )
    
    # Crear mapeo numérico para meses
    mes_map = {name: i+1 for i, name in enumerate(MESES_ES)}
    df_ppto_long['Mes'] = df_ppto_long['Mes_Nom'].map(mes_map)
    df_ppto_long['Presupuesto'] = pd.to_numeric(df_ppto_long['Presupuesto'], errors='coerce').fillna(0)

    # --- PROCESAR REAL ---
    df_real['FECHA'] = pd.to_datetime(df_real['FECHA'], errors='coerce')
    df_real = df_real.dropna(subset=['FECHA'])
    df_real['Mes'] = df_real['FECHA'].dt.month
    df_real['valor_costo'] = pd.to_numeric(df_real['valor_costo'], errors='coerce').fillna(0)
    
    # Agrupar Real por las mismas llaves
    df_real_agg = df_real.groupby(['CENTRO DE COSTOS', 'Rubro Presupuestal', 'Mes'])['valor_costo'].sum().reset_index()
    df_real_agg.rename(columns={'valor_costo': 'Ejecutado'}, inplace=True)
    
    # --- UNIR AMBOS ---
    # Asegurar que los tipos coincidan para el merge
    df_ppto_long['Rubro Presupuestal'] = df_ppto_long['Rubro Presupuestal'].astype(str)
    df_real_agg['Rubro Presupuestal'] = df_real_agg['Rubro Presupuestal'].astype(str)
    
    df_final = pd.merge(
        df_ppto_long, 
        df_real_agg, 
        on=['CENTRO DE COSTOS', 'Rubro Presupuestal', 'Mes'], 
        how='outer'
    ).fillna(0)
    
    # Calcular Desviación
    df_final['Diferencia'] = df_final['Presupuesto'] - df_final['Ejecutado']
    
    return df_final

# Cargar y Procesar
df_raw_ppto, df_raw_real = cargar_datos_ppto()
df_final = procesar_datos(df_raw_ppto, df_raw_real)

if df_final.empty:
    st.warning("No se encontraron datos para mostrar. Verifique las hojas 'Por CC' y 'Control por CC'.")
else:
    # Sidebar Filters
        
    # Dashboard Header
    st.title("🛡️ Dashboard de Seguimiento Presupuestal 2026")
    st.markdown("Comparativo entre Presupuesto Aprobado y Ejecución Real por CC.")
    
    st.header("🔍 Filtros de Seguimiento")
    
    col1, col2 = st.columns(2)
    with col1:
        all_cc = sorted(df_final['CENTRO DE COSTOS'].unique().tolist())
        selected_cc = st.multiselect("🏥 Centro de Costo", all_cc)
    with col2:
        all_rubros = sorted(df_final['Rubro Presupuestal'].unique().tolist())
        selected_rubros = st.multiselect("🏷️ Rubro Presupuestal", all_rubros)
    
    st.markdown("---")
    # Aplicar filtros
    df_filtered = df_final.copy()
    if selected_cc:
        df_filtered = df_filtered[df_filtered['CENTRO DE COSTOS'].isin(selected_cc)]
    if selected_rubros:
        df_filtered = df_filtered[df_filtered['Rubro Presupuestal'].isin(selected_rubros)]
    # Métricas Principales
    total_ppto = df_filtered['Presupuesto'].sum()
    total_real = df_filtered['Ejecutado'].sum()
    total_diff = total_ppto - total_real
    exec_perc = (total_real / total_ppto * 100) if total_ppto > 0 else 0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Presupuesto Inicial", f"${total_ppto:,.0f}")
    m2.metric("💳 Ejecutado Real", f"${total_real:,.0f}", delta=f"{exec_perc:.1f}% de ejecución", delta_color="inverse")
    m3.metric("📉 Saldo Disponible", f"${total_diff:,.0f}", delta_color="normal")
    m4.metric("📈 % Ejecución Total", f"{exec_perc:.1f}%")

    st.markdown("---")
    
    # Gráficos
    col_chart1, col_chart2 = st.columns([2, 1])
    
    with col_chart1:
        st.subheader("📅 Tendencia Mensual: Presupuesto vs Real")
        # Agrupar por mes para la tendencia
        df_mensual = df_filtered.groupby(['Mes', 'Mes_Nom']).agg({
            'Presupuesto': 'sum',
            'Ejecutado': 'sum'
        }).reset_index().sort_values('Mes')

        st.write(df_mensual)
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=df_mensual['Mes_Nom'], 
            y=df_mensual['Presupuesto'], 
            name='Presupuesto',
            marker_color='#3498db'
        ))
        fig_trend.add_trace(go.Bar(
            x=df_mensual['Mes_Nom'], 
            y=df_mensual['Ejecutado'], 
            name='Real',
            marker_color='#e74c3c'
        ))
        fig_trend.update_layout(
            barmode='group',
            xaxis_title="Mes",
            yaxis_title="Monto (COP)",
            hovermode="x unified",
            height=450
        )
        st.plotly_chart(fig_trend, width='stretch')
        
    with col_chart2:
        st.subheader("🎯 Distribución por Rubro")
        df_rubro_pie = df_filtered.groupby('Rubro Presupuestal')['Ejecutado'].sum().reset_index()
        fig_pie = px.pie(
            df_rubro_pie, 
            values='Ejecutado', 
            names='Rubro Presupuestal',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        #fig_pie.update_layout(height=450)
        st.plotly_chart(fig_pie, width='stretch')

    # Detalle por Centro de Costo
    st.subheader("🏢 Detalle de Ejecución por Centro de Costo")
    df_cc_summary = df_filtered.groupby('CENTRO DE COSTOS').agg({
        'Presupuesto': 'sum',
        'Ejecutado': 'sum',
        'Diferencia': 'sum'
    }).reset_index()
    
    df_cc_summary['% Ejecución'] = (df_cc_summary['Ejecutado'] / df_cc_summary['Presupuesto'] * 100).fillna(0)
    
    st.dataframe(
        df_cc_summary.sort_values('Ejecutado', ascending=False),
        column_config={
            "Presupuesto": st.column_config.NumberColumn(format="$%d"),
            "Ejecutado": st.column_config.NumberColumn(format="$%d"),
            "Diferencia": st.column_config.NumberColumn(format="$%d"),
            "% Ejecución": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)
        },
        hide_index=True,
        width='stretch'
    )

    with st.expander("📄 Ver Tabla de Datos Completa"):
        st.dataframe(df_filtered)