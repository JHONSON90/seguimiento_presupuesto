import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
import traceback
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime


# ── CARGA DE DATOS ───────────────────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(show_spinner="Cargando datos de ingresos...", ttl=300)
def cargar_datos_ingresos():
    try:
        df_ppto = conn.read(worksheet="Ingresos Pptados", ttl=300)
        df_real = conn.read(worksheet="Control_Ingresos", ttl=300)
        placeholder = st.empty()
        placeholder.success("Conexión exitosa!!")
        time.sleep(1)
        placeholder.empty()
        return df_ppto, df_real
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {str(e)}")
        st.error(traceback.format_exc())
        return pd.DataFrame(), pd.DataFrame()

# Meses en español
MESES_ES = [
    'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
    'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE'
]
MES_MAP = {i + 1: name for i, name in enumerate(MESES_ES)}

def procesar_datos(df_ppto, df_real):
    if df_ppto.empty or df_real.empty:
        return pd.DataFrame(), pd.DataFrame()

    # ── PROCESAR PRESUPUESTO ─────────────────────────────────────────────────
    df_ppto_processed = df_ppto.copy()
    
    # Renombrar columnas según lo observado en los cambios del usuario y originales
    # Mapeo flexible para manejar variaciones de mayúsculas/minúsculas
    cols_map = {
        'Unidad Funcional': 'UF_Codigo',
        'Nom Uni Funcio': 'UF_Nombre',
        'Cuenta': 'Cuenta',
        'Descripcion': 'Descripcion',
        'Valor Presupuestado': 'Ppto_Anual',
        'VALOR PRESUPUESTADO': 'Ppto_Anual',
        'Valor Mensual': 'Ppto_Mensual',
        'valor mensual': 'Ppto_Mensual',
        'Tipo': 'Tipo',
        'tipo': 'Tipo'
    }
    df_ppto_processed = df_ppto_processed.rename(columns=cols_map)

    # Asegurar que las columnas críticas existan
    expected_cols = ['UF_Codigo', 'UF_Nombre', 'Cuenta', 'Ppto_Mensual', 'Tipo']
    for col in expected_cols:
        if col not in df_ppto_processed.columns:
            # Si falta una columna, intentamos buscarla en minúsculas si no estaba en el mapa
            orig_col = next((c for c in df_ppto.columns if c.lower() == col.lower()), None)
            if orig_col:
                df_ppto_processed[col] = df_ppto[orig_col]
            else:
                df_ppto_processed[col] = 0 if 'Ppto' in col else "Desconocido"

    # Limpieza de valores numéricos
    df_ppto_processed['Ppto_Mensual'] = pd.to_numeric(df_ppto_processed['Ppto_Mensual'], errors='coerce').fillna(0)
    
    # "Expandir" el presupuesto a 12 meses
    meses_lista = list(range(1, 13))
    df_ppto_long = pd.concat([df_ppto_processed.assign(Mes=m) for m in meses_lista])
    
    # ── PROCESAR EJECUCIÓN REAL ──────────────────────────────────────────────
    df_real_processed = df_real.copy()
    
    # CORRECCIÓN DE FECHA: Usar dayfirst=True para formato día/mes/año
    df_real_processed['FECHA'] = pd.to_datetime(df_real_processed['FECHA'], dayfirst=True, errors='coerce')
    df_real_processed = df_real_processed.dropna(subset=['FECHA'])
    
    df_real_processed['Mes'] = df_real_processed['FECHA'].dt.month
    
    # Mapeo de columnas de ejecución
    # El usuario cambió SALDO por Saldo
    saldo_col = 'Saldo' if 'Saldo' in df_real_processed.columns else 'SALDO'
    df_real_processed['Saldo_Real'] = pd.to_numeric(df_real_processed[saldo_col], errors='coerce').fillna(0)
    
    # Asegurar nombres de columnas para agrupación
    # 'Unidad Funcional' -> 'UF_Codigo', 'CUENTA' -> 'Cuenta'
    agg_cols = {
        'Unidad Funcional': 'UF_Codigo',
        'CUENTA': 'Cuenta'
    }
    df_real_agg_base = df_real_processed.rename(columns=agg_cols)
    
    # Agrupar ejecución por Mes, UF y Cuenta
    df_real_agg = df_real_agg_base.groupby(['UF_Codigo', 'Cuenta', 'Mes']).agg({
        'Saldo_Real': 'sum',
        'NIT': 'first',
        'NOMBRE': 'first',
        'Nom Uni Funcio': 'first' # Para rescatar el nombre si falta en ppto
    }).reset_index()
    
    # ── MERGE ────────────────────────────────────────────────────────────────
    df_final = pd.merge(
        df_ppto_long,
        df_real_agg,
        on=['UF_Codigo', 'Cuenta', 'Mes'],
        how='outer'
    )
    
    # Llenar nulos después del merge
    df_final['Ppto_Mensual'] = df_final['Ppto_Mensual'].fillna(0)
    df_final['Saldo_Real'] = df_final['Saldo_Real'].fillna(0)
    df_final['Mes_Nom'] = df_final['Mes'].map(MES_MAP)
    
    # Si UF_Nombre es nulo (registro en Real que no estaba en Ppto), traemos Nom Uni Funcio de la ejecución
    if 'Nom Uni Funcio' in df_final.columns:
        df_final['UF_Nombre'] = df_final['UF_Nombre'].fillna(df_final['Nom Uni Funcio'])
    
    if 'Tipo' in df_final.columns:
        df_final['Tipo'] = df_final['Tipo'].fillna('Eventos')
    
    # Cálculos adicionales
    df_final['Cumplimiento'] = (df_final['Saldo_Real'] / df_final['Ppto_Mensual'].replace(0, pd.NA)) * 100
    df_final['Cumplimiento'] = df_final['Cumplimiento'].fillna(0)
    df_final['Diferencia'] = df_final['Saldo_Real'] - df_final['Ppto_Mensual']

    return df_final, df_real_processed

