import streamlit as st
import pandas as pd
import os
from datetime import date

# 1. Configuración de la página
st.set_page_config(
    page_title="HUEVONADA - Agroavícola Santa Isabel", 
    page_icon="🛡️", 
    layout="wide"
)

# 2. Encabezado: Título HUEVONADA con el Escudo al lado
col1, col2 = st.columns([1, 6])

with col1:
    # Verificación segura de la imagen local para evitar errores si cambia el nombre
    nombre_imagen = "ESCUDO.png"
    if os.path.exists(nombre_imagen):
        st.image(nombre_imagen, width=110)
    elif os.path.exists("escudo.png"):
        st.image("escudo.png", width=110)
    else:
        st.write("🛡️") # Muestra icono por defecto en caso de no hallar la imagen

with col2:
    st.title("HUEVONADA")
    st.caption("Control de Postura y Stock de Huevos — Agroavícola Santa Isabel")

# 3. Conexión nativa de Streamlit a Postgres (Supabase)
conn = st.connection("postgres", type="sql")

# 4. Pestañas de navegación de la aplicación
tab1, tab2 = st.tabs(["📝 Registrar Clasificación Diario", "📊 Reporte de Stock e Inventario"])

# --- PESTAÑA 1: REGISTRO DE ENTRADA ---
with tab1:
    st.subheader("Entrada de Inventario Físico")
    
    with st.form("form_huevos", clear_on_submit=True):
        f_col1, f_col2 = st.columns(2)
        
        with f_col1:
            fecha_registro = st.date_input("Fecha de Conteo", date.today())
            galpon = st.selectbox("Galpón / Ubicación", ["Galpón 1", "Galpón 2", "Galpón 3", "General"])
            clasificacion = st.selectbox(
                "Clasificación / Tamaño", 
                ["Jumbo", "AAA", "AA", "A", "B", "C", "Pique / Roto", "Manchado / Sucio"]
            )
            
        with f_col2:
            cartones = st.number_input("Cubetas / Cartones (30 uds)", min_value=0, step=1, value=0)
            unidades_sueltas = st.number_input("Huevos sueltos", min_value=0, max_value=29, step=1, value=0)
            
            # Cálculo de total
            total_huevos = (cartones * 30) + unidades_sueltas
            st.info(f"👉 **Total calculado:** {total_huevos} huevos")

        observaciones = st.text_area("Notas / Observaciones", placeholder="Ej. Conteo inicial en físico...")
        
        btn_guardar = st.form_submit_button("Guardar Registro", type="primary")

    if btn_guardar:
        if total_huevos <= 0:
            st.warning("Ingresa una cantidad válida mayor a 0.")
        else:
            query = """
                INSERT INTO control_huevos (fecha, galpon, tipo_clasificacion, cantidad_cartones, cantidad_unidades, total_huevos, observaciones)
                VALUES (:fecha, :galpon, :clasif, :cartones, :unidades, :total, :obs);
            """
            with conn.session as session:
                session.execute(
                    query,
                    {
                        "fecha": fecha_registro,
                        "galpon": galpon,
                        "clasif": clasificacion,
                        "cartones": cartones,
                        "unidades": unidades_sueltas,
                        "total": total_huevos,
                        "obs": observaciones
                    }
                )
                session.commit()
                
            st.success(f"¡Registrados {total_huevos} huevos ({clasificacion}) exitosamente!")
            st.cache_data.clear()

# --- PESTAÑA 2: CONSULTA Y REPORTES ---
with tab2:
    st.subheader("📊 Consultas y Balance")
    
    # Consulta de registros
    df_huevos = conn.query(
        "SELECT id, fecha, galpon, tipo_clasificacion, cantidad_cartones, cantidad_unidades, total_huevos, observaciones FROM control_huevos ORDER BY fecha DESC, id DESC;", 
        ttl="1m"
    )
    
    if not df_huevos.empty:
        # Resumen general
        total_acumulado = df_huevos["total_huevos"].sum()
        total_cubetas = total_acumulado // 30
        sobrantes = total_acumulado % 30
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Huevos Acumulados", f"{total_acumulado:,} uds")
        m2.metric("Total Cubetas", f"{total_cubetas:,} cubetas")
        m3.metric("Sueltos Sobrantes", f"{sobrantes} uds")
        
        st.divider()
        
        # Filtros dinámicos
        filt_col1, filt_col2 = st.columns(2)
        with filt_col1:
            filtro_galpon = st.multiselect("Filtrar por Galpón", options=df_huevos["galpon"].unique(), default=df_huevos["galpon"].unique())
        with filt_col2:
            filtro_tipo = st.multiselect("Filtrar por Tamaño/Tipo", options=df_huevos["tipo_clasificacion"].unique(), default=df_huevos["tipo_clasificacion"].unique())
            
        df_filtrado = df_huevos[(df_huevos["galpon"].isin(filtro_galpon)) & (df_huevos["tipo_clasificacion"].isin(filtro_tipo))]
        
        # Tabla interactiva de datos
        st.dataframe(
            df_filtrado,
            use_container_width=True,
            column_config={
                "id": "ID",
                "fecha": "Fecha",
                "galpon": "Galpón",
                "tipo_clasificacion": "Clasificación",
                "cantidad_cartones": "Cubetas (30)",
                "cantidad_unidades": "Sueltos",
                "total_huevos": "Total Unidades",
                "observaciones": "Observaciones"
            }
        )
    else:
        st.info("No hay registros guardados en la base de datos.")
