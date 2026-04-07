import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import plotly.graph_objects as go
import traceback


conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(show_spinner="Cargando datos del presupuesto...", ttl=300)
def cargar_datos_ppto():
    try:
        df_ppto = conn.read(worksheet="Por CC", ttl=300)
        df_real = conn.read(worksheet="Control por CC", ttl=300)
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
MES_MAP = {name: i + 1 for i, name in enumerate(MESES_ES)}
NUM_MES_MAP = {v: k for k, v in MES_MAP.items()}   # número → nombre


def procesar_datos(df_ppto, df_real):
    if df_ppto.empty or df_real.empty:
        return pd.DataFrame()

    
    cols_fijas = [c for c in df_ppto.columns if c not in MESES_ES]
    meses_disponibles = [m for m in MESES_ES if m in df_ppto.columns]

    df_ppto_long = pd.melt(
        df_ppto,
        id_vars=cols_fijas,
        value_vars=meses_disponibles,
        var_name='Mes_Nom',
        value_name='Presupuesto'
    )
    df_ppto_long['Mes'] = df_ppto_long['Mes_Nom'].map(MES_MAP).astype(int)
    df_ppto_long['Presupuesto'] = pd.to_numeric(
        df_ppto_long['Presupuesto'], errors='coerce'
    ).fillna(0)

    df_ppto_long = df_ppto_long.groupby(['CENTRO DE COSTOS', 'Rubro Presupuestal', 'Mes_Nom', 'Mes']).agg(
        Presupuesto=('Presupuesto', 'sum')
    ).reset_index()

    # ── EJECUCIÓN REAL ────────────────────────────────────────────────────────
    df_real = df_real.copy()
    df_real['FECHA'] = pd.to_datetime(df_real['FECHA'], errors='coerce')

    # FIX: eliminar filas sin fecha válida → evita el "Mes 0"
    registros_sin_fecha = df_real['FECHA'].isna().sum()
    if registros_sin_fecha > 0:
        st.info(
            f"ℹ️ Se excluyeron **{registros_sin_fecha}** registro(s) sin fecha válida "
            "en 'Control por CC'."
        )
    df_real = df_real.dropna(subset=['FECHA'])

    df_real['Mes'] = df_real['FECHA'].dt.month.astype(int)
    df_real['valor_costo'] = pd.to_numeric(
        df_real['valor_costo'], errors='coerce'
    ).fillna(0)

    # Agrupar real por CC + Rubro + Mes
    df_real_agg = (
        df_real
        .groupby(['CENTRO DE COSTOS', 'Rubro Presupuestal', 'Mes'])['valor_costo']
        .sum()
        .reset_index()
        .rename(columns={'valor_costo': 'Ejecutado'})
    )

    # ── MERGE ─────────────────────────────────────────────────────────────────
    df_ppto_long['Rubro Presupuestal'] = df_ppto_long['Rubro Presupuestal'].astype(str)
    df_real_agg['Rubro Presupuestal'] = df_real_agg['Rubro Presupuestal'].astype(str)

    df_final = pd.merge(
        df_ppto_long,
        df_real_agg,
        on=['CENTRO DE COSTOS', 'Rubro Presupuestal', 'Mes'],
        how='outer'
    ).fillna(0)

    # FIX: eliminar filas con Mes==0 producidas por fillna del merge outer
    df_final = df_final[df_final['Mes'] > 0].copy()

    # FIX: reconstruir Mes_Nom desde el número de mes (post-merge puede ser 0/vacío)
    df_final['Mes'] = df_final['Mes'].astype(int)
    df_final['Mes_Nom'] = df_final['Mes'].map(NUM_MES_MAP)

    # Cálculos derivados
    df_final['Diferencia'] = df_final['Presupuesto'] - df_final['Ejecutado']
    df_final['% Ejecución'] = (
        (df_final['Ejecutado'] / df_final['Presupuesto'].replace(0, pd.NA)) * 100
    ).fillna(0)

    return df_final


# ─────────────────────────────────────────────────────────────────────────────
# CARGA Y PROCESAMIENTO
# ─────────────────────────────────────────────────────────────────────────────
df_raw_ppto, df_raw_real = cargar_datos_ppto()
df_final = procesar_datos(df_raw_ppto, df_raw_real)

if df_final.empty:
    st.warning(
        "⚠️ No se encontraron datos para mostrar. "
        "Verifique las hojas 'Por CC' y 'Control por CC'."
    )
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ENCABEZADO
# ─────────────────────────────────────────────────────────────────────────────

