import streamlit as st
import pandas as pd
import numpy as np
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


with st.expander("📎 Agregar movimiento gastos a la app"):
    st.info("Recuerda que el archivo debe ser el de movimiento general de las cuentas 5 y 6 (hasta 6130), con una sola hoja (Informe o Hoja1), quitado subtotales, y debes seleccionar la fecha preferiblemente el ultimo dia del mes a subir")
    
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
                        df_libros = conn.read(worksheet="Gastos_Grales_reales", ttl=0)
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
    st.info("Recuerda que el archivo debe ser el de movimiento general de todas las P, con una sola hoja (Informe o Hoja1), quitado subtotales")
    # Mapeo de Rubros Presupuestales (Extraído para facilitar mantenimiento)
    RUBROS_DATOS = {
        'para_cruce': [
            '1_1','2_1','3_1','4_1','4_2','4_3','5_1','5_2','5_3','6_1','6_2','7_1','7_2','8_1','8_2','9_1',
            '9_2','10_1','10_2','11_1','11_2','12_1','12_2','13_1','13_2','14_1','14_2','300_5','300_10',
            '300_15','301_5','302_5','303_5','304_5','305_5','305_10','306_5','307_5','308_5','309_5',
            '310_5','311_5','312_5','313_5','314_5','315_5','316_5','316_6','317_5'
        ],
        "RUBRO": [
            '60104 - Servicio Farmaceutico','60104 - Servicio Farmaceutico','60104 - Servicio Farmaceutico',
            '60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento',
            '60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento',
            '60104 - Servicio Farmaceutico','60104 - Servicio Farmaceutico','60102 - Mantenimiento',
            '60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento',
            '60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento',
            '60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento','60102 - Mantenimiento',
            '60102 - Mantenimiento','60104 - Servicio Farmaceutico','60103 - Osteosintesis',
            '60104 - Servicio Farmaceutico','60101 - Laboratorio Clinico','60104 - Servicio Farmaceutico',
            '60104 - Servicio Farmaceutico','60106 - Suministros','60106 - Suministros','60106 - Suministros',
            '60106 - Suministros','60106 - Suministros','60106 - Suministros','60102 - Mantenimiento',
            '60106 - Suministros','60102 - Mantenimiento','60106 - Suministros','60106 - Suministros',
            '60106 - Suministros','60105 - Sistemas','60106 - Suministros','60106 - Suministros',
            '60106 - Suministros'
        ]
    }

    with st.form("form_compras"):
        ruta = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
        btn_guardar = st.form_submit_button("💾 Guardar en base de datos", type="primary")
        
        if btn_guardar:
            if ruta is not None:
                with st.spinner("Procesando y guardando datos..."):
                    try:
                        # 1. Carga y limpieza inicial
                        df_compras = pd.read_excel(ruta, skiprows=6)
                        df_compras.columns = df_compras.columns.str.strip()
                        
                        # 2. Filtrado por cuenta (solo las que comienzan con 14)
                        if 'CUENTA' in df_compras.columns:
                            df_compras = df_compras[df_compras['CUENTA'].astype(str).str.startswith('14')]
                        
                        # 3. Conversión numérica robusta (evita error de espacios en blanco)
                        for col in ['DEBITOS', 'CREDITOS']:
                            if col in df_compras.columns:
                                df_compras[col] = pd.to_numeric(df_compras[col], errors='coerce').fillna(0)
                        
                        df_compras['SALDO MOV.'] = df_compras.get('DEBITOS', 0) - df_compras.get('CREDITOS', 0)
                        
                        # 4. Procesamiento de Rubros (Cruce de Líneas y Grupos)
                        if 'INVENTARIO-CRUCE-CHEQUE' in df_compras.columns:
                            df_compras['linea_grupo'] = df_compras['INVENTARIO-CRUCE-CHEQUE'].str.extract(r'(\d{7})')
                            
                            # Función auxiliar para generar el código de cruce (linea_grupo)
                            def get_para_cruce(val):
                                if pd.isna(val) or len(str(val)) < 7: return None
                                s = str(val)
                                return f"{int(s[:3])}_{int(s[3:])}"
                            
                            df_compras['para_cruce'] = df_compras['linea_grupo'].apply(get_para_cruce)
                            
                            # Unir con mapeo de rubros
                            df_rubros_ref = pd.DataFrame(RUBROS_DATOS)
                            df_compras = pd.merge(df_compras, df_rubros_ref, on='para_cruce', how='left')
                        
                        # 5. Preparar datos para consolidación
                        df_final = df_compras[['FECHA', 'RUBRO', 'SALDO MOV.']].copy()
                        df_final.columns = ['FECHA', 'RUBRO', 'Valor']
                        
                        # Agrupar y formatear fecha
                        df_final = df_final.groupby(['FECHA', 'RUBRO'], as_index=False)['Valor'].sum()
                        df_final['FECHA'] = pd.to_datetime(df_final['FECHA']).dt.strftime('%Y-%m-%d')

                        # 6. Actualizar Base de Datos en la Nube
                        compras_reales = conn.read(worksheet="Control Compras", ttl=0)
                        compras_reales['FECHA'] = pd.to_datetime(compras_reales['FECHA']).dt.strftime('%Y-%m-%d')
                        
                        db_actualizada = pd.concat([compras_reales, df_final], ignore_index=True)
                        db_actualizada = db_actualizada.drop_duplicates(subset=['FECHA', 'RUBRO', 'Valor'])
                        
                        conn.update(worksheet="Control Compras", data=db_actualizada)
                        
                        st.toast("✅ ¡Compras agregadas exitosamente!")
                        st.cache_data.clear()
                        
                    except Exception as e:
                        st.error(f"Error al procesar el archivo: {e}")
            else:
                st.warning("⚠️ Por favor, selecciona un archivo Excel primero antes de guardar.")


