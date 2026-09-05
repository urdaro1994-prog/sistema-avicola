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

# --- ESTILOS CSS CON FONDO NARANJA Y COMBINACIÓN AZUL/BLANCO ---
st.markdown(
    """
    <style>
    /* Ocultar elementos predeterminados de Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 1. Fondo principal de la App en degradado Naranja cálido */
    .stApp {
        background: linear-gradient(180deg, #FFF3E0 0%, #FFE0B2 100%) !important;
        background-attachment: fixed;
    }

    /* 2. Tarjeta principal flotante blanca con sombra naranja */
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
    
    /* 3. Botones principales en Azul Oscuro Imperial con hover en Naranja */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.2em;
        font-weight: 700;
        font-size: 15px;
        background: linear-gradient(135deg, #0F2C59 0%, #1E3A8A 100%);
        color: #FFFFFF;
        border: none;
        box-shadow: 0px 4px 10px rgba(15, 44, 89, 0.25);
        transition: all 0.25s ease-in-out;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #FF6B00 0%, #E65100 100%);
        color: #FFFFFF;
        box-shadow: 0px 6px 14px rgba(255, 107, 0, 0.35);
        transform: translateY(-1px);
    }
    
    /* 4. Encabezados y títulos */
    h1, h2, h3 {
        color: #0F2C59 !important;
        font-weight: 800 !important;
    }
    
    /* 5. Línea divisoria en Naranja Vibrante */
    hr {
        border-top: 2px solid #FF6B00 !important;
        opacity: 0.85;
        margin-top: 1rem !important;
        margin-bottom: 1.2rem !important;
    }
    
    /* 6. Pestañas de navegación secundaria */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #FFE0B2;
        border-radius: 8px;
        color: #0F2C59;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0F2C59 !important;
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- ENCABEZADO DE LA APP ---
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
            <div style='color: #0F2C59; font-size: 27px; font-weight: 900; letter-spacing: 1.5px; line-height: 1.05; font-family: system-ui, -apple-system, sans-serif;'>
                AGROAVÍCOLA
            </div>
            <div style='color: #E65100; font-size: 21px; font-weight: 800; font-style: italic; letter-spacing: 0.5px; line-height: 1.2;'>
                Santa Isabel
            </div>
            <div style='color: #64748B; font-size: 11px; font-weight: 600; letter-spacing: 0.8px; text-transform: uppercase;'>
                Sistema de Control y Gestión
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- BOTONES DE NAVEGACIÓN RÁPIDA ---
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

# Aquí continúa la lógica del resto de tu aplicación...