# ─────────────────────────────────────────────────────────────────────────────
# EJECUCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

df_raw_ppto, df_raw_real = cargar_datos_ingresos()
df_final, df_real_clean = procesar_datos(df_raw_ppto, df_raw_real)

if df_final.empty:
    st.warning("⚠️ No se pudieron procesar los datos. Verifica las hojas 'Ingresos Pptados' y 'Control_Ingresos'.")
    st.stop()

# ── ENCABEZADO ───────────────────────────────────────────────────────────────
st.title("💰 Seguimiento de Ingresos 2026")
st.markdown("Análisis comparativo de **Facturación Real** vs **Presupuesto Mensual**.")

# ── FILTROS ──────────────────────────────────────────────────────────────────
st.header("🔍 Filtros de Análisis")
col1, col2, col3, col4 = st.columns(4)

with col1:
    all_ufs = sorted(df_final['UF_Nombre'].dropna().unique().tolist())
    selected_ufs = st.multiselect("🏥 Unidad Funcional", all_ufs)

with col2:
    all_tipos = sorted(df_final['Tipo'].dropna().astype(str).unique().tolist())
    selected_tipos = st.multiselect("🏷️ Tipo de Ingreso", all_tipos)

with col3:
    all_meses = MESES_ES
    selected_meses = st.multiselect("📅 Mes", all_meses)

with col4:
    all_clientes = sorted(df_real_clean['NOMBRE'].dropna().unique().tolist())
    selected_clientes = st.multiselect("👤 Cliente", all_clientes)

# Aplicar Filtros
df_filtered = df_final.copy()
df_real_filtered = df_real_clean.copy()

if selected_ufs:
    df_filtered = df_filtered[df_filtered['UF_Nombre'].isin(selected_ufs)]
    df_real_filtered = df_real_filtered[df_real_filtered['Nom Uni Funcio'].isin(selected_ufs)]
if selected_tipos:
    df_filtered = df_filtered[df_filtered['Tipo'].isin(selected_tipos)]
if selected_meses:
    df_filtered = df_filtered[df_filtered['Mes_Nom'].isin(selected_meses)]
    df_real_filtered = df_real_filtered[df_real_filtered['FECHA'].dt.month.map(MES_MAP).isin(selected_meses)]
if selected_clientes:
    df_real_filtered = df_real_filtered[df_real_filtered['NOMBRE'].isin(selected_clientes)]
    nit_list = df_real_filtered['NIT'].unique()
    df_filtered = df_filtered[df_filtered['NIT'].isin(nit_list) | (df_filtered['Saldo_Real'] == 0)]

st.markdown("---")

