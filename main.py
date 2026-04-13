import streamlit as st
from auth_ppto import require_login
from services.users import get_role
from services.logging import log_event



st.set_page_config(
    page_title="Seguimiento de Presupuesto",
    page_icon="👋",
    layout="wide"
)

# st.markdown(
#     """
#     <style>
#         /* Ocultar header principal barra superior de Streamlit */
#         header {visibility: hidden;}
#     </style>
#     """,
#     unsafe_allow_html=True
# )

require_login()

email = st.user.email
name = st.user.name

role = get_role()


# ── BOTÓN PREMIUM — Análisis Profundo ──────────────────────────────────────────
st.sidebar.markdown(f"""
<style>
.sidebar-btn-container {{
    display: flex;
    padding: 5px 0 15px 0;
}}
.sidebar-btn {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    width: 100%;
    padding: 14px 20px;
    border-radius: 12px;
    background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
    color: white !important;
    text-decoration: none !important;
    font-weight: 600;
    font-family: 'Source Sans Pro', sans-serif;
    font-size: 16px;
    border: none;
    box-shadow: 0 4px 12px rgba(26, 115, 232, 0.3);
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    cursor: pointer;
    text-align: center;
}}
.sidebar-btn:hover {{
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 8px 25px rgba(26, 115, 232, 0.45);
    background: linear-gradient(135deg, #1d80ff 0%, #0e52b9 100%);
    color: #ffffff !important;
}}
.sidebar-btn:active {{
    transform: scale(0.96);
    box-shadow: 0 2px 8px rgba(26, 115, 232, 0.3);
}}
.sidebar-btn svg {{
    transition: transform 0.4s ease;
}}
.sidebar-btn:hover svg {{
    transform: rotate(15deg) scale(1.1);
}}
</style>
<div class="sidebar-btn-container">
    <a href="https://costosproin.streamlit.app/" target="_blank" class="sidebar-btn">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
        </svg>
        Análisis Profundo
    </a>
</div>
""", unsafe_allow_html=True)
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.write(f"Bienvenido {name}")

if st.sidebar.button("Cerrar Sesión"):
    st.logout()



#Paginas

activos_fijos = st.Page(
    'views/activos_fijos.py',
    title = 'Activos Fijos',
    icon = '💻'
)

consumos_bodega = st.Page(
    'views/consumos.py',
    title = 'Consumos Bodega',
    icon = '📦'
)

gastos = st.Page(
    'views/gastos.py',
    title = 'Gastos',
    icon = '💸'
)

presupuesto_total = st.Page(
    'views/ppto_total.py',
    title = 'Gastos con Informe Consumos',
    icon = '🧮'
)

ingresos_total = st.Page(
    'views/ingresos.py',
    title = 'Ingresos',
    icon = '💰'
)

admin = st.Page(
    'views/admin.py',
    title = 'Admin',
    icon = "⚙️"
)

rentabilidad = st.Page(
    'views/rentabilidad.py',
    title = 'Rentabilidad',
    icon = '📈'
)

paginas = [ingresos_total,  gastos,presupuesto_total, rentabilidad,  consumos_bodega, activos_fijos,]

if role == 'admin':
    paginas.append(admin)

pg = st.navigation(paginas)

if "current_page" not in st.session_state:
    st.session_state.current_page = None

if st.session_state.current_page != pg.title:
    log_event(email, name, "navigate", pg.title)
    st.session_state.current_page = pg.title

pg.run()