st.write(df_final)
st.title("🛡️ Dashboard de Seguimiento Presupuestal 2026")
st.markdown("Comparativo entre **Presupuesto Aprobado** y **Ejecución Real** por CC y Rubro.")

st.header("🔍 Filtros de Seguimiento")

col1, col2, col3 = st.columns(3)
with col1:
    all_cc = sorted(df_final['CENTRO DE COSTOS'].unique().tolist())
    selected_cc = st.multiselect("🏥 Centro de Costo", all_cc)
with col2:
    all_rubros = sorted(df_final['Rubro Presupuestal'].unique().tolist())
    selected_rubros = st.multiselect("🏷️ Rubro Presupuestal", all_rubros)
with col3:
    meses_disponibles_ui = [m for m in MESES_ES if m in df_final['Mes_Nom'].unique()]
    selected_meses = st.multiselect("📅 Mes", meses_disponibles_ui)

st.markdown("---")

# ── Aplicar filtros ───────────────────────────────────────────────────────────
df_filtered = df_final.copy()
if selected_cc:
    df_filtered = df_filtered[df_filtered['CENTRO DE COSTOS'].isin(selected_cc)]
if selected_rubros:
    df_filtered = df_filtered[df_filtered['Rubro Presupuestal'].isin(selected_rubros)]
if selected_meses:
    df_filtered = df_filtered[df_filtered['Mes_Nom'].isin(selected_meses)]

# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICAS PRINCIPALES
# ─────────────────────────────────────────────────────────────────────────────
total_ppto = df_filtered['Presupuesto'].sum()
total_real = df_filtered['Ejecutado'].sum()
total_diff = total_ppto - total_real
exec_perc = (total_real / total_ppto * 100) if total_ppto > 0 else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 Presupuesto Inicial", f"${total_ppto:,.0f}")
m2.metric(
    "💳 Ejecutado Real",
    f"${total_real:,.0f}",
    delta=f"{exec_perc:.1f}% de ejecución",
    delta_color="inverse"
)
m3.metric(
    "📉 Saldo Disponible",
    f"${total_diff:,.0f}",
    delta_color="normal"
)
m4.metric("📈 % Ejecución Total", f"{exec_perc:.1f}%")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 1: TENDENCIA MENSUAL
# ─────────────────────────────────────────────────────────────────────────────
col_chart1, col_chart2 = st.columns([2, 1])

