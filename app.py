import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import datetime, date
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

# --- ICONO PERSONALIZADO ---
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
    </script>
""", unsafe_allow_html=True)

# --- ESTILOS CSS ---
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stApp { background-color: #c8d6e5 !important; }
    
    .block-container {
        padding-top: 1.5rem; padding-bottom: 5rem;
        padding-left: 1.2rem; padding-right: 1.2rem;
        max-width: 540px;
        background-color: #0f2942 !important;
        border-radius: 16px;
        box-shadow: 0 10px 35px rgba(15, 41, 66, 0.3);
        margin-top: 1rem; margin-bottom: 2rem;
        border: 1px solid #1a3e63;
    }
    
    .stButton>button {
        width: 100%; border-radius: 10px; height: 3.2em;
        font-weight: 600; background-color: #f26822;
        color: white; border: 2px solid #ffffff;
        transition: all 0.2s ease-in-out;
    }
    
    .stButton>button:hover {
        background-color: #ffffff; color: #f26822; border-color: #f26822;
    }

    h1, h2, h3, h4, p, label, .stMarkdown, span, .stSubheader {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #ffffff !important;
    }
    
    .stSubheader { color: #f26822 !important; font-weight: bold !important; }
    </style>
    """,
    unsafe_allow_html=True
)

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