with st.expander("✨Agregar Informe de costos"):
    st.info("Recuerda que el archivo debe ser el informe mensual que esta dentro de la carpeta de cada mes")
    with st.form("form_costos"):
        fecha_informe = st.date_input('🗓️ Fecha del informe')
        ruta = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
        btn_guardar = st.form_submit_button("💾 Guardar en base de datos", type="primary")
        
        if btn_guardar:
            if ruta is not None:
                with st.spinner("Procesando y guardando datos..."):
                    try:
                        # 1. Carga y limpieza inicial
                        pd_costos = pd.read_excel(ruta, skiprows=4, sheet_name="INFORME DE COSTOS 2026")
                        pd_costos = pd_costos.dropna(subset=['CENTRO DE COSTOS'])
                        #elimina de la fila que donde en la columna 'CENTRO DE COSTOS' lo que diga total diferencias
                        pd_costos = pd_costos[~pd_costos['CENTRO DE COSTOS'].isin(['TOTAL', 'TOTAL GENERAL', 'Total general', 'DIFERENCIAS', "PROMOCION Y PREVENCION A", "SERVICIO FARMACÉUTICO A", "APOYO DIAGNOSTICO","APOYO TERAPEUTICO","MEDICINA ESPECIALIZADA","MUNICIPIOS","ODONTOLOGIA ESPECIALIZADA","TOTAL GENERAL"])] #por los meses de enero, febrero y marzo se cargaran estos mpios "ECIS PYM","EL CHARCO", "OLAYA HERERA","SAMANIEGO", "ALBAN", "ANCUYA", "BARBACOAS","BELEN","BERRUECOS","BUESACO","CALI","COLON GENOVA","EL ROSARIO","EL TABLON","FRANCISCO PIZARRO","GUACHUCAL","GUAITARILLA","LA FLORIDA","LA TOLA","LEIVA","LINARES","MAGUI","MALLAMA","RICAURTE","ROBERTO PAYAN","SAN BERNARDO","SAN LORENZO","SAN PEDRO DE CARTAGO","SANTA BARBARA","TAMINANGO","TANGUA","MOSQUERA",

                        #ELIMINAR COLUMNAS A, B, UNIDADES FUNCIONALES
                        pd_costos = pd_costos.drop(columns=['A', 'B', 'UNIDADES FUNCIONALES', 'UNIDAD FUNCIONAL 2','AREA','TOTAL COSTOS DIRECTOS','TOTAL COSTOS INDIRECTOS','TOTAL PARA DISTRIBUIR COMUNICACIÓN','TOTAL PARA DISTRIBUCIÓN DE GASTOS GENERALES','TOTAL PARA DISTRIBUIR PROCESOS DE APOYO ADMINISTRATIVO','DISTRIBUCION ORIENTACION Y VIGILANCIA', 'DISTRIBUCION SERVICIOS GENERALES', 'TOTAL PARA DISTRIBUIR PROCESOS DE APOYO ASISTENCIAL', 'DISTRIBUCION CITAS MEDICAS ', 'AMBULANCIA', 'CAMILLEROS', 'DISTRIBUCION LAVANDERIA', 'DIRECCION CLINICA', 'PROGRAMA IAMI - AIEPI', 'SALUD MENTAL', 'EPIDEMIOLOGIA', 'SEGURIDAD DEL PACIENTE', 'DISTRIBUCION SERVICIO FARMACEUTICO', 'TOTAL PARA DISTRIBUICIN DE ADMINISTRACION', '%', 'CARGA ADMINISTRATIVA', 'CARGA ASEGURADORA', 'TOTAL', '%.1','TOTAL MAS CUENTAS MEDICAS', '%.2', 'Unnamed: 52', 'Unnamed: 53', 'MANTENIMIENTO'])
                        #unpivotear la tabla para pasar
                        pd_costos = pd.melt(pd_costos, id_vars=['CENTRO DE COSTOS'], value_vars=['TOTAL RELACION LABORAL', 'HONORARIOS', 'CONSUMOS DE INSUMOS', 'MEDICAMENTOS',       'DISPOSITIVOS MEDICOS FORMULADOS', 'DISPOSITIVOS MEDICOS DE CONSUMO',       'ALIMENTACION HOSPITALARIA','OXIGENO-     GAS-      AIRE                                  ','SANGRE', 'OTROS COSTOS DIRECTOS',  'ARRENDAMIENTOS', 'DEPRECIACION ACTIVOS FIJOS', 'DEPRECIACION EDIFICIO',       'INCINERACION', 'AGUA', 'ENERGIA','COMUNICACIÓN','GASTOS GENERALES', 'CUENTAS MEDICAS'], value_name='valor_costo')
                        pd_costos['valor_costo'] = pd.to_numeric(pd_costos['valor_costo'], errors='coerce').fillna(0).astype(int)

                        pd_costos = pd_costos[pd_costos['valor_costo'] != 0]
                        pd_costos

                        datos_cruce = {
                            "variable": ['TOTAL RELACION LABORAL','CONSUMOS DE INSUMOS','MEDICAMENTOS ','DISPOSITIVOS MEDICOS FORMULADOS','DISPOSITIVOS MEDICOS DE CONSUMO','ALIMENTACION HOSPITALARIA','SANGRE','DEPRECIACION ACTIVOS FIJOS','DEPRECIACION EDIFICIO','INCINERACION','AGUA','ENERGIA','COMUNICACIÓN','GASTOS GENERALES','CUENTAS MEDICAS','HONORARIOS','OTROS COSTOS DIRECTOS','ARRENDAMIENTOS', 'MEDICAMENTOS', 'DISPOSITIVOS MEDICOS FORMULADOS'],
                            'Rubro Presupuestal': ['50101 - GASTOS DE PERSONAL','50120 - MATERIALES Y SUMINISTROS','50120 - MATERIALES Y SUMINISTROS','50120 - MATERIALES Y SUMINISTROS','50120 - MATERIALES Y SUMINISTROS','50109 - SERVICIOS','50120 - MATERIALES Y SUMINISTROS','50112 - DEPRECIACION','50112 - DEPRECIACION','50109 - SERVICIOS','50109 - SERVICIOS','50109 - SERVICIOS','50109 - SERVICIOS','OTROS GASTOS','50104 - HONORARIOS','50104 - HONORARIOS','OTROS GASTOS','50106 - ARRENDAMIENTOS', '50120 - MATERIALES Y SUMINISTROS', '50120 - MATERIALES Y SUMINISTROS']
                        }
                        df_datos_cruce = pd.DataFrame(datos_cruce)

                        valor_medicamentos = pd_costos[pd_costos['variable'] == 'MEDICAMENTOS']['valor_costo'].sum()
                        valor_dispositivos_medicos_formulados = pd_costos[pd_costos['variable'] == 'DISPOSITIVOS MEDICOS FORMULADOS']['valor_costo'].sum()

                        valor_sf = valor_dispositivos_medicos_formulados + valor_medicamentos

                        pd_costos = pd_costos[~pd_costos['variable'].isin(['MEDICAMENTOS', 'DISPOSITIVOS MEDICOS FORMULADOS'])]
                        
                        #incluir una fila que diga SERVICIO FARMACEUTICO COMO CENTRO DE COSTO VARIABLE MEDICAMENTOS Y valor_costo = valor_medicamentos
                        incluir = {'CENTRO DE COSTOS': 'SERVICIO FARMACÉUTICO', 'variable': 'MEDICAMENTOS ', 'valor_costo': valor_sf}

                        incluir = pd.DataFrame([incluir])
                        pd_costos = pd.concat([pd_costos, incluir], ignore_index=True)

                        para_enviar = pd.merge(pd_costos, df_datos_cruce, on='variable', how='left')
                        para_enviar['FECHA'] = fecha_informe

                        #actualizar en base de datos
                        costos_reales = conn.read(worksheet="Control por CC", ttl=0)
                        costos_unidos_reales = pd.concat([costos_reales, para_enviar], ignore_index=True)


                        conn.update(worksheet="Control por CC", data=costos_unidos_reales)
                        st.toast("✅ Informe de costos agregado exitosamente!!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error al procesar el archivo: {e}")
            else:
                st.warning("⚠️ Por favor, selecciona un archivo Excel primero antes de guardar.")

