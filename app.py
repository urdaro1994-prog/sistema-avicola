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

# --- FUNCIONES DE BASE DE DATOS Y CONEXIÓN ---
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

def inicializar_tabla_gastos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id SERIAL PRIMARY KEY,
            fecha DATE,
            galpon TEXT,
            categoria TEXT,
            descripcion TEXT,
            valor NUMERIC
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def inicializar_tabla_gastos_varios():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gastos_varios (
            id SERIAL PRIMARY KEY,
            fecha DATE,
            categoria TEXT,
            descripcion TEXT,
            valor NUMERIC
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def inicializar_tabla_galpones():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS galpones (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            cantidad_aves INT DEFAULT 0
        );
    """)
    cur.execute("""
        INSERT INTO galpones (nombre, cantidad_aves) VALUES 
        ('Galpón 1', 5000), ('Galpón 2', 5000), ('Galpón 3', 5000)
        ON CONFLICT (nombre) DO NOTHING;
    """)
    conn.commit()
    cur.close()
    conn.close()

def inicializar_tabla_inventario():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            galpon TEXT PRIMARY KEY,
            yumbo INT DEFAULT 0,
            extra INT DEFAULT 0,
            aa INT DEFAULT 0,
            a INT DEFAULT 0,
            b INT DEFAULT 0,
            c INT DEFAULT 0,
            sucio INT DEFAULT 0,
            roto INT DEFAULT 0
        );
    """)
    cur.execute("""
        INSERT INTO inventario (galpon) VALUES 
        ('Galpón 1'), ('Galpón 2'), ('Galpón 3')
        ON CONFLICT (galpon) DO NOTHING;
    """)
    conn.commit()
    cur.close()
    conn.close()

def inicializar_tabla_remisiones():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS remisiones (
            id SERIAL PRIMARY KEY,
            num_remision INT,
            fecha_emision DATE,
            cliente TEXT,
            cedula_nit TEXT,
            telefono TEXT,
            destino TEXT,
            email TEXT,
            conductor TEXT,
            tipo_huevo TEXT,
            cantidad INT,
            precio_unitario NUMERIC,
            total NUMERIC,
            galpon TEXT
        );
    """)
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
            ingreso_alimento NUMERIC DEFAULT 0,
            consumo_alimento NUMERIC DEFAULT 0,
            mortalidad INT DEFAULT 0,
            produccion INT DEFAULT 0,
            edad_semanas INT DEFAULT 0,
            UNIQUE(fecha, galpon)
        );
    """)
    try:
        cur.execute("ALTER TABLE registro_diario ADD COLUMN IF NOT EXISTS edad_semanas INT DEFAULT 0;")
    except Exception:
        conn.rollback()
    conn.commit()
    cur.close()
    conn.close()

# Asegurar creación inicial de todas las tablas requeridas
inicializar_tabla_galpones()
inicializar_tabla_inventario()
inicializar_tabla_remisiones()
inicializar_tabla_registro_diario()

def registrar_diario_db(fecha, galpon, ingreso_alimento, consumo_alimento, mortalidad, produccion, edad_semanas):
    inicializar_tabla_galpones()
    inicializar_tabla_registro_diario()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO registro_diario (fecha, galpon, ingreso_alimento, consumo_alimento, mortalidad, produccion, edad_semanas)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fecha, galpon) 
            DO UPDATE SET 
                ingreso_alimento = EXCLUDED.ingreso_alimento,
                consumo_alimento = EXCLUDED.consumo_alimento,
                mortalidad = EXCLUDED.mortalidad,
                produccion = EXCLUDED.produccion,
                edad_semanas = EXCLUDED.edad_semanas;
        """, (fecha, galpon, ingreso_alimento, consumo_alimento, mortalidad, produccion, edad_semanas))
        
        cur.execute("""
            UPDATE galpones 
            SET cantidad_aves = cantidad_aves - %s 
            WHERE nombre = %s;
        """, (mortalidad, galpon))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def cargar_registro_diario(galpon=None):
    inicializar_tabla_registro_diario()
    conn = get_connection()
    if galpon:
        df = pd.read_sql_query("SELECT * FROM registro_diario WHERE galpon = %s ORDER BY fecha DESC", conn, params=(galpon,))
    else:
        df = pd.read_sql_query("SELECT * FROM registro_diario ORDER BY galpon, fecha DESC", conn)
    conn.close()
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df

def eliminar_registro_diario(registro_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM registro_diario WHERE id = %s", (registro_id,))
    conn.commit()
    cur.close()
    conn.close()

def registrar_gasto(fecha, galpon, categoria, descripcion, valor):
    inicializar_tabla_gastos()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO gastos (fecha, galpon, categoria, descripcion, valor)
        VALUES (%s, %s, %s, %s, %s)
    """, (fecha, galpon, categoria, descripcion, valor))
    conn.commit()
    cur.close()
    conn.close()

def cargar_gastos():
    inicializar_tabla_gastos()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM gastos ORDER BY fecha DESC, id DESC", conn)
    conn.close()
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df

