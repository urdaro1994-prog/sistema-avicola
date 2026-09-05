import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

st.set_page_config(page_title="Control Avícola", layout="wide")

def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])

def registrar_produccion(fecha, galpon, conteos):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO produccion (fecha, galpon, yumbo, extra, aa, a, b, c, sucio, roto)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (fecha, galpon, conteos['Yumbo'], conteos['Extra'], conteos['AA'], 
          conteos['A'], conteos['B'], conteos['C'], conteos['Sucio'], conteos['Roto']))
    
    cur.execute("""
        UPDATE inventario SET
            yumbo = yumbo + %s, extra = extra + %s, aa = aa + %s, a = a + %s,
            b = b + %s, c = c + %s, sucio = sucio + %s, roto = roto + %s
        WHERE galpon = %s
    """, (conteos['Yumbo'], conteos['Extra'], conteos['AA'], conteos['A'],
          conteos['B'], conteos['C'], conteos['Sucio'], conteos['Roto'], galpon))
    conn.commit()
    cur.close()
    conn.close()

def registrar_venta(cliente, galpon, clasificacion, cantidad, total):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ventas (cliente, galpon_origen, clasificacion, cantidad_huevos, total_dinero)
        VALUES (%s, %s, %s, %s, %s)
    """, (cliente, galpon, clasificacion, cantidad, total))
    
    query = f"UPDATE inventario SET {clasificacion.lower()} = {clasificacion.lower()} - %s WHERE galpon = %s"
    cur.execute(query, (cantidad, galpon))
    
    conn.commit()
    cur.close()
    conn.close()

def cargar_inventario():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM inventario ORDER BY galpon", conn)
    conn.close()
    return df.set_index('galpon')

def cargar_ventas():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM ventas ORDER BY id DESC", conn)
    conn.close()
    return df

# --- INTERFAZ DE USUARIO ---
st.title("🐔 Gestión Avícola - Control de Stock")

tab1, tab2, tab3 = st.tabs(["📥 Entrada Producción", "📤 Salida / Ventas", "📊 Inventario Real"])

with tab1:
    st.header("Registro Diario de Postura")
    fecha = st.date_input("Fecha", datetime.now())
    galpon = st.selectbox("Galpón", ["Galpón 1", "Galpón 2", "Galpón 3"])
    
    c1, c2 = st.columns(2)
    with c1:
        y = st.number_input("Yumbo", min_value=0, value=0)
        ex = st.number_input("Extra", min_value=0, value=0)
        aa = st.number_input("AA", min_value=0, value=0)
        a = st.number_input("A", min_value=0, value=0)
    with c2:
        b = st.number_input("B", min_value=0, value=0)
        c = st.number_input("C", min_value=0, value=0)
        suc = st.number_input("Sucio", min_value=0, value=0)
        rot = st.number_input("Roto", min_value=0, value=0)
        
    if st.button("💾 Guardar Producción"):
        conteos = {'Yumbo': y, 'Extra': ex, 'AA': aa, 'A': a, 'B': b, 'C': c, 'Sucio': suc, 'Roto': rot}
        registrar_produccion(fecha, galpon, conteos)
        st.success("¡Registro de producción guardado exitosamente!")

with tab2:
    st.header("Despacho de Ventas")
    df_inv = cargar_inventario()
    cliente = st.text_input("Nombre del Cliente")
    galpon_v = st.selectbox("Galpón Origen", ["Galpón 1", "Galpón 2", "Galpón 3"], key="v_gal")
    clasif_v = st.selectbox("Clasificación", ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"])
    
    stock_disp = df_inv.loc[galpon_v, clasif_v]
    st.info(f"Disponible en {galpon_v} ({clasif_v.upper()}): {stock_disp} huevos")
    
    cant_v = st.number_input("Cantidad de Huevos Vendidos", min_value=1, value=1)
    precio_v = st.number_input("Valor Total Venta ($)", min_value=0.0, value=0.0)
    
    if st.button("🚀 Registrar Venta"):
        if cant_v > stock_disp:
            st.error("No hay suficiente stock en ese galpón para realizar la venta.")
        else:
            registrar_venta(cliente, galpon_v, clasif_v, cant_v, precio_v)
            st.success("Venta procesada y descontada del inventario.")

with tab3:
    st.header("Stock Acumulado Actual")
    st.dataframe(cargar_inventario(), use_container_width=True)
    st.header("Historial de Ventas")
    st.dataframe(cargar_ventas(), use_container_width=True)
import streamlit as st
import pandas as pd
from datetime import date

st.title("🥚 Control de Postura y Stock de Huevos")

# Conexión a Postgres configurada en Secrets
conn = st.connection("postgres", type="sql")

# Pestañas principales
tab1, tab2 = st.tabs(["📝 Registrar Clasificación Diario", "📊 Reporte de Stock"])

# --- PESTAÑA 1: REGISTRO DE CLASIFICACIÓN ---
with tab1:
    st.subheader("Entrada de Inventario Físico")
    
    with st.form("form_huevos", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            fecha_registro = st.date_input("Fecha de Conteo", date.today())
            galpon = st.selectbox("Galpón / Ubicación", ["Galpón 1", "Galpón 2", "Galpón 3", "General"])
            clasificacion = st.selectbox(
                "Clasificación / Tamaño", 
                ["Jumbo", "AAA", "AA", "A", "B", "C", "Pique / Roto", "Manchado / Sucio"]
            )
            
        with col2:
            cartones = st.number_input("Cubetas / Cartones (30 uds)", min_value=0, step=1, value=0)
            unidades_sueltas = st.number_input("Huevos sueltos", min_value=0, max_value=29, step=1, value=0)
            
            # Cálculo automático
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

# --- PESTAÑA 2: BALANCE Y REPORTE DE STOCK ---
with tab2:
    st.subheader("📊 Stock Actual y Consultas")
    
    # Consultar datos guardados
    df_huevos = conn.query("SELECT id, fecha, galpon, tipo_clasificacion, cantidad_cartones, cantidad_unidades, total_huevos, observaciones FROM control_huevos ORDER BY fecha DESC, id DESC;", ttl="1m")
    
    if not df_huevos.empty:
        # Métricas resumidas
        total_acumulado = df_huevos["total_huevos"].sum()
        total_cubetas = total_acumulado // 30
        sobrantes = total_acumulado % 30
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Huevos en Stock", f"{total_acumulado:,} uds")
        c2.metric("Total Cubetas", f"{total_cubetas:,} cubetas")
        c3.metric("Sueltos Sobrantes", f"{sobrantes} uds")
        
        st.divider()
        
        # Filtros de búsqueda
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            filtro_galpon = st.multiselect("Filtrar por Galpón", options=df_huevos["galpon"].unique(), default=df_huevos["galpon"].unique())
        with f_col2:
            filtro_tipo = st.multiselect("Filtrar por Tamaño/Tipo", options=df_huevos["tipo_clasificacion"].unique(), default=df_huevos["tipo_clasificacion"].unique())
            
        df_filtrado = df_huevos[(df_huevos["galpon"].isin(filtro_galpon)) & (df_huevos["tipo_clasificacion"].isin(filtro_tipo))]
        
        # Mostrar tabla interactiva
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
        st.info("No hay registros en el inventario aún.")
