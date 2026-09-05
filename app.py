import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="HUEVONADA URIEL DAVID", layout="wide")

# --- ENCABEZADO CON ESCUDO Y TÍTULO ---
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
        clasificacion = item['Clasificación']
        cantidad = int(item['Cantidad (Huevos)'])
        subtotal = float(item['Subtotal ($)'])
        
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
    st.header("Despacho de Ventas")
    df_inv = cargar_inventario()
    
    col_cli, col_gal = st.columns(2)
    with col_cli:
        cliente = st.text_input("Nombre del Cliente")
    with col_gal:
        galpon_v = st.selectbox("Galpón Origen", ["Galpón 1", "Galpón 2", "Galpón 3"], key="v_gal")

    st.markdown("---")
    st.subheader("🛒 Ingreso de ítems para la venta")
    st.caption("Selecciona la clasificación, cantidad y precio por fila. Haz clic en el botón '+' al final de la tabla para agregar más filas.")

    opciones_clasif = ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"]
    
    df_base = pd.DataFrame([
        {"Clasificación": "yumbo", "Cantidad (Huevos)": 0, "Precio Unitario ($)": 0.0}
    ])

    df_editado = st.data_editor(
        df_base,
        num_rows="dynamic",
        column_config={
            "Clasificación": st.column_config.SelectboxColumn(
                "Clasificación",
                options=opciones_clasif,
                required=True
            ),
            "Cantidad (Huevos)": st.column_config.NumberColumn(
                "Cantidad (Huevos)",
                min_value=0,
                step=1,
                required=True
            ),
            "Precio Unitario ($)": st.column_config.NumberColumn(
                "Precio Unitario ($)",
                min_value=0.0,
                step=10.0,
                format="$%.2f",
                required=True
            )
        },
        use_container_width=True
    )

    # Filtrar solo ítems con cantidad > 0
    items_validos = df_editado[df_editado["Cantidad (Huevos)"] > 0].copy()

    if not items_validos.empty:
        items_validos["Subtotal ($)"] = items_validos["Cantidad (Huevos)"] * items_validos["Precio Unitario ($)"]
        items_validos["Cubetas (30)"] = items_validos["Cantidad (Huevos)"] // 30
        items_validos["Sueltos"] = items_validos["Cantidad (Huevos)"] % 30
        total_huevos = items_validos["Cantidad (Huevos)"].sum()
        total_factura = items_validos["Subtotal ($)"].sum()

        st.markdown("---")
        st.subheader("🧾 Vista Previa de la Factura / Recibo")
        
        # Tarjeta de encabezado de la factura
        col_f1, col_f2, col_f3 = st.columns(3)
        col_f1.metric("Cliente", cliente if cliente.strip() else "—")
        col_f2.metric("Origen", galpon_v)
        col_f3.metric("Total Huevos", f"{total_huevos:,} uds")

        # Tabla de desglose de la factura
        st.dataframe(
            items_validos[[
                "Clasificación", 
                "Cantidad (Huevos)", 
                "Cubetas (30)", 
                "Sueltos", 
                "Precio Unitario ($)", 
                "Subtotal ($)"
            ]],
            use_container_width=True,
            column_config={
                "Precio Unitario ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Subtotal ($)": st.column_config.NumberColumn(format="$%.2f")
            }
        )

        st.markdown(f"### **TOTAL FACTURA: ${total_factura:,.2f}**")

        if st.button("🚀 Confirmar y Guardar Venta Completa", type="primary"):
            if not cliente.strip():
                st.error("Por favor ingresa el nombre del cliente.")
            else:
                # Verificar disponibilidad de stock
                errores_stock = []
                for _, fila in items_validos.iterrows():
                    c_clasif = fila["Clasificación"]
                    c_cant = int(fila["Cantidad (Huevos)"])
                    stock_disp = df_inv.loc[galpon_v, c_clasif]
                    
                    if c_cant > stock_disp:
                        errores_stock.append(f"No hay suficiente stock para **{c_clasif.upper()}**. Disponible: {stock_disp}, Solicitado: {c_cant}")
                
                if errores_stock:
                    for err in errores_stock:
                        st.error(err)
                else:
                    items_dict = items_validos.to_dict(orient="records")
                    registrar_venta_multiple(cliente, galpon_v, items_dict)
                    st.success("¡Venta registrada con éxito y descontada del inventario!")
                    st.rerun()

with tab3:
    st.header("Stock Acumulado Actual")
    st.dataframe(cargar_inventario(), use_container_width=True)
    st.header("Historial de Ventas")
    st.dataframe(cargar_ventas(), use_container_width=True)