def eliminar_gasto(gasto_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM gastos WHERE id = %s", (gasto_id,))
    conn.commit()
    cur.close()
    conn.close()

def registrar_gasto_vario(fecha, categoria, descripcion, valor):
    inicializar_tabla_gastos_varios()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO gastos_varios (fecha, categoria, descripcion, valor)
        VALUES (%s, %s, %s, %s)
    """, (fecha, categoria, descripcion, valor))
    conn.commit()
    cur.close()
    conn.close()

def cargar_gastos_varios():
    inicializar_tabla_gastos_varios()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM gastos_varios ORDER BY fecha DESC, id DESC", conn)
    conn.close()
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df

def eliminar_gasto_vario(gasto_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM gastos_varios WHERE id = %s", (gasto_id,))
    conn.commit()
    cur.close()
    conn.close()

def reiniciar_sistema_completo():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM abonos_cartera;")
    cur.execute("DELETE FROM cartera;")
    cur.execute("DELETE FROM remisiones;")
    cur.execute("DELETE FROM clientes;")
    cur.execute("DELETE FROM gastos;")
    cur.execute("DELETE FROM gastos_varios;")
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
    inicializar_tabla_clientes()
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
    inicializar_tabla_inventario()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM inventario ORDER BY galpon", conn)
    conn.close()
    return df.set_index('galpon')

def registrar_entrada_inventario(galpon, items_entrada):
    inicializar_tabla_inventario()
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
    inicializar_tabla_inventario()
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
    inicializar_tabla_remisiones()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM remisiones ORDER BY id DESC", conn)
    conn.close()
    if not df.empty:
        if 'num_remision' not in df.columns:
            df['num_remision'] = df['id']
        if 'fecha_emision' in df.columns:
            df['fecha_emision'] = pd.to_datetime(df['fecha_emision']).dt.date
    return df

def obtener_siguiente_num_remision():
    inicializar_tabla_remisiones()
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

def registrar_venta_multiple(cliente, cedula, direccion, telefono, email, conductor, num_remision, fecha_remision, items_venta):
    inicializar_tablas_cartera()
    inicializar_tabla_remisiones()
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

def generar_pdf_acumulado_galpon(galpon, df_registros):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()
    
    style_normal = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#333333"))
    style_bold = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor("#333333"))
    style_right = ParagraphStyle('RightStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#333333"), alignment=2)
    style_right_bold = ParagraphStyle('RightBoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor("#333333"), alignment=2)
    style_th = ParagraphStyle('THStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=1)
    style_th_left = ParagraphStyle('THLeftStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=0)
    style_th_right = ParagraphStyle('THRightStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=2)

    img_logo = Image("LOGOASI.png", width=60, height=60) if os.path.exists("LOGOASI.png") else Paragraph("<b>🥚</b>", style_bold)
    
    header_data = [
        [
            img_logo,
            Paragraph("<b>AGROAVICOLA SANTA ISABEL</b><br/><font size=7>NIT. 901.786.799-7<br/>Reporte Acumulado - Registro Diario</font>", style_normal),
            Paragraph(f"<b>Galpón:</b><br/><font size=11 color='#f26822'><b>{galpon}</b></font>", style_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[70, 314, 156])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))

    table_data = [[
        Paragraph("Fecha", style_th_left),
        Paragraph("Sem", style_th),
        Paragraph("Alim. (kg)", style_th_right),
        Paragraph("Mort.", style_th_right),
        Paragraph("Prod. Total", style_th_right)
    ]]
    
    tot_con = 0.0
    tot_mortalidad = 0
    tot_produccion = 0

    for _, fila in df_registros.iterrows():
        fec = str(fila['fecha'])
        edad = int(fila.get('edad_semanas', 0))
        con = float(fila.get('consumo_alimento', 0))
        mor = int(fila.get('mortalidad', 0))
        prod = int(fila.get('produccion', 0))
        
        tot_con += con
        tot_mortalidad += mor
        tot_produccion += prod

        table_data.append([
            Paragraph(fec, style_normal),
            Paragraph(str(edad), style_normal),
            Paragraph(f"{con:,.1f}".replace(",", "."), style_right),
            Paragraph(f"{mor:,}".replace(",", "."), style_right),
            Paragraph(f"{prod:,}".replace(",", "."), style_right)
        ])

    table_data.append([
        Paragraph("<b>TOTAL</b>", style_bold),
        Paragraph("-", style_bold),
        Paragraph(f"<b>{tot_con:,.1f}</b>".replace(",", "."), style_right_bold),
        Paragraph(f"<b>{tot_mortalidad:,}</b>".replace(",", "."), style_right_bold),
        Paragraph(f"<b>{tot_produccion:,}</b>".replace(",", "."), style_right_bold)
    ])

    t_items = Table(table_data, colWidths=[100, 50, 120, 110, 160])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f2942")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.HexColor("#f8fafc"), colors.white]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")),
        ('LINEABOVE', (0,-1), (-1,-1), 1, colors.HexColor("#0f2942")),
    ]))
    story.append(t_items)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# --- CONTROL DE SESIÓN Y AUTENTICACIÓN ---
if "usuario_autenticado" not in str_app.session_state:
    str_app.session_state.usuario_autenticado = None

PASS_ADMIN = "admin123"
PASS_INVITADO = "invitado123"

if str_app.session_state.usuario_autenticado is None:
    col_logo, col_tit = str_app.columns([1, 3.5])
    with col_logo:
        if os.path.exists("LOGOASI.png"):
            str_app.image("LOGOASI.png", width=110)
        else:
            str_app.markdown("<h1 style='margin: 0;'>🥚</h1>", unsafe_allow_html=True)
    with col_tit:
        str_app.markdown('<h2 style="margin: 0; color: #f26822 !important;">AVÍCOLA SANTA ISABEL</h2><p style="margin: 0;">CONTROL DE ACCESO</p>', unsafe_allow_html=True)

    str_app.markdown("---")
    str_app.subheader("🔒 Iniciar Sesión")
    
    tipo_usuario = str_app.selectbox("Seleccione el Tipo de Usuario", ["Administrador", "Invitado"])
    password_ingresada = str_app.text_input("Contraseña", type="password")

    if str_app.button("🚀 Ingresar al Sistema", use_container_width=True):
        if tipo_usuario == "Administrador":
            if password_ingresada == PASS_ADMIN:
                str_app.session_state.usuario_autenticado = "Administrador"
                str_app.success("¡Bienvenido Administrador!")
                str_app.rerun()
            else:
                str_app.error("Contraseña de Administrador incorrecta.")
        elif tipo_usuario == "Invitado":
            if password_ingresada == PASS_INVITADO:
                str_app.session_state.usuario_autenticado = "Invitado"
                str_app.success("¡Bienvenido Invitado (Modo Lectura)!")
                str_app.rerun()
            else:
                str_app.error("Contraseña de Invitado incorrecta.")

else:
    # --- ENCABEZADO ---
    col_logo, col_tit = str_app.columns([1, 3.5])
    with col_logo:
        if os.path.exists("LOGOASI.png"): str_app.image("LOGOASI.png", width=75)
        else: str_app.markdown("<h1 style='margin: 0;'>🥚</h1>", unsafe_allow_html=True)
    with col_tit:
        rol_actual = str_app.session_state.usuario_autenticado
        color_rol = "#f26822" if rol_actual == "Administrador" else "#3498db"
        str_app.markdown(f'<h2 style="margin: 0; color: #f26822 !important;">AVÍCOLA SANTA ISABEL</h2><p style="margin: 0;">Sesión: <b style="color: {color_rol};">{rol_actual}</b></p>', unsafe_allow_html=True)

    if str_app.button("🚪 Cerrar Sesión"):
        str_app.session_state.usuario_autenticado = None
        str_app.session_state.sesion_principal = None
        str_app.session_state.seccion_activa = None
        str_app.rerun()

    str_app.markdown("---")

    # --- LÓGICA DE NAVEGACIÓN PRINCIPAL ---
    if "sesion_principal" not in str_app.session_state:
        str_app.session_state.sesion_principal = None

    if str_app.session_state.sesion_principal is None:
        c_prin1, c_prin2 = str_app.columns(2)
        with c_prin1:
            if str_app.button("📦 Stock y Ventas", use_container_width=True):
                str_app.session_state.sesion_principal = "📦 Stock y Ventas"
                str_app.session_state.seccion_activa = None
                str_app.rerun()
        with c_prin2:
            if str_app.button("📝 Registro Diario", use_container_width=True):
                str_app.session_state.sesion_principal = "📝 Registro Diario"
                str_app.rerun()

        # Botón de reinicio global solo para Administrador
        if rol_actual == "Administrador":
            str_app.markdown("---")
            if "confirmar_reinicio" not in str_app.session_state:
                str_app.session_state.confirmar_reinicio = False

            if not str_app.session_state.confirmar_reinicio:
                if str_app.button("🧹 Reiniciar Sistema (Dejar en Ceros)", use_container_width=True):
                    str_app.session_state.confirmar_reinicio = True
                    str_app.rerun()
            else:
                str_app.warning("⚠️ ¿Estás completamente seguro? Esto borrará todas las remisiones, abonos, clientes, gastos, registros diarios y pondrá el stock en 0.")
                c_conf1, c_conf2 = str_app.columns(2)
                with c_conf1:
                    if str_app.button("✅ Sí, borrar todo", use_container_width=True):
                        reiniciar_sistema_completo()
                        str_app.session_state.confirmar_reinicio = False
                        str_app.success("¡El sistema ha sido reiniciado a ceros con éxito!")
                        str_app.rerun()
                with c_conf2:
                    if str_app.button("❌ Cancelar", use_container_width=True):
                        str_app.session_state.confirmar_reinicio = False
                        str_app.rerun()
    else:
        if str_app.button("⬅️ Regresar al Menú Principal"):
            str_app.session_state.sesion_principal = None
            str_app.session_state.seccion_activa = None
            str_app.rerun()

    # --- CONTENIDO DE LAS SESIONES ---
    if str_app.session_state.sesion_principal == "📦 Stock y Ventas":
        
        if "seccion_activa" not in str_app.session_state or str_app.session_state.seccion_activa is None:
            str_app.subheader("📦 Módulo Stock y Ventas")
            str_app.caption("Seleccione una opción para continuar:")
            
            col_m1, col_m2 = str_app.columns(2)
            with col_m1:
                if str_app.button("📥 Entradas de Stock", use_container_width=True):
                    str_app.session_state.seccion_activa = "📥 Entradas"
                    str_app.rerun()
                if str_app.button("📤 Nueva Remisión", use_container_width=True):
                    str_app.session_state.seccion_activa = "📤 Remisiones"
                    str_app.rerun()
                if str_app.button("📊 Ver Stock Actual", use_container_width=True):
                    str_app.session_state.seccion_activa = "📊 Stock"
                    str_app.rerun()
                if str_app.button("💸 Control de Gastos", use_container_width=True):
                    str_app.session_state.seccion_activa = "💸 Gastos"
                    str_app.rerun()
            with col_m2:
                if str_app.button("👥 Clientes", use_container_width=True):
                    str_app.session_state.seccion_activa = "👥 Clientes"
                    str_app.rerun()
                if str_app.button("💰 Control de Cartera", use_container_width=True):
                    str_app.session_state.seccion_activa = "💰 Cartera"
                    str_app.rerun()
                if str_app.button("⚖️ Inventario Físico", use_container_width=True):
                    str_app.session_state.seccion_activa = "⚖️ Inventario Fisico"
                    str_app.rerun()
                if str_app.button("📜 Historial de Remisiones", use_container_width=True):
                    str_app.session_state.seccion_activa = "📜 Historial"
                    str_app.rerun()
                if str_app.button("📈 Utilidades por Galpón", use_container_width=True):
                    str_app.session_state.seccion_activa = "📈 Utilidades"
                    str_app.rerun()
                if str_app.button("🏷️ Gastos Varios", use_container_width=True):
                    str_app.session_state.seccion_activa = "🏷️ Gastos Varios"
                    str_app.rerun()

        else:
            if str_app.button("🔙 Volver al Menú de Stock"):
                str_app.session_state.seccion_activa = None
                str_app.rerun()
            
            str_app.markdown("---")

            if str_app.session_state.seccion_activa == "📥 Entradas":
                str_app.subheader("📥 Entrada de Producción / Clasificación")
                if rol_actual == "Invitado":
                    str_app.warning("👀 Modo Invitado: Solo puedes visualizar la sección.")
                else:
                    str_app.caption("Registre los huevos recolectados y clasificados para sumarlos al inventario del galpón correspondiente.")
                    galpon_destino = str_app.selectbox("Seleccione el Galpón de Destino", ["Galpón 1", "Galpón 2", "Galpón 3"])
                    
                    opciones_clasif = ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"]
                    df_base_entrada = pd.DataFrame([{"Clasificación": "a", "Cantidad": 1000}])
                    
                    df_entrada_editado = str_app.data_editor(
                        df_base_entrada,
                        num_rows="dynamic",
                        column_config={
                            "Clasificación": str_app.column_config.SelectboxColumn("Clasificación", options=opciones_clasif, required=True),
                            "Cantidad": str_app.column_config.NumberColumn("Cantidad (Huevos)", min_value=1, step=1, required=True)
                        },
                        use_container_width=True,
                        key="editor_entradas_stock"
                    )
                    
                    if str_app.button("➕ Registrar Entrada al Inventario"):
                        entradas_validas = df_entrada_editado[df_entrada_editado["Cantidad"] > 0].copy()
                        if entradas_validas.empty:
                            str_app.warning("Debe ingresar al menos un ítem con cantidad mayor a 0.")
                        else:
                            lista_items_entrada = []
                            for _, r in entradas_validas.iterrows():
                                lista_items_entrada.append({
                                    "Clasificación": r["Clasificación"],
                                    "Cantidad": int(r["Cantidad"])
                                })
                            registrar_entrada_inventario(galpon_destino, lista_items_entrada)
                            str_app.success(f"¡Entrada de inventario registrada correctamente en {galpon_destino}!")

            elif str_app.session_state.seccion_activa == "⚖️ Inventario Fisico":
                str_app.subheader("⚖️ Inventario Físico y Mermas")
                if rol_actual == "Invitado":
                    str_app.warning("👀 Modo Invitado: Solo puedes visualizar el inventario físico.")
                else:
                    str_app.caption("Selecciona el galpón, ingresa el conteo real exacto de los huevos físicos y el sistema ajustará el inventario.")
                    galpon_fisico = str_app.selectbox("Seleccione el Galpón a Auditar", ["Galpón 1", "Galpón 2", "Galpón 3"])
                    
                    df_inv_actual = cargar_inventario()
                    if galpon_fisico in df_inv_actual.index:
                        fila_galp = df_inv_actual.loc[galpon_fisico]
                    else:
                        fila_galp = pd.Series({'yumbo':0, 'extra':0, 'aa':0, 'a':0, 'b':0, 'c':0, 'sucio':0, 'roto':0})

                    datos_fisicos = []
                    for col_clasif in ['yumbo', 'extra', 'aa', 'a', 'b', 'c', 'sucio', 'roto']:
                        stock_sistema = int(fila_galp.get(col_clasif, 0))
                        datos_fisicos.append({
                            "Clasificación": col_clasif,
                            "Stock Sistema": stock_sistema,
                            "Conteo Físico Real": stock_sistema
                        })
                    
                    df_fisico_base = pd.DataFrame(datos_fisicos)
                    df_fisico_editado = str_app.data_editor(
                        df_fisico_base,
                        disabled=["Clasificación", "Stock Sistema"],
                        use_container_width=True,
                        key=f"editor_fisico_{galpon_fisico}"
                    )

                    df_fisico_editado["Diferencia (Merma/Faltante)"] = df_fisico_editado["Stock Sistema"] - df_fisico_editado["Conteo Físico Real"]
                    str_app.dataframe(df_fisico_editado[["Clasificación", "Stock Sistema", "Conteo Físico Real", "Diferencia (Merma/Faltante)"]], use_container_width=True, hide_index=True)

                    if str_app.button("💾 Guardar y Ajustar Inventario Físico"):
                        nuevo_stock_dict = {}
                        for _, r in df_fisico_editado.iterrows():
                            nuevo_stock_dict[r["Clasificación"]] = int(r["Conteo Físico Real"])
                        actualizar_inventario_fisico(galpon_fisico, nuevo_stock_dict)
                        str_app.success(f"¡Inventario físico de {galpon_fisico} aplicado con éxito!")
                        str_app.rerun()

            elif str_app.session_state.seccion_activa == "💸 Gastos":
                str_app.subheader("💸 Control de Gastos por Galpón")
                if rol_actual == "Invitado":
                    str_app.warning("👀 Modo Invitado: Solo puedes visualizar los gastos registrados.")
                else:
                    with str_app.form(key="form_registrar_gasto"):
                        c_fecha_g = str_app.date_input("Fecha del Gasto", value=date.today())
                        c_galpon_g = str_app.selectbox("Galpón Asociado", ["Galpón 1", "Galpón 2", "Galpón 3", "General / Granja"])
                        c_categoria_g = str_app.selectbox("Categoría de Gasto", ["Alimento", "Medicamentos / Sanidad", "Personal / Mano de Obra", "Mantenimiento / Reparaciones", "Servicios Públicos", "Otros"])
                        c_desc_g = str_app.text_input("Descripción del Gasto", placeholder="Ej. Compra de concentrado")
                        c_valor_g = str_app.number_input("Valor ($)", min_value=0.0, step=1000.0, format="%.0f")
                        
                        if str_app.form_submit_button("💾 Guardar Gasto"):
                            if c_valor_g <= 0:
                                str_app.error("El valor del gasto debe ser mayor a 0.")
                            else:
                                registrar_gasto(c_fecha_g, c_galpon_g, c_categoria_g, c_desc_g, c_valor_g)
                                str_app.success("¡Gasto registrado con éxito!")
                                str_app.rerun()

                str_app.markdown("---")
                str_app.markdown("### 📋 Historial y Resumen de Gastos por Mes")
                df_gastos = cargar_gastos()
                if not df_gastos.empty:
                    df_gastos['dt_fecha'] = pd.to_datetime(df_gastos['fecha'])
                    df_gastos['Año'] = df_gastos['dt_fecha'].dt.year
                    df_gastos['Mes_Num'] = df_gastos['dt_fecha'].dt.month
                    meses_nombres = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
                    df_gastos['Mes_Nombre'] = df_gastos['Mes_Num'].map(meses_nombres)

                    col_f1, col_f2 = str_app.columns(2)
                    anios_disponibles = sorted(df_gastos['Año'].unique().tolist(), reverse=True)
                    with col_f1:
                        anio_sel_g = str_app.selectbox("📅 Filtrar Año", anios_disponibles, key="anio_gasto")
                    
                    meses_disp_nums = sorted(df_gastos[df_gastos['Año'] == anio_sel_g]['Mes_Num'].unique().tolist())
                    meses_opc_dict = {meses_nombres[m]: m for m in meses_disp_nums}
                    with col_f2:
                        mes_nombre_sel = str_app.selectbox("📅 Filtrar Mes", list(meses_opc_dict.keys()), key="mes_gasto")
                    
                    mes_num_sel = meses_opc_dict[mes_nombre_sel]
                    df_gf = df_gastos[(df_gastos['Año'] == anio_sel_g) & (df_gastos['Mes_Num'] == mes_num_sel)]
                    tot_mes = df_gf['valor'].astype(float).sum()
                    str_app.markdown(f"**Total Gastos en {mes_nombre_sel} {anio_sel_g}: ${tot_mes:,.0f}**")

                    for _, row_g in df_gf.iterrows():
                        g_id = row_g['id']
                        with str_app.expander(f"📅 {row_g['fecha']} — [{row_g['galpon']}] {row_g['categoria']}: ${float(row_g['valor']):,.0f}"):
                            str_app.write(f"**Descripción:** {row_g['descripcion']}")
                            if rol_actual == "Administrador":
                                if str_app.button(f"🗑️ Eliminar Gasto #{g_id}", key=f"del_g_{g_id}"):
                                    eliminar_gasto(g_id)
                                    str_app.rerun()

            elif str_app.session_state.seccion_activa == "🏷️ Gastos Varios":
                str_app.subheader("🏷️ Control de Gastos Varios y Personales")
                if rol_actual != "Invitado":
                    with str_app.form(key="form_gv"):
                        f_gv = str_app.date_input("Fecha", value=date.today())
                        cat_gv = str_app.selectbox("Categoría", ["Personal", "Hogar", "Vehículo", "Impuestos", "Varios"])
                        desc_gv = str_app.text_input("Descripción")
                        val_gv = str_app.number_input("Valor ($)", min_value=0.0, step=1000.0, format="%.0f")
                        if str_app.form_submit_button("💾 Guardar Gasto Vario"):
                            if val_gv > 0:
                                registrar_gasto_vario(f_gv, cat_gv, desc_gv, val_gv)
                                str_app.success("Registrado con éxito!")
                                str_app.rerun()
                df_gv = cargar_gastos_varios()
                if not df_gv.empty:
                    for _, r in df_gv.iterrows():
                        with str_app.expander(f"📅 {r['fecha']} — [{r['categoria']}] ${float(r['valor']):,.0f}"):
                            str_app.write(r['descripcion'])
                            if rol_actual == "Administrador":
                                if str_app.button(f"🗑️ Eliminar #{r['id']}", key=f"del_gv_{r['id']}"):
                                    eliminar_gasto_vario(r['id'])
                                    str_app.rerun()

            elif str_app.session_state.seccion_activa == "👥 Clientes":
                str_app.subheader("👥 Directorio de Clientes")
                if rol_actual == "Invitado":
                    df_cli = cargar_clientes()
                    for _, r in df_cli.iterrows():
                        str_app.write(f"👤 **{r['nombre']}** | NIT: {r.get('cedula_nit', '')} | Tel: {r.get('telefono', '')}")
                else:
                    tab_n, tab_l = str_app.tabs(["➕ Agregar", "📋 Lista"])
                    with tab_n:
                        with str_app.form("form_nc"):
                            nom = str_app.text_input("Nombre *")
                            ced = str_app.text_input("Cédula / NIT")
                            dir_c = str_app.text_input("Dirección", value="CHOACHI")
                            tel = str_app.text_input("Teléfono")
                            em = str_app.text_input("Email")
                            if str_app.form_submit_button("💾 Guardar"):
                                if nom.strip():
                                    guardar_cliente(nom, ced, dir_c, tel, em)
                                    str_app.success("Guardado!")
                                    str_app.rerun()
                    with tab_l:
                        df_cli = cargar_clientes()
                        for _, r in df_cli.iterrows():
                            with str_app.expander(f"👤 {r['nombre']}"):
                                str_app.write(f"Tel: {r.get('telefono', '')} | Dir: {r.get('direccion', '')}")
                                if str_app.button(f"🗑️ Eliminar {r['nombre']}", key=f"del_c_{r['id']}"):
                                    eliminar_cliente(r['id'])
                                    str_app.rerun()

            elif str_app.session_state.seccion_activa == "📤 Remisiones":
                str_app.subheader("📋 Nueva Remisión")
                if rol_actual == "Invitado":
                    str_app.warning("Modo Invitado: No disponible.")
                else:
                    df_inv = cargar_inventario()
                    df_clientes = cargar_clientes()
                    num_r = obtener_siguiente_num_remision()
                    
                    str_app.markdown(f"### Remisión No. {num_r:06d}")
                    f_rem = str_app.date_input("Fecha", value=date.today())
                    opc_cli = ["-- Escribir nuevo --"] + df_clientes["nombre"].tolist() if not df_clientes.empty else ["-- Escribir nuevo --"]
                    c_sel = str_app.selectbox("Cliente Guardado", opc_cli)

                    v_nom, v_ced, v_dir, v_tel, v_em = "", "", "CHOACHI", "", ""
                    if c_sel != "-- Escribir nuevo --" and not df_clientes.empty:
                        d_c = df_clientes[df_clientes["nombre"] == c_sel].iloc[0]
                        v_nom, v_ced, v_dir, v_tel, v_em = str(d_c.get("nombre","")), str(d_c.get("cedula_nit","")), str(d_c.get("direccion","CHOACHI")), str(d_c.get("telefono","")), str(d_c.get("email",""))

                    cli_n = str_app.text_input("Razón Social *", value=v_nom)
                    ced_n = str_app.text_input("Cédula / NIT", value=v_ced)
                    dir_n = str_app.text_input("Dirección", value=v_dir)
                    tel_n = str_app.text_input("Teléfono", value=v_tel)
                    em_n = str_app.text_input("Email", value=v_em)
                    cond = str_app.text_input("Conductor", value="Ivan Herrera")
                    
                    df_edit = str_app.data_editor(
                        pd.DataFrame([{"Clasificación": "a", "Cantidad (Huevos)": 3000, "Precio Unitario ($)": 370.0, "Galpón Origen": "Galpón 1"}]),
                        num_rows="dynamic",
                        column_config={
                            "Clasificación": str_app.column_config.SelectboxColumn("Clasificación", options=["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"], required=True),
                            "Cantidad (Huevos)": str_app.column_config.NumberColumn("Cantidad", min_value=0, step=1, required=True),
                            "Precio Unitario ($)": str_app.column_config.NumberColumn("Precio ($)", min_value=0.0, step=1.0, format="$%.0f", required=True),
                            "Galpón Origen": str_app.column_config.SelectboxColumn("Galpón Origen", options=["Galpón 1", "Galpón 2", "Galpón 3"], required=True)
                        },
                        use_container_width=True
                    )

                    items_v = df_edit[df_edit["Cantidad (Huevos)"] > 0].copy()
                    if not items_v.empty:
                        items_v["Subtotal ($)"] = items_v["Cantidad (Huevos)"] * items_v["Precio Unitario ($)"]
                        tot_fac = items_v["Subtotal ($)"].sum()
                        str_app.markdown(f"### Total: ${tot_fac:,.0f}")

                        if str_app.button("🚀 Generar Remisión"):
                            if not cli_n.strip():
                                str_app.error("Ingrese el nombre del cliente.")
                            else:
                                guardar_cliente(cli_n, ced_n, dir_n, tel_n, em_n)
                                items_dict = [{'Clasificación': r['Clasificación'], 'Cantidad (Huevos)': r['Cantidad (Huevos)'], 'Precio Unitario ($)': r['Precio Unitario ($)'], 'Subtotal ($)': r['Subtotal ($)'], 'Galpón': r['Galpón Origen']} for _, r in items_v.iterrows()]
                                registrar_venta_multiple(cli_n, ced_n, dir_n, tel_n, em_n, cond, num_r, f_rem, items_dict)
                                str_app.success("¡Remisión guardada con éxito!")

            elif str_app.session_state.seccion_activa == "💰 Cartera":
                str_app.subheader("💰 Control de Cartera y Abonos")
                df_cartera = cargar_cartera()
                if not df_cartera.empty:
                    for _, rc in df_cartera.iterrows():
                        num_r = int(rc['num_remision'])
                        with str_app.expander(f"Remisión N° {num_r:06d} — {rc['cliente']} | Saldo: ${float(rc['saldo']):,.0f} ({rc['estado']})"):
                            str_app.write(f"Total: ${float(rc['total']):,.0f} | Saldo: ${float(rc['saldo']):,.0f}")
                            if rol_actual == "Administrador":
                                with str_app.form(f"abono_{num_r}"):
                                    m_ab = str_app.number_input("Monto Abono ($)", min_value=0.0, step=1000.0)
                                    arch = str_app.file_uploader("Comprobante", type=["png", "jpg", "jpeg", "pdf"], key=f"f_{num_r}")
                                    if str_app.form_submit_button("Registrar Abono"):
                                        if m_ab > 0:
                                            registrar_abono(num_r, m_ab, arch.read() if arch else None, arch.name if arch else None)
                                            str_app.success("Abono registrado!")
                                            str_app.rerun()

            elif str_app.session_state.seccion_activa == "📊 Stock":
                str_app.subheader("📦 Stock Actual en Granja")
                str_app.dataframe(cargar_inventario(), use_container_width=True)

            elif str_app.session_state.seccion_activa == "📜 Historial":
                str_app.subheader("📜 Historial de Remisiones")
                df_hist = cargar_remisiones()
                if not df_hist.empty:
                    for num_sel in df_hist['num_remision'].unique():
                        df_r = df_hist[df_hist['num_remision'] == num_sel]
                        f_s = df_r.iloc[0]
                        with str_app.expander(f"Remisión N° {int(num_sel):06d} — {f_s.get('cliente','')}"):
                            str_app.dataframe(df_r[['tipo_huevo', 'cantidad', 'precio_unitario', 'total', 'galpon']], use_container_width=True)

            elif str_app.session_state.seccion_activa == "📈 Utilidades":
                str_app.subheader("📈 Utilidades del Mes")
                str_app.caption("Balance financiero: Ventas totales menos gastos operativos (galpón y generales).")
                
                df_rem_util = cargar_remisiones()
                df_gas_util = cargar_gastos()
                
                if df_rem_util.empty and df_gas_util.empty:
                    str_app.info("No hay registros suficientes para calcular utilidades.")
                else:
                    if not df_rem_util.empty:
                        df_rem_util['dt_fecha'] = pd.to_datetime(df_rem_util['fecha_emision'])
                        df_rem_util['Año'] = df_rem_util['dt_fecha'].dt.year
                        df_rem_util['Mes_Num'] = df_rem_util['dt_fecha'].dt.month
                    
                    if not df_gas_util.empty:
                        df_gas_util['dt_fecha'] = pd.to_datetime(df_gas_util['fecha'])
                        df_gas_util['Año'] = df_gas_util['dt_fecha'].dt.year
                        df_gas_util['Mes_Num'] = df_gas_util['dt_fecha'].dt.month

                    anios_u = sorted(list(set(df_rem_util['Año'].dropna().tolist() + df_gas_util['Año'].dropna().tolist())), reverse=True)
                    if not anios_u:
                        anios_u = [date.today().year]
                    
                    c_u1, c_u2 = str_app.columns(2)
                    with c_u1:
                        anio_u_sel = str_app.selectbox("📅 Año", anios_u, key="util_anio")
                    
                    meses_nombres = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
                    with c_u2:
                        mes_u_sel = str_app.selectbox("📅 Mes", list(meses_nombres.values()), key="util_mes")
                    
                    mes_u_num = [k for k, v in meses_nombres.items() if v == mes_u_sel][0]
                    
                    ventas_mes = 0.0
                    if not df_rem_util.empty:
                        df_rem_mes = df_rem_util[(df_rem_util['Año'] == anio_u_sel) & (df_rem_util['Mes_Num'] == mes_u_num)]
                        if not df_rem_mes.empty:
                            ventas_mes = df_rem_mes.groupby('num_remision')['total'].first().sum()

                    gastos_mes = 0.0
                    if not df_gas_util.empty:
                        df_gas_mes = df_gas_util[(df_gas_util['Año'] == anio_u_sel) & (df_gas_util['Mes_Num'] == mes_u_num)]
                        if not df_gas_mes.empty:
                            gastos_mes = df_gas_mes['valor'].astype(float).sum()

                    utilidad_mes = ventas_mes - gastos_mes
                    
                    str_app.markdown(f"""
                        <div style="background-color: #1a3e63; color: white; padding: 15px; border-radius: 10px; margin-top: 15px; border-left: 5px solid #f26822;">
                            <p style="margin: 0; font-size: 16px; color: #f26822 !important;"><b>Balance {mes_u_sel} {anio_u_sel}:</b></p>
                            <hr style="border-color: #2c5282; margin: 8px 0;">
                            <p style="margin: 0; font-size: 14px;">📈 Ventas Totales: <b>$ {ventas_mes:,.0f}</b></p>
                            <p style="margin: 0; font-size: 14px;">📉 Gastos Totales: <b>$ {gastos_mes:,.0f}</b></p>
                            <p style="margin: 0; font-size: 16px; margin-top: 5px;">💰 <b>Utilidad Neta: $ {utilidad_mes:,.0f}</b></p>
                        </div>
                    """, unsafe_allow_html=True)

    elif str_app.session_state.sesion_principal == "📝 Registro Diario":
        str_app.subheader("📝 Registro Diario y Control por Galpón")
        str_app.caption("Selecciona el galpón para registrar los parámetros productivos y genera tu reporte acumulado en PDF:")

        galpones_disp = ["Galpón 1", "Galpón 2", "Galpón 3"]
        galpon_seleccionado = str_app.selectbox("Seleccione el Galpón", galpones_disp, key="select_galpon_diario")

        tab_reg, tab_hist = str_app.tabs(["➕ Registrar / Editar Día", "📊 Historial y Reporte PDF"])

        with tab_reg:
            if rol_actual == "Invitado":
                str_app.warning("👀 Modo Invitado: Solo puedes visualizar los registros diarios.")
            else:
                with str_app.form(key=f"form_reg_diario_{galpon_seleccionado}"):
                    fecha_reg = str_app.date_input("Fecha del Registro", value=date.today())
                    
                    c_d1, c_d2 = str_app.columns(2)
                    with c_d1:
                        edad_sem = str_app.number_input("Edad (Semanas)", min_value=0, step=1, value=0)
                        ingreso_alim = str_app.number_input("Ingreso Alimento (kg)", min_value=0.0, step=1.0, format="%.1f")
                    with c_d2:
                        consumo_alim = str_app.number_input("Consumo Alimento (kg)", min_value=0.0, step=1.0, format="%.1f")
                        mortalidad_val = str_app.number_input("Mortalidad (Aves)", min_value=0, step=1)

                    str_app.markdown("---")
                    str_app.markdown("#### 🥚 Producción")
                    produccion_val = str_app.number_input("Producción Total (Huevos)", min_value=0, step=1)

                    btn_guardar_rd = str_app.form_submit_button("💾 Guardar / Actualizar Registro Diario")
                    if btn_guardar_rd:
                        registrar_diario_db(fecha_reg, galpon_seleccionado, ingreso_alim, consumo_alim, mortalidad_val, produccion_val, edad_sem)
                        str_app.success(f"¡Registro guardado correctamente para {galpon_seleccionado} en fecha {fecha_reg}!")
                        str_app.rerun()

        with tab_hist:
            str_app.markdown(f"### 📋 Registros Acumulados - {galpon_seleccionado}")
            df_registros_galp = cargar_registro_diario(galpon_seleccionado)

            if df_registros_galp.empty:
                str_app.info(f"No hay registros diarios guardados para {galpon_seleccionado}.")
            else:
                tot_ing = df_registros_galp['ingreso_alimento'].astype(float).sum()
                tot_con = df_registros_galp['consumo_alimento'].astype(float).sum()
                tot_mor = df_registros_galp['mortalidad'].astype(int).sum()
                tot_prod = df_registros_galp['produccion'].astype(int).sum()

                str_app.markdown(f"""
                    <div style="background-color: #1a3e63; color: white; padding: 12px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #f26822;">
                        <p style="margin: 0; font-size: 15px; color: #f26822 !important;"><b>Acumulados Totales ({galpon_seleccionado}):</b></p>
                        <p style="margin: 0; font-size: 14px;">📥 Ingreso Alimento: <b>{tot_ing:,.1f} kg</b> | 🍽️ Consumo Alimento: <b>{tot_con:,.1f} kg</b></p>
                        <p style="margin: 0; font-size: 14px;">⚠️ Mortalidad: <b>{tot_mor:,} aves</b> | 🥚 Producción Total: <b>{tot_prod:,}</b></p>
                    </div>
                """, unsafe_allow_html=True)

                pdf_acum_buf = generar_pdf_acumulado_galpon(galpon_seleccionado, df_registros_galp)
                str_app.download_button(
                    label=f"📄 Descargar Reporte Acumulado PDF ({galpon_seleccionado})",
                    data=pdf_acum_buf,
                    file_name=f"Reporte_Acumulado_{galpon_seleccionado.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key=f"dl_pdf_acum_{galpon_seleccionado}"
                )

                str_app.markdown("---")
                str_app.markdown("#### Detalle Diario y Opción de Eliminación")
                
                for _, row_rd in df_registros_galp.iterrows():
                    rd_id = row_rd['id']
                    rd_fecha = str(row_rd['fecha'])
                    rd_edad = row_rd.get('edad_semanas', 0)
                    rd_ing = float(row_rd['ingreso_alimento'])
                    rd_con = float(row_rd['consumo_alimento'])
                    rd_mor = int(row_rd['mortalidad'])
                    rd_prod = int(row_rd['produccion'])

                    with str_app.expander(f"📅 {rd_fecha} (Sem {rd_edad}) — Prod: {rd_prod} | Cons: {rd_con}kg | Mort: {rd_mor}"):
                        str_app.write(f"**Edad:** {rd_edad} sem")
                        str_app.write(f"**Ingreso Alimento:** {rd_ing}kg | **Consumo Alimento:** {rd_con}kg")
                        str_app.write(f"**Producción Total:** {rd_prod}")
                        if rol_actual == "Administrador":
                            if str_app.button(f"🗑️ Eliminar Registro ID {rd_id}", key=f"del_rd_{rd_id}"):
                                eliminar_registro_diario(rd_id)
                                str_app.warning("Registro diario eliminado.")
                                str_app.rerun()
