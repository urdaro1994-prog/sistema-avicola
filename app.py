import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import datetime
import io
import base64
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Avícola Santa Isabel",
    page_icon="🥚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CREAR ÍCONO SVG CON HUEVO PARA APPLE Y ANDROID ---
svg_huevo = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="20" fill="#0f2942"/>
  <text x="50" y="68" font-size="65" text-anchor="middle">🥚</text>
</svg>"""

b64_svg = base64.b64encode(svg_huevo.encode('utf-8')).decode('utf-8')
data_uri = f"data:image/svg+xml;base64,{b64_svg}"

st.markdown(f"""
    <script>
        var doc = window.parent.document;
        var oldIcons = doc.querySelectorAll("link[rel*='icon'], link[rel*='apple']");
        oldIcons.forEach(function(el) {{ el.remove(); }});
        var appleIcon = doc.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        appleIcon.href = '{data_uri}';
        doc.head.appendChild(appleIcon);
        var icon = doc.createElement('link');
        icon.rel = 'icon';
        icon.type = 'image/svg+xml';
        icon.href = '{data_uri}';
        doc.head.appendChild(icon);
        var metaTitle = doc.createElement('meta');
        metaTitle.name = 'apple-mobile-web-app-title';
        metaTitle.content = 'Avícola Santa Isabel';
        doc.head.appendChild(metaTitle);
    </script>
""", unsafe_allow_html=True)

# --- ESTILOS CSS CON COLORES PERSONALIZADOS ---
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Fondo general de toda la aplicación (Azul grisáceo exterior) */
    .stApp {
        background-color: #c8d6e5 !important;
    }
    
    /* Contenedor central (La tarjeta principal) en Azul Oscuro */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 5rem;
        padding-left: 1.2rem;
        padding-right: 1.2rem;
        max-width: 540px;
        background-color: #0f2942 !important; /* Tarjeta central en azul oscuro */
        border-radius: 16px;
        box-shadow: 0 10px 35px rgba(15, 41, 66, 0.3);
        margin-top: 1rem;
        margin-bottom: 2rem;
        border: 1px solid #1a3e63;
    }
    
    /* Botones generales con tono naranja corporativo */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3.2em;
        font-weight: 600;
        background-color: #f26822;
        color: white;
        border: 2px solid #ffffff;
        transition: all 0.2s ease-in-out;
    }
    
    .stButton>button:hover {
        background-color: #ffffff;
        color: #f26822;
        border-color: #f26822;
    }

    /* Textos generales dentro de la tarjeta en color blanco */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, span {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #ffffff !important;
    }
    
    /* Títulos principales o subtítulos resaltados en Naranja */
    .stSubheader, h3 {
        color: #f26822 !important;
    }
    
    </style>
    """,
    unsafe_allow_html=True
)

# --- ENCABEZADO PROFESIONAL ---
col_logo, col_tit = st.columns([1, 3.5])
with col_logo:
    if os.path.exists("ESCUDO.png"):
        st.image("ESCUDO.png", width=75)
    elif os.path.exists("escudo.png"):
        st.image("escudo.png", width=75)
    else:
        st.markdown("<h1 style='text-align: center; margin: 0;'>🥚</h1>", unsafe_allow_html=True)
with col_tit:
    st.markdown("""
        <div style="padding-top: 5px;">
            <h2 style="margin: 0; color: #f26822 !important; font-size: 22px; font-weight: 800;">AVÍCOLA SANTA ISABEL</h2>
            <p style="margin: 0; color: #ffffff !important; font-size: 13px; font-weight: 600; letter-spacing: 0.5px;">SISTEMA DE GESTIÓN Y CONTROL</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- NAVEGACIÓN PRINCIPAL ENTRE SESIONES ---
if "sesion_principal" not in st.session_state:
    st.session_state.sesion_principal = "📦 Stock y Ventas"

c_prin1, c_prin2 = st.columns(2)
with c_prin1:
    if st.button("📦 Stock y Ventas", use_container_width=True):
        st.session_state.sesion_principal = "📦 Stock y Ventas"
with c_prin2:
    if st.button("📝 Registro Diario", use_container_width=True):
        st.session_state.sesion_principal = "📝 Registro Diario"

st.markdown("---")

# --- FUNCIONES DE BASE DE DATOS ---
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])

def inicializar_tabla_clientes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            cedula_nit TEXT,
            direccion TEXT,
            telefono TEXT,
            email TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def cargar_clientes():
    inicializar_tabla_clientes()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM clientes ORDER BY nombre ASC", conn)
    conn.close()
    return df

def guardar_cliente(nombre, cedula, direccion, telefono, email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO clientes (nombre, cedula_nit, direccion, telefono, email)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (nombre) DO UPDATE SET
            cedula_nit = EXCLUDED.cedula_nit,
            direccion = EXCLUDED.direccion,
            telefono = EXCLUDED.telefono,
            email = EXCLUDED.email;
    """, (nombre.strip().upper(), cedula, direccion, telefono, email))
    conn.commit()
    cur.close()
    conn.close()

