"""
services/pdf_report.py
Genera un informe PDF trimestral de Presupuesto vs Ejecutado.
Dependencias: reportlab, matplotlib, pandas
"""
import io
import warnings
import traceback
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("Agg")          # backend sin pantalla
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, PageBreak,
)

# ── Silenciar advertencias menores ────────────────────────────────────────────
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ── Paleta corporativa ────────────────────────────────────────────────────────
AZUL_OSC  = colors.HexColor("#0d47a1")
AZUL_MED  = colors.HexColor("#1a73e8")
AZUL_CLR  = colors.HexColor("#e8f0fe")
ROJO      = colors.HexColor("#c62828")
ROJO_CLR  = colors.HexColor("#ffebee")
VERDE     = colors.HexColor("#1b5e20")
VERDE_CLR = colors.HexColor("#e8f5e9")
GRIS      = colors.HexColor("#37474f")
GRIS_FIL  = colors.HexColor("#f5f5f5")
NARANJA   = colors.HexColor("#e65100")
NAR_CLR   = colors.HexColor("#fff3e0")

TRIMESTRES = {
    "Q1 — Enero a Marzo":       [1, 2, 3],
    "Q2 — Abril a Junio":       [4, 5, 6],
    "Q3 — Julio a Septiembre":  [7, 8, 9],
    "Q4 — Octubre a Diciembre": [10, 11, 12],
}
MESES_ES = {
    1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
    7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _fmt(v): return f"${v:,.0f}"
def _pct(v): return f"{v:.1f}%"

def _style_base(hdr_color=None):
    hc = hdr_color or AZUL_OSC
    return TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), hc),
        ("TEXTCOLOR",     (0,0),(-1,0), colors.white),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8),
        ("ALIGN",         (0,0),(-1,0), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,0), 5),
        ("BOTTOMPADDING", (0,0),(-1,0), 5),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 7.5),
        ("ROWBACKGROUND", (0,1),(-1,-1), [colors.white, GRIS_FIL]),
        ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#bdbdbd")),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,1),(-1,-1), 3),
        ("BOTTOMPADDING", (0,1),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
    ])

