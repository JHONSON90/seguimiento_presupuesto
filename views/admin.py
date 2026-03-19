import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.markdown("# Gestión de la aplicación")
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


with st.expander("📎 Agregar movimiento cuentas general a la app"):
    st.info("Recuerda que el archivo debe estar como lo arroja Siigo")
    
    with st.form("form_libro_diario"):
        fecha_libro = st.date_input('🗓️ Fecha del libro diario')
        ruta = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
        
        btn_guardar = st.form_submit_button("💾 Guardar en base de datos", type="primary")
        
        if btn_guardar:
            if ruta is not None:
                with st.spinner("Procesando y guardando datos..."):
                    try:
                        df_libro = pd.read_excel(ruta, skiprows=6)
                        df_libro.columns = df_libro.columns.str.strip()
                        df_libro['CUENTA'] = df_libro['CUENTA'].str.replace(' ', '')
                        #df['CUENTA'] = pd.to_numeric(df['CUENTA'], errors='coerce')
                        df_libro['DEBITOS'] = pd.to_numeric(df_libro['DEBITOS'], errors='coerce').fillna(0)
                        df_libro['CREDITOS'] = pd.to_numeric(df_libro['CREDITOS'], errors='coerce').fillna(0)
                        df_libro['SALDO MOV.'] = df_libro['DEBITOS'] - df_libro['CREDITOS']

                        agrupado = df_libro.groupby('CUENTA')['SALDO MOV.'].sum().reset_index()
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
                        #TODO: HACER FUNCION PARA LEER EL ARCHIVO CONTROL GG Y CAMBIAR EL ESTADO DE LOS REGISTROS REALIZADOS EN EL MES QUE SE ESTA SUBIENDO EL INFORME PARA QUE PASE A SER REAL Y NO PROYECTADO Y QUE ESTOS NO SE MIREN REFLEJADOS EN LOS INFORMES
                        
                        df_libros = pd.concat([df_libros, agrupado], ignore_index=True)
                        conn.update(worksheet="Gastos_Grales_reales", data=df_libros)
                        
                        st.success("✅ Libro diario agregado exitosamente!!")
                        st.cache_data.clear() # Limpiar caché por si otras vistas usan los datos
                        
                    except Exception as e:
                        st.error(f"Error al procesar el archivo: {e}")
            else:
                st.warning("⚠️ Por favor, selecciona un archivo Excel primero antes de guardar.")

