"""
Módulo compartido para análisis de efectividad de autorizaciones.
Usado por gastos.py y consumos.py para comparar datos autorizados vs reales.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def inject_efectividad_css():
    """Inyecta los estilos premium para la sección de efectividad."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ─── Metric Cards ─── */
    .eff-card {
        background: linear-gradient(135deg, rgba(30,34,45,0.92) 0%, rgba(22,26,35,0.97) 100%);
        border-radius: 18px;
        padding: 26px 28px;
        border: 1px solid rgba(255,255,255,0.06);
        box-shadow: 0 8px 32px rgba(0,0,0,0.25);
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .eff-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        border-radius: 18px 18px 0 0;
    }
    .eff-card.green::before  { background: linear-gradient(90deg, #10b981, #34d399); }
    .eff-card.blue::before   { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
    .eff-card.amber::before  { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
    .eff-card.red::before    { background: linear-gradient(90deg, #ef4444, #f87171); }
    .eff-card.purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
    .eff-card:hover { transform: translateY(-4px); box-shadow: 0 16px 48px rgba(0,0,0,0.35); }
    .eff-card .label {
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: rgba(255,255,255,0.5);
        margin-bottom: 8px;
    }
    .eff-card .value {
        font-family: 'Inter', sans-serif;
        font-size: 28px;
        font-weight: 800;
        color: #fff;
        line-height: 1.1;
    }
    .eff-card .delta {
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 600;
        margin-top: 8px;
    }
    .delta-positive { color: #34d399; }
    .delta-negative { color: #f87171; }
    .delta-neutral  { color: #fbbf24; }

    /* ─── Section Title ─── */
    .eff-section-title {
        font-family: 'Inter', sans-serif;
        font-size: 22px;
        font-weight: 700;
        background: linear-gradient(135deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 32px 0 18px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba(96,165,250,0.15);
    }

    /* ─── Gauge Label ─── */
    .gauge-label {
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        font-weight: 600;
        color: rgba(255,255,255,0.6);
        text-align: center;
        margin-top: -10px;
    }

    /* ─── Legend Badge ─── */
    .legend-row {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        margin: 12px 0 20px 0;
    }
    .legend-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 500;
        color: rgba(255,255,255,0.7);
        background: rgba(255,255,255,0.04);
        padding: 6px 14px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .legend-dot {
        width: 10px; height: 10px;
        border-radius: 50%;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)


def _metric_card(label, value, delta_text="", delta_class="delta-neutral", card_color="blue"):
    """Renders a premium metric card."""
    delta_html = f'<div class="delta {delta_class}">{delta_text}</div>' if delta_text else ""
    st.markdown(f"""
    <div class="eff-card {card_color}">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def _gauge_chart(pct):
    """Plotly gauge showing effectiveness percentage."""
    if pct > 100:
        bar_color = "#ef4444"
    elif pct >= 80:
        bar_color = "#10b981"
    else:
        bar_color = "#f59e0b"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={"suffix": "%", "font": {"size": 38, "color": "white", "family": "Inter"}},
        gauge={
            "axis": {"range": [0, max(150, pct + 10)], "tickwidth": 0,
                     "tickcolor": "rgba(0,0,0,0)"},
            "bar": {"color": bar_color, "thickness": 0.35},
            "bgcolor": "rgba(255,255,255,0.04)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 80], "color": "rgba(245,158,11,0.08)"},
                {"range": [80, 100], "color": "rgba(16,185,129,0.08)"},
                {"range": [100, max(150, pct + 10)], "color": "rgba(239,68,68,0.08)"},
            ],
            "threshold": {
                "line": {"color": "#60a5fa", "width": 3},
                "thickness": 0.8,
                "value": 100,
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "family": "Inter"},
        height=220,
        margin=dict(l=30, r=30, t=30, b=10),
    )
    return fig


def render_efectividad(df_auth, df_real,
                       auth_rubro_col, auth_valor_col,
                       real_rubro_col, real_valor_col,
                       auth_fecha_col, real_fecha_col,
                       section_name, emoji):
    """
    Renders the full effectiveness comparison section inline.
    Call this at the bottom of gastos.py or consumos.py.

    Parameters
    ----------
    df_auth : DataFrame — manual authorizations (Control GG / Control Consumos)
    df_real : DataFrame — real execution data (Gastos_Grales_reales / Control Compras)
    auth_rubro_col : str — column name for rubro in df_auth
    auth_valor_col : str — column name for value in df_auth
    real_rubro_col : str — column name for rubro in df_real
    real_valor_col : str — column name for value in df_real
    auth_fecha_col : str — column name for date in df_auth
    real_fecha_col : str — column name for date in df_real
    section_name : str — display name for section title
    emoji : str — emoji for section title
    """

    # ── Inject CSS (idempotent) ─────────────────────────────────────
    inject_efectividad_css()

    # ── Prepare data copies ─────────────────────────────────────────
    df_a = df_auth.copy()
    df_r = df_real.copy()

    df_a[auth_fecha_col] = pd.to_datetime(df_a[auth_fecha_col], dayfirst=True, errors='coerce')
    df_r[real_fecha_col] = pd.to_datetime(df_r[real_fecha_col], dayfirst=True, errors='coerce')
    df_a[auth_valor_col] = pd.to_numeric(df_a[auth_valor_col], errors='coerce').fillna(0)
    df_r[real_valor_col] = pd.to_numeric(df_r[real_valor_col], errors='coerce').fillna(0)

    df_a['_mes'] = df_a[auth_fecha_col].dt.month
    df_a['_mes_nombre'] = df_a[auth_fecha_col].dt.month_name()
    df_r['_mes'] = df_r[real_fecha_col].dt.month
    df_r['_mes_nombre'] = df_r[real_fecha_col].dt.month_name()

    # ── Aggregate by Rubro ──────────────────────────────────────────
    auth_by_rubro = df_a.groupby(auth_rubro_col)[auth_valor_col].sum().reset_index()
    auth_by_rubro.columns = ['Rubro', 'Autorizado']

    real_by_rubro = df_r.groupby(real_rubro_col)[real_valor_col].sum().reset_index()
    real_by_rubro.columns = ['Rubro', 'Ejecutado']

    comp = auth_by_rubro.merge(real_by_rubro, on='Rubro', how='outer').fillna(0)
    comp['Diferencia'] = comp['Ejecutado'] - comp['Autorizado']
    comp['% Ejecución'] = np.where(
        comp['Autorizado'] != 0,
        (comp['Ejecutado'] / comp['Autorizado'] * 100).round(1), 0
    )
    comp['Estado'] = comp['% Ejecución'].apply(
        lambda x: '✅ En rango' if 80 <= x <= 100
        else ('⚠️ Sub-ejecutado' if x < 80
              else ('🔴 Sobre-ejecutado' if x > 100 else '⬜ Sin datos'))
    )

    total_auth = comp['Autorizado'].sum()
    total_real = comp['Ejecutado'].sum()
    total_diff = total_real - total_auth
    pct_global = (total_real / total_auth * 100) if total_auth > 0 else 0

    # ── Section Header ──────────────────────────────────────────────
    st.divider()
    st.markdown(
        f'<div class="eff-section-title">{emoji} Efectividad de Autorizaciones — {section_name}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("""
    <div class="legend-row">
        <span class="legend-badge"><span class="legend-dot" style="background:#3b82f6"></span>Autorizado (manual)</span>
        <span class="legend-badge"><span class="legend-dot" style="background:#10b981"></span>Ejecutado (real)</span>
        <span class="legend-badge"><span class="legend-dot" style="background:#f59e0b"></span>Sub-ejecutado (&lt;80%)</span>
        <span class="legend-badge"><span class="legend-dot" style="background:#ef4444"></span>Sobre-ejecutado (&gt;100%)</span>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI Row ─────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        _metric_card("Total Autorizado", f"${total_auth:,.0f}", card_color="blue")
    with k2:
        _metric_card("Total Ejecutado", f"${total_real:,.0f}", card_color="green")
    with k3:
        delta_cls = "delta-negative" if total_diff > 0 else "delta-positive"
        sign = "+" if total_diff > 0 else ""
        _metric_card("Diferencia", f"${total_diff:,.0f}",
                     delta_text=f"{sign}${total_diff:,.0f}", delta_class=delta_cls,
                     card_color="amber")
    with k4:
        en_rango = (comp['Estado'] == '✅ En rango').sum()
        n_rubros = max(len(comp), 1)
        _metric_card("Rubros en Rango", f"{en_rango} / {len(comp)}",
                     delta_text=f"{en_rango / n_rubros * 100:.0f}% efectividad",
                     delta_class="delta-positive" if en_rango / n_rubros * 100 >= 70 else "delta-negative",
                     card_color="purple")
    with k5:
        sobre = (comp['Estado'] == '🔴 Sobre-ejecutado').sum()
        _metric_card("Sobre-ejecutados", f"{sobre}",
                     delta_text=f"{sobre} rubros excedidos" if sobre > 0 else "Sin excesos",
                     delta_class="delta-negative" if sobre > 0 else "delta-positive",
                     card_color="red")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts Row ──────────────────────────────────────────────────
    chart_left, chart_right = st.columns([2, 1])

    with chart_left:
        comp_sorted = comp.sort_values('Diferencia', ascending=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=comp_sorted['Rubro'], x=comp_sorted['Autorizado'],
            name='Autorizado', orientation='h',
            marker_color='#3b82f6', opacity=0.85,
            text=[f"${v:,.0f}" for v in comp_sorted['Autorizado']],
            textposition='auto', textfont=dict(size=11),
        ))
        fig_bar.add_trace(go.Bar(
            y=comp_sorted['Rubro'], x=comp_sorted['Ejecutado'],
            name='Ejecutado', orientation='h',
            marker_color='#10b981', opacity=0.85,
            text=[f"${v:,.0f}" for v in comp_sorted['Ejecutado']],
            textposition='auto', textfont=dict(size=11),
        ))
        fig_bar.update_layout(
            barmode='group',
            title=dict(text="Autorizado vs Ejecutado por Rubro",
                       font=dict(size=16, color="white", family="Inter")),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(255,255,255,0.7)", family="Inter"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Monto ($)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
            height=max(350, len(comp) * 55),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, font=dict(size=12)),
            margin=dict(l=10, r=20, t=60, b=30),
        )
        st.plotly_chart(fig_bar, width='stretch')

    with chart_right:
        fig_gauge = _gauge_chart(round(pct_global, 1))
        st.plotly_chart(fig_gauge, width='stretch')
        st.markdown('<p class="gauge-label">Efectividad Global de Ejecución</p>',
                    unsafe_allow_html=True)

        # Donut de estados
        estado_counts = comp['Estado'].value_counts().reset_index()
        estado_counts.columns = ['Estado', 'Cantidad']
        color_map = {
            '✅ En rango': '#10b981',
            '⚠️ Sub-ejecutado': '#f59e0b',
            '🔴 Sobre-ejecutado': '#ef4444',
            '⬜ Sin datos': '#64748b',
        }
        fig_donut = px.pie(estado_counts, names='Estado', values='Cantidad',
                           hole=0.55, color='Estado', color_discrete_map=color_map)
        fig_donut.update_traces(textposition='inside', textinfo='label+value',
                                textfont=dict(size=11, family="Inter"))
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="rgba(255,255,255,0.7)", family="Inter"),
            height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
        )
        st.plotly_chart(fig_donut, width='stretch')

    # ── Monthly Trend ───────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)

    auth_monthly = df_a.groupby(['_mes', '_mes_nombre'])[auth_valor_col].sum().reset_index()
    auth_monthly.columns = ['Mes', 'Mes_Nombre', 'Autorizado']
    real_monthly = df_r.groupby(['_mes', '_mes_nombre'])[real_valor_col].sum().reset_index()
    real_monthly.columns = ['Mes', 'Mes_Nombre', 'Ejecutado']

    monthly = auth_monthly.merge(real_monthly, on=['Mes', 'Mes_Nombre'], how='outer').fillna(0)
    monthly = monthly.sort_values('Mes')
    monthly['Diferencia'] = monthly['Ejecutado'] - monthly['Autorizado']

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=monthly['Mes_Nombre'], y=monthly['Autorizado'],
        mode='lines+markers', name='Autorizado',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=9, symbol='circle'),
        fill='tozeroy', fillcolor='rgba(59,130,246,0.08)',
    ))
    fig_trend.add_trace(go.Scatter(
        x=monthly['Mes_Nombre'], y=monthly['Ejecutado'],
        mode='lines+markers', name='Ejecutado',
        line=dict(color='#10b981', width=3),
        marker=dict(size=9, symbol='diamond'),
        fill='tozeroy', fillcolor='rgba(16,185,129,0.08)',
    ))
    diff_colors = ['rgba(239,68,68,0.5)' if d > 0 else 'rgba(16,185,129,0.5)'
                   for d in monthly['Diferencia']]
    fig_trend.add_trace(go.Bar(
        x=monthly['Mes_Nombre'], y=monthly['Diferencia'],
        name='Diferencia', marker_color=diff_colors, opacity=0.5, yaxis='y2',
    ))
    fig_trend.update_layout(
        title=dict(text="📅 Tendencia Mensual: Autorizado vs Ejecutado",
                   font=dict(size=16, color="white", family="Inter")),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="rgba(255,255,255,0.7)", family="Inter"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Monto ($)"),
        yaxis2=dict(overlaying='y', side='right', showgrid=False,
                    title="Diferencia ($)", gridcolor="rgba(255,255,255,0.03)"),
        hovermode='x unified', height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=12)),
        margin=dict(l=10, r=10, t=60, b=30),
    )
    st.plotly_chart(fig_trend, width='stretch')

    # ── Detail Table ────────────────────────────────────────────────
    with st.expander(f"📊 Tabla detallada — Efectividad {section_name}", expanded=False):
        display_comp = comp.copy()
        display_comp['Autorizado'] = display_comp['Autorizado'].apply(lambda x: f"${x:,.0f}")
        display_comp['Ejecutado'] = display_comp['Ejecutado'].apply(lambda x: f"${x:,.0f}")
        display_comp['Diferencia'] = display_comp['Diferencia'].apply(lambda x: f"${x:,.0f}")
        display_comp['% Ejecución'] = display_comp['% Ejecución'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_comp, width='stretch', hide_index=True)