def _mpl_to_image(fig, w_cm=24, h_cm=8):
    """Convierte figura matplotlib a Image de reportlab."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=w_cm*cm, height=h_cm*cm)

def _fmt_miles(x, _):
    if abs(x) >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    elif abs(x) >= 1_000:
        return f"${x/1_000:.0f}K"
    return f"${x:.0f}"

# ── Cabecera / pie de página ──────────────────────────────────────────────────
def _on_page(canvas, doc, trimestre_label, periodo):
    canvas.saveState()
    w, h = doc.pagesize
    canvas.setFillColor(AZUL_OSC)
    canvas.rect(0, h-2.2*cm, w, 2.2*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(1.5*cm, h-1.4*cm, "INFORME TRIMESTRAL — PRESUPUESTO VS EJECUTADO 2026")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w-1.5*cm, h-1.4*cm, f"{trimestre_label}  |  {periodo}")
    canvas.setFillColor(GRIS)
    canvas.rect(0, 0, w, 1*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(1.5*cm, 0.35*cm, "Información confidencial — uso interno")
    canvas.drawRightString(w-1.5*cm, 0.35*cm, f"Página {doc.page}")
    canvas.restoreState()


# ── Función principal ─────────────────────────────────────────────────────────
def generar_pdf(df_final: pd.DataFrame, trimestre_label: str) -> bytes:
    meses_trim = TRIMESTRES.get(trimestre_label, [])
    df = df_final[df_final["Mes"].isin(meses_trim)].copy()
    periodo = (f"{MESES_ES.get(meses_trim[0],'')} – {MESES_ES.get(meses_trim[-1],'')} 2026"
               if meses_trim else "Período no definido")
    generado_en = datetime.now().strftime("%d/%m/%Y %H:%M")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=3*cm, bottomMargin=1.8*cm)

    styles = getSampleStyleSheet()
    S_TIT = ParagraphStyle("tit", parent=styles["Normal"], fontSize=13,
                            textColor=AZUL_OSC, fontName="Helvetica-Bold", spaceAfter=4)
    S_SUB = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10,
                            textColor=GRIS, fontName="Helvetica-Bold", spaceAfter=2)
    S_BOD = ParagraphStyle("bod", parent=styles["Normal"], fontSize=8, spaceAfter=2)
    S_OK  = ParagraphStyle("ok",  parent=styles["Normal"], fontSize=8,
                            textColor=VERDE, fontName="Helvetica-Bold")
    S_ERR = ParagraphStyle("err", parent=styles["Normal"], fontSize=8,
                            textColor=ROJO, fontName="Helvetica-Bold")

    story = []
    def sp(h=0.3): story.append(Spacer(1, h*cm))
    def hr(c=AZUL_MED, t=0.8): story.append(HRFlowable(width="100%", thickness=t, color=c, spaceAfter=4))

    # ── RESUMEN EJECUTIVO ─────────────────────────────────────────────────────
    story.append(Paragraph("Informe Trimestral de Ejecución Presupuestal", S_TIT))
    story.append(Paragraph(f"{trimestre_label}  ·  {periodo}  ·  Generado: {generado_en}", S_BOD))
    hr(); sp(0.2)

    tot_p  = df["Presupuesto"].sum()
    tot_e  = df["Ejecutado"].sum()
    dif    = tot_p - tot_e
    pct_e  = (tot_e/tot_p*100) if tot_p > 0 else 0

    df_cc_g = (df.groupby("CENTRO DE COSTOS")
                 .agg(Presupuesto=("Presupuesto","sum"), Ejecutado=("Ejecutado","sum"))
                 .reset_index())
    df_cc_g["Diferencia"] = df_cc_g["Presupuesto"] - df_cc_g["Ejecutado"]
    df_cc_g["Pct"] = (df_cc_g["Ejecutado"] / df_cc_g["Presupuesto"].replace(0,None) * 100
                      ).infer_objects(copy=False).fillna(0)

    df_rub_g = (df.groupby(["CENTRO DE COSTOS","Rubro Presupuestal"])
                  .agg(Presupuesto=("Presupuesto","sum"), Ejecutado=("Ejecutado","sum"))
                  .reset_index())
    df_rub_g["Diferencia"] = df_rub_g["Presupuesto"] - df_rub_g["Ejecutado"]

    n_cc_exc  = (df_cc_g["Diferencia"]  < 0).sum()
    n_rub_exc = (df_rub_g["Diferencia"] < 0).sum()

    met_data = [
        ["MÉTRICA", "VALOR", "DETALLE"],
        ["💰 Presupuesto Trimestre",  _fmt(tot_p),  "Monto aprobado"],
        ["💳 Ejecutado Real",          _fmt(tot_e),  f"% ejecución: {_pct(pct_e)}"],
        ["📉 Saldo Disponible",        _fmt(dif),
         "Sin exceso ✅" if dif >= 0 else "⚠️ Sobre-ejecución"],
        ["🏢 Áreas con exceso",        str(n_cc_exc),  "Centros de costo sobre presupuesto"],
        ["🏷️ Rubros con exceso",      str(n_rub_exc), "Combinaciones CC/Rubro sobre presupuesto"],
    ]
    t_met = Table(met_data, colWidths=[6*cm, 4.5*cm, 10*cm])
    st_met = _style_base(AZUL_OSC)
    if dif < 0:
        st_met.add("BACKGROUND", (0,3),(-1,3), ROJO_CLR)
        st_met.add("TEXTCOLOR",  (1,3),(1,3),  ROJO)
    else:
        st_met.add("BACKGROUND", (0,3),(-1,3), VERDE_CLR)
    t_met.setStyle(st_met)
    story.append(t_met); sp()

    # ── SECCIÓN 1: TENDENCIA MENSUAL ─────────────────────────────────────────
    story.append(Paragraph("1. Tendencia Mensual — Presupuesto vs Ejecutado", S_SUB))
    hr(AZUL_MED, 0.5); sp(0.2)

    df_men = (df.groupby(["Mes","Mes_Nom"])
                .agg(Presupuesto=("Presupuesto","sum"), Ejecutado=("Ejecutado","sum"))
                .reset_index().sort_values("Mes"))

    if not df_men.empty:
        try:
            fig, ax = plt.subplots(figsize=(12, 4))
            x = np.arange(len(df_men))
            w = 0.35
            ax.bar(x-w/2, df_men["Presupuesto"], w, label="Presupuesto",
                   color="#1a73e8", alpha=0.9)
            ax.bar(x+w/2, df_men["Ejecutado"],   w, label="Ejecutado",
                   color="#e74c3c", alpha=0.9)
            ax.set_xticks(x); ax.set_xticklabels(df_men["Mes_Nom"], fontsize=9)
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_miles))
            ax.tick_params(axis="y", labelsize=8)
            ax.legend(fontsize=9); ax.set_facecolor("white")
            ax.grid(axis="y", alpha=0.3, linestyle="--")
            ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
            story.append(_mpl_to_image(fig, 25, 8))
        except Exception:
            pass
        sp(0.2)

        men_rows = [["Mes","Presupuesto","Ejecutado","Diferencia","% Ejec."]]
        for _, r in df_men.iterrows():
            d = r["Presupuesto"]-r["Ejecutado"]
            p = (r["Ejecutado"]/r["Presupuesto"]*100) if r["Presupuesto"]>0 else 0
            men_rows.append([r["Mes_Nom"],_fmt(r["Presupuesto"]),_fmt(r["Ejecutado"]),_fmt(d),_pct(p)])
        t_men = Table(men_rows, colWidths=[4*cm,4.5*cm,4.5*cm,4.5*cm,3.5*cm])
        st_men = _style_base()
        for i, r in enumerate(df_men.itertuples(), 1):
            if r.Presupuesto - r.Ejecutado < 0:
                st_men.add("BACKGROUND",(0,i),(-1,i), ROJO_CLR)
                st_men.add("TEXTCOLOR", (3,i),(3,i),  ROJO)
        t_men.setStyle(st_men)
        story.append(t_men)
    sp()

    # ── SECCIÓN 2: ÁREAS SOBRE PRESUPUESTO ────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("2. Áreas (Centros de Costo) que Superaron el Presupuesto", S_SUB))
    hr(ROJO, 0.5); sp(0.2)

    df_cc_exc = df_cc_g[df_cc_g["Diferencia"] < 0].copy()
    df_cc_exc["Sobre"] = df_cc_exc["Ejecutado"] - df_cc_exc["Presupuesto"]
    df_cc_exc = df_cc_exc.sort_values("Sobre", ascending=False)

    if df_cc_exc.empty:
        story.append(Paragraph("✅ Ningún Centro de Costo superó su presupuesto.", S_OK))
    else:
        story.append(Paragraph(f"⚠️ {len(df_cc_exc)} área(s) superaron el presupuesto:", S_ERR))
        sp(0.2)
        try:
            fig2, ax2 = plt.subplots(figsize=(12, 4))
            df_plot = df_cc_exc.sort_values("Sobre")
            bars = ax2.barh(df_plot["CENTRO DE COSTOS"], df_plot["Sobre"],
                            color="#c62828", alpha=0.85)
            ax2.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_miles))
            ax2.tick_params(labelsize=8)
            ax2.set_xlabel("Monto sobre presupuesto (COP)", fontsize=8)
            ax2.set_facecolor("white")
            ax2.grid(axis="x", alpha=0.3, linestyle="--")
            ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)
            for bar, pct in zip(bars, df_plot["Pct"]):
                ax2.text(bar.get_width()*1.01, bar.get_y()+bar.get_height()/2,
                         f"{pct:.1f}%", va="center", fontsize=8, color="#c62828")
            story.append(_mpl_to_image(fig2, 25, 9))
        except Exception:
            pass
        sp(0.2)

        cc_rows = [["Centro de Costo","Presupuesto","Ejecutado","Sobre-ejecución","% Ejec."]]
        for _, r in df_cc_exc.iterrows():
            cc_rows.append([r["CENTRO DE COSTOS"],_fmt(r["Presupuesto"]),
                            _fmt(r["Ejecutado"]),_fmt(r["Sobre"]),_pct(r["Pct"])])
        t_cc = Table(cc_rows, colWidths=[7*cm,4.5*cm,4.5*cm,4.5*cm,3.5*cm])
        st_cc = _style_base(ROJO)
        for i in range(1,len(cc_rows)):
            st_cc.add("BACKGROUND",(0,i),(-1,i), ROJO_CLR)
            st_cc.add("TEXTCOLOR", (3,i),(3,i),  ROJO)
        t_cc.setStyle(st_cc); story.append(t_cc)
    sp()

    # Resumen completo CC
    story.append(Paragraph("Resumen completo por Centro de Costo", S_SUB)); sp(0.1)
    all_rows = [["Centro de Costo","Presupuesto","Ejecutado","Diferencia","% Ejec."]]
    for _, r in df_cc_g.sort_values("Ejecutado", ascending=False).iterrows():
        all_rows.append([r["CENTRO DE COSTOS"],_fmt(r["Presupuesto"]),
                         _fmt(r["Ejecutado"]),_fmt(r["Diferencia"]),_pct(r["Pct"])])
    t_all = Table(all_rows, colWidths=[7*cm,4.5*cm,4.5*cm,4.5*cm,3.5*cm])
    st_all = _style_base(GRIS)
    for i,r in enumerate(df_cc_g.sort_values("Ejecutado",ascending=False).itertuples(),1):
        if r.Diferencia < 0:
            st_all.add("BACKGROUND",(0,i),(-1,i), ROJO_CLR)
            st_all.add("TEXTCOLOR", (3,i),(3,i),  ROJO)
    t_all.setStyle(st_all); story.append(t_all); sp()

    # ── SECCIÓN 3: RUBROS SOBRE PRESUPUESTO ───────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("3. Rubros que Superaron el Presupuesto por Centro de Costo", S_SUB))
    hr(NARANJA, 0.5); sp(0.2)

    df_rub_g["Sobre"] = df_rub_g["Ejecutado"] - df_rub_g["Presupuesto"]
    df_rub_g["Pct"]   = (df_rub_g["Sobre"] / df_rub_g["Presupuesto"].replace(0,None) * 100
                         ).infer_objects(copy=False).fillna(0)
    df_rub_exc = df_rub_g[df_rub_g["Diferencia"] < 0].sort_values("Sobre", ascending=False)

    if df_rub_exc.empty:
        story.append(Paragraph("✅ Ningún rubro superó su presupuesto.", S_OK))
    else:
        story.append(Paragraph(f"⚠️ {len(df_rub_exc)} combinación(es) CC/Rubro sobre presupuesto:", S_ERR))
        sp(0.2)

        # Heatmap matplotlib
        try:
            df_heat = df_rub_exc.pivot_table(index="CENTRO DE COSTOS",
                                              columns="Rubro Presupuestal",
                                              values="Pct", aggfunc="sum", fill_value=0)
            fig3, ax3 = plt.subplots(figsize=(12, max(3, len(df_heat)*0.7+1.5)))
            im = ax3.imshow(df_heat.values, cmap="YlOrRd", aspect="auto")
            ax3.set_xticks(range(len(df_heat.columns)))
            ax3.set_xticklabels(df_heat.columns, rotation=35, ha="right", fontsize=7)
            ax3.set_yticks(range(len(df_heat.index)))
            ax3.set_yticklabels(df_heat.index, fontsize=7)
            for i in range(len(df_heat.index)):
                for j in range(len(df_heat.columns)):
                    v = df_heat.values[i,j]
                    if v > 0:
                        ax3.text(j, i, f"{v:.1f}%", ha="center", va="center",
                                 fontsize=7, color="black" if v < 80 else "white")
            plt.colorbar(im, ax=ax3, label="% Exceso")
            story.append(_mpl_to_image(fig3, 25, max(5, len(df_heat)*0.8+2)))
        except Exception:
            pass
        sp(0.2)

        rub_rows = [["Centro de Costo","Rubro Presupuestal","Presupuesto","Ejecutado","Sobre-ejec.","% Exceso"]]
        for _, r in df_rub_exc.iterrows():
            rub_rows.append([r["CENTRO DE COSTOS"],r["Rubro Presupuestal"],
                             _fmt(r["Presupuesto"]),_fmt(r["Ejecutado"]),
                             _fmt(r["Sobre"]),_pct(r["Pct"])])
        t_rub = Table(rub_rows, colWidths=[6*cm,5.5*cm,3.8*cm,3.8*cm,3.8*cm,3*cm])
        st_rub = _style_base(NARANJA)
        for i in range(1,len(rub_rows)):
            st_rub.add("BACKGROUND",(0,i),(-1,i), NAR_CLR)
            st_rub.add("TEXTCOLOR", (4,i),(4,i),  NARANJA)
        t_rub.setStyle(st_rub); story.append(t_rub)
    sp()

    # ── SECCIÓN 4: DETALLE COMPLETO ───────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("4. Detalle Completo por CC, Rubro y Mes", S_SUB))
    hr(GRIS, 0.5); sp(0.2)

    df_det = (df.groupby(["CENTRO DE COSTOS","Rubro Presupuestal","Mes","Mes_Nom"])
                .agg(Presupuesto=("Presupuesto","sum"), Ejecutado=("Ejecutado","sum"))
                .reset_index().sort_values(["CENTRO DE COSTOS","Rubro Presupuestal","Mes"]))
    df_det["Diferencia"] = df_det["Presupuesto"] - df_det["Ejecutado"]
    df_det["Pct"] = (df_det["Ejecutado"] / df_det["Presupuesto"].replace(0,None) * 100
                     ).infer_objects(copy=False).fillna(0)

    det_rows = [["Centro de Costo","Rubro Presupuestal","Mes","Presupuesto","Ejecutado","Diferencia","% Ejec."]]
    for _, r in df_det.iterrows():
        det_rows.append([r["CENTRO DE COSTOS"],r["Rubro Presupuestal"],r["Mes_Nom"],
                         _fmt(r["Presupuesto"]),_fmt(r["Ejecutado"]),
                         _fmt(r["Diferencia"]),_pct(r["Pct"])])
    t_det = Table(det_rows, colWidths=[5.5*cm,5*cm,3*cm,3.8*cm,3.8*cm,3.8*cm,3*cm], repeatRows=1)
    st_det = _style_base(GRIS)
    for i,r in enumerate(df_det.itertuples(),1):
        if r.Diferencia < 0:
            st_det.add("BACKGROUND",(0,i),(-1,i), ROJO_CLR)
            st_det.add("TEXTCOLOR", (5,i),(5,i),  ROJO)
    t_det.setStyle(st_det); story.append(t_det)

    # ── BUILD ─────────────────────────────────────────────────────────────────
    fn = lambda c,d: _on_page(c, d, trimestre_label, periodo)
    doc.build(story, onFirstPage=fn, onLaterPages=fn)
    return buf.getvalue()
