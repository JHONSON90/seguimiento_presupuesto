import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import traceback
from datetime import datetime

# ── CARGA DE DATOS ───────────────────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(show_spinner="Analizando rentabilidad operativa...", ttl=300)
def cargar_datos_rentabilidad():
    try:
        # Ingresos Reales (Hoja Control_Ingresos)
        df_ingresos = conn.read(worksheet="Control_Ingresos", ttl=300)
        # Gastos Reales (Hoja Gastos_Grales_reales)
        df_gastos = conn.read(worksheet="Gastos_Grales_reales", ttl=300)
        return df_ingresos, df_gastos
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

# Meses en español
MESES_ES = [
    'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
    'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE'
]
MES_MAP = {i + 1: name for i, name in enumerate(MESES_ES)}

def procesar_datos(df_ing, df_gas):
    if df_ing.empty or df_gas.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 1. PROCESAR INGRESOS (Global)
    df_i = df_ing.copy()
    df_i['FECHA'] = pd.to_datetime(df_i['FECHA'], dayfirst=True, errors='coerce')
    df_i = df_i.dropna(subset=['FECHA'])
    df_i['Mes'] = df_i['FECHA'].dt.month
    
    # Identificar columna de saldo (flexibilidad de nombres)
    saldo_col_i = 'Saldo' if 'Saldo' in df_i.columns else ('SALDO' if 'SALDO' in df_i.columns else 'CREDITOS')
    df_i['Monto'] = pd.to_numeric(df_i[saldo_col_i], errors='coerce').fillna(0)
    
    ing_mes = df_i.groupby('Mes')['Monto'].sum().reset_index().rename(columns={'Monto': 'Ingresos'})

    # 2. PROCESAR GASTOS (Global)
    df_g = df_gas.copy()
    # En gastos.py se usa 'Fecha' y 'SALDO MOV.'
    df_g['Fecha'] = pd.to_datetime(df_g['Fecha'], errors='coerce')
    df_g = df_g.dropna(subset=['Fecha'])
    df_g['Mes'] = df_g['Fecha'].dt.month
    
    saldo_col_g = 'SALDO MOV.' if 'SALDO MOV.' in df_g.columns else 'SALDO'
    df_g['Monto'] = pd.to_numeric(df_g[saldo_col_g], errors='coerce').fillna(0)
    
    gas_mes = df_g.groupby('Mes')['Monto'].sum().reset_index().rename(columns={'Monto': 'Gastos'})

    # 3. UNIFICACIÓN Y CÁLCULOS
    df_final = pd.merge(ing_mes, gas_mes, on='Mes', how='outer').fillna(0)
    df_final['Utilidad'] = df_final['Ingresos'] - df_final['Gastos']
    df_final['Margen'] = (df_final['Utilidad'] / df_final['Ingresos'].replace(0, pd.NA)) * 100
    df_final['Margen'] = df_final['Margen'].fillna(0)
    df_final['Mes_Nom'] = df_final['Mes'].map(MES_MAP)
    df_final = df_final.sort_values('Mes')
    
    return df_final, df_g

# ── DASHBOARD UI ─────────────────────────────────────────────────────────────

# Carga y procesamiento
df_raw_i, df_raw_g = cargar_datos_rentabilidad()
df_resumen, df_gas_clean = procesar_datos(df_raw_i, df_raw_g)

if df_resumen.empty:
    st.warning("⚠️ No hay suficientes datos para generar el análisis de rentabilidad.")
    st.stop()

