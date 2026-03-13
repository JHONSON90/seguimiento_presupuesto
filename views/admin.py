import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.markdown("# Gestión de Usuarios")
st.markdown("Administra los accesos y roles de la aplicación.")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_users = conn.read(worksheet="Users_data", ttl=0)
    
    # Asegurar que existan las columnas base si la hoja está vacía
    if df_users.empty and len(df_users.columns) < 2:
        df_users = pd.DataFrame(columns=["Email", "Rol"])
        
    st.subheader("👥 Usuarios Autorizados")
    
    # Usar st.data_editor para permitir edición y eliminación directamente en la tabla
    with st.form("form_edit_users"):
        st.caption("Puedes modificar los roles, eliminar filas o añadir nuevos usuarios en la tabla inferior.")
        
        # Configurar el editor de datos
        edited_df = st.data_editor(
            df_users,
            num_rows="dynamic", # Permite añadir y eliminar filas
            width='stretch',
            column_config={
                "Correo": st.column_config.TextColumn(
                    "Correo Electrónico",
                    help="Email corporativo o cuenta de Google",
                    required=True,
                    validate="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
                ),
                "Rol": st.column_config.SelectboxColumn(
                    "Rol de Acceso",
                    help="Nivel de permisos",
                    width="small",
                    options=["admin", "user", "viewer"],
                    required=True
                )
            },
            hide_index=True 
        )
        
        submit_button = st.form_submit_button("Guardar Cambios", type="primary")
        
        if submit_button:
            # Limpiar filas vacías donde el correo no exista
            cleaned_df = edited_df.dropna(subset=["Email"])
            
            # Guardar en GSheets
            conn.update(worksheet="Users_data", data=cleaned_df)
            st.success("✅ Base de usuarios actualizada correctamente.")
            
            # Limpiar caché de la lista de usuarios en users.py 
            st.cache_data.clear()
            st.rerun()
            
except Exception as e:
    st.error(f"Error cargando la base de datos de usuarios: {e}")