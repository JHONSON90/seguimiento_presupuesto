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


st.sidebar.link_button("Analizar datos", url='https://costosproin.streamlit.app/', type='primary')

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
    title = 'Presupuesto',
    icon = '🧮'
)

admin = st.Page(
    'views/admin.py',
    title = 'Admin',
    icon = "⚙️"
)

paginas = [presupuesto_total, activos_fijos, consumos_bodega, gastos]

if role == 'admin':
    paginas.append(admin)

pg = st.navigation(paginas)

if "current_page" not in st.session_state:
    st.session_state.current_page = None

if st.session_state.current_page != pg.title:
    log_event(email, name, "navigate", pg.title)
    st.session_state.current_page = pg.title

pg.run()

