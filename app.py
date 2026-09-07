import streamlit as str_app
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
str_app.set_page_config(
    page_title="Avícola Santa Isabel",
    page_icon="🥚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ICONO PERSONALIZADO (FAVICON) ---
if os.path.exists("LOGOASI.png"):
    with open("LOGOASI.png", "rb") as f:
        b64_svg = base64.b64encode(f.read()).decode('utf-8')
    data_uri = f"data:image/png;base64,{b64_svg}"
else:
    svg_huevo = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="#0f2942"/><text x="50" y="68" font-size="65" text-anchor="middle">🥚</text></svg>"""
    b64_svg = base64.b64encode(svg_huevo.encode('utf-8')).decode('utf-8')
    data_uri = f"data:image/svg+xml;base64,{b64_svg}"

str_app.markdown(f"""
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
        icon.type = 'image/x-icon';
        icon.href = '{data_uri}';
        doc.head.appendChild(icon);
    </script>
""", unsafe_allow_html=True)

# --- ESTILOS CSS ---
str_app.markdown(
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
        font-weight: 650; background-color: #f26822;
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
    return psycopg2.connect(str_app.secrets["postgres"]["url"])

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

def inicializar_tabla_registro_diario():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS registro_diario (
            id SERIAL PRIMARY KEY,
            fecha DATE NOT NULL,
            galpon TEXT NOT NULL,
            semana INT DEFAULT 0,
            mortalidad INT DEFAULT 0,
            alimento_kg NUMERIC(10,2) DEFAULT 0,
            yumbo INT DEFAULT 0,
            extra INT DEFAULT 0,
            aa INT DEFAULT 0,
            a INT DEFAULT 0,
            b INT DEFAULT 0,
            c INT DEFAULT 0,
            sucio INT DEFAULT 0,
            roto INT DEFAULT 0,
            observaciones TEXT,
            UNIQUE(fecha, galpon)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def guardar_registro_diario(fecha, galpon, semana, mortalidad, alimento, huevos_dict, observaciones):
    inicializar_tabla_registro_diario()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO registro_diario (fecha, galpon, semana, mortalidad, alimento_kg, yumbo, extra, aa, a, b, c, sucio, roto, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (fecha, galpon) DO UPDATE SET
            semana = EXCLUDED.semana,
            mortalidad = EXCLUDED.mortalidad,
            alimento_kg = EXCLUDED.alimento_kg,
            yumbo = EXCLUDED.yumbo,
            extra = EXCLUDED.extra,
            aa = EXCLUDED.aa,
            a = EXCLUDED.a,
            b = EXCLUDED.b,
            c = EXCLUDED.c,
            sucio = EXCLUDED.sucio,
            roto = EXCLUDED.roto,
            observaciones = EXCLUDED.observaciones;
    """, (
        fecha, galpon, semana, mortalidad, alimento,
        huevos_dict.get('yumbo', 0),
        huevos_dict.get('extra', 0),
        huevos_dict.get('aa', 0),
        huevos_dict.get('a', 0),
        huevos_dict.get('b', 0),
        huevos_dict.get('c', 0),
        huevos_dict.get('sucio', 0),
        huevos_dict.get('roto', 0),
        observaciones
    ))
    conn.commit()
    cur.close()
    conn.close()

def cargar_registros_diarios():
    inicializar_tabla_registro_diario()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM registro_diario ORDER BY fecha DESC, galpon ASC", conn)
    conn.close()
    return df