def eliminar_cliente(cliente_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
    conn.commit()
    cur.close()
    conn.close()

def cargar_inventario():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM inventario ORDER BY galpon", conn)
    conn.close()
    return df.set_index('galpon')

def cargar_remisiones():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM remisiones ORDER BY id DESC", conn)
    conn.close()
    if not df.empty and 'num_remision' not in df.columns:
        df['num_remision'] = df['id']
    return df

def obtener_siguiente_num_remision():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(MAX(num_remision), 0) + 1 FROM remisiones")
        num = cur.fetchone()[0]
    except Exception:
        conn.rollback()
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM remisiones")
        num = cur.fetchone()[0]
    cur.close()
    conn.close()
    return num

def registrar_venta_multiple(cliente, cedula, direccion, telefono, email, conductor, num_remision, items_venta):
    conn = get_connection()
    cur = conn.cursor()
    fecha_actual = datetime.now()

    cur.execute("""
        SELECT column_name, is_generated, identity_generation 
        FROM information_schema.columns 
        WHERE table_name = 'remisiones';
    """)
    columnas_validas = set()
    for col_name, is_gen, id_gen in cur.fetchall():
        if is_gen != 'ALWAYS' and id_gen != 'ALWAYS':
            columnas_validas.add(col_name)

    for item in items_venta:
        clasificacion = item['Clasificación'].lower()
        cantidad = int(item['Cantidad (Huevos)'])
        subtotal = float(item['Subtotal ($)'])
        precio_u = float(item['Precio Unitario ($)'])
        galp_origen = item.get('Galpón', 'Galpón 1')

        datos_insert = {
            "num_remision": num_remision, "fecha_emision": fecha_actual,
            "cliente": cliente, "cedula_nit": cedula, "telefono": telefono,
            "destino": direccion, "email": email, "conductor": conductor,
            "tipo_huevo": clasificacion, "cantidad": cantidad,
            "precio_unitario": precio_u, "total": subtotal, "galpon": galp_origen
        }
        
        datos_reales = {k: v for k, v in datos_insert.items() if k in columnas_validas}

        if datos_reales:
            cols = ", ".join(datos_reales.keys())
            vals = tuple(datos_reales.values())
            placeholders = ", ".join(["%s"] * len(datos_reales))
            cur.execute(f"INSERT INTO remisiones ({cols}) VALUES ({placeholders})", vals)

        cur.execute(f"UPDATE inventario SET {clasificacion} = {clasificacion} - %s WHERE galpon = %s", (cantidad, galp_origen))

    conn.commit()
    cur.close()
    conn.close()

def actualizar_remision_completa(num_remision, cliente, cedula, direccion, telefono, email, conductor, df_viejos, items_nuevos):
    conn = get_connection()
    cur = conn.cursor()
    fecha_actual = datetime.now()

    for _, row in df_viejos.iterrows():
        c_tipo = str(row.get('tipo_huevo', 'a')).lower()
        c_cant = int(row.get('cantidad', 0))
        g_bd = row.get('galpon', 'Galpón 1')
        cur.execute(f"UPDATE inventario SET {c_tipo} = {c_tipo} + %s WHERE galpon = %s", (c_cant, g_bd))

    cur.execute("""
        SELECT column_name, is_generated, identity_generation 
        FROM information_schema.columns 
        WHERE table_name = 'remisiones';
    """)
    filas_cols = cur.fetchall()
    columnas_totales = [col[0] for col in filas_cols]
    columnas_validas = {c[0] for c in filas_cols if c[1] != 'ALWAYS' and c[2] != 'ALWAYS'}

    col_filtro = "num_remision" if "num_remision" in columnas_totales else "id"
    cur.execute(f"DELETE FROM remisiones WHERE {col_filtro} = %s", (num_remision,))

    for item in items_nuevos:
        clasif = item['Clasificación'].lower()
        cant = int(item['Cantidad (Huevos)'])
        subtotal = float(item['Subtotal ($)'])
        precio_u = float(item['Precio Unitario ($)'])
        galp_origen = item.get('Galpón', 'Galpón 1')

        datos_insert = {
            "num_remision": num_remision, "fecha_emision": fecha_actual,
            "cliente": cliente, "cedula_nit": cedula, "telefono": telefono,
            "destino": direccion, "email": email, "conductor": conductor,
            "tipo_huevo": clasif, "cantidad": cant,
            "precio_unitario": precio_u, "total": subtotal, "galpon": galp_origen
        }
        
        datos_reales = {k: v for k, v in datos_insert.items() if k in columnas_validas}

        if datos_reales:
            cols = ", ".join(datos_reales.keys())
            vals = tuple(datos_reales.values())
            placeholders = ", ".join(["%s"] * len(datos_reales))
            cur.execute(f"INSERT INTO remisiones ({cols}) VALUES ({placeholders})", vals)

        cur.execute(f"UPDATE inventario SET {clasif} = {clasif} - %s WHERE galpon = %s", (cant, galp_origen))

    conn.commit()
    cur.close()
    conn.close()

def eliminar_remision_completa(num_remision, df_viejos):
    conn = get_connection()
    cur = conn.cursor()
    for _, row in df_viejos.iterrows():
        c_tipo = str(row.get('tipo_huevo', 'a')).lower()
        c_cant = int(row.get('cantidad', 0))
        g_bd = row.get('galpon', 'Galpón 1')
        cur.execute(f"UPDATE inventario SET {c_tipo} = {c_tipo} + %s WHERE galpon = %s", (c_cant, g_bd))
        
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'remisiones';")
    cols_existentes = [r[0] for r in cur.fetchall()]
    col_filtro = "num_remision" if "num_remision" in cols_existentes else "id"

    cur.execute(f"DELETE FROM remisiones WHERE {col_filtro} = %s", (num_remision,))

    conn.commit()
    cur.close()
    conn.close()

def generar_pdf_remision(num_remision, fecha_str, conductor, cliente_datos, items_df, total_factura):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    
    header_data = [
        [
            Image("ESCUDO.png", width=60, height=60) if os.path.exists("ESCUDO.png") else "🛡️",
            Paragraph("<font size=16 color='#ffffff'><b>Remisión de Venta</b></font>", style_normal),
            Paragraph("<font size=9 color='#ffffff'><b>Avícola Santa Isabel</b><br/>NIT. 901.786.799 - 7<br/>Cel. 3102397244 - 3125588606</font>", style_normal)
        ]
    ]
    t_header = Table(header_data, colWidths=[80, 260, 200])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0f2942")),
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
        ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor("#0f2942")),
        ('LINEABOVE', (0,0), (-1,0), 1.5, colors.HexColor("#0f2942")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('GRID', (0,1), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#f8fafc"), colors.white]),
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
        ('LINEABOVE', (0,2), (-1,2), 1, colors.HexColor("#0f2942")),
    ]))
    story.append(t_totales)
    doc.build(story)
    buffer.seek(0)
    return buffer

