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