# ── MÉTRICAS PRINCIPALES ─────────────────────────────────────────────────────
total_ppto = df_filtered['Ppto_Mensual'].sum()
total_real = df_filtered['Saldo_Real'].sum()
cumplimiento_total = (total_real / total_ppto * 100) if total_ppto > 0 else 0
diferencia_total = total_real - total_ppto

m1, m2, m3, m4 = st.columns(4)
m1.metric("📊 Presupuesto (Periodo)", f"${total_ppto:,.0f}")
m2.metric("💵 Facturación Real", f"${total_real:,.0f}", 
          delta=f"{cumplimiento_total:.1f}% cumplimiento", 
          delta_color="normal" if cumplimiento_total >= 100 else "inverse")
m3.metric("⚖️ Diferencia", f"${diferencia_total:,.0f}", 
          delta="Sobre presupuesto" if diferencia_total > 0 else "Bajo presupuesto",
          delta_color="normal" if diferencia_total >= 0 else "inverse")
m4.metric("📈 % Cumplimiento General", f"{cumplimiento_total:.1f}%")

st.markdown("---")

# ── GRÁFICOS DE ANÁLISIS ─────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📅 Tendencia Mensual: Presupuesto vs Real")
    df_trend = df_filtered.groupby(['Mes', 'Mes_Nom']).agg({
        'Ppto_Mensual': 'sum',
        'Saldo_Real': 'sum'
    }).reset_index().sort_values('Mes')
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(x=df_trend['Mes_Nom'], y=df_trend['Ppto_Mensual'], name='Presupuesto', marker_color='#3498db'))
    fig_trend.add_trace(go.Bar(x=df_trend['Mes_Nom'], y=df_trend['Saldo_Real'], name='Real', marker_color='#2ecc71'))
    fig_trend.update_layout(barmode='group', height=400, margin=dict(t=20, b=20, l=0, r=0))
    st.plotly_chart(fig_trend, width='stretch')

with col_right:
    st.subheader("🎯 Mix por Tipo de Ingreso")
    df_tipo = df_filtered.groupby('Tipo')['Saldo_Real'].sum().reset_index()
    if not df_tipo.empty and df_tipo['Saldo_Real'].sum() > 0:
        fig_pie = px.pie(df_tipo, values='Saldo_Real', names='Tipo', hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Safe)
        fig_pie.update_layout(height=400, margin=dict(t=20, b=20, l=0, r=0))
        st.plotly_chart(fig_pie, width='stretch')
    else:
        st.info("Sin datos para mostrar.")

st.markdown("---")

# ── COMPARATIVO POR UNIDAD FUNCIONAL ─────────────────────────────────────────
st.subheader("🏥 Comparativo por Unidad Funcional")
df_uf_summary = df_filtered.groupby(['UF_Codigo', 'UF_Nombre']).agg({
    'Ppto_Mensual': 'sum',
    'Saldo_Real': 'sum'
}).reset_index()

df_uf_summary['Cumplimiento'] = (df_uf_summary['Saldo_Real'] / df_uf_summary['Ppto_Mensual'].replace(0, pd.NA)) * 100
df_uf_summary['Cumplimiento'] = df_uf_summary['Cumplimiento'].fillna(0).round(1)

fig_uf = go.Figure()
fig_uf.add_trace(go.Bar(
    y=df_uf_summary['UF_Nombre'],
    x=df_uf_summary['Ppto_Mensual'],
    name='Presupuesto',
    orientation='h',
    marker_color='#bdc3c7'
))
fig_uf.add_trace(go.Bar(
    y=df_uf_summary['UF_Nombre'],
    x=df_uf_summary['Saldo_Real'],
    name='Real',
    orientation='h',
    marker_color='#27ae60'
))
fig_uf.update_layout(
    barmode='group',
    height=max(400, len(df_uf_summary) * 40),
    margin=dict(t=20, b=20, l=0, r=0),
    yaxis={'categoryorder':'total ascending'}
)
st.plotly_chart(fig_uf, width='stretch')

st.markdown("---")

# ── TOP CLIENTES ─────────────────────────────────────────────────────────────
st.subheader("👥 Caracterización: Top 10 Clientes por Facturación")
df_client_top = df_real_filtered.groupby(['NIT', 'NOMBRE'])['Saldo_Real'].sum().reset_index()
df_client_top = df_client_top.sort_values('Saldo_Real', ascending=False).head(10)

