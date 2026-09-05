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

# --- ESTILOS CSS CON CORRECCIÓN DE COLORES DE TEXTO E INPUTS ---
st.markdown(
    """
    <style>
    /* Ocultar menús predeterminados */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 1. Fondo principal de la App en Naranja Cáldido */
    .stApp {
        background: linear-gradient(180deg, #FFF3E0 0%, #FFE0B2 100%) !important;
        background-attachment: fixed;
    }

    /* 2. Tarjeta principal flotante en blanco */
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
    
    /* 3. Corrección de color de etiquetas de texto, inputs y listas desplegables */
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

    /* 4. Botones en Azul Oscuro Imperial con hover Naranja */
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
    
    /* 5. Títulos en Azul Oscuro */
    h1, h2, h3, p {
        color: #0F2C59 !important;
    }
    
    /* 6. Divisores en Naranja */
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

# --- ENCABEZADO CON TEXTO VISIBLE EN AZUL Y NARANJA ---
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

# --- NAVEGACIÓN Y ESTADO ACTIVO ---
if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = "📤 Remisiones"

c_nav1, c_nav2, c_nav3, c_nav4, c_nav5 = st.columns(5)
with c_nav1:
    if st.button("📥 Ent.", use_container_width=True): 
        st.session_state.seccion_activa = "📥 Entrada"
        st.rerun()
with c_nav2:
    if st.button("📤 Rem.", use_container_width=True): 
        st.session_state.seccion_activa = "📤 Remisiones"
        st.rerun()
with c_nav3:
    if st.button("👥 Cli.", use_container_width=True): 
        st.session_state.seccion_activa = "👥 Clientes"
        st.rerun()
with c_nav4:
    if st.button("📊 Stk.", use_container_width=True): 
        st.session_state.seccion_activa = "📊 Stock"
        st.rerun()
with c_nav5:
    if st.button("📜 Hist.", use_container_width=True): 
        st.session_state.seccion_activa = "📜 Historial"
        st.rerun()

st.markdown("---")

# --- LÓGICA DE LAS SECCIONES ---
seccion = st.session_state.seccion_activa

if seccion == "📥 Entrada":
    st.subheader("📥 Registro de Entrada de Inventario")
    st.selectbox("Tipo de Producto / Huevo", ["Huevo Tipo AA", "Huevo Tipo A", "Huevo Tipo B", "Huevo Jumbo"])
    st.number_input("Cantidad (Cubetas/Cajas)", min_value=1, value=10)
    if st.button("Guardar Entrada"):
        st.success("¡Entrada registrada correctamente!")

elif seccion == "📤 Remisiones":
    st.subheader("📤 Generación de Remisión")
    st.selectbox("Seleccionar Cliente", ["Cliente General", "Distribuidora San José", "Supermercado Central"])
    st.text_input("Observaciones o Nota de Entrega", "Entrega por la mañana")
    if st.button("Crear Remisión PDF"):
        st.success("¡Remisión generada con éxito!")

elif seccion == "👥 Clientes":
    st.subheader("👥 Gestión de Clientes")
    st.text_input("Nombre / Razon Social del Cliente")
    st.text_input("Teléfono / Contacto")
    if st.button("Agregar Cliente"):
        st.success("Cliente guardado correctamente.")

elif seccion == "📊 Stock":
    st.subheader("📊 Inventario en Stock")
    data_stock = {"Producto": ["Tipo AA", "Tipo A", "Tipo B"], "Stock Actual": [150, 320, 95]}
    st.table(pd.DataFrame(data_stock))

elif seccion == "📜 Historial":
    st.subheader("📜 Historial de Movimientos")
    st.info("Aquí aparecerá el registro histórico de entradas y salidas.")