with st.expander("💲 Agregar Ingresos"):
    st.info("En esta sección se puedes agregar los ingresos de la empresa, recuerda que el informe para hacerlo es el movimiento general quitado subtotales y en una sola hoja osea solo tiene que tener Hoja1")
    with st.form("form_ingresos"):
        ruta = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])
        btn_guardar = st.form_submit_button("💾 Guardar en base de datos", type="primary")
        
        if btn_guardar:
            if ruta is not None:
                with st.spinner("Procesando y guardando datos..."):
                    try:
                        unidades_funcionales = pd.DataFrame({'Cod_Uf': [4105,4110,4115,4120,4125,4130,4135], 'Nom Uni Funcio':['Urgencias', 'Consulta Externa', 'Hospitalizacion', 'Quirofano',  'Apoyo Diagnostico', 'Apoyo Terapeutico', 'Mercadeo']})
                        ingresos_control = pd.read_excel(ruta, skiprows=6)
                        ingresos_control.columns = ingresos_control.columns.str.strip()
                        ingresos_control = ingresos_control[['FECHA', 'CUENTA', 'NIT', 'NOMBRE','DEBITOS', 'CREDITOS']]
                        ingresos_control['CUENTA'] = ingresos_control['CUENTA'].str.replace(" ", "")
                        ingresos_control['CREDITOS'] = pd.to_numeric(ingresos_control['CREDITOS'], errors='coerce').fillna(0).astype(int)
                        ingresos_control['DEBITOS'] = pd.to_numeric(ingresos_control['DEBITOS'], errors='coerce').fillna(0).astype(int)
                        ingresos_control['Saldo'] = ingresos_control['CREDITOS'] - ingresos_control['DEBITOS']
                        ingresos_control["Clasificacion"] = ingresos_control["CUENTA"].str[:2]
                        ingresos_control["Clasificacion"] = np.where(ingresos_control["Clasificacion"] == "41", "Operacionales", "No Operacionales")
                        ingresos_control['Unidad Funcional'] = ingresos_control['CUENTA'].str[:4].astype(int)
                        #ingresos_control = ingresos_control[ingresos_control['Unidad Funcional'] != 4135]
                        ingresos_control['Unidad Funcional'] = pd.to_numeric(ingresos_control['Unidad Funcional'], errors='coerce').fillna(0).astype(int)
                        ingresos_control = ingresos_control.merge(unidades_funcionales, left_on='Unidad Funcional', right_on='Cod_Uf', how='left').fillna('No Operacionales')
                        
                        capita = ingresos_control[(ingresos_control['CUENTA'] == '4110102702') & (ingresos_control['Saldo'] > 10000000)]
                        VALOR_DISTRIBUIR = capita.Saldo.sum()
                        PARA_DISTRIBUIR = pd.DataFrame({
                            'CUENTA': ['4125100210','4125100310','4110102702','4110103402','4110105402','4110102102','4110102602','4110102802','4110104202','4110104502','4130100102','4130100602','4110103302','4110104402','4130100302','4130100202','4130100802'],
                            'PORCENTAJE' : [0.124253168191507,0.0962459071985921,0.0498630419036186,0.0848546175503838,0.0990476477229005,0.151408256325752,0.133136616877349,0.0647937080489093,0.0336932464173509,0.018565378801987,0.00636601721334622,0.0111461695143457,0.0305430041391138,0.0611776432816374,0.00824929420446009,0.0131886359182637,0.013467646690482]

                        })
                        PARA_DISTRIBUIR['Saldo'] = PARA_DISTRIBUIR['PORCENTAJE'] * VALOR_DISTRIBUIR
                        PARA_DISTRIBUIR.Saldo = PARA_DISTRIBUIR.Saldo.astype(int)
                        PARA_DISTRIBUIR['FECHA'] = ingresos_control.FECHA.max()
                        PARA_DISTRIBUIR['NIT'] = 830053105
                        PARA_DISTRIBUIR['NOMBRE'] = 'FIDEICOMISOS PATRIMONIOS AUTONOMOS FIDUCIARIA LA PREVISORA SA'
                        PARA_DISTRIBUIR['Unidad Funcional'] = PARA_DISTRIBUIR['CUENTA'].str[:4].astype(int)
                        PARA_DISTRIBUIR = PARA_DISTRIBUIR.merge(unidades_funcionales, left_on='Unidad Funcional', right_on='Cod_Uf', how='left')
                        PARA_DISTRIBUIR['Clasificacion'] = 'Operacionales'
                        PARA_DISTRIBUIR['DEBITOS'] = 0
                        PARA_DISTRIBUIR['CREDITOS'] = 0
                        PARA_DISTRIBUIR = PARA_DISTRIBUIR[['FECHA', 'CUENTA', 'NIT', 'NOMBRE', 'Unidad Funcional', 'Nom Uni Funcio', 'Clasificacion', 'DEBITOS', 'CREDITOS', 'Saldo']]

                        ingresos_control = ingresos_control[~((ingresos_control['CUENTA'] == '4110102702') & (ingresos_control['Saldo'] > 10000000))]
                        
                        ingresos_control = ingresos_control.groupby(['FECHA', 'CUENTA', 'NIT', 'NOMBRE','Unidad Funcional', 'Nom Uni Funcio', 'Clasificacion']).agg({
                            'DEBITOS': 'sum',
                            'CREDITOS': 'sum',
                            'Saldo': 'sum'
                        }).reset_index()

                        ingresos_control = pd.concat([ingresos_control, PARA_DISTRIBUIR], ignore_index=True)

                        #actualizar en base de datos
                        ingresos_reales = conn.read(worksheet="Control_Ingresos", ttl=0)
                        ingresos_unidos_reales = pd.concat([ingresos_reales, ingresos_control], ignore_index=True)


                        conn.update(worksheet="Control_Ingresos", data=ingresos_unidos_reales)
                        st.toast("✅ Informe de costos agregado exitosamente!!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error al procesar el archivo: {e}")
            else:
                st.warning("⚠️ Por favor, selecciona un archivo Excel primero antes de guardar.")


                        