if not df_client_top.empty:
    fig_clients = px.bar(df_client_top, x='Saldo_Real', y='NOMBRE', orientation='h',
                         text_auto='.2s', color='Saldo_Real',
                         color_continuous_scale='Greens',
                         title="Top Clientes del Periodo")
    fig_clients.update_layout(yaxis={'categoryorder':'total ascending'}, height=450)
    st.plotly_chart(fig_clients, width='stretch')
else:
    st.info("Sin datos de clientes para mostrar.")

st.markdown("---")

# ANALISIS POR CUENTA CONTABLE

st.subheader("📊 Análisis por Cuenta Contable")

# Agrupar por cuenta contable
df_cuenta_summary = df_filtered.groupby(['Cuenta', 'Descripcion']).agg({
    'Ppto_Mensual': 'sum',
    'Saldo_Real': 'sum'
}).reset_index()

# Calcular cumplimiento por cuenta
df_cuenta_summary['Cumplimiento'] = (df_cuenta_summary['Saldo_Real'] / df_cuenta_summary['Ppto_Mensual'].replace(0, pd.NA)) * 100
df_cuenta_summary['Cumplimiento'] = df_cuenta_summary['Cumplimiento'].fillna(0).round(1)

# Filtrar cuentas con saldo real mayor a 0
df_cuenta_summary = df_cuenta_summary[df_cuenta_summary['Saldo_Real'] > 0]
df_cuenta_summary_fig = df_cuenta_summary.sort_values('Saldo_Real', ascending=False).head(20)

if not df_cuenta_summary.empty:
    # Gráfico de barras por cuenta contable
    fig_cc = go.Figure()
    fig_cc.add_trace(go.Bar(
        y=df_cuenta_summary_fig['Descripcion'],
        x=df_cuenta_summary_fig['Ppto_Mensual'],
        name='Presupuesto',
        orientation='h',
        marker_color='#bdc3c7'
    ))
    fig_cc.add_trace(go.Bar(
        y=df_cuenta_summary_fig['Descripcion'],
        x=df_cuenta_summary_fig['Saldo_Real'],
        name='Real',
        orientation='h',
        marker_color='#27ae60'
    ))
    fig_cc.update_layout(
        barmode='group',
        height=max(400, len(df_cuenta_summary_fig) * 40),
        margin=dict(t=20, b=20, l=0, r=0),
        yaxis={'categoryorder':'total ascending'}
    )
    st.plotly_chart(fig_cc, width='stretch')
    
    # Tabla de detalle por cuenta
    with st.expander("Detalle por Cuenta Contable"):
        st.dataframe(
            df_cuenta_summary.sort_values('Cumplimiento', ascending=False),
            column_config={
                "Ppto_Mensual": st.column_config.NumberColumn("Ppto Mensual", format="$%d"),
                "Saldo_Real": st.column_config.NumberColumn("Saldo Real", format="$%d"),
                "Cumplimiento": st.column_config.ProgressColumn("% Cumplimiento", format="%.1f%%", min_value=0, max_value=200),
            },
            hide_index=True,
            width='stretch'
        )
else:
    st.info("No se registraron ingresos por cuenta contable en este periodo.")

st.markdown("---")
# ── TABLA DE DETALLE ─────────────────────────────────────────────────────────
st.subheader("📄 Detalle de Facturación y Presupuesto")
with st.expander("Expandir Tabla Detallada"):
    df_display = df_filtered[['UF_Nombre', 'Tipo', 'Cuenta', 'Mes_Nom', 'Ppto_Mensual', 'Saldo_Real', 'Diferencia', 'Cumplimiento']].copy()
    
    st.dataframe(
        df_display.sort_values(['UF_Nombre', 'Mes_Nom']),
        column_config={
            "Ppto_Mensual": st.column_config.NumberColumn("Ppto Mensual", format="$%d"),
            "Saldo_Real": st.column_config.NumberColumn("Saldo Real", format="$%d"),
            "Diferencia": st.column_config.NumberColumn("Diferencia", format="$%d"),
            "Cumplimiento": st.column_config.ProgressColumn("% Cumplimiento", format="%.1f%%", min_value=0, max_value=200),
        },
        hide_index=True,
        width='stretch'
    )
