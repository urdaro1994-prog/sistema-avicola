import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Sistema Avícola",
    page_icon="🐔",
    layout="wide"
)

# Inicializar session_state si no existe
if 'seccion_activa' not in st.session_state:
    st.session_state.seccion_activa = "🏠 Inicio"

# Menú lateral de navegación
st.sidebar.title("Menú de Navegación")
st.session_state.seccion_activa = st.sidebar.radio(
    "Selecciona una sección",
    ["🏠 Inicio", "📥 Remisiones", "🥚 Producción", "⚙️ Configuración"]
)

# Estructura principal según la sección activa
if st.session_state.seccion_activa == "🏠 Inicio":
    st.title("Bienvenido al Sistema Avícola")
    st.write("Utiliza el menú lateral para navegar entre las diferentes secciones.")

elif st.session_state.seccion_activa == "📥 Remisiones":
    st.title("Gestión de Remisiones")
    st.write("Aquí puedes consultar, registrar y reimprimir remisiones.")

elif st.session_state.seccion_activa == "🥚 Producción":
    st.title("Control de Producción")
    st.write("Registro de huevos y estadísticas.")

elif st.session_state.seccion_activa == "⚙️ Configuración":
    st.title("Configuración del Sistema")
    st.write("Ajustes generales y conexión a base de datos.")