# --- CONTROL DE CONTENIDO SEGÚN LA SESIÓN PRINCIPAL ---

if st.session_state.sesion_principal == "📦 Stock y Ventas":
    
    # Sub-navegación interna que SOLO se muestra al hacer clic en Stock y Ventas
    if "seccion_activa" not in st.session_state:
        st.session_state.seccion_activa = "📤 Remisiones"

    c_nav1, c_nav2, c_nav3, c_nav4 = st.columns(4)
    with c_nav1:
        if st.button("📤 Rem.", use_container_width=True): st.session_state.seccion_activa = "📤 Remisiones"
    with c_nav2:
        if st.button("👥 Clic.", use_container_width=True): st.session_state.seccion_activa = "👥 Clientes"
    with c_nav3:
        if st.button("📊 Stk.", use_container_width=True): st.session_state.seccion_activa = "📊 Stock"
    with c_nav4:
        if st.button("📜 Hist.", use_container_width=True): st.session_state.seccion_activa = "📜 Historial"

    st.markdown("---")

    if st.session_state.seccion_activa == "📤 Remisiones":
        df_inv = cargar_inventario()
        df_clientes = cargar_clientes()
        num_remision_actual = obtener_siguiente_num_remision()
        
        st.subheader(f"📋 Nueva Remisión No. {num_remision_actual:06d}")

        opciones_cli = ["-- Escribir cliente nuevo --"] + df_clientes["nombre"].tolist() if not df_clientes.empty else ["-- Escribir cliente nuevo --"]
        cliente_sel = st.selectbox("👤 Cargar Cliente Guardado", opciones_cli)

        val_nombre, val_cedula, val_dir, val_tel, val_email = "", "", "CHOACHI", "", ""

        if cliente_sel != "-- Escribir cliente nuevo --" and not df_clientes.empty:
            d_cli = df_clientes[df_clientes["nombre"] == cliente_sel].iloc[0]
            val_nombre = str(d_cli.get("nombre", ""))
            val_cedula = str(d_cli.get("cedula_nit", ""))
            val_dir = str(d_cli.get("direccion", "CHOACHI"))
            val_tel = str(d_cli.get("telefono", ""))
            val_email = str(d_cli.get("email", ""))

        cliente_nombre = st.text_input("Razón Social / Cliente *", value=val_nombre, placeholder="Ej. RAFAEL GARCIA")
        cedula_nit = st.text_input("Cédula / NIT", value=val_cedula, placeholder="Ej. 901.786.799-7")
        direccion = st.text_input("Dirección", value=val_dir)
        telefono = st.text_input("Teléfono", value=val_tel, placeholder="Ej. 3102397244")
        email = st.text_input("Email", value=val_email, placeholder="cliente@correo.com")
        conductor = st.text_input("Conductor", value="Ivan Herrera")
        
        guardar_cli_auto = st.checkbox("💾 Guardar/Actualizar este cliente en el directorio", value=True)

        st.markdown("### 🛒 Detalle del Despacho")
        st.caption("Añada los productos, especificando la clasificación y de qué galpón se descuenta.")
        
        opciones_clasif = ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"]
        opciones_galpones = ["Galpón 1", "Galpón 2", "Galpón 3"]
        
        df_base = pd.DataFrame([{
            "Clasificación": "a", 
            "Cantidad (Huevos)": 3000, 
            "Precio Unitario ($)": 370.0,
            "Galpón Origen": "Galpón 1"
        }])

        df_editado = st.data_editor(
            df_base,
            num_rows="dynamic",
            column_config={
                "Clasificación": st.column_config.SelectboxColumn("Clasificación", options=opciones_clasif, required=True),
                "Cantidad (Huevos)": st.column_config.NumberColumn("Cantidad", min_value=0, step=1, required=True),
                "Precio Unitario ($)": st.column_config.NumberColumn("Precio ($)", min_value=0.0, step=1.0, format="$%.2f", required=True),
                "Galpón Origen": st.column_config.SelectboxColumn("Galpón Origen", options=opciones_galpones, required=True)
            },
            use_container_width=True
        )

        items_validos = df_editado[df_editado["Cantidad (Huevos)"] > 0].copy()

        if not items_validos.empty:
            items_validos["Subtotal ($)"] = items_validos["Cantidad (Huevos)"] * items_validos["Precio Unitario ($)"]
            
            df_agrupado_pdf = items_validos.groupby("Clasificación").agg({
                "Cantidad (Huevos)": "sum",
                "Precio Unitario ($)": "mean",
                "Subtotal ($)": "sum"
            }).reset_index()

            total_factura = items_validos["Subtotal ($)"].sum()
            st.markdown(f"""
                <div style="background-color: #f26822; color: white; padding: 12px; border-radius: 8px; text-align: right; margin-top: 10px; border-left: 5px solid #ffffff;">
                    <h3 style="margin: 0; color: white !important; font-size: 18px;">TOTAL FACTURA: ${total_factura:,.2f}</h3>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🚀 Confirmar y Generar Remisión"):
                if not cliente_nombre.strip():
                    st.error("Por favor ingresa el Nombre del cliente.")
                else:
                    errores_stock = []
                    stock_acumulado_uso = {}
                    for _, fila in items_validos.iterrows():
                        c_clasif = fila["Clasificación"]
                        c_cant = int(fila["Cantidad (Huevos)"])
                        g_orig = fila["Galpón Origen"]
                        
                        key_st = (g_orig, c_clasif)
                        stock_acumulado_uso[key_st] = stock_acumulado_uso.get(key_st, 0) + c_cant

                    for (g_orig, c_clasif), c_cant in stock_acumulado_uso.items():
                        stock_disp = df_inv.loc[g_orig, c_clasif]
                        if c_cant > stock_disp:
                            errores_stock.append(f"Stock insuficiente en {g_orig} para {c_clasif.upper()}. Disponible: {stock_disp}, Solicitado: {c_cant}")

                    if errores_stock:
                        for err in errores_stock: st.error(err)
                    else:
                        if guardar_cli_auto:
                            guardar_cliente(cliente_nombre, cedula_nit, direccion, telefono, email)

                        items_dict = []
                        for _, row in items_validos.iterrows():
                            items_dict.append({
                                'Clasificación': row['Clasificación'],
                                'Cantidad (Huevos)': row['Cantidad (Huevos)'],
                                'Precio Unitario ($)': row['Precio Unitario ($)'],
                                'Subtotal ($)': row['Subtotal ($)'],
                                'Galpón': row['Galpón Origen']
                            })

                        registrar_venta_multiple(cliente_nombre, cedula_nit, direccion, telefono, email, conductor, num_remision_actual, items_dict)
                        st.success(f"¡Remisión No. {num_remision_actual:06d} guardada con éxito!")
                        
                        datos_cliente = {"nombre": cliente_nombre, "cedula": cedula_nit, "direccion": direccion, "telefono": telefono, "email": email}
                        pdf_buffer = generar_pdf_remision(num_remision_actual, datetime.now().strftime("%d/%m/%Y"), conductor, datos_cliente, df_agrupado_pdf, total_factura)
                        st.download_button(label="📄 Descargar Remisión PDF", data=pdf_buffer, file_name=f"Remision_{num_remision_actual:06d}.pdf", mime="application/pdf")

    elif st.session_state.seccion_activa == "👥 Clientes":
        st.subheader("👥 Directorio de Clientes")
        
        tab_nuevo, tab_lista = st.tabs(["➕ Agregar Cliente", "📋 Lista de Clientes"])
        
        with tab_nuevo:
            with st.form(key="form_nuevo_cliente"):
                st.markdown("### Datos del Cliente")
                c_nom = st.text_input("Nombre / Razón Social *", placeholder="Ej. RAFAEL GARCIA")
                c_ced = st.text_input("Cédula / NIT", placeholder="Ej. 901.786.799-7")
                c_dir = st.text_input("Dirección", value="CHOACHI")
                c_tel = st.text_input("Teléfono", placeholder="Ej. 3102397244")
                c_em = st.text_input("Email", placeholder="cliente@correo.com")
                
                if st.form_submit_button("💾 Guardar Cliente"):
                    if not c_nom.strip():
                        st.error("El nombre del cliente es obligatorio.")
                    else:
                        guardar_cliente(c_nom, c_ced, c_dir, c_tel, c_em)
                        st.success(f"¡Cliente {c_nom.upper()} guardado exitosamente!")
                        st.rerun()

        with tab_lista:
            df_cli = cargar_clientes()
            if df_cli.empty:
                st.info("No hay clientes registrados en la base de datos.")
            else:
                st.caption(f"Total registrados: {len(df_cli)}")
                for _, r_cli in df_cli.iterrows():
                    id_c = r_cli['id']
                    nom_c = r_cli['nombre']
                    ced_c = r_cli.get('cedula_nit', '')
                    tel_c = r_cli.get('telefono', '')
                    dir_c = r_cli.get('direccion', '')
                    em_c = r_cli.get('email', '')

                    with st.expander(f"👤 {nom_c} ({ced_c if ced_c else 'Sin Cédula/NIT'})"):
                        st.write(f"**Teléfono:** {tel_c}")
                        st.write(f"**Dirección:** {dir_c}")
                        st.write(f"**Email:** {em_c}")
                        if st.button(f"🗑️ Eliminar {nom_c}", key=f"del_cli_{id_c}"):
                            eliminar_cliente(id_c)
                            st.warning(f"Cliente {nom_c} eliminado.")
                            st.rerun()

    elif st.session_state.seccion_activa == "📊 Stock":
        st.subheader("📦 Stock Actual en Granja")
        st.markdown("Inventario disponible distribuido por galpón.")
        st.dataframe(cargar_inventario(), use_container_width=True)

    elif st.session_state.seccion_activa == "📜 Historial":
        st.subheader("📜 Historial de Remisiones")
        df_historial = cargar_remisiones()
        
        if df_historial.empty:
            st.info("No hay remisiones registradas en la base de datos todavía.")
        else:
            busqueda = st.text_input("🔍 Buscar cliente o N° Remisión", placeholder="Ej. RAFAEL GARCIA o 000001")
            
            if busqueda.strip():
                df_filtrado = df_historial[
                    df_historial['cliente'].astype(str).str.contains(busqueda, case=False, na=False) |
                    df_historial['num_remision'].astype(str).str.contains(busqueda, case=False, na=False)
                ]
            else:
                df_filtrado = df_historial

            if df_filtrado.empty:
                st.warning("No se encontraron remisiones que coincidan con la búsqueda.")
            else:
                nums_remision = sorted(df_filtrado['num_remision'].dropna().unique().astype(int), reverse=True)
                st.caption(f"Mostrando {len(nums_remision)} remisión(es)")

                for num_sel in nums_remision:
                    df_rem = df_historial[df_historial['num_remision'] == num_sel]
                    f_sel = df_rem.iloc[0]
                    
                    cli_nombre = str(f_sel.get('cliente', 'Cliente sin nombre'))
                    tot_val = df_rem['total'].sum() if 'total' in df_rem.columns else 0.0
                    f_emision_val = f_sel.get('fecha_emision', datetime.now())
                    fecha_str = f_emision_val[:10] if isinstance(f_emision_val, str) else pd.to_datetime(f_emision_val).strftime("%d/%m/%Y")
                    
                    titulo_expander = f"📄 Remisión No. {num_sel:06d} — {cli_nombre.upper()} | ${tot_val:,.2f} ({fecha_str})"
                    
                    with st.expander(titulo_expander):
                        tab_pdf, tab_editar = st.tabs(["👁️ Ver / Descargar PDF", "✏️ Editar o Eliminar"])
                        
                        items_actuales = []
                        for _, row in df_rem.iterrows():
                            items_actuales.append({
                                "Clasificación": str(row.get('tipo_huevo', 'a')).upper(),
                                "Cantidad (Huevos)": int(row.get('cantidad', 0)),
                                "Precio Unitario ($)": float(row.get('precio_unitario', 0.0)),
                                "Subtotal ($)": float(row.get('total', 0.0)),
                                "Galpón Origen": str(row.get('galpon', 'Galpón 1'))
                            })
                        df_items_original = pd.DataFrame(items_actuales)
                        
                        df_items_pdf = df_items_original.groupby("Clasificación").agg({
                            "Cantidad (Huevos)": "sum",
                            "Precio Unitario ($)": "mean",
                            "Subtotal ($)": "sum"
                        }).reset_index()
                        
                        cli_datos = {
                            "nombre": cli_nombre,
                            "cedula": str(f_sel.get('cedula_nit', '')),
                            "direccion": str(f_sel.get('destino', '')),
                            "telefono": str(f_sel.get('telefono', '')),
                            "email": str(f_sel.get('email', ''))
                        }
                        conductor_val = str(f_sel.get('conductor', 'Ivan Herrera'))

                        with tab_pdf:
                            pdf_buf = generar_pdf_remision(num_sel, fecha_str, conductor_val, cli_datos, df_items_pdf, tot_val)
                            
                            c_inf1, c_inf2 = st.columns(2)
                            with c_inf1:
                                st.write(f"**Cliente:** {cli_nombre.upper()}")
                                st.write(f"**Cédula/NIT:** {cli_datos['cedula']}")
                                st.write(f"**Fecha:** {fecha_str}")
                            with c_inf2:
                                st.write(f"**Teléfono:** {cli_datos['telefono']}")
                                st.write(f"**Dirección:** {cli_datos['direccion']}")
                                st.write(f"**Conductor:** {conductor_val}")
                            
                            st.dataframe(
                                df_items_pdf[["Clasificación", "Cantidad (Huevos)", "Precio Unitario ($)", "Subtotal ($)"]],
                                use_container_width=True,
                                hide_index=True
                            )
                            st.markdown(f"#### **Total: ${tot_val:,.2f}**")
                            
                            st.download_button(
                                label=f"📥 Descargar PDF Remisión No. {num_sel:06d}",
                                data=pdf_buf,
                                file_name=f"Remision_{num_sel:06d}_{cli_nombre}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_{num_sel}",
                                use_container_width=True
                            )

                        with tab_editar:
                            with st.form(key=f"form_editar_{num_sel}"):
                                c_cliente = st.text_input("Cliente", value=cli_datos['nombre'], key=f"cli_{num_sel}")
                                c_cedula = st.text_input("Cédula / NIT", value=cli_datos['cedula'], key=f"ced_{num_sel}")
                                c_dir = st.text_input("Dirección", value=cli_datos['direccion'], key=f"dir_{num_sel}")
                                c_tel = st.text_input("Teléfono", value=cli_datos['telefono'], key=f"tel_{num_sel}")
                                c_email = st.text_input("Email", value=cli_datos['email'], key=f"em_{num_sel}")
                                c_cond = st.text_input("Conductor", value=conductor_val, key=f"cond_{num_sel}")
                                
                                st.markdown("### 🛒 Productos")
                                df_base_edit = df_items_original[["Clasificación", "Cantidad (Huevos)", "Precio Unitario ($)", "Galpón Origen"]].copy()
                                df_base_edit["Clasificación"] = df_base_edit["Clasificación"].str.lower()
                                opciones_clasif = ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"]
                                opciones_galpones = ["Galpón 1", "Galpón 2", "Galpón 3"]
                                
                                df_editado = st.data_editor(
                                    df_base_edit,
                                    num_rows="dynamic",
                                    column_config={
                                        "Clasificación": st.column_config.SelectboxColumn("Clasificación", options=opciones_clasif, required=True),
                                        "Cantidad (Huevos)": st.column_config.NumberColumn("Cantidad", min_value=0, step=1, required=True),
                                        "Precio Unitario ($)": st.column_config.NumberColumn("Precio ($)", min_value=0.0, step=1.0, format="$%.2f", required=True),
                                        "Galpón Origen": st.column_config.SelectboxColumn("Galpón Origen", options=opciones_galpones, required=True)
                                    },
                                    use_container_width=True,
                                    key=f"editor_{num_sel}"
                                )
                                
                                col_btn1, col_btn2 = st.columns(2)
                                with col_btn1:
                                    submit_actualizar = st.form_submit_button("💾 Actualizar Cambios")
                                with col_btn2:
                                    submit_eliminar = st.form_submit_button("🗑️ Eliminar Remisión")
                                
                                if submit_actualizar:
                                    items_validos = df_editado[df_editado["Cantidad (Huevos)"] > 0].copy()
                                    if items_validos.empty:
                                        st.error("Debe haber al menos un producto válido.")
                                    else:
                                        items_validos["Subtotal ($)"] = items_validos["Cantidad (Huevos)"] * items_validos["Precio Unitario ($)"]
                                        items_dict = []
                                        for _, row in items_validos.iterrows():
                                            items_dict.append({
                                                'Clasificación': row['Clasificación'],
                                                'Cantidad (Huevos)': row['Cantidad (Huevos)'],
                                                'Precio Unitario ($)': row['Precio Unitario ($)'],
                                                'Subtotal ($)': row['Subtotal ($)'],
                                                'Galpón': row['Galpón Origen']
                                            })
                                        
                                        actualizar_remision_completa(
                                            num_sel, c_cliente, c_cedula, c_dir, c_tel, c_email, c_cond, df_rem, items_dict
                                        )
                                        st.success(f"¡Remisión No. {num_sel:06d} actualizada con éxito!")
                                        st.rerun()
                                
                                if submit_eliminar:
                                    eliminar_remision_completa(num_sel, df_rem)
                                    st.warning(f"Remisión No. {num_sel:06d} eliminada correctamente.")
                                    st.rerun()

elif st.session_state.sesion_principal == "📝 Registro Diario":
    st.subheader("📝 Registro Diario de Producción y Galpones")
    st.markdown("Esta sección está lista para que registremos y alimentemos la información diaria próximamente.")
    
    st.info("💡 Aquí podremos programar las entradas de postura, mortalidad, alimento o novedades diarias.")
    
    with st.form(key="form_registro_diario_provisional"):
        fecha_reg = st.date_input("Fecha de Registro", datetime.now())
        galpon_reg = st.selectbox("Galpón", ["Galpón 1", "Galpón 2", "Galpón 3"])
        observacion = st.text_area("Observaciones / Novedades", placeholder="Escribe aquí notas adicionales...")
        
        if st.form_submit_button("Guardar Registro Diario"):
            st.success("¡Espacio preparado con éxito para recibir la lógica de registro diario!")
