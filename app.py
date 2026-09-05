import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Configuración de página móvil
st.set_page_config(page_title="HUEVONADA - App", layout="centered", initial_sidebar_state="collapsed")

# --- ESTILOS CSS TIPO APP MÓVIL (TikTok Style) ---
st.markdown("""
    <style>
    /* Ocultar barra superior, menú y footer de Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Espaciado general para pantallas de teléfono */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        max-width: 500px; /* Ancho típico de celular */
    }
    
    /* Encabezado fijo y moderno */
    .app-header {
        text-align: center;
        background: linear-gradient(135deg, #125375 0%, #0d3850 100%);
        color: white;
        padding: 15px;
        border-radius: 16px;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Tarjetas redondeadas estilo App */
    .app-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 15px;
        border: 1px solid #e1e8ed;
    }
    
    /* Botones principales tipo móvil */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        font-weight: bold;
        background-color: #125375;
        color: white;
        border: none;
    }
    
    /* Ajustes para la tabla de edición */
    div[data-testid="stDataEditor"] {
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
""", unsafe_allow_html=True)

# --- ENCABEZADO FIJO ---
col_logo, col_tit = st.columns([1, 3])
with col_logo:
    if os.path.exists("ESCUDO.png"):
        st.image("ESCUDO.png", width=70)
    elif os.path.exists("escudo.png"):
        st.image("escudo.png", width=70)
    else:
        st.write("🛡️")
with col_tit:
    st.markdown("### **AGROAVÍCOLA**\n*Santa Isabel*")

# --- NAVEGACIÓN INFERIOR (Estilo Menú Móvil) ---
if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = "📤 Remisiones"

# Botones de navegación tipo menú de App abajo
c_nav1, c_nav2, c_nav3 = st.columns(3)
with c_nav1:
    if st.button("📥 Entrada", use_container_width=True):
        st.session_state.seccion_activa = "📥 Entrada"
with c_nav2:
    if st.button("📤 Remisión", use_container_width=True):
        st.session_state.seccion_activa = "📤 Remisiones"
with c_nav3:
    if st.button("📊 Stock", use_container_width=True):
        st.session_state.seccion_activa = "📊 Stock"

st.markdown("---")

# --- FUNCIONES DE BASE DE DATOS ---
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])

def obtener_siguiente_num_remision():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(MAX(num_remision), 0) + 1 FROM ventas")
        num = cur.fetchone()[0]
    except:
        conn.rollback()
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM ventas")
        num = cur.fetchone()[0]
    cur.close()
    conn.close()
    return num

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