# Título y Estilo
st.markdown("""
<style>
    .reportview-container .main .block-container{
        padding-top: 2rem;
    }
    [data-testid="stMetric"] {
        background-color: rgba(26, 115, 232, 0.05);
        padding: 15px;
        border-radius: 12px;
        border-left: 5px solid #1a73e8;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

st.title("💹 Rentabilidad Operativa 2026")
st.markdown("Comparativa de **Ingresos Efectivos** vs **Gastos Generales** del periodo.")

# MÉTRICAS CLAVE
total_i = df_resumen['Ingresos'].sum()
total_g = df_resumen['Gastos'].sum()
total_u = total_i - total_g
margen_g = (total_u / total_i * 100) if total_i > 0 else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 Ingresos Totales", f"${total_i:,.0f}")
m2.metric("💸 Gastos Generales", f"${total_g:,.0f}")
m3.metric("📈 Utilidad Operativa", f"${total_u:,.0f}", 
          delta=f"{margen_g:.1f}% Margen", 
          delta_color="normal" if total_u >= 0 else "inverse")
m4.metric("📊 Margen Operativo", f"{margen_g:.1f}%")

st.markdown("---")

# SECCIÓN DE GRÁFICOS
col_chart1, col_chart2 = st.columns([1.5, 1])

with col_chart1:
    st.subheader("📅 Tendencia de Ingresos vs Gastos")
    fig_tendencia = go.Figure()
    fig_tendencia.add_trace(go.Bar(
        x=df_resumen['Mes_Nom'], y=df_resumen['Ingresos'],
        name='Ingresos Operativos', marker_color='#2ecc71', opacity=0.8
    ))
    fig_tendencia.add_trace(go.Bar(
        x=df_resumen['Mes_Nom'], y=df_resumen['Gastos'],
        name='Gastos Generales', marker_color='#e74c3c', opacity=0.8
    ))
    fig_tendencia.update_layout(
        barmode='group', height=400,
        margin=dict(t=20, b=20, l=0, r=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_tendencia, width='stretch')

with col_chart2:
    st.subheader("📊 Utilidad Neta Mensual")
    colors = ['#27ae60' if x > 0 else '#c0392b' for x in df_resumen['Utilidad']]
    fig_util = px.bar(df_resumen, x='Mes_Nom', y='Utilidad', text_auto='.2s')
    fig_util.update_traces(marker_color=colors, marker_line_color='rgb(8,48,107)', marker_line_width=1.5)
    fig_util.update_layout(height=400, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig_util, width='stretch')

st.markdown("---")

col_bottom1, col_bottom2 = st.columns([1, 1.5])

with col_bottom1:
    st.subheader("🍩 Distribución de Gastos (Rubros)")
    if 'Cod Rubro Pptal' in df_gas_clean.columns:
        df_rubros = df_gas_clean.groupby('Cod Rubro Pptal')['Monto'].sum().reset_index()
        fig_pie = px.pie(df_rubros, values='Monto', names='Cod Rubro Pptal', hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_layout(height=400, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, width='stretch')
    else:
        st.info("No se encontró desglose por rubros en los gastos.")

with col_bottom2:
    st.subheader("📈 Evolución del Margen (%)")
    fig_margen = go.Figure()
    fig_margen.add_trace(go.Scatter(
        x=df_resumen['Mes_Nom'], y=df_resumen['Margen'],
        mode='lines+markers+text',
        text=df_resumen['Margen'].apply(lambda x: f"{x:.1f}%"),
        textposition="top center",
        line=dict(color='#1a73e8', width=3),
        marker=dict(size=10, symbol='diamond'),
        fill='tozeroy', fillcolor='rgba(26, 115, 232, 0.1)'
    ))
    fig_margen.update_layout(height=400, margin=dict(t=20, b=20, l=0, r=0))
    st.plotly_chart(fig_margen, width='stretch')

st.markdown("---")

# TABLA DETALLADA
st.subheader("📋 Detalle de Seguimiento Mensual")
with st.expander("Expandir Tabla de Rentabilidad"):
    st.dataframe(
        df_resumen.sort_values('Mes'),
        column_config={
            "Mes": None,
            "Mes_Nom": st.column_config.TextColumn("Mes"),
            "Ingresos": st.column_config.NumberColumn("Ingresos", format="$%d"),
            "Gastos": st.column_config.NumberColumn("Gastos", format="$%d"),
            "Utilidad": st.column_config.NumberColumn("Utilidad", format="$%d"),
            "Margen": st.column_config.NumberColumn("Margen %", format="%.1f%%"),
        },
        hide_index=True,
        width='stretch'
    )