with st.expander("☁️ Agregar Compras a la app"):
    st.info("Recuerda que el archivo debe estar sin subtotales y contener Hoja1 (2)")
    
    with st.form("form_compras"):
        ruta = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
        btn_guardar = st.form_submit_button("💾 Guardar en base de datos", type="primary")
        
        if btn_guardar:
            if ruta is not None:
                with st.spinner("Procesando y guardando datos..."):
                    try:
                        df_compras = pd.read_excel(ruta, skiprows=6, sheet_name="Hoja1 (2)")
                        df_compras.columns = df_compras.columns.str.strip()
                        #eliminar filas en cuenta no comience con 14
                        df_compras = df_compras[df_compras['CUENTA'].str.startswith('14')]
                        #cambiar tipo de datos para poder calcular el saldo
                        df_compras['DEBITOS'] = pd.to_numeric(df_compras['DEBITOS']).fillna(0)
                        df_compras['CREDITOS'] = df_compras['CREDITOS'].str.replace(' ', '')
                        df_compras['CREDITOS'] = pd.to_numeric(df_compras['CREDITOS']).fillna(0)
                        df_compras['DEBITOS'] = df_compras['DEBITOS'].fillna(0)
                        df_compras['SALDO MOV.'] = df_compras['DEBITOS'] - df_compras ['CREDITOS']
                        df_compras['linea_grupo'] = df_compras['INVENTARIO-CRUCE-CHEQUE'].str.extract(r'(\d{7})')
                        #separar por linea y grupo entonces linea 3 primeros digitos y restante seria grupo
                        lineas_grupos = df_compras['linea_grupo'].value_counts().reset_index()
                        lineas_grupos['linea'] = lineas_grupos['linea_grupo'].str[:3]
                        lineas_grupos['linea'] = pd.to_numeric(lineas_grupos['linea'])
                        lineas_grupos['grupo'] = lineas_grupos['linea_grupo'].str[3:]
                        lineas_grupos['grupo'] = pd.to_numeric(lineas_grupos['grupo'])
                        #unir linea y grupo con un _ en medio
                        lineas_grupos['para_cruce'] = lineas_grupos['linea'].astype(str) + '_' + lineas_grupos['grupo'].astype(str)

                        #crear rubros pptales
                        DATOS = {'para_cruce': ['1_1','2_1','3_1','4_1','4_2','4_3','5_1','5_2','5_3','6_1','6_2','7_1','7_2','8_1','8_2','9_1','9_2','10_1','10_2','11_1','11_2','12_1','12_2','13_1','13_2','14_1','14_2','300_5','300_10','300_15','301_5','302_5','303_5','304_5','305_5','305_10','306_5','307_5','308_5','309_5','310_5','311_5','312_5','313_5','314_5','315_5','316_5','316_6','317_5'],
                        "RUBRO" :['60104 - Servicio Farmaceutico','60104 - Servicio Farmaceutico','60104 - Servicio Farmaceutico','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60104 - Servicio Farmaceutico','60104 - Servicio Farmaceutico','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60104 - Servicio Farmaceutico','60103 - Osteosintesis','60104 - Servicio Farmaceutico','60101 - Laboratorio Clinico','60104 - Servicio Farmaceutico','60104 - Servicio Farmaceutico','60106 - Suministros','60106 - Suministros','60106 - Suministros','60106 - Suministros','60106 - Suministros','60106 - Suministros','60102 - Mantenimiento','60106 - Suministros','60102 - Mantenimiento','60106 - Suministros','60106 - Suministros','60106 - Suministros','60105 - Sistemas','60106 - Suministros','60106 - Suministros','60106 - Suministros']
                        }
                        RUBROS = pd.DataFrame(DATOS)
                        lineas_rubros = pd.merge(lineas_grupos, RUBROS, on='para_cruce', how='left')
                        lineas_rubros = lineas_rubros.drop(columns=['count', 'linea', 'grupo'])
                        para_compras = pd.merge(df_compras, lineas_rubros, on='linea_grupo', how='left')
                        para_compras = para_compras[['FECHA', 'RUBRO', 'SALDO MOV.']]
                        para_compras.columns = ['FECHA', 'RUBRO', 'Valor']
                        para_compras = para_compras.groupby(['FECHA', 'RUBRO'], as_index=False).agg({'Valor': 'sum'}).reset_index()
                        para_compras['FECHA'] = pd.to_datetime(para_compras['FECHA']).dt.strftime('%Y-%m-%d')

                        #Leer la base de datos SOLO al momento de guardar para ahorrar peticiones
                        compras_reales = conn.read(worksheet="Control Compras", ttl=0)
                        #TODO: HACER FUNCION PARA LEER EL ARCHIVO CONTROL GG Y CAMBIAR EL ESTADO DE LOS REGISTROS REALIZADOS EN EL MES QUE SE ESTA SUBIENDO EL INFORME PARA QUE PASE A SER REAL Y NO PROYECTADO Y QUE ESTOS NO SE MIREN REFLEJADOS EN LOS INFORMES
                        compras_reales['FECHA'] = pd.to_datetime(compras_reales['FECHA']).dt.strftime('%Y-%m-%d')
                        compras_reales = pd.concat([compras_reales, para_compras], ignore_index=True)
                        #quitar duplicados para evitar que se repitan los registros
                        compras_reales = compras_reales.drop_duplicates(subset=['FECHA', 'RUBRO', 'Valor'])
                        conn.update(worksheet="Control Compras", data=compras_reales) #169 filas
                        
                        st.toast("✅ Libro diario agregado exitosamente!!")
                        st.cache_data.clear() # Limpiar caché por si otras vistas usan los datos
                        
                    except Exception as e:
                        st.error(f"Error al procesar el archivo: {e}")
            else:
                st.warning("⚠️ Por favor, selecciona un archivo Excel primero antes de guardar.")