def registrar_venta_multiple(cliente, cedula, direccion, telefono, email, conductor, num_remision, galpon, items_venta):
    conn = get_connection()
    cur = conn.cursor()
    for item in items_venta:
        clasificacion = item['Clasificación']
        cantidad = int(item['Cantidad (Huevos)'])
        subtotal = float(item['Subtotal ($)'])
        try:
            cur.execute("""
                INSERT INTO ventas (cliente, galpon_origen, clasificacion, cantidad_huevos, total_dinero, num_remision)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (cliente, galpon, clasificacion, cantidad, subtotal, num_remision))
        except:
            conn.rollback()
            cur.execute("""
                INSERT INTO ventas (cliente, galpon_origen, clasificacion, cantidad_huevos, total_dinero)
                VALUES (%s, %s, %s, %s, %s)
            """, (cliente, galpon, clasificacion, cantidad, subtotal))
        
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

def generar_pdf_remision(num_remision, fecha_str, conductor, cliente_datos, items_df, total_factura):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    
    header_data = [
        [
            Image("ESCUDO.png", width=60, height=60) if os.path.exists("ESCUDO.png") else "🛡️",
            Paragraph("<font size=16 color='#ffffff'><b>Remisión de venta</b></font>", style_normal),
            Paragraph("<font size=9 color='#ffffff'><b>Agroavicola Santa Isabel</b><br/>NIT. 901.786.799 - 7<br/>Cel. 3102397244 - 3125588606</font>", style_normal)
        ]
    ]
    t_header = Table(header_data, colWidths=[80, 260, 200])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#125375")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 15))

    num_str = f"{num_remision:06d}"
    cliente_info_data = [
        [
            Paragraph(f"<b>Remisión No.</b> {num_str}<br/><b>Fecha</b> {fecha_str}<br/><b>Conductor</b> {conductor}", style_normal),
            Paragraph(f"<b>Datos del cliente</b><br/><b>Nombre/Razón Social:</b> {cliente_datos['nombre']}<br/><b>Cédula/NIT:</b> {cliente_datos['cedula']}<br/><b>Dirección:</b> {cliente_datos['direccion']}<br/><b>Teléfono:</b> {cliente_datos['telefono']}<br/><b>Email:</b> {cliente_datos['email']}", style_normal)
        ]
    ]
    t_info = Table(cliente_info_data, colWidths=[240, 300])
    t_info.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
    story.append(t_info)
    story.append(Spacer(1, 15))

    table_data = [["Descripción", "Cantidad", "Valor Unitario", "Valor total"]]
    for _, fila in items_df.iterrows():
        table_data.append([
            str(fila["Clasificación"]).upper(),
            f"{int(fila['Cantidad (Huevos)']):,}",
            f"$ {fila['Precio Unitario ($)']:,.2f}",
            f"$ {fila['Subtotal ($)']:,.2f}"
        ])

    for _ in range(max(0, 5 - len(items_df))):
        table_data.append(["", "", "", ""])

    t_items = Table(table_data, colWidths=[200, 100, 120, 120])
    t_items.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,0), 1.5, colors.black),
        ('LINEABOVE', (0,0), (-1,0), 1.5, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('GRID', (0,1), (-1,-1), 0.5, colors.HexColor("#c1d5e0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#eef4f8"), colors.white]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    totales_data = [
        ["Subtotal", f"$ {total_factura:,.2f}"],
        ["IVA", "$ 0.00"],
        ["Total", f"$ {total_factura:,.2f}"]
    ]
    t_totales = Table(totales_data, colWidths=[420, 120])
    t_totales.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,2), (-1,2), 'Helvetica-Bold'),
        ('LINEABOVE', (0,2), (-1,2), 1, colors.HexColor("#125375")),
    ]))
    story.append(t_totales)

    doc.build(story)
    buffer.seek(0)
    return buffer

# --- SECCIONES DE LA APLICACIÓN ---

# 1. ENTRADA DE PRODUCCIÓN
if st.session_state.seccion_activa == "📥 Entrada":
    st.subheader("📥 Registro Diario de Postura")
    fecha = st.date_input("Fecha", datetime.now())
    galpon = st.selectbox("Galpón", ["Galpón 1", "Galpón 2", "Galpón 3"])
    
    y = st.number_input("Yumbo", min_value=0, value=0)
    ex = st.number_input("Extra", min_value=0, value=0)
    aa = st.number_input("AA", min_value=0, value=0)
    a = st.number_input("A", min_value=0, value=0)
    b = st.number_input("B", min_value=0, value=0)
    c = st.number_input("C", min_value=0, value=0)
    suc = st.number_input("Sucio", min_value=0, value=0)
    rot = st.number_input("Roto", min_value=0, value=0)
        
    if st.button("💾 Guardar Producción"):
        conteos = {'Yumbo': y, 'Extra': ex, 'AA': aa, 'A': a, 'B': b, 'C': c, 'Sucio': suc, 'Roto': rot}
        registrar_produccion(fecha, galpon, conteos)
        st.success("¡Registro de producción guardado!")

# 2. GENERACIÓN DE REMISIONES
elif st.session_state.seccion_activa == "📤 Remisiones":
    df_inv = cargar_inventario()
    num_remision_actual = obtener_siguiente_num_remision()

    st.subheader(f"📋 Remisión No. {num_remision_actual:06d}")
    
    cliente_nombre = st.text_input("Razón Social / Cliente", placeholder="Ej. RAFAEL GARCIA")
    cedula_nit = st.text_input("Cédula / NIT", placeholder="Ej. 901.786.799-7")
    direccion = st.text_input("Dirección", value="CHOACHI")
    telefono = st.text_input("Teléfono", placeholder="Ej. 3102397244")
    email = st.text_input("Email", placeholder="cliente@correo.com")
    conductor = st.text_input("Conductor", value="Ivan Herrera")
    galpon_v = st.selectbox("Galpón Origen", ["Galpón 1", "Galpón 2", "Galpón 3"], key="v_gal_m")

    st.markdown("### 🛒 Detalle del Despacho")
    opciones_clasif = ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"]
    df_base = pd.DataFrame([{"Clasificación": "a", "Cantidad (Huevos)": 3000, "Precio Unitario ($)": 370.0}])

    df_editado = st.data_editor(
        df_base,
        num_rows="dynamic",
        column_config={
            "Clasificación": st.column_config.SelectboxColumn("Clasificación", options=opciones_clasif, required=True),
            "Cantidad (Huevos)": st.column_config.NumberColumn("Cantidad", min_value=0, step=1, required=True),
            "Precio Unitario ($)": st.column_config.NumberColumn("Precio ($)", min_value=0.0, step=1.0, format="$%.2f", required=True)
        },
        use_container_width=True
    )

    items_validos = df_editado[df_editado["Cantidad (Huevos)"] > 0].copy()

    if not items_validos.empty:
        items_validos["Subtotal ($)"] = items_validos["Cantidad (Huevos)"] * items_validos["Precio Unitario ($)"]
        total_factura = items_validos["Subtotal ($)"].sum()

        st.markdown(f"### **TOTAL: ${total_factura:,.2f}**")

        if st.button("🚀 Confirmar y Generar Remisión"):
            if not cliente_nombre.strip():
                st.error("Por favor ingresa el Nombre del cliente.")
            else:
                errores_stock = []
                for _, fila in items_validos.iterrows():
                    c_clasif = fila["Clasificación"]
                    c_cant = int(fila["Cantidad (Huevos)"])
                    stock_disp = df_inv.loc[galpon_v, c_clasif]
                    if c_cant > stock_disp:
                        errores_stock.append(f"Stock insuficiente para {c_clasif.upper()}. Disponible: {stock_disp}")

                if errores_stock:
                    for err in errores_stock:
                        st.error(err)
                else:
                    items_dict = items_validos.to_dict(orient="records")
                    registrar_venta_multiple(
                        cliente_nombre, cedula_nit, direccion, telefono, email, conductor, 
                        num_remision_actual, galpon_v, items_dict
                    )
                    
                    st.success(f"¡Remisión No. {num_remision_actual:06d} lista!")
                    
                    fecha_hoy_str = datetime.now().strftime("%d/%m/%Y")
                    datos_cliente = {
                        "nombre": cliente_nombre,
                        "cedula": cedula_nit,
                        "direccion": direccion,
                        "telefono": telefono,
                        "email": email
                    }
                    pdf_buffer = generar_pdf_remision(
                        num_remision_actual, fecha_hoy_str, conductor, datos_cliente, items_validos, total_factura
                    )

                    st.download_button(
                        label="📄 Descargar Remisión PDF",
                        data=pdf_buffer,
                        file_name=f"Remision_{num_remision_actual:06d}_{cliente_nombre}.pdf",
                        mime="application/pdf"
                    )

# 3. STOCK E HISTORIAL
elif st.session_state.seccion_activa == "📊 Stock":
    st.subheader("📦 Stock en Granja")
    st.dataframe(cargar_inventario(), use_container_width=True)
    
    st.subheader("📜 Historial de Ventas")
    st.dataframe(cargar_ventas(), use_container_width=True)