with col_chart1:
    st.subheader("📅 Tendencia Mensual: Presupuesto vs Real")

    df_mensual = (
        df_filtered
        .groupby(['Mes', 'Mes_Nom'])
        .agg(Presupuesto=('Presupuesto', 'sum'), Ejecutado=('Ejecutado', 'sum'))
        .reset_index()
        .sort_values('Mes')
    )

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
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with col_chart2:
    st.subheader("🎯 Distribución por Rubro")
    df_rubro_pie = df_filtered.groupby('Rubro Presupuestal')['Ejecutado'].sum().reset_index()
    df_rubro_pie = df_rubro_pie[df_rubro_pie['Ejecutado'] > 0]
    if not df_rubro_pie.empty:
        fig_pie = px.pie(
            df_rubro_pie,
            values='Ejecutado',
            names='Rubro Presupuestal',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_layout(height=420)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Sin ejecución para mostrar.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 2: DETALLE POR CENTRO DE COSTO
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🏢 Detalle de Ejecución por Centro de Costo")

df_cc_summary = (
    df_filtered
    .groupby('CENTRO DE COSTOS')
    .agg(
        Presupuesto=('Presupuesto', 'sum'),
        Ejecutado=('Ejecutado', 'sum'),
        Diferencia=('Diferencia', 'sum')
    )
    .reset_index()
)
df_cc_summary['% Ejecución'] = (
    df_cc_summary['Ejecutado'] / df_cc_summary['Presupuesto'].replace(0, pd.NA) * 100
).fillna(0).round(1)

st.dataframe(
    df_cc_summary.sort_values('Ejecutado', ascending=False),
    column_config={
        "Presupuesto": st.column_config.NumberColumn("Presupuesto", format="$%d"),
        "Ejecutado": st.column_config.NumberColumn("Ejecutado", format="$%d"),
        "Diferencia": st.column_config.NumberColumn("Diferencia", format="$%d"),
        "% Ejecución": st.column_config.ProgressColumn(
            "% Ejecución", format="%.1f%%", min_value=0, max_value=100
        ),
    },
    hide_index=True,
    use_container_width=True
)

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 3: COMPARATIVO POR RUBRO POR MES
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📊 Comparativo por Rubro Presupuestal por Mes")

tab_tabla, tab_grafico = st.tabs(["📋 Tabla", "📈 Gráfico"])

df_rubro_mes = (
    df_filtered
    .groupby(['Rubro Presupuestal', 'Mes', 'Mes_Nom'])
    .agg(
        Presupuesto=('Presupuesto', 'sum'),
        Ejecutado=('Ejecutado', 'sum')
    )
    .reset_index()
    .sort_values(['Rubro Presupuestal', 'Mes'])
)
df_rubro_mes['Diferencia'] = df_rubro_mes['Presupuesto'] - df_rubro_mes['Ejecutado']
df_rubro_mes['% Ejecución'] = (
    df_rubro_mes['Ejecutado'] / df_rubro_mes['Presupuesto'].replace(0, pd.NA) * 100
).fillna(0).round(1)

with tab_tabla:
    st.dataframe(
        df_rubro_mes[['Rubro Presupuestal', 'Mes_Nom', 'Presupuesto', 'Ejecutado', 'Diferencia', '% Ejecución']],
        column_config={
            "Mes_Nom": st.column_config.TextColumn("Mes"),
            "Presupuesto": st.column_config.NumberColumn("Presupuesto", format="$%d"),
            "Ejecutado": st.column_config.NumberColumn("Ejecutado", format="$%d"),
            "Diferencia": st.column_config.NumberColumn("Diferencia", format="$%d"),
            "% Ejecución": st.column_config.ProgressColumn(
                "% Ejecución", format="%.1f%%", min_value=0, max_value=100
            ),
        },
        hide_index=True,
        use_container_width=True
    )

with tab_grafico:
    rubros_unicos = sorted(df_rubro_mes['Rubro Presupuestal'].unique().tolist())
    rubro_sel = st.selectbox(
        "Selecciona un Rubro para ver su tendencia mensual:",
        rubros_unicos,
        key="rubro_tendencia"
    )
    df_rubro_sel = df_rubro_mes[df_rubro_mes['Rubro Presupuestal'] == rubro_sel].sort_values('Mes')

    fig_rubro = go.Figure()
    fig_rubro.add_trace(go.Bar(
        x=df_rubro_sel['Mes_Nom'],
        y=df_rubro_sel['Presupuesto'],
        name='Presupuesto',
        marker_color='#2ecc71'
    ))
    fig_rubro.add_trace(go.Bar(
        x=df_rubro_sel['Mes_Nom'],
        y=df_rubro_sel['Ejecutado'],
        name='Ejecutado',
        marker_color='#e67e22'
    ))
    fig_rubro.update_layout(
        barmode='group',
        title=f"Tendencia mensual: {rubro_sel}",
        xaxis_title="Mes",
        yaxis_title="Monto (COP)",
        hovermode="x unified",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_rubro, use_container_width=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 4: ALERTAS — CC SOBRE EL PRESUPUESTO
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🚨 Alertas: Centros de Costo sobre el Presupuesto")

df_cc_alerta = df_cc_summary[df_cc_summary['Diferencia'] < 0].copy()
df_cc_alerta['Sobre-ejecución'] = df_cc_alerta['Ejecutado'] - df_cc_alerta['Presupuesto']
df_cc_alerta['% Exceso'] = (
    df_cc_alerta['Sobre-ejecución'] / df_cc_alerta['Presupuesto'].replace(0, pd.NA) * 100
).fillna(0).round(1)

if df_cc_alerta.empty:
    st.success("✅ Ningún Centro de Costo ha superado su presupuesto en el período seleccionado.")
else:
    st.error(f"⚠️ **{len(df_cc_alerta)} Centro(s) de Costo** han superado su presupuesto:")

    # Gráfico de barras horizontales de exceso
    df_cc_alerta_sorted = df_cc_alerta.sort_values('Sobre-ejecución', ascending=True)
    fig_alerta_cc = go.Figure(go.Bar(
        x=df_cc_alerta_sorted['Sobre-ejecución'],
        y=df_cc_alerta_sorted['CENTRO DE COSTOS'],
        orientation='h',
        marker_color='#e74c3c',
        text=df_cc_alerta_sorted['% Exceso'].apply(lambda x: f"{x:.1f}% exceso"),
        textposition='outside'
    ))
    fig_alerta_cc.update_layout(
        title="Monto de sobre-ejecución por Centro de Costo",
        xaxis_title="Monto sobre el presupuesto (COP)",
        height=max(300, len(df_cc_alerta) * 50 + 100),
        margin=dict(l=200)
    )
    st.plotly_chart(fig_alerta_cc, use_container_width=True)

    st.dataframe(
        df_cc_alerta[['CENTRO DE COSTOS', 'Presupuesto', 'Ejecutado', 'Sobre-ejecución', '% Exceso']]
        .sort_values('Sobre-ejecución', ascending=False),
        column_config={
            "Presupuesto": st.column_config.NumberColumn("Presupuesto", format="$%d"),
            "Ejecutado": st.column_config.NumberColumn("Ejecutado", format="$%d"),
            "Sobre-ejecución": st.column_config.NumberColumn("Sobre-ejecución", format="$%d"),
            "% Exceso": st.column_config.NumberColumn("% Exceso", format="%.1f%%"),
        },
        hide_index=True,
        use_container_width=True
    )

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 5: ALERTAS — RUBROS SOBRE EL PRESUPUESTO
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🏷️ Alertas: Rubros Presupuestales sobre el Presupuesto")

# Agrupar por CC + Rubro para ver dónde exactamente se da el exceso
df_rubro_alerta = (
    df_filtered
    .groupby(['CENTRO DE COSTOS', 'Rubro Presupuestal'])
    .agg(
        Presupuesto=('Presupuesto', 'sum'),
        Ejecutado=('Ejecutado', 'sum')
    )
    .reset_index()
)
df_rubro_alerta['Diferencia'] = df_rubro_alerta['Presupuesto'] - df_rubro_alerta['Ejecutado']
df_rubro_alerta['Sobre-ejecución'] = df_rubro_alerta['Ejecutado'] - df_rubro_alerta['Presupuesto']
df_rubro_alerta['% Exceso'] = (
    df_rubro_alerta['Sobre-ejecución'] / df_rubro_alerta['Presupuesto'].replace(0, pd.NA) * 100
).fillna(0).round(1)

df_rubro_alerta_filtrado = df_rubro_alerta[df_rubro_alerta['Diferencia'] < 0].copy()

if df_rubro_alerta_filtrado.empty:
    st.success("✅ Ningún rubro ha superado su presupuesto en el período seleccionado.")
else:
    n_rubros = len(df_rubro_alerta_filtrado)
    st.error(f"⚠️ **{n_rubros} combinación(es) CC / Rubro** han superado el presupuesto:")

    # Heatmap de exceso: CC vs Rubro
    df_heat = df_rubro_alerta_filtrado.pivot_table(
        index='CENTRO DE COSTOS',
        columns='Rubro Presupuestal',
        values='% Exceso',
        aggfunc='sum',
        fill_value=0
    )
    if not df_heat.empty:
        fig_heat = px.imshow(
            df_heat,
            text_auto=".1f",
            color_continuous_scale=["#fff3cd", "#f39c12", "#e74c3c"],
            title="% de Exceso por CC y Rubro (solo los que superan presupuesto)",
            labels=dict(color="% Exceso"),
            aspect="auto"
        )
        fig_heat.update_layout(
            height=max(350, len(df_heat) * 50 + 150),
            xaxis_title="Rubro Presupuestal",
            yaxis_title="Centro de Costo"
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    st.dataframe(
        df_rubro_alerta_filtrado[
            ['CENTRO DE COSTOS', 'Rubro Presupuestal', 'Presupuesto', 'Ejecutado', 'Sobre-ejecución', '% Exceso']
        ].sort_values('Sobre-ejecución', ascending=False),
        column_config={
            "Presupuesto": st.column_config.NumberColumn("Presupuesto", format="$%d"),
            "Ejecutado": st.column_config.NumberColumn("Ejecutado", format="$%d"),
            "Sobre-ejecución": st.column_config.NumberColumn("Sobre-ejecución", format="$%d"),
            "% Exceso": st.column_config.NumberColumn("% Exceso", format="%.1f%%"),
        },
        hide_index=True,
        use_container_width=True
    )

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 6: TABLA COMPLETA (EXPANDIBLE)
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📄 Ver Tabla de Datos Completa"):
    st.dataframe(
        df_filtered[['CENTRO DE COSTOS', 'Rubro Presupuestal', 'Mes_Nom', 'Presupuesto', 'Ejecutado', 'Diferencia', '% Ejecución']],
        column_config={
            "Mes_Nom": st.column_config.TextColumn("Mes"),
            "Presupuesto": st.column_config.NumberColumn("Presupuesto", format="$%d"),
            "Ejecutado": st.column_config.NumberColumn("Ejecutado", format="$%d"),
            "Diferencia": st.column_config.NumberColumn("Diferencia", format="$%d"),
            "% Ejecución": st.column_config.ProgressColumn("% Ejecución", format="%.1f%%", min_value=0, max_value=100),
        },
        hide_index=True,
        use_container_width=True
    )