def inicializar_tablas_cartera():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cartera (
            num_remision INT PRIMARY KEY,
            cliente TEXT,
            total NUMERIC,
            saldo NUMERIC,
            estado TEXT DEFAULT 'PENDIENTE'
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS abonos_cartera (
            id SERIAL PRIMARY KEY,
            num_remision INT,
            fecha_abono TIMESTAMP,
            monto NUMERIC,
            comprobante BYTEA,
            nombre_comprobante TEXT
        );
    """)
    try:
        cur.execute("ALTER TABLE abonos_cartera ADD COLUMN IF NOT EXISTS comprobante BYTEA;")
        cur.execute("ALTER TABLE abonos_cartera ADD COLUMN IF NOT EXISTS nombre_comprobante TEXT;")
    except Exception:
        conn.rollback()
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

def registrar_entrada_inventario(galpon, items_entrada):
    conn = get_connection()
    cur = conn.cursor()
    for item in items_entrada:
        clasificacion = item['Clasificación'].lower()
        cantidad = int(item['Cantidad'])
        cur.execute(f"UPDATE inventario SET {clasificacion} = {clasificacion} + %s WHERE galpon = %s", (cantidad, galpon))
    conn.commit()
    cur.close()
    conn.close()

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

def cargar_cartera():
    inicializar_tablas_cartera()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM cartera ORDER BY num_remision DESC", conn)
    conn.close()
    return df

def registrar_abono(num_remision, monto_abono, comprobante_bytes=None, nombre_comprobante=None):
    inicializar_tablas_cartera()
    conn = get_connection()
    cur = conn.cursor()
    fecha_actual = datetime.now()
    
    comp_binary = psycopg2.Binary(comprobante_bytes) if comprobante_bytes else None

    cur.execute("""
        INSERT INTO abonos_cartera (num_remision, fecha_abono, monto, comprobante, nombre_comprobante)
        VALUES (%s, %s, %s, %s, %s)
    """, (num_remision, fecha_actual, monto_abono, comp_binary, nombre_comprobante))
    
    cur.execute("SELECT total FROM cartera WHERE num_remision = %s", (num_remision,))
    res = cur.fetchone()
    if res:
        total = float(res[0])
        cur.execute("SELECT COALESCE(SUM(monto), 0) FROM abonos_cartera WHERE num_remision = %s", (num_remision,))
        total_abonos = float(cur.fetchone()[0])
        nuevo_saldo = max(0.0, total - total_abonos)
        nuevo_estado = 'PAGADA' if nuevo_saldo <= 0 else 'PENDIENTE'
        
        cur.execute("""
            UPDATE cartera SET saldo = %s, estado = %s WHERE num_remision = %s
        """, (nuevo_saldo, nuevo_estado, num_remision))
        
    conn.commit()
    cur.close()
    conn.close()

def obtener_abonos_con_comprobante(num_remision):
    inicializar_tablas_cartera()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, fecha_abono, monto, comprobante, nombre_comprobante FROM abonos_cartera WHERE num_remision = %s ORDER BY fecha_abono DESC", (num_remision,))
    filas = cur.fetchall()
    cur.close()
    conn.close()
    return filas

def registrar_venta_multiple(cliente, cedula, direccion, telefono, email, conductor, num_remision, fecha_remision, items_venta):
    inicializar_tablas_cartera()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT column_name, is_generated, identity_generation 
        FROM information_schema.columns 
        WHERE table_name = 'remisiones';
    """)
    columnas_validas = set()
    for col_name, is_gen, id_gen in cur.fetchall():
        if is_gen != 'ALWAYS' and id_gen != 'ALWAYS':
            columnas_validas.add(col_name)

    total_venta_acumulado = 0.0

    for item in items_venta:
        clasificacion = item['Clasificación'].lower()
        cantidad = int(item['Cantidad (Huevos)'])
        subtotal = float(item['Subtotal ($)'])
        precio_u = float(item['Precio Unitario ($)'])
        galp_origen = item.get('Galpón', 'Galpón 1')
        total_venta_acumulado += subtotal

        datos_insert = {
            "num_remision": num_remision, "fecha_emision": fecha_remision,
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

    cur.execute("""
        INSERT INTO cartera (num_remision, cliente, total, saldo, estado)
        VALUES (%s, %s, %s, %s, 'PENDIENTE')
        ON CONFLICT (num_remision) DO UPDATE SET
            cliente = EXCLUDED.cliente,
            total = EXCLUDED.total,
            saldo = EXCLUDED.saldo;
    """, (num_remision, cliente.strip().upper(), total_venta_acumulado, total_venta_acumulado))

    conn.commit()
    cur.close()
    conn.close()

def actualizar_remision_completa(num_remision, cliente, cedula, direccion, telefono, email, conductor, fecha_remision, df_viejos, items_nuevos):
    inicializar_tablas_cartera()
    conn = get_connection()
    cur = conn.cursor()

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

    nuevo_total_calc = 0.0
    for item in items_nuevos:
        clasif = item['Clasificación'].lower()
        cant = int(item['Cantidad (Huevos)'])
        subtotal = float(item['Subtotal ($)'])
        precio_u = float(item['Precio Unitario ($)'])
        galp_origen = item.get('Galpón', 'Galpón 1')
        nuevo_total_calc += subtotal

        datos_insert = {
            "num_remision": num_remision, "fecha_emision": fecha_remision,
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

    cur.execute("SELECT COALESCE(SUM(monto), 0) FROM abonos_cartera WHERE num_remision = %s", (num_remision,))
    total_abonos = float(cur.fetchone()[0])
    nuevo_saldo = max(0.0, nuevo_total_calc - total_abonos)
    nuevo_estado = 'PAGADA' if nuevo_saldo <= 0 else 'PENDIENTE'

    cur.execute("""
        INSERT INTO cartera (num_remision, cliente, total, saldo, estado)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (num_remision) DO UPDATE SET
            cliente = EXCLUDED.cliente,
            total = EXCLUDED.total,
            saldo = EXCLUDED.saldo,
            estado = EXCLUDED.estado;
    """, (num_remision, cliente.strip().upper(), nuevo_total_calc, nuevo_saldo, nuevo_estado))

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
    cur.execute("DELETE FROM cartera WHERE num_remision = %s", (num_remision,))
    cur.execute("DELETE FROM abonos_cartera WHERE num_remision = %s", (num_remision,))

    conn.commit()
    cur.close()
    conn.close()

def generar_pdf_remision(num_remision, fecha_str, conductor, cliente_datos, items_df, total_factura):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados limpios y profesionales
    style_title = ParagraphStyle('TitleStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor("#0f2942"))
    style_subtitle = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#0f2942"))
    style_normal = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333"))
    style_bold = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#333333"))
    style_right = ParagraphStyle('RightStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333"), alignment=2)
    style_right_bold = ParagraphStyle('RightBoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#333333"), alignment=2)
    style_th = ParagraphStyle('THStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=1)
    style_th_left = ParagraphStyle('THLeftStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=0)
    style_th_right = ParagraphStyle('THRightStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=2)

    num_str = f"{num_remision:06d}"

    # --- ENCABEZADO PRINCIPAL (Estilo exacto de la imagen) ---
    img_logo = Image("ESCUDO.png", width=50, height=50) if os.path.exists("ESCUDO.png") else Paragraph("<b>🥚</b>", style_title)
    
    header_data = [
        [
            img_logo,
            Paragraph("<b>AGROAVICOLA SANTA ISABEL</b><br/><font size=8>NIT. 901.786.799-7<br/>Cel. 3102397244-3125588606</font>", style_normal),
            Paragraph(f"<b>Remisión No.</b><br/><font size=12 color='#f26822'><b>{num_str}</b></font>", style_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[60, 314, 160])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 5))

    # --- DATOS GENERALES Y CLIENTE ---
    info_data = [
        [
            Paragraph("<b>Fecha</b>", style_bold),
            Paragraph(f": {fecha_str}", style_normal),
            Paragraph("<b>Datos del cliente</b>", style_subtitle),
            ""
        ],
        [
            Paragraph("<b>Conductor</b>", style_bold),
            Paragraph(f": {conductor}", style_normal),
            Paragraph("<b>Nombre/Razón Social</b>", style_bold),
            Paragraph(f": {cliente_datos['nombre']}", style_normal)
        ],
        [
            Paragraph("", style_normal),
            Paragraph("", style_normal),
            Paragraph("<b>Cédula/NIT</b>", style_bold),
            Paragraph(f": {cliente_datos['cedula']}", style_normal)
        ],
        [
            Paragraph("", style_normal),
            Paragraph("", style_normal),
            Paragraph("<b>Dirección</b>", style_bold),
            Paragraph(f": {cliente_datos['direccion']}", style_normal)
        ],
        [
            Paragraph("", style_normal),
            Paragraph("", style_normal),
            Paragraph("<b>Teléfono</b>", style_bold),
            Paragraph(f": {cliente_datos['telefono']}", style_normal)
        ],
        [
            Paragraph("", style_normal),
            Paragraph("", style_normal),
            Paragraph("<b>Email</b>", style_bold),
            Paragraph(f": {cliente_datos['email']}", style_normal)
        ],
    ]
    t_info = Table(info_data, colWidths=[70, 160, 110, 194])
    t_info.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 15))

    # --- TABLA DE ITEMS ---
    table_data = [[
        Paragraph("Descripción", style_th_left),
        Paragraph("Cantidad", style_th),
        Paragraph("Valor Unitario", style_th_right),
        Paragraph("Valor total", style_th_right)
    ]]
    
    for _, fila in items_df.iterrows():
        table_data.append([
            Paragraph(str(fila["Clasificación"]).upper(), style_normal),
            Paragraph(f"{int(fila['Cantidad (Huevos)']):,}".replace(",", "."), style_right),
            Paragraph(f"$ {fila['Precio Unitario ($)']:,.0f}".replace(",", "."), style_right),
            Paragraph(f"$ {fila['Subtotal ($)']:,.0f}".replace(",", "."), style_right)
        ])

    t_items = Table(table_data, colWidths=[140, 100, 130, 164])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f2942")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#f8fafc"), colors.white]),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    # --- TOTALES ---
    totales_data = [
        [Paragraph("<b>Subtotal</b>", style_right), Paragraph(f"<b>$ {total_factura:,.2f}</b>".replace(",", "X").replace(".", ",").replace("X", "."), style_right_bold)],
        [Paragraph("<b>IVA</b>", style_right), Paragraph("<b>$ 0,00</b>", style_right_bold)],
        [Paragraph("<b>Total</b>", style_right), Paragraph(f"<b>$ {total_factura:,.2f}</b>".replace(",", "X").replace(".", ",").replace("X", "."), style_right_bold)]
    ]
    t_totales = Table(totales_data, colWidths=[374, 160])
    t_totales.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LINEABOVE', (0,2), (-1,2), 1, colors.HexColor("#0f2942")),
    ]))
    story.append(t_totales)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# --- ENCABEZADO ---
