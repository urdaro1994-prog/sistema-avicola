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

# URL pública de tu logo en GitHub
URL_LOGO = "https://raw.githubusercontent.com/TU_USUARIO/sistema-avicola/main/ESCUDO.png"

# Configuración de la página
st.set_page_config(
    page_title="App David",
    page_icon="🥚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 1. Inyección de Metaetiquetas PWA (Icono y Nombre al instalar)
st.markdown(
    f"""
    <meta name="apple-mobile-web-app-title" content="App David">
    <meta name="application-name" content="App David">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="apple-touch-icon" sizes="180x180" href="{URL_LOGO}">
    <link rel="icon" type="image/png" sizes="192x192" href="{URL_LOGO}">
    <link rel="shortcut icon" href="{URL_LOGO}">
    """,
    unsafe_allow_html=True
)

# 2. Estilos CSS App Móvil
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        max-width: 500px;
    }
    
    .app-header {
        text-align: center;
        background: linear-gradient(135deg, #125375 0%, #0d3850 100%);
        color: white;
        padding: 15px;
        border-radius: 16px;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .app-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 15px;
        border: 1px solid #e1e8ed;
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        font-weight: bold;
        background-color: #125375;
        color: white;
        border: none;
    }
    
    div[data-testid="stDataEditor"] {
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)
