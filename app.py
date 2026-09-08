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
    
    /* Botones principales y de envío */
    .stButton>button, div.stFormSubmitButton>button {
        width: 100% !important; border-radius: 10px !important; height: 3.2em !important;
        font-weight: 650 !important; background-color: #f26822 !important;
        color: white !important; border: 2px solid #ffffff !important;
    }
    
    .stButton>button p, .stButton>button span, div.stFormSubmitButton>button p, div.stFormSubmitButton>button span {
        color: white !important;
    }
    
    .stButton>button:hover, div.stFormSubmitButton>button:hover {
        background-color: #ffffff !important; 
        border-color: #f26822 !important;
    }

    .stButton>button:hover p, .stButton>button:hover span, div.stFormSubmitButton>button:hover p, div.stFormSubmitButton>button:hover span {
        color: #f26822 !important;
    }

    /* Textos generales del contenedor */
    .block-container h1, .block-container h2, .block-container h3, .block-container h4, .block-container p {
        color: #ffffff;
    }

    /* Estilo armónico para los Expander (Historial / Remisiones) */
    [data-testid="stExpander"] {
        background-color: #163559 !important;
        border-radius: 8px !important;
        border: 1px solid #244c7c !important;
    }
    
    [data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span {
        color: #ffffff !important;
        font-weight: bold !important;
    }

    [data-testid="stExpanderDetails"] {
        color: #ffffff !important;
    }
    
    /* Etiquetas de los campos */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label, .stFileUploader label {
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
    cur.execute("INSERT INTO inventario (galpon) VALUES ('Galpón 1') ON CONFLICT (galpon) DO NOTHING;")
    cur.execute("INSERT INTO inventario (galpon) VALUES ('Galpón 2') ON CONFLICT (galpon) DO NOTHING;")
    cur.execute("INSERT INTO inventario (galpon) VALUES ('Galpón 3') ON CONFLICT (galpon) DO NOTHING;")
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

def inicializar_tablas_registro_diario():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS galpon_config (
            galpon TEXT PRIMARY KEY,
            edad_semanas INT DEFAULT 0,
            edad_dias INT DEFAULT 0,
            aves_iniciales INT DEFAULT 0
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS registros_diarios (
            id SERIAL PRIMARY KEY,
            fecha DATE,
            galpon TEXT,
            mortalidad INT DEFAULT 0,
            concentrado_ingresado NUMERIC DEFAULT 0,
            concentrado_consumido NUMERIC DEFAULT 0,
            huevos_recolectados INT DEFAULT 0,
            observaciones TEXT
        );
    """)
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
    inicializar_tabla_clientes()
    inicializar_tabla_inventario()
    inicializar_tabla_remisiones()
    inicializar_tablas_cartera()
    inicializar_tabla_gastos()
    inicializar_tabla_gastos_varios()
    inicializar_tablas_registro_diario()
    
    conn = get_connection()
    cur = conn.cursor()
    
    tablas_a_limpiar = ["abonos_cartera", "cartera", "remisiones", "clientes", "gastos", "gastos_varios", "registros_diarios", "galpon_config"]
    for tabla in tablas_a_limpiar:
        try:
            cur.execute(f"DELETE FROM {tabla};")
        except Exception:
            conn.rollback()
            
    try:
        cur.execute("""
            UPDATE inventario SET 
                yumbo = 0, extra = 0, aa = 0, a = 0, b = 0, c = 0, sucio = 0, roto = 0;
        """)
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

def obtener_siguiente_remision():
    # Consulta el número más alto registrado en la tabla remisiones
    response = supabase.table("remisiones").select("num_remision").order("num_remision", desc=True).limit(1).execute()
    
    if response.data and response.data[0].get("num_remision") is not None:
        ultimo_num = int(response.data[0]["num_remision"])
        # Retorna el siguiente número, asegurando que como mínimo sea 192 si la tabla estuviera por debajo
        return max(ultimo_num + 1, 192)
    
    # Si la tabla está totalmente vacía, inicia en 192
    return 192

def cargar_cartera():
    inicializar_tablas_cartera()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM cartera ORDER BY num_remision DESC", conn)
    conn.close()
    return df

def cargar_abonos_remision(num_remision):
    inicializar_tablas_cartera()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM abonos_cartera WHERE num_remision = %s ORDER BY fecha_abono DESC", conn, params=(num_remision,))
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
    inicializar_tabla_inventario()
    conn = get_connection()
    cur = conn.cursor()

    # Validación estricta de stock antes de procesar la remisión
    for item in items_venta:
        clasificacion = item['Clasificación'].lower()
        cantidad = int(item['Cantidad (Huevos)'])
        galp_origen = item.get('Galpón', 'Galpón 1')
        
        cur.execute(f"SELECT {clasificacion} FROM inventario WHERE galpon = %s", (galp_origen,))
        res = cur.fetchone()
        stock_actual = res[0] if res else 0
        if cantidad > stock_actual:
            cur.close()
            conn.close()
            raise ValueError(f"Stock insuficiente de '{clasificacion.upper()}' en {galp_origen}. Stock actual: {stock_actual:,}, solicitado: {cantidad:,}".replace(",", "."))

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

def guardar_config_galpon(galpon, semanas, dias, aves):
    inicializar_tablas_registro_diario()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO galpon_config (galpon, edad_semanas, edad_dias, aves_iniciales)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (galpon) DO UPDATE SET
            edad_semanas = EXCLUDED.edad_semanas,
            edad_dias = EXCLUDED.edad_dias,
            aves_iniciales = EXCLUDED.aves_iniciales;
    """, (galpon, semanas, dias, aves))
    conn.commit()
    cur.close()
    conn.close()

def cargar_config_galpon(galpon):
    inicializar_tablas_registro_diario()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT edad_semanas, edad_dias, aves_iniciales FROM galpon_config WHERE galpon = %s", (galpon,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    if res:
        return {"edad_semanas": res[0], "edad_dias": res[1], "aves_iniciales": res[2]}
    return None

def registrar_dia_galpon(fecha, galpon, mortalidad, conc_ingresado, conc_consumido, huevos, observaciones):
    inicializar_tablas_registro_diario()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO registros_diarios (fecha, galpon, mortalidad, concentrado_ingresado, concentrado_consumido, huevos_recolectados, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (fecha, galpon, mortalidad, conc_ingresado, conc_consumido, huevos, observaciones))
    conn.commit()
    cur.close()
    conn.close()

def cargar_registros_diarios(galpon=None):
    inicializar_tablas_registro_diario()
    conn = get_connection()
    if galpon:
        df = pd.read_sql_query("SELECT * FROM registros_diarios WHERE galpon = %s ORDER BY fecha DESC, id DESC", conn, params=(galpon,))
    else:
        df = pd.read_sql_query("SELECT * FROM registros_diarios ORDER BY fecha DESC, id DESC", conn)
    conn.close()
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df

def eliminar_registro_diario(reg_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM registros_diarios WHERE id = %s", (reg_id,))
    conn.commit()
    cur.close()
    conn.close()

def generar_pdf_registro_diario(galpon_nombre, config, df_reg, current_edad_str, current_aves, saldo_conc):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()
    
    style_normal = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333"))
    style_bold = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#333333"))
    style_right = ParagraphStyle('RightStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333"), alignment=2)
    style_th = ParagraphStyle('THStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=1)
    style_th_left = ParagraphStyle('THLeftStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=0)
    style_th_right = ParagraphStyle('THRightStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=2)

    img_logo = Image("LOGOASI.png", width=70, height=70) if os.path.exists("LOGOASI.png") else Paragraph("<b>🥚</b>", style_bold)
    
    header_data = [
        [
            img_logo,
            Paragraph("<b>AGROAVICOLA SANTA ISABEL</b><br/><font size=8>NIT. 901.786.799-7<br/>Reporte Registro Diario - " + galpon_nombre + "</font>", style_normal),
            Paragraph(f"<b>Fecha Reporte:</b><br/><font size=10 color='#f26822'><b>{datetime.now().strftime('%Y-%m-%d')}</b></font>", style_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[80, 294, 160])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))

    aves_ini_val = config['aves_iniciales'] if config else 0
    resumen_data = [
        [Paragraph(f"<b>Edad Actual:</b> {current_edad_str}", style_normal), Paragraph(f"<b>Aves Actuales:</b> {current_aves:,}".replace(",", "."), style_normal)],
        [Paragraph(f"<b>Aves Iniciales:</b> {aves_ini_val:,}".replace(",", "."), style_normal), Paragraph(f"<b>Saldo Concentrado:</b> {saldo_conc:,.1f} bultos", style_normal)]
    ]
    t_resumen = Table(resumen_data, colWidths=[267, 267])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_resumen)
    story.append(Spacer(1, 15))

    table_data = [[
        Paragraph("Fecha", style_th_left),
        Paragraph("Mortalidad", style_th),
        Paragraph("Ingreso Conc. (Bultos)", style_th_right),
        Paragraph("Consumo Conc. (Bultos)", style_th_right),
        Paragraph("Huevos", style_th_right)
    ]]
    
    for _, fila in df_reg.iterrows():
        table_data.append([
            Paragraph(str(fila["fecha"]), style_normal),
            Paragraph(str(int(fila.get("mortalidad", 0))), style_right),
            Paragraph(f"{float(fila.get('concentrado_ingresado', 0)):.1f}", style_right),
            Paragraph(f"{float(fila.get('concentrado_consumido', 0)):.1f}", style_right),
            Paragraph(str(int(fila.get("huevos_recolectados", 0))), style_right)
        ])

    t_items = Table(table_data, colWidths=[100, 90, 115, 115, 114])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f2942")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#f8fafc"), colors.white]),
    ]))
    story.append(t_items)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generar_pdf_gastos(df_gastos, titulo_reporte):
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

    img_logo = Image("LOGOASI.png", width=70, height=70) if os.path.exists("LOGOASI.png") else Paragraph("<b>🥚</b>", style_bold)
    
    header_data = [
        [
            img_logo,
            Paragraph("<b>AGROAVICOLA SANTA ISABEL</b><br/><font size=8>NIT. 901.786.799-7<br/>" + titulo_reporte + "</font>", style_normal),
            Paragraph(f"<b>Fecha:</b><br/><font size=10 color='#f26822'><b>{datetime.now().strftime('%Y-%m-%d')}</b></font>", style_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[80, 294, 160])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 15))

    table_data = [[
        Paragraph("Fecha", style_th_left),
        Paragraph("Galpón / Cat.", style_th_left),
        Paragraph("Categoría / Desc.", style_th_left),
        Paragraph("Valor ($)", style_th_right)
    ]]
    
    total_gasto = 0.0
    for _, fila in df_gastos.iterrows():
        val = float(fila.get("valor", 0))
        total_gasto += val
        col2_val = str(fila.get("galpon", fila.get("categoria", "")))
        col3_val = str(fila.get("categoria", "")) if "galpon" in fila else str(fila.get("descripcion", ""))
        
        table_data.append([
            Paragraph(str(fila.get("fecha", "")), style_normal),
            Paragraph(col2_val, style_normal),
            Paragraph(col3_val, style_normal),
            Paragraph(f"$ {val:,.0f}".replace(",", "."), style_right)
        ])

    t_items = Table(table_data, colWidths=[90, 110, 174, 160])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f2942")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#f8fafc"), colors.white]),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    totales_data = [
        [Paragraph("<b>Total Gastos</b>", style_right), Paragraph(f"<b>$ {total_gasto:,.0f}</b>".replace(",", "."), style_right_bold)]
    ]
    t_totales = Table(totales_data, colWidths=[374, 160])
    t_totales.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LINEABOVE', (0,0), (-1,0), 1, colors.HexColor("#0f2942")),
    ]))
    story.append(t_totales)
    
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
                    df_base_entrada = pd.DataFrame([{"Clasificación": "a", "Cantidad": 0}])
                    
                    df_entrada_editado = str_app.data_editor(
                        df_base_entrada,
                        num_rows="dynamic",
                        column_config={
                            "Clasificación": str_app.column_config.SelectboxColumn("Clasificación", options=opciones_clasif, required=True),
                            "Cantidad": str_app.column_config.NumberColumn("Cantidad (Huevos)", min_value=1, step=1, format="%d", required=True)
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
                            str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                            str_app.success(f"¡Entrada de inventario registrada correctamente en {galpon_destino}!")

            elif str_app.session_state.seccion_activa == "⚖️ Inventario Fisico":
                str_app.subheader("⚖️ Inventario Físico y Mermas")
                if rol_actual == "Invitado":
                    str_app.warning("👀 Modo Invitado: Solo lectura.")
                else:
                    galpon_fisico = str_app.selectbox("Seleccione el Galpón a Auditar", ["Galpón 1", "Galpón 2", "Galpón 3"])
                    df_inv_actual = cargar_inventario()
                    fila_galp = df_inv_actual.loc[galpon_fisico] if galpon_fisico in df_inv_actual.index else pd.Series({'yumbo':0, 'extra':0, 'aa':0, 'a':0, 'b':0, 'c':0, 'sucio':0, 'roto':0})

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
                        column_config={
                            "Stock Sistema": str_app.column_config.NumberColumn("Stock Sistema", format="%d"),
                            "Conteo Físico Real": str_app.column_config.NumberColumn("Conteo Físico Real", min_value=0, step=1, format="%d")
                        },
                        use_container_width=True,
                        key=f"editor_fisico_{galpon_fisico}"
                    )

                    df_fisico_editado["Diferencia (Merma/Faltante)"] = df_fisico_editado["Stock Sistema"] - df_fisico_editado["Conteo Físico Real"]
                    str_app.dataframe(df_fisico_editado[["Clasificación", "Stock Sistema", "Conteo Físico Real", "Diferencia (Merma/Faltante)"]], use_container_width=True, hide_index=True)

                    if str_app.button("💾 Guardar y Ajustar Inventario Físico"):
                        nuevo_stock_dict = {r["Clasificación"]: int(r["Conteo Físico Real"]) for _, r in df_fisico_editado.iterrows()}
                        actualizar_inventario_fisico(galpon_fisico, nuevo_stock_dict)
                        str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                        str_app.success(f"¡Inventario físico de {galpon_fisico} aplicado con éxito!")
                        str_app.rerun()

            elif str_app.session_state.seccion_activa == "💸 Gastos":
                str_app.subheader("💸 Control de Gastos por Galpón")
                if rol_actual == "Invitado":
                    str_app.warning("👀 Modo Invitado: Solo lectura.")
                else:
                    with str_app.form(key="form_registrar_gasto"):
                        c_fecha_g = str_app.date_input("Fecha del Gasto", value=date.today())
                        c_galpon_g = str_app.selectbox("Galpón Asociado", ["Galpón 1", "Galpón 2", "Galpón 3", "General / Granja"])
                        c_categoria_g = str_app.selectbox("Categoría de Gasto", ["Alimento", "Medicamentos / Sanidad", "Personal / Mano de Obra", "Mantenimiento / Reparaciones", "Servicios Públicos", "Otros"])
                        c_desc_g = str_app.text_input("Descripción del Gasto", placeholder="Ej. Compra de concentrado fase 1")
                        c_valor_g = str_app.number_input("Valor ($)", min_value=0.0, step=1000.0, format="%.0f")
                        
                        if str_app.form_submit_button("💾 Guardar Gasto"):
                            if c_valor_g <= 0:
                                str_app.error("El valor del gasto debe ser mayor a 0.")
                            else:
                                registrar_gasto(c_fecha_g, c_galpon_g, c_categoria_g, c_desc_g, c_valor_g)
                                str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                str_app.success("¡Gasto registrado con éxito!")
                                str_app.rerun()

                str_app.markdown("---")
                df_gastos = cargar_gastos()
                if not df_gastos.empty:
                    df_gastos['dt_fecha'] = pd.to_datetime(df_gastos['fecha'])
                    df_gastos['Año'] = df_gastos['dt_fecha'].dt.year
                    df_gastos['Mes_Num'] = df_gastos['dt_fecha'].dt.month
                    meses_nombres = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
                    
                    c_f1, c_f2 = str_app.columns(2)
                    anio_sel_g = c_f1.selectbox("📅 Año (Gastos)", sorted(df_gastos['Año'].unique().tolist(), reverse=True), key="anio_gasto")
                    mes_nombre_sel = c_f2.selectbox("📅 Mes (Gastos)", list(meses_nombres.values()), key="mes_gasto")
                    mes_num_sel = [k for k, v in meses_nombres.items() if v == mes_nombre_sel][0]
                    
                    df_gf = df_gastos[(df_gastos['Año'] == anio_sel_g) & (df_gastos['Mes_Num'] == mes_num_sel)]
                    str_app.markdown(f"**Total Gastos Mes:** ${df_gf['valor'].sum():,.0f}")
                    
                    if not df_gf.empty:
                        pdf_gastos_buf = generar_pdf_gastos(df_gf, f"Reporte de Gastos - {mes_nombre_sel} {anio_sel_g}")
                        str_app.download_button(
                            label="📄 Descargar Gastos del Mes en PDF",
                            data=pdf_gastos_buf,
                            file_name=f"Gastos_{mes_nombre_sel}_{anio_sel_g}.pdf",
                            mime="application/pdf"
                        )
                        str_app.markdown("---")

                    for _, row_g in df_gf.iterrows():
                        with str_app.expander(f"📅 {row_g['fecha']} — [{row_g['galpon']}] {row_g['categoria']}: ${float(row_g['valor']):,.0f}"):
                            str_app.write(f"**Desc:** {row_g['descripcion']}")
                            if rol_actual == "Administrador" and str_app.button(f"🗑️ Eliminar Gasto #{row_g['id']}", key=f"del_g_{row_g['id']}"):
                                eliminar_gasto(row_g['id'])
                                str_app.rerun()

            elif str_app.session_state.seccion_activa == "🏷️ Gastos Varios":
                str_app.subheader("🏷️ Control de Gastos Varios y Personales")
                if rol_actual == "Invitado":
                    str_app.warning("👀 Modo Invitado: Solo lectura.")
                else:
                    with str_app.form(key="form_registrar_gv"):
                        c_fecha_gv = str_app.date_input("Fecha", value=date.today())
                        c_cat_gv = str_app.selectbox("Categoría", ["Personal", "Hogar", "Vehículo", "Impuestos", "Varios"])
                        c_desc_gv = str_app.text_input("Descripción")
                        c_val_gv = str_app.number_input("Valor ($)", min_value=0.0, step=1000.0, format="%.0f")
                        if str_app.form_submit_button("💾 Guardar Gasto Vario"):
                            registrar_gasto_vario(c_fecha_gv, c_cat_gv, c_desc_gv, c_val_gv)
                            str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                            str_app.success("¡Guardado!")
                            str_app.rerun()

                df_gv = cargar_gastos_varios()
                if not df_gv.empty:
                    pdf_gv_buf = generar_pdf_gastos(df_gv, "Reporte de Gastos Varios y Personales")
                    str_app.download_button(
                        label="📄 Descargar Gastos Varios en PDF",
                        data=pdf_gv_buf,
                        file_name="Gastos_Varios.pdf",
                        mime="application/pdf"
                    )
                    str_app.markdown("---")

                    for _, r in df_gv.iterrows():
                        with str_app.expander(f"📅 {r['fecha']} — [{r['categoria']}] ${float(r['valor']):,.0f}"):
                            str_app.write(f"**Desc:** {r['descripcion']}")
                            if rol_actual == "Administrador" and str_app.button(f"🗑️ Eliminar #{r['id']}", key=f"del_gv_{r['id']}"):
                                eliminar_gasto_vario(r['id'])
                                str_app.rerun()

            elif str_app.session_state.seccion_activa == "👥 Clientes":
                str_app.subheader("👥 Directorio de Clientes")
                df_cli = cargar_clientes()
                if rol_actual == "Administrador":
                    tab_n, tab_l = str_app.tabs(["➕ Agregar", "📋 Lista"])
                    with tab_n:
                        with str_app.form("form_cli"):
                            nom = str_app.text_input("Nombre *")
                            ced = str_app.text_input("Cédula/NIT")
                            dir_ = str_app.text_input("Dirección")
                            tel = str_app.text_input("Teléfono")
                            em = str_app.text_input("Email")
                            if str_app.form_submit_button("Guardar"):
                                if nom.strip():
                                    guardar_cliente(nom, ced, dir_, tel, em)
                                    str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                    str_app.success("Guardado!")
                                    str_app.rerun()
                    with tab_l:
                        for _, r in df_cli.iterrows():
                            with str_app.expander(f"👤 {r['nombre']}"):
                                str_app.write(f"Tel: {r.get('telefono','')}")
                                if str_app.button(f"🗑️ Eliminar", key=f"del_c_{r['id']}"):
                                    eliminar_cliente(r['id'])
                                    str_app.rerun()
                else:
                    for _, r in df_cli.iterrows():
                        str_app.write(f"👤 **{r['nombre']}** | Tel: {r.get('telefono','')}")

            elif str_app.session_state.seccion_activa == "📤 Remisiones":
                str_app.subheader("📋 Nueva Remisión")
                if rol_actual == "Invitado":
                    str_app.warning("👀 Modo Invitado.")
                else:
                    df_inv = cargar_inventario()
                    df_clientes = cargar_clientes()
                    num_rem_act = obtener_siguiente_num_remision()
                    
                    str_app.markdown(f"### Remisión No. {num_rem_act:06d}")
                    fecha_rem = str_app.date_input("Fecha", value=date.today())
                    opciones_cli = ["-- Escribir cliente nuevo --"] + df_clientes["nombre"].tolist() if not df_clientes.empty else ["-- Escribir cliente nuevo --"]
                    cliente_sel = str_app.selectbox("Cliente Guardado", opciones_cli)

                    v_nom, v_ced, v_dir, v_tel, v_em = "", "", "CHOACHI", "", ""
                    if cliente_sel != "-- Escribir cliente nuevo --" and not df_clientes.empty:
                        d_cli = df_clientes[df_clientes["nombre"] == cliente_sel].iloc[0]
                        v_nom, v_ced, v_dir, v_tel, v_em = str(d_cli.get("nombre","")), str(d_cli.get("cedula_nit","")), str(d_cli.get("direccion","CHOACHI")), str(d_cli.get("telefono","")), str(d_cli.get("email",""))

                    c_nom = str_app.text_input("Cliente *", value=v_nom)
                    c_ced = str_app.text_input("Cédula/NIT", value=v_ced)
                    c_dir = str_app.text_input("Dirección", value=v_dir)
                    c_tel = str_app.text_input("Teléfono", value=v_tel)
                    c_em = str_app.text_input("Email", value=v_em)
                    c_cond = str_app.text_input("Conductor", value="Ivan Herrera")
                    guardar_cli_auto = str_app.checkbox("Guardar cliente", value=True)

                    df_base = pd.DataFrame([{"Clasificación": "a", "Cantidad (Huevos)": 0, "Precio Unitario ($)": 0, "Galpón Origen": "Galpón 1"}])
                    df_editado = str_app.data_editor(
                        df_base, 
                        num_rows="dynamic", 
                        column_config={
                            "Clasificación": str_app.column_config.SelectboxColumn("Clasificación", options=["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"], required=True),
                            "Cantidad (Huevos)": str_app.column_config.NumberColumn("Cantidad (Huevos)", min_value=1, step=1, format="%d", required=True),
                            "Precio Unitario ($)": str_app.column_config.NumberColumn("Precio Unitario ($)", min_value=0, format="$%d", required=True),
                            "Galpón Origen": str_app.column_config.SelectboxColumn("Galpón Origen", options=["Galpón 1", "Galpón 2", "Galpón 3"], required=True)
                        },
                        use_container_width=True
                    )
                    items_validos = df_editado[df_editado["Cantidad (Huevos)"] > 0].copy()

                    if not items_validos.empty:
                        items_validos["Subtotal ($)"] = items_validos["Cantidad (Huevos)"] * items_validos["Precio Unitario ($)"]
                        tot_fac = items_validos["Subtotal ($)"].sum()
                        str_app.markdown(f"#### Total: ${tot_fac:,.0f}")

                        if str_app.button("🚀 Generar Remisión"):
                            if guardar_cli_auto and c_nom.strip():
                                guardar_cliente(c_nom, c_ced, c_dir, c_tel, c_em)
                            
                            items_dict = [{'Clasificación': r['Clasificación'], 'Cantidad (Huevos)': r['Cantidad (Huevos)'], 'Precio Unitario ($)': r['Precio Unitario ($)'], 'Subtotal ($)': r['Subtotal ($)'], 'Galpón': r['Galpón Origen']} for _, r in items_validos.iterrows()]
                            
                            try:
                                registrar_venta_multiple(c_nom, c_ced, c_dir, c_tel, c_em, c_cond, num_rem_act, fecha_rem, items_dict)
                                str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                                str_app.success("¡Remisión guardada con éxito!")

                                cliente_datos = {"nombre": c_nom, "cedula": c_ced, "direccion": c_dir, "telefono": c_tel, "email": c_em}
                                pdf_buf = generar_pdf_remision(num_rem_act, str(fecha_rem), c_cond, cliente_datos, items_validos, tot_fac)
                                str_app.download_button(
                                    label="📄 Descargar Remisión en PDF",
                                    data=pdf_buf,
                                    file_name=f"Remision_{num_rem_act:06d}.pdf",
                                    mime="application/pdf"
                                )
                            except ValueError as e:
                                str_app.error(str(e))

            elif str_app.session_state.seccion_activa == "💰 Cartera":
                str_app.subheader("💰 Control de Cartera e Historial de Abonos")
                df_cartera = cargar_cartera()
                if df_cartera.empty:
                    str_app.info("Sin deudas registradas.")
                else:
                    for _, row in df_cartera.iterrows():
                        with str_app.expander(f"Remisión N° {int(row['num_remision']):06d} — {row['cliente']} | Saldo: ${float(row['saldo']):,.0f} ({row['estado']})"):
                            str_app.markdown("#### 📜 Historial de Abonos")
                            df_abonos = cargar_abonos_remision(int(row['num_remision']))
                            if not df_abonos.empty:
                                df_abonos_mostrar = df_abonos[['fecha_abono', 'monto', 'nombre_comprobante']].copy()
                                df_abonos_mostrar.columns = ['Fecha y Hora', 'Monto ($)', 'Comprobante']
                                df_abonos_mostrar['Monto ($)'] = df_abonos_mostrar['Monto ($)'].apply(lambda x: f"${float(x):,.0f}".replace(",", "."))
                                str_app.dataframe(df_abonos_mostrar, use_container_width=True, hide_index=True)
                            else:
                                str_app.info("No hay abonos registrados para esta remisión.")

                            str_app.markdown("---")
                            if rol_actual == "Administrador":
                                with str_app.form(key=f"ab_{row['num_remision']}"):
                                    str_app.markdown("#### ➕ Registrar Nuevo Abono")
                                    monto = str_app.number_input("Abono ($)", min_value=0.0, max_value=float(row['saldo']), step=1000.0, format="%.0f")
                                    arch = str_app.file_uploader("Comprobante (Opcional)", type=["png","jpg","jpeg","pdf"], key=f"f_{row['num_remision']}")
                                    if str_app.form_submit_button("Registrar Abono"):
                                        if monto <= 0:
                                            str_app.error("El monto del abono debe ser mayor a 0.")
                                        else:
                                            registrar_abono(int(row['num_remision']), monto, arch.read() if arch else None, arch.name if arch else None)
                                            str_app.toast("¡Abono registrado con éxito! 🎉", icon="✅")
                                            str_app.success("¡Abono registrado correctamente!")
                                            str_app.rerun()

            elif str_app.session_state.seccion_activa == "📊 Stock":
                str_app.subheader("📦 Stock Actual")
                str_app.dataframe(cargar_inventario(), use_container_width=True)

            elif str_app.session_state.seccion_activa == "📜 Historial":
                str_app.subheader("📜 Historial de Remisiones")
                df_h = cargar_remisiones()
                if not df_h.empty:
                    for num_sel in sorted(df_h['num_remision'].unique(), reverse=True):
                        df_r = df_h[df_h['num_remision'] == num_sel]
                        f_sel = df_r.iloc[0]
                        cliente_nombre = f_sel.get('cliente', '')
                        
                        with str_app.expander(f"Remisión #{int(num_sel):06d} – {cliente_nombre}"):
                            columnas_deseadas = ['tipo_huevo', 'cantidad', 'precio_unitario', 'total', 'galpon']
                            columnas_validas = [col for col in columnas_deseadas if col in df_r.columns]
                            
                            if not df_r.empty and columnas_validas:
                                str_app.dataframe(df_r[columnas_validas], use_container_width=True)
                                
                                cliente_datos = {
                                    "nombre": cliente_nombre,
                                    "cedula": f_sel.get('cedula_nit', ''),
                                    "direccion": f_sel.get('destino', 'CHOACHI'),
                                    "telefono": f_sel.get('telefono', ''),
                                    "email": f_sel.get('email', '')
                                }
                                
                                items_pdf = df_r.rename(columns={
                                    'tipo_huevo': 'Clasificación',
                                    'cantidad': 'Cantidad (Huevos)',
                                    'precio_unitario': 'Precio Unitario ($)',
                                    'total': 'Subtotal ($)'
                                })
                                
                                total_factura = df_r['total'].sum()
                                fecha_str = str(f_sel.get('fecha_emision', date.today()))
                                conductor_val = f_sel.get('conductor', 'Ivan Herrera')
                                
                                pdf_buf = generar_pdf_remision(int(num_sel), fecha_str, conductor_val, cliente_datos, items_pdf, total_factura)
                                
                                str_app.download_button(
                                    label=f"📄 Descargar PDF Remisión #{int(num_sel):06d}",
                                    data=pdf_buf,
                                    file_name=f"Remision_{int(num_sel):06d}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_hist_{num_sel}"
                                )
                            else:
                                str_app.warning("No se encontraron registros o columnas válidas para esta remisión.")
                else:
                    str_app.info("No hay remisiones registradas.")

            elif str_app.session_state.seccion_activa == "📈 Utilidades":
                str_app.subheader("📈 Utilidades por Galpón")
                str_app.caption("Análisis financiero de ingresos por ventas, gastos directos y utilidad neta por galpón.")
                
                df_rem = cargar_remisiones()
                df_gas = cargar_gastos()
                
                if df_rem.empty and df_gas.empty:
                    str_app.info("No hay datos suficientes de ventas o gastos para calcular utilidades.")
                else:
                    galpones = ["Galpón 1", "Galpón 2", "Galpón 3"]
                    resumen_utilidades = []
                    
                    for g in galpones:
                        ingresos = 0.0
                        if not df_rem.empty and 'galpon' in df_rem.columns and 'total' in df_rem.columns:
                            ingresos = float(df_rem[df_rem['galpon'] == g]['total'].sum())
                        
                        gastos = 0.0
                        if not df_gas.empty and 'galpon' in df_gas.columns and 'valor' in df_gas.columns:
                            gastos = float(df_gas[df_gas['galpon'] == g]['valor'].sum())
                        
                        utilidad = ingresos - gastos
                        resumen_utilidades.append({
                            "Galpón": g,
                            "Ingresos ($)": ingresos,
                            "Gastos ($)": gastos,
                            "Utilidad ($)": utilidad
                        })
                    
                    gastos_generales = 0.0
                    if not df_gas.empty and 'galpon' in df_gas.columns and 'valor' in df_gas.columns:
                        gastos_generales = float(df_gas[df_gas['galpon'] == "General / Granja"]['valor'].sum())
                    
                    df_util = pd.DataFrame(resumen_utilidades)
                    
                    total_ingresos = df_util["Ingresos ($)"].sum()
                    total_gastos_galpones = df_util["Gastos ($)"].sum()
                    total_gastos_gral = gastos_generales
                    utilidad_neta_total = total_ingresos - (total_gastos_galpones + total_gastos_gral)
                    
                    col_u1, col_u2, col_u3 = str_app.columns(3)
                    col_u1.metric("Total Ingresos", f"${total_ingresos:,.0f}".replace(",", "."))
                    col_u2.metric("Total Gastos", f"${(total_gastos_galpones + total_gastos_gral):,.0f}".replace(",", "."))
                    col_u3.metric("Utilidad Neta", f"${utilidad_neta_total:,.0f}".replace(",", "."))
                    
                    str_app.markdown("---")
                    str_app.markdown("#### 📋 Detalle Financiero por Galpón")
                    
                    df_mostrar = df_util.copy()
                    df_mostrar["Ingresos ($)"] = df_mostrar["Ingresos ($)"].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                    df_mostrar["Gastos ($)"] = df_mostrar["Gastos ($)"].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                    df_mostrar["Utilidad ($)"] = df_mostrar["Utilidad ($)"].apply(lambda x: f"$ {x:,.0f}".replace(",", "."))
                    
                    str_app.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                    
                    if gastos_generales > 0:
                        str_app.info(f"💡 Gastos Generales / Granja no asignados a un galpón específico: $ {gastos_generales:,.0f}".replace(",", "."))

    elif str_app.session_state.sesion_principal == "📝 Registro Diario":
        str_app.subheader("📜 Módulo de Registro Diario (Edades, Mortalidad y Concentrado)")
        galpon_reg = str_app.selectbox("Seleccione el Galpón", ["Galpón 1", "Galpón 2", "Galpón 3"], key="galp_reg_sel")
        tab_config, tab_diario, tab_historial = str_app.tabs(["⚙️ Configuración Inicial", "✍️ Registrar Día", "📊 Historial y PDF"])
        
        with tab_config:
            str_app.markdown("#### Configuración Inicial del Lote (Se ingresa una sola vez)")
            config_actual = cargar_config_galpon(galpon_reg)
        
            ini_sem = config_actual['edad_semanas'] if config_actual else 0
            ini_dias = config_actual['edad_dias'] if config_actual else 0
            ini_aves = config_actual['aves_iniciales'] if config_actual else 0
            
            with str_app.form(f"form_config_{galpon_reg}"):
                c_sem = str_app.number_input("Edad Inicial (Semanas)", min_value=0, value=int(ini_sem), step=1)
                c_dias = str_app.number_input("Edad Inicial (Días adicionales 0-6)", min_value=0, max_value=6, value=int(ini_dias), step=1)
                c_aves = str_app.number_input("Número de Aves Iniciales del Lote", min_value=0, value=int(ini_aves), step=10)
                
                if str_app.form_submit_button("💾 Guardar Configuración del Galpón"):
                    guardar_config_galpon(galpon_reg, c_sem, c_dias, c_aves)
                    str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                    str_app.success(f"¡Configuración de {galpon_reg} guardada con éxito!")
                    str_app.rerun()

        with tab_diario:
            if rol_actual == "Invitado":
                str_app.warning("👀 Modo Invitado: No tienes permisos para registrar datos diarios.")
            else:
                config = cargar_config_galpon(galpon_reg)
                if not config:
                    str_app.warning("⚠️ Primero debes configurar la Edad y Aves Iniciales en la pestaña 'Configuración Inicial'.")
                else:
                    with str_app.form(f"form_reg_diario_{galpon_reg}"):
                        fecha_reg = str_app.date_input("Fecha del Registro", value=date.today())
                        mortalidad = str_app.number_input("Mortalidad del Día (Aves muertas)", min_value=0, value=0, step=1)
                        conc_ing = str_app.number_input("Concentrado Ingresado (Bultos)", min_value=0.0, value=0.0, step=0.5, format="%g")
                        conc_cons = str_app.number_input("Concentrado Consumido (Bultos)", min_value=0.0, value=0.0, step=0.5, format="%g")
                        huevos = str_app.number_input("Huevos Recolectados (Opcional)", min_value=0, value=0, step=1)
                        obs = str_app.text_input("Observaciones / Novedades")
                        
                        if str_app.form_submit_button("📥 Guardar Registro Diario"):
                            registrar_dia_galpon(fecha_reg, galpon_reg, int(mortalidad), float(conc_ing), float(conc_cons), int(huevos), obs)
                            str_app.toast("¡Registrado con éxito! 🎉", icon="✅")
                            str_app.success(f"¡Registro diario guardado para {galpon_reg}! La edad y el stock de aves se han actualizado automáticamente.")
                            str_app.rerun()

        with tab_historial:
            str_app.markdown(f"#### 📊 Resumen y Registros de {galpon_reg}")
            config = cargar_config_galpon(galpon_reg)
            df_reg = cargar_registros_diarios(galpon_reg)
            
            if not config:
                str_app.info("Galpón sin configuración inicial.")
            else:
                dias_acumulados = len(df_reg)
                total_dias_calc = config['edad_dias'] + dias_acumulados
                semanas_extra = total_dias_calc // 7
                dias_finales = total_dias_calc % 7
                edad_actual_sem = config['edad_semanas'] + semanas_extra
                edad_actual_str = f"{edad_actual_sem} semanas y {dias_finales} días"
                
                total_mortalidad = int(df_reg['mortalidad'].sum()) if not df_reg.empty else 0
                aves_actuales = config['aves_iniciales'] - total_mortalidad
                
                total_conc_ing = float(df_reg['concentrado_ingresado'].sum()) if not df_reg.empty else 0.0
                total_conc_cons = float(df_reg['concentrado_consumido'].sum()) if not df_reg.empty else 0.0
                saldo_concentrado = total_conc_ing - total_conc_cons

                # Cálculo del porcentaje de producción de la última semana (últimos 7 días)
                porc_prod_semana = 0.0
                if not df_reg.empty and 'huevos_recolectados' in df_reg.columns:
                    df_ultimos_7 = df_reg.head(7)
                    total_huevos_7d = df_ultimos_7['huevos_recolectados'].sum()
                    dias_conteo = len(df_ultimos_7)
                    if dias_conteo > 0 and aves_actuales > 0:
                        promedio_diario_huevos = total_huevos_7d / dias_conteo
                        porc_prod_semana = (promedio_diario_huevos / aves_actuales) * 100

                str_app.markdown(f"""
                    <div style="background-color: #1a3e63; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #f26822;">
                        <p style="margin: 0; font-size: 16px; color: #f26822 !important;"><b>Edad Actual del Lote:</b> {edad_actual_str}</p>
                        <p style="margin: 0; font-size: 14px;">Aves Iniciales: {config['aves_iniciales']:,} | Mortalidad Acumulada: {total_mortalidad}</p>
                        <p style="margin: 0; font-size: 15px; color: #f26822 !important;"><b>Aves Vivas Actuales:</b> {aves_actuales:,}</p>
                        <p style="margin: 0; font-size: 15px; color: #f26822 !important;"><b>% Producción Acumulado (Últimos 7 días):</b> {porc_prod_semana:.2f}%</p>
                        <hr style="border-color: #2c5282; margin: 8px 0;">
                        <p style="margin: 0; font-size: 14px;">Concentrado Ingresado: {total_conc_ing:.1f} bultos | Consumido: {total_conc_cons:.1f} bultos</p>
                        <p style="margin: 0; font-size: 15px; color: #2c5282 !important;"><b>Saldo Concentrado Bodega:</b> {saldo_concentrado:.1f} bultos</p>
                    </div>
                """, unsafe_allow_html=True)

                if not df_reg.empty:
                    pdf_buf = generar_pdf_registro_diario(galpon_reg, config, df_reg, edad_actual_str, aves_actuales, saldo_concentrado)
                    str_app.download_button(
                        label=f"📄 Descargar Reporte PDF de {galpon_reg}",
                        data=pdf_buf,
                        file_name=f"Registro_Diario_{galpon_reg.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
                    
                    str_app.markdown("---")
                    str_app.markdown("#### 📑 Detalle Histórico de Registros")
                    for _, row in df_reg.iterrows():
                        r_id = row['id']
                        r_fecha = str(row['fecha'])
                        r_mort = int(row['mortalidad'])
                        r_ing = float(row['concentrado_ingresado'])
                        r_cons = float(row['concentrado_consumido'])
                        r_hue = int(row['huevos_recolectados'])
                        r_obs = row['observaciones']

                        with str_app.expander(f"📅 {r_fecha} | Mortalidad: {r_mort} | Conc. Consumido: {r_cons} bultos"):
                            str_app.write(f"**Concentrado Ingresado:** {r_ing} bultos")
                            str_app.write(f"**Huevos Recolectados:** {r_hue}")
                            str_app.write(f"**Observaciones:** {r_obs}")
                            if rol_actual == "Administrador" and str_app.button(f"🗑️ Eliminar Registro #{r_id}", key=f"del_reg_{r_id}"):
                                eliminar_registro_diario(r_id)
                                str_app.warning("Registro diario eliminado y cálculos actualizados.")
                                str_app.rerun()
                else:
                    str_app.info("No hay registros diarios ingresados todavía para este galpón.")
