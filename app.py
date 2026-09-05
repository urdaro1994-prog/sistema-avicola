import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="HUEVONADA URIEL DAVID", layout="wide")

# --- ENCABEZADO CON ESCUDO Y TÍTULO NUEVO ---
col_logo, col_titulo = st.columns([1, 5])

with col_logo:
    if os.path.exists("ESCUDO.png"):
        st.image("ESCUDO.png", width=120)
    elif os.path.exists("escudo.png"):
        st.image("escudo.png", width=120)
    else:
        st.write("🛡️")

with col_titulo:
    st.title("HUEVONADA URIEL DAVID")
    st.caption("Gestión Avícola - Control de Stock")

# --- FUNCIONES DE BASE DE DATOS ---
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

def registrar_venta_multiple(cliente, galpon, items_venta):
    conn = get_connection()
    cur = conn.cursor()
    
    for item in items_venta:
        clasificacion = item['clasificacion']
        cantidad = item['cantidad']
        precio_unitario = item['precio_unitario']
        subtotal = item['subtotal']
        
        # Guardar en historial de ventas
        cur.execute("""
            INSERT INTO ventas (cliente, galpon_origen, clasificacion, cantidad_huevos, total_dinero)
            VALUES (%s, %s, %s, %s, %s)
        """, (cliente, galpon, clasificacion, cantidad, subtotal))
        
        # Descontar del inventario
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

# --- INTERFAZ DE USUARIO EN PESTAÑAS ---
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
    st.header("Despacho de Ventas Múltiples")
    df_inv = cargar_inventario()
    
    # Inicializar el carrito de compras en la sesión de Streamlit
    if "carrito_ventas" not in st.session_state:
        st.session_state.carrito_ventas = []

    col_cli, col_gal = st.columns(2)
    with col_cli:
        cliente = st.text_input("Nombre del Cliente")
    with col_gal:
        galpon_v = st.selectbox("Galpón Origen", ["Galpón 1", "Galpón 2", "Galpón 3"], key="v_gal")

    st.markdown("---")
    st.subheader("➕ Agregar Productos a la Venta")
    
    col_clas, col_cant, col_prec, col_btn = st.columns([2, 2, 2, 1])
    
    with col_clas:
        clasif_v = st.selectbox("Clasificación", ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"], key="v_clas")
        stock_disp = df_inv.loc[galpon_v, clasif_v]
        st.caption(f"Disponible: **{stock_disp}** huevos")

    with col_cant:
        cant_v = st.number_input("Cantidad (Huevos)", min_value=1, value=1, key="v_cant")

    with col_prec:
        precio_unitario = st.number_input("Precio Unitario ($)", min_value=0.0, value=0.0, step=10.0, key="v_prec")

    with col_btn:
        st.write(" ") # Espaciador para alinear el botón
        st.write(" ")
        if st.button("➕ Agregar"):
            if cant_v > stock_disp:
                st.error("Supera el stock.")
            elif precio_unitario <= 0:
                st.warning("Precio inválido.")
            else:
                subtotal = cant_v * precio_unitario
                st.session_state.carrito_ventas.append({
                    "clasificacion": clasif_v,
                    "cantidad": cant_v,
                    "precio_unitario": precio_unitario,
                    "subtotal": subtotal
                })
                st.success(f"Añadido {clasif_v.upper()}")

    # Mostrar la lista de ítems agregados a esta venta
    if st.session_state.carrito_ventas:
        st.markdown("### 🛒 Resumen de la Venta")
        df_carrito = pd.DataFrame(st.session_state.carrito_ventas)
        st.dataframe(df_carrito, use_container_width=True)

        total_factura = df_carrito["subtotal"].sum()
        st.markdown(f"### **TOTAL FACTURA: ${total_factura:,.2f}**")

        col_guardar, col_limpiar = st.columns([2, 1])
        
        with col_guardar:
            if st.button("🚀 Confirmar y Guardar Venta Completa", type="primary"):
                if not cliente.strip():
                    st.error("Por favor ingresa el nombre del cliente.")
                else:
                    registrar_venta_multiple(cliente, galpon_v, st.session_state.carrito_ventas)
                    st.success("¡Venta registrada con éxito y descontada del inventario!")
                    st.session_state.carrito_ventas = [] # Limpiar carrito
                    st.rerun()

        with col_limpiar:
            if st.button("🗑️ Vaciar Lista"):
                st.session_state.carrito_ventas = []
                st.rerun()

with tab3:
    st.header("Stock Acumulado Actual")
    st.dataframe(cargar_inventario(), use_container_width=True)
    st.header("Historial de Ventas")
    st.dataframe(cargar_ventas(), use_container_width=True)