def reiniciar_sistema_completo():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM abonos_cartera;")
    cur.execute("DELETE FROM cartera;")
    cur.execute("DELETE FROM remisiones;")
    cur.execute("DELETE FROM clientes;")
    cur.execute("DELETE FROM registro_diario;")
    cur.execute("""
        UPDATE inventario SET 
            yumbo = 0, extra = 0, aa = 0, a = 0, b = 0, c = 0, sucio = 0, roto = 0;
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

def actualizar_inventario_fisico(galpon, nuevo_stock_dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE inventario SET 
            yumbo = %s, extra = %s, aa = %s, a = %s, b = %s, c = %s, sucio = %s, roto = %s
        WHERE galpon = %s
    """, (
        nuevo_stock_dict.get('yumbo', 0),
        nuevo_stock_dict.get('extra', 0),
        nuevo_stock_dict.get('aa', 0),
        nuevo_stock_dict.get('a', 0),
        nuevo_stock_dict.get('b', 0),
        nuevo_stock_dict.get('c', 0),
        nuevo_stock_dict.get('sucio', 0),
        nuevo_stock_dict.get('roto', 0),
        galpon
    ))
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
        cur.execute("SELECT COALESCE(MAX(num_remision), 191) + 1 FROM remisiones")
        num = cur.fetchone()[0]
    except Exception:
        conn.rollback()
        cur.execute("SELECT COALESCE(MAX(id), 191) + 1 FROM remisiones")
        num = cur.fetchone()[0]
    cur.close()
    conn.close()
    return max(num, 192)

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
    
    style_normal = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333"))
    style_bold = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#333333"))
    style_right = ParagraphStyle('RightStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333"), alignment=2)
    style_right_bold = ParagraphStyle('RightBoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#333333"), alignment=2)
    style_th = ParagraphStyle('THStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=1)
    style_th_left = ParagraphStyle('THLeftStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=0)
    style_th_right = ParagraphStyle('THRightStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=2)

    num_str = f"{num_remision:06d}"

    img_logo = Image("LOGOASI.png", width=70, height=70) if os.path.exists("LOGOASI.png") else Paragraph("<b>🥚</b>", style_bold)
    
    header_data = [
        [
            img_logo,
            Paragraph("<b>AGROAVICOLA SANTA ISABEL</b><br/><font size=8>NIT. 901.786.799-7<br/>Cel. 3102397244 - 3125588606</font>", style_normal),
            Paragraph(f"<b>Remisión No.</b><br/><font size=13 color='#f26822'><b>{num_str}</b></font>", style_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[80, 294, 160])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))

    info_data = [
        [
            Paragraph("<b>Fecha</b>", style_bold),
            Paragraph(f": {fecha_str}", style_normal),
            Paragraph("<b>Datos del cliente</b>", style_bold),
            ""
        ],
        [
            Paragraph("<b>Conductor</b>", style_bold),
            Paragraph(f": {conductor}", style_normal),
            Paragraph("<b>Nombre / Razón Social</b>", style_bold),
            Paragraph(f": {cliente_datos['nombre']}", style_normal)
        ],
        [
            Paragraph("", style_normal),
            Paragraph("", style_normal),
            Paragraph("<b>Cédula / NIT</b>", style_bold),
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
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 15))

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

    totales_data = [
        [Paragraph("<b>Subtotal</b>", style_right), Paragraph(f"<b>$ {total_factura:,.0f}</b>".replace(",", "."), style_right_bold)],
        [Paragraph("<b>IVA</b>", style_right), Paragraph("<b>$ 0</b>", style_right_bold)],
        [Paragraph("<b>Total</b>", style_right), Paragraph(f"<b>$ {total_factura:,.0f}</b>".replace(",", "."), style_right_bold)]
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

def seccion_registro_diario():
    str_app.subheader("📝 Registro Diario (Mortalidad, Alimento y Postura)")
    
    inicializar_tabla_registro_diario()
    df_inv = cargar_inventario()
    lista_galpones = df_inv.index.tolist() if not df_inv.empty else ["Galpón 1", "Galpón 2"]

    with str_app.form("form_registro_diario"):
        col1, col2, col3 = str_app.columns(3)
        with col1:
            fecha_reg = str_app.date_input("Fecha del Registro", value=date.today())
        with col2:
            galpon_reg = str_app.selectbox("Galpón", lista_galpones)
        with col3:
            semana_reg = str_app.number_input("Semana de Aves", min_value=0, value=20, step=1)

        str_app.markdown("---")
        col_m, col_a = str_app.columns(2)
        with col_m:
            mortalidad_reg = str_app.number_input("Mortalidad (Aves muertas)", min_value=0, value=0, step=1)
        with col_a:
            alimento_reg = str_app.number_input("Alimento Consumido (Kg)", min_value=0.0, value=0.0, step=0.5)

        str_app.markdown("---")
        str_app.markdown("##### 🥚 Conteo de Huevos por Clasificación")
        
        c1, c2, c3, c4 = str_app.columns(4)
        with c1:
            yumbo = str_app.number_input("Yumbo", min_value=0, value=0, step=1)
            b = str_app.number_input("B", min_value=0, value=0, step=1)
        with c2:
            extra = str_app.number_input("Extra", min_value=0, value=0, step=1)
            c = str_app.number_input("C", min_value=0, value=0, step=1)
        with c3:
            aa = str_app.number_input("AA", min_value=0, value=0, step=1)
            sucio = str_app.number_input("Sucio", min_value=0, value=0, step=1)
        with c4:
            a_clas = str_app.number_input("A", min_value=0, value=0, step=1)
            roto = str_app.number_input("Roto", min_value=0, value=0, step=1)

        observaciones = str_app.text_area("Observaciones o Novedades", placeholder="Ej: Comportamiento normal, cambio de alimento...")

        submitted = str_app.form_submit_button("💾 Guardar Registro Diario")
        if submitted:
            huevos_dict = {
                'yumbo': yumbo, 'extra': extra, 'aa': aa, 'a': a_clas,
                'b': b, 'c': c, 'sucio': sucio, 'roto': roto
            }
            guardar_registro_diario(fecha_reg, galpon_reg, semana_reg, mortalidad_reg, alimento_reg, huevos_dict, observaciones)
            str_app.success(f"¡Registro guardado con éxito para el {galpon_reg} en fecha {fecha_reg}!")
            str_app.rerun()

    str_app.markdown("---")
    str_app.subheader("📊 Historial de Registros Diarios")
    df_registros = cargar_registros_diarios()
    if not df_registros.empty:
        str_app.dataframe(df_registros, use_container_width=True)
    else:
        str_app.info("No hay registros diarios guardados todavía.")
