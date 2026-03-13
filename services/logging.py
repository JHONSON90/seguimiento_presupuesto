import streamlit as st
import pandas as pd
import datetime
import time
from streamlit_gsheets import GSheetsConnection

def log_event(email, name, event, page):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="logs", ttl=0)
        
        timestamp = datetime.datetime.now().isoformat()
        
        if len(df.columns) >= 5:
            columns = df.columns[:5]
        else:
            columns = ["Email", "Usuario", "Evento", "Pagina", "Fecha"]
            
        new_row = pd.DataFrame([[email, name, event, page, timestamp]], columns=columns)
        
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="logs", data=updated_df)
    except Exception as e:
        placeholder = st.empty()
        placeholder.error(f"Error registrando el log de acceso: {e}")
        time.sleep(2)
        placeholder.empty()

def log_login():
    email = st.user.email
    name = st.user.name
    log_event(email, name, "login", "auth")

# def login_page():

#     col1, col2, col3 = st.columns([1,2,1])

#     with col2:
#         st.markdown("## Plataforma de Análisis del presupuesto")
#         st.markdown("Acceso privado")

#         st.image("assets/logo.png", width=150)

#         st.button(
#             "Continuar con Google",
#             width='stretch',
#             on_click=st.login
#         )


# if not st.user.is_logged_in:
#     login_page()
#     st.stop()