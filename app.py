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
    page_title="App David - Agroavícola Santa Isabel",
    page_icon="🥚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CREAR ÍCONO SVG CON HUEVO PARA APPLE Y ANDROID ---
svg_huevo = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="22" fill="#0F2C59"/>
  <circle cx="50" cy="50" r="38" fill="#FF6B00" opacity="0.2"/>
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
        metaTitle.content = 'App David';
        doc.head.appendChild(metaTitle);
    </script>
""", unsafe_allow_html=True)

# --- ESTILOS CSS PERSONALIZADOS (FONDO NARANJA + COMBINACIÓN AZUL/BLANCO) ---
st.markdown(
    """
    <style>
    /* Ocultar elementos nativos de Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Fondo Naranja Degradado Cálido */
    .stApp {
        background: linear-gradient(180deg, #FFF3E0 0%, #FFE0B2 100%) !important;
        background-attachment: fixed;
    }

    /* Tarjeta Central Flotante Blanca */
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 5rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 520px;
        background-color: #FFFFFF;
        border-radius: 22px;
        box-shadow: 0px 10px 30px rgba(230, 81, 0, 0.18);
        margin-top: 10px;
    }
    
    /* Textos y Etiquetas Visibles en Azul Oscuro Imperial */
    label, .stSelectbox label, .stNumberInput label, .stTextInput label, .stDateInput label {
        color: #0F2C59 !important;
        font-weight: 700 !important;
        font-size: 14px !important;
    }
    
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background-color: #FAFAFA !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 10px !important;
        color: #0F2C59 !important;
    }

    div[data-baseweb="select"] span {
        color: #0F2C59 !important;
        font-weight: 600 !important;
    }

    /* Botones Principales en Azul Oscuro */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.2em;
        font-weight: 700;
        font-size: 14px;
        background: linear-gradient(135deg, #0F2C59 0%, #1E3A8A 100%);
        color: #FFFFFF !important;
        border: none;
        box-shadow: 0px 4px 10px rgba(15, 44, 89, 0.25);
        transition: all 0.25s ease-in-out;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #FF6B00 0%, #E65100 100%);
        color: #FFFFFF !important;
        box-shadow: 0px 6px 14px rgba(255, 107, 0, 0.35);
        transform: translateY(-1px);
    }
    
    /* Títulos e Indicadores */
    h1, h2, h3, p {
        color: #0F2C59 !important;
    }
    
    hr {
        border-top: 2px solid #FF6B00 !important;
        opacity: 0.85;
        margin-top: 0.8rem !important;
        margin-bottom: 1.2rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- CONEXIÓN A BASE DE DATOS POSTGRESQL ---
def get_connection():
    try:
        conn = psycopg2.connect(st.secrets["postgres"]["url"])
        return conn
    except Exception as e:
        st.error(f"Error de conexión a la base de datos: {e}")
        return None

# --- INICIALIZACIÓN DE TABLAS EN LA BASE DE DATOS ---
def init_db():
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL UNIQUE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                id SERIAL PRIMARY KEY,
                fecha DATE NOT NULL,
                tipo_movimiento VARCHAR(20) NOT NULL,
                producto VARCHAR(50) NOT NULL,
                cajas INT DEFAULT 0,
                cubetas INT DEFAULT 0,
                unidades INT DEFAULT 0,
                total_huevos INT NOT NULL,
                cliente VARCHAR(100),
                precio_unidad NUMERIC(10,2) DEFAULT 0,
                total_dinero NUMERIC(12,2) DEFAULT 0,
                consecutivo VARCHAR(20)
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()

init_db()

# --- ENCABEZADO AGROAVÍCOLA SANTA ISABEL ---
col_logo, col_tit = st.columns([1, 3.8])
with col_logo:
    if os.path.exists("ESCUDO.png"):
        st.image("ESCUDO.png", width=80)
    elif os.path.exists("escudo.png"):
        st.image("escudo.png", width=80)
    else:
        st.markdown("<div style='font-size: 55px; text-align: center; line-height: 1;'>🛡️</div>", unsafe_allow_html=True)

with col_tit:
    st.markdown("""
        <div style='padding-left: 5px;'>
            <div style='color: #0F2C59; font-size: 26px; font-weight: 900; letter-spacing: 1.2px; line-height: 1.05; font-family: system-ui, -apple-system, sans-serif;'>
                AGROAVÍCOLA
            </div>
            <div style='color: #E65100; font-size: 20px; font-weight: 800; font-style: italic; letter-spacing: 0.5px; line-height: 1.2;'>
                Santa Isabel
            </div>
            <div style='color: #475569; font-size: 11px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;'>
                Sistema de Control y Gestión
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- NAVEGACIÓN Y PESTAÑAS ---
if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = "📤 Remisiones"

c_nav1, c_nav2, c_nav3, c_nav4, c_nav5 = st.columns(5)
with c_nav1:
    if st.button("📥 Ent.", use_container_width=True): st.session_state.seccion_activa = "📥 Entrada"
with c_nav2:
    if st.button("📤 Rem.", use_container_width=True): st.session_state.seccion_activa = "📤 Remisiones"
with c_nav3:
    if st.button("👥 Cli.", use_container_width=True): st.session_state.seccion_activa = "👥 Clientes"
with c_nav4:
    if st.button("📊 Stk.", use_container_width=True): st.session_state.seccion_activa = "📊 Stock"
with c_nav5:
    if st.button("📜 Hist.", use_container_width=True): st.session_state.seccion_activa = "📜 Historial"

st.markdown("---")

PRODUCTOS = ["JUMBO", "AAA", "AA", "A", "B", "C", "D", "VENCIDO / ROTO"]

# --- FUNCIONES DE BASE DE DATOS ---
def obtener_clientes():
    conn = get_connection()
    if conn:
        df = pd.read_sql("SELECT nombre FROM clientes ORDER BY nombre ASC", conn)
        conn.close()
        return df["nombre"].tolist()
    return []

def agregar_cliente(nombre):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO clientes (nombre) VALUES (%s)", (nombre.strip().upper(),))
            conn.commit()
            st.success(f"Cliente '{nombre.upper()}' agregado con éxito.")
        except Exception as e:
            st.error(f"Error al agregar cliente: {e}")
        finally:
            cursor.close()
            conn.close()

def guardar_movimiento(fecha, tipo, producto, cajas, cubetas, unidades, total_huevos, cliente=None, precio=0, total_dinero=0, consecutivo=None):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventario (fecha, tipo_movimiento, producto, cajas, cubetas, unidades, total_huevos, cliente, precio_unidad, total_dinero, consecutivo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (fecha, tipo, producto, cajas, cubetas, unidades, total_huevos, cliente, precio, total_dinero, consecutivo))
        conn.commit()
        cursor.close()
        conn.close()

def obtener_siguiente_consecutivo():
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(CAST(NULLIF(regexp_replace(consecutivo, '\D', '', 'g'), '') AS INTEGER)) FROM inventario WHERE consecutivo IS NOT NULL")
        res = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        if res:
            return f"REM-{(res + 1):04d}"
    return "REM-0001"

# --- GENERADOR DE PDF REMISIÓN ---
def generar_pdf_remision(consecutivo, fecha, cliente, df_detalles, total_general):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=18, textColor=colors.HexColor('#0F2C59'), fontName='Helvetica-Bold')
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.HexColor('#475569'))
    rem_style = ParagraphStyle('RemStyle', parent=styles['Heading2'], fontSize=14, leading=16, textColor=colors.HexColor('#FF6B00'), alignment=2, fontName='Helvetica-Bold')

    elements = []
    
    logo_p = Paragraph("<b>AGROAVÍCOLA SANTA ISABEL</b><br/><font size=8>NIT / REGISTRO: 123456789-0<br/>Contacto: 310 000 0000</font>", title_style)
    rem_p = Paragraph(f"<b>REMISIÓN</b><br/><font size=11 color='#0F2C59'>Nº {consecutivo}</font><br/><font size=9 color='#475569'>Fecha: {fecha}</font>", rem_style)
    
    header_table = Table([[logo_p, rem_p]], colWidths=[330, 220])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    cli_p = Paragraph(f"<b>CLIENTE:</b> {cliente.upper()}", ParagraphStyle('Cli', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#0F2C59')))
    elements.append(cli_p)
    elements.append(Spacer(1, 12))

    table_data = [["Producto", "Cajas", "Cubet.", "Unid.", "Total H.", "Val. Unid", "Total ($)"]]
    for _, row in df_detalles.iterrows():
        table_data.append([
            str(row["Producto"]),
            str(row["Cajas"]),
            str(row["Cubetas"]),
            str(row["Unidades"]),
            str(row["Total Huevos"]),
            f"${row['Precio Unitario']:,.2f}",
            f"${row['Total ($)']:,.2f}"
        ])
    
    table_data.append(["TOTAL GENERAL", "", "", "", "", "", f"${total_general:,.2f}"])

    t = Table(table_data, colWidths=[110, 50, 50, 50, 70, 90, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F2C59')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FFE0B2')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))
    
    firma_data = [["_______________________", "_______________________"], ["Entregado por", "Recibido por (Cliente)"]]
    tf = Table(firma_data, colWidths=[270, 270])
    tf.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0F2C59')),
        ('FONTSIZE', (0,0), (-1,-1), 9)
    ]))
    elements.append(tf)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- SECCIONES DE LA APLICACIÓN ---
seccion = st.session_state.seccion_activa

if seccion == "📥 Entrada":
    st.subheader("📥 Registro de Entrada de Producción")
    fecha_ent = st.date_input("Fecha de Entrada", datetime.now())
    prod_ent = st.selectbox("Tipo de Huevo", PRODUCTOS)
    
    c1, c2, c3 = st.columns(3)
    with c1: cajas = st.number_input("Cajas (360)", min_value=0, value=0, step=1)
    with c2: cubetas = st.number_input("Cubetas (30)", min_value=0, value=0, step=1)
    with c3: unidades = st.number_input("Unidades", min_value=0, value=0, step=1)
    
    tot_huevos = (cajas * 360) + (cubetas * 30) + unidades
    st.info(f" Total de Huevos a ingresar: **{tot_huevos:,}** unidades")
    
    if st.button("📥 Registrar Entrada", use_container_width=True):
        if tot_huevos > 0:
            guardar_movimiento(fecha_ent, "ENTRADA", prod_ent, cajas, cubetas, unidades, tot_huevos)
            st.success(f"¡Ingresados {tot_huevos:,} huevos de tipo {prod_ent} correctamente!")
            st.rerun()
        else:
            st.warning("Ingrese una cantidad válida mayor a 0.")

elif seccion == "📤 Remisiones":
    st.subheader("📤 Generación de Remisión / Salida")
    clientes_list = obtener_clientes()
    
    if not clientes_list:
        st.warning("⚠️ No hay clientes registrados. Vaya a la sección '👥 Cli.' para registrar uno.")
    else:
        cli_sel = st.selectbox("Seleccionar Cliente", clientes_list)
        fecha_rem = st.date_input("Fecha de Remisión", datetime.now())
        consecutivo_actual = obtener_siguiente_consecutivo()
        st.caption(f"Consecutivo asignado: **{consecutivo_actual}**")
        
        st.markdown("---")
        st.markdown("##### 🛒 Detalle de Productos a Facturar")
        
        if "carrito_remision" not in st.session_state:
            st.session_state.carrito_remision = []
            
        with st.form("form_item"):
            p_sel = st.selectbox("Producto", PRODUCTOS)
            col_a, col_b, col_c = st.columns(3)
            with col_a: c_cajas = st.number_input("Cajas", min_value=0, value=0)
            with col_b: c_cubetas = st.number_input("Cubetas", min_value=0, value=0)
            with col_c: c_unidades = st.number_input("Unidades", min_value=0, value=0)
            p_precio = st.number_input("Precio por Huevo ($)", min_value=0.0, value=500.0, step=10.0)
            
            btn_add = st.form_submit_button("➕ Agregar al Carrito")
            if btn_add:
                t_h = (c_cajas * 360) + (c_cubetas * 30) + c_unidades
                if t_h > 0:
                    val_tot = t_h * p_precio
                    st.session_state.carrito_remision.append({
                        "Producto": p_sel, "Cajas": c_cajas, "Cubetas": c_cubetas,
                        "Unidades": c_unidades, "Total Huevos": t_h,
                        "Precio Unitario": p_precio, "Total ($)": val_tot
                    })
                    st.success(f"Añadido {p_sel} ({t_h:,} huevos)")
                    st.rerun()
                else:
                    st.error("Ingrese una cantidad válida.")

        if st.session_state.carrito_remision:
            df_cart = pd.DataFrame(st.session_state.carrito_remision)
            st.dataframe(df_cart[["Producto", "Total Huevos", "Precio Unitario", "Total ($)"]], use_container_width=True)
            tot_remision = df_cart["Total ($)"].sum()
            st.markdown(f"### **Total Remisión: ${tot_remision:,.2f}**")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🗑️ Vaciar Carrito"):
                    st.session_state.carrito_remision = []
                    st.rerun()
            with col_b2:
                if st.button("✅ Procesar y Crear PDF", use_container_width=True):
                    for item in st.session_state.carrito_remision:
                        guardar_movimiento(
                            fecha_rem, "SALIDA", item["Producto"],
                            item["Cajas"], item["Cubetas"], item["Unidades"],
                            item["Total Huevos"], cli_sel, item["Precio Unitario"],
                            item["Total ($)"], consecutivo_actual
                        )
                    
                    pdf_buf = generar_pdf_remision(consecutivo_actual, fecha_rem.strftime('%d/%m/%Y'), cli_sel, df_cart, tot_remision)
                    st.download_button(
                        label="📄 Descargar Remisión PDF",
                        data=pdf_buf,
                        file_name=f"Remision_{consecutivo_actual}_{cli_sel}.pdf",
                        mime="application/pdf"
                    )
                    st.session_state.carrito_remision = []
                    st.success("¡Remisión procesada y guardada exitosamente!")

elif seccion == "👥 Clientes":
    st.subheader("👥 Registro y Gestión de Clientes")
    nuevo_cli = st.text_input("Nombre del Nuevo Cliente / Distribuidor")
    if st.button("➕ Agregar Cliente", use_container_width=True):
        if nuevo_cli.strip():
            agregar_cliente(nuevo_cli)
            st.rerun()
        else:
            st.warning("Por favor ingrese un nombre válido.")
            
    st.markdown("---")
    st.markdown("##### 📜 Clientes Registrados")
    list_c = obtener_clientes()
    if list_c:
        for c in list_c:
            st.text(f"• {c}")
    else:
        st.info("Aún no hay clientes registrados.")

elif seccion == "📊 Stock":
    st.subheader("📊 Inventario Actual en Stock")
    conn = get_connection()
    if conn:
        df_inv = pd.read_sql("SELECT * FROM inventario", conn)
        conn.close()
        
        if not df_inv.empty:
            resumen = []
            for p in PRODUCTOS:
                entradas = df_inv[(df_inv["producto"] == p) & (df_inv["tipo_movimiento"] == "ENTRADA")]["total_huevos"].sum()
                salidas = df_inv[(df_inv["producto"] == p) & (df_inv["tipo_movimiento"] == "SALIDA")]["total_huevos"].sum()
                stock_h = entradas - salidas
                
                cajas_stk = stock_h // 360
                rem_cajas = stock_h % 360
                cubetas_stk = rem_cajas // 30
                unidades_stk = rem_cajas % 30
                
                resumen.append({
                    "Producto": p,
                    "Stock (Huevos)": stock_h,
                    "Cajas": cajas_stk,
                    "Cubetas": cubetas_stk,
                    "Unid. Sueltas": unidades_stk
                })
            
            st.dataframe(pd.DataFrame(resumen), use_container_width=True)
        else:
            st.info("No hay movimientos registrados en el inventario.")

elif seccion == "📜 Historial":
    st.subheader("📜 Historial de Movimientos")
    conn = get_connection()
    if conn:
        df_hist = pd.read_sql("SELECT fecha, consecutivo, tipo_movimiento, cliente, producto, total_huevos, total_dinero FROM inventario ORDER BY id DESC LIMIT 50", conn)
        conn.close()
        if not df_hist.empty:
            st.dataframe(df_hist, use_container_width=True)
        else:
            st.info("Historial vacío.")