col_logo, col_tit = st.columns([1, 3.5])
with col_logo:
    if os.path.exists("ESCUDO.png"): st.image("ESCUDO.png", width=75)
    else: st.markdown("<h1 style='margin: 0;'>🥚</h1>", unsafe_allow_html=True)
with col_tit:
    st.markdown('<h2 style="margin: 0; color: #f26822 !important;">AVÍCOLA SANTA ISABEL</h2><p style="margin: 0;">SISTEMA DE GESTIÓN Y CONTROL</p>', unsafe_allow_html=True)

st.markdown("---")

# --- LÓGICA DE NAVEGACIÓN PRINCIPAL ---
if "sesion_principal" not in st.session_state:
    st.session_state.sesion_principal = None

if st.session_state.sesion_principal is None:
    c_prin1, c_prin2 = st.columns(2)
    with c_prin1:
        if st.button("📦 Stock y Ventas", use_container_width=True):
            st.session_state.sesion_principal = "📦 Stock y Ventas"
            st.session_state.seccion_activa = "📥 Entradas"
            st.rerun()
    with c_prin2:
        if st.button("📝 Registro Diario", use_container_width=True):
            st.session_state.sesion_principal = "📝 Registro Diario"
            st.rerun()
else:
    if st.button("⬅️ Regresar al Menú Principal"):
        st.session_state.sesion_principal = None
        st.rerun()

