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
    
    /* Estilo para el botón de regresar (un poco más discreto o diferente si se desea) */
    .back-button button {
        background-color: transparent !important;
        border: 1px solid #f26822 !important;
        color: #f26822 !important;
        height: 2.5em !important;
        margin-bottom: 20px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- FUNCIONES DE BASE DE DATOS ---
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])

def cargar_clientes():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM clientes ORDER BY nombre ASC", conn)
    conn.close()
    return df

def cargar_inventario():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM inventario ORDER BY galpon", conn)
    conn.close()
    return df.set_index('galpon')

def cargar_remisiones():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM remisiones ORDER BY id DESC", conn)
    conn.close()
    return df

def obtener_siguiente_num_remision():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(num_remision), 0) + 1 FROM remisiones")
    num = cur.fetchone()[0]
    cur.close()
    conn.close()
    return num

def registrar_venta_multiple(cliente, cedula, direccion, telefono, email, conductor, num_remision, items_venta):
    conn = get_connection()
    cur = conn.cursor()
    fecha_actual = datetime.now()
    for item in items_venta:
        cur.execute(f"INSERT INTO remisiones (num_remision, fecha_emision, cliente, cedula_nit, telefono, destino, email, conductor, tipo_huevo, cantidad, precio_unitario, total, galpon) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (num_remision, fecha_actual, cliente, cedula, telefono, direccion, email, conductor, item['Clasificación'].lower(), item['Cantidad'], item['Precio'], item['Subtotal'], item['Galpón']))
        cur.execute(f"UPDATE inventario SET {item['Clasificación'].lower()} = {item['Clasificación'].lower()} - %s WHERE galpon = %s", (item['Cantidad'], item['Galpón']))
    conn.commit()
    cur.close()
    conn.close()

def generar_pdf_remision(num_remision, fecha_str, conductor, cliente_datos, items_df, total_factura):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    header_data = [[Image("ESCUDO.png", width=60, height=60) if os.path.exists("ESCUDO.png") else "🛡️",
                    Paragraph("<font size=16 color='#ffffff'><b>Remisión de Venta</b></font>", style_normal),
                    Paragraph("<font size=9 color='#ffffff'><b>Avícola Santa Isabel</b><br/>NIT. 901.786.799-7</font>", style_normal)]]
    t_header = Table(header_data, colWidths=[80, 260, 200])
    t_header.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0f2942")), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('TEXTCOLOR', (0,0), (-1,-1), colors.white)]))
    story.append(t_header)
    story.append(Spacer(1, 15))
    cliente_info = [[Paragraph(f"<b>Remisión:</b> {num_remision:06d}<br/><b>Fecha:</b> {fecha_str}<br/><b>Conductor:</b> {conductor}", style_normal),
                     Paragraph(f"<b>Cliente:</b> {cliente_datos['nombre']}<br/><b>NIT/CC:</b> {cliente_datos['cedula']}<br/><b>Dir:</b> {cliente_datos['direccion']}", style_normal)]]
    t_info = Table(cliente_info, colWidths=[240, 300])
    story.append(t_info)
    story.append(Spacer(1, 15))
    table_data = [["Descripción", "Cantidad", "Precio Unit.", "Total"]]
    for _, fila in items_df.iterrows():
        table_data.append([str(fila["Clasificación"]).upper(), f"{int(fila['Cantidad (Huevos)']):,}", f"${fila['Precio Unitario ($)']:,.0f}", f"${fila['Subtotal ($)']:,.0f}"])
    t_items = Table(table_data, colWidths=[200, 100, 120, 120])
    t_items.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f26822")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    story.append(t_items)
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<font size=12><b>TOTAL A PAGAR: ${total_factura:,.0f}</b></font>", styles['Right']))
    doc.build(story)
    buffer.seek(0)
    return buffer

# --- ENCABEZADO ---
col_logo, col_tit = st.columns([1, 3.5])
with col_logo:
    if os.path.exists("ESCUDO.png"): st.image("ESCUDO.png", width=75)
    else: st.markdown("<h1 style='margin: 0;'>🥚</h1>", unsafe_allow_html=True)
with col_tit:
    st.markdown('<h2 style="margin: 0; color: #f26822 !important;">AVÍCOLA SANTA ISABEL</h2><p style="margin: 0;">SISTEMA DE GESTIÓN Dashboard 2.0</p>', unsafe_allow_html=True)

st.markdown("---")

# --- LÓGICA DE NAVEGACIÓN PRINCIPAL ---
if "sesion_principal" not in st.session_state:
    st.session_state.sesion_principal = None

# Solo mostrar los dos botones si no hay ninguna sesión activa
if st.session_state.sesion_principal is None:
    c_prin1, c_prin2 = st.columns(2)
    with c_prin1:
        if st.button("📦 Stock y Ventas", use_container_width=True):
            st.session_state.sesion_principal = "📦 Stock y Ventas"
            st.session_state.seccion_activa = "📤 Remisiones"
            st.rerun()
    with c_prin2:
        if st.button("📝 Registro Diario", use_container_width=True):
            st.session_state.sesion_principal = "📝 Registro Diario"
            st.rerun()
else:
    # BOTÓN PARA REGRESAR SIEMPRE VISIBLE CUANDO ESTÉS EN UNA SESIÓN
    if st.button("⬅️ Regresar al Menú Principal"):
        st.session_state.sesion_principal = None
        st.rerun()

# --- CONTENIDO DE LAS SESIONES ---
if st.session_state.sesion_principal == "📦 Stock y Ventas":
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
        
        cliente_sel = st.selectbox("👤 Cargar Cliente Guardado", ["-- Escribir cliente nuevo --"] + df_clientes["nombre"].tolist())
        val_nombre, val_cedula, val_dir, val_tel, val_email = "", "", "CHOACHI", "", ""
        if cliente_sel != "-- Escribir cliente nuevo --":
            d_cli = df_clientes[df_clientes["nombre"] == cliente_sel].iloc[0]
            val_nombre, val_cedula, val_dir, val_tel, val_email = d_cli['nombre'], d_cli['cedula_nit'], d_cli['direccion'], d_cli['telefono'], d_cli['email']

        c_nom = st.text_input("Razón Social *", value=val_nombre)
        c_ced = st.text_input("Cédula / NIT", value=val_cedula)
        c_dir = st.text_input("Dirección", value=val_dir)
        c_tel = st.text_input("Teléfono", value=val_tel)
        c_em = st.text_input("Email", value=val_email)
        c_cond = st.text_input("Conductor", value="Ivan Herrera")

        st.markdown("### 🛒 Detalle del Despacho")
        opciones_clasif = ["yumbo", "extra", "aa", "a", "b", "c", "sucio", "roto"]
        opciones_galpones = ["Galpón 1", "Galpón 2", "Galpón 3"]
        
        df_base = pd.DataFrame([{"Clasificación": "a", "Cantidad (Huevos)": 3000, "Precio Unitario ($)": 370.0, "Galpón Origen": "Galpón 1"}])
        df_editado = st.data_editor(df_base, num_rows="dynamic", column_config={
            "Clasificación": st.column_config.SelectboxColumn("Clasificación", options=opciones_clasif, required=True),
            "Cantidad (Huevos)": st.column_config.NumberColumn("Cantidad", min_value=1, step=1, required=True),
            "Precio Unitario ($)": st.column_config.NumberColumn("Precio ($)", min_value=0, step=1, format="$%.0f", required=True),
            "Galpón Origen": st.column_config.SelectboxColumn("Galpón Origen", options=opciones_galpones, required=True)
        }, use_container_width=True)

        if not df_editado.empty:
            df_editado["Subtotal ($)"] = df_editado["Cantidad (Huevos)"] * df_editado["Precio Unitario ($)"]
            total_f = df_editado["Subtotal ($)"].sum()
            st.markdown(f'<div style="background-color:#f26822; padding:10px; border-radius:8px; text-align:right;"><h3>TOTAL: ${total_f:,.0f}</h3></div>', unsafe_allow_html=True)
            
            if st.button("🚀 Confirmar y Generar Remisión"):
                items_venta = []
                for _, r in df_editado.iterrows():
                    items_venta.append({'Clasificación': r['Clasificación'], 'Cantidad': r['Cantidad (Huevos)'], 'Precio': r['Precio Unitario ($)'], 'Subtotal': r['Subtotal ($)'], 'Galpón': r['Galpón Origen']})
                registrar_venta_multiple(c_nom, c_ced, c_dir, c_tel, c_em, c_cond, num_remision_actual, items_venta)
                st.success("Remisión guardada!")
                
                # Agrupamos para el PDF
                df_pdf = df_editado.groupby("Clasificación").agg({"Cantidad (Huevos)":"sum", "Precio Unitario ($)":"mean", "Subtotal ($)":"sum"}).reset_index()
                pdf = generar_pdf_remision(num_remision_actual, datetime.now().strftime("%d/%m/%Y"), c_cond, {'nombre':c_nom, 'cedula':c_ced, 'direccion':c_dir}, df_pdf, total_f)
                st.download_button("📥 Descargar PDF", data=pdf, file_name=f"Remision_{num_remision_actual}.pdf")

    elif st.session_state.seccion_activa == "📊 Stock":
        st.subheader("📦 Stock Actual en Granja")
        st.dataframe(cargar_inventario(), use_container_width=True)

    elif st.session_state.seccion_activa == "👥 Clientes":
        st.subheader("👥 Clientes")
        st.dataframe(cargar_clientes(), use_container_width=True)

    elif st.session_state.seccion_activa == "📜 Historial":
        st.subheader("📜 Historial de Ventas")
        st.dataframe(cargar_remisiones(), use_container_width=True)

elif st.session_state.sesion_principal == "📝 Registro Diario":
    st.subheader("📝 Registro Diario")
    st.info("💡 Sección lista para alimentación de datos de postura y mortalidad próximamente.")
    with st.form("diario"):
        f = st.date_input("Fecha")
        g = st.selectbox("Galpón", ["G1", "G2", "G3"])
        st.form_submit_button("Guardar")

¡Espero que esta nueva estructura te resulte mucho más cómoda para trabajar! Avísame qué te gustaría agregar a la parte de **Registro Diario**.

Su slide deck sobre la **Nueva Navegación Dashboard** para Avícola Santa Isabel está listo. No dude en revisarlo para entender la nueva lógica de arquitectura.
