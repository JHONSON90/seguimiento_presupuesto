import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.markdown("# Gestión de Usuarios")
st.markdown("Administra los accesos, roles, adicion de informacion en la app.")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_users = conn.read(worksheet="Users_data", ttl=60)
    
    # Asegurar que existan las columnas base si la hoja está vacía
    if df_users.empty and len(df_users.columns) < 2:
        df_users = pd.DataFrame(columns=["Email", "Rol"])
        
    with st.expander("👥 Usuarios Autorizados"):
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


with st.expander("➕ Agregar libro diario a la app"):
    st.info("Recuerda que el archivo debe estar como lo arroja Siigo")
    
    with st.form("form_libro_diario"):
        fecha_libro = st.date_input('🗓️ Fecha del libro diario')
        ruta = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
        
        btn_guardar = st.form_submit_button("💾 Guardar en base de datos", type="primary")
        
        if btn_guardar:
            if ruta is not None:
                with st.spinner("Procesando y guardando datos..."):
                    try:
                        df = pd.read_excel(ruta, skiprows=6)
                        df.columns = df.columns.str.strip()
                        df['CUENTA'] = df['CUENTA'].str.replace(' ', '')
                        #df['CUENTA'] = pd.to_numeric(df['CUENTA'], errors='coerce')
                        df['DEBITOS'] = pd.to_numeric(df['DEBITOS'], errors='coerce').fillna(0)
                        df['CREDITOS'] = pd.to_numeric(df['CREDITOS'], errors='coerce').fillna(0)
                        df['SALDO MOV.'] = df['DEBITOS'] - df['CREDITOS']

                        agrupado = df.groupby('CUENTA')['SALDO MOV.'].sum().reset_index()
                        agrupado['CUENTA'] = agrupado['CUENTA'].astype(str)
                        agrupado['Fecha'] = fecha_libro
                        df_rubros = conn.read(worksheet="Rubros_gasto", ttl=6000)
                        df_rubros['CUENTA'] = df_rubros['CUENTA'].astype(int)
                        df_rubros['CUENTA'] = df_rubros['CUENTA'].astype(str)
                        #st.write(df_rubros)
                        agrupado = agrupado.merge(df_rubros.set_index('CUENTA'), on='CUENTA', how='left')
                        #st.write(agrupado)
                        
                        #Leer la base de datos SOLO al momento de guardar para ahorrar peticiones
                        df_libros = conn.read(worksheet="Gastos_Grales_reales", ttl=60)
                        
                        df_libros = pd.concat([df_libros, agrupado], ignore_index=True)
                        conn.update(worksheet="Gastos_Grales_reales", data=df_libros)
                        
                        st.success("✅ Libro diario agregado exitosamente!!")
                        st.cache_data.clear() # Limpiar caché por si otras vistas usan los datos
                        
                    except Exception as e:
                        st.error(f"Error al procesar el archivo: {e}")
            else:
                st.warning("⚠️ Por favor, selecciona un archivo Excel primero antes de guardar.")