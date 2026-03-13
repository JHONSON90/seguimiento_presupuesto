import streamlit as st
from services.users import is_allowed
from services.logging import log_login


def login_screen():
    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.image("assets/logo.png", width=90)
        st.title("Plataforma de análisis del presupuesto 2026")
        st.write("Acceso seguro")
        st.button(
            "Continuar con Google",
            width='stretch',
            on_click=st.login
        )


def require_login():

    if not st.user.is_logged_in:
        login_screen()
        st.stop()
    email = st.user.email

    if not is_allowed(email):
        import time
        
        warning_placeholder = st.empty()
        for i in range(5, 0, -1):
            warning_placeholder.warning(f"Usuario {email} no autorizado. Redirigiendo al login en {i} segundos...")
            time.sleep(1)
            
        st.logout()

    if "login_logged" not in st.session_state:

        log_login()

        st.session_state.login_logged = True

# if not is_allowed():
#     login_page()
#     st.stop()

# def require_login():
#     if not st.user.is_logged_in:
#         login_screen()
#         st.stop()
#     email = st.user.email
#     name = st.user.name

#     if not is_allowed(email):
#         st.error("No tienes permisos para acceder a esta sección")
#         st.stop()
    
#     if 'login_logged' not in st.session_state:
#         log_login(email, name)
#         st.session_state.login_logged = True