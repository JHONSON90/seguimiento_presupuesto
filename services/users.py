import streamlit as st
from streamlit_gsheets import GSheetsConnection

@st.cache_data(ttl=60)
def get_users_dict():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Users_data", ttl=0)
        
        # Normalizar los nombres de columnas
        cols = [str(c).lower().strip() for c in df.columns]
        df.columns = cols
        
        # Detectar la columna de correo (email o correo o la primera)
        email_col = 'email' if 'email' in cols else ('correo' if 'correo' in cols else cols[0])
        rol_col = 'rol' if 'rol' in cols else ('role' if 'role' in cols else (cols[1] if len(cols) > 1 else None))
        
        df = df.dropna(subset=[email_col])
        
        usuarios = {}
        for _, row in df.iterrows():
            email_val = str(row[email_col]).strip().lower()
            rol_val = str(row[rol_col]).strip().lower() if rol_col else "user"
            if email_val and email_val != 'nan':
                usuarios[email_val] = rol_val
                
        return usuarios
    except Exception as e:
        st.error(f"Error accediendo a la tabla Users: {e}")
        return {}

def get_email():
    if st.user.is_logged_in:
        return st.user.email
    return None

def get_role(email=None):
    if email is None:
        email = get_email()
    
    if not email:
        return None
        
    usuarios = get_users_dict()
    return usuarios.get(email.lower())

def is_allowed(email=None):
    if email is None:
        email = get_email()
        
    if not email:
        return False
        
    usuarios = get_users_dict()
    return email.lower() in usuarios

def require_role(role):
    user_role = get_role()
    if user_role != role:
        st.error("No tienes permisos para acceder a esta sección")
        st.stop()