# --- CONTENIDO DE LAS SESIONES ---
if st.session_state.sesion_principal == "📦 Stock y Ventas":
    c_nav1, c_nav2, c_nav3, c_nav4, c_nav5, c_nav6 = st.columns(6)
    with c_nav1:
        if st.button("📥 Entr.", use_container_width=True): st.session_state.seccion_activa = "📥 Entradas"
    with c_nav2:
        if st.button("👥 Clic.", use_container_width=True): st.session_state.seccion_activa = "👥 Clientes"
    with c_nav3:
        if st.button("📤 Vent.", use_container_width=True): st.session_state.seccion_activa = "📤 Remisiones"
    with c_nav4:
        if st.button("💰 Cart.", use_container_width=True): st.session_state.seccion_activa = "💰 Cartera"
    with c_nav5:
        if st.button("📊 Stk.", use_container_width=True): st.session_state.seccion_activa = "📊 Stock"
    with c_nav6:
        if st.button("📜 Hist.", use_container_width=True): st.session_state.seccion_activa = "📜 Historial"

    st.markdown("---")

    if st.session_state.seccion_activa == "📥 Entradas":
        st.subheader("📥 Entrada de Producción / Clasificación")
        st.caption("Registre los huevos recolectados y clasificados para sumarlos al inventario del galpón correspondiente.")
        
        galpon_destino = st.selectbox("Seleccione el Galpón de Destino", ["Galpón 1", "Galpón 2", "Galpón 3"])
        
        opciones_clasif = ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"]
        df_base_entrada = pd.DataFrame([
            {"Clasificación": "a", "Cantidad": 1000}
        ])
        
        df_entrada_editado = st.data_editor(
            df_base_entrada,
            num_rows="dynamic",
            column_config={
                "Clasificación": st.column_config.SelectboxColumn("Clasificación", options=opciones_clasif, required=True),
                "Cantidad": st.column_config.NumberColumn("Cantidad (Huevos)", min_value=1, step=1, required=True)
            },
            use_container_width=True,
            key="editor_entradas_stock"
        )
        
        if st.button("➕ Registrar Entrada al Inventario"):
            entradas_validas = df_entrada_editado[df_entrada_editado["Cantidad"] > 0].copy()
            if entradas_validas.empty:
                st.warning("Debe ingresar al menos un ítem con cantidad mayor a 0.")
            else:
                lista_items_entrada = []
                for _, r in entradas_validas.iterrows():
                    lista_items_entrada.append({
                        "Clasificación": r["Clasificación"],
                        "Cantidad": int(r["Cantidad"])
                    })
                registrar_entrada_inventario(galpon_destino, lista_items_entrada)
                st.success(f"¡Entrada registrada correctamente en {galpon_destino}!")
                st.rerun()

    elif st.session_state.seccion_activa == "👥 Clientes":
        st.subheader("👥 Directorio de Clientes")
        tab_nuevo, tab_lista = st.tabs(["➕ Agregar Cliente", "📋 Lista de Clientes"])
        
        with tab_nuevo:
            with st.form(key="form_nuevo_cliente"):
                c_nom = st.text_input("Nombre / Razón Social *")
                c_ced = st.text_input("Cédula / NIT")
                c_dir = st.text_input("Dirección", value="CHOACHI")
                c_tel = st.text_input("Teléfono")
                c_em = st.text_input("Email")
                if st.form_submit_button("💾 Guardar Cliente"):
                    if not c_nom.strip():
                        st.error("El nombre es obligatorio.")
                    else:
                        guardar_cliente(c_nom, c_ced, c_dir, c_tel, c_em)
                        st.success(f"¡Cliente {c_nom.upper()} guardado!")
                        st.rerun()

        with tab_lista:
            df_cli = cargar_clientes()
            if df_cli.empty:
                st.info("No hay clientes registrados.")
            else:
                for _, r_cli in df_cli.iterrows():
                    id_c = r_cli['id']
                    nom_c = r_cli['nombre']
                    with st.expander(f"👤 {nom_c} ({r_cli.get('cedula_nit', '')})"):
                        st.write(f"**Teléfono:** {r_cli.get('telefono', '')}")
                        st.write(f"**Dirección:** {r_cli.get('direccion', '')}")
                        if st.button(f"🗑️ Eliminar {nom_c}", key=f"del_cli_{id_c}"):
                            eliminar_cliente(id_c)
                            st.warning("Cliente eliminado.")
                            st.rerun()

    elif st.session_state.seccion_activa == "📤 Remisiones":
        df_inv = cargar_inventario()
        df_clientes = cargar_clientes()
        num_remision_actual = obtener_siguiente_num_remision()
        
        st.subheader(f"📋 Nueva Remisión No. {num_remision_actual:06d}")

        # --- Selector de Fecha editable ---
        fecha_remision = st.date_input("📅 Fecha de la Remisión", value=date.today())

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

                        registrar_venta_multiple(cliente_nombre, cedula_nit, direccion, telefono, email, conductor, num_remision_actual, fecha_remision, items_dict)
                        st.success(f"¡Remisión No. {num_remision_actual:06d} guardada y deuda creada en cartera con éxito!")
                        
                        # Formato de fecha en español idéntico a tu ejemplo
                        dias_sem = {'Monday':'lunes', 'Tuesday':'martes', 'Wednesday':'miércoles', 'Thursday':'jueves', 'Friday':'viernes', 'Saturday':'sábado', 'Sunday':'domingo'}
                        meses_anio = {1:'enero', 2:'febrero', 3:'marzo', 4:'abril', 5:'mayo', 6:'junio', 7:'julio', 8:'agosto', 9:'septiembre', 10:'octubre', 11:'noviembre', 12:'diciembre'}
                        dia_txt = dias_sem.get(fecha_remision.strftime('%A'), '')
                        mes_txt = meses_anio.get(fecha_remision.month, '')
                        fecha_formateada_str = f"{dia_txt}, {fecha_remision.day} de {mes_txt} de {fecha_remision.year}"

                        datos_cliente = {"nombre": cliente_nombre, "cedula": cedula_nit, "direccion": direccion, "telefono": telefono, "email": email}
                        pdf_buffer = generar_pdf_remision(num_remision_actual, fecha_formateada_str, conductor, datos_cliente, df_agrupado_pdf, total_factura)
                        st.download_button(label="📄 Descargar Remisión PDF", data=pdf_buffer, file_name=f"Remision_{num_remision_actual:06d}.pdf", mime="application/pdf")

    elif st.session_state.seccion_activa == "💰 Cartera":
        st.subheader("💰 Control de Cartera y Abonos")
        st.caption("Gestione las deudas pendientes por factura, registre los abonos de los clientes y adjunte sus comprobantes de pago.")

        df_cartera = cargar_cartera()
        if df_cartera.empty:
            st.info("No hay deudas ni facturas registradas en cartera.")
        else:
            total_por_cobrar = df_cartera[df_cartera['estado'] == 'PENDIENTE']['saldo'].astype(float).sum()
            total_general_facturado = df_cartera['total'].astype(float).sum()

            st.markdown(f"""
                <div style="background-color: #1a3e63; color: white; padding: 12px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #f26822;">
                    <p style="margin: 0; font-size: 14px;">Total Facturado: <b>${total_general_facturado:,.2f}</b></p>
                    <p style="margin: 0; font-size: 16px; color: #f26822 !important;">Total Pendiente por Cobrar: <b>${total_por_cobrar:,.2f}</b></p>
                </div>
            """, unsafe_allow_html=True)

            busqueda_cartera = st.text_input("🔍 Buscar cliente o N° Remisión en Cartera", placeholder="Ej. RAFAEL GARCIA")
            df_cart_filtrado = df_cartera[
                df_cartera['cliente'].astype(str).str.contains(busqueda_cartera, case=False, na=False) |
                df_cartera['num_remision'].astype(str).str.contains(busqueda_cartera, case=False, na=False)
            ] if busqueda_cartera.strip() else df_cartera

            if df_cart_filtrado.empty:
                st.warning("No se encontraron registros de cartera con ese criterio.")
            else:
                for _, row_cart in df_cart_filtrado.iterrows():
                    num_r = int(row_cart['num_remision'])
                    cli_c = str(row_cart['cliente'])
                    tot_c = float(row_cart['total'])
                    saldo_c = float(row_cart['saldo'])
                    estado_c = str(row_cart['estado'])

                    color_estado = "🟢 PAGADA" if estado_c == 'PAGADA' else "🔴 PENDIENTE"

                    with st.expander(f"Remisión N° {num_r:06d} — {cli_c} | Saldo: ${saldo_c:,.2f} ({color_estado})"):
                        st.write(f"**Total Factura:** ${tot_c:,.2f}")
                        st.write(f"**Saldo Pendiente:** ${saldo_c:,.2f}")
                        st.write(f"**Estado:** {estado_c}")

                        st.markdown("---")
                        st.markdown("##### 💵 Registrar Abono y Comprobante")
                        
                        with st.form(key=f"form_abono_{num_r}"):
                            monto_abono = st.number_input("Monto del Abono ($)", min_value=0.0, max_value=max(0.0, saldo_c), step=1000.0, format="%.2f")
                            archivo_comp = st.file_uploader("Adjuntar Comprobante de Pago (Imagen o PDF)", type=["png", "jpg", "jpeg", "pdf"], key=f"file_comp_{num_r}")
                            btn_guardar_abono = st.form_submit_button("📥 Guardar Abono con Comprobante")

                            if btn_guardar_abono:
                                if monto_abono <= 0:
                                    st.error("El monto del abono debe ser mayor a 0.")
                                else:
                                    bytes_archivo = archivo_comp.read() if archivo_comp is not None else None
                                    nombre_archivo = archivo_comp.name if archivo_comp is not None else None
                                    
                                    registrar_abono(num_r, monto_abono, bytes_archivo, nombre_archivo)
                                    st.success(f"¡Abono de ${monto_abono:,.2f} registrado con éxito!")
                                    st.rerun()

                        st.markdown("##### 📜 Historial de Abonos y Comprobantes")
                        abonos_filas = obtener_abonos_con_comprobante(num_r)
                        if not abonos_filas:
                            st.info("No hay abonos registrados para esta factura.")
                        else:
                            for ab_id, ab_fecha, ab_monto, ab_comp, ab_nom in abonos_filas:
                                c_ab1, c_ab2 = st.columns([2, 1])
                                with c_ab1:
                                    st.write(f"📅 {str(ab_fecha)[:19]} — **${float(ab_monto):,.2f}**")
                                with c_ab2:
                                    if ab_comp and ab_nom:
                                        st.download_button(
                                            label="📎 Ver Comprobante",
                                            data=ab_comp,
                                            file_name=ab_nom,
                                            mime="application/octet-stream",
                                            key=f"dl_comp_{ab_id}"
                                        )
                                    else:
                                        st.caption("Sin archivo adjunto")

    elif st.session_state.seccion_activa == "📊 Stock":
        st.subheader("📦 Stock Actual en Granja")
        st.dataframe(cargar_inventario(), use_container_width=True)

    elif st.session_state.seccion_activa == "📜 Historial":
        st.subheader("📜 Historial de Remisiones")
        df_historial = cargar_remisiones()
        
        if df_historial.empty:
            st.info("No hay remisiones registradas.")
        else:
            busqueda = st.text_input("🔍 Buscar cliente o N° Remisión", placeholder="Ej. RAFAEL GARCIA")
            df_filtrado = df_historial[
                df_historial['cliente'].astype(str).str.contains(busqueda, case=False, na=False) |
                df_historial['num_remision'].astype(str).str.contains(busqueda, case=False, na=False)
            ] if busqueda.strip() else df_historial

            if df_filtrado.empty:
                st.warning("No se encontraron coincidencias.")
            else:
                nums_remision = sorted(df_filtrado['num_remision'].dropna().unique().astype(int), reverse=True)
                for num_sel in nums_remision:
                    df_rem = df_filtrado[df_filtrado['num_remision'] == num_sel]
                    f_sel = df_rem.iloc[0]
                    cli_nombre = str(f_sel.get('cliente', ''))
                    tot_val = df_rem['total'].sum() if 'total' in df_rem.columns else 0.0
                    fecha_db_val = f_sel.get('fecha_emision')
                    
                    if isinstance(fecha_db_val, (datetime, date)):
                        dias_sem = {'Monday':'lunes', 'Tuesday':'martes', 'Wednesday':'miércoles', 'Thursday':'jueves', 'Friday':'viernes', 'Saturday':'sábado', 'Sunday':'domingo'}
                        meses_anio = {1:'enero', 2:'febrero', 3:'marzo', 4:'abril', 5:'mayo', 6:'junio', 7:'julio', 8:'agosto', 9:'septiembre', 10:'octubre', 11:'noviembre', 12:'diciembre'}
                        f_date_obj = fecha_db_val if isinstance(fecha_db_val, date) else fecha_db_val.date()
                        dia_txt = dias_sem.get(f_date_obj.strftime('%A'), '')
                        mes_txt = meses_anio.get(f_date_obj.month, '')
                        fecha_str = f"{dia_txt}, {f_date_obj.day} de {mes_txt} de {f_date_obj.year}"
                        f_date_default = f_date_obj
                    else:
                        fecha_str = str(fecha_db_val)[:10]
                        f_date_default = date.today()
                    
                    with st.expander(f"📄 Remisión No. {num_sel:06d} — {cli_nombre.upper()} | ${tot_val:,.2f} ({fecha_str})"):
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
                        df_items_pdf = df_items_original.groupby("Clasificación").agg({"Cantidad (Huevos)": "sum", "Precio Unitario ($)": "mean", "Subtotal ($)": "sum"}).reset_index()
                        
                        cli_datos = {"nombre": cli_nombre, "cedula": str(f_sel.get('cedula_nit', '')), "direccion": str(f_sel.get('destino', '')), "telefono": str(f_sel.get('telefono', '')), "email": str(f_sel.get('email', ''))}
                        conductor_val = str(f_sel.get('conductor', 'Ivan Herrera'))

                        with tab_pdf:
                            pdf_buf = generar_pdf_remision(num_sel, fecha_str, conductor_val, cli_datos, df_items_pdf, tot_val)
                            st.dataframe(df_items_pdf, use_container_width=True, hide_index=True)
                            st.markdown(f"#### **Total: ${tot_val:,.2f}**")
                            st.download_button(label=f"📥 Descargar PDF No. {num_sel:06d}", data=pdf_buf, file_name=f"Remision_{num_sel:06d}.pdf", mime="application/pdf", key=f"dl_{num_sel}")

                        with tab_editar:
                            with st.form(key=f"form_editar_{num_sel}"):
                                c_fecha = st.date_input("Fecha de la Remisión", value=f_date_default, key=f"fec_{num_sel}")
                                c_cliente = st.text_input("Cliente", value=cli_datos['nombre'], key=f"cli_{num_sel}")
                                c_cedula = st.text_input("Cédula / NIT", value=cli_datos['cedula'], key=f"ced_{num_sel}")
                                c_dir = st.text_input("Dirección", value=cli_datos['direccion'], key=f"dir_{num_sel}")
                                c_tel = st.text_input("Teléfono", value=cli_datos['telefono'], key=f"tel_{num_sel}")
                                c_email = st.text_input("Email", value=cli_datos['email'], key=f"em_{num_sel}")
                                c_cond = st.text_input("Conductor", value=conductor_val, key=f"cond_{num_sel}")
                                
                                df_editado = st.data_editor(df_items_original[["Clasificación", "Cantidad (Huevos)", "Precio Unitario ($)", "Galpón Origen"]], num_rows="dynamic", key=f"edit_{num_sel}")
                                
                                c_b1, c_b2 = st.columns(2)
                                with c_b1: sub_act = st.form_submit_button("💾 Actualizar Cambios")
                                with c_b2: sub_elm = st.form_submit_button("🗑️ Remoción / Eliminar Remisión")
                                
                                if sub_act:
                                    items_validos = df_editado[df_editado["Cantidad (Huevos)"] > 0].copy()
                                    items_validos["Subtotal ($)"] = items_validos["Cantidad (Huevos)"] * items_validos["Precio Unitario ($)"]
                                    items_dict = [{'Clasificación': r['Clasificación'], 'Cantidad (Huevos)': r['Cantidad (Huevos)'], 'Precio Unitario ($)': r['Precio Unitario ($)'], 'Subtotal ($)': r['Subtotal ($)'], 'Galpón': r['Galpón Origen']} for _, r in items_validos.iterrows()]
                                    actualizar_remision_completa(num_sel, c_cliente, c_cedula, c_dir, c_tel, c_email, c_cond, c_fecha, df_rem, items_dict)
                                    st.success("Remisión y cartera actualizadas!")
                                    st.rerun()
                                if sub_elm:
                                    eliminar_remision_completa(num_sel, df_rem)
                                    st.warning("Remisión y registro de cartera eliminados.")
                                    st.rerun()

elif st.session_state.sesion_principal == "📝 Registro Diario":
    st.subheader("📝 Registro Diario")
    st.info("💡 Sección lista para alimentación de datos de postura y mortalidad próximamente.")
    with st.form("diario"):
        st.date_input("Fecha")
        st.selectbox("Galpón", ["Galpón 1", "Galpón 2", "Galpón 3"])
        st.form_submit_button("Guardar")
